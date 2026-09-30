"""Budget engine: remaining budget, category limits, daily allowance.

Guidance values, not financial advice — and never an automatic block.  The
warning is an intervention; the decision stays with the user.
"""
from __future__ import annotations

import calendar
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from SRC.MODELS import BudgetImpact, clamp

SAFE_MAX = 70.0
WATCH_MAX = 90.0


def _month_bounds(when: datetime) -> Tuple[datetime, datetime]:
    first = when.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(when.year, when.month)[1]
    last = first.replace(day=last_day, hour=23, minute=59, second=59)
    return first, last


def _spend_mask(history: Optional[pd.DataFrame], when: datetime) -> Optional[pd.Series]:
    """Rows that count as *spending* in the calendar month of ``when``.

    Single source of truth: debits only, never a self-transfer (moving your own
    money is not spending), never a future row.
    """
    if history is None or len(history) == 0:
        return None
    first, last = _month_bounds(when)
    return (
        (history["direction"] == "DEBIT")
        & (~history["self_transfer"].astype(bool))
        & (history["timestamp"] >= first)
        & (history["timestamp"] <= last)
    )


def month_spend(history: Optional[pd.DataFrame], when: datetime) -> float:
    """Total real spending in the calendar month of ``when``."""
    mask = _spend_mask(history, when)
    if mask is None:
        return 0.0
    return float(history.loc[mask, "amount"].sum())


def category_spend(history: Optional[pd.DataFrame], when: datetime) -> Dict[str, float]:
    """Category totals for the calendar month of ``when``."""
    out: Dict[str, float] = {}
    if history is None or len(history) == 0:
        return out
    mask = _spend_mask(history, when)
    if mask is None:
        return out
    rows = history.loc[mask]
    for category, group in rows.groupby("category"):
        out[str(category)] = float(group["amount"].sum())
    return out


def budget_state(utilisation_pct: float) -> str:
    if utilisation_pct >= 100.0:
        return "EXCEEDED"
    if utilisation_pct >= WATCH_MAX:
        return "NEAR LIMIT"
    if utilisation_pct >= SAFE_MAX:
        return "WATCH"
    return "SAFE"


def budget_band(utilisation_after: float, would_exceed: bool) -> str:
    """Budget-impact band for the fusion matrix (LOW / MEDIUM / HIGH)."""
    if would_exceed or utilisation_after >= 100.0:
        return "HIGH"
    if utilisation_after >= 80.0:
        return "MEDIUM"
    return "LOW"


def budget_impact(
    payment_amount: float,
    category: str,
    history: Optional[pd.DataFrame],
    cfg: Dict[str, Any],
    when: datetime,
    forecast: Optional[Dict[str, Any]] = None,
) -> BudgetImpact:
    """Everything the payment does to the user's money this month."""
    budget_cfg = cfg["budget"]
    limit = float(budget_cfg["monthly_limit"])
    cat_limit = float(budget_cfg.get("food_limit", 0.0)) if category == "FOOD" else 0.0
    if category != "FOOD":
        cat_limit = float(budget_cfg.get(f"{category.lower()}_limit", 0.0))

    spent = month_spend(history, when)
    cat_spent = category_spend(history, when).get(category, 0.0)
    amount = float(payment_amount)

    spent_after = spent + amount
    remaining_after = limit - spent_after
    util_before = 100.0 * spent / limit if limit else 0.0
    util_after = 100.0 * spent_after / limit if limit else 0.0
    cat_util_after = (
        100.0 * (cat_spent + amount) / cat_limit if cat_limit > 0 else 0.0
    )
    would_exceed_month = remaining_after < 0
    would_exceed_category = bool(cat_limit > 0 and (cat_spent + amount) > cat_limit)

    projected = float((forecast or {}).get("projected_month_end", 0.0))
    overrun = max(0.0, projected - limit)

    risk = clamp(max(util_after, cat_util_after))
    band = budget_band(util_after, would_exceed_month or would_exceed_category)

    messages: List[str] = []
    if would_exceed_month:
        messages.append("budget_exceed_month")
    if would_exceed_category:
        messages.append("budget_exceed_category")
    if overrun > 0:
        messages.append("projected_overrun_note")

    return BudgetImpact(
        monthly_limit=limit,
        spent_before=spent,
        remaining_before=limit - spent,
        utilisation_before=round(util_before, 1),
        state_before=budget_state(util_before),
        spent_after=spent_after,
        remaining_after=remaining_after,
        utilisation_after=round(util_after, 1),
        category=category,
        category_limit=cat_limit,
        category_spent_before=cat_spent,
        category_spent_after=cat_spent + amount,
        category_utilisation_after=round(cat_util_after, 1),
        would_exceed_month=would_exceed_month,
        would_exceed_category=would_exceed_category,
        projected_month_end=projected,
        projected_overrun=overrun,
        forecast_confidence=str((forecast or {}).get("confidence", "LOW")),
        budget_risk=round(risk, 1),
        budget_band=band,
        messages=messages,
    )


def daily_allowance(remaining: float, when: datetime) -> float:
    """Remaining budget spread over the days left in the month."""
    _, last = _month_bounds(when)
    days_left = max((last - when).days + 1, 1)
    return remaining / days_left if remaining > 0 else 0.0


# --------------------------------------------------------------------------- #
#  Spending triage: needs / wants / unnecessary
# --------------------------------------------------------------------------- #

TRIAGE_BUCKETS: Tuple[str, ...] = ("needs", "wants", "unnecessary")

# Display labels, Tamil first because the elder mode is Tamil first.
TRIAGE_LABELS: Dict[str, Dict[str, str]] = {
    "needs": {"en": "Needs", "ta": "தேவையான செலவுகள்"},
    "wants": {"en": "Wants", "ta": "விருப்ப செலவுகள்"},
    "unnecessary": {"en": "Unnecessary", "ta": "தேவையற்ற செலவுகள்"},
}
TRIAGE_ICONS: Dict[str, str] = {"needs": "\U0001f35a", "wants": "\U0001f6cd\ufe0f",
                               "unnecessary": "\U0001f4a8"}


def triage_label(bucket: str, lang: str = "en") -> str:
    """Localised name of a triage bucket."""
    return TRIAGE_LABELS.get(bucket, TRIAGE_LABELS["wants"]).get(lang, bucket)


def triage_of(category: str, cfg: Dict[str, Any]) -> str:
    """Classify a category as needs / wants / unnecessary (default: wants)."""
    mapping = (cfg.get("budget", {}) or {}).get("triage_map", {}) or {}
    bucket = mapping.get(str(category).upper(), "wants")
    return bucket if bucket in TRIAGE_BUCKETS else "wants"


def spend_by_triage(
    history: Optional[pd.DataFrame], when: datetime, cfg: Dict[str, Any]
) -> Dict[str, float]:
    """This month's spending split into needs / wants / unnecessary.

    Self-transfers are excluded (they are not spending - see the dashboard rule),
    and the three buckets always add up to ``month_spend``.
    """
    out: Dict[str, float] = {bucket: 0.0 for bucket in TRIAGE_BUCKETS}
    mask = _spend_mask(history, when)
    if mask is None:
        return out
    rows = history.loc[mask]
    for category, amount in zip(rows["category"], rows["amount"]):
        out[triage_of(str(category), cfg)] += float(amount)
    return {bucket: round(value, 2) for bucket, value in out.items()}


def triage_summary(
    history: Optional[pd.DataFrame], when: datetime, cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """Everything the elder-mode card needs: split, total, remaining, share."""
    split = spend_by_triage(history, when, cfg)
    total = sum(split.values())
    limit = float(cfg.get("budget", {}).get("monthly_limit", 0.0) or 0.0)
    remaining = round(limit - total, 2)
    return {
        "split": split,
        "total": round(total, 2),
        "limit": limit,
        "remaining": remaining,
        "utilisation": round(100.0 * total / limit, 1) if limit else 0.0,
        "state": budget_state(100.0 * total / limit) if limit else "SAFE",
        "shares": {
            bucket: (round(100.0 * split[bucket] / total, 1) if total else 0.0)
            for bucket in TRIAGE_BUCKETS
        },
    }
