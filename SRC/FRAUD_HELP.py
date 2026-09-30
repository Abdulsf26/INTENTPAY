"""Post-scam guidance: what to do when a payment has already gone wrong.

Honest by design: this module cannot and does not claim to reverse a completed
UPI payment.  It guides the user to the real remedies (1930 helpline,
cybercrime.gov.in, bank dispute) inside the golden hour, and produces a
copy-ready complaint draft.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from SRC.LANGUAGE import t


def help_steps(lang: str = "en") -> List[str]:
    return [t(f"help_step{i}", lang) for i in range(1, 6)]


def complaint_draft(payment: Any, result: Any, profile: Any, lang: str = "en") -> str:
    """Copy-ready draft the user can paste into the cybercrime portal."""
    when = payment.resolved_timestamp().strftime("%d-%m-%Y %H:%M")
    payee = payment.payee_name or "(unknown)"
    upi = payment.payee_upi or "(unknown)"
    utr = getattr(result, "utr", "") or "(pending)"
    reason = payment.intent_text or "(not stated)"
    if lang == "ta":
        return (
            "சைபர் கிரைம் புகார் (வரைவு)\n"
            f"தேதி/நேரம்: {when}\n"
            f"தொகை: ₹{payment.amount:.2f}\n"
            f"பெறுபவர்: {payee} ({upi})\n"
            f"பரிவர்த்தனை குறிப்பு (UTR): {utr}\n"
            f"சொன்ன காரணம்: {reason}\n"
            "நடப்பு: பணம் அனுப்பப்பட்டது; உடனடியாக கணக்கு உறைக்க வேண்டும்.\n"
            "வாடிக்கையாளர்: (பெயர் / கைபேசி எண் / வங்கி கணக்கு)\n"
        )
    return (
        "Cyber-crime complaint (draft)\n"
        f"Date/time: {when}\n"
        f"Amount: INR {payment.amount:.2f}\n"
        f"Recipient: {payee} ({upi})\n"
        f"Transaction reference (UTR): {utr}\n"
        f"Reason given at payment time: {reason}\n"
        "Request: immediate freeze of the beneficiary account and dispute "
        "registration with the remitter bank.\n"
        "Customer: (name / phone / bank account)\n"
    )


def golden_hour_note(lang: str = "en") -> str:
    return t("help_note", lang)
