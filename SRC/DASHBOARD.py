"""Flat, pure-white HTML component kit used by the Streamlit UI.

Design contract (from the brief): pure white background, no glassmorphism, no
gradients, no shadows-as-decoration, consistent alignment, generous touch
targets in elder mode.  Everything is inline-styled so it renders identically
in the app, in an exported report and in a screenshot.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from SRC.MODELS import inr

TONES: Dict[str, Dict[str, str]] = {
    "neutral": {"fg": "#0F172A", "bg": "#FFFFFF", "bd": "#E2E8F0", "muted": "#64748B"},
    "good": {"fg": "#15803D", "bg": "#F0FDF4", "bd": "#BBF7D0", "muted": "#166534"},
    "warn": {"fg": "#B45309", "bg": "#FFFBEB", "bd": "#FDE68A", "muted": "#92400E"},
    "bad": {"fg": "#B91C1C", "bg": "#FEF2F2", "bd": "#FECACA", "muted": "#991B1B"},
    "info": {"fg": "#1D4ED8", "bg": "#EFF6FF", "bd": "#BFDBFE", "muted": "#1E40AF"},
    "dark": {"fg": "#0F172A", "bg": "#F8FAFC", "bd": "#CBD5E1", "muted": "#334155"},
}

RISK_TONE = {"LOW": "good", "MEDIUM": "warn", "HIGH": "bad", "CRITICAL": "bad"}
BUDGET_TONE = {"LOW": "good", "MEDIUM": "warn", "HIGH": "bad"}


def tone_for_band(band: str) -> str:
    return RISK_TONE.get(band, "neutral")


def inject_css(font_scale: float = 1.0, elder_mode: bool = False) -> str:
    """Global stylesheet: white canvas, flat cards, tight alignment.

    The app is **light-mode by design**.  Streamlit follows the operating system's
    colour scheme, so on a machine set to dark the widgets keep their dark theme
    while the page canvas is forced white here — which leaves near-black buttons
    with near-black labels (the scenario chips became unreadable).  Two things fix
    that for good: the browser is told the page is light-only (`color-scheme`), and
    every widget surface is painted explicitly instead of relying on the theme.
    """
    scale = float(font_scale) * (1.12 if elder_mode else 1.0)
    base = 15 * scale
    return f"""
<style>
    :root {{ color-scheme: light !important; }}
    html, body {{
        background-color: #FFFFFF !important;
        color-scheme: light !important;
    }}
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stBottom"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [class*="stAppViewContainer"], [class*="stMain"], [class*="stSidebar"] {{
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }}
    /* native form controls must not follow the OS dark preference either */
    input, textarea, select, button, [contenteditable] {{
        color-scheme: light !important;
    }}
    [data-testid="stAppViewBlockContainer"] {{
        padding-top: 1.2rem;
        max-width: 1240px;
    }}
    [data-testid="stSidebar"] {{
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }}
    h1, h2, h3, h4, h5, p, li, label, .stMarkdown {{
        font-family: "Segoe UI", "Nirmala UI", Roboto, Arial, sans-serif !important;
        color: #0F172A !important;
    }}
    h1 {{ font-size: {1.55 * scale:.2f}rem !important; font-weight: 700 !important; letter-spacing: -0.01em; }}
    h2 {{ font-size: {1.18 * scale:.2f}rem !important; font-weight: 700 !important; }}
    h3 {{ font-size: {1.02 * scale:.2f}rem !important; font-weight: 650 !important; }}
    p, li {{ font-size: {base / 16:.2f}rem !important; line-height: 1.5; }}
    .ip-card {{
        border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 16px;
        background: #FFFFFF; margin-bottom: 12px;
    }}
    .ip-card h4 {{
        margin: 0 0 8px 0; font-size: {0.82 * scale:.2f}rem; font-weight: 650;
        text-transform: uppercase; letter-spacing: 0.06em; color: #64748B;
    }}
    .ip-kpi-value {{ font-size: {1.6 * scale:.2f}rem; font-weight: 700; line-height: 1.15; }}
    .ip-kpi-sub {{ font-size: {0.82 * scale:.2f}rem; color: #64748B; margin-top: 2px; }}
    .ip-badge {{
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: {0.76 * scale:.2f}rem; font-weight: 700; letter-spacing: 0.04em;
        border: 1px solid; white-space: nowrap;
    }}
    .ip-table {{ width: 100%; border-collapse: collapse; font-size: {0.9 * scale:.2f}rem; }}
    .ip-table th {{
        text-align: left; color: #64748B; font-weight: 650; font-size: {0.76 * scale:.2f}rem;
        text-transform: uppercase; letter-spacing: 0.05em; padding: 7px 10px;
        border-bottom: 1px solid #E2E8F0;
    }}
    .ip-table td {{ padding: 8px 10px; border-bottom: 1px solid #F1F5F9; vertical-align: middle; }}
    .ip-table tr:last-child td {{ border-bottom: none; }}
    .ip-num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .ip-row {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: stretch; }}
    .ip-row > * {{ flex: 1 1 0; min-width: 0; }}
    .ip-gauge-track {{
        position: relative; height: {elder_mode and 18 or 14}px; border-radius: 999px;
        background: #F1F5F9; border: 1px solid #E2E8F0; overflow: hidden;
    }}
    .ip-gauge-fill {{ height: 100%; border-radius: 999px 0 0 999px; }}
    .ip-gauge-marker {{
        position: absolute; top: -3px; width: 3px; height: calc(100% + 6px);
        background: #0F172A; border-radius: 2px;
    }}
    .ip-bar-track {{ height: 9px; background: #F1F5F9; border-radius: 999px; overflow: hidden; }}
    .ip-bar-fill {{ height: 100%; border-radius: 999px; }}
    .ip-signal {{ display: flex; justify-content: space-between; gap: 10px; padding: 6px 0;
        border-bottom: 1px dashed #F1F5F9; font-size: {0.92 * scale:.2f}rem; }}
    .ip-signal:last-child {{ border-bottom: none; }}
    .ip-muted {{ color: #64748B !important; }}
    .ip-strong {{ font-weight: 700; }}
    .ip-divider {{ border: none; border-top: 1px solid #E2E8F0; margin: 14px 0; }}
    /* buttons: modern selector first (stButton wrapper), legacy kept for safety */
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button,
    [data-testid="stFormSubmitButton"] button, [data-testid="stLinkButton"] a,
    .stButton > button {{
        border-radius: 8px !important; border: 1px solid #CBD5E1 !important;
        background: #FFFFFF !important; color: #0F172A !important;
        font-family: "Segoe UI", "Nirmala UI", Roboto, Arial, sans-serif !important;
        font-weight: 600 !important; font-size: {0.92 * scale:.2f}rem !important;
        padding: {elder_mode and "0.7rem 1.1rem" or "0.45rem 0.9rem"} !important;
        box-shadow: none !important; line-height: 1.35 !important;
        white-space: normal !important;
    }}
    [data-testid="stButton"] button *, [data-testid="stDownloadButton"] button *,
    .stButton > button * {{ color: #0F172A !important; }}
    [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover,
    .stButton > button:hover {{ background: #F8FAFC !important; border-color: #94A3B8 !important; }}
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"],
    .stButton > button[kind="primary"] {{
        background: #1D4ED8 !important; border-color: #1D4ED8 !important; color: #FFFFFF !important;
    }}
    [data-testid="stButton"] button[kind="primary"] *,
    [data-testid="stDownloadButton"] button[kind="primary"] *,
    [data-testid="stFormSubmitButton"] button[kind="primary"] *,
    .stButton > button[kind="primary"] * {{ color: #FFFFFF !important; }}
    [data-testid="stButton"] button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover {{ background: #1E40AF !important; }}
    [data-testid="stButton"] button:disabled, .stButton > button:disabled {{
        background: #F1F5F9 !important; color: #94A3B8 !important; border-color: #E2E8F0 !important;
    }}
    /* inputs, selectboxes and their dropdowns: white surface, dark text */
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input, [data-testid="stTextInput"] div,
    [data-testid="stTextArea"] div, [data-testid="stNumberInput"] div,
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div, [data-baseweb="select"] input {{
        background-color: #FFFFFF !important; color: #0F172A !important;
        border-color: #CBD5E1 !important; caret-color: #0F172A !important;
    }}
    [data-baseweb="select"] span, [data-baseweb="select"] div {{ color: #0F172A !important; }}
    [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="popover"] *,
    [role="listbox"], [role="option"], [role="listbox"] * {{ 
        background-color: #FFFFFF !important; color: #0F172A !important;
    }}
    [role="option"]:hover, [role="option"][aria-selected="true"] {{
        background-color: #EFF6FF !important; color: #1D4ED8 !important;
    }}
    input::placeholder, textarea::placeholder {{ color: #94A3B8 !important; opacity: 1 !important; }}
    /* checkboxes, radios, sliders, expanders, tabs, alerts */
    [data-testid="stCheckbox"] label, [data-testid="stCheckbox"] label *,
    [data-testid="stRadio"] label, [data-testid="stRadio"] label *,
    [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] *,
    label, .stMarkdown, .stMarkdown * {{ color: #0F172A !important; }}
    [data-testid="stExpander"] details, [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary * {{
        background-color: #FFFFFF !important; color: #0F172A !important;
    }}
    [data-testid="stExpander"] details[open] > div:last-child {{ background-color: #FFFFFF !important; }}
    [data-testid="stTabs"] button, [data-testid="stTabs"] button * {{
        color: #0F172A !important;
    }}
    [data-testid="stAlert"], [data-testid="stAlert"] * {{ color: #0F172A !important; }}
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
        color: #0F172A !important;
    }}
    [data-testid="stSlider"] div {{ color: #0F172A !important; }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{ background-color: #FFFFFF !important; }}
    [data-testid="stSidebar"] * {{ color: #0F172A !important; }}
    [data-testid="stSidebar"] [data-testid="stButton"] button {{ background: #FFFFFF !important; }}
    [data-testid="stSidebar"] [data-testid="stButton"] button * {{ color: #0F172A !important; }}
    [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
    .stAlert {{ border-radius: 8px !important; }}
    footer {{ visibility: hidden; }}
    #MainMenu {{ visibility: hidden; }}
</style>
"""


def card(title: Optional[str], body_html: str, tone: str = "neutral") -> str:
    palette = TONES[tone]
    heading = f"<h4>{title}</h4>" if title else ""
    return (
        f'<div class="ip-card" style="border-color:{palette["bd"]};background:{palette["bg"]};">'
        f"{heading}{body_html}</div>"
    )


def kpi(label: str, value: str, sub: str = "", tone: str = "neutral") -> str:
    palette = TONES[tone]
    sub_html = f'<div class="ip-kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="ip-card" style="border-color:{palette["bd"]};">'
        f'<h4 style="color:{palette["muted"]};">{label}</h4>'
        f'<div class="ip-kpi-value" style="color:{palette["fg"]};">{value}</div>{sub_html}</div>'
    )


def badge(text: str, tone: str = "neutral") -> str:
    palette = TONES[tone]
    return (
        f'<span class="ip-badge" style="color:{palette["fg"]};background:{palette["bg"]};'
        f'border-color:{palette["bd"]};">{text}</span>'
    )


def band_badge(band: str, label: Optional[str] = None) -> str:
    return badge(label or band, tone_for_band(band))


def progress_bar(pct: float, tone: str = "info", show_pct: bool = True) -> str:
    palette = TONES[tone]
    width = max(0.0, min(100.0, float(pct)))
    label = f"{width:.0f}%" if show_pct else ""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div class="ip-bar-track" style="flex:1;">'
        f'<div class="ip-bar-fill" style="width:{width:.1f}%;background:{palette["fg"]};"></div></div>'
        f'<span style="font-variant-numeric:tabular-nums;color:{palette["fg"]};font-weight:650;'
        f'min-width:44px;text-align:right;">{label}</span></div>'
    )


def gauge(score: float, band: str, label: Optional[str] = None) -> str:
    """0-100 risk gauge with band segments and a position marker."""
    palette = TONES[tone_for_band(band)]
    width = max(0.0, min(100.0, float(score)))
    segments = (
        '<div style="position:absolute;left:0;top:0;bottom:0;width:30%;background:#F0FDF4;"></div>'
        '<div style="position:absolute;left:30%;top:0;bottom:0;width:25%;background:#FFFBEB;"></div>'
        '<div style="position:absolute;left:55%;top:0;bottom:0;width:20%;background:#FEF2F2;"></div>'
        '<div style="position:absolute;left:75%;top:0;bottom:0;width:25%;background:#FEE2E2;"></div>'
    )
    return (
        f'<div style="position:relative;">'
        f'<div class="ip-gauge-track">{segments}'
        f'<div class="ip-gauge-marker" style="left:calc({width:.1f}% - 1px);"></div></div>'
        f'<div style="display:flex;justify-content:space-between;margin-top:5px;'
        f'font-size:0.72rem;color:#64748B;">'
        f"<span>0</span><span>30</span><span>55</span><span>75</span><span>100</span></div>"
        f'<div style="margin-top:6px;display:flex;align-items:baseline;gap:10px;">'
        f'<span style="font-size:2rem;font-weight:750;color:{palette["fg"]};'
        f'font-variant-numeric:tabular-nums;">{score:.0f}</span>'
        f'<span style="color:#64748B;">/ 100</span>'
        f"{band_badge(band, label)}</div></div>"
    )


def component_row(label: str, value: Optional[float], note: str = "") -> str:
    if value is None:
        return (
            f'<div class="ip-signal"><span>{label}</span>'
            f'<span class="ip-muted">{note or "not provided"}</span></div>'
        )
    tone = "good" if value < 30 else ("warn" if value < 55 else "bad")
    return (
        f'<div class="ip-signal"><span>{label}</span>'
        f'<span style="display:flex;align-items:center;gap:10px;min-width:180px;">'
        f'<span style="flex:1;max-width:150px;">{progress_bar(value, tone, show_pct=False)}</span>'
        f'<span class="ip-num ip-strong" style="color:{TONES[tone]["fg"]};">{value:.0f}</span>'
        f"</span></div>"
    )


def signal_list(items: Sequence[Dict[str, Any]], lang: str = "en") -> str:
    if not items:
        return '<p class="ip-muted">No notable risk signals.</p>'
    rows = []
    for item in items:
        text = item.get(f"text_{lang}") or item.get("text_en", "")
        tone = {"high": "bad", "medium": "warn", "low": "neutral"}.get(item.get("severity"), "neutral")
        rows.append(
            f'<div class="ip-signal"><span style="color:{TONES[tone]["fg"]};">{text}</span>'
            f'<span class="ip-muted ip-num">+{item.get("contribution", 0):.0f}</span></div>'
        )
    return "".join(rows)


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    numeric_cols: Optional[Sequence[int]] = None,
) -> str:
    numeric = set(numeric_cols or [])
    head = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = []
        for idx, cell in enumerate(row):
            css = ' class="ip-num"' if idx in numeric else ""
            cells.append(f"<td{css}>{cell}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table class="ip-table"><thead><tr>' + head + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table>"
    )


def alert(message: str, tone: str = "info", title: str = "") -> str:
    palette = TONES[tone]
    heading = (
        f'<div style="font-weight:700;margin-bottom:3px;color:{palette["fg"]};">{title}</div>'
        if title
        else ""
    )
    return (
        f'<div class="ip-card" style="border-color:{palette["bd"]};background:{palette["bg"]};'
        f'padding:11px 14px;margin-bottom:10px;">{heading}'
        f'<div style="color:{palette["muted"]};">{message}</div></div>'
    )


def money(amount: Any) -> str:
    return inr(amount)


def chip_row(items: Sequence[Dict[str, str]]) -> str:
    """Small labelled chips (used for scenario hints)."""
    chips = "".join(
        f'<span class="ip-badge" style="color:#334155;background:#F8FAFC;border-color:#E2E8F0;'
        f'margin:2px 4px 2px 0;">{item["label"]}</span>'
        for item in items
    )
    return f'<div style="margin:6px 0 10px 0;">{chips}</div>'
