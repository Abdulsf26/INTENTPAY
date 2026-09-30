"""IntentPay central configuration.

Every tunable parameter lives here so a judge can change any knob from the
Judge Panel and immediately see the effect on the pipeline.  An invalid
configuration is rejected and the last working configuration is preserved,
exactly as required by the implementation manual (page 11).
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

SUPPORTED_LANGUAGES: Tuple[str, ...] = ("en", "ta")

DEFAULT_CONFIG: Dict[str, Any] = {
    # ---- payment safety engine -------------------------------------------------
    "risk": {
        # fusion weights (must sum to 1.0)
        "transaction_weight": 0.40,
        "intent_weight": 0.45,
        "beneficiary_weight": 0.15,
        # when to ask "why are you paying?"
        "ask_intent_above": 55.0,
        # risk bands
        "medium_threshold": 30.0,
        "high_threshold": 55.0,
        "critical_threshold": 75.0,
        # anomaly model blend (0 = pure rules, 1 = pure Isolation Forest)
        "anomaly_blend": 0.45,
        "anomaly_contamination": 0.05,
        "anomaly_n_estimators": 120,
    },
    # ---- personal financial guardian ------------------------------------------
    "budget": {
        "monthly_limit": 15000.0,
        "food_limit": 6000.0,
        "alert_at_percent": 80.0,
        "forecast_window_days": 14,
        "seasonality_factor": 1.0,
        # spending triage: every category is a NEED, a WANT or UNNECESSARY.
        # Editable in the Judge Panel - a layman can re-classify any category.
        "triage_map": {
            "ESSENTIALS": "needs",
            "HEALTH": "needs",
            "BILLS": "needs",
            "EDUCATION": "needs",
            "FOOD": "wants",
            "SHOPPING": "wants",
            "TRAVEL": "wants",
            "ENTERTAINMENT": "unnecessary",
            "OTHER": "wants",
        },
    },
    # ---- emergency PIN / decoy mode -------------------------------------------
    #  A duress feature: the emergency PIN opens a *restricted fake* environment.
    #  In this prototype it is a simulation (no real UPI app is integrated), the
    #  banner is shown on purpose, and every decoy event is written to the local
    #  black box.  A production build must hide the banner entirely and be
    #  designed together with the bank/PSP.
    "decoy": {
        "emergency_pin": "9111",
        "decoy_balance": 1240.0,
        "decoy_transaction_limit": 500.0,
        "decoy_monthly_limit": 3000.0,
        "show_decoy_banner": True,
    },
    # ---- accessibility ----------------------------------------------------------
    "accessibility": {
        "language": "ta",
        "elder_mode": True,
        "voice": True,
        "font_scale": 1.25,
    },
    # ---- privacy -----------------------------------------------------------------
    "privacy": {
        "local_only": True,
        "store_raw_voice": False,
        "retention_days": 7,
    },
    # ---- AI engine ----------------------------------------------------------------
    "ai": {
        # "local"    = offline deterministic engine (default, no data leaves device)
        # "ollama"   = a model on the user's own machine via Ollama (still local)
        # "external" = optional hosted LLM for intent analysis (needs API key)
        "engine": "local",
        "external_timeout_s": 8,
        "ollama_model": "llama3.1:8b",
        "ollama_host": "http://127.0.0.1:11434",
        "ollama_timeout_s": 30,
    },
}

_NUMERIC = (int, float)


def default_config() -> Dict[str, Any]:
    """Return a deep copy of the factory configuration."""
    return copy.deepcopy(DEFAULT_CONFIG)


def merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``patch`` into ``base`` and return a new dict."""
    out = copy.deepcopy(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = value
    return out


def _num(value: Any) -> float:
    """Coerce to float; raise ValueError with a readable message."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a number here")
    if isinstance(value, _NUMERIC):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(f"not a number: {value!r}")


def _as_float_tree(node: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce numeric-looking strings to floats (judge panel text inputs)."""
    out: Dict[str, Any] = {}
    for key, value in node.items():
        if isinstance(value, dict):
            out[key] = _as_float_tree(value)
        elif isinstance(value, str):
            text = value.strip()
            try:
                out[key] = float(text)
            except ValueError:
                out[key] = text
        else:
            out[key] = value
    return out


def validate_config(cfg: Dict[str, Any]) -> List[str]:
    """Return a list of human-readable validation errors ([] means valid)."""
    errors: List[str] = []
    risk = cfg.get("risk", {})
    budget = cfg.get("budget", {})
    acc = cfg.get("accessibility", {})
    priv = cfg.get("privacy", {})

    def _check_range(name: str, value: Any, lo: float, hi: float) -> float:
        try:
            v = _num(value)
        except ValueError:
            errors.append(f"{name} must be a number (got {value!r})")
            return lo
        if not (lo <= v <= hi):
            errors.append(f"{name} must be between {lo:g} and {hi:g} (got {v:g})")
        return v

    for name in ("transaction_weight", "intent_weight", "beneficiary_weight"):
        _check_range(name, risk.get(name, 0), 0.0, 1.0)
    try:
        total = _num(risk.get("transaction_weight", 0)) + _num(
            risk.get("intent_weight", 0)
        ) + _num(risk.get("beneficiary_weight", 0))
        if abs(total - 1.0) > 1e-6:
            errors.append(
                "risk weights must sum to 1.0 (currently "
                f"{total:.4f}: transaction + intent + beneficiary)"
            )
    except ValueError:
        pass

    _check_range("anomaly_blend", risk.get("anomaly_blend", 0), 0.0, 1.0)
    contamination = _check_range(
        "anomaly_contamination", risk.get("anomaly_contamination", 0.05), 0.001, 0.5
    )
    n_est = risk.get("anomaly_n_estimators", 120)
    try:
        if int(n_est) < 10:
            errors.append("anomaly_n_estimators must be >= 10")
    except (TypeError, ValueError):
        errors.append("anomaly_n_estimators must be an integer >= 10")

    medium = _check_range("medium_threshold", risk.get("medium_threshold", 30), 0, 100)
    high = _check_range("high_threshold", risk.get("high_threshold", 55), 0, 100)
    critical = _check_range(
        "critical_threshold", risk.get("critical_threshold", 75), 0, 100
    )
    if not (medium < high < critical):
        errors.append(
            "thresholds must satisfy medium < high < critical "
            f"(got {medium:g} < {high:g} < {critical:g})"
        )
    _check_range("ask_intent_above", risk.get("ask_intent_above", 55), 0, 100)

    _check_range("budget.monthly_limit", budget.get("monthly_limit", 0), 0, 1e12)
    _check_range("budget.food_limit", budget.get("food_limit", 0), 0, 1e12)
    _check_range("budget.alert_at_percent", budget.get("alert_at_percent", 80), 1, 100)
    window = budget.get("forecast_window_days", 14)
    try:
        if not (3 <= int(window) <= 60):
            errors.append("budget.forecast_window_days must be between 3 and 60")
    except (TypeError, ValueError):
        errors.append("budget.forecast_window_days must be an integer")
    _check_range(
        "budget.seasonality_factor", budget.get("seasonality_factor", 1.0), 0.1, 5.0
    )

    if acc.get("language") not in SUPPORTED_LANGUAGES:
        errors.append(
            f"accessibility.language must be one of {list(SUPPORTED_LANGUAGES)}"
        )
    for flag in ("elder_mode", "voice", "local_only", "store_raw_voice"):
        if not isinstance(acc.get(flag, priv.get(flag)), bool):
            if flag in acc and not isinstance(acc.get(flag), bool):
                errors.append(f"accessibility.{flag} must be true/false")
            if flag in priv and not isinstance(priv.get(flag), bool):
                errors.append(f"privacy.{flag} must be true/false")
    try:
        if float(priv.get("retention_days", 7)) < 0:
            errors.append("privacy.retention_days must be >= 0")
    except (TypeError, ValueError):
        errors.append("privacy.retention_days must be a number >= 0")

    if cfg.get("ai", {}).get("engine") not in ("local", "ollama", "external"):
        errors.append("ai.engine must be 'local', 'ollama' or 'external'")
    for key, low, high in (("external_timeout_s", 1, 120), ("ollama_timeout_s", 1, 300)):
        value = cfg.get("ai", {}).get(key, 8)
        if not isinstance(value, _NUMERIC) or not low <= float(value) <= high:
            errors.append(f"ai.{key} must be a number between {low} and {high}")
    host = str(cfg.get("ai", {}).get("ollama_host", ""))
    if host and not host.startswith(("http://", "https://")):
        errors.append("ai.ollama_host must start with http:// or https://")

    # ---- spending triage map ----
    triage = budget.get("triage_map", {})
    if not isinstance(triage, dict):
        errors.append("budget.triage_map must be a mapping of category -> needs|wants|unnecessary")
    else:
        for category, bucket in triage.items():
            if bucket not in ("needs", "wants", "unnecessary"):
                errors.append(
                    f"budget.triage_map[{category}] must be needs, wants or unnecessary "
                    f"(got {bucket!r})"
                )

    # ---- emergency PIN / decoy ----
    decoy = cfg.get("decoy", {})
    pin_value = decoy.get("emergency_pin", "")
    if isinstance(pin_value, bool):
        pin_value = ""
    elif isinstance(pin_value, (int, float)):
        # the judge panel sends text, which _as_float_tree turns into a number
        pin_value = str(int(pin_value))
    pin = str(pin_value)
    if not (pin.isdigit() and 4 <= len(pin) <= 8):
        errors.append("decoy.emergency_pin must be 4-8 digits")
    for name in ("decoy_balance", "decoy_transaction_limit", "decoy_monthly_limit"):
        _check_range(f"decoy.{name}", decoy.get(name, 0), 0, 1e12)
    if not isinstance(decoy.get("show_decoy_banner"), bool):
        errors.append("decoy.show_decoy_banner must be true/false")

    return errors


def apply_config(
    current: Dict[str, Any], patch: Dict[str, Any]
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate-then-apply a configuration patch.

    Returns ``(new_config, errors)``.  When ``errors`` is non-empty the
    ``current`` configuration is returned unchanged.
    """
    coerced = _as_float_tree(patch or {})
    # a numeric PIN arrives as a float from the text inputs - keep it digits
    decoy_patch = (coerced.get("decoy") or {})
    pin = decoy_patch.get("emergency_pin")
    if isinstance(pin, float) and pin.is_integer():
        decoy_patch["emergency_pin"] = str(int(pin))
    candidate = merge(current, coerced)
    errors = validate_config(candidate)
    if errors:
        return current, errors
    return candidate, []


def risk_band(score: float, cfg: Dict[str, Any]) -> str:
    """Map a 0-100 risk score onto LOW / MEDIUM / HIGH / CRITICAL."""
    risk = cfg["risk"]
    if score >= float(risk["critical_threshold"]):
        return "CRITICAL"
    if score >= float(risk["high_threshold"]):
        return "HIGH"
    if score >= float(risk["medium_threshold"]):
        return "MEDIUM"
    return "LOW"
