"""WorldShepherd claim evidence gate v0.3: structural validation, never proof.

Standard library only. Claims are always bounded by evidence type and human review.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

KINDS = {'control', 'simulation', 'software', 'formal_proof', 'lab_measurement'}
OUTCOMES = {'PASS', 'FAIL', 'INCONCLUSIVE'}
REQUIRED = ('claim_id', 'claim_type', 'statement', 'null_hypothesis',
            'observable', 'comparison', 'falsification_rule',
            'required_controls', 'limitations')
STATUS = {
    'physical': {'HYPOTHESIS', 'SIMULATED ONLY', 'PHYSICAL DATA RECORDED'},
    'software': {'HYPOTHESIS', 'INTERNAL SOFTWARE RESULTS'},
    'mathematical': {'HYPOTHESIS', 'FORMAL ARTIFACT RECORDED'},
}
STATUS_KIND = {'SIMULATED ONLY': 'simulation',
               'PHYSICAL DATA RECORDED': 'lab_measurement',
               'INTERNAL SOFTWARE RESULTS': 'software',
               'FORMAL ARTIFACT RECORDED': 'formal_proof'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value) is not None


def file_sha(root, rel):
    """Hash a regular file with relative-path and symlink checks.

    This is NOT a hostile-filesystem/TOCTOU defense; use immutable snapshots
    for adversarial data and authenticated ECHO custody for trusted releases.
    """
    if not isinstance(rel, str) or not rel or '\\' in rel:
        raise ValueError('invalid artifact path')
    item = Path(rel)
    if item.is_absolute() or '..' in item.parts or '.' in rel.split('/'):
        raise ValueError('absolute or traversing artifact path')
    base = Path(root).resolve(strict=True)
    path = base
    for part in item.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('symlink not permitted')
    if not path.resolve(strict=True).is_relative_to(base) or not path.is_file():
        raise ValueError('artifact outside root or not a file')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def audit_package(pkg, prereg, root, pinned_sha256):
    """Verify an evidence envelope, not the physical or mathematical truth."""
    if not isinstance(pkg, dict) or not isinstance(prereg, dict):
        raise ValueError('package and prereg must be JSON objects')
    errors, warnings = [], []
    claim_hash = digest(canonical(prereg))
    if not valid_sha(pinned_sha256) or claim_hash != pinned_sha256.lower():
        errors.append('PREREG_PIN_MISMATCH')
    for key in REQUIRED:
        if prereg.get(key) in (None, '', []):
            errors.append(f'PREREG_FIELD_MISSING:{key}')
    claim_type = prereg.get('claim_type')
    if not isinstance(claim_type, str) or claim_type not in STATUS:
        errors.append('UNKNOWN_CLAIM_TYPE')
    if prereg.get('claim_id') != pkg.get('claim_id'):
        errors.append('CLAIM_ID_MISMATCH')
    controls = prereg.get('required_controls')
    if not isinstance(controls, list) or any(not isinstance(c, str) or not c for c in controls):
        errors.append('MALFORMED_REQUIRED_CONTROLS')
        controls = []
    if len(controls) != len(set(controls)):
        errors.append('DUPLICATE_REQUIRED_CONTROL')
    runs = pkg.get('runs')
    if not isinstance(runs, list) or not runs:
        errors.append('NO_RUNS')
        runs = []
    counts = {k: 0 for k in sorted(OUTCOMES)}
    run_ids = set()
    valid_kinds = set()
    good_controls = set()
    failed_controls = set()
    verified_artifacts = 0
    verified_run_configs = 0
    for idx, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f'INVALID_RUN:{idx}')
            continue
        rid = run.get('id')
        if not isinstance(rid, str) or not rid or rid in run_ids:
            errors.append(f'DUPLICATE_OR_INVALID_RUN_ID:{rid}')
        if isinstance(rid, str):
            run_ids.add(rid)
        kind, outcome = run.get('kind'), run.get('outcome')
        if not isinstance(kind, str) or kind not in KINDS:
            errors.append(f'INVALID_KIND:{rid}')
        if not isinstance(outcome, str) or outcome not in OUTCOMES:
            errors.append(f'INVALID_OUTCOME:{rid}')
        else:
            counts[outcome] += 1
        if not valid_sha(run.get('config_sha256')):
            errors.append(f'CONFIG_DIGEST_MISSING:{rid}')
        config_artifact = run.get('config_artifact')
        valid_config = False
        if not isinstance(config_artifact, dict) or set(config_artifact) != {'path', 'sha256'}:
            errors.append(f'CONFIG_DESCRIPTOR_MALFORMED:{rid}')
        else:
            try:
                actual_config = file_sha(root, config_artifact['path'])
                if (not valid_sha(config_artifact['sha256'])
                        or actual_config != config_artifact['sha256'].lower()
                        or not valid_sha(run.get('config_sha256'))
                        or actual_config != run['config_sha256'].lower()):
                    errors.append(f'CONFIG_HASH_MISMATCH:{rid}')
                else:
                    valid_config = True
                    verified_run_configs += 1
            except (OSError, ValueError, TypeError, KeyError) as ex:
                errors.append(f'CONFIG_UNAVAILABLE:{rid}:{ex}')
        artifact = run.get('artifact')
        valid_artifact = False
        if not isinstance(artifact, dict) or set(artifact) != {'path', 'sha256'}:
            errors.append(f'ARTIFACT_DESCRIPTOR_MALFORMED:{rid}')
        else:
            try:
                actual = file_sha(root, artifact['path'])
                if not valid_sha(artifact['sha256']) or actual != artifact['sha256'].lower():
                    errors.append(f'ARTIFACT_HASH_MISMATCH:{rid}')
                else:
                    valid_artifact = True
                    verified_artifacts += 1
            except (OSError, ValueError, TypeError, KeyError) as ex:
                errors.append(f'ARTIFACT_UNAVAILABLE:{rid}:{ex}')
        if valid_artifact and valid_config and isinstance(kind, str) and kind in KINDS:
            valid_kinds.add(kind)
        if kind == 'control' and isinstance(run.get('control'), str):
            if valid_artifact and valid_config and outcome == 'PASS':
                good_controls.add(run['control'])
            else:
                failed_controls.add(run['control'])
    summary = pkg.get('summary')
    if not isinstance(summary, dict) or summary.get('counts') != counts:
        errors.append('SUMMARY_EVENT_RECONCILIATION_FAILED')
    if not isinstance(summary, dict) or summary.get('run_ids') != sorted(run_ids):
        errors.append('SUMMARY_RUN_ID_RECONCILIATION_FAILED')
    for control in controls:
        if control not in good_controls:
            errors.append(f'REQUIRED_CONTROL_NOT_PASSED:{control}')
        if control in failed_controls:
            errors.append(f'REQUIRED_CONTROL_HAS_FAILED_RUN:{control}')
    requested = pkg.get('requested_status', 'HYPOTHESIS')
    permitted_statuses = STATUS.get(claim_type, {'HYPOTHESIS'}) if isinstance(claim_type, str) else {'HYPOTHESIS'}
    if not isinstance(requested, str) or requested not in permitted_statuses:
        errors.append(f'UNSUPPORTED_CLAIM_PROMOTION:{requested}')
    required_kind = STATUS_KIND.get(requested) if isinstance(requested, str) else None
    if required_kind and required_kind not in valid_kinds:
        errors.append(f'REQUESTED_STATUS_HAS_NO_VERIFIED_ARTIFACT:{required_kind}')
    if any(isinstance(r, dict) and r.get('outcome') != 'PASS' for r in runs):
        warnings.append('Negative or inconclusive runs retained for human scientific review')
    if pkg.get('independent_attestation_anchor'):
        warnings.append('An anchor reference is recorded but NOT cryptographically verified')
    else:
        warnings.append('No separately verified independent witness; local integrity only')
    warnings.append('Configuration file bytes match recorded SHA-256, but this does NOT prove those bytes were used by the executable or frozen before the run')
    warnings.append('Structural audit does not prove scientific truth, novelty, calibration, or independent replication')
    return {
        'audit_version': 'WS-CLAIM-GATE-0.3',
        'claim_id': pkg.get('claim_id'),
        'preregistration_sha256': claim_hash,
        'integrity': 'PASS' if not errors else 'BLOCKED',
        'errors': sorted(errors),
        'warnings': sorted(warnings),
        'event_counts': counts,
        'artifacts_verified_sha256': verified_artifacts,
        'run_configurations_verified_sha256': verified_run_configs,
        'requested_status': requested,
        'claim_automatically_proven': False,
        'requires_human_review': True,
        'external_independence_verified': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prereg', 'package', 'root', 'pinned-prereg-sha256', 'out'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    prereg = json.loads(Path(args.prereg).read_text(encoding='utf-8'))
    pkg = json.loads(Path(args.package).read_text(encoding='utf-8'))
    report = audit_package(pkg, prereg, args.root, args.pinned_prereg_sha256)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'integrity': report['integrity'], 'errors': report['errors']}))
    raise SystemExit(0 if report['integrity'] == 'PASS' else 2)


if __name__ == '__main__':
    main()
