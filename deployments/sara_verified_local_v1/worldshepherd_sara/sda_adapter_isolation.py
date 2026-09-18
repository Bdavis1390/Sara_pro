from __future__ import annotations

import os
import resource
import signal
import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SdaAdapterIsolationError(RuntimeError):
    pass


class SdaAdapterRunStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    INPUT_REJECTED = "INPUT_REJECTED"
    TIMED_OUT = "TIMED_OUT"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    PROCESS_FAILED = "PROCESS_FAILED"


class SdaAdapterIsolationPolicy(BaseModel):
    """Bounded local subprocess policy for one trusted adapter executable.

    This gate constrains untrusted input presented to a configured adapter. It is
    not a complete hostile-code sandbox: it does not create a network namespace,
    chroot/pivot_root, seccomp profile, SELinux/AppArmor domain, or container.
    """

    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1, max_length=128)
    adapter_id: str = Field(min_length=1, max_length=128)
    adapter_version: str = Field(min_length=1, max_length=64)
    executable_path: str = Field(min_length=1, max_length=4096)
    max_input_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    max_output_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    max_stderr_bytes: int = Field(ge=1, le=4 * 1024 * 1024)
    timeout_seconds: float = Field(gt=0.0, le=120.0)
    cpu_seconds: int = Field(ge=1, le=120)
    memory_limit_bytes: int = Field(ge=64 * 1024 * 1024, le=4 * 1024 * 1024 * 1024)
    max_open_files: int = Field(ge=8, le=256)
    allow_exit_codes: list[int] = Field(default_factory=lambda: [0], min_length=1, max_length=16)

    @field_validator("executable_path")
    @classmethod
    def executable_must_be_absolute(cls, value: str) -> str:
        path = Path(value)
        if not path.is_absolute():
            raise ValueError("adapter executable_path must be absolute")
        if "\x00" in value:
            raise ValueError("adapter executable_path contains NUL")
        return value

    @field_validator("allow_exit_codes")
    @classmethod
    def exit_codes_are_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("allow_exit_codes contains duplicates")
        return value


class SdaAdapterRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SdaAdapterRunStatus
    return_code: int | None
    stdout: bytes
    stderr: bytes
    input_bytes: int = Field(ge=0)
    stdout_bytes: int = Field(ge=0)
    stderr_bytes: int = Field(ge=0)
    environment_keys_exposed: list[str] = Field(default_factory=list)
    working_directory_ephemeral: bool = True
    network_isolation_enforced: bool = False
    claims_boundary: str = (
        "Reference local subprocess resource/isolation evidence only. No network "
        "namespace, chroot, seccomp, MAC policy, container escape resistance, "
        "hostile-code sandboxing, production accreditation, or classified-network "
        "authorization is established."
    )


def _validate_command(policy: SdaAdapterIsolationPolicy, arguments: Sequence[str]) -> list[str]:
    if len(arguments) > 64:
        raise SdaAdapterIsolationError("adapter argument count exceeds 64")
    command = [policy.executable_path]
    for value in arguments:
        if not isinstance(value, str):
            raise SdaAdapterIsolationError("adapter arguments must be strings")
        if not value or len(value) > 8192:
            raise SdaAdapterIsolationError("adapter argument must contain 1-8192 characters")
        if "\x00" in value:
            raise SdaAdapterIsolationError("adapter argument contains NUL")
        command.append(value)
    return command


def _set_child_limits(policy: SdaAdapterIsolationPolicy) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (policy.cpu_seconds, policy.cpu_seconds),
    )
    resource.setrlimit(
        resource.RLIMIT_AS,
        (policy.memory_limit_bytes, policy.memory_limit_bytes),
    )
    resource.setrlimit(
        resource.RLIMIT_NOFILE,
        (policy.max_open_files, policy.max_open_files),
    )
    file_limit = max(policy.max_output_bytes, policy.max_stderr_bytes)
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))


def _bounded_read(path: Path, limit: int) -> tuple[bytes, int, bool]:
    size = path.stat().st_size
    exceeded = size > limit
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        exceeded = True
        data = data[:limit]
    return data, size, exceeded


def run_isolated_adapter(
    *,
    policy: SdaAdapterIsolationPolicy,
    arguments: Sequence[str],
    payload: bytes,
) -> SdaAdapterRunResult:
    """Execute one configured adapter with fail-closed local resource bounds.

    The configured executable/arguments are trusted configuration. The payload is
    untrusted source material. shell=False, a minimal environment, an ephemeral
    cwd, closed inherited file descriptors, a separate process session, hard POSIX
    resource limits, and a wall-clock deadline reduce blast radius.

    Network access is deliberately not claimed as isolated in G3A.
    """

    if not isinstance(payload, bytes):
        raise SdaAdapterIsolationError("adapter payload must be bytes")

    if len(payload) > policy.max_input_bytes:
        return SdaAdapterRunResult(
            status=SdaAdapterRunStatus.INPUT_REJECTED,
            return_code=None,
            stdout=b"",
            stderr=b"",
            input_bytes=len(payload),
            stdout_bytes=0,
            stderr_bytes=0,
            environment_keys_exposed=[],
        )

    command = _validate_command(policy, arguments)
    executable = Path(policy.executable_path)
    if not executable.exists() or not executable.is_file():
        raise SdaAdapterIsolationError("configured adapter executable does not exist")
    if not os.access(executable, os.X_OK):
        raise SdaAdapterIsolationError("configured adapter executable is not executable")

    minimal_environment = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    with tempfile.TemporaryDirectory(prefix="ws-sda-adapter-") as temp_name:
        temp_dir = Path(temp_name)
        temp_dir.chmod(0o700)
        stdin_path = temp_dir / "stdin.bin"
        stdout_path = temp_dir / "stdout.bin"
        stderr_path = temp_dir / "stderr.bin"
        stdin_path.write_bytes(payload)
        stdin_path.chmod(0o600)

        timed_out = False
        return_code: int | None = None
        with (
            stdin_path.open("rb") as stdin_handle,
            stdout_path.open("wb") as stdout_handle,
            stderr_path.open("wb") as stderr_handle,
        ):
            try:
                process = subprocess.Popen(
                    command,
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    cwd=temp_dir,
                    env=minimal_environment,
                    shell=False,
                    close_fds=True,
                    start_new_session=True,
                    preexec_fn=lambda: _set_child_limits(policy),
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise SdaAdapterIsolationError(
                    "failed to start adapter under isolation policy"
                ) from exc

            try:
                return_code = process.wait(timeout=policy.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return_code = process.wait(timeout=5)

        stdout, stdout_size, stdout_exceeded = _bounded_read(
            stdout_path, policy.max_output_bytes
        )
        stderr, stderr_size, stderr_exceeded = _bounded_read(
            stderr_path, policy.max_stderr_bytes
        )

        if timed_out:
            status = SdaAdapterRunStatus.TIMED_OUT
        elif (
            stdout_exceeded
            or stderr_exceeded
            or return_code == -signal.SIGXFSZ
            or (
                return_code not in policy.allow_exit_codes
                and (
                    stdout_size >= policy.max_output_bytes
                    or stderr_size >= policy.max_stderr_bytes
                )
            )
        ):
            # Some runtimes turn RLIMIT_FSIZE into an application-level write/flush
            # failure rather than surfacing SIGXFSZ directly. A non-allowed exit
            # with a capture file pinned at its configured bound is conservatively
            # classified as an output-limit violation.
            status = SdaAdapterRunStatus.OUTPUT_LIMIT_EXCEEDED
        elif return_code not in policy.allow_exit_codes:
            status = SdaAdapterRunStatus.PROCESS_FAILED
        else:
            status = SdaAdapterRunStatus.SUCCEEDED

        return SdaAdapterRunResult(
            status=status,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            input_bytes=len(payload),
            stdout_bytes=stdout_size,
            stderr_bytes=stderr_size,
            environment_keys_exposed=sorted(minimal_environment),
        )
