"""IntentPay — Streamlit application (entry point).

Run with:  streamlit run APP.PY     (or double-click START_HERE.BAT)

Pages
-----
1. Payment simulator   — the live pre-payment flow judges can play with.
2. Money dashboard     — overview / spending / safety / limits.
3. Judge panel         — every engine parameter, customer data, AI + privacy.
4. Accuracy & cost     — labelled evaluation, threshold sweep, cost model.
5. Scam help           — 1930 / cybercrime.gov.in guidance + complaint draft.
6. About & research    — positioning, architecture, references, limitations.
"""
from __future__ import annotations

import copy
import json
import sys
import time
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# make "SRC" importable no matter where streamlit is launched from
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from SRC import BUDGET as budget_engine
from SRC import DATA_LOADER as dl
from SRC import EXPLAIN
from SRC import LOCAL_LLM
from SRC import METRICS as metrics_mod
from SRC import RECURRING as recurring_engine
from SRC.CATEGORIZER import LOW_CONFIDENCE
from SRC.CONFIG import apply_config, default_config, risk_band, validate_config
from SRC.DASHBOARD import (
    alert,
    badge,
    band_badge,
    card,
    chip_row,
    component_row,
    gauge,
    inject_css,
    kpi,
    money,
    progress_bar,
    signal_list,
    table,
    tone_for_band,
)
from SRC.FORECAST import robust_forecast
from SRC.FRAUD_HELP import complaint_draft, golden_hour_note, help_steps
from SRC.LANGUAGE import band_label, category_label, t
from SRC.MODELS import PaymentRequest, Transaction, inr
from SRC.RECURRING import (
    detect_recurring,
    discretionary_allowance,
    monthly_recurring_commitment,
    upcoming_within,
)
from SRC.SIMULATION import (
    CITY_COORDS,
    PaymentFlow,
    answer_voice_query,
    evaluate_scenario,
    golden_demo,
    qr_png_bytes,
)
from SRC.VOICE import listen, speak, stt_available, tts_available

# --------------------------------------------------------------------------- #
#  Page config
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="IntentPay — AI Payment Intent Guardian (NAS CODERS)",
    page_icon="\U0001F6E1",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={},
)

CATEGORIES = ["FOOD", "ESSENTIALS", "HEALTH", "TRAVEL", "EDUCATION", "BILLS",
              "SHOPPING", "ENTERTAINMENT", "TRANSFER", "OTHER"]
CHANNELS = ["P2P", "QR", "LINK"]
CHANNEL_LABEL = {"P2P": "channel_p2p", "QR": "channel_qr", "LINK": "channel_link"}

# Navigation is stored as a *display label* (never a format_func) so widget state
# stays predictable across language switches and automated UI tests.
NAV_KEYS = ["nav_pay", "nav_dashboard", "nav_judge", "nav_metrics", "nav_help", "nav_about"]
LANGUAGE_LABELS = {"en": "English", "ta": "தமிழ் (Tamil)"}
AI_LABELS = {
    "local": "LOCAL lexicon (offline, default)",
    "ollama": "OLLAMA (your own model, runs on this computer)",
    "external": "EXTERNAL (hosted LLM - data leaves this computer)",
}
ENGINE_BY_LABEL = {label: key for key, label in AI_LABELS.items()}


def nav_labels(lang: str) -> Dict[str, str]:
    return {t(key, lang): key for key in NAV_KEYS}


def category_labels(lang: str) -> Dict[str, str]:
    return {category_label(category, lang): category for category in CATEGORIES}


def channel_labels(lang: str) -> Dict[str, str]:
    return {t(CHANNEL_LABEL[channel], lang): channel for channel in CHANNELS}


def category_label_for(code: str, lang: str) -> str:
    """Display label for a category code (used when loading a scenario)."""
    labels = category_labels(lang)
    for label, category in labels.items():
        if category == code:
            return label
    return next(iter(labels))


def channel_label_for(code: str, lang: str) -> str:
    """Display label for a channel code (used when loading a scenario)."""
    labels = channel_labels(lang)
    for label, channel in labels.items():
        if channel == code:
            return label
    return next(iter(labels))

# --------------------------------------------------------------------------- #
#  Session bootstrap
# --------------------------------------------------------------------------- #


def _sync_profile_limits(cfg: Dict[str, Any], profile: Any) -> Dict[str, Any]:
    """Bring the config in line with the active customer.

    Budget limits come from the profile, and so do the accessibility settings:
    the Tamil-speaking elder customer gets Tamil and large type, the other gets
    English.  The user can still override either from the sidebar.
    """
    cfg = copy.deepcopy(cfg)
    cfg["budget"]["monthly_limit"] = float(profile.monthly_limit)
    cfg["budget"]["food_limit"] = float(profile.category_limits.get("FOOD", 6000.0))
    language = str(getattr(profile, "language", "en") or "en")
    if language in ("en", "ta"):
        cfg["accessibility"]["language"] = language
    elder = bool(getattr(profile, "elder_mode", False))
    cfg["accessibility"]["elder_mode"] = elder
    cfg["accessibility"]["font_scale"] = 1.25 if elder else 1.0
    return cfg


def init_session() -> None:
    """Seed the session. `setdefault` everywhere: a rerun that lost a key must
    re-seed it instead of crashing the whole page."""
    st.session_state.setdefault("cfg", default_config())
    st.session_state.setdefault("customer_id", "customer_one")
    profiles = dl.load_profiles()
    st.session_state.setdefault("profiles", profiles)
    if not st.session_state.profiles:
        st.session_state.profiles = profiles
    profiles = st.session_state.profiles
    if st.session_state.customer_id not in profiles:
        st.session_state.customer_id = "customer_one"
    profile = profiles[st.session_state.customer_id]
    if "profile" not in st.session_state:
        # assigned once: edits made in the judge panel must survive reruns
        st.session_state.profile = profile
    else:
        profile = st.session_state.profile
    if not st.session_state.get("cfg_synced"):
        st.session_state.cfg = _sync_profile_limits(st.session_state.cfg, profile)
    st.session_state.setdefault("cfg_synced", True)
    st.session_state.setdefault("history", dl.load_history(profile.customer_id))
    st.session_state.setdefault("corrections", dl.CorrectionsStore())
    st.session_state.setdefault("flow", PaymentFlow())
    st.session_state.setdefault("audit", [])
    st.session_state.setdefault("metrics", None)
    st.session_state.setdefault("golden", None)
    st.session_state.setdefault("notice", None)
    st.session_state.setdefault("voice_answer", None)
    st.session_state.setdefault("metrics_history", None)


init_session()


def seed_form_defaults() -> None:
    """Seed the simulator form once, so widgets never need a `value=` argument.

    A widget that is created with `value=` *and* has its key already present in
    session state logs a Streamlit warning on every scenario load. Seeding the
    defaults here keeps the console clean and the form deterministic.
    """
    profile = st.session_state.profile
    lang = str(st.session_state.cfg.get("accessibility", {}).get("language", "en"))
    defaults = {
        "f_amount": 500.0,
        "f_method": "UPI",
        "f_payee_name": "",
        "f_payee_upi": "",
        "f_category": next(iter(category_labels(lang))),
        "f_date": date.today(),
        "f_time": dtime(datetime.now().hour, 0),
        "f_city": profile.usual_city,
        "f_channel": next(iter(channel_labels(lang))),
        "f_new_payee": False,
        "f_device": "",
        "f_battery": 85,
        "f_on_call": False,
        "f_call_minutes": 10,
        "f_intent": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


seed_form_defaults()

# Deep-link support: http://127.0.0.1:8501/?page=nav_dashboard opens that page.
# Must run before the sidebar, which seeds "page_key" from the navigation radio.
_requested_page = st.query_params.get("page", "nav_pay")
if _requested_page in NAV_KEYS and "page_key" not in st.session_state:
    st.session_state["page_key"] = _requested_page

CFG: Dict[str, Any] = st.session_state.cfg
PROFILE = st.session_state.profile
HISTORY: pd.DataFrame = st.session_state.history
LANG: str = str(CFG.get("accessibility", {}).get("language", "en"))
ELDER: bool = bool(CFG.get("accessibility", {}).get("elder_mode", False))
LOCAL_ONLY: bool = bool(CFG.get("privacy", {}).get("local_only", True))
AI_ENGINE: str = str(CFG.get("ai", {}).get("engine", "local"))


def notify(message: str, tone: str = "info") -> None:
    st.session_state.notice = {"message": message, "tone": tone}


def show_notice() -> None:
    notice = st.session_state.get("notice")
    if notice:
        alert(notice["message"], notice["tone"])
        st.session_state.notice = None


def rerun() -> None:  # pragma: no cover - streamlit runtime
    st.rerun()


def audit(event: Dict[str, Any]) -> None:
    st.session_state.audit.append({**event, "ts": datetime.now().isoformat(timespec="seconds")})


# --------------------------------------------------------------------------- #
#  Header + sidebar
# --------------------------------------------------------------------------- #

st.markdown(inject_css(CFG["accessibility"].get("font_scale", 1.0), ELDER), unsafe_allow_html=True)

# belt and braces: the sidebar reads the customer list, so it must exist no matter
# what a previous rerun did to the session state
if not st.session_state.get("profiles"):
    st.session_state.profiles = dl.load_profiles()

with st.sidebar:
    st.markdown(
        f'<div style="padding:6px 2px 2px 2px;">'
        f'<span style="font-size:1.35rem;font-weight:800;letter-spacing:-0.02em;">IntentPay</span>'
        f'<span class="ip-badge" style="margin-left:8px;color:#334155;background:#F8FAFC;'
        f'border-color:#E2E8F0;">{t("team_name", LANG)}</span></div>'
        f'<div class="ip-muted" style="font-size:0.8rem;margin:4px 0 12px 0;">'
        f'{t("app_tagline", LANG)}</div>',
        unsafe_allow_html=True,
    )
    labels = nav_labels(LANG)
    options = list(labels.keys())
    current_key = st.session_state.get("page_key", "nav_pay")
    index = options.index(t(current_key, LANG)) if t(current_key, LANG) in options else 0
    page = st.radio(
        "Navigation",
        options=options,
        index=index,
        label_visibility="collapsed",
    )
    nav_page = labels.get(page, "nav_pay")
    st.session_state["page_key"] = nav_page
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)

    # customer switch
    _profiles = st.session_state.get("profiles") or dl.load_profiles()
    st.session_state.profiles = _profiles
    customer_options = {
        f'{p.name} - {p.usual_city} (age {p.age})': key
        for key, p in _profiles.items()
    }
    customer_label = st.radio(
        t("customer", LANG),
        options=list(customer_options.keys()),
        key="customer_radio",
    )
    selected_customer = customer_options.get(customer_label, st.session_state.customer_id)
    if selected_customer != st.session_state.customer_id:
        st.session_state.customer_id = selected_customer
        st.session_state.profile = _profiles[selected_customer]
        st.session_state.history = dl.load_history(selected_customer)
        # The new customer's language and elder preference come with them.  The
        # sidebar widgets must be *assigned*, not popped: Streamlit keeps the
        # widget value on the frontend, so a popped key is restored from the
        # browser on the next run and the box keeps showing the old language
        # while the page is already in the new one.  Assigning is legal here
        # because these widgets have not been instantiated yet in this run.
        st.session_state.cfg = _sync_profile_limits(st.session_state.cfg, st.session_state.profile)
        st.session_state["lang_select"] = LANGUAGE_LABELS.get(
            st.session_state.cfg["accessibility"]["language"], LANGUAGE_LABELS["en"])
        st.session_state["elder_checkbox"] = bool(
            st.session_state.cfg["accessibility"]["elder_mode"])
        st.session_state["voice_checkbox"] = bool(
            st.session_state.cfg["accessibility"].get("voice", True))
        for form_key in ("f_category", "f_channel"):
            st.session_state.pop(form_key, None)
        st.session_state.flow = PaymentFlow()
        notify(f'Switched to {st.session_state.profile.name}.', "info")
        rerun()

    # language
    lang_label = st.selectbox(
        t("language", LANG),
        options=list(LANGUAGE_LABELS.values()),
        index=0 if LANG == "en" else 1,
        key="lang_select",
    )
    lang_choice = "en" if lang_label == LANGUAGE_LABELS["en"] else "ta"
    if lang_choice != LANG:
        st.session_state.cfg["accessibility"]["language"] = lang_choice
        # page_key (not a widget key) keeps the user on the same page; the
        # translated form widgets are re-rendered from scratch
        for form_key in ("f_category", "f_channel"):
            st.session_state.pop(form_key, None)
        rerun()

    elder = st.checkbox(t("elder_mode", LANG), value=ELDER, key="elder_checkbox")
    if elder != ELDER:
        st.session_state.cfg["accessibility"]["elder_mode"] = elder
        st.session_state.cfg["accessibility"]["font_scale"] = 1.25 if elder else 1.0
        rerun()

    voice_on = st.checkbox(t("voice", LANG), value=bool(CFG["accessibility"].get("voice", True)),
                           key="voice_checkbox")
    if voice_on != bool(CFG["accessibility"].get("voice", True)):
        st.session_state.cfg["accessibility"]["voice"] = voice_on
        rerun()

    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)

    # privacy / AI status badges
    badges = [badge(t("mode_local_only", LANG), "good") if LOCAL_ONLY
              else badge(t("mode_external_ai", LANG), "bad")]
    st.markdown(" ".join(badges), unsafe_allow_html=True)
    if not LOCAL_ONLY and AI_ENGINE == "external":
        st.markdown(alert(t("data_leaves_warning", LANG), "warn"), unsafe_allow_html=True)

    if st.button(f"♻️  {t('safe_reset', LANG)}", use_container_width=True, key="safe_reset_btn"):
        st.session_state.cfg = _sync_profile_limits(default_config(), st.session_state.profile)
        st.session_state.history = dl.load_history(st.session_state.customer_id)
        st.session_state.corrections = dl.CorrectionsStore()
        st.session_state.flow = PaymentFlow()
        st.session_state.audit = []
        st.session_state.metrics = None
        st.session_state.golden = None
        notify(t("reset_done", LANG), "good")
        rerun()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "customer": st.session_state.profile.to_dict(),
        "config": st.session_state.cfg,
        "flow_events": st.session_state.flow.events,
        "audit": st.session_state.audit,
    }
    st.download_button(
        f"⬇️  {t('export', LANG)}",
        data=json.dumps(report, indent=2, ensure_ascii=False, default=str),
        file_name="INTENTPAY_REPORT.JSON",
        mime="application/json",
        use_container_width=True,
        key="export_report_btn",
    )
    st.markdown(
        f'<div class="ip-muted" style="font-size:0.72rem;margin-top:14px;line-height:1.45;">'
        f'{t("prototype_notice", LANG)}</div>',
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
#  Top header
# --------------------------------------------------------------------------- #

st.markdown(
    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
    f'flex-wrap:wrap;gap:10px;">'
    f'<div><h1 style="margin:0;">IntentPay '
    f'<span class="ip-muted" style="font-weight:500;font-size:1rem;">AI Payment Intent Guardian '
    f'+ Personal Financial Guardian</span></h1>'
    f'<div class="ip-muted" style="margin-top:3px;">{t("about_what", LANG)}</div></div>'
    f'<div style="text-align:right;">{badge(st.session_state.profile.name, "dark")}<br/>'
    f'<span class="ip-muted" style="font-size:0.75rem;">demo customer</span></div></div>'
    f'<hr class="ip-divider">',
    unsafe_allow_html=True,
)

show_notice()

# --------------------------------------------------------------------------- #
#  Helpers shared by pages
# --------------------------------------------------------------------------- #


def current_month_numbers() -> Dict[str, Any]:
    now = datetime.now()
    limit = float(CFG["budget"]["monthly_limit"])
    spent = budget_engine.month_spend(HISTORY, now)
    forecast = robust_forecast(HISTORY, CFG, now)
    return {
        "now": now,
        "limit": limit,
        "spent": spent,
        "remaining": limit - spent,
        "utilisation": 100.0 * spent / limit if limit else 0.0,
        "state": budget_engine.budget_state(100.0 * spent / limit if limit else 0.0),
        "forecast": forecast,
        "daily_allowance": budget_engine.daily_allowance(limit - spent, now),
        "days_remaining": forecast["days_remaining"],
    }


def run_evaluate(payment: PaymentRequest) -> Any:
    """Evaluate a payment, mirror it into the audit trail, return the result."""
    result = st.session_state.flow.evaluate(
        payment, HISTORY, st.session_state.profile, CFG, st.session_state.corrections.as_dict()
    )
    audit(
        {
            "event": "payment_evaluated",
            "amount": payment.amount,
            "payee": payment.payee_name,
            "payee_upi": payment.payee_upi,
            "fraud_risk": result.fraud_risk,
            "band": result.band,
            "intent_risk": result.intent_risk,
            "budget_band": result.budget.budget_band,
            "latency_ms": result.latency_ms.get("total_ms"),
        }
    )
    return result


def form_values() -> Dict[str, Any]:
    """Collect simulator form values from session state."""
    day = st.session_state.get("f_date") or date.today()
    clock = st.session_state.get("f_time") or dtime(datetime.now().hour, 0)
    when = datetime.combine(day, clock)
    return {
        "amount": float(st.session_state.get("f_amount") or 0.0),
        "method": st.session_state.get("f_method", "UPI"),
        "payee_name": st.session_state.get("f_payee_name", ""),
        "payee_upi": st.session_state.get("f_payee_upi", ""),
        "purpose_category": category_labels(LANG).get(
            st.session_state.get("f_category", ""), "OTHER"
        ),
        "timestamp": when,
        "city": st.session_state.get("f_city", st.session_state.profile.usual_city),
        "on_call": bool(st.session_state.get("f_on_call", False)),
        "call_duration_s": int(float(st.session_state.get("f_call_minutes") or 0) * 60),
        "channel": channel_labels(LANG).get(st.session_state.get("f_channel", ""), "P2P"),
        "new_payee": bool(st.session_state.get("f_new_payee", False)),
        "device_id": st.session_state.get("f_device", ""),
        "battery_pct": int(st.session_state.get("f_battery") or 85),
        # the blocking "why are you paying?" prompt keeps its own key so it never
        # has to touch an already-instantiated widget
        "intent_text": (st.session_state.get("f_intent_reason")
                        or st.session_state.get("f_intent") or ""),
    }


def load_scenario_into_form(scenario: Dict[str, Any]) -> None:
    """Populate the form from a scenario payload (before widgets render)."""
    payment = scenario["payment"]
    st.session_state.f_amount = float(payment["amount"])
    st.session_state.f_method = payment.get("method", "UPI")
    st.session_state.f_payee_name = payment.get("payee_name", "")
    st.session_state.f_payee_upi = payment.get("payee_upi", "")
    st.session_state.f_category = category_label_for(
        payment.get("purpose_category", "OTHER"), LANG
    )
    st.session_state.f_date = date.today()
    st.session_state.f_time = dtime(int(payment.get("hour", datetime.now().hour)), 0)
    st.session_state.f_city = payment.get("city", st.session_state.profile.usual_city)
    st.session_state.f_on_call = bool(payment.get("on_call", False))
    st.session_state.f_call_minutes = int(payment.get("call_duration_s", 0)) // 60
    st.session_state.f_channel = channel_label_for(payment.get("channel", "P2P"), LANG)
    st.session_state.f_new_payee = bool(payment.get("new_payee", False))
    st.session_state.f_device = payment.get("device_id", "")
    st.session_state.f_battery = int(payment.get("battery_pct", 85))
    st.session_state.pop("f_intent_reason", None)
    # a Tamil-first user should hear Tamil reasons in the demo, not English ones
    intent = payment.get("intent_text", "")
    if LANG == "ta" and payment.get("intent_text_ta"):
        intent = payment["intent_text_ta"]
    st.session_state.f_intent = intent


def render_result(result: Any, payment: PaymentRequest, compact: bool = False) -> None:
    """The result block: fraud gauge, components, budget, explanation, actions."""
    lang = LANG
    left, right = st.columns([1.15, 1.0])

    with left:
        st.markdown(
            card(
                t("fraud_risk", lang),
                gauge(result.fraud_risk, result.band, band_label(result.band, lang))
                + '<div class="ip-divider"></div>'
                + component_row(t("transaction_risk", lang), result.transaction_risk)
                + component_row(
                    t("intent_risk", lang), result.intent_risk,
                    note=t("unknown", lang) if result.intent_risk is None else "",
                )
                + component_row(t("recipient_risk", lang), result.recipient_risk)
                + f'<div class="ip-signal"><span class="ip-muted">'
                f'{t("latency", lang)}</span><span class="ip-muted ip-num">'
                f'{result.latency_ms.get("total_ms", 0):.0f} ms</span></div>',
                tone=tone_for_band(result.band),
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            card(
                t("explanation", lang),
                signal_list(result.explanation, lang),
            ),
            unsafe_allow_html=True,
        )

    with right:
        b = result.budget
        st.markdown(
            card(
                t("sec_budget_impact", lang),
                table(
                    [t("amount", lang), t("budget", lang), t("remaining", lang)],
                    [[
                        money(payment.amount),
                        money(b.monthly_limit),
                        money(b.remaining_after),
                    ]],
                    numeric_cols=[0, 1, 2],
                )
                + '<div style="margin-top:10px;">'
                + f'<div class="ip-signal"><span>{t("total_spent", lang)}</span>'
                  f'<span class="ip-num">{money(b.spent_after)}</span></div>'
                + f'<div class="ip-signal"><span>{t("budget_used", lang)}</span>'
                  f'<span class="ip-num">{b.utilisation_after:.0f}%</span></div>'
                + f'<div class="ip-signal"><span>{category_label(b.category, lang)}</span>'
                  f'<span class="ip-num">{money(b.category_spent_after)}'
                  + (f' / {money(b.category_limit)}' if b.category_limit else "")
                  + "</span></div>"
                + f'<div class="ip-signal"><span>{t("projected_month_end", lang)}</span>'
                  f'<span class="ip-num">{money(b.projected_month_end)}</span></div>'
                + "</div>"
                + '<div style="margin-top:8px;">'
                + badge(t(b.state_before, lang), "good" if b.state_before == "SAFE" else "warn")
                + " "
                + badge(
                    f'{t("budget", lang)}: {b.budget_band}',
                    "good" if b.budget_band == "LOW" else ("warn" if b.budget_band == "MEDIUM" else "bad"),
                )
                + "</div>",
                tone="neutral",
            ),
            unsafe_allow_html=True,
        )
        for message_key in b.messages:
            st.markdown(alert(t(message_key, lang), "warn"), unsafe_allow_html=True)

        st.markdown(
            card(
                t("recommendation", lang),
                f'<div style="font-weight:650;margin-bottom:6px;">{result.recommendation}</div>'
                + f'<div class="ip-muted" style="font-size:0.85rem;">'
                f'category: {category_label(result.category, lang)} · '
                f'confidence: {result.category_confidence:.0%}</div>',
                tone="bad" if result.band in ("HIGH", "CRITICAL") else (
                    "warn" if result.band == "MEDIUM" else "good"),
            ),
            unsafe_allow_html=True,
        )

        if result.ai_fallback:
            st.markdown(
                alert("External AI was unavailable — the local offline engine answered.", "info"),
                unsafe_allow_html=True,
            )

        if not compact:
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(f"✅ {t('approve', lang)}", type="primary",
                             use_container_width=True, key="approve_btn"):
                    st.session_state.flow.decide("APPROVED")
                    new_history, txn, handoff = st.session_state.flow.commit(
                        HISTORY, st.session_state.profile
                    )
                    st.session_state.history = new_history
                    audit({"event": "payment_committed", "amount": payment.amount,
                           "payee": payment.payee_name, "utr": txn.utr,
                           "band": result.band})
                    notify(f"Payment simulated and added to the demo ledger (UTR {txn.utr}).", "good")
                    rerun()
            with c2:
                if st.button(f"✖ {t('cancel', lang)}", use_container_width=True, key="cancel_btn"):
                    st.session_state.flow.decide("CANCELLED")
                    notify("Payment cancelled. Nothing was sent — this is the safe outcome.", "good")
                    rerun()
            with c3:
                if st.button(f"🆘 {t('help_btn', lang)}", use_container_width=True, key="help_btn"):
                    st.session_state.flow.decide("HELP")
                    st.session_state["page_key"] = "nav_help"
                    rerun()

    # handoff card after commit
    if st.session_state.flow.state == "COMMITTED" and st.session_state.flow.handoff:
        handoff = st.session_state.flow.handoff
        qr = qr_png_bytes(handoff["upi_uri"])
        qr_html = (
            f'<img src="data:image/png;base64,{_b64(qr)}" style="width:148px;height:148px;'
            f'border:1px solid #E2E8F0;border-radius:8px;"/>'
            if qr
            else ""
        )
        st.markdown(
            card(
                "Simulated UPI handoff",
                f'<div style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">'
                f"{qr_html}"
                f'<div style="flex:1;min-width:260px;">'
                f'<div class="ip-muted" style="font-size:0.85rem;">upi:// deep link</div>'
                f'<code style="font-size:0.8rem;word-break:break-all;">{handoff["upi_uri"]}</code>'
                f'<div style="margin-top:8px;">{badge("UTR " + handoff["utr"], "dark")}</div>'
                f'<div class="ip-muted" style="margin-top:8px;font-size:0.85rem;">'
                f'{handoff["note_en"]}</div></div></div>',
                tone="info",
            ),
            unsafe_allow_html=True,
        )


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")


# --------------------------------------------------------------------------- #
#  Send-money flow: the judge's path through the app
# --------------------------------------------------------------------------- #


def render_reason_requested(result: Any) -> None:
    """Did the app stop to ask why?  The threshold maths is shown, not hidden."""
    lang = LANG
    ask_above = float(CFG["risk"]["ask_intent_above"])
    prelim = float(result.features.get("preliminary_score", result.fraud_risk))
    if result.intent_provided:
        return
    if result.intent_requested:
        st.markdown(
            alert(
                f'{t("reason_yes", lang)}<div class="ip-muted" style="margin-top:6px;font-size:0.82rem;">'
                f'preliminary score {prelim:.1f} &ge; ask_intent_above {ask_above:.0f} '
                f'(both editable in the Judge Panel)</div>',
                "warn",
                title=f'❓ {t("reason_requested", lang)}',
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            alert(
                f'{t("reason_no", lang)}<div class="ip-muted" style="margin-top:6px;font-size:0.82rem;">'
                f'preliminary score {prelim:.1f} &lt; ask_intent_above {ask_above:.0f} '
                f'— no interruption, no friction</div>',
                "good",
                title=f'✅ {t("reason_requested", lang)}',
            ),
            unsafe_allow_html=True,
        )


def render_intent_prompt() -> None:
    """The blocking question: 'why are you paying?'."""
    lang = LANG
    flow: PaymentFlow = st.session_state.flow
    st.markdown(
        card(
            f'❓ {t("intent_prompt_title", lang)}',
            f'<div class="ip-muted">{t("intent_prompt_hint", lang)}</div>',
            tone="warn",
        ),
        unsafe_allow_html=True,
    )
    st.text_area(
        t("intent_text", lang),
        height=90,
        key="f_intent_reason",
        label_visibility="collapsed",
        placeholder="e.g. cousin's college admission fees / மகளுக்கு கல்லூரி கட்டணம்",
    )
    if st.button(f"🔍 {t('evaluate', lang)}", type="primary", key="submit_reason_btn",
                 use_container_width=True):
        reason = str(st.session_state.get("f_intent_reason", "") or "")
        flow.record_intent(reason)
        payment = PaymentFlow.payment_from_values(form_values(), st.session_state.profile)
        run_evaluate(payment)
        rerun()


def render_attribution(result: Any) -> None:
    """SHAP-style attribution: the points each signal added, summing to the score."""
    lang = LANG
    rows = list(getattr(result, "attribution", []) or [])
    if not rows:
        return
    total = round(sum(float(row["points"]) for row in rows), 1)
    body = table(
        [t("attribution_title", lang).split(" (")[0], "points"],
        [[row["signal_ta"] if lang == "ta" else row["signal_en"],
          f'{row["points"]:+.1f}'] for row in rows],
        numeric_cols=[1],
    )
    body += (
        f'<div class="ip-signal"><span>{t("attribution_sum", lang)}</span>'
        f'<span class="ip-num">{total:+.1f} / {result.fraud_risk:.1f}</span></div>'
        f'<div class="ip-muted" style="margin-top:6px;font-size:0.8rem;">'
        f'{t("attribution_note", lang)}</div>'
    )
    with st.expander(f"🧮 {t('attribution_title', lang)}  ({len(rows)} signals)"):
        st.markdown(card("", body, tone="neutral"), unsafe_allow_html=True)


def render_decoy_panel() -> None:
    """Emergency PIN -> restricted decoy environment (duress protection)."""
    lang = LANG
    flow: PaymentFlow = st.session_state.flow
    decoy_cfg = CFG.get("decoy", {}) or {}
    st.markdown(f"### 🛡️ {t('decoy_title', lang)}")
    st.markdown(f'<div class="ip-muted">{t("decoy_what", lang)}</div>', unsafe_allow_html=True)

    if not flow.decoy_mode:
        pin_col, btn_col = st.columns([2, 1])
        with pin_col:
            st.text_input(t("decoy_pin_label", lang), type="password", key="decoy_pin_input",
                          help="demo PIN is configured in the Judge Panel")
        with btn_col:
            st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
            if st.button(t("decoy_activate", lang), key="decoy_unlock_btn",
                         use_container_width=True):
                outcome = flow.check_pin(st.session_state.get("decoy_pin_input", ""), CFG)
                if not outcome.get("decoy"):
                    notify(t("decoy_wrong_pin", lang), "warn")
                else:
                    notify(t("decoy_active", lang), "good")
                rerun()
    else:
        st.markdown(
            alert(t("decoy_active", lang) + " " + t("decoy_boundary", lang), "warn",
                  title=f'🛡️ {t("decoy_title", lang)}'),
            unsafe_allow_html=True,
        )
        balance = float(decoy_cfg.get("decoy_balance", 0.0))
        limit = float(decoy_cfg.get("decoy_transaction_limit", 0.0))
        monthly = float(decoy_cfg.get("decoy_monthly_limit", 0.0))
        st.markdown(
            card(
                t("decoy_balance", lang),
                f'<div style="font-size:1.6rem;font-weight:750;">{money(balance)}</div>'
                f'<div class="ip-muted" style="font-size:0.82rem;">'
                f'{t("decoy_limit", lang)}: {money(limit)} · monthly {money(monthly)}</div>',
                tone="dark",
            ),
            unsafe_allow_html=True,
        )
        d1, d2 = st.columns([2, 1])
        with d1:
            st.text_input(t("payee_name", lang), key="decoy_payee")
            st.number_input(t("amount", lang) + " (₹)", min_value=0.0, step=100.0,
                            key="decoy_amount")
        with d2:
            st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
            if st.button(t("decoy_pay", lang), type="primary", key="decoy_pay_btn",
                         use_container_width=True):
                outcome = flow.decoy_payment(
                    float(st.session_state.get("decoy_amount", 0.0) or 0.0),
                    str(st.session_state.get("decoy_payee", "") or ""), CFG,
                )
                notify(outcome["message_ta"] if lang == "ta" else outcome["message_en"],
                       "bad" if outcome["blocked"] else "good")
                rerun()
        if flow.decoy_log:
            last = flow.decoy_log[-1]
            st.markdown(
                alert(last["message_ta"] if lang == "ta" else last["message_en"],
                      "bad" if last["blocked"] else "good"),
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="ip-muted" style="font-size:0.78rem;">'
            f'🔔 {t("blackbox_event", lang)}: silent_alert · '
            f'{t("decoy_exit", lang)} restores the real environment.</div>',
            unsafe_allow_html=True,
        )
        if st.button(t("decoy_exit", lang), key="decoy_exit_btn"):
            flow.decoy_mode = False
            notify("Back to the real environment.", "info")
            rerun()


def render_blackbox_panel() -> None:
    """UPI Black Box: tamper-evident timeline of the events around a payment."""
    lang = LANG
    flow: PaymentFlow = st.session_state.flow
    box = flow.blackbox
    st.markdown(f"### ✈️ {t('blackbox_title', lang)}")
    st.markdown(f'<div class="ip-muted">{t("blackbox_what", lang)}</div>', unsafe_allow_html=True)

    st.session_state.setdefault("blackbox_tampered", False)

    if not box.entries:
        st.markdown(alert(t("blackbox_empty", lang), "info"), unsafe_allow_html=True)
    else:
        ok, bad_index = box.verify()
    if st.session_state.blackbox_tampered:
        ok, bad_index = False, 0
    if not box.entries:
        ok, bad_index, tone = False, None, "neutral"
    else:
        tone = "good" if ok else "bad"
    if box.entries:
        st.markdown(
            alert(t("blackbox_integrity_ok", lang) if ok
                  else f'{t("blackbox_integrity_broken", lang)} (entry #{bad_index})', tone),
            unsafe_allow_html=True,
        )
    rows = [
        [f'{row["ts"][11:19]}', row["event"], row["summary"], row["short_hash"]]
        for row in box.timeline()
    ]
    st.markdown(
        card(t("blackbox_timeline", lang), table(["time", t("blackbox_event", lang), "", t("blackbox_hash", lang)], rows),
             tone="neutral"),
        unsafe_allow_html=True,
    )
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button(f"🔍 {t('blackbox_verify', lang)}", key="blackbox_verify_btn",
                     use_container_width=True):
            st.session_state.blackbox_tampered = False
            ok, bad_index = box.verify()
            notify(t("blackbox_integrity_ok", lang) if ok else t("blackbox_integrity_broken", lang),
                   "good" if ok else "bad")
            rerun()
    with b2:
        if st.button(f"🧪 {t('blackbox_tamper_demo', lang)}", key="blackbox_tamper_btn",
                     use_container_width=True):
            # deliberately corrupt the first entry to prove the chain detects it
            if box.entries:
                box.entries[0]["payload"]["amount"] = 1.0
                box.entries[0]["payload"]["summary"] = "edited after the fact"
                st.session_state.blackbox_tampered = True
                notify(t("blackbox_integrity_broken", lang), "bad")
            else:
                notify(t("blackbox_empty", lang), "warn")
            rerun()
    with b3:
        st.download_button(
            f"⬇️ {t('blackbox_export', lang)}",
            data=box.export_json(),
            file_name=f"{box.case_id}_INCIDENT_REPORT.JSON",
            mime="application/json",
            use_container_width=True,
            key="blackbox_export_btn",
        )
    st.markdown(f'<div class="ip-muted" style="font-size:0.78rem;">{t("blackbox_boundary", lang)}</div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Page 1: payment simulator
# --------------------------------------------------------------------------- #


def page_pay() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_pay', lang)}", unsafe_allow_html=True)

    # ---- scenario chips (rendered before the form so they can seed it) ----
    scenarios = dl.load_scenarios()
    st.markdown(f"**{t('sec_scenarios', lang)}**")
    names = list(scenarios.keys())
    # four per row: five per row truncates the longer labels ("Food ₹1,200
    # (budget impact)") to "Food ₹1,200 (budd…" and the chips stop being readable
    cols_per_row = 4
    for row_start in range(0, len(names), cols_per_row):
        row_names = names[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_names))
        for col, name in zip(cols, row_names):
            scenario = scenarios[name]
            label = scenario.get(f"label_{lang}") or scenario["label_en"]
            if col.button(label, key=f"scenario_{name}", use_container_width=True,
                          help=scenario.get(f"hint_{lang}") or scenario["hint_en"]):
                load_scenario_into_form(scenario)
                payment = PaymentFlow.payment_from_values(form_values(), st.session_state.profile)
                run_evaluate(payment)
                rerun()

    # ---- golden demo ----
    with st.expander(f"⭐ {t('sec_golden_demo', lang)}"):
        st.markdown(
            '<div class="ip-muted">Same ₹25,000 payment, two stories: an ordinary reason '
            'vs. "the bank threatened me". Two different warnings from two different problems.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Run golden demo", key="golden_btn", use_container_width=True):
            with st.spinner("Evaluating both contexts…"):
                st.session_state.golden = golden_demo(
                    HISTORY, st.session_state.profile, CFG,
                    st.session_state.corrections.as_dict(),
                )
        golden = st.session_state.golden
        if golden:
            g1, g2 = st.columns(2)
            for col, (title, result) in zip(
                (g1, g2),
                (("Ordinary reason", golden["ordinary"]), ("Coerced reason", golden["coerced"])),
            ):
                with col:
                    st.markdown(
                        card(
                            title,
                            gauge(result.fraud_risk, result.band, band_label(result.band, lang))
                            + '<div class="ip-divider"></div>'
                            + signal_list(result.explanation, lang)
                            + f'<div class="ip-signal"><span>{t("recommendation", lang)}</span>'
                              f'<span class="ip-num" style="max-width:60%;text-align:right;">'
                              f'{result.recommendation}</span></div>',
                            tone=tone_for_band(result.band),
                        ),
                        unsafe_allow_html=True,
                    )
            st.markdown(
                alert(
                    f"Same amount, same recipient — the risk score moves by "
                    f"{golden['delta']:+.0f} points purely because of the *reason given*. "
                    "That is the innovation: the user's own words are a fraud signal.",
                    "info",
                ),
                unsafe_allow_html=True,
            )

    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)

    # ---- payment form ----
    st.markdown(f"### 💸 {t('send_money_title', lang)}")
    st.markdown(f'<div class="ip-muted">{t("send_money_hint", lang)}</div>',
                unsafe_allow_html=True)
    left, right = st.columns([1.35, 1.0])
    with left:
        c1, c2 = st.columns(2)
        with c1:
            st.number_input(t("amount", lang) + " (₹)", min_value=1.0, max_value=10_000_000.0,
                            step=100.0, key="f_amount")
            st.selectbox(t("payment_method", lang), options=["UPI", "BANK"], key="f_method")
            st.text_input(t("payee_name", lang), key="f_payee_name")
            st.text_input(t("payee_upi", lang), key="f_payee_upi",
                          help="e.g. name@bank — never your own UPI PIN/OTP")
            st.selectbox(t("category", lang), options=list(category_labels(lang).keys()),
                         key="f_category")
        with c2:
            st.date_input(t("date", lang), key="f_date")
            st.time_input(t("time", lang), key="f_time")
            st.selectbox(t("location", lang), options=list(CITY_COORDS.keys()), key="f_city")
            st.selectbox(t("channel", lang), options=list(channel_labels(lang).keys()),
                         key="f_channel")
            st.checkbox(t("new_payee", lang), key="f_new_payee")
            st.text_input(t("device", lang), key="f_device",
                          help=f"known devices: {', '.join(st.session_state.profile.known_devices)}")
            st.slider(t("battery", lang), 1, 100, value=None, key="f_battery")
        st.checkbox(t("on_call", lang), key="f_on_call")
        if st.session_state.get("f_on_call"):
            st.number_input(t("call_duration", lang), min_value=0, max_value=600,
                            step=5, key="f_call_minutes")

    with right:
        st.markdown(f"### {t('sec_intent', lang)}")
        st.markdown(
            '<div class="ip-muted" style="font-size:0.85rem;">A short reason in your own words. '
            'Risky payments are checked for urgency, authority claims, threats and secrecy '
            'patterns — in English or Tamil.</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            t("intent_text", lang),
            height=110,
            key="f_intent",
            label_visibility="collapsed",
            placeholder="e.g. cousin's college admission fees",
        )
        if st.button(f"🔍 {t('evaluate', lang)}", type="primary", use_container_width=True,
                     key="evaluate_btn"):
            payment = PaymentFlow.payment_from_values(form_values(), st.session_state.profile)
            if payment.amount <= 0:
                notify("Enter an amount first.", "warn")
            else:
                run_evaluate(payment)
                rerun()

    # ---- result ----
    flow: PaymentFlow = st.session_state.flow
    if flow.result is not None and flow.payment is not None:
        st.markdown(f"### {t('sec_result', lang)}", unsafe_allow_html=True)
        render_reason_requested(flow.result)
        if flow.result.intent_requested and not flow.result.intent_provided:
            render_intent_prompt()
        elif flow.result.intent_unknown and not flow.result.intent_requested:
            st.markdown(alert(t("intent_missing_note", lang), "info"), unsafe_allow_html=True)
        flow.record_warning()
        render_result(flow.result, flow.payment)
        render_attribution(flow.result)
    else:
        st.markdown(
            alert(
                "Pick a scenario above or fill the form and press “Check this payment”. "
                "Every parameter is editable — nothing is pre-canned.",
                "info",
                title="Ready",
            ),
            unsafe_allow_html=True,
        )

    # ---- safety features (always reachable, result or not) ----
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### 🛡️ {t('safe_mode', lang)}", unsafe_allow_html=True)
    render_blackbox_panel()
    render_decoy_panel()

    # ---- voice Q&A ----
    with st.expander("🎙️ Voice questions — ask about your money"):
        query = st.text_input(
            "Ask about your money",
            key="voice_query",
            placeholder="how much did I spend this month? / இந்த மாதம் எவ்வளவு செலவாகிறது?",
        )
        vcol1, vcol2 = st.columns([1, 2])
        with vcol1:
            if st.button("🎙️ Speak", key="voice_speak_btn", use_container_width=True):
                ok, payload = listen(lang)
                if ok:
                    st.session_state.voice_query = payload
                    notify(f'Heard: "{payload}"', "info")
                    rerun()
                else:
                    notify(f"{t('voice_unavailable', lang)} ({payload})", "warn")
        with vcol2:
            if st.button("🔊 Answer", key="voice_answer_btn", use_container_width=True):
                answer = answer_voice_query(
                    st.session_state.get("voice_query", ""), HISTORY,
                    st.session_state.profile, CFG, st.session_state.flow.result,
                )
                st.session_state.voice_answer = answer
                if CFG["accessibility"].get("voice", True):
                    ok, detail = speak(answer["text"], lang)
                    if not ok:
                        st.session_state.voice_answer = {**answer, "note": detail}
                rerun()
        answer = st.session_state.get("voice_answer")
        if answer:
            st.markdown(
                card("Answer", f'<div style="font-weight:650;">{answer["text"]}</div>'
                              + (f'<div class="ip-muted" style="margin-top:4px;">{answer["note"]}</div>'
                                 if answer.get("note") else ""), tone="info"),
                unsafe_allow_html=True,
            )
        if not tts_available():
            st.markdown(
                f'<div class="ip-muted" style="font-size:0.78rem;">{t("voice_unavailable", lang)} '
                '(TTS: pip install pyttsx3 · STT: pip install SpeechRecognition)</div>',
                unsafe_allow_html=True,
            )


# --------------------------------------------------------------------------- #
def render_local_llm_panel() -> None:
    """Local AI: detect the machine, recommend a model, install and link it.

    Four visible steps — detect, recommend, install, link — so a judge can put a
    real language model behind the intent layer in about two minutes and see the
    link work.  Nothing here is required: the offline lexicon is the default and
    the fallback for every path below.
    """
    lang = LANG
    cfg = st.session_state.cfg
    ai_cfg = cfg.get("ai", {}) or {}
    st.session_state.setdefault("llm_specs", None)
    st.session_state.setdefault("llm_reco", None)
    st.session_state.setdefault("llm_log", [])

    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### {t('llm_title', lang)}")
    st.markdown(f'<div class="ip-muted">{t("llm_what", lang)}</div>', unsafe_allow_html=True)

    # ---- step 1: detect the machine ---------------------------------------- #
    d1, d2 = st.columns([1, 2])
    with d1:
        if st.button(t("llm_detect", lang), key="llm_detect_btn", use_container_width=True):
            with st.spinner("Reading this machine…"):
                st.session_state.llm_specs = LOCAL_LLM.machine_specs()
                st.session_state.llm_reco = LOCAL_LLM.recommend_model(st.session_state.llm_specs)
            rerun()
    with d2:
        st.markdown(f'<div class="ip-muted">{t("llm_detect_hint", lang)}</div>',
                    unsafe_allow_html=True)

    specs = st.session_state.llm_specs
    reco = st.session_state.llm_reco
    if specs:
        st.markdown(
            card(
                t("llm_specs_title", lang),
                table(
                    ["", t("llm_detected", lang)],
                    [["OS", specs["os"]],
                     ["CPU", f'{specs["cpu"]} ({specs["cores"]} cores)'],
                     [t("llm_ram", lang), specs["ram_text"]],
                     ["GPU", specs["gpu_text"]],
                     [t("llm_disk", lang), f'{specs["free_disk_gb"]:.1f} GB free'
                      if specs["free_disk_gb"] else "unknown"],
                     ["Python", specs["python"]]],
                ),
                tone="neutral",
            ),
            unsafe_allow_html=True,
        )
    if reco:
        st.markdown(
            card(
                f'{t("llm_reco_title", lang)} — {reco["model"]}',
                f'<div class="ip-strong">{reco["params"]} · '
                f'{t("llm_download", lang)} {reco["download_gb"]:.1f} GB · '
                f'{t("llm_needs", lang)} ≈ {reco["ram_gb"]} GB</div>'
                f'<div style="margin-top:6px;">{t("llm_why", lang)}: '
                f'<span class="ip-strong">{reco["why_ta"] if lang == "ta" else reco["why_en"]}'
                f'</span></div>'
                f'<div class="ip-muted" style="margin-top:6px;">{t("llm_tamil", lang)}: '
                f'{t("llm_tamil_" + reco["tamil"], lang)}</div>',
                tone="good" if reco["fits"] else "warn",
            ),
            unsafe_allow_html=True,
        )

    # ---- step 2: pick the model -------------------------------------------- #
    status = LOCAL_LLM.ollama_ready(cfg)
    installed_models = status["models"]
    options: List[str] = []
    for name in ([reco["model"]] if reco else []) + installed_models + \
            [entry["model"] for entry in LOCAL_LLM.MODEL_CATALOGUE]:
        if name not in options:
            options.append(name)
    current = str(ai_cfg.get("ollama_model") or LOCAL_LLM.DEFAULT_MODEL)
    have_current = any(m == current or m.startswith(f"{current}:") for m in installed_models)
    # the configured model is not on this machine but others are: offer what is there,
    # otherwise "Linked" stays red for a reason the user cannot see
    default_choice = current if (have_current or not installed_models) else installed_models[0]
    if current not in options:
        options.insert(0, current)
    choice = st.selectbox(t("llm_model", lang), options=options,
                          index=options.index(default_choice), key="llm_model_select")
    host = st.text_input(t("llm_host", lang), value=str(ai_cfg.get("ollama_host") or
                                                        LOCAL_LLM.ollama_host(cfg)),
                         key="llm_host_input",
                         help="http://127.0.0.1:11434 is the Ollama default")
    timeout_s = st.number_input(t("llm_timeout", lang), min_value=1, max_value=300,
                                value=int(ai_cfg.get("ollama_timeout_s", 30)),
                                key="llm_timeout_input")

    # ---- step 3: status + install ------------------------------------------ #
    st.markdown(
        card(
            t("llm_status_title", lang),
            table(
                [t("llm_step", lang), t("llm_state", lang)],
                [[t("llm_installed", lang),
                  ("✓ " + status["installed_detail"]) if status["installed"]
                  else ("✗ " + status["installed_detail"])],
                 [t("llm_server", lang),
                  ("✓ " + status["server_detail"]) if status["server_running"]
                  else ("✗ " + status["server_detail"])],
                 [t("llm_model_present", lang),
                  f'✓ {len(installed_models)} model(s): {", ".join(installed_models)}'
                  if installed_models else "✗ none downloaded yet"],
                 [t("llm_linked", lang),
                  "✓ linked — the intent engine will use this model"
                  if status["linked"] else "✗ not linked yet"]],
            ),
            tone="good" if status["linked"] else "warn",
        ),
        unsafe_allow_html=True,
    )

    if not status["linked"] and installed_models:
        if st.button(t("llm_link_now", lang), type="primary", key="llm_link_now_btn",
                     use_container_width=True):
            new_cfg, errors = apply_config(
                cfg, {"ai": {"engine": "ollama", "ollama_model": installed_models[0]},
                      "privacy": {"local_only": True}})
            if errors:
                st.session_state.cfg["ai"]["engine"] = "ollama"
                st.session_state.cfg["ai"]["ollama_model"] = installed_models[0]
            else:
                st.session_state.cfg = new_cfg
            notify(f"Linked to {installed_models[0]} — the intent engine now uses it.", "good")
            rerun()
    if not status["linked"] and installed_models:
        st.markdown(
            alert(
                (f'Pick <b>{installed_models[0]}</b> in “Model to use” above, then press '
                 f'<b>5. Use this model</b> — that is the only step left.')
                if lang == "en" else
                (f'மேலே உள்ள “Model to use”-ல் <b>{installed_models[0]}</b> என்பதைத் தேர்வு செய்து, '
                 f'<b>5. Use this model</b> அழுத்துங்கள் — மீதமுள்ள படி அது மட்டும்.'),
                "info",
            ),
            unsafe_allow_html=True,
        )

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button(t("llm_start_server", lang), key="llm_start_btn",
                     use_container_width=True):
            with st.spinner("Starting ollama serve…"):
                ok, detail = LOCAL_LLM.ollama_start_server(cfg)
            notify(detail, "good" if ok else "warn")
            rerun()
    with b2:
        if st.button(t("llm_pull", lang), key="llm_pull_btn", use_container_width=True):
            with st.spinner(f"Downloading {choice} — this can take a few minutes…"):
                ok, detail = LOCAL_LLM.ollama_pull(choice, cfg)
            st.session_state.llm_log.append(detail)
            notify(detail.splitlines()[-1] if detail else "done",
                   "good" if ok else "warn")
            rerun()
    with b3:
        if st.button(t("llm_test", lang), key="llm_test_btn", use_container_width=True):
            with st.spinner("Asking the local model…"):
                probe_cfg = {**cfg, "ai": {**ai_cfg, "ollama_model": choice,
                                           "ollama_host": host,
                                           "ollama_timeout_s": timeout_s}}
                result = LOCAL_LLM.test_link(probe_cfg)
            st.session_state.llm_log.append(str(result.get("detail")))
            notify(
                f'{t("llm_linked", lang)} ✓' if result["ok"]
                else f'{t("llm_not_linked", lang)} ({result["stage"]})',
                "good" if result["ok"] else "warn",
            )
            rerun()
    with b4:
        if st.button(t("llm_use_model", lang), key="llm_use_btn", use_container_width=True):
            payload = {"ai": {"ollama_model": choice, "engine": "ollama"},
                       "privacy": {"local_only": True}}
            if str(host or "").strip():
                payload["ai"]["ollama_host"] = str(host).strip()
            if isinstance(timeout_s, (int, float)) and timeout_s:
                payload["ai"]["ollama_timeout_s"] = int(timeout_s)
            new_cfg, errors = apply_config(cfg, payload)
            if errors:
                for error in errors:
                    st.markdown(alert(error, "bad"), unsafe_allow_html=True)
                # never leave the user stuck: fall back to the plain model choice
                st.session_state.cfg["ai"]["engine"] = "ollama"
                st.session_state.cfg["ai"]["ollama_model"] = choice
                notify(f"Intent engine now uses {choice} on this machine.", "good")
                rerun()
            else:
                st.session_state.cfg = new_cfg
                notify(f"Intent engine now uses {choice} on this machine.", "good")
                rerun()

    # ---- step 4: the exact commands, always visible ------------------------ #
    st.markdown(f"**{t('llm_commands', lang)}**")
    st.markdown(
        table(
            [t("llm_step", lang), t("llm_command", lang)],
            [[entry["label"], f'<code style="font-size:0.86rem;">{entry["command"]}</code>']
             for entry in LOCAL_LLM.install_commands()],
        ),
        unsafe_allow_html=True,
    )
    if st.session_state.llm_log:
        with st.expander(t("llm_log", lang)):
            for line in st.session_state.llm_log[-6:]:
                st.markdown(f'<div class="ip-muted" style="font-size:0.82rem;">{line}</div>',
                            unsafe_allow_html=True)
    st.markdown(
        alert(t("llm_boundary", lang), "info"),
        unsafe_allow_html=True,
    )


#  Page 2: money dashboard
# --------------------------------------------------------------------------- #


def page_dashboard() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_dashboard', lang)}", unsafe_allow_html=True)
    numbers = current_month_numbers()
    forecast = numbers["forecast"]

    tabs = st.tabs([t("sec_overview", lang), t("sec_spending", lang),
                    t("sec_safety", lang), t("sec_limits", lang)])

    # ---------------- overview ----------------
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi(t("total_spent", lang), money(numbers["spent"]),
                        f'{t("budget", lang)} {money(numbers["limit"])}',
                        "neutral"), unsafe_allow_html=True)
        c2.markdown(kpi(t("remaining", lang), money(max(numbers["remaining"], 0)),
                        f'{t("daily_allowance", lang)}: {money(numbers["daily_allowance"])}',
                        "good" if numbers["remaining"] > 0 else "bad"), unsafe_allow_html=True)
        c3.markdown(kpi(t("budget_used", lang), f'{numbers["utilisation"]:.0f}%',
                        f'{numbers["days_remaining"]} {t("days_remaining", lang).lower()}',
                        "good" if numbers["utilisation"] < 70 else (
                            "warn" if numbers["utilisation"] < 90 else "bad")),
                    unsafe_allow_html=True)
        c4.markdown(kpi(t("projected_month_end", lang), money(forecast["projected_month_end"]),
                        f'{t("forecast_confidence", lang)}: {forecast["confidence"]}',
                        "warn" if forecast["projected_overrun"] > 0 else "neutral"),
                    unsafe_allow_html=True)

        st.markdown(progress_bar(numbers["utilisation"],
                                 "good" if numbers["utilisation"] < 70 else (
                                     "warn" if numbers["utilisation"] < 90 else "bad")),
                    unsafe_allow_html=True)

        alerts: List[str] = []
        if numbers["state"] in ("NEAR LIMIT", "EXCEEDED"):
            alerts.append(alert(
                f'{t("total_spent", lang)}: {money(numbers["spent"])} — '
                f'{t("budget_used", lang)} {numbers["utilisation"]:.0f}%.', "warn"))
        if forecast["projected_overrun"] > 0:
            alerts.append(alert(
                f'{t("projected_overrun_note", lang)} '
                f'({money(forecast["projected_month_end"])} vs {money(numbers["limit"])}).', "warn"))
        commitments = detect_recurring(HISTORY)
        upcoming = upcoming_within(commitments, numbers["now"], days=7)
        if upcoming:
            alerts.append(alert(
                f'{t("recurring_upcoming", lang)}: '
                + ", ".join(f'{c["merchant"]} {money(c["amount"])}' for c in upcoming[:3]), "info"))
        uncategorised = HISTORY[HISTORY["category"] == "OTHER"]
        if len(uncategorised):
            alerts.append(alert(
                f'{len(uncategorised)} {t("uncategorised", lang)} — review them in the Spending tab.',
                "info"))
        for item in alerts:
            st.markdown(item, unsafe_allow_html=True)

        # ---- needs / wants / unnecessary (the elder-friendly split) ----
        triage = budget_engine.triage_summary(HISTORY, numbers["now"], CFG)
        triage_rows = []
        for bucket, icon in (("needs", "🍚"), ("wants", "🛍️"), ("unnecessary", "💸")):
            triage_rows.append([
                f"{icon} {t('triage_' + bucket, lang)}",
                money(triage["split"][bucket]),
                f'{triage["shares"][bucket]:.0f}%',
            ])
        triage_body = table([t("triage_title", lang), "₹", t("triage_share", lang)], triage_rows,
                            numeric_cols=[1, 2])
        triage_body += (
            f'<div class="ip-signal"><span>{t("triage_total", lang)}</span>'
            f'<span class="ip-num">{money(triage["total"])}</span></div>'
        )
        if triage["remaining"] >= 0:
            triage_body += (
                f'<div class="ip-signal"><span>{t("triage_remaining", lang)}</span>'
                f'<span class="ip-num">{money(triage["remaining"])}</span></div>'
            )
        st.markdown(
            card(t("triage_title", lang), triage_body + f'<div class="ip-muted" '
                 f'style="margin-top:6px;font-size:0.8rem;">{t("triage_note", lang)}</div>',
                 tone="warn" if triage["remaining"] < 0 else "neutral"),
            unsafe_allow_html=True,
        )
        if triage["remaining"] < 0:
            st.markdown(
                alert(f'⚠️ {t("triage_over", lang)} {money(abs(triage["remaining"]))}.', "bad"),
                unsafe_allow_html=True,
            )
        elif triage["remaining"] <= 0.15 * triage["limit"]:
            st.markdown(
                alert(f'⚠️ {t("triage_remaining", lang)} {money(triage["remaining"])}.', "warn"),
                unsafe_allow_html=True,
            )

        st.markdown(f'<div class="ip-muted" style="margin:14px 0 6px 0;">{t("trend_7d", lang)}</div>',
                    unsafe_allow_html=True)
        series = forecast["series"][-7:]
        st.bar_chart(pd.DataFrame({"spend": series}), height=180)

        recent = HISTORY.tail(8).iloc[::-1]
        st.markdown(f'<div style="margin:12px 0 6px 0;font-weight:650;">{t("recent_transactions", lang)}</div>',
                    unsafe_allow_html=True)
        rows = []
        for _, txn in recent.iterrows():
            rows.append([
                txn["timestamp"].strftime("%d %b %H:%M"),
                str(txn["merchant_label"]),
                category_label(str(txn["category"]), lang),
                money(txn["amount"]),
                "self" if txn["self_transfer"] else "",
            ])
        st.markdown(table(["when", "merchant", t("category", lang), t("amount", lang), ""],
                          rows, numeric_cols=[3]), unsafe_allow_html=True)

    # ---------------- spending ----------------
    with tabs[1]:
        cat_spend = budget_engine.category_spend(HISTORY, numbers["now"])
        limits = {"FOOD": float(CFG["budget"]["food_limit"])}
        rows = []
        total = sum(cat_spend.values())
        for category in dl.CATEGORY_ORDER:
            if category not in cat_spend:
                continue
            amount = cat_spend[category]
            limit = limits.get(category, 0.0)
            status = ""
            if limit:
                pct = 100.0 * amount / limit
                status = t("exceeded", lang) if pct >= 100 else f"{pct:.0f}%"
            rows.append([
                category_label(category, lang), money(amount),
                f"{100.0 * amount / total:.0f}%" if total else "",
                money(limit) if limit else "—", status,
            ])
        rows.append(["**" + t("total_spent", lang) + "**", money(total), "100%", "—", ""])
        st.markdown(table([t("category", lang), t("amount", lang), "share",
                           t("budget", lang), t("budget_used", lang)], rows,
                          numeric_cols=[1, 3]), unsafe_allow_html=True)

        st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
        st.markdown(f'**{t("change_category", lang)}** — '
                    '<span class="ip-muted">the categoriser learns from your corrections</span>',
                    unsafe_allow_html=True)
        needs_review = HISTORY[
            (HISTORY["category"] == "OTHER")
            | (HISTORY["category_confidence"] < LOW_CONFIDENCE)
        ].tail(10)
        if not len(needs_review):
            st.markdown('<div class="ip-muted">Nothing to review.</div>', unsafe_allow_html=True)
        for idx, (_, txn) in enumerate(needs_review.iterrows()):
            c1, c2, c3 = st.columns([2.4, 1.4, 1.2])
            c1.markdown(f'{txn["merchant_label"]} · {money(txn["amount"])} · '
                        f'{txn["timestamp"].strftime("%d %b")}', unsafe_allow_html=True)
            choice = c2.selectbox(
                "category", options=CATEGORIES, key=f"fix_{txn['id']}_{idx}",
                label_visibility="collapsed",
            )
            if c3.button(t("apply", lang), key=f"fix_btn_{txn['id']}_{idx}",
                         use_container_width=True):
                st.session_state.corrections.add(str(txn["merchant_label"]), choice)
                notify(f'Saved: "{txn["merchant_label"]}" → {category_label(choice, lang)}. '
                       "Future payments use this category.", "good")
                rerun()

    # ---------------- safety ----------------
    with tabs[2]:
        flow: PaymentFlow = st.session_state.flow
        if flow.result is not None:
            st.markdown(
                card(
                    f'{t("fraud_risk", lang)} — {t("score", lang)} {flow.result.fraud_risk:.0f}',
                    gauge(flow.result.fraud_risk, flow.result.band,
                          band_label(flow.result.band, lang))
                    + '<div class="ip-divider"></div>'
                    + signal_list(flow.result.explanation, lang),
                    tone=tone_for_band(flow.result.band),
                ),
                unsafe_allow_html=True,
            )
        events = [e for e in st.session_state.audit if e.get("event") == "payment_evaluated"]
        if events:
            rows = [
                [e.get("ts", "")[11:19], money(e.get("amount", 0)), str(e.get("payee", "")),
                 f'{e.get("fraud_risk", 0):.0f}', str(e.get("band", "")),
                 str(e.get("budget_band", ""))]
                for e in events[-12:][::-1]
            ]
            st.markdown(table(["time", t("amount", lang), "payee", "score", "fraud", "budget"],
                              rows, numeric_cols=[1, 3]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="ip-muted">Evaluate a payment in the simulator to see its '
                        'safety history here.</div>', unsafe_allow_html=True)
        st.markdown(
            alert("Risk scores are decision support, not proof of fraud. Completed UPI payments "
                  "cannot be reversed by this app — see Scam help.", "info"),
            unsafe_allow_html=True,
        )

    # ---------------- limits ----------------
    with tabs[3]:
        c1, c2 = st.columns(2)
        with c1:
            new_monthly = st.number_input(
                t("budget", lang) + " (₹)", min_value=0.0, max_value=1_000_000.0,
                value=float(CFG["budget"]["monthly_limit"]), step=500.0, key="limits_monthly")
            new_food = st.number_input(
                f'{category_label("FOOD", lang)} {t("budget", lang)} (₹)',
                min_value=0.0, max_value=1_000_000.0,
                value=float(CFG["budget"]["food_limit"]), step=250.0, key="limits_food")
            if st.button(t("apply", lang), key="limits_apply"):
                cfg_new, errors = apply_config(
                    CFG, {"budget": {"monthly_limit": new_monthly, "food_limit": new_food}}
                )
                if errors:
                    notify("; ".join(errors), "bad")
                else:
                    st.session_state.cfg = cfg_new
                    st.session_state.profile.monthly_limit = new_monthly
                    st.session_state.profile.category_limits["FOOD"] = new_food
                    notify("Budget limits updated — dashboard and payment checks recalculated.",
                           "good")
                    rerun()

        commitments = detect_recurring(HISTORY)
        disc = discretionary_allowance(HISTORY, CFG, numbers["now"], commitments)
        with c2:
            st.markdown(
                card(
                    t("discretionary", lang),
                    table([t("budget", lang), t("amount", lang)],
                          [[t("budget", lang), money(disc["monthly_limit"])],
                           [category_label("ESSENTIALS", lang) + " + " + t("budget", lang).lower(),
                            money(disc["essential_spent"])],
                           [t("recurring_upcoming", lang), money(disc["recurring_monthly_commitment"])],
                           ["**" + t("discretionary", lang) + "**", money(disc["remaining_discretionary"])]],
                          numeric_cols=[1]),
                    tone="neutral",
                ),
                unsafe_allow_html=True,
            )

        if commitments:
            rows = [
                [c["merchant"], money(c["amount"]), f'{c["median_gap_days"]:.0f}d',
                 c["next_expected"][:10], "yes" if c["amount_increased"] else ""]
                for c in commitments
            ]
            st.markdown(table(["merchant", t("amount", lang), "every", "next", "increased"],
                              rows, numeric_cols=[1]), unsafe_allow_html=True)
        else:
            st.markdown('<div class="ip-muted">No recurring payments detected yet.</div>',
                        unsafe_allow_html=True)
        st.markdown(
            '<div class="ip-muted" style="font-size:0.78rem;">NPCI UPI AutoPay already supports '
            'viewing / revoking mandates in your app. IntentPay adds the budget impact of those '
            'commitments; it does not claim to manage mandates.</div>',
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
#  Page 3: judge panel — every parameter live
# --------------------------------------------------------------------------- #


def _number_row(label: str, key_path: List[str], value: float, lo: float, hi: float,
                step: float, help_text: str = "") -> Optional[Dict[str, Any]]:
    section, name = key_path
    widget_key = f"cfg_{section}_{name}"
    entered = st.number_input(
        label, min_value=lo, max_value=hi, value=float(value), step=step,
        key=widget_key, help=help_text or None,
    )
    if float(entered) != float(value):
        return {section: {name: float(entered)}}
    return None


def page_judge() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_judge', lang)}", unsafe_allow_html=True)
    st.markdown(
        '<div class="ip-muted">Every engine parameter is live: change a value, press Apply, '
        'and the simulator, dashboard and metrics recalculate immediately. Invalid values are '
        'rejected and the last working configuration is kept.</div>',
        unsafe_allow_html=True,
    )

    # ---------------- engine parameters ----------------
    st.markdown(f"### {t('sec_config', lang)}")
    risk = CFG["risk"]
    budget = CFG["budget"]
    patch: Dict[str, Any] = {}

    st.markdown("**Risk fusion weights** *(must sum to 1.0)*")
    c1, c2, c3 = st.columns(3)
    with c1:
        w_t = st.number_input("transaction_weight", 0.0, 1.0, float(risk["transaction_weight"]),
                              0.05, key="w_t", help="weight of behavioural/transaction signals")
    with c2:
        w_i = st.number_input("intent_weight", 0.0, 1.0, float(risk["intent_weight"]), 0.05,
                              key="w_i", help="weight of the user's stated reason")
    with c3:
        w_r = st.number_input("beneficiary_weight", 0.0, 1.0, float(risk["beneficiary_weight"]),
                              0.05, key="w_r", help="weight of recipient intelligence")
    st.markdown(
        f'<div class="ip-muted" style="font-size:0.8rem;">sum = {w_t + w_i + w_r:.2f} '
        f'(1.00 required)</div>', unsafe_allow_html=True)
    patch["risk"] = {
        "transaction_weight": w_t, "intent_weight": w_i, "beneficiary_weight": w_r,
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        patch["risk"]["ask_intent_above"] = st.number_input(
            "ask_intent_above", 0.0, 100.0, float(risk["ask_intent_above"]), 1.0, key="ask_above",
            help="preliminary score above which IntentPay asks 'why are you paying?'")
    with c2:
        patch["risk"]["medium_threshold"] = st.number_input(
            "medium_threshold", 0.0, 100.0, float(risk["medium_threshold"]), 1.0, key="med_thr")
    with c3:
        patch["risk"]["high_threshold"] = st.number_input(
            "high_threshold", 0.0, 100.0, float(risk["high_threshold"]), 1.0, key="high_thr")
    patch["risk"]["critical_threshold"] = st.number_input(
        "critical_threshold", 0.0, 100.0, float(risk["critical_threshold"]), 1.0, key="crit_thr")

    st.markdown("**Anomaly model (Isolation Forest)**")
    c1, c2, c3 = st.columns(3)
    with c1:
        patch["risk"]["anomaly_blend"] = st.number_input(
            "anomaly_blend", 0.0, 1.0, float(risk["anomaly_blend"]), 0.05, key="blend",
            help="0 = pure rules, 1 = pure Isolation Forest")
    with c2:
        patch["risk"]["anomaly_contamination"] = st.number_input(
            "anomaly_contamination", 0.001, 0.5, float(risk["anomaly_contamination"]), 0.01,
            key="contamination", help="expected share of unusual payments in history")
    with c3:
        patch["risk"]["anomaly_n_estimators"] = int(st.number_input(
            "anomaly_n_estimators", 10, 500, int(risk["anomaly_n_estimators"]), 10,
            key="n_estimators", help="trees; 120 trains in <100 ms on demo data"))

    st.markdown("**Budget & forecast**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        patch["budget"] = {"monthly_limit": st.number_input(
            "monthly_limit", 0.0, 1_000_000.0, float(budget["monthly_limit"]), 500.0, key="b_monthly")}
    with c2:
        patch["budget"]["food_limit"] = st.number_input(
            "food_limit", 0.0, 1_000_000.0, float(budget["food_limit"]), 250.0, key="b_food")
    with c3:
        patch["budget"]["alert_at_percent"] = st.number_input(
            "alert_at_percent", 1.0, 100.0, float(budget["alert_at_percent"]), 5.0, key="b_alert")
    with c4:
        patch["budget"]["forecast_window_days"] = int(st.number_input(
            "forecast_window_days", 3, 60, int(budget["forecast_window_days"]), 1, key="b_window"))
    patch["budget"]["seasonality_factor"] = st.number_input(
        "seasonality_factor", 0.1, 5.0, float(budget["seasonality_factor"]), 0.1, key="b_season")

    if st.button(t("apply", lang), type="primary", key="cfg_apply"):
        new_cfg, errors = apply_config(CFG, patch)
        if errors:
            for error in errors:
                st.markdown(alert(error, "bad"), unsafe_allow_html=True)
        else:
            st.session_state.cfg = new_cfg
            st.session_state.profile.monthly_limit = float(new_cfg["budget"]["monthly_limit"])
            st.session_state.profile.category_limits["FOOD"] = float(new_cfg["budget"]["food_limit"])
            notify("Configuration applied — all pages recalculated.", "good")
            rerun()
    if st.button(t("reset_defaults", lang), key="cfg_reset"):
        st.session_state.cfg = _sync_profile_limits(default_config(), st.session_state.profile)
        notify("Factory defaults restored.", "info")
        rerun()

    # ---------------- customer data ----------------
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### {t('sec_customer', lang)}")
    profile = st.session_state.profile
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("name", value=profile.name, key="cust_name")
        st.number_input("age", 1, 120, int(profile.age), 1, key="cust_age")
        st.selectbox("usual_city", options=list(CITY_COORDS.keys()),
                     index=list(CITY_COORDS.keys()).index(profile.usual_city)
                     if profile.usual_city in CITY_COORDS else 0, key="cust_city")
        st.number_input("typical_amount", 1.0, 1_000_000.0, float(profile.typical_amount),
                        50.0, key="cust_typical")
    with c2:
        st.number_input("monthly_limit", 0.0, 1_000_000.0, float(profile.monthly_limit),
                        500.0, key="cust_limit")
        st.number_input("food_limit", 0.0, 1_000_000.0,
                        float(profile.category_limits.get("FOOD", 6000.0)), 250.0, key="cust_food")
        st.number_input("history seed", 1, 9999, int(profile.seed), 1, key="cust_seed",
                        help="same seed + same date = same demo history")
        st.multiselect("known_devices", options=[*profile.known_devices, "device-windows-02",
                                                 "device-unknown-99"],
                       default=list(profile.known_devices), key="cust_devices")
    payees = ", ".join(p.get("name", "") for p in profile.known_payees) or "—"
    st.markdown(
        card("Known payees (recipient intelligence)",
             f'<div>{payees}</div>'
             f'<div class="ip-muted" style="margin-top:6px;font-size:0.82rem;">Payments to these '
             f'UPI IDs are treated as known recipients; anything else is a new payee.</div>'),
        unsafe_allow_html=True,
    )
    if st.button(t("apply", lang) + " — " + t("sec_customer", lang), key="cust_apply"):
        profile.name = st.session_state.cust_name
        profile.age = int(st.session_state.cust_age)
        city = st.session_state.cust_city
        profile.usual_city = city
        profile.usual_lat, profile.usual_lon = CITY_COORDS[city]
        profile.typical_amount = float(st.session_state.cust_typical)
        profile.monthly_limit = float(st.session_state.cust_limit)
        profile.category_limits["FOOD"] = float(st.session_state.cust_food)
        profile.seed = int(st.session_state.cust_seed)
        profile.known_devices = list(st.session_state.cust_devices)
        st.session_state.cfg = _sync_profile_limits(st.session_state.cfg, profile)
        st.session_state.history = dl.load_history(profile.customer_id)
        notify(f"Customer data applied for {profile.name}. History regenerated (seed "
               f"{profile.seed}).", "good")
        rerun()

    # ---------------- spending triage map ----------------
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### {t('sec_budget', lang)} — {t('triage_title', lang)}")
    st.markdown(
        '<div class="ip-muted">Classify every category as a need, a want or unnecessary. '
        'The dashboard card (and the Tamil elder card) follows this map.</div>',
        unsafe_allow_html=True,
    )
    triage_patch: Dict[str, str] = {}
    tri_cols = st.columns(3)
    for index, category in enumerate(CATEGORIES):
        current = budget_engine.triage_of(category, CFG)
        with tri_cols[index % 3]:
            choice = st.selectbox(
                category_label(category, lang),
                options=list(budget_engine.TRIAGE_BUCKETS),
                index=list(budget_engine.TRIAGE_BUCKETS).index(current),
                key=f"triage_{category}",
                format_func=lambda bucket: t("triage_" + bucket, lang),
            )
            triage_patch[category] = choice
    if st.button(t("apply", lang) + " — " + t("triage_title", lang), key="triage_apply"):
        new_cfg, errors = apply_config(CFG, {"budget": {"triage_map": triage_patch}})
        if errors:
            for error in errors:
                st.markdown(alert(error, "bad"), unsafe_allow_html=True)
        else:
            st.session_state.cfg = new_cfg
            notify("Spending triage map applied.", "good")
            rerun()

    # ---------------- emergency PIN / decoy mode ----------------
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### 🛡️ {t('decoy_title', lang)}")
    st.markdown(f'<div class="ip-muted">{t("decoy_boundary", lang)}</div>', unsafe_allow_html=True)
    decoy_cfg = CFG.get("decoy", {}) or {}
    d1, d2, d3 = st.columns(3)
    with d1:
        decoy_pin = st.text_input("emergency_pin", value=str(decoy_cfg.get("emergency_pin", "9111")),
                                  key="decoy_pin_cfg", help="4-8 digits; demo value is 9111")
        decoy_balance = st.number_input("decoy_balance", min_value=0.0, step=100.0,
                                        value=float(decoy_cfg.get("decoy_balance", 1240.0)),
                                        key="decoy_balance_cfg")
    with d2:
        decoy_txn_limit = st.number_input(
            "decoy_transaction_limit", min_value=0.0, step=100.0,
            value=float(decoy_cfg.get("decoy_transaction_limit", 500.0)), key="decoy_txn_cfg",
            help="0 = no amount can ever be transferred in decoy mode")
        decoy_monthly = st.number_input(
            "decoy_monthly_limit", min_value=0.0, step=500.0,
            value=float(decoy_cfg.get("decoy_monthly_limit", 3000.0)), key="decoy_monthly_cfg")
    with d3:
        decoy_banner = st.checkbox("show_decoy_banner (prototype only)",
                                   value=bool(decoy_cfg.get("show_decoy_banner", True)),
                                   key="decoy_banner_cfg")
    if st.button(t("apply", lang) + " — " + t("decoy_title", lang), key="decoy_cfg_apply"):
        new_cfg, errors = apply_config(
            CFG,
            {"decoy": {"emergency_pin": decoy_pin, "decoy_balance": decoy_balance,
                       "decoy_transaction_limit": decoy_txn_limit,
                       "decoy_monthly_limit": decoy_monthly,
                       "show_decoy_banner": decoy_banner}},
        )
        if errors:
            for error in errors:
                st.markdown(alert(error, "bad"), unsafe_allow_html=True)
        else:
            st.session_state.cfg = new_cfg
            notify("Emergency PIN / decoy settings applied.", "good")
            rerun()

    # ---------------- AI engine ----------------
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### {t('sec_ai', lang)}")
    st.markdown(
        '<div class="ip-muted">The default LOCAL engine is a deterministic bilingual '
        '(English/Tamil) lexicon that works offline. EXTERNAL routes the reason text to a hosted '
        'LLM and falls back to LOCAL on any failure — the demo proves the fallback works.</div>',
        unsafe_allow_html=True,
    )
    engine_label = st.radio("engine", options=list(AI_LABELS.values()), key="ai_engine")
    engine = ENGINE_BY_LABEL.get(engine_label, "local")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Apply AI engine", key="ai_apply"):
            new_cfg, errors = apply_config(CFG, {"ai": {"engine": engine},
                                                 "privacy": {"local_only": engine == "local"}})
            if errors:
                for error in errors:
                    st.markdown(alert(error, "bad"), unsafe_allow_html=True)
            else:
                st.session_state.cfg = new_cfg
                notify(f"AI engine set to {engine.upper()}.", "good")
                rerun()
    with c2:
        if st.button("Simulate AI failure (fallback demo)", key="ai_fail"):
            st.session_state.cfg["ai"]["engine"] = "external"
            st.session_state.cfg["privacy"]["local_only"] = True  # no key -> forced fallback
            notify("External AI selected but no API key is present — every intent analysis now "
                   "falls back to the local engine. The payment flow never breaks.", "warn")
            rerun()
    if st.session_state.cfg["ai"]["engine"] == "external":
        import os

        has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("INTENTPAY_LLM_KEY"))
        st.markdown(
            alert(
                "API key detected — reason text will be sent to the hosted model."
                if has_key else
                "No API key found (set GEMINI_API_KEY in .env). The engine falls back to LOCAL "
                "automatically — try the 'Fake bank call' scenario to see it.",
                "info" if has_key else "warn",
            ),
            unsafe_allow_html=True,
        )
    render_local_llm_panel()

    # ---------------- privacy ----------------
    st.markdown(f"### {t('sec_privacy', lang)}")
    retention = st.number_input("retention_days", 0, 365, int(CFG["privacy"]["retention_days"]),
                                1, key="priv_retention")
    store_voice = st.checkbox("store_raw_voice", value=bool(CFG["privacy"]["store_raw_voice"]),
                              key="priv_voice",
                              help="default OFF — raw voice is processed then discarded")
    if st.button(t("apply", lang) + " — " + t("sec_privacy", lang), key="priv_apply"):
        new_cfg, errors = apply_config(CFG, {"privacy": {"retention_days": retention,
                                                        "store_raw_voice": store_voice}})
        if errors:
            for error in errors:
                st.markdown(alert(error, "bad"), unsafe_allow_html=True)
        else:
            st.session_state.cfg = new_cfg
            notify("Privacy settings applied.", "good")
            rerun()

    # ---------------- audit ----------------
    st.markdown('<hr class="ip-divider">', unsafe_allow_html=True)
    st.markdown(f"### {t('sec_audit', lang)}")
    events = list(reversed(st.session_state.audit))[:15]
    if events:
        rows = [[e.get("ts", "")[11:19], e.get("event", ""),
                 money(e.get("amount", 0) or 0), str(e.get("payee", "")),
                 f'{e.get("fraud_risk", 0):.0f}' if e.get("fraud_risk") is not None else ""]
                for e in events]
        st.markdown(table(["time", "event", t("amount", lang), "payee", "score"], rows,
                          numeric_cols=[2, 4]), unsafe_allow_html=True)
    else:
        st.markdown('<div class="ip-muted">No events yet.</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Page 4: accuracy & cost
# --------------------------------------------------------------------------- #


def _eval_payment(row: pd.Series, profile: Any, with_intent: bool = True) -> PaymentRequest:
    hour = int(row["hour"])
    when = datetime.now().replace(hour=hour, minute=30, second=0, microsecond=0)
    return PaymentRequest(
        amount=float(row["amount"]),
        method="UPI",
        payee_name=f"eval payee {row['eval_id']}",
        payee_upi=f"eval{row['eval_id']}@upi",
        purpose_category="OTHER",
        timestamp=when,
        city=profile.usual_city,
        lat=profile.usual_lat,
        lon=profile.usual_lon,
        on_call=bool(row["on_call"]),
        call_duration_s=int(row["call_duration_s"]),
        channel=str(row["channel"]),
        new_payee=bool(row["new_payee"]),
        device_id=profile.known_devices[0] if profile.known_devices else "",
        battery_pct=85,
        intent_text=str(row["purpose"]) if with_intent else None,
    )


def page_metrics() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_metrics', lang)}", unsafe_allow_html=True)
    st.markdown(
        f'<div class="ip-muted">{t("metrics_note", lang)} The set contains normal payments, '
        'deliberately signal-rich *legitimate* payments, and seven social-engineering families.</div>',
        unsafe_allow_html=True,
    )

    if st.button(f"▶ {t('metrics_run', lang)}", type="primary", key="metrics_run_btn"):
        with st.spinner(t("metrics_running", lang)):
            st.session_state.metrics = _run_metrics()
    metrics = st.session_state.metrics
    if not metrics:
        return

    overall = metrics["overall"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(kpi(t("metrics_precision", lang), f'{100 * overall["precision"]:.1f}%',
                    f'TP {overall["TP"]} / FP {overall["FP"]}', "neutral"), unsafe_allow_html=True)
    c2.markdown(kpi(t("metrics_recall", lang), f'{100 * overall["recall"]:.1f}%',
                    f'FN {overall["FN"]}', "neutral"), unsafe_allow_html=True)
    c3.markdown(kpi(t("metrics_f1", lang), f'{overall["f1"]:.3f}',
                    f'MCC {overall["mcc"]:.3f}', "good"), unsafe_allow_html=True)
    c4.markdown(kpi(t("metrics_fpr", lang), f'{100 * overall["fpr"]:.1f}%',
                    f'TN {overall["TN"]}', "neutral"), unsafe_allow_html=True)
    c5.markdown(kpi(t("metrics_latency", lang), f'{overall["latency"]["median_ms"]:.0f} ms',
                    f'p95 {overall["latency"]["p95_ms"]:.0f} ms', "neutral"), unsafe_allow_html=True)

    # ---- confusion matrix
    st.markdown(f"### {t('metrics_confusion', lang)}")
    tp, fp, fn, tn = overall["TP"], overall["FP"], overall["FN"], overall["TN"]
    cm_html = (
        '<table class="ip-table" style="max-width:520px;">'
        '<tr><th></th><th>predicted fraud</th><th>predicted ok</th></tr>'
        f'<tr><td><b>actual fraud</b></td>'
        f'<td style="background:#FEF2F2;color:#B91C1C;font-weight:700;">TP {tp}</td>'
        f'<td style="background:#FEF2F2;color:#B91C1C;">FN {fn}</td></tr>'
        f'<tr><td><b>actual ok</b></td>'
        f'<td style="background:#FFFBEB;color:#B45309;">FP {fp}</td>'
        f'<td style="background:#F0FDF4;color:#15803D;">TN {tn}</td></tr></table>'
    )
    st.markdown(cm_html, unsafe_allow_html=True)
    st.markdown(
        f'<div class="ip-muted" style="font-size:0.85rem;">interruption rate: '
        f'{100 * overall["interruption_rate"]:.1f}% of payments are asked '
        f'"why are you paying?" — the rest are never interrupted.</div>',
        unsafe_allow_html=True,
    )

    # ---- family breakdown
    st.markdown(f"### {t('metrics_family', lang)}")
    rows = []
    for f in metrics["family_table"]:
        if f["positives"] > 0:
            rows.append([f["family"], str(f["n"]), f'{100 * f["recall"]:.0f}%',
                         f'{100 * f["precision"]:.0f}%'])
        else:
            rows.append([f["family"], str(f["n"]), "-",
                         f'{f["fp"]} false alarm(s) of {f["n"]}'])
    st.markdown(table(["family", "n", t("metrics_recall", lang), t("metrics_precision", lang)],
                      rows, numeric_cols=[1]), unsafe_allow_html=True)

    # ---- ablation
    st.markdown(f"### {t('metrics_ablation', lang)}")
    rows = [[v["name"], v["description"], f'{v["f1"]:.3f}', f'{v["best_f1"]:.3f}',
             f'{100 * v["recall"]:.0f}%'] for v in metrics["ablation"]]
    st.markdown(table(["layer", "what it is", "F1 @ current threshold",
                       "best F1 (own threshold)", t("metrics_recall", lang)], rows,
                      numeric_cols=[2, 3]), unsafe_allow_html=True)
    st.markdown(
        '<div class="ip-muted" style="font-size:0.85rem;">The intent layer is what separates '
        'a coerced payment from an ordinary one — behaviour alone cannot see it.</div>',
        unsafe_allow_html=True,
    )

    # ---- threshold sweep
    st.markdown(f"### {t('metrics_threshold_sweep', lang)}")
    sweep = metrics["sweep"]
    best = metrics["best"]
    rows = [[f'{r["threshold"]:.0f}', f'{100 * r["precision"]:.1f}%', f'{100 * r["recall"]:.1f}%',
             f'{r["f1"]:.3f}'] for r in sweep]
    st.markdown(table(["threshold", t("metrics_precision", lang), t("metrics_recall", lang),
                       t("metrics_f1", lang)], rows, numeric_cols=[0, 1, 2, 3]),
                unsafe_allow_html=True)
    st.markdown(
        alert(
            f'F1-optimal threshold on this synthetic set: {best["threshold"]:.0f} '
            f'(F1 {best["f1"]:.3f}). Current decision threshold: '
            f'{CFG["risk"]["high_threshold"]:.0f}.',
            "info",
        ),
        unsafe_allow_html=True,
    )
    if st.button("Use F1-optimal threshold", key="apply_best_threshold"):
        target = int(best["threshold"])
        if not (CFG["risk"]["medium_threshold"] < target < CFG["risk"]["critical_threshold"]):
            notify("Optimal threshold conflicts with medium/critical bounds — adjust those first.",
                   "warn")
        else:
            new_cfg, errors = apply_config(CFG, {"risk": {"high_threshold": float(target)}})
            if errors:
                notify("; ".join(errors), "bad")
            else:
                st.session_state.cfg = new_cfg
                notify(f"high_threshold set to {target}.", "good")
                rerun()

    # ---- cost model
    st.markdown(f"### {t('metrics_loss', lang)}")
    st.markdown(
        '<div class="ip-muted">Loss = C_FN × missed frauds + C_FP × false alarms + '
        'λ × interruptions (Elkan 2001; Bahnsen et al. 2015). Missing a scam costs real money; '
        'a false alarm costs a few seconds of attention.</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c_fn = c1.number_input("C_FN (₹ per missed scam)", 0.0, 1_000_000.0, 25000.0, 1000.0,
                           key="cost_fn")
    c_fp = c2.number_input("C_FP (₹ per false alarm)", 0.0, 10_000.0, 15.0, 5.0, key="cost_fp")
    lam = c3.number_input("λ (friction weight)", 0.0, 100.0, 1.0, 1.0, key="cost_lambda")
    current_loss = metrics_mod.expected_loss(
        overall, c_fn, c_fp, lam, overall["interruption_rate"], overall["n"]
    )
    best_loss = metrics_mod.expected_loss(
        metrics["best_metrics"], c_fn, c_fp, lam,
        metrics["best_metrics"]["interruption_rate"], overall["n"],
    )
    c1.markdown(kpi("loss at current threshold", money(current_loss),
                    f'threshold {CFG["risk"]["high_threshold"]:.0f}', "neutral"),
                unsafe_allow_html=True)
    c2.markdown(kpi("loss at F1-optimal threshold", money(best_loss),
                    f'threshold {best["threshold"]:.0f}', "neutral"), unsafe_allow_html=True)
    c3.markdown(kpi("savings", money(max(current_loss - best_loss, 0)),
                    "cost model on synthetic data", "good"), unsafe_allow_html=True)


def _run_metrics() -> Optional[Dict[str, Any]]:
    """Evaluate the labelled set with the current configuration."""
    profile = st.session_state.profile
    if st.session_state.metrics_history is None:
        st.session_state.metrics_history = dl.load_history("customer_one")
    history = st.session_state.metrics_history
    eval_set = dl.load_eval_set()
    cfg = st.session_state.cfg
    threshold = float(cfg["risk"]["high_threshold"])
    ask_above = float(cfg["risk"]["ask_intent_above"])
    corrections = st.session_state.corrections.as_dict()

    def evaluator(row: pd.Series) -> Dict[str, Any]:
        payment = _eval_payment(row, profile, with_intent=True)
        result = evaluate_scenario(
            {
                "amount": payment.amount, "method": payment.method,
                "payee_name": payment.payee_name, "payee_upi": payment.payee_upi,
                "purpose_category": payment.purpose_category,
                "timestamp": payment.timestamp, "city": payment.city,
                "lat": payment.lat, "lon": payment.lon, "on_call": payment.on_call,
                "call_duration_s": payment.call_duration_s, "channel": payment.channel,
                "new_payee": payment.new_payee, "device_id": payment.device_id,
                "battery_pct": payment.battery_pct, "intent_text": payment.intent_text,
            },
            history, profile, cfg, corrections,
        )
        return {"score": result.fraud_risk, "latency_ms": result.latency_ms.get("total_ms", 0.0)}

    rows = [row for _, row in eval_set.iterrows()]
    evaluation = metrics_mod.evaluate_labelled(rows, evaluator, threshold, ask_above)

    # ablation: behaviour only / behaviour + anomaly / full engine
    ablation: List[Dict[str, Any]] = []
    variants = [
        ("Rules + recipient", "behaviour rules only (no anomaly model, no intent)",
         {"risk": {"anomaly_blend": 0.0}}, False),
        ("+ Isolation Forest", "adds behavioural anomaly layer",
         {}, False),
        ("+ Intent (full engine)", "adds the user's stated reason as a signal",
         {}, True),
    ]
    for name, description, cfg_patch, with_intent in variants:
        variant_cfg = copy.deepcopy(cfg)
        if cfg_patch:
            variant_cfg, errors = apply_config(variant_cfg, cfg_patch)
            if errors:
                continue

        def variant_evaluator(row: pd.Series, with_intent: bool = with_intent) -> Dict[str, Any]:
            payment = _eval_payment(row, profile, with_intent=with_intent)
            result = evaluate_scenario(
                {
                    "amount": payment.amount, "method": payment.method,
                    "payee_name": payment.payee_name, "payee_upi": payment.payee_upi,
                    "purpose_category": payment.purpose_category,
                    "timestamp": payment.timestamp, "city": payment.city,
                    "lat": payment.lat, "lon": payment.lon, "on_call": payment.on_call,
                    "call_duration_s": payment.call_duration_s, "channel": payment.channel,
                    "new_payee": payment.new_payee, "device_id": payment.device_id,
                    "battery_pct": payment.battery_pct, "intent_text": payment.intent_text,
                },
                history, profile, variant_cfg, corrections,
            )
            return {"score": result.fraud_risk, "latency_ms": result.latency_ms.get("total_ms", 0.0)}

        variant_eval = metrics_mod.evaluate_labelled(rows, variant_evaluator, threshold, ask_above)
        variant_sweep = metrics_mod.threshold_sweep(variant_eval["scores"], variant_eval["labels"])
        variant_best = metrics_mod.best_f1_threshold(variant_sweep)
        ablation.append(
            {
                "name": name,
                "description": description,
                "f1": variant_eval["overall"]["f1"],
                "best_f1": variant_best["f1"],
                "best_threshold": variant_best["threshold"],
                "recall": variant_eval["overall"]["recall"],
                "precision": variant_eval["overall"]["precision"],
            }
        )

    sweep = metrics_mod.threshold_sweep(evaluation["scores"], evaluation["labels"])
    best = metrics_mod.best_f1_threshold(sweep)
    best_pred = [1 if s >= best["threshold"] else 0 for s in evaluation["scores"]]
    best_metrics = metrics_mod.classification_metrics(evaluation["labels"], best_pred)
    interruptions_best = sum(1 for s in evaluation["scores"] if s >= ask_above)
    best_metrics["interruption_rate"] = round(interruptions_best / max(len(rows), 1), 4)
    best_metrics["n"] = len(rows)

    family_table = metrics_mod.family_breakdown(
        evaluation["families"], evaluation["scores"], evaluation["labels"], threshold
    )
    return {
        "overall": evaluation["overall"],
        "sweep": sweep,
        "best": best,
        "best_metrics": best_metrics,
        "ablation": ablation,
        "family_table": family_table,
    }


# --------------------------------------------------------------------------- #
#  Page 5: scam help
# --------------------------------------------------------------------------- #


def page_help() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_help', lang)}", unsafe_allow_html=True)
    st.markdown(
        alert(
            ("New to the app? <b>USER_MANUAL.PDF</b> in the project folder explains every page in "
             "plain language — no technical background needed. "
             "README.MD and RESOURCES/FORMULAS.MD are the technical versions.")
            if lang == "en" else
            ("பயன்பாட்டைப் பற்றி அறிய <b>USER_MANUAL.PDF</b> தான் சரி — தெளிவான மொழியில் ஒவ்வொரு "
             "பக்கத்தையும் விளக்குகிறது. தொழில்நுட்ப விவரங்களுக்கு README.MD மற்றும் "
             "RESOURCES/FORMULAS.MD."),
            "info",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(t("help_title", lang), "<ol style='margin:0;padding-left:18px;'>"
             + "".join(f"<li style='margin-bottom:6px;'>{step}</li>" for step in help_steps(lang))
             + "</ol>" + f'<div class="ip-muted" style="margin-top:8px;">'
               f"{golden_hour_note(lang)}</div>", tone="bad"),
        unsafe_allow_html=True,
    )

    flow: PaymentFlow = st.session_state.flow
    if flow.payment is not None and flow.result is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                card(t("utr", lang),
                     f'<div style="font-size:1.5rem;font-weight:750;">{flow.result.utr}</div>'
                     f'<div class="ip-muted" style="font-size:0.82rem;">Reference this ID with '
                     f'your bank and in the cybercrime portal.</div>', tone="dark"),
                unsafe_allow_html=True,
            )
            st.markdown(
                card(t("amount", lang),
                     f'<div style="font-size:1.5rem;font-weight:750;">'
                     f'{money(flow.payment.amount)}</div>'
                     f'<div class="ip-muted" style="font-size:0.82rem;">'
                     f'{flow.payment.payee_name} · {flow.payment.payee_upi}</div>',
                     tone="dark"),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(f'**{t("complaint_draft", lang)}**')
            st.code(complaint_draft(flow.payment, flow.result, st.session_state.profile, lang),
                    language="text")
            st.markdown('<div class="ip-muted" style="font-size:0.8rem;">Copy this into '
                        'cybercrime.gov.in and share it with your bank helpline.</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown(
            alert("Run a payment in the simulator first — the complaint draft will be filled with "
                  "its details automatically.", "info"),
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="ip-muted" style="margin-top:16px;font-size:0.85rem;">'
        'National cybercrime helpline: <b>1930</b> · Portal: <b>cybercrime.gov.in</b> · '
        'Suspect check: “Report &amp; Check Suspect” on the same portal. '
        'Banks and police never ask for OTP, UPI PIN or passwords — and no agency arrests '
        'anyone over a video call.</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
#  Page 6: about & research
# --------------------------------------------------------------------------- #


def page_about() -> None:
    lang = LANG
    st.markdown(f"## {t('nav_about', lang)}", unsafe_allow_html=True)
    st.markdown(
        card(
            "The product",
            f'<div style="font-weight:650;margin-bottom:6px;">{t("about_what", lang)}</div>'
            '<div class="ip-muted">Every fraud system asks “is this payment suspicious?” '
            'IntentPay asks “why are you paying?” — and answers “where did my money go?” '
            'around it. One engine, two levels of complexity: plain Tamil and voice for an '
            'older user, full scores and thresholds for a technical one.</div>'
            f'<div style="margin-top:8px;">{t("about_boundary", lang)}</div>',
            tone="info",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Architecture",
            table(
                ["layer", "file", "what it does"],
                [
                    ["features", "SRC/FEATURES.PY", "20+ behavioural signals (amount, velocity, location, call, battery, channel…)"],
                    ["anomaly", "SRC/ANOMALY.PY", "Isolation Forest on the customer's own history; percentile score"],
                    ["intent", "SRC/INTENT_ENGINE.PY", "bilingual social-engineering lexicon + optional LLM with fallback"],
                    ["recipient", "SRC/RISK_ENGINE.PY", "new payee, reports, handle type, verification"],
                    ["fusion", "SRC/RISK_ENGINE.PY", "weighted fraud score, bands, conditional intent prompt"],
                    ["budget", "SRC/BUDGET.PY + FORECAST.PY", "limits, category caps, robust median forecast"],
                    ["recurring", "SRC/RECURRING.PY", "commitment detection, discretionary allowance"],
                    ["explain", "SRC/EXPLAIN.PY", "ranked, bilingual, contribution-scored reasons"],
                    ["metrics", "SRC/METRICS.PY", "precision/recall/F1/FPR/MCC, threshold sweep, cost model"],
                    ["privacy", "SRC/VOICE.PY + CONFIG.PY", "local-only default, raw voice discarded, no PIN/OTP fields"],
                ],
            ),
            tone="neutral",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            t("layers_title", lang),
            table(
                ["layer", "in production", "in this prototype", "question it answers"],
                [[layer["layer"], layer["production"], layer["prototype"], layer["question"]]
                 for layer in EXPLAIN.MODEL_LAYERS],
            ),
            tone="neutral",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Research & references",
            '<ol style="margin:0;padding-left:18px;font-size:0.9rem;">'
            "<li>RBI Annual Report 2024-25 — digital payment frauds were 13,516 cases (56.5% of "
            "banking frauds, ₹520 crore); UPI did 185.8 bn transactions (+41.7%).</li>"
            "<li>LocalCircles survey (Jun 2025) — 1 in 5 Indian families hit by UPI fraud; "
            "51% filed no complaint anywhere.</li>"
            "<li>I4C advisory on “digital arrest” — CBI/Police/Customs/ED/Judges do not arrest "
            "over video calls; report on 1930 / cybercrime.gov.in.</li>"
            "<li>NPCI UPI AutoPay enhancement (circular OC-223, Oct 2025) — view, revoke, pause, "
            "modify mandates.</li>"
            "<li>Google Pay “Ask Google Pay” (2026) — Gemini spending insights, ten Indian "
            "languages.</li>"
            "<li>Hybrid ML + anomaly detection for UPI fraud (IJIRT 178524, 2025) — Random "
            "Forest / Isolation Forest flagged 87% of outlier transactions, &lt;300 ms per "
            "evaluation.</li>"
            "<li>Elkan (2001) &amp; Bahnsen et al. (2015) — cost-sensitive fraud evaluation; "
            "accuracy is misleading under class imbalance.</li>"
            "<li>Threshold optimisation for F1/F2/MCC in imbalanced fraud detection "
            "(IRJMETS, 2025).</li>"
            "</ol>",
            tone="neutral",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        card(
            "Limitations (honest)",
            '<ul style="margin:0;padding-left:18px;font-size:0.9rem;">'
            "<li>Synthetic data proves the pipeline, not production accuracy.</li>"
            "<li>The intent lexicon can misread colloquial speech; scores are decision support, "
            "never proof of fraud.</li>"
            "<li>Merchant categorisation can be wrong — hence corrections are one tap.</li>"
            "<li>Forecasts can be wrong; thin history is labelled low confidence.</li>"
            "<li>A standalone app has no bank/NPCI private intelligence; recipient intelligence "
            "here is a demo feed.</li>"
            "<li>Budget warnings are guidance, not financial advice; this app cannot reverse a "
            "completed UPI payment.</li>"
            "</ul>",
            tone="warn",
        ),
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
#  Dispatch
# --------------------------------------------------------------------------- #

PAGES = {
    "nav_pay": page_pay,
    "nav_dashboard": page_dashboard,
    "nav_judge": page_judge,
    "nav_metrics": page_metrics,
    "nav_help": page_help,
    "nav_about": page_about,
}

PAGES.get(st.session_state.get("page_key", "nav_pay"), page_pay)()

st.markdown(
    '<hr class="ip-divider"><div class="ip-muted" style="font-size:0.75rem;text-align:center;">'
    'IntentPay · NAS CODERS · synthetic-data prototype · no UPI PIN/OTP/password is ever '
    'requested · completed UPI payments cannot be reversed by this app'
    '</div>',
    unsafe_allow_html=True,
)
