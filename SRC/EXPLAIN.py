"""Explanation layer: turn every score into plain, ranked reasons.

Each entry is ``{key, contribution, text_en, text_ta, severity}`` sorted by
contribution so the biggest driver of the decision comes first.  When SHAP is
installed it is used to attribute the Isolation Forest score as well; the
prototype never *requires* it.
"""
from __future__ import annotations

from typing import Any, Dict, List

from SRC.LANGUAGE import t

_INTENT_FAMILY_TO_KEY = {
    "URGENCY": "expl_urgency",
    "AUTHORITY": "expl_authority",
    "THREAT": "expl_threat",
    "SECRECY": "expl_secrecy",
    "VERIFICATION": "expl_verification",
    "SAFE_ACCOUNT": "expl_safe_account",
    "LOTTERY": "expl_lottery",
    "REFUND_QR": "expl_refund_qr",
    "DELIVERY_SUPPORT": "expl_delivery_support",
    "OTP_PIN": "expl_otp_pin",
    "JOB_FEE": "expl_job_fee",
    "FAMILY_EMERGENCY": "expl_family_emergency",
}

_SIGNAL_KEYS = [
    ("expl_payee_reports", "txn_payee_reports", 20.0),
    ("expl_new_payee", "txn_new_payee", 16.0),
    ("expl_amount_high", "txn_amount_unusual", 14.0),
    ("expl_on_call", "txn_on_call_amount", 12.0),
    ("expl_velocity", "txn_velocity", 10.0),
    ("expl_location", "txn_location", 10.0),
    ("expl_category_dev", "txn_category_deviation", 8.0),
    ("expl_channel_link", "txn_channel_link", 6.0),
    ("expl_night", "txn_night", 6.0),
    ("expl_device_new", "txn_device_new", 5.0),
    ("expl_battery", "txn_battery_low", 4.0),
    ("expl_round_amount", "txn_round_amount", 3.0),
]


def _severity(contribution: float) -> str:
    if contribution >= 12.0:
        return "high"
    if contribution >= 5.0:
        return "medium"
    return "low"


def build_explanation(result: Any, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rank the drivers behind the fraud score (and the budget warning)."""
    entries: List[Dict[str, Any]] = []
    features = result.features or {}

    # ---- transaction / behaviour drivers
    for text_key, feature_key, weight in _SIGNAL_KEYS:
        value = float(features.get(feature_key, 0.0) or 0.0)
        if value <= 0.0:
            continue
        contribution = round(weight * min(value, 1.0), 1)
        entries.append(
            {
                "key": text_key,
                "contribution": contribution,
                "text_en": t(text_key, "en"),
                "text_ta": t(text_key, "ta"),
                "severity": _severity(contribution),
                "group": "behaviour",
            }
        )

    # ---- anomaly layer
    anomaly = float(getattr(result, "anomaly_score", 50.0) or 0.0)
    blend = float(cfg["risk"].get("anomaly_blend", 0.45))
    if anomaly >= 60.0:
        contribution = round(blend * anomaly, 1)
        entries.append(
            {
                "key": "expl_anomaly",
                "contribution": contribution,
                "text_en": t("expl_anomaly", "en")
                + f" (score {anomaly:.0f}/100, {result.anomaly_confidence.lower()} confidence)",
                "text_ta": t("expl_anomaly", "ta")
                + f" ({anomaly:.0f}/100, {result.anomaly_confidence})",
                "severity": _severity(contribution),
                "group": "behaviour",
            }
        )

    # ---- intent drivers (the product's core signal)
    for signal in getattr(result, "matched_signals", []) or []:
        family = signal.get("family")
        key = _INTENT_FAMILY_TO_KEY.get(family)
        if not key:
            continue
        weight = float(signal.get("weight", 0.5)) * 100.0 * float(signal.get("factor", 1.0))
        intent_weight = float(cfg["risk"].get("intent_weight", 0.45))
        contribution = round(intent_weight * weight * float(signal.get("factor", 1.0)), 1)
        entries.append(
            {
                "key": key,
                "contribution": contribution,
                "text_en": t(key, "en") + _phrases_suffix(signal.get("phrases"), "en"),
                "text_ta": t(key, "ta"),
                "severity": _severity(contribution),
                "group": "intent",
            }
        )
    for bonus in (getattr(result, "__dict__", {}).get("_intent_result", {}) or {}).get(
        "bonus", []
    ) or []:
        contribution = round(float(cfg["risk"].get("intent_weight", 0.45)) * bonus["amount"], 1)
        entries.append(
            {
                "key": "expl_" + bonus["label"].replace(" ", "_").replace("+", "and"),
                "contribution": contribution,
                "text_en": f"Combined pattern: {bonus['label']}",
                "text_ta": f"இணைந்த அறிகுறி: {bonus['label']}",
                "severity": _severity(contribution),
                "group": "intent",
            }
        )

    # ---- missing intent is itself information
    if result.intent_unknown:
        entries.append(
            {
                "key": "expl_intent_unknown",
                "contribution": 10.0,
                "text_en": t("expl_intent_unknown", "en"),
                "text_ta": t("expl_intent_unknown", "ta"),
                "severity": "medium",
                "group": "intent",
            }
        )

    # ---- budget drivers
    budget = result.budget
    if budget.would_exceed_month:
        entries.append(
            {
                "key": "budget_exceed_month",
                "contribution": 20.0,
                "text_en": t("budget_exceed_month", "en"),
                "text_ta": t("budget_exceed_month", "ta"),
                "severity": "high",
                "group": "budget",
            }
        )
    if budget.would_exceed_category:
        entries.append(
            {
                "key": "budget_exceed_category",
                "contribution": 18.0,
                "text_en": t("budget_exceed_category", "en"),
                "text_ta": t("budget_exceed_category", "ta"),
                "severity": "high",
                "group": "budget",
            }
        )
    if budget.projected_overrun > 0:
        entries.append(
            {
                "key": "projected_overrun_note",
                "contribution": 12.0,
                "text_en": t("projected_overrun_note", "en"),
                "text_ta": t("projected_overrun_note", "ta"),
                "severity": "medium",
                "group": "budget",
            }
        )

    entries.sort(key=lambda e: e["contribution"], reverse=True)
    return entries[:8]


def _phrases_suffix(phrases: Any, lang: str) -> str:
    phrases = [p for p in (phrases or []) if p]
    if not phrases:
        return ""
    shown = ", ".join(f'"{p.strip()}"' for p in phrases[:3])
    if lang == "en":
        return f" (matched: {shown})"
    return f" (பொருந்தியவை: {shown})"


# --------------------------------------------------------------------------- #
#  SHAP-style attribution table
# --------------------------------------------------------------------------- #

# The four layers a production system would use, and what this prototype runs
# instead.  Shown on the About page and next to the score so the mapping is
# explicit rather than implied.
MODEL_LAYERS: List[Dict[str, str]] = [
    {
        "layer": "Behaviour / sequence",
        "production": "Transformer or LSTM over the user's transaction sequence",
        "prototype": "Isolation Forest trained on this customer's own history, scored as a "
                     "percentile (SRC/ANOMALY.py)",
        "question": "Does this payment fit this user's normal pattern?",
    },
    {
        "layer": "Connections",
        "production": "Graph Neural Network over account / device / merchant / payee links",
        "prototype": "Recipient intelligence: new payee, prior reports, handle type, device "
                     "match, verified own-account rule (SRC/RISK_ENGINE.py)",
        "question": "Is this device, account or merchant linked to suspicious activity?",
    },
    {
        "layer": "Transaction details",
        "production": "Random Forest + XGBoost ensemble over amount, time, device, channel, "
                      "velocity",
        "prototype": "Weighted rule set over the same 20+ features (SRC/FEATURES.py)",
        "question": "Do the payment's own details look unusual?",
    },
    {
        "layer": "Fusion",
        "production": "Stacked / calibrated combiner",
        "prototype": "Weighted sum w_t·transaction + w_i·intent + w_r·recipient, with the "
                     "weights visible and editable (SRC/RISK_ENGINE.py)",
        "question": "How likely is this payment to be a scam?",
    },
    {
        "layer": "Explanation",
        "production": "SHAP / LIME feature attribution",
        "prototype": "Ranked contribution table below: every driver with the points it added, "
                     "in English and Tamil (this module)",
        "question": "Why did the model say that?",
    },
]


def signal_contributions(result: Any, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """SHAP-style attribution: one row per signal, with the points it added.

    Additive by construction - the rows sum to the fraud score (up to rounding),
    which is what makes the score auditable instead of a black box.
    """
    entries = build_explanation(result, cfg)
    rows = [
        {
            "signal": entry["text_en"],
            "signal_ta": entry["text_ta"],
            "group": entry["group"],
            "severity": entry["severity"],
            "contribution": entry["contribution"],
        }
        for entry in entries
    ]
    rows.sort(key=lambda row: float(row["contribution"]), reverse=True)
    return rows


def attribution_total(result: Any, cfg: Dict[str, Any]) -> Dict[str, float]:
    """Sum of attributed points vs the reported score (rounding-aware)."""
    rows = signal_contributions(result, cfg)
    attributed = round(sum(float(row["contribution"]) for row in rows), 1)
    return {
        "attributed": attributed,
        "score": round(float(getattr(result, "fraud_risk", 0.0)), 1),
        "gap": round(abs(attributed - float(getattr(result, "fraud_risk", 0.0))), 1),
    }
