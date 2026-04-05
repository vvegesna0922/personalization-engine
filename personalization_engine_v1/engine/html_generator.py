"""
engine/html_generator.py
────────────────────────
Converts a DashboardData payload into a fully self-contained HTML file.
Renders via Jinja2 so template logic stays separate from Python code.
"""

from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models.customer import DashboardData, CampaignAction, CustomerProfile
from engine.profiler import _recommend

# Resolve the templates directory relative to this file
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)

# ── Custom Jinja2 filters ─────────────────────────────────────────────────────

def _badge_class(action: CampaignAction) -> str:
    return {
        CampaignAction.SEND: "badge-green",
        CampaignAction.WAIT: "badge-amber",
        CampaignAction.FLAG: "badge-red",
    }[action]

def _score_color(score: int) -> str:
    if score >= 80: return "#3B6D11"
    if score >= 60: return "#185FA5"
    if score >= 40: return "#854F0B"
    return "#A32D2D"

def _fmt_hours(hours: list[int]) -> str:
    return ", ".join(f"{h}:00" for h in hours)

_env.filters["badge_class"]  = _badge_class
_env.filters["score_color"]  = _score_color
_env.filters["fmt_hours"]    = _fmt_hours


# ── Public API ────────────────────────────────────────────────────────────────

def render_dashboard(data: DashboardData, output_path: Path | None = None) -> str:
    """
    Render the dashboard HTML from *data*.

    If *output_path* is given the HTML is also written to that file.
    Always returns the HTML string.
    """
    template = _env.get_template("dashboard.html")

    # Build heatmap opacity lookup for template use
    heatmap_opacities: list[list[float]] = []
    for row in data.heatmap.matrix:
        heatmap_opacities.append([round(v / 9 * 0.8 + 0.05, 3) for v in row])

    # Build a dict keyed by customer_id for easy template lookup
    predictions = {p.customer_id: p for p in data.predictions}

    html = template.render(
        overview=data.overview,
        category=data.category,
        heatmap=data.heatmap,
        heatmap_opacities=heatmap_opacities,
        segments=data.segments,
        customers=data.customers,
        predictions=predictions,
        prediction_accuracy=data.prediction_accuracy,
        timing_rules=data.timing_rules,
        segment_rules=data.segment_rules,
        content_matrix=data.content_matrix,
        campaigns=data.campaigns,
        CampaignAction=CampaignAction,
        recommend=_recommend,
        enumerate=enumerate,
    )

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

    return html
