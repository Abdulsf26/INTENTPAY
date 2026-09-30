"""Payment-flow orchestration: draft -> evaluate -> intent -> decision ->
simulated handoff -> commit.

The simulator is a *concept* handoff: it produces the same UPI deep link a
real app would hand to the phone's UPI app, plus a deterministic demo UTR.
No money moves, no PIN/OTP is ever involved.
"""
from __future__ import annotations

import copy
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from SRC import BUDGET as budget_engine
from SRC import DATA_LOADER as data_loader
from SRC.DATA_LOADER import append_transaction, history_to_frame
from SRC.BLACKBOX import BlackBox
from SRC.MODELS import CustomerProfile, PaymentRequest, Transaction, make_utr
from SRC.RISK_ENGINE import evaluate_payment

CITY_COORDS = {
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Bengaluru": (12.9716, 77.5946),
}


class PaymentFlow:
    """Stateful pre-payment conversation for one session."""

    def __init__(self) -> None:
        self.payment: Optional[PaymentRequest] = None
        self.result: Optional[Any] = None
        self.state: str = "IDLE"  # IDLE | EVALUATED | DECIDED | COMMITTED | HELP
        self.decision: Optional[str] = None
        self.committed_transaction: Optional[Transaction] = None
        self.handoff: Optional[Dict[str, Any]] = None
        self.events: List[Dict[str, Any]] = []
        # tamper-evident record of everything that happened around this payment
        self.blackbox = BlackBox()
        self.decoy_mode: bool = False
        self.decoy_log: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------- build --
    @staticmethod
    def payment_from_values(values: Dict[str, Any], profile: CustomerProfile) -> PaymentRequest:
        """Build a PaymentRequest from simulator form values."""
        when = values.get("timestamp") or datetime.now()
        if isinstance(when, str):
            when = datetime.fromisoformat(when)
        city = values.get("city") or profile.usual_city
        lat, lon = CITY_COORDS.get(city, (profile.usual_lat, profile.usual_lon))
        if values.get("lat") is not None and values.get("lon") is not None:
            lat, lon = float(values["lat"]), float(values["lon"])
        intent = values.get("intent_text")
        return PaymentRequest(
            amount=float(values.get("amount") or 0.0),
            method=values.get("method", "UPI"),
            payee_name=str(values.get("payee_name", "") or ""),
            payee_upi=str(values.get("payee_upi", "") or ""),
            purpose_category=str(values.get("purpose_category", "OTHER") or "OTHER"),
            timestamp=when,
            city=city,
            lat=lat,
            lon=lon,
            on_call=bool(values.get("on_call", False)),
            call_duration_s=int(values.get("call_duration_s") or 0),
            channel=str(values.get("channel", "P2P") or "P2P"),
            new_payee=bool(values.get("new_payee", False)),
            device_id=str(values.get("device_id", "") or ""),
            battery_pct=int(values.get("battery_pct") or 85),
            intent_text=(str(intent) if intent is not None else None),
            note=str(values.get("note", "") or ""),
        )

    # ------------------------------------------------------------- evaluate --
    def evaluate(
        self,
        payment: PaymentRequest,
        history: pd.DataFrame,
        profile: CustomerProfile,
        cfg: Dict[str, Any],
        corrections: Optional[Dict[str, str]] = None,
    ) -> Any:
        started = time.perf_counter()
        result = evaluate_payment(
            payment, history, profile, cfg,
            corrections=corrections,
            payee_reports=data_loader.payee_reports(payment.payee_upi),
        )
        self.payment = payment
        self.result = result
        self.state = "EVALUATED"
        self.decision = None
        self.events.append(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "evaluated",
                "amount": payment.amount,
                "payee": payment.payee_name,
                "score": result.fraud_risk,
                "band": result.band,
                "wall_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )
        self._record(
            "payment_drafted",
            {"amount": payment.amount, "payee": payment.payee_name,
             "payee_upi": payment.payee_upi, "channel": payment.channel,
             "method": payment.method,
             "when": payment.resolved_timestamp().isoformat(timespec="minutes")},
        )
        self._record(
            "risk_analysed",
            {"amount": payment.amount, "payee": payment.payee_name, "score": result.fraud_risk,
             "band": result.band, "transaction_risk": result.transaction_risk,
             "intent_risk": result.intent_risk, "recipient_risk": result.recipient_risk,
             "wall_ms": round((time.perf_counter() - started) * 1000, 1)},
        )
        if result.intent_requested:
            self._record("intent_requested", {"reason": "preliminary score crossed the threshold",
                                              "ask_above": None})
        return result

    def _record(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Append one event to the black box and to the legacy event list."""
        entry = self.blackbox.append(event, payload)
        self.events.append({"ts": entry["ts"], "event": event, **payload})
        return entry

    def record_intent(self, reason: str) -> None:
        """Called after the user types their reason (black-box evidence)."""
        self._record("intent_provided", {"reason": reason})

    def record_warning(self) -> None:
        """Called when a HIGH/CRITICAL warning is shown on screen."""
        if self.result is None:
            return
        if any(e["event"] == "warning_shown" for e in self.blackbox.entries):
            return
        self._record("warning_shown", {"band": self.result.band,
                                       "score": self.result.fraud_risk})

    def record_incident(self) -> None:
        """Called from the scam-help page: the user reports this payment."""
        self._record("incident_reported",
                     {"amount": self.payment.amount if self.payment else None,
                      "utr": self.result.utr if self.result else None})

    # -------------------------------------------------------------- decide ---
    def decide(self, decision: str) -> Dict[str, Any]:
        if self.result is None or self.payment is None:
            return {"ok": False, "error": "nothing to decide"}
        self.decision = decision
        self.state = "DECIDED" if decision != "HELP" else "HELP"
        self._record("user_confirmed", {"decision": decision,
                                        "amount": self.payment.amount,
                                        "payee": self.payment.payee_name,
                                        "score": self.result.fraud_risk,
                                        "band": self.result.band})
        return {"ok": True, "decision": decision}

    # ------------------------------------------------------------- decoy ----
    def check_pin(self, pin: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency-PIN check.

        The emergency PIN is a duress feature: entering it opens a *restricted
        fake* environment instead of the real one.  This prototype simulates that
        environment (no real UPI app is integrated) and records a silent alert in
        the black box.
        """
        expected = str((cfg.get("decoy", {}) or {}).get("emergency_pin", ""))
        if not expected or str(pin).strip() != expected:
            return {"decoy": False, "error": "wrong_pin"}
        self.decoy_mode = True
        self._record("decoy_activated",
                     {"detail": "emergency PIN accepted - restricted environment opened"})
        self._record("silent_alert",
                     {"detail": "duress signal recorded locally; a production build would "
                                "notify a trusted contact / helpline without alerting the "
                                "person holding the phone"})
        return {"decoy": True}

    def decoy_payment(self, amount: float, payee: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a payment inside the restricted environment.

        Enforces the decoy limits set in the Judge Panel: a transaction limit of
        zero means nothing is ever 'transferred', and any amount above the limit
        is refused with the same message a real limit would produce.
        """
        decoy_cfg = cfg.get("decoy", {}) or {}
        limit = float(decoy_cfg.get("decoy_transaction_limit", 0.0) or 0.0)
        amount = float(amount or 0.0)
        if limit <= 0.0:
            outcome = {"ok": False, "blocked": True, "reason": "limit_zero",
                       "message_en": "Transaction limit is set to zero - no amount can be "
                                     "transferred in this mode.",
                       "message_ta": "பரிவர்த்தனை வரம்பு பூஜ்யமாக உள்ளது - இந்த பயன்முறையில் "
                                     "எந்தத் தொகையும் மாற்ற முடியாது."}
        elif amount > limit:
            outcome = {"ok": False, "blocked": True, "reason": "over_limit",
                       "message_en": f"Amount is above the ₹{limit:,.0f} limit set for this mode.",
                       "message_ta": f"இந்த பயன்முறைக்கான ₹{limit:,.0f} வரம்பைத் தாண்டிய தொகை."}
        else:
            outcome = {"ok": True, "blocked": False, "reason": "simulated",
                       "message_en": "Payment Successful (simulated - no real money moved).",
                       "message_ta": "பேமெண்ட் வெற்றி (உருவகப்படுத்தப்பட்டது - உண்மையான பணம் "
                                     "நகரவில்லை).",
                       "utr": make_utr("decoy", amount, payee)}
        self.decoy_log.append({"amount": amount, "payee": payee, **outcome})
        self._record("payment_simulated",
                     {"amount": amount, "payee": payee, "decoy": True, **outcome})
        return outcome

    # -------------------------------------------------------------- commit ---
    def commit(
        self, history: pd.DataFrame, profile: CustomerProfile
    ) -> Tuple[pd.DataFrame, Transaction, Dict[str, Any]]:
        """Approve: build the transaction + simulated UPI handoff."""
        if self.result is None or self.payment is None:
            raise RuntimeError("no evaluated payment to commit")
        payment = self.payment
        now = payment.resolved_timestamp()
        utr = self.result.utr
        txn = Transaction(
            id=f"{profile.customer_id}-{now.strftime('%Y%m%d%H%M%S')}",
            timestamp=now,
            amount=float(payment.amount),
            direction="DEBIT",
            merchant_label=payment.payee_name or payment.note or "demo payee",
            upi_id=payment.payee_upi,
            source="simulator",
            category=self.result.category,
            category_confidence=self.result.category_confidence,
            essential_flag=(self.result.category in ("FOOD", "HEALTH", "ESSENTIALS", "EDUCATION")),
            self_transfer=self.result.self_transfer,
            note=payment.intent_text or "",
            utr=utr,
        )
        new_history = append_transaction(history, txn)
        handoff = {
            "upi_uri": (
                f"upi://pay?pa={payment.payee_upi}&pn={payment.payee_name}"
                f"&am={payment.amount:.2f}&cu=INR&tn=IntentPay-demo"
            ),
            "utr": utr,
            "qr": True,
            "note_en": (
                "Concept handoff: in a production app this deep link opens the "
                "user's UPI app for PIN entry. This prototype never asks for a "
                "PIN and never moves money."
            ),
            "note_ta": (
                "கருத்து Handoff: உண்மையான ஆப்பில் இந்த லிங்க் UPI ஆப்பைத் திறக்கும். "
                "இந்த டெமோ PIN கேட்காது, பணம் நகர்த்தாது."
            ),
        }
        self.handoff = handoff
        self.committed_transaction = txn
        self.state = "COMMITTED"
        self._record("payment_simulated",
                     {"amount": payment.amount, "payee": payment.payee_name, "utr": utr,
                      "decoy": False, "summary": f"₹{payment.amount:,.0f} simulated to "
                                                 f"{payment.payee_name}"})
        return new_history, txn, handoff


def evaluate_scenario(
    scenario: Dict[str, Any],
    history: pd.DataFrame,
    profile: CustomerProfile,
    cfg: Dict[str, Any],
    corrections: Optional[Dict[str, str]] = None,
) -> Any:
    """Evaluate one scenario payload (used by the golden demo + metrics)."""
    flow = PaymentFlow()
    payment = flow.payment_from_values(copy.deepcopy(scenario), profile)
    return flow.evaluate(payment, history, profile, cfg, corrections)


def golden_demo(
    history: pd.DataFrame, profile: CustomerProfile, cfg: Dict[str, Any],
    corrections: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Same amount, two stories: ordinary reason vs. coerced reason."""
    from SRC import DATA_LOADER as dl

    pair = dl.golden_pair()
    ordinary = evaluate_scenario(pair["ordinary"], history, profile, cfg, corrections)
    coerced = evaluate_scenario(pair["coerced"], history, profile, cfg, corrections)
    return {
        "ordinary": ordinary,
        "coerced": coerced,
        "delta": round(coerced.fraud_risk - ordinary.fraud_risk, 1),
    }


def upi_uri(payment: PaymentRequest) -> str:
    return (
        f"upi://pay?pa={payment.payee_upi}&pn={payment.payee_name}"
        f"&am={payment.amount:.2f}&cu=INR&tn=IntentPay-demo"
    )


def qr_png_bytes(uri: str) -> Optional[bytes]:
    """Real QR code bytes for the UPI deep link (optional dependency)."""
    try:
        import io

        import qrcode

        image = qrcode.make(uri, box_size=6, border=1)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:  # noqa: BLE001 - QR is a nice-to-have, never a blocker
        return None


def answer_voice_query(
    query: str, history: pd.DataFrame, profile: CustomerProfile, cfg: Dict[str, Any],
    last_result: Optional[Any] = None,
) -> Dict[str, Any]:
    """Answer simple voice questions about money and risk (EN + TA)."""
    from SRC.LANGUAGE import category_label, t
    from SRC.MODELS import inr

    text = (query or "").lower()
    now = datetime.now()
    limit = float(cfg["budget"]["monthly_limit"])
    spent = budget_engine.month_spend(history, now)
    remaining = limit - spent
    lang = cfg.get("accessibility", {}).get("language", "en")

    def _finish(key: str, **kwargs: Any) -> Dict[str, Any]:
        return {"key": key, "text": t(key, lang, **kwargs), "lang": lang}

    if any(w in text for w in ["spend", "spent", "செலவ", "எவ்வளவு ஆயிறது"]):
        return _finish("voice_answer_total", spent=inr(spent), budget=inr(limit), remaining=inr(max(remaining, 0)))
    if any(w in text for w in ["left", "remain", "மீத", "மீதம்"]):
        return _finish("voice_answer_remaining", remaining=inr(max(remaining, 0)), budget=inr(limit))
    if any(w in text for w in ["food", "grocer", "உணவ"]):
        cat = budget_engine.category_spend(history, now).get("FOOD", 0.0)
        return _finish("voice_answer_category", category=category_label("FOOD", lang), spent=inr(cat))
    if any(w in text for w in ["why", "risk", "ஏன்", "ஆபத்த"]):
        if last_result is not None:
            signals = ", ".join(
                item["text_en"] for item in (last_result.explanation or [])[:3]
            ) or "no strong signals"
            return _finish("voice_answer_why", signals=signals)
        return _finish("voice_help")
    return _finish("voice_help")
