"""
data/seed.py
────────────
Sample customer activity records.
In production, swap this module for a database query or
a CSV/JSON ingestion pipeline that populates the same structure.

Each dict maps directly onto CustomerProfile fields.
40 customers across all 6 segments for richer model testing.
"""

from models.customer import (
    CustomerProfile, SessionTiming, Category, Segment
)

RAW_CUSTOMERS: list[dict] = [

    # ── Full-Price (6) ───────────────────────────────────────────────────────
    dict(id=1,  name="Marcus Reid",        initials="MR", color="#534AB7",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[18,19,20,21], purchase_freq=4.2, avg_order_value=247,
         categories=[Category.FORMAL, Category.STREETWEAR],
         size_consistent=0.95, discount_usage=0.04, engagement_score=94),

    dict(id=2,  name="Priya Sharma",       initials="PS", color="#6B5FD0",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[19,20,21],   purchase_freq=5.1, avg_order_value=312,
         categories=[Category.FORMAL, Category.ATHLETIC],
         size_consistent=0.93, discount_usage=0.06, engagement_score=97),

    dict(id=3,  name="Elena Vasquez",      initials="EV", color="#7B6BE0",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[18,19,20],   purchase_freq=3.8, avg_order_value=289,
         categories=[Category.FORMAL],
         size_consistent=0.92, discount_usage=0.08, engagement_score=88),

    dict(id=4,  name="James Chen",         initials="JC", color="#4A40A5",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[19,20,21],   purchase_freq=3.4, avg_order_value=198,
         categories=[Category.STREETWEAR, Category.FORMAL],
         size_consistent=0.88, discount_usage=0.11, engagement_score=79),

    dict(id=5,  name="Sophia Andersen",    initials="SA", color="#3D3598",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[18,20,21],   purchase_freq=4.6, avg_order_value=340,
         categories=[Category.ATHLETIC, Category.FORMAL],
         size_consistent=0.97, discount_usage=0.03, engagement_score=92),

    dict(id=6,  name="Kwame Asante",       initials="KA", color="#8070E8",
         segment=Segment.FULL_PRICE,       timing=SessionTiming.EVENING,
         session_hours=[18,19,20],   purchase_freq=3.9, avg_order_value=215,
         categories=[Category.FORMAL],
         size_consistent=0.90, discount_usage=0.09, engagement_score=85),

    # ── Night Streetwear (7) ─────────────────────────────────────────────────
    dict(id=7,  name="Zoe Kim",            initials="ZK", color="#0F6E56",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[22,23,0,1],  purchase_freq=2.8, avg_order_value=89,
         categories=[Category.STREETWEAR],
         size_consistent=0.88, discount_usage=0.12, engagement_score=72),

    dict(id=8,  name="Dev Okafor",         initials="DO", color="#157A60",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[23,0,1,2],   purchase_freq=2.1, avg_order_value=76,
         categories=[Category.STREETWEAR],
         size_consistent=0.84, discount_usage=0.28, engagement_score=55),

    dict(id=9,  name="Riya Menon",         initials="RM", color="#1A8670",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[22,23,0],    purchase_freq=2.4, avg_order_value=94,
         categories=[Category.STREETWEAR],
         size_consistent=0.86, discount_usage=0.15, engagement_score=68),

    dict(id=10, name="Caleb Torres",       initials="CT", color="#0C5E4A",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[23,0,1],     purchase_freq=3.0, avg_order_value=112,
         categories=[Category.STREETWEAR],
         size_consistent=0.82, discount_usage=0.20, engagement_score=74),

    dict(id=11, name="Nia Johnson",        initials="NJ", color="#0A5040",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[22,23,1],    purchase_freq=1.8, avg_order_value=67,
         categories=[Category.STREETWEAR],
         size_consistent=0.79, discount_usage=0.35, engagement_score=49),

    dict(id=12, name="Dmitri Volkov",      initials="DV", color="#1E9070",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[0,1,2],      purchase_freq=2.3, avg_order_value=83,
         categories=[Category.STREETWEAR],
         size_consistent=0.85, discount_usage=0.18, engagement_score=63),

    dict(id=13, name="Amara Diallo",       initials="AD", color="#127A60",
         segment=Segment.NIGHT_STREETWEAR, timing=SessionTiming.LATE_NIGHT,
         session_hours=[22,23,0],    purchase_freq=2.7, avg_order_value=101,
         categories=[Category.STREETWEAR, Category.ATHLETIC],
         size_consistent=0.91, discount_usage=0.09, engagement_score=77),

    # ── Lunch Shopper (7) ────────────────────────────────────────────────────
    dict(id=14, name="Tyler Brooks",       initials="TB", color="#854F0B",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[12,13],      purchase_freq=3.1, avg_order_value=67,
         categories=[Category.ATHLETIC, Category.STREETWEAR],
         size_consistent=0.91, discount_usage=0.38, engagement_score=61),

    dict(id=15, name="Nadia Vogt",         initials="NV", color="#9A5C0D",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[11,12,13],   purchase_freq=2.9, avg_order_value=92,
         categories=[Category.ATHLETIC],
         size_consistent=0.89, discount_usage=0.45, engagement_score=58),

    dict(id=16, name="Felix Wagner",       initials="FW", color="#7A470A",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[12,13],      purchase_freq=2.6, avg_order_value=78,
         categories=[Category.STREETWEAR],
         size_consistent=0.83, discount_usage=0.42, engagement_score=55),

    dict(id=17, name="Ingrid Park",        initials="IP", color="#B06A0F",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[11,12],      purchase_freq=2.2, avg_order_value=54,
         categories=[Category.ATHLETIC],
         size_consistent=0.78, discount_usage=0.52, engagement_score=47),

    dict(id=18, name="Omar Hassan",        initials="OH", color="#6B3D08",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[12,13,14],   purchase_freq=3.4, avg_order_value=103,
         categories=[Category.STREETWEAR, Category.ATHLETIC],
         size_consistent=0.87, discount_usage=0.29, engagement_score=66),

    dict(id=19, name="Lena Müller",        initials="LM", color="#C07510",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[11,12],      purchase_freq=2.4, avg_order_value=61,
         categories=[Category.ATHLETIC],
         size_consistent=0.81, discount_usage=0.48, engagement_score=52),

    dict(id=20, name="Tariq Abubakar",     initials="TA", color="#9E5F0C",
         segment=Segment.LUNCH_SHOPPER,    timing=SessionTiming.LUNCH,
         session_hours=[12,13],      purchase_freq=3.2, avg_order_value=88,
         categories=[Category.STREETWEAR],
         size_consistent=0.86, discount_usage=0.33, engagement_score=71),

    # ── Sale Shopper (9) ─────────────────────────────────────────────────────
    dict(id=21, name="Aisha Patel",        initials="AP", color="#A32D2D",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.VARIED,
         session_hours=[10,14,20],   purchase_freq=1.4, avg_order_value=44,
         categories=[Category.STREETWEAR, Category.FORMAL],
         size_consistent=0.72, discount_usage=0.94, engagement_score=38),

    dict(id=22, name="Miles Cruz",         initials="MC", color="#B83535",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.EVENING,
         session_hours=[18,19,20],   purchase_freq=1.1, avg_order_value=31,
         categories=[Category.STREETWEAR, Category.ATHLETIC],
         size_consistent=0.63, discount_usage=0.97, engagement_score=22),

    dict(id=23, name="Kenji Yamamoto",     initials="KY", color="#8F2727",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.VARIED,
         session_hours=[10,15,20],   purchase_freq=1.2, avg_order_value=38,
         categories=[Category.STREETWEAR],
         size_consistent=0.68, discount_usage=0.88, engagement_score=31),

    dict(id=24, name="Fatima Al-Rashid",   initials="FA", color="#C43C3C",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.EVENING,
         session_hours=[17,18,19],   purchase_freq=1.6, avg_order_value=52,
         categories=[Category.FORMAL, Category.STREETWEAR],
         size_consistent=0.75, discount_usage=0.91, engagement_score=41),

    dict(id=25, name="Brendan Murphy",     initials="BM", color="#7A2020",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.VARIED,
         session_hours=[9,14,21],    purchase_freq=0.9, avg_order_value=29,
         categories=[Category.ATHLETIC],
         size_consistent=0.61, discount_usage=0.96, engagement_score=18),

    dict(id=26, name="Yuki Tanaka",        initials="YT", color="#D04040",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.AFTERNOON,
         session_hours=[13,14,15],   purchase_freq=1.5, avg_order_value=47,
         categories=[Category.STREETWEAR],
         size_consistent=0.70, discount_usage=0.85, engagement_score=44),

    dict(id=27, name="Chidi Okonkwo",      initials="CO", color="#952A2A",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.EVENING,
         session_hours=[18,19],      purchase_freq=1.0, avg_order_value=35,
         categories=[Category.ATHLETIC, Category.STREETWEAR],
         size_consistent=0.65, discount_usage=0.93, engagement_score=27),

    dict(id=28, name="Rosa Gutierrez",     initials="RG", color="#BF3030",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.VARIED,
         session_hours=[11,16,20],   purchase_freq=1.3, avg_order_value=41,
         categories=[Category.STREETWEAR],
         size_consistent=0.69, discount_usage=0.89, engagement_score=35),

    dict(id=29, name="Hamid Rahimi",       initials="HR", color="#882525",
         segment=Segment.SALE_SHOPPER,     timing=SessionTiming.LUNCH,
         session_hours=[12,13],      purchase_freq=1.7, avg_order_value=58,
         categories=[Category.FORMAL],
         size_consistent=0.74, discount_usage=0.82, engagement_score=48),

    # ── Athletic Regular (6) ─────────────────────────────────────────────────
    dict(id=30, name="Jordan Ngo",         initials="JN", color="#185FA5",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[6,7,8],      purchase_freq=3.8, avg_order_value=128,
         categories=[Category.ATHLETIC],
         size_consistent=0.97, discount_usage=0.22, engagement_score=81),

    dict(id=31, name="Serena Banks",       initials="SB", color="#1A6BB8",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[5,6,7],      purchase_freq=4.3, avg_order_value=142,
         categories=[Category.ATHLETIC],
         size_consistent=0.96, discount_usage=0.18, engagement_score=87),

    dict(id=32, name="Tobias Klein",       initials="TK", color="#1558A0",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[6,7,8],      purchase_freq=3.5, avg_order_value=119,
         categories=[Category.ATHLETIC],
         size_consistent=0.94, discount_usage=0.25, engagement_score=76),

    dict(id=33, name="Alicia Moreno",      initials="AM", color="#1D75C0",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[5,6,7],      purchase_freq=4.7, avg_order_value=156,
         categories=[Category.ATHLETIC],
         size_consistent=0.98, discount_usage=0.14, engagement_score=91),

    dict(id=34, name="Patrick O'Brien",    initials="PO", color="#134E90",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[6,7,8,9],    purchase_freq=3.2, avg_order_value=108,
         categories=[Category.ATHLETIC, Category.STREETWEAR],
         size_consistent=0.92, discount_usage=0.30, engagement_score=69),

    dict(id=35, name="Mei-Ling Zhou",      initials="MZ", color="#2070BC",
         segment=Segment.ATHLETIC_REGULAR, timing=SessionTiming.MORNING,
         session_hours=[6,7,8],      purchase_freq=4.0, avg_order_value=134,
         categories=[Category.ATHLETIC],
         size_consistent=0.95, discount_usage=0.19, engagement_score=83),

    # ── Formal Rare (5) ──────────────────────────────────────────────────────
    dict(id=36, name="Sara Lin",           initials="SL", color="#3c3489",
         segment=Segment.FORMAL_RARE,      timing=SessionTiming.WEEKEND,
         session_hours=[10,11,14,15],purchase_freq=0.7, avg_order_value=410,
         categories=[Category.FORMAL],
         size_consistent=0.99, discount_usage=0.02, engagement_score=48),

    dict(id=37, name="Bartholomew Hughes", initials="BH", color="#4A4295",
         segment=Segment.FORMAL_RARE,      timing=SessionTiming.WEEKEND,
         session_hours=[10,11,14],   purchase_freq=0.5, avg_order_value=520,
         categories=[Category.FORMAL],
         size_consistent=0.99, discount_usage=0.01, engagement_score=52),

    dict(id=38, name="Anastasia Petrova",  initials="AP", color="#302A7A",
         segment=Segment.FORMAL_RARE,      timing=SessionTiming.WEEKEND,
         session_hours=[11,12,15],   purchase_freq=0.6, avg_order_value=380,
         categories=[Category.FORMAL],
         size_consistent=0.98, discount_usage=0.05, engagement_score=44),

    dict(id=39, name="Wellington Osei",    initials="WO", color="#524FA0",
         segment=Segment.FORMAL_RARE,      timing=SessionTiming.WEEKEND,
         session_hours=[10,11,14],   purchase_freq=0.8, avg_order_value=445,
         categories=[Category.FORMAL],
         size_consistent=0.97, discount_usage=0.03, engagement_score=58),

    dict(id=40, name="Claudia Reinholt",   initials="CR", color="#2A2570",
         segment=Segment.FORMAL_RARE,      timing=SessionTiming.WEEKEND,
         session_hours=[11,14,15],   purchase_freq=0.6, avg_order_value=490,
         categories=[Category.FORMAL],
         size_consistent=0.98, discount_usage=0.04, engagement_score=46),
]

# Pre-parsed list of CustomerProfile objects used throughout the engine
CUSTOMERS: list[CustomerProfile] = [CustomerProfile(**r) for r in RAW_CUSTOMERS]
