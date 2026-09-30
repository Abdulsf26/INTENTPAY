"""Risk fusion engine: transaction behaviour + recipient + user intent.

Fraud risk and budget risk are deliberately kept as separate dimensions and
fused into a *recommendation*, never collapsed into one meaningless number.

    fraud_risk = w_t * transaction_risk + w_i * intent_risk + w_r * recipient_risk

When no reason is given and the preliminary (transaction + recipient) score
crosses ``ask_intent_above``, the engine returns ``intent_requested=True`` and
the UI asks "why are you paying?" — that conditional prompt is the product.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from SRC import BUDGET as budget_engine
from SRC.ANOMALY import anomaly_score_with_profile
from SRC.CATEGORIZER import categorise
from SRC.EXPLAIN import build_explanation
from SRC.FEATURES import extract_features
from SRC.FORECAST import robust_forecast
from SRC.INTENT_ENGINE import score_intent
from SRC.LANGUAGE import t
from SRC.MODELS import (
    BudgetImpact,
    CustomerProfile,
    PaymentRequest,
    RiskResult,
    clamp,
    make_utr,
)
from SRC.CONFIG import risk_band

# --------------------------------------------------------------------------- #
#  Rule weights for the transaction-behaviour component (sum of maxima = 1.00)
# --------------------------------------------------------------------------- #

RULE_WEIGHTS: Dict[str, float] = {
    "new_payee": 0.16,
    "amount_unusual": 0.14,       # z-score and ratio-to-median, combined
    "night": 0.06,
    "velocity": 0.10,
    "location": 0.10,
    "on_call_amount": 0.12,
    "battery_low": 0.04,
    "channel_link": 0.06,
    "device_new": 0.05,
    "round_amount": 0.03,
    "payee_reports": 0.20,
    "category_deviation": 0.08,
}

RECIPIENT_WEIGHTS: Dict[str, float] = {
    "new_payee": 0.35,
    "payee_reports": 0.35,
    "personal_handle": 0.10,
    "recently_added": 0.15,
    "unverified_merchant": 0.10,
}


def _rule_factors(features: Dict[str, float], payment: PaymentRequest) -> Dict[str, float]:
    """Map raw signals to bounded 0-1 risk factors (documented in FORMULAS.MD)."""
    zscore = float(features.get("amount_zscore", 0.0))
    ratio = float(features.get("amount_ratio", 0.0))
    amount_unusual = max(0.0, min(1.0, max(zscore / 4.0, (ratio - 1.0) / 5.0)))
    velocity = float(features.get("velocity_24h", 0.0))
    return {
        "new_payee": float(features.get("is_new_payee", 0.0)),
        "amount_unusual": amount_unusual,
        "night": float(features.get("is_night", 0.0)),
        "velocity": max(0.0, min(1.0, velocity / 6.0)),
        "location": float(features.get("is_new_location", 0.0)),
        "on_call_amount": min(1.0, float(features.get("on_call", 0.0)) * (float(payment.amount) / 20000.0)),
        "battery_low": float(features.get("battery_low", 0.0)),
        "channel_link": float(features.get("channel_link", 0.0)),
        "device_new": float(features.get("device_new", 0.0)),
        "round_amount": float(features.get("is_round_amount", 0.0)),
        "payee_reports": float(features.get("payee_reports", 0.0)),
        "category_deviation": max(0.0, min(1.0, float(features.get("category_deviation", 0.0)) / 5.0)),
    }


def transaction_risk(
    features: Dict[str, float],
    payment: PaymentRequest,
    history: Optional[pd.DataFrame],
    profile: CustomerProfile,
    cfg: Dict[str, Any],
) -> Tuple[float, Dict[str, Any]]:
    """Blend the rule layer with the Isolation Forest layer."""
    risk_cfg = cfg["risk"]
    factors = _rule_factors(features, payment)
    rule_score = sum(RULE_WEIGHTS[name] * value for name, value in factors.items())
    rule_risk = clamp(100.0 * rule_score)

    anomaly, anomaly_confidence, anomaly_details = anomaly_score_with_profile(
        features, history, profile, cfg
    )
    blend = float(risk_cfg.get("anomaly_blend", 0.45))
    total = (1.0 - blend) * rule_risk + blend * anomaly
    details = {
        "rule_risk": round(rule_risk, 1),
        "anomaly_score": anomaly,
        "anomaly_confidence": anomaly_confidence,
        "anomaly_details": anomaly_details,
        "factors": {k: round(v, 3) for k, v in factors.items()},
        "blend": blend,
    }
    return round(clamp(total), 1), details


def recipient_risk(
    payment: PaymentRequest,
    profile: CustomerProfile,
    payee_reports: int = 0,
) -> Tuple[float, Dict[str, Any]]:
    """Recipient intelligence: newness, reports, handle type, verification."""
    factors = {
        "new_payee": 1.0 if payment.new_payee else 0.0,
        "payee_reports": min(float(payee_reports), 5.0) / 5.0,
        "personal_handle": 1.0 if (payment.payee_upi and payment.payee_upi.split("@")[0].isdigit()) else 0.0,
        "recently_added": 1.0 if payment.new_payee else 0.0,
        "unverified_merchant": 0.0,
    }
    known = {p.get("upi_id", "").lower() for p in profile.known_payees}
    if payment.payee_upi and payment.payee_upi.lower() in known:
        factors["recently_added"] = 0.0
        factors["new_payee"] = min(factors["new_payee"], 0.3)
    score = sum(RECIPIENT_WEIGHTS[name] * value for name, value in factors.items())
    return round(clamp(100.0 * score), 1), {
        "factors": {k: round(v, 3) for k, v in factors.items()}
    }


def _fuse_fraud(
    transaction: float,
    intent: Optional[float],
    recipient: float,
    cfg: Dict[str, Any],
) -> Tuple[float, str]:
    """Weighted fusion; missing intent redistributes weight honestly."""
    risk_cfg = cfg["risk"]
    w_t = float(risk_cfg["transaction_weight"])
    w_i = float(risk_cfg["intent_weight"])
    w_r = float(risk_cfg["beneficiary_weight"])
    if intent is None:
        base = w_t + w_r
        if base <= 0:
            return 50.0, "intent-unknown-neutral"
        score = (w_t * transaction + w_r * recipient) / base
        return round(clamp(score), 1), "intent-unknown-renormalised"
    score = w_t * transaction + w_i * intent + w_r * recipient
    return round(clamp(score), 1), "full-fusion"


# --------------------------------------------------------------------------- #
#  Exact additive attribution (SHAP-style)
# --------------------------------------------------------------------------- #

def _label(key: str, lang: str = "en") -> str:
    try:
        return t(key, lang)
    except Exception:  # pragma: no cover - defensive
        return key


def fraud_attribution(
    txn_risk: float,
    txn_details: Dict[str, Any],
    intent_risk: Optional[float],
    intent_result: Optional[Dict[str, Any]],
    rcpt_risk: float,
    rcpt_details: Dict[str, Any],
    fraud: float,
    cfg: Dict[str, Any],
    self_transfer: bool = False,
) -> List[Dict[str, Any]]:
    """Decompose the fraud score into the points every signal added.

    The fusion is linear, so the decomposition is exact: the rows sum to the
    reported score (within one rounding step), which is what makes the score
    auditable instead of a black box.

    ```
    fraud = w_t·transaction + w_i·intent + w_r·recipient   (weights sum to 1)
    transaction = (1-blend)·rules + blend·anomaly
    ```
    """
    risk_cfg = cfg["risk"]
    w_t = float(risk_cfg["transaction_weight"])
    w_i = float(risk_cfg["intent_weight"])
    w_r = float(risk_cfg["beneficiary_weight"])
    blend = float(risk_cfg.get("anomaly_blend", 0.45))
    if intent_risk is None:
        # same renormalisation _fuse_fraud applies when no reason is given
        base = w_t + w_r
        if base > 1e-9:
            w_t, w_r = w_t / base, w_r / base
        w_i = 0.0

    rows: List[Dict[str, Any]] = []

    # ---- 1. behaviour block: rules + anomaly, exactly as fused ---------------
    factors = (txn_details or {}).get("factors", {}) or {}
    rule_total = sum(RULE_WEIGHTS[name] * float(value) for name, value in factors.items())
    rule_risk = min(100.0, 100.0 * rule_total)
    anomaly = float((txn_details or {}).get("anomaly_score", 50.0) or 50.0)
    txn_unclamped = (1.0 - blend) * rule_risk + blend * anomaly
    txn_scale = (float(txn_risk) / txn_unclamped) if txn_unclamped > 1e-9 else 0.0

    for name, value in factors.items():
        value = float(value or 0.0)
        if value <= 0.0:
            continue
        share = (RULE_WEIGHTS[name] * value) / rule_total if rule_total > 1e-9 else 0.0
        points = w_t * txn_scale * (1.0 - blend) * rule_risk * share
        rows.append(_row(_RULE_LABELS.get(name, name), "behaviour", points, value))
    if anomaly > 0.0 and blend > 0.0:
        points = w_t * txn_scale * blend * anomaly
        confidence = str((txn_details or {}).get("anomaly_confidence", ""))
        rows.append(_row("expl_anomaly", "behaviour", points,
                         detail=f"{anomaly:.0f}/100 {confidence}".strip()))

    # ---- 2. intent block ------------------------------------------------------
    if intent_risk is not None and w_i > 0.0:
        matched = list((intent_result or {}).get("matched", []) or [])
        bonuses = list((intent_result or {}).get("bonus", []) or [])
        raw = sum(float(m.get("weight", 0.0)) * float(m.get("factor", 0.0)) for m in matched)
        bonus_total = sum(float(b.get("amount", 0.0)) for b in bonuses)
        unclamped = 100.0 * min(1.0, raw) + bonus_total
        scale = (float(intent_risk) / unclamped) if unclamped > 1e-9 else 0.0
        for signal in matched:
            share = (float(signal["weight"]) * float(signal["factor"])) / raw if raw > 1e-9 else 0.0
            points = w_i * scale * 100.0 * min(1.0, raw) * share
            key = _INTENT_KEY.get(signal.get("family"), signal.get("family", ""))
            rows.append(_row(key, "intent", points,
                             detail=", ".join((signal.get("phrases") or signal.get("roots") or [])[:3])))
        for bonus in bonuses:
            points = w_i * scale * float(bonus.get("amount", 0.0))
            rows.append(_row("expl_" + str(bonus.get("label", "")).replace(" ", "_").replace("+", "and"),
                             "intent", points, detail=str(bonus.get("label", ""))))

    # ---- 3. recipient block ---------------------------------------------------
    rcpt_factors = (rcpt_details or {}).get("factors", {}) or {}
    rcpt_total = sum(RECIPIENT_WEIGHTS[name] * float(value)
                     for name, value in rcpt_factors.items())
    for name, value in rcpt_factors.items():
        value = float(value or 0.0)
        if value <= 0.0:
            continue
        share = (RECIPIENT_WEIGHTS[name] * value) / rcpt_total if rcpt_total > 1e-9 else 0.0
        points = w_r * (float(rcpt_risk) / 100.0) * 100.0 * share if rcpt_total > 1e-9 else 0.0
        rows.append(_row(_RECIPIENT_LABELS.get(name, name), "recipient", points, value))

    # ---- 3b. residuals: a component with no matching signal still costs points
    intent_rows = [row for row in rows if row["group"] == "intent"]
    if intent_risk is not None and w_i > 0.0 and not intent_rows:
        rows.append(_row("expl_intent_baseline", "intent", w_i * float(intent_risk),
                         detail="no scam pattern in the reason"))
    if not [row for row in rows if row["group"] == "recipient"] and float(rcpt_risk) > 0.0:
        rows.append(_row("expl_recipient_baseline", "recipient", w_r * float(rcpt_risk)))

    # ---- 4. self-transfer cap (the one honest negative) -----------------------
    attributed = sum(row["points"] for row in rows)
    cap_gap = round(float(fraud) - attributed, 1)
    if self_transfer and abs(cap_gap) > 0.05:
        rows.append(_row("expl_self_transfer_cap", "cap", cap_gap, detail="own-account transfer"))

    rows.sort(key=lambda row: float(row["points"]), reverse=True)
    return rows


_RULE_LABELS = {
    "new_payee": "expl_new_payee",
    "amount_unusual": "expl_amount_high",
    "night": "expl_night",
    "velocity": "expl_velocity",
    "location": "expl_location",
    "on_call_amount": "expl_on_call",
    "battery_low": "expl_battery",
    "channel_link": "expl_channel",
    "device_new": "expl_device",
    "round_amount": "expl_round_amount",
    "payee_reports": "expl_payee_reports",
    "category_deviation": "expl_category_deviation",
}
_RECIPIENT_LABELS = {
    "new_payee": "expl_new_payee",
    "payee_reports": "expl_payee_reports",
    "personal_handle": "expl_personal_handle",
    "recently_added": "expl_recently_added",
    "unverified_merchant": "expl_unverified_merchant",
}
_INTENT_KEY = {
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


def _row(key: str, group: str, points: float, value: Optional[float] = None,
         detail: str = "") -> Dict[str, Any]:
    return {
        "key": key,
        "group": group,
        "points": round(float(points), 1),
        "signal_en": _label(key, "en") + (f" ({detail})" if detail else ""),
        "signal_ta": _label(key, "ta"),
        "value": None if value is None else round(float(value), 3),
    }


def _recommendation(fraud_band: str, budget_band: str, intent_unknown: bool) -> Tuple[str, str]:
    """Fusion truth table (manual page 6)."""
    high_fraud = fraud_band in ("HIGH", "CRITICAL")
    if fraud_band == "LOW" and budget_band == "LOW":
        return "verdict_normal", "normal"
    if fraud_band == "LOW" and budget_band in ("MEDIUM", "HIGH"):
        return "verdict_budget_warning", "budget-warning"
    if high_fraud and budget_band == "LOW":
        return "verdict_fraud_intervention", "fraud-intervention"
    if high_fraud and budget_band in ("MEDIUM", "HIGH"):
        return "verdict_strong_warning", "strong-warning"
    if intent_unknown and budget_band in ("MEDIUM", "HIGH"):
        return "verdict_budget_missing_fraud", "budget-missing-fraud"
    if high_fraud:
        return "verdict_fraud_unknown_budget", "fraud-unknown-budget"
    return "verdict_budget_warning", "review"


def evaluate_payment(
    payment: PaymentRequest,
    history: Optional[pd.DataFrame],
    profile: CustomerProfile,
    cfg: Dict[str, Any],
    corrections: Optional[Dict[str, str]] = None,
    payee_reports: int = 0,
) -> RiskResult:
    """Run the complete pre-payment pipeline for one candidate payment."""
    timings: Dict[str, float] = {}
    started = time.perf_counter()

    # 1. categorise (also detects self-transfers).  An explicit user choice in
    # the payment form always wins over the automatic classifier.
    category, category_confidence, category_stage, self_transfer = categorise(
        payment.payee_name or payment.note,
        note=payment.note,
        upi_id=payment.payee_upi,
        profile_own_upi_ids=profile.own_upi_ids,
        corrections=corrections,
        history=history,
    )
    explicit = (payment.purpose_category or "").upper()
    if explicit and explicit != "OTHER" and not self_transfer:
        category, category_confidence, category_stage = explicit, 1.0, "user-selected"
    payment.purpose_category = category
    timings["categorise_ms"] = round((time.perf_counter() - started) * 1000, 3)

    # 2. features
    t0 = time.perf_counter()
    features = extract_features(payment, history, profile, payee_reports=payee_reports)
    timings["features_ms"] = round((time.perf_counter() - t0) * 1000, 3)

    # 3. transaction + recipient components
    t0 = time.perf_counter()
    txn_risk, txn_details = transaction_risk(features, payment, history, profile, cfg)
    rcpt_risk, rcpt_details = recipient_risk(payment, profile, payee_reports)
    timings["behaviour_ms"] = round((time.perf_counter() - t0) * 1000, 3)

    # 4. intent (conditional)
    t0 = time.perf_counter()
    intent_result = score_intent(payment.intent_text, cfg)
    intent_risk = intent_result["risk"] if not intent_result["unknown"] else None
    timings["intent_ms"] = round((time.perf_counter() - t0) * 1000, 3)

    # 5. preliminary fusion decides whether to ask for intent
    prelim, prelim_mode = _fuse_fraud(txn_risk, None, rcpt_risk, cfg)
    ask_above = float(cfg["risk"]["ask_intent_above"])
    intent_requested = False
    intent_provided = payment.intent_text is not None and str(payment.intent_text).strip() != ""
    intent_unknown = False
    if intent_provided:
        fraud, mode = _fuse_fraud(txn_risk, intent_risk, rcpt_risk, cfg)
    else:
        fraud, mode = prelim, prelim_mode
        intent_unknown = prelim >= ask_above
        if intent_unknown:
            intent_requested = True

    band = risk_band(fraud, cfg)

    # moving your own money between your own accounts is not a scam signal by
    # itself (the classic "safe account" scam sends money to a *fraudster*,
    # never to a verified own account) -> cap and label it honestly.
    if self_transfer:
        # cap just below the MEDIUM band so a genuine own-account transfer is
        # never reported as "review" (the safe-account scam targets *fraudster*
        # accounts, which the recipient layer still scores as new payees)
        cap = max(1.0, float(cfg["risk"]["medium_threshold"]) - 1.0)
        fraud = min(fraud, cap)
        band = risk_band(fraud, cfg)

    # 6. budget dimension (kept separate)
    t0 = time.perf_counter()
    now = payment.resolved_timestamp()
    forecast = robust_forecast(history, cfg, now)
    impact = budget_engine.budget_impact(
        payment.amount, category, history, cfg, now, forecast
    )
    timings["budget_ms"] = round((time.perf_counter() - t0) * 1000, 3)

    # 7. recommendation
    rec_key, rec_kind = _recommendation(band, impact.budget_band, intent_unknown)
    if self_transfer:
        rec_key, rec_kind = "verdict_normal", "self-transfer"

    timings["total_ms"] = round((time.perf_counter() - started) * 1000, 3)

    attribution = fraud_attribution(
        txn_risk, txn_details, intent_risk, intent_result, rcpt_risk, rcpt_details,
        fraud, cfg, self_transfer=self_transfer,
    )
    # the score *before* the reason was known - shown next to the threshold so the
    # "did it ask me why?" decision is auditable
    features = {**features, "preliminary_score": prelim, "ask_intent_above": ask_above}

    result = RiskResult(
        fraud_risk=fraud,
        band=band,
        transaction_risk=txn_risk,
        intent_risk=intent_risk,
        recipient_risk=rcpt_risk,
        intent_requested=intent_requested,
        intent_provided=intent_provided,
        intent_unknown=intent_unknown,
        ai_engine=intent_result.get("engine", "local"),
        ai_fallback=bool(intent_result.get("fallback", False)),
        anomaly_score=float(txn_details["anomaly_score"]),
        anomaly_confidence=txn_details["anomaly_confidence"],
        budget=impact,
        recommendation=t(
            rec_key, cfg.get("accessibility", {}).get("language", "en")
        ),
        recommendation_key=rec_key,
        explanation=[],
        attribution=attribution,
        features={**features, **{f"txn_{k}": v for k, v in txn_details["factors"].items()}},
        matched_signals=intent_result.get("matched", []),
        latency_ms=timings,
        category=category,
        category_confidence=category_confidence,
        self_transfer=self_transfer,
        utr=make_utr(profile.customer_id, payment.payee_upi, payment.amount, str(now)),
    )
    # attach extra detail for the explainer / UI
    result.features["_txn_details"] = 0.0  # placeholder keeps schema stable
    result.__dict__["_txn_details"] = txn_details  # type: ignore[attr-defined]
    result.__dict__["_rcpt_details"] = rcpt_details  # type: ignore[attr-defined]
    result.__dict__["_intent_result"] = intent_result  # type: ignore[attr-defined]
    result.__dict__["_forecast"] = forecast  # type: ignore[attr-defined]
    result.__dict__["_fusion_mode"] = mode  # type: ignore[attr-defined]
    result.__dict__["_category_stage"] = category_stage  # type: ignore[attr-defined]
    result.explanation = build_explanation(result, cfg)
    return result


from SRC.LANGUAGE import t  # noqa: E402  (placed here to keep imports tidy)
