"""
models/customer.py
──────────────────
Data models for the Behavioral Personalization Engine.

Uses Python stdlib dataclasses only — zero third-party dependencies
for the core engine. The FastAPI layer (api/app.py) adds Pydantic on
top for HTTP validation; the rest of the system never needs it.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json


# ── Enumerations ─────────────────────────────────────────────────────────────

class SessionTiming(str, Enum):
    MORNING    = "morning"       # 06:00 – 09:00
    LUNCH      = "lunch"         # 11:00 – 13:00
    AFTERNOON  = "afternoon"     # 13:00 – 17:00
    EVENING    = "evening"       # 18:00 – 21:00
    LATE_NIGHT = "late_night"    # 22:00 – 02:00
    VARIED     = "varied"        # no dominant window
    WEEKEND    = "weekend"       # activity clusters on Sat/Sun


class Category(str, Enum):
    STREETWEAR = "streetwear"
    FORMAL     = "formal"
    ATHLETIC   = "athletic"


class Segment(str, Enum):
    FULL_PRICE       = "Full-Price"
    NIGHT_STREETWEAR = "Night Streetwear"
    LUNCH_SHOPPER    = "Lunch Shopper"
    SALE_SHOPPER     = "Sale Shopper"
    ATHLETIC_REGULAR = "Athletic Regular"
    FORMAL_RARE      = "Formal Rare"


class Channel(str, Enum):
    EMAIL = "Email"
    PUSH  = "Push"
    SMS   = "SMS"


class CampaignAction(str, Enum):
    SEND = "send"
    WAIT = "wait"
    FLAG = "flag"


# ── Serialisation helper ──────────────────────────────────────────────────────

class _Serialisable:
    """Mixin that adds .to_dict() and .to_json() to any dataclass."""
    def to_dict(self) -> dict:
        def _conv(v):
            if isinstance(v, Enum):          return v.value
            if isinstance(v, _Serialisable): return v.to_dict()
            if isinstance(v, list):          return [_conv(i) for i in v]
            if isinstance(v, dict):          return {k: _conv(val) for k, val in v.items()}
            return v
        import dataclasses as _dc
        return {f.name: _conv(getattr(self, f.name)) for f in _dc.fields(self)}  # type: ignore

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), **kwargs)


# ── Core customer profile ─────────────────────────────────────────────────────

@dataclass
class CustomerProfile(_Serialisable):
    """
    A single customer's behavioral fingerprint.
    All fields come from activity data ingestion; derived properties
    are computed on demand.
    """
    id:               int
    name:             str
    initials:         str
    color:            str                   # hex, for avatar display
    segment:          Segment
    timing:           SessionTiming
    session_hours:    list[int]             # hours of day (0-23) most active
    purchase_freq:    float                 # average purchases per month
    avg_order_value:  float
    categories:       list[Category]
    size_consistent:  float                 # 0 = never same size, 1 = always
    discount_usage:   float                 # fraction of orders using a discount
    engagement_score: int                   # 0 – 100

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_late_night(self) -> bool:
        return self.timing == SessionTiming.LATE_NIGHT

    @property
    def is_lunch_browser(self) -> bool:
        return self.timing == SessionTiming.LUNCH

    @property
    def is_sale_only(self) -> bool:
        return self.discount_usage > 0.70

    @property
    def is_full_price_buyer(self) -> bool:
        return self.discount_usage < 0.15

    @property
    def discount_label(self) -> str:
        if self.discount_usage > 0.70: return "Sale-only buyer"
        if self.discount_usage < 0.15: return "Full-price buyer"
        return "Mixed"

    def to_dict(self) -> dict:
        d = super().to_dict()
        # Append computed properties so templates can access them directly
        d["is_late_night"]      = self.is_late_night
        d["is_lunch_browser"]   = self.is_lunch_browser
        d["is_sale_only"]       = self.is_sale_only
        d["is_full_price_buyer"]= self.is_full_price_buyer
        d["discount_label"]     = self.discount_label
        return d


# ── Aggregated segment stats ──────────────────────────────────────────────────

@dataclass
class SegmentSummary(_Serialisable):
    name:       Segment
    count:      int
    percentage: float
    color:      str


# ── Rule engine types ─────────────────────────────────────────────────────────

@dataclass
class Rule(_Serialisable):
    condition: str    # human-readable condition expression
    action:    str    # human-readable action description


@dataclass
class ContentRow(_Serialisable):
    segment:       Segment
    send_time:     str
    channel:       Channel
    offer:         str
    predicted_ctr: float    # percent, e.g. 12.4


# ── Segment prediction ───────────────────────────────────────────────────────

@dataclass
class CustomerPrediction(_Serialisable):
    """
    Output of the rule-based segment classifier for one customer.
    predicted_segment may differ from the customer's assigned segment,
    indicating their behavior has drifted or they were mis-labelled.
    """
    customer_id:       int
    predicted_segment: Segment
    confidence:        int            # 0–100: how clearly they match the segment
    matches_actual:    bool           # predicted == customer.segment
    best_channel:      Channel
    best_send_time:    str
    offer:             str
    action:            str            # full recommended marketing action
    rationale:         str            # which signals drove the prediction
    all_scores:        dict           # {segment_value: score} for transparency


# ── Campaign decision ─────────────────────────────────────────────────────────

@dataclass
class CampaignDecision(_Serialisable):
    action:        CampaignAction
    segment:       Segment
    send_window:   str
    message:       str
    predicted_ctr: Optional[float] = None
    rationale:     Optional[str]   = None   # populated by LLM layer; None for rule-based decisions


# ── Overview / KPI ────────────────────────────────────────────────────────────

@dataclass
class OverviewMetrics(_Serialisable):
    total_customers:     int
    avg_order_value:     float
    engagement_score:    float
    sale_dependency_pct: float    # percent of customers who only buy on sale


@dataclass
class CategoryBreakdown(_Serialisable):
    streetwear_pct:        float
    athletic_pct:          float
    formal_pct:            float
    streetwear_avg_basket: float
    athletic_avg_basket:   float
    formal_avg_basket:     float


@dataclass
class HeatmapData(_Serialisable):
    """
    Session activity matrix.
      rows   = time slots  (6am, 9am, 12pm, 3pm, 6pm, 9pm, 12am)
      cols   = days of week (Mon – Sun)
      values = relative activity intensity 1 – 9
    """
    time_labels: list[str]
    day_labels:  list[str]
    matrix:      list[list[int]]    # [time_slot_index][day_index]


# ── Simulation ────────────────────────────────────────────────────────────────

@dataclass
class SimulationInputs(_Serialisable):
    discount_aggressiveness: float = 30.0
    send_time_optimization:  float = 60.0
    segmentation_depth:      int   = 4
    content_personalization: float = 75.0


@dataclass
class SimulationResult(_Serialisable):
    ctr_uplift:       float
    open_rate_lift:   float
    conversion_lift:  float
    unsub_risk:       float
    revenue_lift:     float
    aov_impact:       float
    gross_margin_est: float
    ltv_impact_12mo:  float
    segment_lifts:    dict   # segment name (str) → predicted lift (float)


# ── Full dashboard payload ────────────────────────────────────────────────────

@dataclass
class DashboardData(_Serialisable):
    overview:             OverviewMetrics
    category:             CategoryBreakdown
    heatmap:              HeatmapData
    segments:             list[SegmentSummary]
    customers:            list[CustomerProfile]
    predictions:          list[CustomerPrediction]
    prediction_accuracy:  float                    # % where predicted == assigned segment
    timing_rules:         list[Rule]
    segment_rules:        list[Rule]
    content_matrix:       list[ContentRow]
    campaigns:      list[CampaignDecision]
    simulation:     SimulationResult
