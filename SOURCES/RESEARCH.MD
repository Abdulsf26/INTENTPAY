# IntentPay — Research Notes & References

Checked 30 September 2026. Every claim below shaped a concrete product decision.

## 1. Scale of the problem (why this matters now)

* **RBI Annual Report 2024-25**: digital payment frauds numbered **13,516 cases — 56.5 % of all
  reported banking frauds — totalling ₹520 crore**; UPI processed **185.8 billion transactions**
  in FY25 (+41.7 % YoY) and accounted for **83.4 %** of digital payment volume. RBI also runs a
  Central Payment Fraud Information Registry (CPFIR) using AI/ML.
  → *Product decision: fraud intervention must be cheap enough to run on every payment, which is
  why the anomaly model is cached and the intent engine is a deterministic local lexicon.*
* **LocalCircles survey (June 2025)**: **1 in 5 families** using UPI experienced fraud since
  2022; **51 % of victims filed no complaint anywhere**; 50 % said their settings/PIN were
  compromised, 40 % clicked payment links.
  → *Product decision: the scam-help page must be one click from a risky payment, and must tell
  the user exactly where to go (1930, cybercrime.gov.in, bank).*
* **"Digital arrest" advisories (I4C, NPCI)**: CBI/Police/Customs/ED/Judges **do not** arrest or
  investigate over video calls; fraudsters use "refundable security deposit" and "clearing your
  name" framing; victims include senior citizens and even a retired banker who lost ₹22.92
  crore. Recommended actions: hang up, call **1930**, file at **cybercrime.gov.in**, alert the
  bank inside the "golden hour", preserve evidence.
  → *Product decision: AUTHORITY + THREAT + SECRECY families carry the highest intent weights,
  and the digital-arrest scenario is a first-class demo.*
* **Reddit / r/LegalAdviceIndia / r/india victim threads**: fake electricity-meter APK with
  remote access, a ₹10 collect request used to capture the UPI PIN, fake Delhivery customer-care
  numbers, ₹91k–₹99.5k losses, money layered to mule accounts within minutes.
  → *Product decision: small amounts are not safe by default (QR refund + OTP/PIN families), and
  velocity + new-payee + link signals are first-class.*

## 2. What already exists (positioning)

* **Google Pay "Ask Google Pay" (2026)**: opt-in Gemini experience analysing spending, savings
  tips and financial education in ten Indian languages, using transaction history + CIBIL data
  inside Google Pay; still limited to some users. Google Pay history covers only GPay-made
  transactions, with date/amount/type/status filters and statement export.
  → *Positioning: spending insights in Indian languages exist; asking "why are you paying?"
  before a risky transfer does not. We never claim to have invented AI finance chat.*
* **NPCI UPI AutoPay enhancement (circular OC-223, Oct 2025)**: users can view active mandates
  in an app of their choice and revoke / pause / modify them.
  → *Product decision: IntentPay adds financial-*impact* intelligence for recurring commitments
  (budget share, next expected date, amount increases) and explicitly does not claim mandate
  management.*
* **RBI circulars 2024-2026**: 4-hour cooling period for new UPI beneficiaries above ₹2,000,
  mandatory "YOU ARE PAYING" alerts for collect requests, 5-day SIM-swap cooling, proposed
  biometric re-authentication for high-value UPI.
  → *Product decision: our new-payee and collect-request (QR/LINK) signals align with the same
  direction regulators are pushing.*

## 3. Methods literature (how we built the engine)

* **Hybrid ML + anomaly detection for UPI fraud** (IJIRT 178524, 2025): combines supervised
  models (Random Forest, Logistic Regression, XGBoost) with behavioural anomaly detection on
  frequency, location, amount and device context; flagged 87 % of outlier transactions later
  confirmed fraudulent, with **< 300 ms** evaluation — the feasibility bar our ~13 ms target
  beats by an order of magnitude.
* **Unsupervised behavioural baselines** (HMM / autoencoder / Isolation Forest approaches in
  the UPI fraud literature): per-customer normality models catch account takeover without fraud
  labels — the reason our anomaly layer trains on each customer's *own* history.
* **Cost-sensitive evaluation** — Elkan (2001), Bahnsen et al. (2015), and the JRFM 2025 study
  "Beyond Accuracy": with asymmetric error costs and heavy class imbalance, accuracy is
  misleading; expected-loss and PR-based metrics are the honest evaluation. → *Product decision:
  the Metrics page reports precision/recall/F1/FPR/MCC plus a `C_FN·FN + C_FP·FP + λ·friction`
  loss model, never bare accuracy.*
* **Threshold optimisation** (IRJMETS 2025, PaySim): post-training threshold choice dominates
  real-world utility; F2/MCC matter when false negatives cost more than false alarms.
  → *Product decision: the threshold sweep is a first-class UI feature with one-click apply, and
  the cost model lets a judge price their own C_FN / C_FP.*

## 4. Privacy & safety references

* **OWASP MASVS** and **OWASP API Security Top 10 (2023)**: local-first prototype, no secrets in
  the client, no sensitive payload logging, visible data-egress indicator when an external AI
  engine is enabled.
* **RBI financial-inclusion and financial-literacy work** supports designing for *understandable
  control*, not just account access — the reason the elder mode is amount-first and voice-first.

## 5. Honest limitations (restated for the record)

Synthetic data cannot establish production accuracy; the intent lexicon can misread colloquial
speech; merchant categorisation can be wrong (hence one-tap corrections); forecasts can be wrong
(thin history is labelled low confidence); a standalone app has no bank/NPCI private
intelligence; budget warnings are guidance, not financial advice; risk scores are not proof of
fraud; completed UPI payments are not automatically reversible.
