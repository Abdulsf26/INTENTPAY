"""Deterministic synthetic data generator for the demo.

* two customer profiles (a salaried professional in Chennai; a retired,
  Tamil-first senior citizen in Coimbatore),
* ~120 days of realistic transaction history per customer (including
  recurring subscriptions, monthly rent, term fees and self-transfers),
* a labelled evaluation set (normal vs. seven social-engineering families),
* the one-click demo scenarios used by the simulator.

Everything is seeded, so the same date always produces the same demo — a
judge can change a parameter and see exactly what changed.  Amounts are tuned
so each demo customer starts the month in a realistic state (roughly 75-85%
of budget used) which makes the budget-warning scenarios demonstrable.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from SRC.MODELS import CustomerProfile, Transaction, make_utr

# --------------------------------------------------------------------------- #
#  Merchant catalogues (English + Tamil labels)
# --------------------------------------------------------------------------- #

MERCHANTS: Dict[str, List[Dict[str, Any]]] = {
    "FOOD": [
        {"en": "Annai Grocery Store", "ta": "அன்னை கிரானா", "mean": 300, "sd": 90},
        {"en": "Saravana Hotel", "ta": "சரவணா ஹோட்டல்", "mean": 140, "sd": 45},
        {"en": "Nilgiris Supermarket", "ta": "நீலகிரி சூப்பர் மார்க்கெட்", "mean": 480, "sd": 160},
        {"en": "Milk Co-op", "ta": "பாலா சங்கம்", "mean": 32, "sd": 6},
    ],
    "ESSENTIALS": [
        {"en": "Water Board", "ta": "நீர்வாரம்", "mean": 130, "sd": 30},
    ],
    "HEALTH": [
        {"en": "Apollo Pharmacy", "ta": "அப்போலோ மருந்துக் கடை", "mean": 380, "sd": 160},
        {"en": "City Clinic", "ta": "சிட்டி கிளினிக்", "mean": 520, "sd": 220},
    ],
    "TRAVEL": [
        {"en": "Indian Oil Fuel", "ta": "இந்தியன் ஆயில்", "mean": 650, "sd": 250},
        {"en": "TNSTC Bus", "ta": "டிஎன்எஸ்டிசி பஸ்", "mean": 45, "sd": 20},
        {"en": "Metro Card Topup", "ta": "மெட்ரோ டாப்அப்", "mean": 150, "sd": 60},
    ],
    "EDUCATION": [
        {"en": "Stationery Shop", "ta": "ஸ்டேஷனரி", "mean": 180, "sd": 90},
    ],
    "BILLS": [
        {"en": "Tata Power", "ta": "டாடா பவர்", "mean": 620, "sd": 240},
        {"en": "Airtel Mobile", "ta": "ஏர்டெல் மொபைல்", "mean": 279, "sd": 0},
        {"en": "Netflix", "ta": "நெட்ஃபிக்ஸ்", "mean": 499, "sd": 0},
    ],
    "SHOPPING": [
        {"en": "Amazon", "ta": "அமேசான்", "mean": 900, "sd": 700},
        {"en": "Big Bazaar", "ta": "பிக் பஜார்", "mean": 600, "sd": 400},
    ],
    "ENTERTAINMENT": [
        {"en": "PVR Cinemas", "ta": "பிவிஆர் சினிமா", "mean": 420, "sd": 140},
        {"en": "Zomato", "ta": "ஜோமேட்டோ", "mean": 360, "sd": 150},
    ],
}

CATEGORY_MIX: Dict[str, Dict[str, float]] = {
    "customer_one": {
        "FOOD": 0.69, "ESSENTIALS": 0.05, "HEALTH": 0.06, "TRAVEL": 0.08,
        "EDUCATION": 0.04, "BILLS": 0.0, "SHOPPING": 0.05, "ENTERTAINMENT": 0.03,
    },
    "customer_two": {
        "FOOD": 0.62, "ESSENTIALS": 0.06, "HEALTH": 0.11, "TRAVEL": 0.07,
        "EDUCATION": 0.02, "BILLS": 0.04, "SHOPPING": 0.04, "ENTERTAINMENT": 0.02,
    },
}

# purchases per day choice weights (index = number of purchases)
PURCHASE_WEIGHTS = {
    "customer_one": [44, 30, 18, 7, 1, 0],
    "customer_two": [42, 30, 20, 7, 1, 0],
}

AMOUNT_SCALE = {"customer_one": 0.82, "customer_two": 0.55}

RENT = {"customer_one": 3800.0, "customer_two": 2500.0}
SELF_TRANSFER = {"customer_one": 3000.0, "customer_two": 2000.0}
SCHOOL_FEE = {"customer_one": 2400.0, "customer_two": 900.0}

CITIES = {
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Bengaluru": (12.9716, 77.5946),
}

HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 4, 7, 8, 8, 7, 7, 8, 7, 6, 6, 7, 8, 9, 10, 8, 5, 3, 2]


def customer_profiles() -> Dict[str, CustomerProfile]:
    """The two demo customers (editable live in the Judge panel)."""
    return {
        "customer_one": CustomerProfile(
            customer_id="customer_one",
            name="Arun Kumar",
            age=34,
            language="en",
            elder_mode=False,
            usual_city="Chennai",
            usual_lat=CITIES["Chennai"][0],
            usual_lon=CITIES["Chennai"][1],
            typical_amount=520.0,
            monthly_limit=15000.0,
            category_limits={"FOOD": 6000.0},
            known_devices=["device-android-01", "device-windows-02"],
            own_upi_ids=["arun@okhdfc", "arun.savings@okhdfc"],
            known_payees=[
                {"name": "Annai Grocery Store", "upi_id": "annaigrocery@ybl"},
                {"name": "Saravana Hotel", "upi_id": "saravanahotel@ybl"},
                {"name": "Apollo Pharmacy", "upi_id": "apollopharm@axl"},
                {"name": "Airtel Mobile", "upi_id": "airtel@icici"},
                {"name": "Rent - Landlord", "upi_id": "landlord.chennai@hdfcbank"},
                {"name": "Priya (sister)", "upi_id": "priya.k@okaxis"},
            ],
            seed=11,
        ),
        "customer_two": CustomerProfile(
            customer_id="customer_two",
            name="Meenakshi Ammal",
            age=68,
            language="ta",
            elder_mode=True,
            usual_city="Coimbatore",
            usual_lat=CITIES["Coimbatore"][0],
            usual_lon=CITIES["Coimbatore"][1],
            typical_amount=260.0,
            monthly_limit=9000.0,
            category_limits={"FOOD": 3500.0, "HEALTH": 2000.0},
            known_devices=["device-android-mom"],
            own_upi_ids=["meena@okaxis", "meena.savings@okaxis"],
            known_payees=[
                {"name": "அன்னை கிரானா", "upi_id": "annaigrocery@ybl"},
                {"name": "அப்போலோ மருந்துக் கடை", "upi_id": "apollopharm@axl"},
                {"name": "Rent - Landlord", "upi_id": "landlord.cbe@hdfcbank"},
                {"name": "Rajan (son)", "upi_id": "rajan.m@oksbi"},
            ],
            seed=23,
        ),
    }


def _label(merchant: Dict[str, Any], language: str) -> str:
    return merchant["ta"] if language == "ta" else merchant["en"]


def _pick_category(rng: random.Random, mix: Dict[str, float]) -> str:
    roll = rng.random()
    cumulative = 0.0
    for category, weight in mix.items():
        cumulative += weight
        if roll <= cumulative:
            return category
    return "FOOD"


def generate_customer_history(
    profile: CustomerProfile, today: Optional[datetime] = None, days: int = 120
) -> pd.DataFrame:
    """Deterministic ~120-day transaction history for one customer."""
    today = (today or datetime.now()).replace(hour=20, minute=0, second=0, microsecond=0)
    rng = random.Random(profile.seed)
    mix = CATEGORY_MIX[profile.customer_id]
    language = profile.language
    scale = AMOUNT_SCALE[profile.customer_id]
    rows: List[Transaction] = []
    counter = 0

    def add(when: datetime, amount: float, merchant_label: str, category: str, upi: str,
            essential: bool = False, recurring: bool = False, note: str = "",
            self_transfer: bool = False) -> None:
        nonlocal counter
        counter += 1
        rows.append(
            Transaction(
                id=f"{profile.customer_id}-{counter:04d}",
                timestamp=when,
                amount=round(float(amount), 2),
                direction="DEBIT",
                merchant_label=merchant_label,
                upi_id=upi,
                source="demo",
                category=category,
                category_confidence=0.95,
                essential_flag=essential,
                recurring_flag=recurring,
                self_transfer=self_transfer,
                note=note,
                utr=make_utr(profile.customer_id, counter, when),
            )
        )

    for day_offset in range(days, -1, -1):
        day = today - timedelta(days=day_offset)
        weekday = day.weekday()
        n_purchases = rng.choices(
            [0, 1, 2, 3, 4, 5], weights=PURCHASE_WEIGHTS[profile.customer_id]
        )[0]
        if weekday >= 5:
            n_purchases += rng.choices([0, 1], weights=[60, 40])[0]
        for _ in range(n_purchases):
            category = _pick_category(rng, mix)
            merchant = rng.choice(MERCHANTS[category])
            amount = max(10.0, rng.gauss(merchant["mean"], merchant["sd"] or 1.0)) * scale
            hour = rng.choices(range(24), weights=HOUR_WEIGHTS)[0]
            when = day.replace(hour=hour, minute=rng.randint(0, 59))
            add(when, amount, _label(merchant, language), category,
                f"{merchant['en'].split()[0].lower()}@upi",
                essential=(category in ("FOOD", "HEALTH")))

        # monthly rent on the 3rd
        if day.day == 3:
            add(day.replace(hour=9, minute=30), RENT[profile.customer_id], "House Rent",
                "ESSENTIALS", "landlord@hdfcbank", essential=True, note="monthly rent")
        # term fees in April and June
        if day.day == 10 and day.month in (4, 6):
            add(day.replace(hour=11, minute=0), SCHOOL_FEE[profile.customer_id], "School Fees",
                "EDUCATION", "school@icici", essential=True, note="term fee")
        # monthly electricity bill on the 18th
        if day.day == 18:
            add(day.replace(hour=10, minute=15), 620.0 * (0.7 if profile.customer_id == "customer_two" else 1.0),
                "Tata Power", "BILLS", "tatapower@icici", essential=True, note="electricity bill")
        # self transfer to own savings (excluded from spending totals)
        if day.day in (7, 22):
            add(day.replace(hour=18, minute=15), SELF_TRANSFER[profile.customer_id], "Own Savings",
                "TRANSFER", profile.own_upi_ids[-1], note="self transfer", self_transfer=True)

    # explicit recurring commitments (same merchant + amount, regular gaps)
    recurring_plan = [
        ("Netflix", "BILLS", 499.0, 1, 30),
        ("Airtel Mobile", "BILLS", 279.0, 5, 30),
        ("Milk Co-op", "FOOD", 32.0, 3, 5),
    ]
    if profile.customer_id == "customer_two":
        recurring_plan = [
            ("Airtel Mobile", "BILLS", 279.0, 5, 30),
            ("Milk Co-op", "FOOD", 32.0, 3, 5),
            ("Saravana Hotel", "FOOD", 140.0, 2, 7),
        ]
    for name, category, amount, start_day, gap in recurring_plan:
        for k in range(days // gap + 1):
            when = today - timedelta(days=start_day + k * gap)
            if when > today:
                continue
            merchant = next(m for m in MERCHANTS[category] if m["en"] == name)
            add(when.replace(hour=10, minute=0), amount, _label(merchant, language), category,
                f"{name.split()[0].lower()}@icici", essential=True, recurring=True)

    frame = pd.DataFrame([t.to_dict() for t in rows])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    return frame


# --------------------------------------------------------------------------- #
#  Labelled evaluation set
# --------------------------------------------------------------------------- #


def generate_eval_set(today: Optional[datetime] = None) -> pd.DataFrame:
    """A labelled set of candidate payments used by the Metrics page."""
    rng = random.Random(4242)
    rows: List[Dict[str, Any]] = []

    def add(family: str, label: int, amount: float, purpose: str, on_call: bool,
            call_minutes: int, channel: str, new_payee: bool, hour: int) -> None:
        rows.append(
            {
                "family": family,
                "label": label,
                "amount": round(amount, 2),
                "purpose": purpose,
                "on_call": on_call,
                "call_duration_s": call_minutes * 60,
                "channel": channel,
                "new_payee": new_payee,
                "hour": hour,
            }
        )

    # ---- normal payments (label 0)
    normal_purposes = [
        "monthly grocery shopping at the usual store",
        "milk and vegetables from the co-op",
        "electricity bill payment",
        "mobile recharge",
        "medicine for blood pressure from Apollo",
        "bus pass topup for daily commute",
        "school fees for my daughter",
        "house rent transfer to landlord",
        "fuel for the scooter",
        "dinner at the usual hotel",
    ]
    for _ in range(180):
        add("normal", 0, round(max(40, rng.gauss(520, 380)), 2), rng.choice(normal_purposes),
            on_call=False, call_minutes=0,
            channel=rng.choices(["P2P", "QR"], weights=[70, 30])[0],
            new_payee=rng.random() < 0.15,
            hour=rng.choices(range(24), weights=HOUR_WEIGHTS)[0])

    # ---- tricky-but-legitimate payments (label 0, deliberately signal-rich)
    tricky = [
        ("hospital called, my father needs surgery money today", True, 25, "P2P", True, 23),
        ("accident emergency, please send quickly", True, 40, "LINK", True, 22),
        ("plumber came at night for urgent repair", False, 0, "QR", True, 23),
        ("late night cab, driver waiting", False, 0, "QR", True, 23),
        ("new shopkeeper asked for advance", False, 0, "P2P", True, 19),
    ]
    for purpose, on_call, minutes, channel, new_payee, hour in tricky * 6:
        add("tricky_benign", 0, round(max(500, rng.gauss(3500, 1800)), 2), purpose,
            on_call=on_call, call_minutes=minutes, channel=channel,
            new_payee=new_payee, hour=hour)

    # ---- social-engineering families (label 1)
    families: List[Dict[str, Any]] = [
        {
            "family": "bank_impersonation", "count": 30,
            "purposes": [
                "bank manager called, my KYC is incomplete, pay to safe account to verify",
                "SBI officer said account will be blocked, need to deposit to RBI safe account",
                "bank verification pending, transfer to government account immediately",
                "customer care said re-kyc needed, share otp to verify my card",
            ],
            "amount": (4000, 45000), "on_call": True, "minutes": (10, 40),
            "channel": "LINK", "new_payee": True, "hour": (9, 21),
        },
        {
            "family": "digital_arrest", "count": 30,
            "purposes": [
                "police called, case registered against me, stay on video call and pay to avoid arrest",
                "CBI officer said digital arrest, don't tell anyone, transfer to safe account",
                "customs officer threatened arrest, pay penalty immediately",
                "cyber cell said my aadhaar is linked to crime, keep the call on and pay",
            ],
            "amount": (25000, 250000), "on_call": True, "minutes": (45, 240),
            "channel": "P2P", "new_payee": True, "hour": (8, 23),
        },
        {
            "family": "lottery_investment", "count": 25,
            "purposes": [
                "won lottery, pay processing fee to receive prize",
                "investment scheme doubles money, guaranteed returns",
                "crypto trading group, pay registration fee",
                "click this link to claim jackpot, pay tax",
            ],
            "amount": (2000, 60000), "on_call": False, "minutes": (0, 0),
            "channel": "LINK", "new_payee": True, "hour": (10, 23),
        },
        {
            "family": "refund_qr", "count": 25,
            "purposes": [
                "scan this qr to receive refund",
                "scan to receive money, cashback pending",
                "enter pin to receive the refund",
                "approve the collect request to get your money back",
            ],
            "amount": (1, 5000), "on_call": True, "minutes": (5, 30),
            "channel": "QR", "new_payee": True, "hour": (9, 22),
        },
        {
            "family": "fake_support", "count": 25,
            "purposes": [
                "electricity meter update, pay 10 rupees to the support team",
                "courier parcel held, pay customs fee via link",
                "customer care sent apk for mobile recharge offer",
                "delivery agent asked to scan for verification",
            ],
            "amount": (10, 15000), "on_call": True, "minutes": (5, 45),
            "channel": "LINK", "new_payee": True, "hour": (9, 22),
        },
        {
            "family": "job_fee", "count": 20,
            "purposes": [
                "job offer, pay registration fee",
                "work from home data entry job, pay training fee",
                "placement fee for offer letter",
                "part time job, pay security deposit",
            ],
            "amount": (500, 20000), "on_call": False, "minutes": (0, 0),
            "channel": "LINK", "new_payee": True, "hour": (10, 21),
        },
        {
            "family": "family_emergency_scam", "count": 20,
            "purposes": [
                "my son met an accident, hospital needs money urgently, new number",
                "daughter in hospital, pay immediately to unknown account",
                "mother admitted, don't call back, transfer to this number",
            ],
            "amount": (10000, 90000), "on_call": True, "minutes": (10, 60),
            "channel": "P2P", "new_payee": True, "hour": (0, 23),
        },
    ]
    for spec in families:
        for _ in range(spec["count"]):
            lo, hi = spec["amount"]
            add(spec["family"], 1, round(rng.uniform(lo, hi), 2), rng.choice(spec["purposes"]),
                on_call=spec["on_call"],
                call_minutes=rng.randint(*spec["minutes"]) if spec["minutes"][1] else 0,
                channel=spec["channel"], new_payee=spec["new_payee"],
                hour=rng.randint(*spec["hour"]))

    frame = pd.DataFrame(rows)
    frame.insert(0, "eval_id", [f"EVAL-{i:04d}" for i in range(1, len(frame) + 1)])
    return frame


# --------------------------------------------------------------------------- #
#  Demo scenarios (one-click in the simulator)
# --------------------------------------------------------------------------- #


def demo_scenarios() -> Dict[str, Any]:
    """One-click scenarios.  Every field is editable afterwards."""
    return {
        "normal_500": {
            "label_en": "Normal ₹500 grocery",
            "label_ta": "இயல்பான ₹500 மளிகை",
            "hint_en": "Known merchant, daytime, no call -> LOW risk, no interruption.",
            "hint_ta": "தெரிந்த கடை, பகல் நேரம், அழைப்பு இல்லை -> குறைந்த ஆபத்து.",
            "payment": {
                "amount": 500, "method": "UPI", "payee_name": "Annai Grocery Store",
                "payee_upi": "annaigrocery@ybl", "purpose_category": "FOOD",
                "hour": 11, "city": "Chennai", "on_call": False, "call_duration_s": 0,
                "channel": "P2P", "new_payee": False, "device_id": "device-android-01",
                "battery_pct": 85, "intent_text": "monthly grocery shopping at the usual store",
                "intent_text_ta": "வழக்கமான மளிகை கடையில் மாத மளிகை வாங்குகிறேன்",
            },
        },
        "new_payee_25000": {
            "label_en": "New payee ₹25,000",
            "label_ta": "புதிய பெறுபவர் ₹25,000",
            "hint_en": "No reason given -> IntentPay asks WHY, then you type any reason and watch the score move.",
            "hint_ta": "காரணம் இல்லை -> IntentPay ஏன் என்று கேட்கும்; காரணம் சொன்னால் மதிப்பு மாறும்.",
            "payment": {
                "amount": 25000, "method": "UPI", "payee_name": "Unknown Person",
                "payee_upi": "9876543210@ybl", "purpose_category": "OTHER",
                "hour": 19, "city": "Chennai", "on_call": False, "call_duration_s": 0,
                "channel": "P2P", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 72, "intent_text": "",
            },
        },
        "fake_bank_call": {
            "label_en": "Fake bank call",
            "label_ta": "போலி வங்கி அழைப்பு",
            "hint_en": "'Bank officer' + urgency + safe account -> HIGH intent risk.",
            "hint_ta": "'வங்கி அதிகாரி' + அவசரம் + பாதுகாப்பான கணக்கு -> அதிக நோக்க ஆபத்து.",
            "payment": {
                "amount": 15000, "method": "UPI", "payee_name": "Bank Verification",
                "payee_upi": "kyc.safe.account@demo", "purpose_category": "OTHER",
                "hour": 15, "city": "Chennai", "on_call": True, "call_duration_s": 1500,
                "channel": "LINK", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 46, "intent_text": "bank manager called, KYC incomplete, pay to safe account to verify immediately",
                "intent_text_ta": "வங்கி அதிகாரி கூறினார், கேஒய்சி முடிக்கவில்லை, பாதுகாப்பான கணக்குக்கு உடனே அனுப்புங்கள்",
            },
        },
        "digital_arrest": {
            "label_en": "Digital arrest",
            "label_ta": "டிஜிட்டல் கைது",
            "hint_en": "Police impersonation + threats + secrecy -> CRITICAL.",
            "hint_ta": "காவல் போலி + பீதி + ரகசியம் -> மிக உயர் ஆபத்து.",
            "payment": {
                "amount": 75000, "method": "UPI", "payee_name": "Cyber Cell Officer",
                "payee_upi": "cybercell.gov@demo", "purpose_category": "OTHER",
                "hour": 21, "city": "Chennai", "on_call": True, "call_duration_s": 5400,
                "channel": "P2P", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 18, "intent_text": "police called, case registered, stay on video call, don't tell anyone, pay to avoid arrest",
                "intent_text_ta": "காவல் துறை வழக்கு பதிந்தது என்று சொன்னார், வீடியோ அழைப்பில் இருங்கள், யாரிடமும் சொல்லாதே, கைதை தவிர்க்க பணம் அனுப்புங்கள்",
            },
        },
        "food_1200_over_budget": {
            "label_en": "Food ₹1,200 (budget)",
            "label_ta": "உணவு ₹1,200 (பட்ஜெட்)",
            "hint_en": "Low fraud risk, but exceeds the food limit -> budget warning.",
            "hint_ta": "மோசடி ஆபத்து குறைவு, உணவு வரம்பை தாண்டும் -> பட்ஜெட் எச்சரிக்கை.",
            "payment": {
                "amount": 1200, "method": "UPI", "payee_name": "Nilgiris Supermarket",
                "payee_upi": "nilgiris@ybl", "purpose_category": "FOOD",
                "hour": 12, "city": "Chennai", "on_call": False, "call_duration_s": 0,
                "channel": "P2P", "new_payee": False, "device_id": "device-android-01",
                "battery_pct": 80, "intent_text": "festival grocery shopping",
                "intent_text_ta": "பண்டிகர் மளிகை வாங்குதல்",
            },
        },
        "lottery_fee": {
            "label_en": "Lottery fee",
            "label_ta": "லாட்டரி கட்டணம்",
            "hint_en": "'Won lottery, pay processing fee' -> HIGH intent risk.",
            "hint_ta": "'லாட்டரி வெற்றி, கட்டணம் செலுத்து' -> அதிக நோக்க ஆபத்து.",
            "payment": {
                "amount": 25000, "method": "UPI", "payee_name": "Prize Cell",
                "payee_upi": "prize.lottery@demo", "purpose_category": "OTHER",
                "hour": 22, "city": "Chennai", "on_call": False, "call_duration_s": 0,
                "channel": "LINK", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 33, "intent_text": "won lottery, pay processing fee to receive the prize money",
                "intent_text_ta": "லாட்டரி பரிசு வென்றுள்ளேன், பரிசு பணம் பெற கட்டணம் செலுத்த வேண்டும்",
            },
        },
        "qr_refund_scam": {
            "label_en": "QR refund scam",
            "label_ta": "QR ரிஃபண்ட் மோசடி",
            "hint_en": "'Scan QR to receive refund' is a collect-request pattern.",
            "hint_ta": "'பணம் பெற ஸ்கேன்' என்பது கலெக்ட் ரிக்வெஸ்ட் மோசடி.",
            "payment": {
                "amount": 10, "method": "UPI", "payee_name": "Refund Desk",
                "payee_upi": "refund.desk@demo", "purpose_category": "OTHER",
                "hour": 14, "city": "Chennai", "on_call": True, "call_duration_s": 900,
                "channel": "QR", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 60, "intent_text": "scan this qr to receive my refund",
                "intent_text_ta": "ரிஃபண்ட் பெற கியூஆர் ஸ்கேன் செய்யுங்கள், கேஷ்பேக் நிலுவையில் உள்ளது",
            },
        },
        "night_low_battery": {
            "label_en": "Night + low battery",
            "label_ta": "இரவு + குறைந்த பேட்டரி",
            "hint_en": "Unusual hour, low battery, new payee, payment link.",
            "hint_ta": "இரவு நேரம், குறைந்த பேட்டரி, புதிய பெறுபவர், லிங்க்.",
            "payment": {
                "amount": 9000, "method": "UPI", "payee_name": "Quick Help",
                "payee_upi": "quick.help@demo", "purpose_category": "OTHER",
                "hour": 23, "city": "Chennai", "on_call": True, "call_duration_s": 600,
                "channel": "LINK", "new_payee": True, "device_id": "device-unknown-99",
                "battery_pct": 9, "intent_text": "urgent help needed tonight",
                "intent_text_ta": "இன்று இரவு உடனே உதவி தேவை, தாமதிக்காதே",
            },
        },
        "family_emergency": {
            "label_en": "Family emergency",
            "label_ta": "குடும்ப அவசரம்",
            "hint_en": "Genuine emergencies exist: moderate signal, verify by calling.",
            "hint_ta": "உண்மையான அவசரம் உண்டு: நடுத்தர அறிகுறி, நேரடி அழைப்பில் உறுதி செய்யுங்கள்.",
            "payment": {
                "amount": 20000, "method": "UPI", "payee_name": "New Number",
                "payee_upi": "new.number@ybl", "purpose_category": "OTHER",
                "hour": 2, "city": "Chennai", "on_call": True, "call_duration_s": 1200,
                "channel": "P2P", "new_payee": True, "device_id": "device-android-01",
                "battery_pct": 55, "intent_text": "my son met with an accident, hospital needs money urgently",
                "intent_text_ta": "என் மகன் விபத்தில் சிக்கினார், மருத்துவமனைக்கு உடனே பணம் தேவை",
            },
        },
        "self_transfer": {
            "label_en": "Own account transfer",
            "label_ta": "சொந்த கணக்கு பரிமாற்றம்",
            "hint_en": "Moving your own money is not spending -> excluded from budget.",
            "hint_ta": "சொந்த பணம் பரிமாற்றம் செலவு அல்ல -> பட்ஜெட்டில் கணக்கிடப்படாது.",
            "payment": {
                "amount": 3000, "method": "UPI", "payee_name": "Own Savings",
                "payee_upi": "arun.savings@okhdfc", "purpose_category": "TRANSFER",
                "hour": 18, "city": "Chennai", "on_call": False, "call_duration_s": 0,
                "channel": "P2P", "new_payee": False, "device_id": "device-android-01",
                "battery_pct": 88, "intent_text": "moving my own money to savings",
                "intent_text_ta": "சொந்த சேமிப்பு கணக்குக்கு பணம் மாற்றுகிறேன்",
            },
        },
    }


def golden_demo_pair() -> Dict[str, Any]:
    """The same payment in two contexts (ordinary reason vs. coerced reason)."""
    base = {
        "amount": 25000, "method": "UPI", "payee_name": "Ravi (cousin)",
        "payee_upi": "ravi.cousin@ybl", "purpose_category": "OTHER",
        "hour": 19, "city": "Chennai", "on_call": False, "call_duration_s": 0,
        "channel": "P2P", "new_payee": True, "device_id": "device-android-01",
        "battery_pct": 70,
    }
    return {
        "ordinary": {**base, "intent_text": "cousin's college admission fees",
                     "intent_text_ta": "சிறிய தகப்பனார் கல்லூரி சேர்க்கை கட்டணம்"},
        "coerced": {
            **base,
            "on_call": True, "call_duration_s": 2400, "battery_pct": 22,
            "intent_text": "bank officer threatened to block my account, pay immediately or face arrest, don't tell anyone",
            "intent_text_ta": "வங்கி அதிகாரி கணக்கு முடக்குவதாக பீதி படுத்தினார், உடனே பணம் அனுப்பாதது நிலைக்கு கைது வழக்கு, யாரிடமும் சொல்லாதே",
        },
    }


# --------------------------------------------------------------------------- #
#  Recipient intelligence (demo)
# --------------------------------------------------------------------------- #

PAYEE_INTEL: Dict[str, int] = {
    "kyc.safe.account@demo": 6,
    "cybercell.gov@demo": 9,
    "prize.lottery@demo": 5,
    "refund.desk@demo": 4,
    "quick.help@demo": 3,
    "new.number@ybl": 2,
}
