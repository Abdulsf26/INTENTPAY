# IntentPay — Formula Reference

Every number the app shows is reproducible from the transaction dataset and the current
configuration. A judge who changes a parameter can predict exactly what changes.

## 1. Behavioural signals (SRC/FEATURES.py)

| Signal | Definition | Why it matters |
|---|---|---|
| `amount_zscore` | `(x − μ) / σ` over the customer's own past debits | Large deviations from personal normality |
| `amount_ratio` | `x / median(past debits)` | Robust to one expensive past day |
| `category_deviation` | `x / mean(same category, last 30 d)` | "₹1,200 food" is normal for some, wild for others |
| `velocity_24h` | debits in the last 24 h | Drip-drain fraud: many small payments fast |
| `frequency_7d` | debits in the last 7 days | Account-takeover bursts |
| `is_new_payee` | no prior debit to this UPI ID | Most scams need a fresh beneficiary |
| `location_change_km` | haversine(payment, usual location) | SIM-swap / remote-control patterns |
| `is_night` | hour ≥ 22 or < 6 | Coerced payments happen at night |
| `on_call_amount` | `on_call · min(x / 20000, 1)` | Paying *while* on a call is the digital-arrest signature |
| `battery_low` | battery ≤ 20 % | Device-pressure heuristic from victim reports |
| `channel_link` | payment arrived via link | Phishing-link flows |
| `is_round_amount` | `x ≥ 1000 and x mod 1000 = 0` | Psychological marker of coerced amounts |
| `device_new` | device not in known devices | New-device takeover |
| `payee_reports` | `min(reports, 5) / 5` | Demo recipient intelligence |

`log_amount`, `hour_sin`, `hour_cos` are included so the anomaly model sees amount scale and
time-of-day cyclicity.

## 2. Transaction risk

Rule factors `f_i ∈ [0, 1]` with fixed weights `w_i` (sum of maxima = 1.00):

| factor | weight | mapping |
|---|---|---|
| `payee_reports` | 0.20 | `min(reports,5)/5` |
| `new_payee` | 0.16 | 0/1 |
| `amount_unusual` | 0.14 | `max(z/4, (ratio−1)/5)` clipped to [0,1] |
| `on_call_amount` | 0.12 | `on_call · min(x/20000, 1)` |
| `velocity` | 0.10 | `min(velocity_24h/6, 1)` |
| `location` | 0.10 | 0/1 (> 50 km) |
| `category_deviation` | 0.08 | `min(dev/5, 1)` |
| `channel_link` | 0.06 | 0/1 |
| `night` | 0.06 | 0/1 |
| `device_new` | 0.05 | 0/1 |
| `battery_low` | 0.04 | 0/1 |
| `round_amount` | 0.03 | 0/1 |

```
rule_risk   = 100 · Σ w_i · f_i
anomaly     = 100 · clamp((percentile − 0.75) / 0.25)
transaction = (1 − blend) · rule_risk + blend · anomaly        blend = 0.45 default
```

**Anomaly percentile.** An Isolation Forest (`n_estimators=120`, `contamination=0.05`,
`random_state=42`) is trained on the customer's own history feature vectors. For a new payment,
`raw = −decision_function(x)`; `percentile = |{history scores ≤ raw}| / n`. Payments at or below
the 75th percentile score 0; the top ~5 % (the model's contamination band) score ≈ 100. The raw
`decision_function` value is never shown because its scale is not interpretable.

Why percentile instead of the raw score: it is bounded, stable across datasets, and directly
explainable ("more unusual than 96 % of this customer's own payments").

## 3. Intent risk (SRC/INTENT_ENGINE.py)

Twelve weighted families, matched bilingually (English + Tamil). Two matchers run
together, because Tamil inflects where English does not:

* **phrases** — exact substrings. Two distinct phrases of one family saturate the
  factor (`min(hits, 2)/2`).
* **roots** — substring stems (`அனுப்ப` catches `அனுப்புங்கள்`, `அனுப்ப வேண்டும்`,
  `அனுப்பினார்`; `invest` catches `investment`). A root counts for half a phrase,
  so it can complete a family but never inflate it. Roots are matched
  virama-insensitively, and a stray virama before a vowel sign is dropped at
  normalisation (`ரீஃபண்டு` == `ரீஃபண்ட்டு`).

| family | weight | family | weight |
|---|---|---|---|
| URGENCY | 0.90 | LOTTERY | 0.90 |
| AUTHORITY | 1.00 | REFUND_QR | 0.85 |
| THREAT | 1.00 | DELIVERY_SUPPORT | 0.70 |
| SECRECY | 0.95 | JOB_FEE | 0.75 |
| VERIFICATION | 0.80 | FAMILY_EMERGENCY | 0.50 |
| SAFE_ACCOUNT | 0.90 | OTP_PIN | 0.90 |

```
raw     = Σ_family weight · max(phrase_factor, root_factor)
phrase_factor = min(phrase_hits, 2)/2        root_factor = min(1, 0.5 · root_hits)
score   = 100 · min(1, raw) + Σ combination bonuses
if benign phrases matched and no high-severity family:  score *= 0.55
```

Combination bonuses (+8 authority+threat, +8 authority+secrecy, +8 safe-account+authority,
+8 refund-QR+OTP/PIN, +6 urgency+threat, +8 urgency+authority, +6 urgency+safe-account,
+6 KYC+urgency) capture the fact that real scams *stack* patterns.
`FAMILY_EMERGENCY` carries only 0.50 because genuine emergencies exist — the app says
"verify by calling the person directly" instead of accusing a relative.

Missing reason → `risk = None` (**unknown**, not zero).

## 4. Fusion and bands (SRC/RISK_ENGINE.py)

```
fraud = w_t · transaction + w_i · intent + w_r · recipient      (weights sum to 1)
if intent unknown:  fraud = (w_t · transaction + w_r · recipient) / (w_t + w_r)
bands:  LOW < medium(30) ≤ MEDIUM < high(55) ≤ HIGH < critical(75) ≤ CRITICAL
ask intent when:  preliminary fraud ≥ ask_intent_above (55)
self-transfer to a verified own account:  fraud := min(fraud, medium_threshold − 1)
   (always lands in LOW: moving your own money is not a scam signal)
```

### 4.1 Exact attribution (SRC/RISK_ENGINE.py: `fraud_attribution`)

The score is decomposed into signed point contributions that **sum back to the score itself**,
which is what makes the "why this score?" panel honest rather than decorative.

```
attributed_points(k) = group_weight(k) · raw_component(k)      for each fired signal
attributed_points    = Σ_k points(k)  +  Σ_residual residual_points
fraud                = attributed_points                     (worst gap 0.20 on the demo set)
```

* Weights are taken **after** the same renormalisation the fusion uses when intent is unknown
  (`w_t/(w_t+w_r)`, `w_r/(w_t+w_r)`, `w_i = 0`), so the intent family contributes nothing when no
  reason was given.
* A component with no fired signal still gets a **residual row** (`expl_intent_baseline`,
  `expl_recipient_baseline`) equal to its weight times its raw component — otherwise a
  low-scoring payment would report a total below its score.
* The self-transfer cap appears as a single negative row (`expl_self_transfer_cap`).
* Rows are ranked by |points| and carry English + Tamil labels; the panel shows them as
  "signal → points", so a judge can add the column by hand and land on the score.

## 5. Budget layer (SRC/BUDGET.py, SRC/FORECAST.py)

```
R = B − S                                  remaining
U = S / B                                  utilisation
D_robust = median(daily spend, last k days) k = 14
P = S + D_robust · days_remaining · seasonality
O = max(0, P − B)                          projected overrun
U_c = S_c / B_c                            category utilisation
states: SAFE < 70% ≤ WATCH < 90% ≤ NEAR LIMIT < 100% ≤ EXCEEDED
budget band for a candidate payment: HIGH if it would exceed month or category, else
                                      MEDIUM if utilisation after ≥ 80%, else LOW
confidence: HIGH ≥ 90 days history, MEDIUM 30–89, LOW < 30
```

Median (not mean) is used deliberately: one unusual day must not distort the projection.

### 5.1 Spending triage (SRC/BUDGET.py)

```
bucket(category) = triage_map[category]          (needs | wants | unnecessary, default wants)
S_b   = Σ spend of categories in bucket b (current month, transfers to self excluded)
share_b = 100 · S_b / S_total
remaining = monthly_limit − S_total
```

The map is a plain dict in the config, editable live in the Judge Panel; unknown categories fall
back to `wants` instead of raising. Tamil labels: தேவையான செலவுகள் / விருப்ப செலவுகள் /
தேவையற்ற செலவுகள். Measured on customer one (this month): needs ₹6,227.21 (33.3 %),
wants ₹6,035.98 (64.4 %), unnecessary ₹430.05 (2.3 %), total ₹12,693.24.

### 5.2 UPI black box (SRC/BLACKBOX.py)

```
h_0 = 0
h_i = SHA256( h_{i-1} || canonical_json(entry_i) )
entry_i = {seq, ts, event, payload, prev_hash, hash, short_hash}
verify() -> (chain_ok, first_bad_index)      # an edit *or* a deletion changes every later hash
```

Each entry commits to its predecessor, so removing an entry shifts every following hash and the
break is reported at the first mismatched index. The chain is **device-local**: it is tamper-*evidence*
for a dispute, not proof against a compromised device — production would anchor `short_hash`
values to a notary or ledger (the export already carries them).

### 5.3 Emergency PIN / decoy mode (SRC/SIMULATION.py)

```
check_pin(pin)     : pin == decoy.emergency_pin  -> decoy_mode := true  + silent_alert
decoy_payment(a,p) : a > decoy_transaction_limit  -> blocked, reason "over_limit"
                     decoy_transaction_limit == 0  -> blocked, reason "limit_zero"
                     otherwise                     -> reason "simulated", decoy_log += entry
exit               : decoy_mode := false
```

Demo values: PIN `9111`, decoy balance ₹1,240, per-transaction limit ₹500, monthly limit ₹3,000.
Every activation and every simulated payment is written to the black box, so the record shows
that a duress PIN was used even though nothing real moved.

## 6. Fusion truth table (fraud × budget)

| fraud | budget | recommendation |
|---|---|---|
| LOW | LOW | normal payment |
| LOW | MED/HIGH | budget warning — user decides |
| HIGH/CRIT | LOW | fraud intervention |
| HIGH/CRIT | MED/HIGH | strong warning + verify + budget impact |
| unknown | MED/HIGH | budget warning + "safety check incomplete" |
| HIGH/CRIT | unknown | fraud intervention; never imply budget safety |

## 7. Evaluation (SRC/METRICS.py)

```
Precision = TP / (TP + FP)      Recall = TP / (TP + FN)
F1        = 2PR / (P + R)       FPR    = FP / (FP + TN)
MCC       = (TP·TN − FP·FN) / sqrt((TP+FP)(TP+FN)(TN+FP)(TN+FN))
Loss      = C_FN · FN + C_FP · FP + λ · interruption_rate · N
```

Defaults for the demo cost model: `C_FN = ₹25,000` (median reported scam loss scale),
`C_FP = ₹15` (seconds of user attention), `λ = 1`. The threshold sweep reports the F1-optimal
decision threshold; the app never silently changes it — a judge applies it explicitly.

## 8. The four production layers (SRC/EXPLAIN.py: `MODEL_LAYERS`)

| Layer | Production counterpart | Prototype implementation | Question it answers |
|---|---|---|---|
| Behaviour | Graph Neural Network over a device/identity graph (GNN-FedFast, 2024-25) | Isolation Forest on this customer's own history | Does this payment look like this person? |
| Connections | GNN edges: shared devices, payees, locations | known-device list, new-payee flag, haversine distance from the usual city | Is the recipient/device part of a trusted graph? |
| Transaction details | Gradient-boosted classifier (XGBoost) over engineered features | weighted rule table over 20+ features | Is the payment itself unusual? |
| Fusion | calibrated ensemble + threshold optimisation | fixed weighted fusion (0.40/0.45/0.15) + band thresholds + cost-sensitive sweep | How do the layers combine into one decision? |
| Explanation | SHAP / LIME feature attribution | `fraud_attribution()` — exact additive split of the fused score | Why did it decide that? |

The intent layer is the prototype's own contribution: production would train an intent classifier
on labelled social-engineering corpora; here it is a deterministic bilingual lexicon so the whole
demo runs offline and reproducibly.

## 9. Latency budget

Measured on the demo data (single evaluation, model cached): **~13 ms** total
(features ≈ 4 ms, behaviour ≈ 2 ms, intent < 1 ms, budget/forecast ≈ 5 ms), first evaluation
after a history change ≈ 0.5 s (one Isolation Forest training, then cached).
~385 labelled evaluations complete in ≈ 6 s.


## 10. Local model selection (SRC/LOCAL_LLM.py)

```
budget = total_RAM + (2 GB if GPU_VRAM >= 6 GB else 0)
model  = largest catalogue entry with ram_gb <= budget      (else the smallest, and say so)
ollama_generate_json(prompt) -> POST {host}/api/generate
                                 {model, prompt, stream:false, format:json,
                                  options:{temperature:0}}
ready  = installed AND server_answering AND model_downloaded
engine = ollama  ->  model answer (clamped 0-100, <=6 signals)
                     on ANY failure -> local lexicon, with the reason shown
```

Catalogue: gemma2:2b (6 GB) · qwen2.5:3b (8 GB) · llama3.1:8b (16 GB) · gemma2:9b (24 GB) ·
qwen2.5:14b (32 GB). Tamil quality is stated per model (weak/fair/good) because small models read
Tamil far less reliably than the bilingual lexicon — which is why the lexicon stays the fallback.
