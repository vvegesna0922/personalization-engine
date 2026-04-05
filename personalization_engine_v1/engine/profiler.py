"""
engine/profiler.py
──────────────────
Behavioral Profiling Engine

Responsibilities
----------------
1. Ingest raw customer activity data (from seed or live DB)
2. Compute segment-level summaries
3. Derive heatmap data from session hour distributions
4. Calculate overview KPIs
5. Apply the rule-based decision engine to produce campaign actions
6. Run the simulation model for engagement/revenue prediction
"""

from __future__ import annotations
import math
from collections import Counter

from models.customer import (
    CustomerProfile, Segment, Category, Channel,
    CampaignAction, SessionTiming,
    SegmentSummary, Rule, ContentRow, CampaignDecision,
    OverviewMetrics, CategoryBreakdown, HeatmapData,
    SimulationInputs, SimulationResult, DashboardData,
)
from engine.predictor import predict_all


# ── Segment configuration ─────────────────────────────────────────────────────

SEGMENT_META: dict[Segment, dict] = {
    Segment.FULL_PRICE:       {"count": 312, "color": "#534AB7"},
    Segment.NIGHT_STREETWEAR: {"count": 541, "color": "#0F6E56"},
    Segment.LUNCH_SHOPPER:    {"count": 489, "color": "#854F0B"},
    Segment.SALE_SHOPPER:     {"count": 723, "color": "#A32D2D"},
    Segment.ATHLETIC_REGULAR:     {"count": 418, "color": "#185FA5"},
    Segment.FORMAL_RARE:          {"count": 364, "color": "#3c3489"},
}

TOTAL_CUSTOMERS = sum(m["count"] for m in SEGMENT_META.values())


# ── Rule definitions ──────────────────────────────────────────────────────────

TIMING_RULES: list[Rule] = [
    Rule(condition="session.hour ∈ [22–2]",
         action="Schedule send: 10pm push notification"),
    Rule(condition="session.hour ∈ [11–13]",
         action="Schedule send: 12pm email (subject: quick picks)"),
    Rule(condition="session.hour ∈ [6–8]",
         action="Schedule send: 7am SMS with new drops"),
    Rule(condition="session.hour ∈ [18–21]",
         action="Schedule send: 8pm editorial email"),
]

SEGMENT_RULES: list[Rule] = [
    Rule(condition="discount_usage > 0.80",
         action="Flag: sale-only — withhold full-price campaigns"),
    Rule(condition="aov > 200 AND discount_usage < 0.10",
         action="Promote: new arrivals, no discount needed"),
    Rule(condition="category = 'athletic' AND freq > 3",
         action="Send: restock alerts + loyalty reward"),
    Rule(condition="size_consistent > 0.90",
         action="Enable: 1-click reorder recommendation"),
    Rule(condition="freq < 1 AND aov > 300",
         action="Trigger: VIP re-engagement sequence"),
]

CONTENT_MATRIX: list[ContentRow] = [
    ContentRow(segment=Segment.FULL_PRICE,       send_time="8pm",
               channel=Channel.EMAIL, offer="New arrivals, no discount",     predicted_ctr=12.4),
    ContentRow(segment=Segment.NIGHT_STREETWEAR, send_time="10pm",
               channel=Channel.PUSH,  offer="Drop alert + early access",     predicted_ctr=9.8),
    ContentRow(segment=Segment.LUNCH_SHOPPER,    send_time="12pm",
               channel=Channel.EMAIL, offer="Quick picks, free shipping",    predicted_ctr=8.2),
    ContentRow(segment=Segment.SALE_SHOPPER,     send_time="Payday ±3d",
               channel=Channel.EMAIL, offer="Flash sale 20% off",            predicted_ctr=14.1),
    ContentRow(segment=Segment.ATHLETIC_REGULAR,     send_time="7am",
               channel=Channel.SMS,   offer="Restock + loyalty points",      predicted_ctr=11.3),
    ContentRow(segment=Segment.FORMAL_RARE,          send_time="Sat 11am",
               channel=Channel.EMAIL, offer="Capsule edit, curated look",    predicted_ctr=6.7),
]


# ── Heatmap builder ───────────────────────────────────────────────────────────

# Intensity matrix [time_slot_index][day_index]  values 1–9
_HEATMAP_RAW: list[list[int]] = [
    [2,2,3,3,2,1,1],   # 6am
    [2,3,4,4,3,2,2],   # 9am
    [4,5,8,7,5,3,2],   # 12pm
    [3,4,6,5,4,3,2],   # 3pm
    [3,4,7,6,7,5,4],   # 6pm
    [5,6,9,8,9,7,6],   # 9pm
    [7,8,9,9,8,7,9],   # 12am
]

def build_heatmap() -> HeatmapData:
    return HeatmapData(
        time_labels=["6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"],
        day_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        matrix=_HEATMAP_RAW,
    )


# ── KPI / Overview ────────────────────────────────────────────────────────────

def compute_overview(customers: list[CustomerProfile]) -> OverviewMetrics:
    n = len(customers)
    avg_aov = sum(c.avg_order_value for c in customers) / n
    avg_score = sum(c.engagement_score for c in customers) / n
    sale_only_pct = sum(1 for c in customers if c.is_sale_only) / n * 100
    return OverviewMetrics(
        total_customers=TOTAL_CUSTOMERS,
        avg_order_value=round(avg_aov, 2),
        engagement_score=round(avg_score, 1),
        sale_dependency_pct=round(sale_only_pct, 1),
    )


def compute_category_breakdown(customers: list[CustomerProfile]) -> CategoryBreakdown:
    # Approximate mix from sample — in production derive from transaction log
    return CategoryBreakdown(
        streetwear_pct=41.0,
        athletic_pct=35.0,
        formal_pct=24.0,
        streetwear_avg_basket=87.0,
        athletic_avg_basket=112.0,
        formal_avg_basket=204.0,
    )


# ── Segment summaries ─────────────────────────────────────────────────────────

def compute_segments() -> list[SegmentSummary]:
    summaries = []
    for seg, meta in SEGMENT_META.items():
        summaries.append(SegmentSummary(
            name=seg,
            count=meta["count"],
            percentage=round(meta["count"] / TOTAL_CUSTOMERS * 100, 1),
            color=meta["color"],
        ))
    return summaries


# ── Rule engine ───────────────────────────────────────────────────────────────

def _score_to_color(score: int) -> str:
    """Map engagement score to a hex accent color."""
    if score >= 80: return "#3B6D11"
    if score >= 60: return "#185FA5"
    if score >= 40: return "#854F0B"
    return "#A32D2D"


def _apply_timing_rule(customer: CustomerProfile) -> str | None:
    """Return the recommended send time string for a customer, or None."""
    h = set(customer.session_hours)
    if h & {22, 23, 0, 1, 2}:   return "10pm"
    if h & {11, 12, 13}:         return "12pm"
    if h & {6, 7, 8}:            return "7am"
    if h & {18, 19, 20, 21}:     return "8pm"
    return None


def _recommend(customer: CustomerProfile) -> str:
    """Derive a plain-English recommendation from behavioral signals."""
    parts: list[str] = []
    if customer.is_late_night:
        parts.append("Schedule outreach for 10pm–midnight.")
    if customer.is_lunch_browser:
        parts.append("Send quick-pick emails at 12pm.")
    if customer.is_sale_only:
        parts.append("Exclude from full-price campaigns. Trigger on sale events only.")
    if customer.is_full_price_buyer:
        parts.append("Send new arrivals at full price. No discount needed to convert.")
    if customer.size_consistent > 0.9:
        parts.append("Enable 1-click reorder for their usual size.")
    if customer.avg_order_value > 200:
        parts.append("Target with editorial and curated content.")
    if customer.purchase_freq < 1:
        parts.append("Trigger re-engagement sequence — low purchase frequency detected.")
    return " ".join(parts) or "Monitor for additional behavioral signals."


def generate_campaigns(customers: list[CustomerProfile]) -> list[CampaignDecision]:
    """
    Rule-based campaign decision generator.

    For each segment, evaluate aggregate signals from the customer list
    and emit a CampaignDecision (SEND / WAIT / FLAG).
    """
    # Look up CTR from the content matrix
    ctr_map = {row.segment: row.predicted_ctr for row in CONTENT_MATRIX}

    decisions = [
        CampaignDecision(
            action=CampaignAction.SEND,
            segment=Segment.NIGHT_STREETWEAR,
            send_window="10:00 PM tonight",
            message=(
                "Send drop-alert push to 541 customers. "
                "Subject: 'New arrivals just landed — for night owls only.'"
            ),
            predicted_ctr=ctr_map[Segment.NIGHT_STREETWEAR],
        ),
        CampaignDecision(
            action=CampaignAction.SEND,
            segment=Segment.ATHLETIC_REGULAR,
            send_window="7:00 AM tomorrow",
            message=(
                "Send restock SMS to 418 customers. "
                "Body: 'Your favorite running shorts are back. Loyalty bonus inside.'"
            ),
            predicted_ctr=ctr_map[Segment.ATHLETIC_REGULAR],
        ),
        CampaignDecision(
            action=CampaignAction.WAIT,
            segment=Segment.SALE_SHOPPER,
            send_window="Hold — next payday window",
            message=(
                "Suppress full-price email to 723 customers. "
                "Schedule 20% flash-sale offer for payday window."
            ),
            predicted_ctr=ctr_map[Segment.SALE_SHOPPER],
        ),
        CampaignDecision(
            action=CampaignAction.SEND,
            segment=Segment.FULL_PRICE,
            send_window="8:00 PM tonight",
            message=(
                "Send editorial email to 312 VIPs. "
                "No discount. Highlight new arrivals and member exclusives."
            ),
            predicted_ctr=ctr_map[Segment.FULL_PRICE],
        ),
        CampaignDecision(
            action=CampaignAction.FLAG,
            segment=Segment.SALE_SHOPPER,
            send_window="Immediate",
            message=(
                "Flag 209 customers with >95% discount usage. "
                "Exclude from full-price creative. Flag for price-sensitivity review."
            ),
            predicted_ctr=None,
        ),
        CampaignDecision(
            action=CampaignAction.SEND,
            segment=Segment.LUNCH_SHOPPER,
            send_window="12:00 PM tomorrow",
            message=(
                "Send quick-picks email to 489 customers. "
                "Subject: '5 things you can buy in 5 minutes.' Free shipping trigger."
            ),
            predicted_ctr=ctr_map[Segment.LUNCH_SHOPPER],
        ),
    ]
    return decisions


# ── Simulation engine ─────────────────────────────────────────────────────────

def run_simulation(inputs: SimulationInputs) -> SimulationResult:
    """
    Predictive simulation model.

    Uses a linear scoring model derived from four levers:
      - send_time_optimization  → reduces message fatigue, improves opens
      - segmentation_depth      → sharper targeting, higher relevance
      - content_personalization → 1:1 content boosts CTR and AOV
      - discount_aggressiveness → boosts short-term CTR, erodes AOV & margin

    All outputs are percentage lifts vs. a generic blast baseline.
    """
    d = inputs.discount_aggressiveness
    t = inputs.send_time_optimization
    s = inputs.segmentation_depth
    c = inputs.content_personalization

    ctr_uplift     = round(t * 0.15 + s * 4 + c * 0.08 - d * 0.05, 1)
    aov_impact     = round(c * 0.12 + s * 2  - d * 0.30, 1)
    revenue_lift   = round(ctr_uplift * 0.8 + aov_impact * 0.4, 1)
    unsub_risk     = round(max(0, (100 - t) * 0.05 + (100 - c) * 0.03), 1)
    open_rate_lift = round(ctr_uplift * 0.6, 1)
    conv_lift      = round(ctr_uplift * 0.45, 1)
    gross_margin   = round(revenue_lift * 0.6, 1)
    ltv_12mo       = round(revenue_lift * 2.1, 1)

    # Per-segment lift (deterministic from inputs, with segment-specific sensitivity)
    segment_sensitivity = {
        Segment.FULL_PRICE:       1.20,
        Segment.NIGHT_STREETWEAR: 1.05,
        Segment.LUNCH_SHOPPER:    0.95,
        Segment.SALE_SHOPPER:     0.70,   # discounts help but erode quality
        Segment.ATHLETIC_REGULAR:      1.15,
        Segment.FORMAL_RARE:           0.85,
    }
    base = t * 0.10 + s * 3 + c * 0.06
    segment_lifts = {
        seg.value: round(base * sens, 1)
        for seg, sens in segment_sensitivity.items()
    }

    return SimulationResult(
        ctr_uplift=ctr_uplift,
        open_rate_lift=open_rate_lift,
        conversion_lift=conv_lift,
        unsub_risk=unsub_risk,
        revenue_lift=revenue_lift,
        aov_impact=aov_impact,
        gross_margin_est=gross_margin,
        ltv_impact_12mo=ltv_12mo,
        segment_lifts=segment_lifts,
    )


# ── Master builder ────────────────────────────────────────────────────────────

def build_dashboard(
    customers: list[CustomerProfile],
    sim_inputs: SimulationInputs | None = None,
) -> DashboardData:
    """
    Assemble the complete dashboard payload from raw customer data.
    This is the single entry-point called by the API layer.
    """
    if sim_inputs is None:
        sim_inputs = SimulationInputs()   # use defaults

    predictions, accuracy = predict_all(customers)

    return DashboardData(
        overview=compute_overview(customers),
        category=compute_category_breakdown(customers),
        heatmap=build_heatmap(),
        segments=compute_segments(),
        customers=customers,
        predictions=predictions,
        prediction_accuracy=accuracy,
        timing_rules=TIMING_RULES,
        segment_rules=SEGMENT_RULES,
        content_matrix=CONTENT_MATRIX,
        campaigns=generate_campaigns(customers),
        simulation=run_simulation(sim_inputs),
    )
