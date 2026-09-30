"""Isolation Forest behavioural-anomaly layer.

The model learns *this customer's* normal payment behaviour from their own
history (unsupervised, no labels needed) and scores how far a new payment
deviates.

Score mapping (documented in RESOURCES/FORMULAS.MD):

    percentile = share of the customer's own history that is LESS unusual
    score      = 100 * clamp((percentile - 0.75) / 0.25)

so payments at or below the customer's 75th-percentile behaviour score ~0 and
only genuine tail outliers (top quartile, and especially the ~5% the model
treats as contamination) approach 100.  The raw ``decision_function`` scale is
never shown because it is not interpretable.

Compute-cost notes (the prototype must stay feasible):
  * the trained model + score vector are cached per (history, config) key,
  * default 120 trees on ~300 rows trains in well under 100 ms,
  * repeated evaluations of the same history reuse the cache (~1 ms each).
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from SRC.FEATURES import anomaly_vector, history_matrix

_MIN_HISTORY_FOR_MODEL = 20
_CACHE_LIMIT = 8

# key -> (model, sorted_scores, n_rows)
_MODEL_CACHE: "OrderedDict[str, Tuple[Any, np.ndarray, int]]" = OrderedDict()


def _history_key(history: Optional[pd.DataFrame], profile_id: str) -> str:
    """Deterministic cache key for a history snapshot."""
    if history is None or len(history) == 0:
        return f"{profile_id}:empty"
    debits = history[(history["direction"] == "DEBIT") & (~history["self_transfer"].astype(bool))]
    if len(debits) == 0:
        return f"{profile_id}:empty"
    total = float(debits["amount"].sum())
    return f"{profile_id}:{len(debits)}:{total:.2f}:{str(debits['timestamp'].max())}"


def _get_model(
    history: Optional[pd.DataFrame],
    profile: Any,
    cfg: Dict[str, Any],
) -> Optional[Tuple[Any, np.ndarray, int]]:
    """Train (and memoise) the Isolation Forest for this history + config."""
    risk = cfg["risk"]
    key = _history_key(history, profile.customer_id)
    if key.endswith(":empty"):
        return None
    n_estimators = int(risk["anomaly_n_estimators"])
    contamination = float(risk["anomaly_contamination"])
    cache_key = f"{key}|{n_estimators}|{contamination}"
    cached = _MODEL_CACHE.get(cache_key)
    if cached is not None:
        _MODEL_CACHE.move_to_end(cache_key)
        return cached
    matrix = history_matrix(history, profile)
    if matrix.shape[0] < _MIN_HISTORY_FOR_MODEL:
        return None
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=42,  # determinism: same history -> same model
        n_jobs=1,
    )
    model.fit(matrix)
    sorted_scores = np.sort(-model.decision_function(matrix))
    entry = (model, sorted_scores, int(matrix.shape[0]))
    _MODEL_CACHE[cache_key] = entry
    if len(_MODEL_CACHE) > _CACHE_LIMIT:
        _MODEL_CACHE.popitem(last=False)
    return entry


def anomaly_score_with_profile(
    features: Dict[str, float],
    history: Optional[pd.DataFrame],
    profile: Any,
    cfg: Dict[str, Any],
) -> Tuple[float, str, Dict[str, Any]]:
    """Return ``(score_0_100, confidence, details)`` for one payment."""
    entry = _get_model(history, profile, cfg)
    if entry is None:
        rows = 0 if history is None else len(history)
        return 50.0, "LOW", {
            "note": f"no usable history yet ({rows} rows) — anomaly layer neutral",
            "history_rows": rows,
        }
    model, sorted_scores, n_rows = entry
    vector = np.array([anomaly_vector(features)], dtype=float)
    raw = float(-model.decision_function(vector)[0])
    position = float(np.searchsorted(sorted_scores, raw, side="right"))
    percentile = position / max(len(sorted_scores), 1)
    score = round(100.0 * min(max((percentile - 0.75) / 0.25, 0.0), 1.0), 1)
    confidence = "HIGH" if n_rows >= 60 else "MEDIUM"
    details = {
        "raw_decision": round(raw, 4),
        "history_rows": n_rows,
        "percentile": round(percentile, 3),
        "n_estimators": int(cfg["risk"]["anomaly_n_estimators"]),
        "contamination": float(cfg["risk"]["anomaly_contamination"]),
        "note": "tail-scaled percentile among this customer's own history",
    }
    return score, confidence, details


def clear_cache() -> None:
    _MODEL_CACHE.clear()
