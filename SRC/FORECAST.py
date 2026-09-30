"""Robust month-end forecasting.

Uses the *median* of recent daily spend (not the mean) so one expensive day
cannot distort the projection, multiplied by remaining days and a
configurable seasonality factor.  Forecasts from thin history are labelled
low confidence instead of pretending to be precise.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from SRC.BUDGET import _month_bounds, month_spend


def daily_spend_series(
    history: Optional[pd.DataFrame], when: datetime, window_days: int
) -> List[float]:
    """Spend per day for the last ``window_days`` days (zeros included)."""
    if history is None or len(history) == 0:
        return [0.0] * window_days
    start = (when - timedelta(days=window_days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    mask = (
        (history["direction"] == "DEBIT")
        & (~history["self_transfer"].astype(bool))
        & (history["timestamp"] >= start)
        & (history["timestamp"] <= when)
    )
    rows = history.loc[mask]
    per_day = [0.0] * window_days
    for offset in range(window_days):
        day = start + timedelta(days=offset)
        day_end = day + timedelta(days=1)
        day_mask = (rows["timestamp"] >= day) & (rows["timestamp"] < day_end)
        per_day[offset] = float(rows.loc[day_mask, "amount"].sum())
    return per_day


def history_days(history: Optional[pd.DataFrame]) -> int:
    """Days of usable history (first debit to the latest transaction)."""
    if history is None or len(history) == 0:
        return 0
    first = history["timestamp"].min()
    last = history["timestamp"].max()
    return int((last - first).days) + 1


def forecast_confidence(days: int) -> str:
    if days >= 90:
        return "HIGH"
    if days >= 30:
        return "MEDIUM"
    return "LOW"


def robust_forecast(
    history: Optional[pd.DataFrame], cfg: Dict[str, Any], when: datetime
) -> Dict[str, Any]:
    """Projected month-end spend with a median-based daily rate."""
    budget_cfg = cfg["budget"]
    window = int(budget_cfg["forecast_window_days"])
    seasonality = float(budget_cfg.get("seasonality_factor", 1.0))
    limit = float(budget_cfg["monthly_limit"])

    series = daily_spend_series(history, when, window)
    d_robust = float(np.median(series)) if series else 0.0
    _, month_last = _month_bounds(when)
    days_remaining = max((month_last - when).days + 1, 1)
    spent = month_spend(history, when)
    projected = spent + d_robust * days_remaining * seasonality
    overrun = max(0.0, projected - limit)
    days_of_history = history_days(history)

    return {
        "spent_so_far": round(spent, 2),
        "daily_median": round(d_robust, 2),
        "daily_mean": round(float(np.mean(series)) if series else 0.0, 2),
        "days_remaining": days_remaining,
        "projected_month_end": round(projected, 2),
        "projected_overrun": round(overrun, 2),
        "confidence": forecast_confidence(days_of_history),
        "history_days": days_of_history,
        "window_days": window,
        "seasonality_factor": seasonality,
        "series": series,
    }


def forecast_error(actual: float, forecast: float) -> float:
    """Relative absolute error (used by the finance-metrics tests)."""
    return abs(forecast - actual) / max(abs(actual), 1e-9)
