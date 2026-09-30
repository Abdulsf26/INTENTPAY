# IntentPay — 14-Minute Judge Demo Script

Golden rule for the presenter: **show, don't tell**. Every claim below is a button press, not a
sentence. The two scenarios that win hackathons are at 2:00 (conditional intent prompt) and
6:00 (low fraud, high budget impact) — do not skip them. If time is short, cut the accuracy
section to the ablation table and keep the attribution / black box / decoy trio at 9:00–12:00.

---

## 0:00–1:00 — The problem (no slides needed)

* India processed **185.8 billion UPI transactions in FY25** (+41.7 %), and digital-payment
  frauds were **13,516 cases — 56.5 % of all banking frauds, ₹520 crore** (RBI Annual Report
  2024-25).
* A 2025 survey found **1 in 5 Indian families** has been hit by UPI fraud, and **51 % of
  victims filed no complaint anywhere**.
* Meanwhile every app answers *"is this payment suspicious?"* — after the money has left.

Open the app: *"IntentPay asks **why are you paying** — before the money leaves."*

## 1:00–2:00 — A normal payment must not be interrupted

Payment simulator → **Normal ₹500 grocery** → **LOW (≈15/100)**, no prompt, no friction.

Point out the interruption-rate metric on the Accuracy page: ~40 % of payments get asked, the
rest are never bothered. Fraud UX that interrupts everyone gets ignored by everyone.

## 2:00–3:00 — The innovation: the conditional intent prompt

**New payee ₹25,000** → no reason given → the app stops and asks **"Why are you paying?"**

1. Type: *"cousin's college admission fees"* → MEDIUM → "review".
2. Clear it and type: *"bank officer said pay now or my account will be blocked"* → HIGH/CRITICAL.

Same amount, same recipient, **the only difference is the user's own words**. That is the
product. (This is also the golden demo in one click.)

## 3:00–4:00 — The fake-bank call

**Fake bank call** → CRITICAL. Open the explanation list: authority + urgency + "safe account"
framing + on-call + low battery + new payee. Mention the honest note: *risk scores are decision
support, not proof of fraud — the app tells the user to verify via their bank's own app.*

## 4:00–5:00 — Tamil elder mode

Switch language to **தமிழ்** in the sidebar (elder mode is on by default). Everything —
labels, verdicts, explanations — is in Tamil. Press the voice answer button:
*"இந்த மாதம் எவ்வளவு செலவாகிறது?"* → spoken answer with total, budget and remaining.

Design rule being demonstrated: amount-first, short sentences, big touch targets, voice replay,
no jargon.

## 5:00–5:30 — Needs, wants, unnecessary (the elder-friendly money view)

Still on the simulator result, scroll to the **triage** line, or open the dashboard: the month is
split into **needs ₹6,227 · wants ₹6,036 · unnecessary ₹430** (of ₹12,693 spent) with each bucket's
share and the amount left in the monthly limit. Switch the customer to **Meenakshi Ammal** in the
sidebar and the whole card turns Tamil — தேவையான செலவுகள் / விருப்ப செலவுகள் / தேவையற்ற
செலவுகள் — with larger type. Say it plainly: *an older user should be able to see, in one line,
what they had to spend and what they chose to spend.*

Then Judge panel → **spending triage map** → move FOOD to *needs* → Apply, and show the dashboard
card following it. Every parameter is live.

## 5:30–6:00 — The money dashboard

Money dashboard → this month **₹12,693 / ₹15,000** (85 %), food **₹5,540 / ₹6,000** (92 %),
projected month-end, forecast confidence, 7-day trend, recent transactions, one-tap category
correction. Self-transfers are visibly excluded from spending.

## 6:00–7:00 — Two different problems, two different warnings

**Food ₹1,200 (budget)** → **fraud LOW, budget impact HIGH**: *"this payment exceeds your food
limit — review and decide."* The app does **not** block the payment: budget control belongs to
the user, not to a tiny financial dictator living in the browser.

## 7:00–8:00 — Digital arrest + the honest exit

**Digital arrest** → CRITICAL (police impersonation + threat + secrecy + 90-minute video call).
Press **"I think I was scammed"** → scam-help page: call **1930**, file at **cybercrime.gov.in**,
bank dispute with the UTR, evidence checklist, copy-ready complaint draft. State the boundary
out loud: *we cannot reverse a completed UPI payment — only the bank, NPCI or the recipient can;
speed is everything.*

## 8:00–10:00 — The judge panel (let them drive)

Hand the laptop over. Invite them to change, live:

* fusion weights (must sum to 1 — invalid input is rejected with the exact error),
* `ask_intent_above`, the three band thresholds,
* anomaly blend / contamination / trees,
* monthly and food budget limits,
* the **needs/wants/unnecessary triage map** (every category → needs, wants or unnecessary),
* the **emergency PIN and the decoy balance / per-transaction / monthly limits**,
* customer data (switch to **Meenakshi Ammal**, 68, Coimbatore, Tamil — language, elder mode and
  type size follow the customer automatically) or change the history seed to regenerate a
  completely different demo customer,
* AI engine: LOCAL ⇄ EXTERNAL (with no key set, the fallback is visible),
* SAFE DEMO RESET and the JSON report export.

## 9:00–10:00 — Why this score: attribution that adds up

Back on the simulator, open **"Why this score?"** under the fake-bank-call result. The panel lists
every signal with its signed points, biggest first, and the column **sums to the score on the
card** — no mystery remainder. Add the four numbers at the top by hand if a judge is sceptical.

Then open **About & research** → the **four production layers** table: behaviour (GNN →
Isolation Forest), connections (graph edges → known devices/new payee), transaction details
(XGBoost → weighted rules), fusion (calibrated ensemble → fixed weights + threshold sweep),
explanation (SHAP → exact additive attribution). *Here is the research path, stated honestly.*

## 10:00–11:00 — UPI black box

Scroll to **Safety features → ✈️ UPI black box**. Press **Verify**: the hash chain over every step
of this payment (drafted → analysed → asked → warned → reason given → re-analysed → decision) is
intact. Press **Tamper with an entry**: the chain breaks at the exact entry index. Press **Verify**
again to restore. Download the JSON incident report and show it. Say the boundary out loud: *this
is a concept — the chain lives on the device, so it is tamper-evidence for a dispute; production
would anchor the hashes to a notary or ledger, and the events would come from a real UPI/NPCI
integration that does not exist here.*

## 11:00–12:00 — Emergency PIN / decoy mode

Press **Activate decoy mode** and type the demo PIN **9111** (shown in the Judge panel). The
environment changes: a decoy balance of ₹1,240 with a ₹500 per-transaction limit, and a banner
that says this is a simulation.

1. Try to pay **₹25,000** → **blocked** (`over_limit`).
2. Pay **₹200** → **simulated**, nothing real moves.
3. Judge panel → set the decoy transaction limit to **0** → every amount is now blocked
   (`limit_zero`).

Then **Exit decoy mode**. Point at the black box: `decoy_activated`, `silent_alert` and the
simulated payments are all logged, so the record proves a duress PIN was used. Say the boundary
out loud: *a real decoy must be undiscoverable — no banner, no "restore real environment" button,
and the PIN never stored in a config file. This prototype keeps those visible on purpose so you
can see the mechanism.*

## 12:00–13:00 — Accuracy & cost

Run the evaluation: precision / recall / **F1**, FPR, MCC, confusion matrix, per-family recall,
the **ablation table** (rules → +anomaly → +intent: the intent layer is what lifts precision),
the F1-optimal threshold sweep, and the cost model. Be explicit: *synthetic data proves the
pipeline, not production accuracy.*

## 13:00–13:30 — Local AI (Ollama)

Judge panel → **Local AI model (Ollama)** → **1. Detect this machine** → the specs table and the
recommended model appear with the reason ("16 GB detected → llama3.1:8b needs about 16 GB,
download 4.7 GB"). Press **2. Start server**, **3. Download model**, **4. Test the link** — the
status table turns green and the probe returns a JSON risk score from the local model. Press
**5. Use this model** and run the fake-bank-call scenario again: the same verdict, now from a real
language model running on the laptop. If Ollama is not installed the panel says so and shows the
exact commands.

## 13:30–14:00 — Privacy + architecture

Local-only indicator, raw voice discarded, no PIN/OTP field anywhere in the app, SAFE DEMO
RESET, then the architecture slide (RESOURCES/ARCHITECTURE.SVG) and the production path:
consent-based statement import → pilot → PSP/bank integration → privacy-preserving learning →
security audit and governance.

---

## Judge questions — ready answers

| Question | Answer |
|---|---|
| Why not Google Pay? | Ask Google Pay already does spending insights in ten languages. Nobody asks **why** you are paying before a risky transfer, and nobody connects that answer to your budget. |
| How do you get bank data? | Synthetic demo data + CSV/statement import in the prototype; regulated consent-based integration is the production path. We never claim live bank access. |
| Can you reverse a UPI payment? | No. We guide the user to 1930, cybercrime.gov.in and their bank inside the golden hour — and we say so on screen. |
| Why voice? | Lower literacy/interface friction for older users — not autonomous payment control. |
| What's genuinely new? | Conditional, explainable **user-stated intent** as a first-class fraud signal, fused with budget impact in one pre-payment moment — plus the needs/wants/unnecessary view for older users, an exact attribution of every score, a tamper-evident black box, and a duress-PIN decoy mode. |
| How exact is the explanation? | Exactly exact: the attribution rows sum to the score (worst gap 0.20 points across the ten scenarios, tested), so there is no unexplained remainder. |
| Is the black box real? | The mechanism is real (SHA-256 hash chain, tamper detection on edit or deletion, JSON export); the UPI events are simulated, and the chain is device-local — it is tamper-*evidence*, anchor-ready, and the app says so. |
| Is the decoy mode real? | It is a concept prototype: the PIN, limits and simulated payments are real code paths, but nothing touches a real account. A production decoy must be indistinguishable from the real app, which is why the demo's banner and exit button are prototype-only. |
| What if the AI is wrong? | Explainable scores, bounded actions, user keeps the decision, deterministic local fallback, and a cost model that prices false alarms. |
| Isn't this just a rule engine? | The anomaly layer learns each customer's own baseline; the intent layer is a weighted bilingual model; both are ablated and measured on the Metrics page. |
| Cost to run? | ~13 ms per decision on a laptop after the first call; the model is cached per history. |
