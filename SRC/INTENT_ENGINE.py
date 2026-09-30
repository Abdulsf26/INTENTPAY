"""Intent engine: understand *why* the user says they are paying.

This is the product's core innovation.  Fraud systems ask "is this payment
suspicious?"; IntentPay asks "why are you paying?" and treats the answer as a
first-class risk signal.

Three engines, one interface:

* **LOCAL (default)** — a deterministic, offline, bilingual (English + Tamil)
  weighted lexicon over social-engineering families (urgency, authority
  impersonation, threats, secrecy, KYC framing, "safe account", lottery /
  investment, refund-QR collect-request pattern, fake customer care, OTP/PIN
  requests, job fees, family emergency).  Works with no internet and no API
  key, and always produces the same score for the same text.
* **OLLAMA (optional)** — a model that runs on the user's own machine via Ollama
  (https://ollama.com).  Nothing leaves the device.  The Judge panel detects the
  machine, recommends a model that fits, installs/starts/downloads it and proves
  the link works.  Falls back to the local engine on any failure.
* **EXTERNAL (optional)** — a hosted LLM call (Gemini) for colloquial text.
  Requires an API key in the environment, shows a visible "data leaves this
  computer" indicator, and *always* falls back to the local engine on any
  failure, timeout or malformed response.

Honest boundary: this is a decision-support signal, not proof of fraud.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
#  Weighted lexicon (English + Tamil)
# --------------------------------------------------------------------------- #

LEXICON: Dict[str, Dict[str, Any]] = {
    "URGENCY": {
        "weight": 0.90,
        "explanation_key": "expl_urgency",
        "phrases": [
            "immediately", "immediate", "urgent", "right now", "asap",
            "within 10 minutes", "within 15 minutes", "today itself",
            "without delay", "hurry", "last warning", "final notice",
            "before the call ends", "at once", "do it now",
            "உடனே அனுப்ப", "உடனடியாக", "விரைவில்", "இப்போதே", "தாமதிக்காதே",
            "இன்றே", "கால் மணி நேரத்தில்", "சீக்கிரமாக",
        ],
    },
    "AUTHORITY": {
        "weight": 1.00,
        "explanation_key": "expl_authority",
        "phrases": [
            "bank manager", "bank officer", "rbi", "reserve bank", "police",
            "cbi", "customs", "income tax", "enforcement directorate",
            "cyber cell", "trai", "government", "magistrate", "judge",
            "court", "arrest warrant", "fir", "case registered", "fir registered",
            "digital arrest", " investigation ", "investigation team",
            "bank official", "branch manager", "from the bank",
            "நீதிபதி", "நீதிமன்றம்", "காவல்", "சைபர்", "வரித்துறை", "அரசு",
            "கைது", "ஆய்வு", "வங்கி அதிகாரி", "வங்கி மக்கள்", "வங்கி ஊழியர்",
            "வங்கியில் இருந்து", "வங்கி நிருபர்", "ரிசர்வ் வங்கி", "அரசு அதிகாரி",
            "காவல் துறை", "வங்கி சொல்", "வங்கி கூற",
        ],
    },
    "THREAT": {
        "weight": 1.00,
        "explanation_key": "expl_threat",
        "phrases": [
            "arrest", "jail", "prison", "custody", "account will be blocked",
            "account blocked", "account frozen", "freeze", "penalty", "fine",
            "legal action", " suo moto", "arrested", "police will come",
            "will be arrested", "blocked permanently", "case against you",
            "கைது", "செல்", "கணக்கு முடக்கம்", "அபராதம்", "சட்ட நடவடிக்கை",
            "கணக்கு முட்டு", "வழக்கு", "செல்ல வைப்பார்கள்",
        ],
    },
    "SECRECY": {
        "weight": 0.95,
        "explanation_key": "expl_secrecy",
        "phrases": [
            "don't tell anyone", "do not tell anyone", "don't tell your family",
            "don't tell your son", "don't tell your daughter", "dont disconnect",
            "don't disconnect", "stay on the call", "video call", "screen share",
            "anydesk", "teamviewer", "quick support", "whatsapp video",
            "keep this between us", "don't hang up", "do not hang up",
            "யாருடனும் சொல்லாதே", "யாரிடமும் சொல்லாதே", "காலை விடாதே",
            "வீடியோ கால்", "திரையை பகிர", "இதை ரகசியமாக வை", "மறை",
        ],
    },
    "VERIFICATION": {
        "weight": 0.80,
        "explanation_key": "expl_verification",
        "phrases": [
            "to verify", "verification", "kyc", "re-kyc", "update kyc",
            "aadhaar link", "link aadhaar", "account suspended", "pan card",
            "sim will be blocked", "re-verification", "kyc update", "e-kyc",
            "சரிபார்ப்பு", "கேஒய்சி", "ஆதார்", "சிம் முடக்கம்", "கணக்கு நிறுத்தம்",
        ],
    },
    "SAFE_ACCOUNT": {
        "weight": 0.90,
        "explanation_key": "expl_safe_account",
        "phrases": [
            "safe account", "hold account", "secure account", "government account",
            "rbi account", "designated account", "deposit to keep money safe",
            "safe custody", "keep the money safe", "send to this account for safe",
            "பாதுகாப்பான கணக்கு", "அரசு கணக்கு", "பாதுகாக கணக்கு",
            "பணத்தை பாதுகாக", "பாதுகாப்பு கணக்கு",
        ],
    },
    "LOTTERY": {
        "weight": 0.90,
        "explanation_key": "expl_lottery",
        "phrases": [
            "lottery", "prize", "jackpot", "double your money", "investment",
            "trading", "crypto", "bitcoin", "guaranteed returns", "click this link",
            "processing fee for prize", "lottery tax", "lucky draw", "spin and win",
            "invest and get", "double returns", "high returns", "fixed returns",
            "profit sharing", "trading app", "invest in",
            "லாட்டரி", "பரிசு", "இரட்டிப்பு", "முதலீடு", "கிரிப்டோ",
            "லாபம்", "பங்கு சந்தை", "அதிக லாபம்", "உறுதி லாபம்",
        ],
    },
    "REFUND_QR": {
        "weight": 0.85,
        "explanation_key": "expl_refund_qr",
        "phrases": [
            "scan to receive", "scan the qr to receive", "scan this qr",
            "receive money", "refund", "cashback pending", "scan qr for refund",
            "enter pin to receive", "approve to receive", "scan to get money",
            "collect request", "money will be credited",
            "பணம் பெற ஸ்கேன்", "பணத்தை பெற", "பணம் திரும்ப பெற",
            "ரீஃபண்டு பெற", "கியூஆர் ஸ்கேன் செய்து பணம் பெற", "ரீஃபண்ட்", "ரிஃபண்ட்",
            "கேஷ்பேக்",
            "பணம் வரவு வைக்க", "கூட்டு கோரிக்கை",
        ],
    },
    "DELIVERY_SUPPORT": {
        "weight": 0.70,
        "explanation_key": "expl_delivery_support",
        "phrases": [
            "customer care", "delivery", "courier", "parcel", "electricity",
            "meter", "recharge offer", "support team", "apk", "app update",
            "remote access", "customer service", "fake electricity",
            "கஸ்டமர் கேர்", "டெலிவரி", "பார்சல்", "மீட்டர்", "மின்சாரம்",
            "ரீசார்ஜ் ஆஃபர்", "ஆப் புதுப்பிப்பு",
        ],
    },
    "OTP_PIN": {
        "weight": 0.90,
        "explanation_key": "expl_otp_pin",
        "phrases": [
            "share otp", "send otp", "tell me the otp", "upi pin", "cvv",
            "card number", "debit card", "password", "otp", "one time password",
            "share the pin", "pin to receive",
            "ஓடிபி", "பின்", "கார்டு எண்", "கடவுச்சொல்",
        ],
    },
    "JOB_FEE": {
        "weight": 0.75,
        "explanation_key": "expl_job_fee",
        "phrases": [
            "job offer", "placement", "registration fee", "training fee",
            "offer letter", "work from home job", "data entry job",
            "part time job", "joining fee", "job registration",
            "வேலை வாய்ப்பு", "பதிவு கட்டணம்", "பயிற்சி கட்டணம்",
            "வேலை நிருபர்", "வீட்டில் வேலை",
        ],
    },
    "FAMILY_EMERGENCY": {
        "weight": 0.50,
        "explanation_key": "expl_family_emergency",
        "phrases": [
            "hospital", "accident", "emergency", "operation", "my son",
            "my daughter", "mother needs", "father needs", " admitted ",
            "surgery", "icu", "blood donation", "brother needs",
            "மருத்துவமனை", "விபத்து", "அவசரம்", "அறுவை சிகிச்சை", "மகன்",
            "மகள்", "அம்மாவுக்கு", "அப்பாவுக்கு", "சகோதரருக்கு", "இதய அதிர்வு",
        ],
    },
}

# Roots are matched as substrings, which is how Tamil actually works: the verb
# stem is stable while the ending changes with politeness and tense
# ("அனுப்புங்கள்" / "அனுப்ப வேண்டும்" / "அனுப்பினார்").  A root match counts
# for less than an exact phrase, so it can only complete - never inflate - a
# family score.
ROOTS: Dict[str, List[str]] = {
    "URGENCY": ["உடன", "விரைவ", "இப்போத", "சீக்கிர", "தாமத", "immediat",
                "urgent", "asap", "hurry", "at once", "last warning",
                "final notice"],
    "AUTHORITY": ["அதிகாரி", "காவல்", "நீதிபதி", "நீதிமன்ற", "சைபர்",
                  "வரித்துறை", "அரசு", "கைது", "ஆய்வாளர்", "வங்கி", "ரிசர்வ்",
                  "bank manager", "bank officer", "rbi", "police", "cbi",
                  "customs", "income tax", "enforcement", "magistrate", "judge",
                  "arrest warrant", "official", "government"],
    "THREAT": ["முடக்கம்", "அபராதம்", "சட்ட", "செல்ல வை", "வழக்கு", "arrest",
               "jail", "prison", "custody", "blocked", "frozen", "freeze",
               "penalty", "legal action", "case against"],
    "SECRECY": ["யாரிடமும்", "யாருடனும்", "சொல்லாதே", "காலை விடாதே", "வீடியோ",
                "திரையை பகிர", "ரகசிய", "don't tell", "do not tell",
                "don't hang up", "do not hang up", "video call", "screen share",
                "anydesk", "teamviewer", "stay on the call"],
    "VERIFICATION": ["சரிபார்ப்பு", "கேஒய்சி", "ஆதார்", "சிம்", "verif", "kyc",
                     "aadhaar", "pan card", "suspended", "re-verification"],
    "SAFE_ACCOUNT": ["பாதுகாப்பான கணக்கு", "பாதுகாக", "அரசு கணக்கு",
                     "safe account", "secure account", "designated account",
                     "keep the money safe", "safe custody", "hold account"],
    "LOTTERY": ["லாட்டரி", "பரிசு", "இரட்டிப்பு", "முதலீடு", "லாபம்",
                "கிரிப்டோ", "பங்கு", "lottery", "prize", "jackpot", "double",
                "invest", "trading", "crypto", "bitcoin", "guaranteed",
                "returns", "profit", "lucky draw"],
    "REFUND_QR": ["பணம் பெற", "பணத்தை பெற", "திரும்ப பெற", "திரும்பப் பெற",
                  "பணம் திரும்ப", "ரீஃபண்ட்", "ரிஃபண்ட்", "கேஷ்பேக்", "வரவு வைக்க",
                  "scan to receive", "scan this qr", "scan the qr", "receive money",
                  "refund", "cashback", "enter pin to receive", "approve to receive",
                  "collect request"],
    "DELIVERY_SUPPORT": ["கஸ்டமர் கேர்", "டெலிவரி", "பார்சல்", "மீட்டர்",
                         "மின்சாரம்", "ரீசார்ஜ்", "customer care", "delivery",
                         "courier", "parcel", "electricity", "meter", "apk",
                         "remote access", "customer service"],
    "OTP_PIN": ["ஓடிபி", "பின்", "கார்டு எண்", "கடவுச்சொல்", "share otp",
                "send otp", "upi pin", "cvv", "card number", "password", "otp"],
    "JOB_FEE": ["வேலை வாய்ப்பு", "பதிவு கட்டணம்", "பயிற்சி கட்டணம்", "நிருபர்",
                "job offer", "placement", "registration fee", "training fee",
                "offer letter", "work from home", "data entry", "joining fee"],
    "FAMILY_EMERGENCY": ["மருத்துவமனை", "விபத்து", "அவசரம்", "அறுவை", "மகன்",
                         "மகள்", "அம்மா", "அப்பா", "சகோதர", "hospital",
                         "accident", "emergency", "operation", "my son",
                         "my daughter", "admitted", "surgery", "icu"],
}

BENIGN_PHRASES = [
    "rent", "groceries", "grocery", "medical bill", "hospital bill",
    "school fee", "college fee", "salary", "milk", "vegetables",
    "electricity bill", "mobile recharge", "water bill", "gas cylinder",
    "house rent", "monthly rent", "fee payment", "bill payment",
    "வாடிக்கை", "மளிகை", "பள்ளி கட்டணம்", "கல்லூரி கட்டணம்", "சலூன்",
    "மருத்துவ கட்டணம்", "மின்சார கட்டணம்", "தண்ணீர் கட்டணம்",
    "மொபைல் ரீசார்ஜ்", "எரிவாயு", "அரிசி", "சர்க்கரை", "வீட்டு செலவு",
]

# combination bonuses: (family_a, family_b, bonus)
COMBINATION_BONUSES = [
    (("AUTHORITY", "THREAT"), 8.0, "authority + threat"),
    (("AUTHORITY", "SECRECY"), 8.0, "authority + secrecy"),
    (("URGENCY", "THREAT"), 6.0, "urgency + threat"),
    (("SAFE_ACCOUNT", "AUTHORITY"), 8.0, "safe-account + authority"),
    (("REFUND_QR", "OTP_PIN"), 8.0, "refund-QR + OTP/PIN"),
    (("URGENCY", "AUTHORITY"), 8.0, "urgency + authority"),
    (("URGENCY", "SAFE_ACCOUNT"), 6.0, "urgency + safe-account"),
    (("VERIFICATION", "URGENCY"), 6.0, "KYC framing + urgency"),
]


# Tamil vowel signs (U+0BBE-U+0BCD, the virama included).  A virama directly
# before a vowel sign is never valid Tamil - it is a typing artefact
# ("ரீஃபண்டுக்காக" typed as ரீஃஃபண்டு + க்காக), and it makes exact phrase
# matching fail.  Dropping it keeps real consonant clusters ("ண்ட") intact.
_TAMIL_VOWEL = "[\u0bbe-\u0bcd]"


def _normalise(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub("\u0bcd(?=" + _TAMIL_VOWEL + ")", "", text)
    return f" {text.strip()} "


def score_intent_local(text: Optional[str]) -> Dict[str, Any]:
    """Deterministic weighted-lexicon scoring of a stated reason."""
    if text is None or not str(text).strip():
        return {
            "risk": None,
            "unknown": True,
            "matched": [],
            "bonus": [],
            "benign": False,
            "engine": "local",
            "fallback": False,
            "note": "no reason provided",
        }
    norm = _normalise(str(text))
    matched: List[Dict[str, Any]] = []
    for family, spec in LEXICON.items():
        hits = [p for p in spec["phrases"] if p in norm]
        # Tamil and English both inflect: a stem ("அனுப்ப") is stable while the
        # ending changes with politeness and tense, so root hits are matched as
        # substrings and count for less than an exact phrase.
        # roots are matched virama-insensitively: Tamil writers drop or keep the
        # dead consonant freely ("ரீஃபண்ட்" vs "ரீஃபண்டுக்காக")
        root_hits = [
            r for r in ROOTS.get(family, [])
            if r in norm or r.replace("\u0bcd", "") in norm.replace("\u0bcd", "")
        ]
        if not hits and not root_hits:
            continue
        phrase_factor = min(len(hits), 2) / 2.0 if hits else 0.0
        root_factor = min(1.0, 0.5 * len(root_hits)) if root_hits else 0.0
        factor = max(phrase_factor, root_factor)
        matched.append(
            {
                "family": family,
                "weight": spec["weight"],
                "factor": factor,
                "phrases": hits[:4],
                "roots": root_hits[:4],
                "explanation_key": spec["explanation_key"],
            }
        )

    benign = any(p in norm for p in BENIGN_PHRASES)
    high_severity = [m for m in matched if m["weight"] >= 0.8]

    if not matched:
        risk = 8.0 if benign else 18.0
        return {
            "risk": round(risk, 1),
            "unknown": False,
            "matched": [],
            "bonus": [],
            "benign": benign,
            "engine": "local",
            "fallback": False,
            "note": "no social-engineering patterns found",
        }

    raw = sum(m["weight"] * m["factor"] for m in matched)
    bonus: List[Dict[str, Any]] = []
    for (fam_a, fam_b), amount, label in COMBINATION_BONUSES:
        families = {m["family"] for m in matched}
        if fam_a in families and fam_b in families:
            bonus.append({"label": label, "amount": amount})
    score = 100.0 * min(1.0, raw) + sum(b["amount"] for b in bonus)
    # a clearly benign reason with no high-severity family should not scream
    if benign and not high_severity:
        score *= 0.55
    score = max(0.0, min(100.0, score))
    return {
        "risk": round(score, 1),
        "unknown": False,
        "matched": matched,
        "bonus": bonus,
        "benign": benign,
        "engine": "local",
        "fallback": False,
        "note": "weighted bilingual lexicon",
    }


# --------------------------------------------------------------------------- #
#  Optional external engine (Gemini) with hard fallback to local
# --------------------------------------------------------------------------- #

_EXTERNAL_PROMPT = """You are a payment-fraud social-engineering analyst for India.
Read the user's stated reason for a payment and return ONLY compact JSON:
{{"risk": <0-100 number>, "signals": [<short english labels>], "explanation": "<one short sentence>"}}
risk = likelihood that the payer is being manipulated into paying (urgency, authority impersonation, threats, secrecy, safe-account, lottery, refund-QR, OTP requests).
Reason: "{text}"
"""


def _external_available(cfg: Dict[str, Any]) -> bool:
    if cfg.get("privacy", {}).get("local_only", True):
        return False
    if cfg.get("ai", {}).get("engine", "local") != "external":
        return False
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("INTENTPAY_LLM_KEY"))


def score_intent_external(text: Optional[str], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Try the hosted LLM; on ANY problem fall back to the local engine."""
    local = score_intent_local(text)
    if text is None or not str(text).strip():
        return local
    if not _external_available(cfg):
        local["fallback"] = True
        local["note"] = "external AI unavailable — local engine used"
        return local
    try:  # pragma: no cover - network path, exercised manually with a key
        import requests

        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("INTENTPAY_LLM_KEY")
        timeout = float(cfg.get("ai", {}).get("external_timeout_s", 8))
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={key}"
        )
        payload = {
            "contents": [{"parts": [{"text": _EXTERNAL_PROMPT.format(text=text)}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200},
        }
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r"\{.*\}", content, re.S)
        parsed = json.loads(match.group(0) if match else content)
        risk = float(parsed.get("risk", 0))
        risk = max(0.0, min(100.0, risk))
        signals = [str(s) for s in parsed.get("signals", [])][:6]
        explanation = str(parsed.get("explanation", ""))[:200]
        return {
            "risk": round(risk, 1),
            "unknown": False,
            "matched": [
                {
                    "family": "EXTERNAL",
                    "weight": 1.0,
                    "factor": 1.0,
                    "phrases": signals,
                    "explanation_key": "expl_authority" if not signals else None,
                }
            ],
            "bonus": [],
            "benign": local["benign"],
            "engine": "external",
            "fallback": False,
            "note": explanation or "external LLM analysis",
        }
    except Exception as exc:  # noqa: BLE001 - never let AI break the payment flow
        local["fallback"] = True
        local["note"] = f"external AI failed ({type(exc).__name__}) — local engine used"
        return local


def score_intent_ollama(text: Optional[str], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the local Ollama model; on ANY problem fall back to the local engine.

    The prompt and the JSON contract are the same ones the hosted engine uses, so
    both are interchangeable and both are bounded: risk is clamped to 0-100 and at
    most six signals are kept.
    """
    local = score_intent_local(text)
    if text is None or not str(text).strip():
        return local
    if (cfg.get("ai", {}) or {}).get("engine") != "ollama":
        local["fallback"] = True
        local["note"] = "Ollama engine not selected — local engine used"
        return local
    try:  # pragma: no cover - needs a local Ollama server
        from SRC import LOCAL_LLM

        status = LOCAL_LLM.ollama_ready(cfg)
        if not status["linked"]:
            local["fallback"] = True
            local["note"] = ("local model not linked "
                             f"({status['installed_detail'] if not status['installed'] else 'server not running'}) "
                             "— local engine used")
            return local
        ok, parsed, detail = LOCAL_LLM.ollama_generate_json(_EXTERNAL_PROMPT.format(text=text), cfg)
        if not ok:
            local["fallback"] = True
            local["note"] = f"local model failed ({detail}) — local engine used"
            return local
        risk = float(parsed.get("risk", 0) or 0)
        risk = max(0.0, min(100.0, risk))
        signals = [str(s) for s in parsed.get("signals", [])][:6]
        explanation = str(parsed.get("explanation", ""))[:200]
        return {
            "risk": round(risk, 1),
            "unknown": False,
            "matched": [
                {
                    "family": "OLLAMA",
                    "weight": 1.0,
                    "factor": 1.0,
                    "phrases": signals,
                    "explanation_key": "expl_authority" if not signals else None,
                }
            ],
            "bonus": [],
            "benign": local["benign"],
            "engine": "ollama",
            "fallback": False,
            "note": explanation or "local Ollama model analysis",
        }
    except Exception as exc:  # noqa: BLE001 - never let AI break the payment flow
        local["fallback"] = True
        local["note"] = f"local model failed ({type(exc).__name__}) — local engine used"
        return local


def score_intent(text: Optional[str], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Unified entry point used by the risk engine."""
    engine = str((cfg.get("ai", {}) or {}).get("engine", "local"))
    if engine == "ollama":
        return score_intent_ollama(text, cfg)
    return score_intent_external(text, cfg)
