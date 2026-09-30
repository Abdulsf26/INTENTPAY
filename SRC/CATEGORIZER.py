"""Three-stage spending categoriser (learned rules -> keywords -> fallback).

The manual's quality rule: "A wrong category corrupts the budget, and then
every warning built on it becomes polished nonsense."  So every classification
carries a confidence, low-confidence rows land in OTHER and are surfaced for
one-tap user correction, and self-transfers are excluded from consumption.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

ESSENTIAL_CATEGORIES = {"ESSENTIALS", "HEALTH", "EDUCATION", "BILLS", "FOOD"}
DISCRETIONARY_CATEGORIES = {"SHOPPING", "ENTERTAINMENT"}

# learned merchant -> category map is cached per history signature because it
# is rebuilt on every categorise() call otherwise (hot path).
_MERCHANT_CACHE: "OrderedDict[str, Dict[str, str]]" = OrderedDict()
_MERCHANT_CACHE_LIMIT = 8

KEYWORDS: Dict[str, List[str]] = {
    "FOOD": [
        "grocery", "grocer", "restaurant", "hotel", "mess", "canteen",
        "bakery", "milk", "vegetable", "fruits", "supermarket", "kirana",
        "உணவு", "மளிகை", "ஹோட்டல்", "பாலா", "கிரானா",
    ],
    "ESSENTIALS": [
        "rent", "house", "utilities", "water", "gas", "cylinder", "maintenance",
        "வாடிக்கை", "நீர்", "சிலிண்டர்", "வீட்டு செலவு",
    ],
    "HEALTH": [
        "medicine", "pharmacy", "hospital", "clinic", "doctor", "lab", "dental",
        "மருத்துவ", "மருந்து", "மருத்துவமனை", "கிளினிக்",
    ],
    "TRAVEL": [
        "fuel", "petrol", "diesel", "bus", "train", "cab", "taxi", "auto",
        "metro", "irctc", "travel",
        "எரிவாயு", "பெட்ரோல்", "பஸ்", "ரயில்", "கேப்", "ஆட்டோ",
    ],
    "EDUCATION": [
        "school", "college", "fee", "fees", "books", "stationery", "course",
        "tuition", "university",
        "பள்ளி", "கல்லூரி", "கட்டணம்", "புத்தகம்", "டியுஷன்",
    ],
    "BILLS": [
        "mobile", "recharge", "internet", "broadband", "dth", "subscription",
        "electricity", "bill",
        "மொபைல்", "ரீசார்ஜ்", "இணையம்", "கட்டணம்", "மின்",
    ],
    "SHOPPING": [
        "mall", "fashion", "clothes", "electronics", "amazon", "flipkart",
        "myntra", "shoes", "gift",
        "ஷாப்பிங்", "ஆடை", "மின்சாதனம்",
    ],
    "ENTERTAINMENT": [
        "movie", "cinema", "pvr", "netflix", "spotify", "game", "prime video",
        "hotstar", "zomato",
        "சினிமா", "திரைப்படம்", "ஓட்டம்",
    ],
}

CONFIDENCE_LEARNED = 0.90
CONFIDENCE_RULE = 0.85
CONFIDENCE_KEYWORD = 0.65
CONFIDENCE_FALLBACK = 0.20
LOW_CONFIDENCE = 0.50


def _history_signature(history: Optional[pd.DataFrame]) -> str:
    if history is None or len(history) == 0:
        return "empty"
    debits = history[(history["direction"] == "DEBIT") & (~history["self_transfer"].astype(bool))]
    if len(debits) == 0:
        return "empty"
    return f"{len(debits)}:{float(debits['amount'].sum()):.2f}:{str(debits['timestamp'].max())}"


def _learn_merchant_map(history: Optional[pd.DataFrame]) -> Dict[str, str]:
    """Majority category per merchant label, learned from the local history."""
    if history is None or len(history) == 0:
        return {}
    signature = _history_signature(history)
    cached = _MERCHANT_CACHE.get(signature)
    if cached is not None:
        _MERCHANT_CACHE.move_to_end(signature)
        return cached
    debits = history[(history["direction"] == "DEBIT") & (~history["self_transfer"].astype(bool))]
    if len(debits) == 0:
        return {}
    out: Dict[str, str] = {}
    for merchant, group in debits.groupby(debits["merchant_label"].astype(str).str.lower()):
        counts = group["category"].value_counts()
        out[str(merchant)] = str(counts.index[0])
    _MERCHANT_CACHE[signature] = out
    if len(_MERCHANT_CACHE) > _MERCHANT_CACHE_LIMIT:
        _MERCHANT_CACHE.popitem(last=False)
    return out


def categorise(
    merchant_label: str,
    note: str = "",
    upi_id: str = "",
    profile_own_upi_ids: Optional[List[str]] = None,
    corrections: Optional[Dict[str, str]] = None,
    history: Optional[pd.DataFrame] = None,
) -> Tuple[str, float, str, bool]:
    """Return ``(category, confidence, stage, self_transfer)``."""
    own = {u.lower() for u in (profile_own_upi_ids or [])}
    if upi_id and upi_id.lower() in own:
        return "TRANSFER", 1.0, "self-transfer", True

    label = (merchant_label or "").strip().lower()
    if corrections and label in {k.lower(): v for k, v in corrections.items()}:
        lookup = {k.lower(): v for k, v in corrections.items()}
        return lookup[label].upper(), 1.0, "user-correction", False

    learned = _learn_merchant_map(history)
    if label and label in learned:
        return learned[label].upper(), CONFIDENCE_LEARNED, "learned-from-history", False

    text = f" {label} {(note or '').lower()} "
    best_category, best_hits = "OTHER", 0
    for category, words in KEYWORDS.items():
        hits = sum(1 for word in words if word in text)
        if hits > best_hits:
            best_category, best_hits = category, hits
    if best_hits > 0:
        confidence = min(CONFIDENCE_KEYWORD + 0.1 * (best_hits - 1), 0.9)
        return best_category, round(confidence, 2), "keyword-model", False

    return "OTHER", CONFIDENCE_FALLBACK, "fallback-ask-user", False


def is_essential(category: str) -> bool:
    return category.upper() in ESSENTIAL_CATEGORIES


def is_discretionary(category: str) -> bool:
    return category.upper() in DISCRETIONARY_CATEGORIES
