"""Recurring-payment (UPI AutoPay-style) detection and commitment impact.

NPCI's UPI AutoPay enhancement (circular OC-223, Oct 2025) already lets users
view, revoke, pause and modify mandates.  IntentPay therefore does *not*
claim to invent mandate management — it adds financial-impact intelligence:
what the commitments cost against the monthly budget, what is due next, and
when a recurring amount silently increases.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from SRC.CATEGORIZER import is_essential


def detect_recurring(history: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    """Find same-merchant/same-amount payments at regular intervals."""
    if history is None or len(history) == 0:
        return []
    debits = history[(history["direction"] == "DEBIT") & (~history["self_transfer"].astype(bool))]
    commitments: List[Dict[str, Any]] = []
    if len(debits) == 0:
        return commitments

    for (merchant, amount), group in debits.groupby(
        [debits["merchant_label"].astype(str), debits["amount"].astype(float)]
    ):
        if len(group) < 3:
            continue
        times = sorted(group["timestamp"].tolist())
        gaps = [
            (times[i + 1] - times[i]).total_seconds() / 86400.0
            for i in range(len(times) - 1)
        ]
        median_gap = float(np.median(gaps))
        if median_gap <= 0:
            continue
        regularity = float(np.std(gaps)) / median_gap if median_gap else 99.0
        # regular = gaps don't wobble more than ~25% of the median gap
        if regularity > 0.25 or median_gap < 5:
            continue
        baseline = float(group["amount"].iloc[0])
        commitments.append(
            {
                "merchant": str(merchant),
                "amount": float(amount),
                "occurrences": int(len(group)),
                "median_gap_days": round(median_gap, 1),
                "regularity": round(regularity, 3),
                "first_seen": times[0].isoformat(),
                "last_seen": times[-1].isoformat(),
                "next_expected": (times[-1] + timedelta(days=median_gap)).isoformat(),
                "amount_increased": bool(float(amount) > baseline * 1.2),
                "category": str(group["category"].iloc[-1]),
            }
        )
    commitments.sort(key=lambda c: c["next_expected"])
    return commitments


def monthly_recurring_commitment(commitments: List[Dict[str, Any]]) -> float:
    """Project recurring commitments into a monthly rupee figure."""
    total = 0.0
    for item in commitments:
        gap = max(float(item.get("median_gap_days", 30.0)), 1.0)
        total += float(item["amount"]) * (30.0 / gap)
    return round(total, 2)


def upcoming_within(commitments: List[Dict[str, Any]], when: datetime, days: int = 7) -> List[Dict[str, Any]]:
    horizon = when + timedelta(days=days)
    out = []
    for item in commitments:
        try:
            due = datetime.fromisoformat(item["next_expected"])
        except (KeyError, ValueError):
            continue
        if when <= due <= horizon:
            out.append(item)
    return out


def discretionary_allowance(
    history: Optional[pd.DataFrame],
    cfg: Dict[str, Any],
    when: datetime,
    commitments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """How much genuinely optional money is left after essentials and
    known recurring commitments."""
    from SRC.BUDGET import category_spend, month_spend

    limit = float(cfg["budget"]["monthly_limit"])
    if commitments is None:
        commitments = detect_recurring(history)
    spent = month_spend(history, when)
    cat_spend = category_spend(history, when)
    essential = sum(v for k, v in cat_spend.items() if is_essential(k))
    optional = sum(v for k, v in cat_spend.items() if not is_essential(k) and k != "TRANSFER")
    recurring = monthly_recurring_commitment(commitments)
    available = limit - essential - recurring
    return {
        "monthly_limit": limit,
        "essential_spent": round(essential, 2),
        "optional_spent": round(optional, 2),
        "recurring_monthly_commitment": recurring,
        "available_discretionary": round(available, 2),
        "remaining_discretionary": round(available - optional, 2),
        "total_spent": round(spent, 2),
    }
