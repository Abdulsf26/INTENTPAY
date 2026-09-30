"""Data access layer: profiles, histories, scenarios, evaluation set.

The app regenerates the demo histories at startup (deterministic per date) so
the "this month" budget maths is always current; the CSVs shipped in DATA/
are the samples produced on the build date and are used by the test-suite.
Nothing here touches the network.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from SRC import DATA_GENERATOR as generator
from SRC.MODELS import CustomerProfile, Transaction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "DATA")

CATEGORY_ORDER = [
    "FOOD", "ESSENTIALS", "HEALTH", "TRAVEL", "EDUCATION",
    "BILLS", "SHOPPING", "ENTERTAINMENT", "TRANSFER", "OTHER",
]


def load_profiles() -> Dict[str, CustomerProfile]:
    return generator.customer_profiles()


def profile_by_id(customer_id: str) -> CustomerProfile:
    profiles = load_profiles()
    return profiles.get(customer_id, profiles["customer_one"])


def load_history(customer_id: str, today: Optional[datetime] = None) -> pd.DataFrame:
    """Deterministic fresh history for the demo (regenerated per session)."""
    profile = profile_by_id(customer_id)
    return generator.generate_customer_history(profile, today=today)


def load_eval_set(today: Optional[datetime] = None) -> pd.DataFrame:
    return generator.generate_eval_set(today=today)


def load_scenarios() -> Dict[str, Any]:
    return generator.demo_scenarios()


def golden_pair() -> Dict[str, Any]:
    return generator.golden_demo_pair()


def payee_reports(upi_id: str) -> int:
    return int(generator.PAYEE_INTEL.get(upi_id, 0))


def history_to_frame(transactions: List[Transaction]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(
            columns=["id", "timestamp", "amount", "direction", "merchant_label",
                     "upi_id", "source", "category", "category_confidence",
                     "essential_flag", "recurring_flag", "self_transfer", "note", "utr"]
        )
    frame = pd.DataFrame([t.to_dict() for t in transactions])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame.sort_values("timestamp").reset_index(drop=True)


def append_transaction(history: pd.DataFrame, transaction: Transaction) -> pd.DataFrame:
    """Append one committed payment to the local store."""
    row = pd.DataFrame([transaction.to_dict()])
    row["timestamp"] = pd.to_datetime(row["timestamp"])
    return pd.concat([history, row], ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def write_sample_files(today: Optional[datetime] = None) -> Dict[str, str]:
    """Write the sample CSVs / JSON shipped with the repository."""
    os.makedirs(DATA_DIR, exist_ok=True)
    written: Dict[str, str] = {}
    profiles = load_profiles()
    for customer_id, profile in profiles.items():
        frame = load_history(customer_id, today=today)
        path = os.path.join(DATA_DIR, f"DEMO_HISTORY_{customer_id.upper()}.CSV")
        frame.to_csv(path, index=False)
        written[customer_id] = path
    eval_path = os.path.join(DATA_DIR, "EVAL_SET.CSV")
    load_eval_set(today=today).to_csv(eval_path, index=False)
    scenarios_path = os.path.join(DATA_DIR, "SCENARIOS.JSON")
    with open(scenarios_path, "w", encoding="utf-8") as handle:
        json.dump(load_scenarios(), handle, indent=2, ensure_ascii=False)
    profiles_path = os.path.join(DATA_DIR, "CUSTOMER_PROFILES.JSON")
    with open(profiles_path, "w", encoding="utf-8") as handle:
        json.dump({k: v.to_dict() for k, v in profiles.items()}, handle, indent=2, ensure_ascii=False)
    written["eval"] = eval_path
    written["scenarios"] = scenarios_path
    written["profiles"] = profiles_path
    return written


class CorrectionsStore:
    """User category corrections, kept in memory and optionally on disk."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or os.path.join(DATA_DIR, "USER_CORRECTIONS.JSON")
        self.data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    self.data = dict(json.load(handle))
            except (OSError, ValueError):
                self.data = {}

    def add(self, merchant_label: str, category: str, persist: bool = True) -> None:
        self.data[str(merchant_label).strip().lower()] = str(category).upper()
        if persist:
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as handle:
                    json.dump(self.data, handle, indent=2, ensure_ascii=False)
            except OSError:
                pass

    def as_dict(self) -> Dict[str, str]:
        return dict(self.data)
