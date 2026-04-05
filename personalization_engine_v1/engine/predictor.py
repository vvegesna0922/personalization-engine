"""
engine/predictor.py
───────────────────
Rule-based segment classifier and marketing strategy recommender.

For each customer, scores them against all 6 segment behavioral profiles
using raw signals (AOV, discount usage, timing, purchase frequency, categories).
Returns the best-fit segment, a 0–100 confidence score, and a recommended
marketing strategy with rationale.

No external APIs — pure deterministic scoring.
"""

from __future__ import annotations
from models.customer import (
    CustomerProfile, CustomerPrediction,
    Segment, Channel, SessionTiming, Category,
)


# ── Recommended strategy per segment ─────────────────────────────────────────

_STRATEGY: dict[Segment, dict] = {
    Segment.FULL_PRICE: {
        "channel":   Channel.EMAIL,
        "send_time": "8pm",
        "offer":     "New arrivals, no discount",
        "action":    "Send an 8pm editorial email featuring new full-price arrivals. "
                     "No discount required — this customer converts at full price.",
    },
    Segment.NIGHT_STREETWEAR: {
        "channel":   Channel.PUSH,
        "send_time": "10pm",
        "offer":     "Drop alert + early access",
        "action":    "Send a 10pm push notification with a new drop alert. "
                     "Use scarcity language and early-access framing.",
    },
    Segment.LUNCH_SHOPPER: {
        "channel":   Channel.EMAIL,
        "send_time": "12pm",
        "offer":     "Quick picks, free shipping",
        "action":    "Send a 12pm email with 5 curated quick-pick items and a free "
                     "shipping trigger. Keep copy short and scannable.",
    },
    Segment.SALE_SHOPPER: {
        "channel":   Channel.EMAIL,
        "send_time": "Payday ±3 days",
        "offer":     "Flash sale 20% off",
        "action":    "Hold all campaigns until the payday window. Send a 20% flash "
                     "sale email with scarcity messaging. Full-price campaigns will be ignored.",
    },
    Segment.ATHLETIC_REGULAR: {
        "channel":   Channel.SMS,
        "send_time": "7am",
        "offer":     "Restock + loyalty points",
        "action":    "Send a 7am SMS with restock alerts for athletic gear plus a loyalty "
                     "points bonus. This customer responds to early-morning outreach.",
    },
    Segment.FORMAL_RARE: {
        "channel":   Channel.EMAIL,
        "send_time": "Saturday 11am",
        "offer":     "Capsule edit, curated look",
        "action":    "Send a Saturday 11am editorial email with a curated capsule look. "
                     "Focus on quality and exclusivity, not price.",
    },
}


# ── Segment scoring functions ─────────────────────────────────────────────────
# Each returns a float 0–100: how well the customer matches that segment.

def _score_full_price(c: CustomerProfile) -> float:
    s = 0.0
    # AOV: primary signal
    if   c.avg_order_value > 250: s += 35
    elif c.avg_order_value > 175: s += 22
    elif c.avg_order_value > 120: s += 10
    # Low discount: defining signal
    if   c.discount_usage < 0.08: s += 35
    elif c.discount_usage < 0.15: s += 22
    elif c.discount_usage < 0.25: s +=  8
    # Evening browsing
    if c.timing == SessionTiming.EVENING: s += 15
    # Engagement
    if   c.engagement_score > 85: s += 10
    elif c.engagement_score > 70: s +=  5
    # Formal category (small boost)
    if Category.FORMAL in c.categories: s += 5
    return min(s, 100.0)


def _score_night_streetwear(c: CustomerProfile) -> float:
    s = 0.0
    # Late-night: primary signal
    if c.timing == SessionTiming.LATE_NIGHT: s += 40
    # Streetwear category: co-primary
    if Category.STREETWEAR in c.categories: s += 25
    # Moderate discount (not sale-hunter, not full-price)
    if 0.05 <= c.discount_usage <= 0.45:    s += 20
    # Not premium AOV
    if c.avg_order_value < 130:             s += 10
    # Regular-ish frequency
    if c.purchase_freq > 1.5:              s +=  5
    return min(s, 100.0)


def _score_lunch_shopper(c: CustomerProfile) -> float:
    s = 0.0
    if c.timing == SessionTiming.LUNCH:         s += 45
    if 0.25 <= c.discount_usage <= 0.60:       s += 25
    if 40 <= c.avg_order_value <= 120:         s += 20
    if c.purchase_freq > 2.0:                 s += 10
    return min(s, 100.0)


def _score_sale_shopper(c: CustomerProfile) -> float:
    s = 0.0
    # Discount: overwhelmingly primary
    if   c.discount_usage > 0.80: s += 55
    elif c.discount_usage > 0.65: s += 30
    elif c.discount_usage > 0.50: s += 15
    # Low AOV
    if   c.avg_order_value < 60: s += 25
    elif c.avg_order_value < 80: s += 10
    # Low frequency (only purchases on sale)
    if c.purchase_freq < 2.0: s += 15
    # Varied timing
    if c.timing == SessionTiming.VARIED: s += 5
    return min(s, 100.0)


def _score_athletic_regular(c: CustomerProfile) -> float:
    s = 0.0
    if c.timing == SessionTiming.MORNING:       s += 35
    if Category.ATHLETIC in c.categories:      s += 30
    if   c.purchase_freq > 3.5:               s += 20
    elif c.purchase_freq > 2.5:               s += 10
    if c.discount_usage < 0.35:               s += 10
    if c.size_consistent > 0.90:              s +=  5
    return min(s, 100.0)


def _score_formal_rare(c: CustomerProfile) -> float:
    s = 0.0
    # Premium AOV: primary
    if   c.avg_order_value > 350: s += 35
    elif c.avg_order_value > 250: s += 20
    elif c.avg_order_value > 180: s +=  8
    # Very low discount
    if   c.discount_usage < 0.06: s += 25
    elif c.discount_usage < 0.12: s += 12
    # Rare purchasing
    if   c.purchase_freq < 0.9: s += 25
    elif c.purchase_freq < 1.5: s += 12
    # Formal category
    if Category.FORMAL in c.categories:  s += 10
    if c.timing == SessionTiming.WEEKEND: s +=  5
    return min(s, 100.0)


_SCORERS = {
    Segment.FULL_PRICE:       _score_full_price,
    Segment.NIGHT_STREETWEAR: _score_night_streetwear,
    Segment.LUNCH_SHOPPER:    _score_lunch_shopper,
    Segment.SALE_SHOPPER:     _score_sale_shopper,
    Segment.ATHLETIC_REGULAR: _score_athletic_regular,
    Segment.FORMAL_RARE:      _score_formal_rare,
}


# ── Rationale builder ─────────────────────────────────────────────────────────

def _build_rationale(c: CustomerProfile, seg: Segment) -> str:
    parts: list[str] = []

    if seg == Segment.FULL_PRICE:
        if c.avg_order_value > 175:
            parts.append(f"high AOV (${c.avg_order_value:.0f})")
        if c.discount_usage < 0.15:
            parts.append(f"low discount usage ({c.discount_usage*100:.0f}%)")
        if c.timing == SessionTiming.EVENING:
            parts.append("evening browsing pattern")

    elif seg == Segment.NIGHT_STREETWEAR:
        if c.timing == SessionTiming.LATE_NIGHT:
            parts.append("late-night activity window")
        if Category.STREETWEAR in c.categories:
            parts.append("streetwear preference")
        parts.append(f"moderate discount usage ({c.discount_usage*100:.0f}%)")

    elif seg == Segment.LUNCH_SHOPPER:
        parts.append("midday session pattern")
        if c.discount_usage > 0.25:
            parts.append(f"discount-driven ({c.discount_usage*100:.0f}%)")
        parts.append(f"moderate basket size (${c.avg_order_value:.0f})")

    elif seg == Segment.SALE_SHOPPER:
        parts.append(f"high discount dependency ({c.discount_usage*100:.0f}%)")
        if c.avg_order_value < 65:
            parts.append(f"low AOV (${c.avg_order_value:.0f})")
        if c.purchase_freq < 2:
            parts.append("infrequent purchases outside sale events")

    elif seg == Segment.ATHLETIC_REGULAR:
        if c.timing == SessionTiming.MORNING:
            parts.append("morning session window")
        if Category.ATHLETIC in c.categories:
            parts.append("athletic category focus")
        if c.purchase_freq > 3:
            parts.append(f"high purchase frequency ({c.purchase_freq:.1f}×/mo)")

    elif seg == Segment.FORMAL_RARE:
        parts.append(f"premium AOV (${c.avg_order_value:.0f})")
        if c.discount_usage < 0.10:
            parts.append("full-price buying pattern")
        if c.purchase_freq < 1.2:
            parts.append("infrequent purchasing")

    return "Signals: " + ", ".join(parts) + "." if parts else "Based on overall behavioral signals."


# ── Public API ────────────────────────────────────────────────────────────────

def predict_customer(c: CustomerProfile) -> CustomerPrediction:
    """Score a customer against all 6 segments and return the best-fit prediction."""
    scores = {seg: fn(c) for seg, fn in _SCORERS.items()}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    best_seg,    best_score  = ranked[0]
    second_seg,  second_score = ranked[1]

    gap        = best_score - second_score
    confidence = int(min(100, best_score * 0.6 + gap * 0.8))

    strat = _STRATEGY[best_seg]

    return CustomerPrediction(
        customer_id       = c.id,
        predicted_segment = best_seg,
        confidence        = confidence,
        matches_actual    = (best_seg == c.segment),
        best_channel      = strat["channel"],
        best_send_time    = strat["send_time"],
        offer             = strat["offer"],
        action            = strat["action"],
        rationale         = _build_rationale(c, best_seg),
        all_scores        = {seg.value: round(score, 1) for seg, score in scores.items()},
    )


def predict_all(customers: list[CustomerProfile]) -> tuple[list[CustomerPrediction], float]:
    """
    Run predictions for every customer.
    Returns (predictions, accuracy_pct) where accuracy is the % whose
    predicted segment matches their assigned segment.
    """
    predictions = [predict_customer(c) for c in customers]
    if not predictions:
        return predictions, 0.0
    matches = sum(1 for p in predictions if p.matches_actual)
    accuracy = round(matches / len(predictions) * 100, 1)
    return predictions, accuracy
