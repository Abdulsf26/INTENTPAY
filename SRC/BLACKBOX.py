"""UPI Black Box: a tamper-evident timeline of the events around a payment.

The idea, borrowed from an aircraft's flight recorder: a payment app answers
"did my payment succeed?", but when something goes wrong the user needs
"what happened *around* this payment, why was it flagged, what did I confirm,
and what evidence do I have?".

This module records the important events only - never the full history - as a
hash chain: every entry stores the SHA-256 of the previous entry, so any edit,
deletion or reordering of an earlier entry breaks the chain and ``verify()``
reports exactly where.

Honest boundary: a local hash chain is tamper-*evident* on this device. A
production deployment would anchor the chain head to an append-only service or
a permissioned ledger so the evidence survives a lost or wiped phone. It is an
evidence log, not a reversal mechanism: a completed UPI payment still cannot be
undone by this app.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

GENESIS = "0" * 64

# The events that matter for an incident report, in the order they usually happen.
EVENT_ORDER = [
    "payment_drafted",
    "risk_analysed",
    "intent_requested",
    "intent_provided",
    "warning_shown",
    "user_confirmed",
    "payment_simulated",
    "incident_reported",
    "silent_alert",
    "decoy_activated",
    "config_changed",
]


def _canonical(payload: Any) -> str:
    """Stable JSON so the same payload always hashes to the same digest."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=str)


def _digest(previous: str, payload: Any) -> str:
    return hashlib.sha256(f"{previous}|{_canonical(payload)}".encode("utf-8")).hexdigest()


class BlackBox:
    """Append-only, hash-chained event log for one session."""

    def __init__(self, case_id: Optional[str] = None) -> None:
        self.case_id = case_id or datetime.now().strftime("INTENTPAY-%Y%m%d-%H%M%S")
        self.entries: List[Dict[str, Any]] = []

    # ------------------------------------------------------------- append --
    def append(self, event: str, payload: Optional[Dict[str, Any]] = None,
               ts: Optional[str] = None) -> Dict[str, Any]:
        """Append one event and return the stored entry (with its hash)."""
        previous = self.entries[-1]["hash"] if self.entries else GENESIS
        body = {
            "case_id": self.case_id,
            "event": str(event),
            "payload": payload or {},
            "ts": ts or datetime.now().isoformat(timespec="seconds"),
        }
        entry = {
            "index": len(self.entries),
            "ts": body["ts"],
            "event": body["event"],
            "payload": body["payload"],
            "previous_hash": previous,
            "hash": _digest(previous, body),
        }
        self.entries.append(entry)
        return entry

    # -------------------------------------------------------------- verify --
    def verify(self) -> Tuple[bool, Optional[int]]:
        """Check the chain.  Returns ``(ok, first_bad_index)``."""
        previous = GENESIS
        for position, entry in enumerate(self.entries):
            body = {
                "case_id": self.case_id,
                "event": entry["event"],
                "payload": entry["payload"],
                "ts": entry["ts"],
            }
            if entry.get("previous_hash") != previous or entry.get("hash") != _digest(previous, body):
                return False, position
            previous = entry["hash"]
        return True, None

    # ------------------------------------------------------------ timeline --
    def timeline(self) -> List[Dict[str, Any]]:
        """Display-ready timeline: time, event, one-line summary, short hash."""
        out: List[Dict[str, Any]] = []
        for entry in self.entries:
            payload = entry.get("payload") or {}
            summary = payload.get("summary") or _summarise(entry["event"], payload)
            out.append(
                {
                    "index": entry["index"],
                    "ts": entry["ts"],
                    "event": entry["event"],
                    "summary": summary,
                    "hash": entry["hash"],
                    "short_hash": entry["hash"][:12],
                    "previous_hash": entry.get("previous_hash", GENESIS)[:12],
                }
            )
        return out

    # ------------------------------------------------------------- report --
    def incident_report(self) -> Dict[str, Any]:
        """Structured incident report for the bank / cybercrime portal."""
        ok, bad_index = self.verify()
        findings: Dict[str, Any] = {}
        for entry in self.entries:
            findings.setdefault(entry["event"], entry.get("payload") or {})
        return {
            "case_id": self.case_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "event_count": len(self.entries),
            "integrity": {"chain_ok": ok, "first_bad_index": bad_index},
            "events": self.timeline(),
            "findings": findings,
        }

    # ------------------------------------------------------------ export ---
    def export_json(self) -> str:
        return json.dumps(self.incident_report(), indent=2, ensure_ascii=False, default=str)


def _summarise(event: str, payload: Dict[str, Any]) -> str:
    """One-line human summary of an event payload."""
    if "summary" in payload:
        return str(payload["summary"])
    amount = payload.get("amount")
    payee = payload.get("payee") or payload.get("payee_upi") or ""
    score = payload.get("score")
    band = payload.get("band")
    if event == "risk_analysed" and score is not None:
        return f"risk {score} ({band}) for {payee}".strip()
    if event == "payment_drafted" and amount is not None:
        return f"{amount} to {payee}".strip()
    if event == "intent_requested":
        return "the app asked why the user is paying"
    if event == "intent_provided":
        reason = str(payload.get("reason", ""))[:60]
        return f"user stated: {reason}" if reason else "user stated a reason"
    if event == "warning_shown":
        return f"warning shown ({payload.get('band', '')})".strip()
    if event == "user_confirmed":
        return f"user chose: {payload.get('decision', '')}".strip()
    if event == "payment_simulated":
        return f"payment of {amount} simulated to {payee}".strip()
    if event == "incident_reported":
        return "user reported this payment as a scam"
    if event == "silent_alert":
        return "silent duress alert recorded (decoy mode)"
    if event == "decoy_activated":
        return "restricted decoy environment opened"
    if event == "config_changed":
        return str(payload.get("detail", "configuration changed"))
    return event.replace("_", " ")
