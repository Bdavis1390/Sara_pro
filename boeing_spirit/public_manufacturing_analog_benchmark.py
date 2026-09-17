#!/usr/bin/env python3
"""Independent public manufacturing-analog benchmark for WS-BOEING-01.

This benchmark downloads two CC BY 4.0 UCI manufacturing datasets and runs
fully deterministic, standard-library-only cross-validation:

* Steel Plates Faults: 7-class surface-defect pattern-recognition analog.
* SECOM: imbalanced semiconductor process pass/fail yield analog with missing data.

The results test ingestion, preprocessing, class-imbalance accounting, confusion
matrices and repeatable measurement. They are NOT Boeing/Spirit validation and
must never be promoted to a partner/production evidence class.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import statistics
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

USER_AGENT = "Worldshepherd-Public-Manufacturing-Analog/1.0"
STEEL_URL = "https://archive.ics.uci.edu/static/public/198/steel%2Bplates%2Bfaults.zip"
SECOM_URL = "https://archive.ics.uci.edu/static/public/179/secom.zip"


def fetch(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if getattr(r, "status", 200) != 200:
            raise RuntimeError(f"unexpected HTTP status for {url}: {getattr(r, 'status', None)}")
    if not body.startswith(b"PK"):
        raise RuntimeError(f"expected ZIP content from {url}")
    return body


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def zip_member_bytes(blob: bytes, wanted: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = zf.namelist()
        matches = [name for name in names if name.lower().endswith(wanted.lower())]
        if len(matches) != 1:
            raise RuntimeError(f"expected one {wanted!r} member, found {matches!r} in {names!r}")
        return zf.read(matches[0])


def stratified_folds(labels: list[int], k: int = 5) -> list[list[int]]:
    buckets: dict[int, list[int]] = defaultdict(list)
    for i, label in enumerate(labels):
        buckets[label].append(i)
    folds = [[] for _ in range(k)]
    for label in sorted(buckets):
        for j, idx in enumerate(buckets[label]):
            folds[j % k].append(idx)
    for fold in folds:
        fold.sort()
    return folds


def confusion_metrics(y_true: list[int], y_pred: list[int], labels: list[int]) -> dict:
    matrix = {str(a): {str(b): 0 for b in labels} for a in labels}
    for a, b in zip(y_true, y_pred):
        matrix[str(a)][str(b)] += 1
    recalls = {}
    precisions = {}
    for label in labels:
        tp = matrix[str(label)][str(label)]
        actual = sum(matrix[str(label)].values())
        predicted = sum(matrix[str(a)][str(label)] for a in labels)
        recalls[str(label)] = tp / actual if actual else 0.0
        precisions[str(label)] = tp / predicted if predicted else 0.0
    accuracy = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    return {
        "accuracy": round(accuracy, 6),
        "macro_recall": round(statistics.fmean(recalls.values()), 6),
        "macro_precision": round(statistics.fmean(precisions.values()), 6),
        "per_class_recall": {k: round(v, 6) for k, v in recalls.items()},
        "per_class_precision": {k: round(v, 6) for k, v in precisions.items()},
        "confusion_matrix": matrix,
    }


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 1.0
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, 1.0
    variance = statistics.fmean((x - mean) ** 2 for x in values)
    std = math.sqrt(variance)
    return mean, std if std > 1e-12 else 1.0


def benchmark_steel(blob: bytes) -> dict:
    raw = zip_member_bytes(blob, "Faults.NNA").decode("utf-8", errors="strict")
    rows = [[float(x) for x in line.split()] for line in raw.splitlines() if line.strip()]
    if len(rows) != 1941:
        raise RuntimeError(f"Steel Plates instance count changed: {len(rows)}")
    if any(len(row) != 34 for row in rows):
        raise RuntimeError("Steel Plates row width is not 34 (27 features + 7 labels)")
    X = [row[:27] for row in rows]
    y = [max(range(7), key=lambda j: row[27 + j]) for row in rows]
    if any(sum(1 for value in row[27:] if value == 1.0) != 1 for row in rows):
        raise RuntimeError("Steel Plates target is not one-hot as expected")

    folds = stratified_folds(y, 5)
    all_true: list[int] = []
    all_pred: list[int] = []
    for test_idx in folds:
        test_set = set(test_idx)
        train_idx = [i for i in range(len(X)) if i not in test_set]
        means = []
        stds = []
        for j in range(27):
            m, s = mean_std([X[i][j] for i in train_idx])
            means.append(m)
            stds.append(s)
        centroids: dict[int, list[float]] = {}
        for label in range(7):
            members = [i for i in train_idx if y[i] == label]
            centroids[label] = [statistics.fmean((X[i][j] - means[j]) / stds[j] for i in members) for j in range(27)]
        for i in test_idx:
            z = [(X[i][j] - means[j]) / stds[j] for j in range(27)]
            pred = min(range(7), key=lambda label: sum((a - b) ** 2 for a, b in zip(z, centroids[label])))
            all_true.append(y[i])
            all_pred.append(pred)

    metrics = confusion_metrics(all_true, all_pred, list(range(7)))
    return {
        "dataset": "UCI Steel Plates Faults",
        "uci_id": 198,
        "doi": "10.24432/C5J88N",
        "license": "CC BY 4.0",
        "instances": len(rows),
        "features": 27,
        "classes": 7,
        "evaluation": "deterministic stratified 5-fold nearest-centroid after train-fold z-score normalization",
        "metrics": metrics,
        "dataset_zip_sha256": sha256_bytes(blob),
        "source_url": STEEL_URL,
    }


def parse_float(token: str) -> float | None:
    return None if token.lower() == "nan" else float(token)


def benchmark_secom(blob: bytes) -> dict:
    data_raw = zip_member_bytes(blob, "secom.data").decode("utf-8", errors="strict")
    labels_raw = zip_member_bytes(blob, "secom_labels.data").decode("utf-8", errors="strict")
    Xraw = [[parse_float(x) for x in line.split()] for line in data_raw.splitlines() if line.strip()]
    y = [int(line.split()[0]) for line in labels_raw.splitlines() if line.strip()]
    if len(Xraw) != 1567 or len(y) != 1567:
        raise RuntimeError(f"SECOM instance count changed: X={len(Xraw)} y={len(y)}")
    width = len(Xraw[0])
    if width < 500 or any(len(row) != width for row in Xraw):
        raise RuntimeError(f"unexpected SECOM feature width: {width}")
    if set(y) != {-1, 1}:
        raise RuntimeError(f"unexpected SECOM labels: {sorted(set(y))}")

    folds = stratified_folds(y, 5)
    all_true: list[int] = []
    all_pred: list[int] = []
    selected_counts: list[int] = []

    for test_idx in folds:
        test_set = set(test_idx)
        train_idx = [i for i in range(len(Xraw)) if i not in test_set]
        feature_stats = []
        for j in range(width):
            present = [Xraw[i][j] for i in train_idx if Xraw[i][j] is not None]
            missing_fraction = 1.0 - len(present) / len(train_idx)
            if not present or missing_fraction > 0.50:
                continue
            mean, std = mean_std([float(v) for v in present])
            if std <= 1e-12:
                continue
            pass_vals = [float(Xraw[i][j]) for i in train_idx if y[i] == -1 and Xraw[i][j] is not None]
            fail_vals = [float(Xraw[i][j]) for i in train_idx if y[i] == 1 and Xraw[i][j] is not None]
            if not pass_vals or not fail_vals:
                continue
            effect = abs(statistics.fmean(fail_vals) - statistics.fmean(pass_vals)) / std
            feature_stats.append((effect, j, mean, std))
        feature_stats.sort(key=lambda row: (-row[0], row[1]))
        selected = feature_stats[:40]
        if len(selected) < 20:
            raise RuntimeError(f"too few usable SECOM features: {len(selected)}")
        selected_counts.append(len(selected))

        centroids: dict[int, list[float]] = {}
        for label in (-1, 1):
            members = [i for i in train_idx if y[i] == label]
            coords = []
            for _, j, mean, std in selected:
                vals = [float(Xraw[i][j]) if Xraw[i][j] is not None else mean for i in members]
                coords.append(statistics.fmean((v - mean) / std for v in vals))
            centroids[label] = coords

        for i in test_idx:
            z = []
            for _, j, mean, std in selected:
                value = float(Xraw[i][j]) if Xraw[i][j] is not None else mean
                z.append((value - mean) / std)
            d_pass = sum((a - b) ** 2 for a, b in zip(z, centroids[-1]))
            d_fail = sum((a - b) ** 2 for a, b in zip(z, centroids[1]))
            pred = 1 if d_fail < d_pass else -1
            all_true.append(y[i])
            all_pred.append(pred)

    metrics = confusion_metrics(all_true, all_pred, [-1, 1])
    pass_recall = metrics["per_class_recall"]["-1"]
    fail_recall = metrics["per_class_recall"]["1"]
    metrics["balanced_accuracy"] = round((pass_recall + fail_recall) / 2.0, 6)
    metrics["balanced_error_rate"] = round(1.0 - metrics["balanced_accuracy"], 6)
    metrics["false_negative_rate_fail_class"] = round(1.0 - fail_recall, 6)
    metrics["false_positive_rate_fail_class"] = round(1.0 - pass_recall, 6)

    return {
        "dataset": "UCI SECOM",
        "uci_id": 179,
        "doi": "10.24432/C54305",
        "license": "CC BY 4.0",
        "instances": len(Xraw),
        "features_observed": width,
        "fail_examples": sum(1 for label in y if label == 1),
        "pass_examples": sum(1 for label in y if label == -1),
        "evaluation": "deterministic stratified 5-fold; train-fold mean imputation; remove >50% missing/constant features; top-40 train-fold standardized class-mean effect; nearest centroid",
        "selected_feature_count_by_fold": selected_counts,
        "metrics": metrics,
        "dataset_zip_sha256": sha256_bytes(blob),
        "source_url": SECOM_URL,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="boeing_spirit/evidence/public-manufacturing-analog-report.json")
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()

    steel_blob = fetch(STEEL_URL, args.timeout)
    secom_blob = fetch(SECOM_URL, args.timeout)
    steel = benchmark_steel(steel_blob)
    secom = benchmark_secom(secom_blob)

    report = {
        "schema": "WS-BOEING-SPIRIT-PUBLIC-MANUFACTURING-ANALOG-V1",
        "as_of": "2026-09-03",
        "evidence_class": "INDEPENDENT PUBLIC MANUFACTURING ANALOG BENCHMARK",
        "result": "PASS",
        "datasets": [steel, secom],
        "minimum_sanity_checks": {
            "steel_macro_recall_nonzero": steel["metrics"]["macro_recall"] > 0.0,
            "secom_fail_recall_nonzero": secom["metrics"]["per_class_recall"]["1"] > 0.0,
            "secom_pass_recall_nonzero": secom["metrics"]["per_class_recall"]["-1"] > 0.0,
            "all_metrics_bounded": all(0.0 <= x <= 1.0 for x in [steel["metrics"]["accuracy"], steel["metrics"]["macro_recall"], secom["metrics"]["balanced_accuracy"]]),
        },
        "contact_gate_effect": "NONE",
        "claims_boundary": (
            "This is independent public manufacturing-analog evidence, not Boeing/Spirit data or partner validation. "
            "It establishes only that the Worldshepherd measurement pipeline can reproducibly ingest public manufacturing data, "
            "handle multiclass defects, missing values and class imbalance, and report confusion/error metrics. It does not establish "
            "Boeing/Spirit root cause, APQP/PPAP acceptance, supplier approval, production effectiveness, defect reduction, savings, "
            "airworthiness, regulatory/contractual compliance, certification, adoption, or a statistical probability of remediation."
        ),
    }
    if not all(report["minimum_sanity_checks"].values()):
        report["result"] = "FAIL"
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "steel_accuracy": steel["metrics"]["accuracy"],
        "steel_macro_recall": steel["metrics"]["macro_recall"],
        "secom_balanced_accuracy": secom["metrics"]["balanced_accuracy"],
        "secom_fail_recall": secom["metrics"]["per_class_recall"]["1"],
        "contact_gate_effect": report["contact_gate_effect"],
    }, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
