# IntentPay — Pitch (2 minutes, spoken)

**One line:** Every fraud system asks *"is this payment suspicious?"* — IntentPay asks
***"why are you paying?"***, in your own language, before the money leaves.

**The problem (30 seconds).**
UPI did 185.8 billion transactions in FY25 and digital-payment fraud hit 13,516 cases — 56.5 %
of all banking frauds, ₹520 crore (RBI Annual Report 2024-25). One in five Indian families has
been hit, and most never file a complaint. The dominant pattern is not card theft — it is
**social engineering**: a fake bank officer, a "digital arrest" video call, a lottery fee, a
refund QR. Existing systems score the *transaction*. They are blind to the *story* the user is
being told.

**The product (45 seconds).**
IntentPay is a pre-payment safety layer plus a personal finance layer in one app.

* When a payment crosses the user's own safety threshold, IntentPay asks **why** they are
  paying — in English or Tamil, by text or voice.
* A bilingual, explainable intent model reads the reason for urgency, authority impersonation,
  threats, secrecy, "safe account", lottery and refund-QR patterns, and fuses it with
  behavioural anomaly detection (Isolation Forest on that customer's own history) and recipient
  intelligence.
* The same moment also answers the money question: what this payment does to the monthly
  budget, the category limit, the forecast, and the recurring commitments.
* Two different problems, two different warnings — a coerced ₹25,000 is a fraud intervention; a
  perfectly innocent ₹1,200 grocery run that busts the food limit is a budget warning. Neither
  blocks the user: the app explains, the human decides.
* For an older Tamil-speaking user, all of this appears in plain Tamil with voice support. For a
  technical user, the same system exposes every score, weight, threshold and explanation.

**The proof (30 seconds).**
A working prototype with a live simulator (judges can change every parameter), a Tamil elder
mode, a labelled evaluation with precision/recall/F1 and a cost model, an honest scam-help exit
(1930 / cybercrime.gov.in), and a hard privacy boundary: local-only by default, no UPI
PIN/OTP/password field anywhere, raw voice discarded.

**The ask.** We are NAS CODERS, and we would love to show you the golden demo: the same
₹25,000 payment, twice — once with an ordinary reason, once with a coerced one.
