"""Feature engineering: turn a payment + customer history into ~20 signals.

Every signal is deterministic, cheap to compute and explainable.  The same
function is used for (a) the live payment under evaluation and (b) each
historical row used to train the anomaly model — so training and inference
can never drift apart.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from SRC.MODELS import CustomerProfile, PaymentRequest, Transaction, haversine_km

# Ordered numeric vector fed to the Isolation Forest (kept in sync with
# ``anomaly_vector``).  17 signals -> ~1.5 KB per row, trains in milliseconds.
ANOMALY_FEATURES: List[str] = [
    "log_amount",
    "amount_zscore",
    "hour_sin",
    "hour_cos",
    "is_new_payee",
    "payee_history_count",
    "velocity_1h",
    "velocity_24h",
    "frequency_7d",
    "category_deviation",
    "location_change_km",
    "on_call",
    "call_duration_s",
    "battery_low",
    "channel_link",
    "is_round_amount",
    "device_new",
    "payee_reports",
]


def _debits(history: pd.DataFrame) -> pd.DataFrame:
    """Real spending only: DEBIT rows that are not self-transfers."""
    if history is None or len(history) == 0:
        return pd.DataFrame(columns=["timestamp", "amount", "upi_id", "category", "merchant_label"])
    mask = (history["direction"] == "DEBIT") & (~history["self_transfer"].astype(bool))
    return history[mask]


def extract_features(
    payment: PaymentRequest,
    history: Optional[pd.DataFrame],
    profile: CustomerProfile,
    payee_reports: int = 0,
    now: Optional[Any] = None,
) -> Dict[str, float]:
    """Compute all behavioural signals for one candidate payment."""
    ts = payment.resolved_timestamp(now)
    debits = _debits(history)
    prior = debits[debits["timestamp"] <= ts] if len(debits) else debits

    amounts = prior["amount"].astype(float)
    median_amt = float(amounts.median()) if len(amounts) else 0.0
    mean_amt = float(amounts.mean()) if len(amounts) else 0.0
    std_amt = float(amounts.std(ddof=1)) if len(amounts) > 1 else 0.0

    amount = float(payment.amount)
    amount_zscore = (amount - mean_amt) / std_amt if std_amt > 1e-9 else 0.0
    amount_ratio = amount / median_amt if median_amt > 1e-9 else 0.0

    payee_counts = (
        prior.groupby("upi_id").size().to_dict() if len(prior) else {}
    )
    payee_history_count = int(payee_counts.get(payment.payee_upi, 0)) if payment.payee_upi else 0
    is_new_payee = 1.0 if (payment.new_payee or payee_history_count == 0) else 0.0

    if len(prior):
        times = prior["timestamp"]
        velocity_1h = int((times >= ts - timedelta(hours=1)).sum())
        velocity_24h = int((times >= ts - timedelta(hours=24)).sum())
        frequency_7d = int((times >= ts - timedelta(days=7)).sum())
    else:
        velocity_1h = velocity_24h = frequency_7d = 0

    category = (payment.purpose_category or "OTHER").upper()
    cat_prior = prior[prior["category"] == category] if len(prior) else prior
    if len(cat_prior):
        cat_30d = cat_prior[cat_prior["timestamp"] >= ts - timedelta(days=30)]
        base = float(cat_30d["amount"].mean()) if len(cat_30d) else float(cat_prior["amount"].mean())
    else:
        base = 0.0
    category_deviation = amount / base if base > 1e-9 else 0.0

    if payment.lat is not None and payment.lon is not None:
        location_change_km = haversine_km(payment.lat, payment.lon, profile.usual_lat, profile.usual_lon)
    else:
        location_change_km = 0.0
    is_new_location = 1.0 if location_change_km > 50.0 else 0.0

    hour = ts.hour
    is_night = 1.0 if (hour >= 22 or hour < 6) else 0.0
    on_call = 1.0 if payment.on_call else 0.0
    battery_low = 1.0 if int(payment.battery_pct) <= 20 else 0.0
    channel_link = 1.0 if payment.channel == "LINK" else 0.0
    is_round_amount = 1.0 if (amount >= 1000 and amount % 1000 == 0) else 0.0
    device_new = 0.0 if (not payment.device_id or payment.device_id in profile.known_devices) else 1.0
    payee_rep_scaled = min(float(payee_reports), 5.0) / 5.0

    features: Dict[str, float] = {
        # raw / context
        "amount": amount,
        "hour": float(hour),
        "is_night": is_night,
        "category": 0.0,  # placeholder (non numeric; excluded from vector)
        # relative-to-history
        "amount_zscore": float(amount_zscore),
        "amount_ratio": float(amount_ratio),
        "amount_above_median": 1.0 if amount_ratio > 3 else 0.0,
        "category_deviation": float(category_deviation),
        # recipient
        "is_new_payee": is_new_payee,
        "payee_history_count": float(payee_history_count),
        "payee_reports": payee_rep_scaled,
        # velocity / frequency
        "velocity_1h": float(velocity_1h),
        "velocity_24h": float(velocity_24h),
        "frequency_7d": float(frequency_7d),
        # context
        "location_change_km": float(location_change_km),
        "is_new_location": is_new_location,
        "on_call": on_call,
        "call_duration_s": float(max(0, int(payment.call_duration_s or 0))),
        "battery_low": battery_low,
        "channel_link": channel_link,
        "is_round_amount": is_round_amount,
        "device_new": device_new,
        "log_amount": float(np.log1p(max(amount, 0.0))),
        "hour_sin": float(np.sin(2 * np.pi * hour / 24.0)),
        "hour_cos": float(np.cos(2 * np.pi * hour / 24.0)),
        # history depth (for confidence labels)
        "history_rows": float(len(prior)),
    }
    return features


def anomaly_vector(features: Dict[str, float]) -> List[float]:
    """Project a feature dict onto the fixed anomaly-model vector."""
    return [float(features.get(name, 0.0)) for name in ANOMALY_FEATURES]


def features_for_history_row(
    row: Transaction,
    prior_rows: pd.DataFrame,
    profile: CustomerProfile,
) -> Dict[str, float]:
    """Recompute features for a historical row (used to train the model)."""
    payment = PaymentRequest(
        amount=float(row.amount),
        method="UPI",
        payee_name=row.merchant_label,
        payee_upi=row.upi_id,
        purpose_category=row.category,
        timestamp=row.timestamp,
        lat=profile.usual_lat,
        lon=profile.usual_lon,
        on_call=False,
        channel="P2P",
        new_payee=False,
        device_id=profile.known_devices[0] if profile.known_devices else "",
        battery_pct=85,
    )
    return extract_features(payment, prior_rows, profile)


def history_matrix(history: Optional[pd.DataFrame], profile: CustomerProfile) -> np.ndarray:
    """Feature matrix of the customer's own history (training data)."""
    if history is None or len(history) == 0:
        return np.zeros((0, len(ANOMALY_FEATURES)))
    debits = _debits(history).sort_values("timestamp").reset_index(drop=True)
    rows: List[List[float]] = []
    for idx in range(len(debits)):
        row = debits.iloc[idx]
        prior = debits.iloc[:idx]
        feat = features_for_history_row(row, prior, profile)
        rows.append(anomaly_vector(feat))
    return np.asarray(rows, dtype=float)
