"""Evaluation metrics, threshold sweep and cost model.

Fraud data is imbalanced and errors are asymmetric, so accuracy is close to
meaningless: we report precision / recall / F1 / FPR / MCC, plus a cost model
``Loss = C_FN * FN + C_FP * FP + lambda * friction`` (Elkan 2001; Bahnsen et
al. 2015) and an F1-optimal threshold sweep.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


def classification_metrics(
    y_true: Sequence[int], y_pred: Sequence[int]
) -> Dict[str, float]:
    """Precision / recall / F1 / FPR / accuracy / MCC for the positive class."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    accuracy = (tp + tn) / max(tp + fp + tn + fn, 1)
    denom = math.sqrt(float(tp + fp) * float(tp + fn) * float(tn + fp) * float(tn + fn))
    mcc = ((tp * tn - fp * fn) / denom) if denom > 0 else 0.0
    return {
        "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
        "accuracy": round(accuracy, 4),
        "mcc": round(mcc, 4),
    }


def latency_stats(values: Sequence[float]) -> Dict[str, float]:
    if not len(values):
        return {"mean_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    arr = np.asarray(values, dtype=float)
    return {
        "mean_ms": round(float(arr.mean()), 2),
        "median_ms": round(float(np.median(arr)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "max_ms": round(float(arr.max()), 2),
    }


def threshold_sweep(
    scores: Sequence[float], y_true: Sequence[int], thresholds: Optional[List[float]] = None
) -> List[Dict[str, float]]:
    """F1 / precision / recall at each candidate decision threshold."""
    scores = np.asarray(scores, dtype=float)
    y_true = np.asarray(y_true, dtype=int)
    thresholds = thresholds or list(range(20, 96, 5))
    rows: List[Dict[str, float]] = []
    for threshold in thresholds:
        pred = (scores >= threshold).astype(int)
        metrics = classification_metrics(y_true, pred)
        rows.append(
            {
                "threshold": float(threshold),
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "fpr": metrics["fpr"],
            }
        )
    return rows


def best_f1_threshold(sweep: List[Dict[str, float]]) -> Dict[str, float]:
    if not sweep:
        return {"threshold": 0.0, "f1": 0.0}
    return max(sweep, key=lambda row: row["f1"])


def expected_loss(
    metrics: Dict[str, float],
    cost_false_negative: float,
    cost_false_positive: float,
    friction_per_interruption: float,
    interruption_rate: float,
    n_total: int,
) -> float:
    """Cost-sensitive loss (manual page 13)."""
    loss = (
        cost_false_negative * metrics.get("FN", 0)
        + cost_false_positive * metrics.get("FP", 0)
        + friction_per_interruption * interruption_rate * n_total
    )
    return round(loss, 2)


def family_breakdown(
    families: Sequence[str], scores: Sequence[float], y_true: Sequence[int], threshold: float
) -> List[Dict[str, Any]]:
    """Recall per scam family - where the engine is strong and where it leaks.

    Families with no positive labels (normal / tricky-benign) report their
    false-alarm count instead, because precision/recall are undefined there.
    """
    out: List[Dict[str, Any]] = []
    for family in sorted(set(families)):
        idx = [i for i, f in enumerate(families) if f == family]
        y = [int(y_true[i]) for i in idx]
        s = [float(scores[i]) for i in idx]
        pred = [1 if v >= threshold else 0 for v in s]
        metrics = classification_metrics(y, pred)
        out.append(
            {
                "family": family,
                "n": len(idx),
                "positives": sum(y),
                "recall": metrics["recall"],
                "precision": metrics["precision"],
                "fpr": metrics["fpr"],
                "fp": metrics["FP"],
            }
        )
    return out


def evaluate_labelled(
    rows: List[Dict[str, Any]],
    evaluator: Callable[[Dict[str, Any]], Dict[str, float]],
    threshold: float,
    ask_above: float,
) -> Dict[str, Any]:
    """Run ``evaluator`` over labelled rows and summarise everything.

    ``evaluator`` receives one row dict and must return at least
    ``{"score": float, "latency_ms": float}``.
    """
    scores: List[float] = []
    labels: List[int] = []
    latencies: List[float] = []
    interruptions = 0
    for row in rows:
        result = evaluator(row)
        score = float(result["score"])
        scores.append(score)
        labels.append(int(row["label"]))
        latencies.append(float(result.get("latency_ms", 0.0)))
        if score >= ask_above:
            interruptions += 1
    metrics = classification_metrics(labels, [1 if s >= threshold else 0 for s in scores])
    metrics["interruption_rate"] = round(interruptions / max(len(rows), 1), 4)
    metrics["latency"] = latency_stats(latencies)
    metrics["n"] = len(rows)
    return {
        "overall": metrics,
        "scores": scores,
        "labels": labels,
        "families": [row.get("family", "normal") for row in rows],
    }
