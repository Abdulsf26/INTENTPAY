"""Bilingual (English / Tamil) string catalogue for IntentPay.

Design rule from the manual: amount-first, short sentences, no financial
jargon.  Tamil is the primary accessibility language (elder mode); English is
the developer/judge language.  Any missing key falls back to English and then
to the key itself so the UI never shows a blank label.
"""
from __future__ import annotations

from typing import Any, Dict

STRINGS: Dict[str, Dict[str, str]] = {
    # ------------------------------------------------------------------ app ---
    "app_name": {"en": "IntentPay", "ta": "IntentPay"},
    "app_tagline": {
        "en": "Before money leaves: is this payment dangerous, and what does it do to my budget?",
        "ta": "பணம் போகும் முன்: இது ஆபத்தா? என் பட்ஜெட்டுக்கு என்ன தாக்கம்?",
    },
    "team_name": {"en": "NAS CODERS", "ta": "NAS CODERS"},
    "prototype_notice": {
        "en": "Prototype with synthetic demo data. No UPI PIN / OTP / password is ever requested. Completed UPI payments cannot be reversed by this app.",
        "ta": "இது செயற்கை (டெமோ) தரவு கொண்ட பாதுகாப்பு அமைப்பு. UPI PIN / OTP / கடவுச்சொல்லை இது ஒருபோதும் கேட்காது. பணம் அனுப்பப்பட்ட பிறகு இதன் மூலம் திரும்ப பெற முடியாது.",
    },
    "mode_local_only": {"en": "LOCAL-ONLY", "ta": "உள்ளூர்-மட்டும்"},
    "mode_external_ai": {"en": "EXTERNAL AI ON", "ta": "வெளி AI இயக்கத்தில்"},
    "data_leaves_warning": {
        "en": "External AI is enabled: your payment reason text leaves this computer.",
        "ta": "வெளி AI இயக்கத்தில் உள்ளது: நீங்கள் தட்டச்சு செய்யும் காரணம் இந்த கணினியை விட்டு வெளியேறும்.",
    },
    "safe_reset": {"en": "SAFE DEMO RESET", "ta": "பாதுகாப்பான டெமோ ரீசெட்"},
    "reset_done": {"en": "Session reset. Demo state cleared.", "ta": "அமர்வு மீட்டமைக்கப்பட்டது."},
    # ------------------------------------------------------------------ nav ---
    "nav_pay": {"en": "Payment simulator", "ta": "பணம் அனுப்பு"},
    "nav_dashboard": {"en": "Money dashboard", "ta": "பண டாஷ்போர்டு"},
    "nav_judge": {"en": "Judge panel", "ta": "மதிப்பீட்டு பேனல்"},
    "nav_metrics": {"en": "Accuracy & cost", "ta": "துல்லியம் & செலவு"},
    "nav_help": {"en": "Scam help", "ta": "மோசடி உதவி"},
    "nav_about": {"en": "About & research", "ta": "பற்றி & ஆய்வு"},
    # -------------------------------------------------------------- common ----
    "amount": {"en": "Amount", "ta": "தொகை"},
    "payment_method": {"en": "Payment type", "ta": "பேமெண்ட் வகை"},
    "upi": {"en": "UPI", "ta": "யுபிஐ"},
    "bank": {"en": "Bank transfer", "ta": "வங்கி பரிமாற்றம்"},
    "payee_name": {"en": "Recipient name", "ta": "பெறும் வர் பெயர்"},
    "payee_upi": {"en": "Recipient UPI ID", "ta": "பெறும் வர் UPI ஐடி"},
    "category": {"en": "Category", "ta": "வகை"},
    "date": {"en": "Date", "ta": "தேதி"},
    "time": {"en": "Time", "ta": "நேரம்"},
    "location": {"en": "Location", "ta": "இடம்"},
    "on_call": {"en": "On a phone/video call while paying", "ta": "பேமெண்ட் நேரத்தில் ஃபோன்/வீடியோ அழைப்பில்"},
    "call_duration": {"en": "Call duration (minutes)", "ta": "அழைப்பு நேரம் (நிமிடம்)"},
    "channel": {"en": "Payment channel", "ta": "பேமெண்ட் வழி"},
    "channel_p2p": {"en": "Direct (P2P)", "ta": "நேரடி (P2P)"},
    "channel_qr": {"en": "QR scan", "ta": "QR ஸ்கேன்"},
    "channel_link": {"en": "Payment link", "ta": "பேமெண்ட் லிங்க்"},
    "new_payee": {"en": "First payment to this recipient", "ta": "இந்த பெறுபவருக்கு முதல் பேமெண்ட்"},
    "device": {"en": "Device", "ta": "சாதனம்"},
    "battery": {"en": "Battery level (%)", "ta": "பேட்டரி நிலை (%)"},
    "intent_text": {"en": "Why are you paying? (your own words)", "ta": "ஏன் பணம் அனுப்புகிறீர்கள்? (உங்கள் வார்த்தையில்)"},
    "evaluate": {"en": "Check this payment", "ta": "இந்த பேமெண்ட்டை பரிசோதி"},
    "approve": {"en": "Continue payment", "ta": "தொடரவும்"},
    "cancel": {"en": "Cancel payment", "ta": "ரத்து செய்யவும்"},
    "help_btn": {"en": "I think I was scammed", "ta": "என்னை மோசடி செய்து விட்டார்கள்"},
    "apply": {"en": "Apply", "ta": "பயன்படுத்து"},
    "reset_defaults": {"en": "Reset defaults", "ta": "முன்னிருப்புக்கு மீட்டு"},
    "export": {"en": "Export report", "ta": "அறிக்கை பதிவிறக்கம்"},
    "customer": {"en": "Customer", "ta": "வாடிக்கையாளர்"},
    "language": {"en": "Language", "ta": "மொழி"},
    "elder_mode": {"en": "Elder mode (large text, voice)", "ta": "மூத்தவர்கள் பயன்முறை (பெரிய எழுத்து, குரல்)"},
    "voice": {"en": "Voice support", "ta": "குரல் உதவி"},
    "unknown": {"en": "Unknown", "ta": "தெரியவில்லை"},
    # ----------------------------------------------------------------- bands ---
    "low": {"en": "LOW", "ta": "குறைந்தது"},
    "medium": {"en": "MEDIUM", "ta": "நடுத்தரம்"},
    "high": {"en": "HIGH", "ta": "அதிகம்"},
    "critical": {"en": "CRITICAL", "ta": "மிக உயர்"},
    "safe": {"en": "SAFE", "ta": "பாதுகாப்பு"},
    "watch": {"en": "WATCH", "ta": "கவனம்"},
    "near_limit": {"en": "NEAR LIMIT", "ta": "எல்லை அருகில்"},
    "exceeded": {"en": "EXCEEDED", "ta": "தாண்டியது"},
    "overrun": {"en": "PROJECTED OVERRUN", "ta": "மாத இறுதியில் தாண்டும்"},
    # ------------------------------------------------------------- sections ---
    "sec_payment_details": {"en": "1. Payment details", "ta": "1. பேமெண்ட் விவரம்"},
    "sec_intent": {"en": "2. Why are you paying?", "ta": "2. ஏன் பணம் அனுப்புகிறீர்கள்?"},
    "sec_result": {"en": "3. Safety check result", "ta": "3. பாதுகாப்பு முடிவு"},
    "sec_budget_impact": {"en": "Budget impact of this payment", "ta": "இந்த பேமெண்ட்டின் பட்ஜெட் தாக்கம்"},
    "sec_scenarios": {"en": "Demo scenarios (one click)", "ta": "டெமோ நிலைகள் (ஒரு கிளிக்க்)"},
    "sec_golden_demo": {"en": "Golden demo: same amount, two different stories", "ta": "கோல்டன் டெமோ: அதே தொகை, இரண்டு வேறு காரணங்கள்"},
    "sec_overview": {"en": "Overview", "ta": "சுருக்கம்"},
    "sec_spending": {"en": "Spending", "ta": "செலவு"},
    "sec_safety": {"en": "Payment safety", "ta": "பேமெண்ட் பாதுகாப்பு"},
    "sec_limits": {"en": "Limits & commitments", "ta": "வரம்புகள் & கடமைகள்"},
    "sec_config": {"en": "Engine parameters", "ta": "அமைப்பு மதிப்புகள்"},
    "sec_customer": {"en": "Customer data", "ta": "வாடிக்கையாளர் தரவு"},
    "sec_ai": {"en": "AI engine", "ta": "AI எஞ்சின் (இயந்திரம்)"},
    "sec_privacy": {"en": "Privacy", "ta": "தனியுரிமை"},
    "sec_metrics": {"en": "Model quality on the labelled demo set", "ta": "டெமோ தரவில் மாதிரியின் தரம்"},
    "sec_audit": {"en": "Local audit trail", "ta": "உள்ளூர் பதிவு"},
    # ---------------------------------------------------------- intent flow ---
    "intent_needed_title": {
        "en": "IntentPay needs to know why you are paying",
        "ta": "ஏன் பணம் அனுப்புகிறீர்கள் என்று IntentPay-க்கு தெரிய வேண்டும்",
    },
    "intent_needed_body": {
        "en": "This payment crosses your safety threshold. A short reason in your own words lets us check for social-engineering patterns (urgency, authority claims, threats, secrecy).",
        "ta": "இந்த பேமெண்ட் உங்கள் பாதுகாப்பு எல்லையை தாண்டுகிறது. உங்கள் சொந்த வார்த்தையில் ஒரு சிறு காரணம், அவசரம் / அதிகாரி பேச்சு / பீதி / ரகசியம் போன்ற மோசடி அறிகுறிகளை பரிசோதிக்க உதவும்.",
    },
    "intent_missing_note": {
        "en": "No reason given — the safety check is incomplete for this payment.",
        "ta": "காரணம் தெரிவிக்கப்படவில்லை — இந்த பேமெண்ட்டின் பாதுகாப்பு பரிசோதனை முழுமையாகவில்லை.",
    },
    "intent_provided_ok": {
        "en": "Reason received. Re-check with your reason.",
        "ta": "காரணம் பெறப்பட்டது. காரணத்துடன் மீண்டும் பரிசோதிக்கவும்.",
    },
    "fraud_risk": {"en": "Fraud / scam risk", "ta": "மோசடி ஆபத்து"},
    "transaction_risk": {"en": "Transaction behaviour", "ta": "பரிவர்த்தனை நடத்தை"},
    "intent_risk": {"en": "Intent (your reason)", "ta": "நோக்கம் (உங்கள் காரணம்)"},
    "recipient_risk": {"en": "Recipient", "ta": "பெறுபவர்"},
    "recommendation": {"en": "Recommendation", "ta": "பரிந்துரை"},
    "explanation": {"en": "Why this score", "ta": "இந்த மதிப்பு ஏன்"},
    "score": {"en": "Score", "ta": "மதிப்பு"},
    "latency": {"en": "Latency", "ta": "தாமத நேரம்"},
    "compute_cost": {"en": "Compute cost", "ta": "கணக்கீட்டு செலவு"},
    # -------------------------------------------------------------- verdicts --
    "verdict_normal": {
        "en": "Looks like a normal payment. No interruption needed.",
        "ta": "இது இயல்பான பேமெண்ட். தடை தேவையில்லை.",
    },
    "verdict_budget_warning": {
        "en": "Low fraud risk, but this payment hurts your budget. Review and decide.",
        "ta": "மோசடி ஆபத்து குறைவு, ஆனால் இந்த பேமெண்ட் பட்ஜெட்டை பாதிக்கும். பரிசீலித்து முடிவு செய்யுங்கள்.",
    },
    "verdict_fraud_intervention": {
        "en": "High fraud risk. Do not pay until you verify through a channel you trust (bank app / branch / official helpline).",
        "ta": "மோசடி ஆபத்து அதிகம். நம்பக வழியில் (வங்கி ஆப் / கிளை / அதிகாரப்பூர்வ எண்) உறுதி செய்யும் வரை பணம் அனுப்பாதீர்கள்.",
    },
    "verdict_strong_warning": {
        "en": "High fraud risk AND budget overrun. Strongly recommended: stop and verify with someone you trust.",
        "ta": "மோசடி ஆபத்து அதிகம் மற்றும் பட்ஜெட் தாண்டும். நம்பக நபருடன் உறுதி செய்யும் வரை நிற்கவும்.",
    },
    "verdict_budget_missing_fraud": {
        "en": "Budget impact is high, but we could not complete the safety check (missing reason).",
        "ta": "பட்ஜெட் தாக்கம் அதிகம், ஆனால் பாதுகாப்பு பரிசோதனை முழுமையாகவில்லை (காரணம் இல்லை).",
    },
    "verdict_fraud_unknown_budget": {
        "en": "High fraud risk. Verify first — do not assume anything about budget safety.",
        "ta": "மோசடி ஆபத்து அதிகம். முதலில் உறுதி செய்யுங்கள் — பட்ஜெட் பாதுகாப்பைப் பற்றி எதிர்பார்க்க வேண்டாம்.",
    },
    # ------------------------------------------------------------ dashboard ---
    "total_spent": {"en": "Spent this month", "ta": "இந்த மாதம் செலவு"},
    "budget": {"en": "Budget", "ta": "பட்ஜெட்"},
    "remaining": {"en": "Remaining", "ta": "மீதம்"},
    "budget_used": {"en": "Budget used", "ta": "பட்ஜெட் பயன்பாடு"},
    "days_remaining": {"en": "Days remaining", "ta": "மீதம் நாட்கள்"},
    "projected_month_end": {"en": "Projected month-end", "ta": "மாத இறுதி கணிப்பு"},
    "forecast_confidence": {"en": "Forecast confidence", "ta": "கணிப்பு நம்பகத்தன்மை"},
    "daily_allowance": {"en": "Safe to spend per day", "ta": "ஒரு நாளுக்கு பாதுகாப்பான செலவு"},
    "recent_transactions": {"en": "Recent transactions", "ta": "சமீபத்திய பரிவர்த்தனைகள்"},
    "change_category": {"en": "Change category", "ta": "வகையை மாற்று"},
    "uncategorised": {"en": "needs review", "ta": "மறுஆய்வு தேவை"},
    "no_transactions": {"en": "No transactions yet.", "ta": "பரிவர்த்தனைகள் இல்லை."},
    "trend_7d": {"en": "Last 7 days", "ta": "கடந்த 7 நாட்கள்"},
    # -------------------------------------------------------------- budgets ---
    "budget_exceed_month": {
        "en": "This payment goes above your monthly budget.",
        "ta": "இந்த பேமெண்ட் மாத பட்ஜெட்டை தாண்டும்.",
    },
    "budget_exceed_category": {
        "en": "This payment goes above your category limit.",
        "ta": "இந்த பேமெண்ட் வகை வரம்பை தாண்டும்.",
    },
    "projected_overrun_note": {
        "en": "At your current pace the month may end above budget.",
        "ta": "இந்த வேகத்தில் மாதம் பட்ஜெட்டை தாண்டி முடியும்.",
    },
    "discretionary": {"en": "Discretionary money left", "ta": "விருப்ப செலவுக்கு மீதம்"},
    "recurring_upcoming": {
        "en": "Recurring payments expected soon",
        "ta": "விரைவில் எதிர்பார்க்கும் நியமিত பேமெண்ட்கள்",
    },
    # ----------------------------------------------------------- categories ---
    "cat_FOOD": {"en": "Food", "ta": "உணவு"},
    "cat_ESSENTIALS": {"en": "Essentials", "ta": "அத்தியாவசியம்"},
    "cat_HEALTH": {"en": "Health", "ta": "சுகாதாரம்"},
    "cat_TRAVEL": {"en": "Travel", "ta": "பயணம்"},
    "cat_EDUCATION": {"en": "Education", "ta": "கல்வி"},
    "cat_BILLS": {"en": "Bills", "ta": "கட்டணம்"},
    "cat_SHOPPING": {"en": "Shopping", "ta": "வாங்கியவை"},
    "cat_ENTERTAINMENT": {"en": "Entertainment", "ta": "பொழுதுபோக்கு"},
    "cat_TRANSFER": {"en": "Transfer (not spending)", "ta": "பரிமாற்றம் (செலவு அல்ல)"},
    "cat_OTHER": {"en": "Other", "ta": "மற்றவை"},
    # ------------------------------------------------- spending triage card --
    "triage_title": {"en": "Where this month's money went", "ta": "இந்த மாத செலவு"},
    "triage_needs": {"en": "Needs", "ta": "தேவையான செலவுகள்"},
    "triage_wants": {"en": "Wants", "ta": "விருப்ப செலவுகள்"},
    "triage_unnecessary": {"en": "Unnecessary", "ta": "தேவையற்ற செலவுகள்"},
    "triage_total": {"en": "Total spend", "ta": "மொத்த செலவு"},
    "triage_remaining": {"en": "Left in your monthly limit", "ta": "மாதாந்திர வரம்பில் மீதம்"},
    "triage_over": {"en": "Over your monthly limit by", "ta": "மாதாந்திர வரம்பை தாண்டியது"},
    "triage_share": {"en": "share", "ta": "பங்கு"},
    "triage_note": {
        "en": "A simple split so anyone can see what is essential, what is optional and "
              "what could be cut. Re-classify any category in the Judge Panel.",
        "ta": "எது அவசியம், எது விருப்பம், எது குறைக்கலாம் என்பதை எளிதாகப் பார்க்கும் வகைப் பிரிவு. மதிப்பீட்டு பேனலில் எந்த வகையையும் மாற்றிக்கூடலாம்.",
    },
    # -------------------------------------------------------- UPI Black Box --
    "llm_title": {
        "en": "Local AI model (Ollama)",
        "ta": "உள்ளமை AI மாதிரி (Ollama)",
    },
    "llm_what": {
        "en": "Optional: run a real language model on this computer to read the user's reason. "
              "Nothing leaves the machine. The offline lexicon stays the fallback at every step.",
        "ta": "விருப்பத்திற்கு: பயனரின் காரணத்தைப் படிக்க இந்த கணினியிலேயே ஒரு உண்மையான மொழி "
              "மாதிரியை இயக்கலாம். எதுவும் கணினியை விட்டு வெளியேறாது. ஒவ்வொரு நிலையிலும் "
              "இணையத்திற்று இல்லாத மொழிப் பட்டியல் பாதுகாப்பாக இருக்கும்.",
    },
    "llm_detect": {
        "en": "1. Detect this machine",
        "ta": "1. இந்த கணினியைக் கண்டறி",
    },
    "llm_detect_hint": {
        "en": "Reads memory, CPU, GPU and free disk, then recommends the largest model that "
              "fits comfortably.",
        "ta": "நினைவகம், CPU, GPU, காலி வட்டு என்பவற்றைப் படித்து, சிறப்பாக இயங்கும் மிகப் பெரிய "
              "மாதிரியைப் பரிந்துரைக்கும்.",
    },
    "llm_specs_title": {
        "en": "What this machine has",
        "ta": "இந்த கணினியில் உள்ளது",
    },
    "llm_detected": {
        "en": "Detected",
        "ta": "கண்டறியப்பட்டது",
    },
    "llm_ram": {
        "en": "Memory (RAM)",
        "ta": "நினைவகம் (RAM)",
    },
    "llm_disk": {
        "en": "Free disk",
        "ta": "காலி வட்டு",
    },
    "llm_reco_title": {
        "en": "Recommended model",
        "ta": "பரிந்துரைக்கப்பட்ட மாதிரி",
    },
    "llm_download": {
        "en": "download",
        "ta": "பதிவிறக்கம்",
    },
    "llm_needs": {
        "en": "needs",
        "ta": "தேவை",
    },
    "llm_why": {
        "en": "Why",
        "ta": "ஏன்",
    },
    "llm_tamil": {
        "en": "Tamil quality",
        "ta": "தமிழ் தரம்",
    },
    "llm_tamil_weak": {
        "en": "weak — English only for safety-critical wording",
        "ta": "மடுக்கு — பாதுகாப்புக்கு முக்கியமான வார்த்தைகளுக்கு ஆங்கிலம் மட்டும்",
    },
    "llm_tamil_fair": {
        "en": "fair — Tamil is understood, the lexicon is still the safety net",
        "ta": "சராசரி — தமிழ் புரியும், பாதுகாப்புக்கு மொழிப் பட்டியல் தான் உறுதி",
    },
    "llm_tamil_good": {
        "en": "good — handles Tamil well",
        "ta": "நல்லது — தமிழை நன்றாக கையாளும்",
    },
    "llm_model": {
        "en": "Model to use",
        "ta": "பயன்படுத்தும் மாதிரி",
    },
    "llm_host": {
        "en": "Ollama address",
        "ta": "Ollama முகவரி",
    },
    "llm_timeout": {
        "en": "Timeout (seconds)",
        "ta": "காத்திருப்பு (வினாடிகள்)",
    },
    "llm_status_title": {
        "en": "Link status",
        "ta": "இணைப்பு நிலை",
    },
    "llm_step": {
        "en": "Step",
        "ta": "படி",
    },
    "llm_state": {
        "en": "State",
        "ta": "நிலை",
    },
    "llm_installed": {
        "en": "Ollama installed",
        "ta": "Ollama நிறுவப்பட்டது",
    },
    "llm_server": {
        "en": "Server running",
        "ta": "சேவையகம் இயங்குகிறது",
    },
    "llm_model_present": {
        "en": "Model downloaded",
        "ta": "மாதிரி பதிவிறக்கப்பட்டது",
    },
    "llm_linked": {
        "en": "Linked",
        "ta": "இணைக்கப்பட்டது",
    },
    "llm_not_linked": {
        "en": "Not linked",
        "ta": "இணைக்கப்படவில்லை",
    },
    "llm_start_server": {
        "en": "2. Start server",
        "ta": "2. சேவையகத்தை இயக்கு",
    },
    "llm_pull": {
        "en": "3. Download model",
        "ta": "3. மாதிரியைப் பதிவிறக்கு",
    },
    "llm_test": {
        "en": "4. Test the link",
        "ta": "4. இணைப்பைச் சோதி",
    },
    "llm_link_now": {
        "en": "Link now — use the model already on this computer",
        "ta": "இப்போதே இணை — இந்த கணினியில் ஏற்கனவே உள்ள மாதிரியைப் பயன்படுத்து",
    },
    "llm_use_model": {
        "en": "5. Use this model",
        "ta": "5. இந்த மாதிரியைப் பயன்படுத்து",
    },
    "llm_commands": {
        "en": "Or do it yourself — these are the exact commands",
        "ta": "அல்லது நீங்களே செய்யலாம் — இவை துல்லியமான கட்டளைகள்",
    },
    "llm_command": {
        "en": "Command",
        "ta": "கட்டளை",
    },
    "llm_log": {
        "en": "What the last actions printed",
        "ta": "கடைசி நடவடிக்கைகள் காட்டியது",
    },
    "llm_boundary": {
        "en": "Honest boundary: a local model is only as good as its size, and small models "
              "read Tamil far less reliably than the bilingual lexicon. That is why the offline "
              "lexicon stays the fallback for every path — if the model is missing, slow or "
              "answers badly, the app says so and keeps working. Ollama must be installed "
              "separately; this button does not install it silently.",
        "ta": "நேர்மையான எல்லை: உள்ளமை மாதிரியின் தரம் அதன் அளவைப் பொறுத்தது; சிறிய மாதிரிகள் "
              "தமிழை இருமொழிப் பட்டியலை விட நம்பகமாகப் படிக்காது. அதனால் ஒவ்வொரு பாதையிலும் "
              "இணையத்திற்று இல்லாத மொழிப் பட்டியல் பாதுகாப்பாக இருக்கும் — மாதிரி இல்லாவிட்டால், "
              "மெதுவாக இருந்தால் அல்லது மோசமாகப் பதிலளித்தால், பயன்பாடு அதைச் சொல்லி தொடர்ந்து "
              "இயங்கும். Ollama-வை தனியாக நிறுவ வேண்டும்; இந்த பொத்தான் அமைதியாக நிறுவாது.",
    },
    "safe_mode": {
        "en": "Safety features",
        "ta": "பாதுகாப்பு அம்சங்கள்",
    },
    "blackbox_title": {"en": "UPI Black Box", "ta": "UPI கருப்பு பெட்டி"},
    "blackbox_what": {
        "en": "Like an aircraft's black box: the important events around a payment are "
              "recorded in a hash chain, so if something goes wrong the story can be "
              "reconstructed and the record cannot be quietly edited.",
        "ta": "விமானத்தின் கருப்பு பெட்டி போல: பேமெண்ட்டைச் சுற்றிய முக்கிய நிகழ்வுகள் ஹாஷ் "
              "சங்கிலியாக பதிவு செய்யப்படுகின்றன; ஏதும் தவறு நடந்தால் முழு கதையையும் "
              "மீட்டெடுக்க முடியும், பதிவை அமைதியாக மாற்ற முடியாது.",
    },
    "blackbox_timeline": {"en": "Event timeline", "ta": "நிகழ்வு வரலாறு"},
    "blackbox_event": {"en": "Event", "ta": "நிகழ்வு"},
    "blackbox_hash": {"en": "Hash", "ta": "ஹாஷ்"},
    "blackbox_verify": {"en": "Verify integrity", "ta": "அசல்தன்மையை சரிபார்க்க"},
    "blackbox_tamper_demo": {
        "en": "Demo: edit an old entry (proves tampering is detected)",
        "ta": "டெமோ: பழைய பதிவை மாற்று (மாற்றம் கண்டறியப்படும்)",
    },
    "blackbox_integrity_ok": {
        "en": "Chain intact — no entry has been edited, deleted or reordered.",
        "ta": "சங்கிலி பாதுகாப்பாக உள்ளது — எந்த பதிவும் மாற்றப்படவில்லை.",
    },
    "blackbox_integrity_broken": {
        "en": "Chain broken — the record was changed after it was written.",
        "ta": "சங்கிலி உடைந்தது — பதிவு செய்த பிறகு மாற்றப்பட்டது.",
    },
    "blackbox_export": {"en": "Download incident report", "ta": "சம்பவ அறிக்கையை பதிவிறக்கம்"},
    "blackbox_empty": {
        "en": "No payment evaluated yet — the timeline fills as you use the simulator.",
        "ta": "இன்னும் பேமெண்ட் மதிப்பீடு செய்யப்படவில்லை — சிமுலேட்டரைப் பயன்படுத்தும்போது "
              "நிகழ்வுகள் சேர்க்கப்படும்.",
    },
    "blackbox_boundary": {
        "en": "Boundary: a local hash chain is tamper-evident on this device. Production would "
              "anchor the chain to an append-only service or permissioned ledger. It is "
              "evidence, not a reversal — a completed UPI payment cannot be undone.",
        "ta": "வரம்பு: இந்த சாதனத்தில் ஹாஷ் சங்கிலி மாற்றத்தைக் காட்டும். உண்மையான அமலாக்கத்தில் சங்கிலியை மாற்ற முடியாத (append-only) சேவையால் அல்லது அனுமதியுள்ள லெட்ஜரால் உறுதிப்படுத்துவார்கள். இது சான்று மட்டுமே — முடிந்த பேமெண்ட்டை மாற்ற முடியாது.",
    },
    # ---------------------------------------------------- emergency PIN ------
    "decoy_title": {"en": "Emergency PIN (duress protection)", "ta": "அவசர PIN (கட்டாயத்திற்கு பாதுகாப்பு)"},
    "decoy_what": {
        "en": "If someone forces you to pay, enter the emergency PIN instead of your normal "
              "one. The app opens a restricted, harmless environment: it looks real, but no "
              "money moves and a silent alert is recorded.",
        "ta": "யாராவது கட்டாயப்படுத்தி பணம் கேட்டால், சாதாரண PIN-க்குப் பதிலாக அவசர PIN-ஐ "
              "அழுத்துங்கள். ஆப் ஒரு தடுக்கப்பட்ட, தீங்கில்லாத சூழலைத் திறக்கும்: "
              "உண்மையானது போல் தெரியும், ஆனால் பணம் நகராது, ஒரு அமைதிய எச்சரிக்கை பதிவாகிறது.",
    },
    "decoy_pin_label": {"en": "Enter PIN", "ta": "PIN-ஐ உள்ளிடுங்கள்"},
    "decoy_activate": {"en": "Unlock", "ta": "திற"},
    "decoy_active": {
        "en": "Restricted mode active — this is a simulation, nothing real is affected.",
        "ta": "வரையறுக்கப்பட்ட பயன்முறை இயக்கத்தில் — இது உருவகம், உண்மையில் எதுவும் பாதிக்கப்படாது.",
    },
    "decoy_exit": {"en": "Exit restricted mode (demo)", "ta": "வரையறுக்கப்பட்ட பயன்முறையை விடு (டெமோ)"},
    "decoy_balance": {"en": "Visible balance", "ta": "தெரியும் இருப்பு"},
    "decoy_limit": {"en": "Transaction limit", "ta": "பரிவர்த்தனை வரம்பு"},
    "decoy_pay": {"en": "Pay (simulated)", "ta": "செலுத்து (உருவகம்)"},
    "decoy_wrong_pin": {"en": "Wrong PIN.", "ta": "தவறான PIN."},
    "decoy_boundary": {
        "en": "Prototype boundary: the restricted environment is simulated here because no real "
              "UPI app is integrated. A production build needs the bank/PSP, must hide every "
              "sign that it is active, and the limits below are set to zero by default.",
        "ta": "டெமோ வரம்பு: உண்மையான UPI ஆப் இணைக்கப்படாததால் இந்த வரையறுக்கப்பட்ட சூழல் உருவகமாக "
              "உள்ளது. உண்மையான அமலாக்கத்தில் வங்கி/PSP தேவை, இது இயக்கத்தில் உள்ளது என்பதை "
              "மறைக்க வேண்டும், கீழ் உள்ள வரம்புகள் இயல்பாக பூஜ்யம் (0) ஆக இருக்கும்.",
    },
    # ------------------------------------------------------- send money ------
    "send_money_title": {"en": "Send money", "ta": "பணம் அனுப்பு"},
    "send_money_hint": {
        "en": "Fill the payment exactly as you would in a UPI app, then let IntentPay check it "
              "before it leaves.",
        "ta": "UPI ஆப்பில் செய்வது போலவே பேமெண்ட்டை நிரப்பி, அது புறப்படும் முன் IntentPay "
              "சரிபார்க்க விடுங்கள்.",
    },
    "reason_requested": {"en": "Reason requested?", "ta": "காரணம் கேட்கப்பட்டதா?"},
    "reason_yes": {
        "en": "YES — this payment is unusual enough that IntentPay stopped to ask why.",
        "ta": "ஆம் — இந்த பேமெண்ட் போதுமான அளவு அசாதாரணமானது, எனவே IntentPay ஏன் என்று கேட்கிறது.",
    },
    "reason_no": {
        "en": "NO — this payment looks normal, so you were not interrupted.",
        "ta": "இல்லை — இந்த பேமெண்ட் இயல்பானது, எனவே நீங்கள் குறுக்கிடப்படவில்லை.",
    },
    "intent_prompt_title": {"en": "Why are you paying?", "ta": "நீங்கள் ஏன் செலுத்துகிறீர்கள்?"},
    "intent_prompt_hint": {
        "en": "One line in your own words. Nothing is sent anywhere.",
        "ta": "உங்கள் சொந்த வார்த்தையில் ஒரு வரி. எதுவும் எங்கும் அனுப்பப்படாது.",
    },
    "attribution_title": {
        "en": "Why this score (SHAP-style attribution)",
        "ta": "இந்த மதிப்பு ஏன் (SHAP-பாணி பங்களிப்பு)",
    },
    "attribution_note": {
        "en": "The fusion is a weighted sum, so the points below add up to the score exactly — "
              "every reason is visible and checkable.",
        "ta": "மதிப்பு எடையுள்ள கூட்டல், எனவே கீழ் உள்ள புள்ளிகள் மதிப்புடன் சரியாகக் "
              "கூடும் — ஒவ்வொரு காரணமும் தெரியும், சரிபார்க்கக்கூடியது.",
    },
    "attribution_sum": {"en": "Total attributed", "ta": "மொத்தப் புள்ளிகள்"},
    "layers_title": {
        "en": "Fraud layers: what production runs, what this prototype runs",
        "ta": "மோசடி அடுக்குகள்: உண்மையில் எது, இந்த டெமோவில் எது",
    },
    # ---------------------------------------------------------- explanations --
    "expl_amount_high": {
        "en": "Amount is unusually large for this customer",
        "ta": "இந்த வாடிக்கையாளருக்கு தொகை அதிகமாக உள்ளது",
    },
    "expl_new_payee": {
        "en": "First payment to this recipient",
        "ta": "இந்த பெறுபவருக்கு முதல் பேமெண்ட்",
    },
    "expl_night": {
        "en": "Payment at an unusual hour (night)",
        "ta": "இரவு நேரத்தில் செய்யப்படும் பேமெண்ட்",
    },
    "expl_velocity": {
        "en": "Many payments in a short time (velocity)",
        "ta": "குறுகிய நேரத்தில் பல பேமெண்ட்கள்",
    },
    "expl_location": {
        "en": "Paying from an unusual location",
        "ta": "வழக்கமற்ற இடத்தில் பேமெண்ட்",
    },
    "expl_on_call": {
        "en": "Paying while on a call",
        "ta": "அழைப்பில் பேசிக்கொண்டே பேமெண்ட்",
    },
    "expl_battery": {
        "en": "Very low battery (device pressure pattern)",
        "ta": "மிக குறைந்த பேட்டரி (சாதன அழுத்தம்)",
    },
    "expl_link": {
        "en": "Payment arrived through a link",
        "ta": "லிங்க் மூலம் வந்த பேமெண்ட்",
    },
    "expl_device_new": {
        "en": "New / unknown device",
        "ta": "புதிய / தெரியாத சாதனம்",
    },
    "expl_round_amount": {
        "en": "Suspiciously round amount",
        "ta": "சந்தேகத்திற்கு இடமான வட்ட எண் தொகை",
    },
    "expl_payee_reports": {
        "en": "Recipient has fraud reports in demo intelligence",
        "ta": "பெறுபவருக்கு டெமோ தரவில் மோசடி புகார்கள் உள்ளன",
    },
    "expl_category_dev": {
        "en": "Far above normal spending for this category",
        "ta": "இந்த வகைக்கு இயல்பான செலவை விட மிக அதிகம்",
    },
    "expl_personal_handle": {
        "en": "Recipient is a personal phone-number handle (not a verified merchant)",
        "ta": "பெறுபவர் தனிநபர் கைபேசி எண் (சரிபார்க்கப்பட்ட வியாபாரி அல்ல)",
    },
    "expl_recently_added": {
        "en": "Recipient was added to the phone very recently",
        "ta": "பெறுபவர் மிக சமீபத்தில் சேர்க்கப்பட்டார்",
    },
    "expl_unverified_merchant": {
        "en": "Merchant could not be verified",
        "ta": "வியாபாரியை சரிபார்க்க முடியவில்லை",
    },
    "expl_intent_baseline": {
        "en": "Reason contained no scam pattern (baseline intent score)",
        "ta": "காரணத்தில் மோசடி அறிகுறி இல்லை (அடிப்படை நோக்க மதிப்பு)",
    },
    "expl_recipient_baseline": {
        "en": "Recipient carried no risk signal (baseline recipient score)",
        "ta": "பெறுபவருக்கு ஆபத்து அறிகுறி இல்லை (அடிப்படை பெறுபவர் மதிப்பு)",
    },
    "expl_self_transfer_cap": {
        "en": "Own-account transfer: score capped (moving your own money is not a scam signal)",
        "ta": "சொந்த கணக்கு பரிமாற்றம்: மதிப்பு வரம்பிடப்பட்டது (சொந்த பணம் மோசடி அறிகுறி அல்ல)",
    },
    "expl_anomaly": {
        "en": "Behaviour differs from this customer's history (Isolation Forest)",
        "ta": "இந்த வாடிக்கையாளரின் வரலாற்றிலிருந்து நடத்தை மாறுபடுகிறது",
    },
    "expl_urgency": {
        "en": "Reason contains urgency pressure",
        "ta": "காரணத்தில் அவசர அழுத்தம் உள்ளது",
    },
    "expl_authority": {
        "en": "Reason claims authority (bank / police / government)",
        "ta": "காரணம் அதிகாரியைக் குறிப்பிடுகிறது (வங்கி / காவல் / அரசு)",
    },
    "expl_threat": {
        "en": "Reason contains threats (arrest, block, penalty)",
        "ta": "காரணத்தில் பீதி உள்ளது (கைது, தடை, அபராதம்)",
    },
    "expl_secrecy": {
        "en": "Reason asks for secrecy or staying on the call",
        "ta": "காரணம் ரகசியம் / அழைப்பை விடாமல் இருக்க சொல்கிறது",
    },
    "expl_verification": {
        "en": "KYC / verification framing",
        "ta": "KYC / சரிபார்ப்பு காரணம்",
    },
    "expl_safe_account": {
        "en": "'Safe account' / 'hold account' framing",
        "ta": "'பாதுகாப்பான கணக்கு' / 'பணம் வைக்கும் கணக்கு' வகை",
    },
    "expl_lottery": {
        "en": "Lottery / investment / double-money framing",
        "ta": "லட்டரி / முதலீடு / பணத்தை இரட்டிப்பாக்கும் வழி",
    },
    "expl_refund_qr": {
        "en": "'Scan to receive money' pattern (collect-request scam)",
        "ta": "'பணம் பெற ஸ்கேன் செய்' வடிவம் (கலெக்ட் ரிக்வெஸ்ட் மோசடி)",
    },
    "expl_family_emergency": {
        "en": "Family emergency framing (verify by calling the person directly)",
        "ta": "குடும்ப அவசரநிலை (நேரடி அழைப்பால் உறுதி செய்யுங்கள்)",
    },
    "expl_delivery_support": {
        "en": "Fake customer-care / delivery framing",
        "ta": "போலி கஸ்டமர் கேர் / டெலிவரி காரணம்",
    },
    "expl_otp_pin": {
        "en": "Asks for OTP / PIN / card details",
        "ta": "OTP / PIN / கார்டு விவரம் கேட்கிறது",
    },
    "expl_job_fee": {
        "en": "Job / placement fee framing",
        "ta": "வேலை / பிளேஸ்மெண்ட் கட்டணம் கோரிகை",
    },
    "expl_benign": {
        "en": "Reason looks like a normal payment",
        "ta": "காரணம் இயல்பான பேமெண்ட் போல் உள்ளது",
    },
    "expl_intent_unknown": {
        "en": "No reason given for this payment",
        "ta": "இந்த பேமெண்ட்டுக்கு காரணம் தரப்படவில்லை",
    },
    # ---------------------------------------------------------- scam help ----
    "help_title": {"en": "If you think you were scammed — act fast", "ta": "மோசடி எனில் — விரைவாக செயல்படுங்கள்"},
    "help_step1": {
        "en": "1. Call the national cybercrime helpline 1930 immediately (golden hour matters).",
        "ta": "1. உடனே தேசிய சைபர் கிரைம் எண் 1930-ஐ அழைக்கவும் (முதல் ஒரு மணி நேரம் மிக முக்கியம்).",
    },
    "help_step2": {
        "en": "2. File a report at cybercrime.gov.in (also use 'Report and Check Suspect').",
        "ta": "2. cybercrime.gov.in-இல் புகார் அளிக்கவும் ('Report and Check Suspect' பயன்படுத்தவும்).",
    },
    "help_step3": {
        "en": "3. Call your bank's helpline and ask them to freeze the recipient account / raise a dispute with the UTR.",
        "ta": "3. வங்கி எண்ணை அழைத்து பெறுபவர் கணக்கு உறைத்து, UTR-உடன் புகார் பதிவு செய்ய சொல்லவும்.",
    },
    "help_step4": {
        "en": "4. Keep evidence: screenshots, call logs, UPI transaction IDs (UTR), messages.",
        "ta": "4. சாட்சி கையாளுங்கள்: ஸ்கிரீன்ஷாட், அழைப்பு பதிவேட்டு, UTR, செய்திகள்.",
    },
    "help_step5": {
        "en": "5. Never share OTP, UPI PIN or passwords with anyone — banks and police never ask.",
        "ta": "5. OTP, UPI PIN, கடவுச்சொல்லை யாருடனும் பகிர்ந்து கொள்ளாதீர்கள் — வங்கி / காவல் ஒருபோதும் கேட்காது.",
    },
    "help_note": {
        "en": "Honest limitation: this app cannot reverse a completed UPI payment. Only your bank, NPCI or the recipient can. Speed is everything.",
        "ta": "உண்மை: செலுத்திய பேமெண்ட்டை இந்த ஆப் திரும்ப பெற முடியாது. வங்கி, NPCI அல்லது பெறுபவர் மட்டுமே முடியும். விரைவு மிக முக்கியம்.",
    },
    "complaint_draft": {"en": "Complaint draft (copy this)", "ta": "புகார் வரைவு (இதை நகலெடுங்கள்)"},
    "utr": {"en": "Demo UTR reference", "ta": "டெமோ UTR குறிப்பு"},
    # ---------------------------------------------------------------- voice ---
    "voice_unavailable": {
        "en": "Voice is not available in this environment (optional packages missing). Typing works the same.",
        "ta": "இந்த சூழலில் குரல் கிடைக்கவில்லை (விருப்ப பாக்கேஜ்கள் இல்லை). தட்டச்சு செய்தாலும் அதே பலன்.",
    },
    "voice_listening": {"en": "Listening…", "ta": "கேட்கிறேன்…"},
    "voice_answer_total": {
        "en": "This month you spent {spent}. Budget {budget}, remaining {remaining}.",
        "ta": "இந்த மாதம் {spent} செலவாகியுள்ளது. பட்ஜெட் {budget}, மீதம் {remaining}.",
    },
    "voice_answer_remaining": {
        "en": "You have {remaining} left this month out of {budget}.",
        "ta": "இந்த மாதத்தில் {budget}-இல் {remaining} மீதம் உள்ளது.",
    },
    "voice_answer_category": {
        "en": "{category} spending this month is {spent}.",
        "ta": "இந்த மாதம் {category} செலவு {spent}.",
    },
    "voice_answer_why": {
        "en": "The main risk signals were: {signals}.",
        "ta": "முக்கிய ஆபத்து அறிகுறிகள்: {signals}.",
    },
    "voice_help": {
        "en": "Ask: how much did I spend, how much is left, food spending, or why is this risky.",
        "ta": "கேளுங்கள்: எவ்வளவு செலவு, எவ்வளவு மீதம், உணவு செலவு, ஏன் ஆபத்து.",
    },
    # --------------------------------------------------------------- metrics --
    "metrics_precision": {"en": "Precision", "ta": "துல்லியம் (Precision)"},
    "metrics_recall": {"en": "Recall", "ta": "ரிகால்"},
    "metrics_f1": {"en": "F1 score", "ta": "F1 மதிப்பு"},
    "metrics_fpr": {"en": "False positive rate", "ta": "தவறான எச்சரிக்கை விகிதம்"},
    "metrics_accuracy": {"en": "Accuracy", "ta": "துல்லியம்"},
    "metrics_mcc": {"en": "MCC", "ta": "MCC"},
    "metrics_interruption": {"en": "Interruption rate", "ta": "குறுக்கிட விகிதம்"},
    "metrics_latency": {"en": "Decision latency", "ta": "முடிவு நேரம்"},
    "metrics_loss": {"en": "Expected loss (cost model)", "ta": "எதிர்பார்க்கும் இழப்பு (செலவு மாதிரி)"},
    "metrics_run": {"en": "Run evaluation", "ta": "மதிப்பீடு ஓட்டு"},
    "metrics_running": {"en": "Evaluating…", "ta": "மதிப்பிடுகிறது…"},
    "metrics_note": {
        "en": "Synthetic labelled set — proves the pipeline works end to end, not production accuracy.",
        "ta": "செயற்கை லேபிள் தரவு — உற்பத்தி தரம் அல்ல, நிலைமை முழுமைக்கு உதவும்.",
    },
    "metrics_confusion": {"en": "Confusion matrix", "ta": "குழப்பு அணி"},
    "metrics_family": {"en": "Recall by scam family", "ta": "மோசடி வகையின்படி ரிகால்"},
    "metrics_threshold_sweep": {"en": "Threshold sweep (F1 optimum)", "ta": "எல்லை ஸ்கேன் (F1 சிறந்தது)"},
    "metrics_ablation": {"en": "What each layer adds", "ta": "ஒவ்வொரு அடுக்கின் பங்கு"},
    # ----------------------------------------------------------------- about --
    "about_what": {
        "en": "IntentPay asks 'why are you paying?' before risky payments, and answers 'where did my money go?' around them.",
        "ta": "IntentPay ஆபத்தான பேமெண்ட்டுக்கு முன் 'ஏன் செலுத்துகிறீர்கள்?' என்று கேட்டு, செலவுகளைப் பற்றி 'என் பணம் எங்கே போயிறது?' என்று பதில் சொல்கிறது.",
    },
    "about_boundary": {
        "en": "Prototype boundary: synthetic data, localhost, no UPI PIN/OTP/password, no call recording, no claim of reversing completed payments.",
        "ta": "எல்லை: செயற்கை தரவு, லோக்கல்ஹோஸ்ட், UPI PIN/OTP/கடவுச்சொல் இல்லை, அழைப்பு பதிவேட்டு இல்லை, செலுத்திய பேமெண்ட்டை திரும்ப பெறுவதா எனும் உறுதிமொழி இல்லை.",
    },
}


def t(key: str, lang: str = "en", **fmt: Any) -> str:
    """Translate a key; falls back to English, then to the key itself."""
    entry = STRINGS.get(key, {})
    text = entry.get(lang) or entry.get("en") or key
    if fmt:
        try:
            text = text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def category_label(category: str, lang: str = "en") -> str:
    return t(f"cat_{category}", lang)


def band_label(band: str, lang: str = "en") -> str:
    mapping = {
        "LOW": "low",
        "MEDIUM": "medium",
        "HIGH": "high",
        "CRITICAL": "critical",
        "SAFE": "safe",
        "WATCH": "watch",
        "NEAR LIMIT": "near_limit",
        "EXCEEDED": "exceeded",
        "PROJECTED OVERRUN": "overrun",
    }
    return t(mapping.get(band, "low"), lang)


def available_languages() -> list:
    return ["en", "ta"]
