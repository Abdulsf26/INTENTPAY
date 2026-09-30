# IntentPay — AI Payment Intent Guardian + Personal Financial Guardian

**Team: NAS CODERS** · CitiBank fintech hackathon prototype · synthetic data, runs fully offline

> Every fraud system asks *"is this payment suspicious?"*
> IntentPay asks ***"why are you paying?"*** — and answers *"where did my money go?"* around it.

IntentPay is a **pre-payment safety layer + personal finance layer** in one app. Before a risky
payment leaves an account it analyses the transaction, the recipient, and — the novel part — the
**user's own stated reason for paying**, looking for the social-engineering patterns behind
India's biggest fraud waves (fake-bank calls, "digital arrest", lottery fees, refund-QR scams,
fake customer care, job fees). Around every payment it keeps the user's money legible:
categorised spending, category and monthly limits, robust forecasting, and recurring-commitment
impact.

---

## 1. Run it (Windows, one click)

1. Install **Python 3.10+** from <https://www.python.org/downloads/> (tick *Add python.exe to PATH*).
2. **Double-click `START_HERE.BAT`.** It creates the virtual environment, installs dependencies,
   and opens the app at <http://127.0.0.1:8501>.

That's the whole install. `INSTALL.BAT` / `RUN.BAT` split the same steps if you prefer.
Optional voice packages install automatically and are never required (typing works identically).

```bat
START_HERE.BAT          :: setup + launch (recommended)
INSTALL.BAT             :: setup only
RUN.BAT                 :: launch only
python -m streamlit run APP.py   :: manual launch after activating .venv
```

No internet is needed after installation for the core demo. No UPI PIN / OTP / password is ever
requested, stored, or transmitted — there is no such field anywhere in the app.

Deep links open a page directly: <http://127.0.0.1:8501/?page=nav_dashboard> (or `nav_pay`,
`nav_judge`, `nav_metrics`, `nav_help`, `nav_about`).

---

## 2. The 6 pages

| Page | What a judge can do there |
|---|---|
| **Payment simulator** | Fill any payment (amount, type, recipient, time, location, channel, on-call, battery, device, reason) → see fraud score, component scores, budget impact, ranked explanations and a simulated UPI handoff. The card says **whether the reason is requested** and blocks for it when the preliminary score is high. 10 one-click scenarios + the **golden demo** (same ₹25,000, two different reasons → two different verdicts). Voice questions ("how much did I spend this month?"). Below the result: **why this score** (SHAP-style attribution that adds up), the **UPI black box** and the **emergency PIN / decoy mode**. |
| **Money dashboard** | This month's spend / budget / remaining, forecast, category breakdown with one-tap category corrections, payment-safety history, limits, recurring commitments — and the new **needs / wants / unnecessary** split (₹6,227 needs · ₹6,036 wants · ₹430 unnecessary of ₹12,693 spent) in English and தமிழ். |
| **Judge panel** | **Every engine parameter live**: fusion weights, thresholds, anomaly blend/contamination/trees, budget limits, **needs/wants/unnecessary triage map**, **emergency PIN + decoy balance/limits**, forecast window, customer data (name, city, limits, devices, history seed), **AI engine switch including a local Ollama model** (detects the machine, recommends a model that fits, installs/starts/downloads it and proves the link), privacy settings, local audit trail, JSON report export, SAFE DEMO RESET. |
| **Accuracy & cost** | Labelled evaluation of 385 synthetic payments: precision / recall / F1 / FPR / MCC, confusion matrix, per-scam-family recall, layer ablation, F1 threshold sweep with one-click apply, and a cost-sensitive loss model (`C_FN·FN + C_FP·FP + λ·friction`). On the shipped set: **P 0.94 · R 0.83 · F1 0.89 · FPR 4.3 %**, F1-optimal threshold 45 → F1 0.94. |
| **Scam help** | The honest post-scam path: 1930 helpline, cybercrime.gov.in, bank dispute with the UTR, evidence checklist — plus a copy-ready complaint draft built from the last payment. |
| **About & research** | Positioning, architecture, citations, limitations — and the **four production layers** table (behaviour → connections → transaction details → fusion → explanation), with the production counterpart and the prototype implementation side by side. |

---

## 3. How the safety engine works

```
payment ──► features (20+ signals) ──► ┌─ transaction risk  (rules + Isolation Forest)
                                       ├─ recipient risk    (new payee, reports, handle)
                                       └─ intent risk       (your reason, EN + TA)
                                                │
                                    weighted fusion (w_t, w_i, w_r)
                                                │
                          band: LOW / MEDIUM / HIGH / CRITICAL
                                                │
        if preliminary score ≥ ask_intent_above ──► "Why are you paying?" (re-check)
                                                │
                     fraud risk  ⊕  budget impact  ──► recommendation
```

* **Transaction risk** = `(1 − blend) · rule_score + blend · anomaly_score`. The Isolation Forest
  is trained on *this customer's own history* (unsupervised, no labels), and its score is a
  tail-scaled percentile: median behaviour → 0, top ~5 % → ~100.
* **Intent risk** = a deterministic bilingual weighted lexicon over 12 social-engineering
  families with combination bonuses (authority+threat, safe-account+authority, refund-QR+OTP…).
  Two optional engines can replace it — a **local model on your own machine (Ollama)** and a
  hosted LLM — and **any failure falls back to the lexicon**; the payment flow never breaks.
  The Judge panel's local-AI block detects RAM/CPU/GPU/disk, recommends the largest model that
  fits (2 B → 14 B), runs `ollama serve` / `ollama pull`, and proves the link with a live probe.
* **Fraud risk** = `w_t·transaction + w_i·intent + w_r·recipient` (default 0.40 / 0.45 / 0.15,
  validated to sum to 1). Missing intent redistributes weight honestly instead of pretending
  to zero risk.
* **Budget risk is a separate dimension** (limits, category caps, median-based forecast). The
  fusion truth table combines them: low-fraud + high-budget → budget warning; high-fraud +
  high-budget → strong warning; and a self-transfer is never counted as spending.
* Everything is **explainable**: each score ships ranked, contribution-scored reasons in
  English and Tamil, plus a **SHAP-style attribution table that adds up to the score itself**
  (worst gap 0.20 points across all ten scenarios — the decomposition is exact, so no judge can
  find a "mystery" 10 points), plus per-stage latency.
* Every payment also writes a **UPI black box**: a SHA-256 hash-chained log of what the app
  saw, decided and showed, with a tamper demo that proves an edited or deleted entry is
  detectable, and a JSON incident export.
* An **emergency PIN** opens a decoy environment with its own balance and limits, so a payment
  forced under duress cannot touch the real money. Both of these are clearly labelled
  simulations in the UI — see §6.

All formulas are written out in [`RESOURCES/FORMULAS.MD`](RESOURCES/FORMULAS.MD).

---

## 4. Demo script (14 minutes)

See [`RESOURCES/DEMO_SCRIPT.MD`](RESOURCES/DEMO_SCRIPT.MD) for the full minute-by-minute script
and the judge-question cheat sheet. The short version:

| Time | Move |
|---|---|
| 0:00 | The problem: UPI fraud is at record scale and 1 in 5 families has been hit |
| 1:00 | Normal ₹500 grocery → LOW, no interruption |
| 2:00 | New payee ₹25,000 → *"Why are you paying?"* → type a reason → score moves |
| 3:00 | Fake bank call → CRITICAL (authority + urgency + safe account) |
| 4:00 | Tamil elder mode: same story in தமிழ், voice answer |
| 5:00 | Dashboard: ₹12,693 / ₹15,000, forecast, food at 92 % |
| 6:00 | Food ₹1,200 → **low fraud, high budget impact** — two different problems |
| 7:00 | Digital arrest → CRITICAL + scam help (1930 / cybercrime.gov.in) |
| 8:00 | Judge panel: change weights/thresholds live and watch every page follow |
| 9:00 | **Why this score**: attribution that adds up, and the four-layer production mapping |
| 10:00 | **UPI black box**: verify the chain, then tamper with an entry and watch it break |
| 11:00 | **Emergency PIN → decoy mode**: ₹25,000 blocked by the ₹500 decoy limit, ₹200 simulated |
| 12:00 | Accuracy & cost: F1 ≈ 0.89 (P 0.94 / R 0.83), ablation showing what the intent layer adds |
| 13:00 | **Local AI**: detect the machine → recommended model → start server → download → link |
| 14:00 | Privacy: local-only indicator, SAFE DEMO RESET, no PIN/OTP anywhere |

---

## 5. Repository layout

```
INTENTPAY/
├── START_HERE.BAT            one-click install + launch (Windows)
├── INSTALL.BAT / RUN.BAT     split install / launch
├── APP.py                    Streamlit entry point (6 pages)
├── .streamlit/config.toml    pins the Streamlit theme to light (tool-mandated path)
├── REQUIREMENTS.TXT          core dependencies
├── REQUIREMENTS_VOICE.TXT    optional voice (pyttsx3 / SpeechRecognition)
├── ENV_EXAMPLE.TXT           copy to .env for the optional external AI engine
├── AGENTS.MD                 build log: decisions, architecture, test evidence
├── README.MD                 this file
├── SRC/                      the engine (all modules ALL-CAPS named)
│   ├── CONFIG.py             defaults + strict validation (invalid → keep last good)
│   ├── MODELS.py             dataclasses, Indian money formatting, haversine
│   ├── LANGUAGE.py           full EN/TA string catalogue
│   ├── FEATURES.py           20+ behavioural signals (train/inference share code)
│   ├── ANOMALY.py            Isolation Forest + cached percentile scoring
│   ├── INTENT_ENGINE.py      bilingual social-engineering lexicon + optional LLM
│   ├── CATEGORIZER.py        3-stage classifier with user corrections
│   ├── BUDGET.py / FORECAST.py / RECURRING.py   money management layer
│   ├── RISK_ENGINE.py        fusion, bands, conditional intent prompt, self-transfer rule,
│   │                         fraud_attribution() = exact additive score split
│   ├── EXPLAIN.py            ranked bilingual explanations + MODEL_LAYERS
│   ├── BLACKBOX.py           hash-chained event log, verify(), incident report
│   ├── LOCAL_LLM.py          machine specs, model recommendation, Ollama install/link
│   ├── DATA_GENERATOR.py     deterministic synthetic customers, eval set, scenarios
│   ├── DATA_LOADER.py        profiles/histories/scenarios access
│   ├── METRICS.py            P/R/F1/FPR/MCC, threshold sweep, cost model
│   ├── SIMULATION.py         payment flow: draft → evaluate → intent → decision → handoff
│   ├── VOICE.py              optional TTS/STT with graceful degradation
│   ├── FRAUD_HELP.py         1930 / cybercrime.gov.in guidance + complaint draft
│   └── DASHBOARD.py          flat white HTML component kit (no glassmorphism)
├── DATA/                     generated demo histories, labelled eval set, scenarios
├── RESOURCES/                pitch, demo script, formulas, architecture diagram, research
├── TESTS/RUN_TESTS.py        52 engine tests (no pytest needed)
│   └── TESTS/RUN_UI_TESTS.py   107 UI checks via Streamlit AppTest (needs streamlit)
├── USER_MANUAL.PDF            plain-language manual (install, folders, aim, how to use)
└── LICENSE                    MIT (NAS CODERS)
```

> **File naming:** every deliverable is ALL CAPS (`README.MD`, `START_HERE.BAT`, `RESOURCES/`).
> Python modules keep a lowercase `.py` extension because CPython's import system only
> recognises `.py` — the module names themselves are ALL CAPS (`SRC/RISK_ENGINE.py`).

---

## 6. Design boundaries (what this prototype does *not* claim)

* Synthetic data proves the **pipeline**, not production accuracy.
* Risk scores are **decision support, never proof of fraud**; budget warnings are guidance,
  not financial advice.
* The app **cannot reverse a completed UPI payment** — only the bank, NPCI or the recipient
  can. That is why the scam-help page exists.
* Recipient intelligence is a demo feed; production would use consent-based regulated
  integration with a bank/PSP.
* No covert monitoring, no call recording, no WhatsApp scraping, no UPI PIN/OTP/password field.
* The optional **local model** is as good as its size: small models read Tamil far less reliably
  than the bilingual lexicon, which is why the lexicon remains the fallback on every path.
  Installing Ollama is the user's explicit choice — the app never installs software silently.
* Raw voice is processed then discarded by default (`store_raw_voice = OFF`).
* **The UPI black box and the emergency-PIN decoy mode are concept prototypes.** There is no
  real UPI integration: the black box is a device-local hash chain (tamper-*evidence*; production
  would anchor hashes to a notary/ledger), and the decoy mode simulates payments against a
  synthetic balance. A production decoy must be *undiscoverable* — so the demo banner and the
  "restore real environment" button are prototype-only, and the PIN would never live in a
  config file.
* `USER_MANUAL.PDF` is the layman's version of this file: what the app is for, which folder is
  which, how to install it on Windows, and how to use every page with no jargon.

Research citations (RBI Annual Report 2024-25, I4C digital-arrest advisories, NPCI AutoPay
circular OC-223, Ask Google Pay, hybrid-ML UPI fraud papers, Elkan/Bahnsen cost-sensitive
evaluation) are listed in [`RESOURCES/RESEARCH.MD`](RESOURCES/RESEARCH.MD) and in-app.

---

## 7. Tests

```bat
python TESTS\RUN_TESTS.py        :: 63 engine tests
python TESTS\RUN_UI_TESTS.py     :: 125 UI checks (drives the real app, needs streamlit)
```

63 engine tests cover money totals, transfer exclusion, the 3-stage categoriser, user
corrections, budget remaining/overrun, median-robust forecasting, recurring detection,
intent detection (EN + TA), missing intent, AI-failure fallback, all seven safety scenarios,
self-transfer handling, empty-history behaviour, determinism, bad input, the full commit flow,
configuration validation, and metric maths — plus the triage split, the black box chain (verify,
tamper, delete), the emergency PIN and its limits, the exactness of the attribution, and the
local-LLM layer (machine detection, recommendation monotonicity, honest messaging on a small
machine, link status when Ollama is absent, and the fallback/clamping of a local model's answer).

The UI suite drives `APP.py` itself through Streamlit's AppTest harness: all six pages render,
every button on every page is clickable, scam scenarios land in the right band, the golden demo
separates an ordinary reason from a coerced one, judge-panel changes reach the engine, the
Metrics page computes and applies the F1-optimal threshold, and the Tamil / elder / customer
switches all work, and the new local-AI panel detects, recommends and falls back without
crashing on a machine with no Ollama. Current result: **63/63 engine, 125/125 UI**.

*IntentPay is a project codename for this hackathon; rename before any commercial use.*
