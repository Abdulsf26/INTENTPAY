"""Core data models for IntentPay (dataclasses + small helpers).

Kept dependency-free so the whole engine can be unit-tested without Streamlit.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
#  Money formatting (Indian digit grouping: 12,34,567)
# --------------------------------------------------------------------------- #


def inr(amount: Any, decimals: int = 0) -> str:
    """Format a number with Indian digit grouping and a rupee sign."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return "₹" + str(amount)
    sign = "-" if value < 0 else ""
    value = abs(value)
    text = f"{value:,.{decimals}f}"
    if "." in text:
        int_part, frac = text.split(".")
    else:
        int_part, frac = text, ""
    int_part = int_part.replace(",", "")
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups: List[str] = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups + [last3])
    out = sign + "₹" + int_part
    if frac:
        out += "." + frac
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# --------------------------------------------------------------------------- #
#  Records
# --------------------------------------------------------------------------- #


@dataclass
class Transaction:
    """One row of the local transaction store."""

    id: str
    timestamp: datetime
    amount: float
    direction: str  # DEBIT | CREDIT
    merchant_label: str
    upi_id: str
    source: str = "demo"
    category: str = "OTHER"
    category_confidence: float = 0.0
    essential_flag: bool = False
    recurring_flag: bool = False
    self_transfer: bool = False
    note: str = ""
    utr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Transaction":
        data = dict(data)
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        data["timestamp"] = ts
        return Transaction(**data)


@dataclass
class CustomerProfile:
    """Everything the engine knows about the person paying."""

    customer_id: str
    name: str
    age: int
    language: str = "ta"
    elder_mode: bool = True
    usual_city: str = "Chennai"
    usual_lat: float = 13.0827
    usual_lon: float = 80.2707
    typical_amount: float = 650.0
    monthly_limit: float = 15000.0
    category_limits: Dict[str, float] = field(default_factory=dict)
    known_devices: List[str] = field(default_factory=lambda: ["device-android-01"])
    own_upi_ids: List[str] = field(default_factory=list)
    known_payees: List[Dict[str, Any]] = field(default_factory=list)
    seed: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CustomerProfile":
        return CustomerProfile(**dict(data))


@dataclass
class PaymentRequest:
    """A candidate payment (before any risk analysis)."""

    amount: float
    method: str = "UPI"  # UPI | BANK
    payee_name: str = ""
    payee_upi: str = ""
    purpose_category: str = "OTHER"
    timestamp: Optional[datetime] = None
    city: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    on_call: bool = False
    call_duration_s: int = 0
    channel: str = "P2P"  # P2P | QR | LINK
    new_payee: bool = False
    device_id: str = ""
    battery_pct: int = 85
    intent_text: Optional[str] = None
    note: str = ""

    def resolved_timestamp(self, now: Optional[datetime] = None) -> datetime:
        return self.timestamp or now or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.timestamp:
            data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class BudgetImpact:
    """What a payment does to the user's money (kept separate from fraud)."""

    monthly_limit: float = 0.0
    spent_before: float = 0.0
    remaining_before: float = 0.0
    utilisation_before: float = 0.0
    state_before: str = "SAFE"
    spent_after: float = 0.0
    remaining_after: float = 0.0
    utilisation_after: float = 0.0
    category: str = "OTHER"
    category_limit: float = 0.0
    category_spent_before: float = 0.0
    category_spent_after: float = 0.0
    category_utilisation_after: float = 0.0
    would_exceed_month: bool = False
    would_exceed_category: bool = False
    projected_month_end: float = 0.0
    projected_overrun: float = 0.0
    forecast_confidence: str = "LOW"
    budget_risk: float = 0.0
    budget_band: str = "LOW"  # LOW | MEDIUM | HIGH budget impact
    messages: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskResult:
    """Full output of the pre-payment evaluation pipeline."""

    fraud_risk: float = 0.0
    band: str = "LOW"
    transaction_risk: float = 0.0
    intent_risk: Optional[float] = None
    recipient_risk: float = 0.0
    intent_requested: bool = False
    intent_provided: bool = False
    intent_unknown: bool = False
    ai_engine: str = "local"
    ai_fallback: bool = False
    anomaly_score: float = 50.0
    anomaly_confidence: str = "LOW"
    budget: BudgetImpact = field(default_factory=BudgetImpact)
    recommendation: str = ""
    recommendation_key: str = "verdict_normal"
    explanation: List[Dict[str, Any]] = field(default_factory=list)
    # SHAP-style additive decomposition of the fraud score (sums to fraud_risk)
    attribution: List[Dict[str, Any]] = field(default_factory=list)
    features: Dict[str, float] = field(default_factory=dict)
    matched_signals: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: Dict[str, float] = field(default_factory=dict)
    category: str = "OTHER"
    category_confidence: float = 0.0
    self_transfer: bool = False
    utr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_utr(*parts: Any) -> str:
    """Deterministic 12-digit demo UTR reference (never a real bank UTR)."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return digest[:12].upper()
