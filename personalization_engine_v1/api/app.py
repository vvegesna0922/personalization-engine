"""
api/app.py
──────────
FastAPI application — the HTTP layer of the Behavioral Personalization Engine.

Endpoints
─────────
GET  /                     → Redirect to /dashboard
GET  /dashboard            → Render and return the full HTML dashboard
GET  /api/overview         → KPI metrics JSON
GET  /api/customers        → Full customer list (filterable, sortable)
GET  /api/customers/{id}   → Single customer profile
GET  /api/segments         → Segment summaries
GET  /api/campaigns        → Today's campaign decisions
GET  /api/rules            → All timing + segment rules
GET  /api/heatmap          → Session timing heatmap matrix
POST /api/simulate         → Run simulation with custom inputs
GET  /api/export           → Generate & download the HTML dashboard file
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticBase, Field

from data.db import CUSTOMERS
from engine.profiler import build_dashboard, run_simulation
from engine.html_generator import render_dashboard
from models.customer import SimulationInputs


# ── Pydantic I/O schemas ──────────────────────────────────────────────────────

class SimulationRequest(PydanticBase):
    discount_aggressiveness: float = Field(30, ge=0,  le=100)
    send_time_optimization:  float = Field(60, ge=0,  le=100)
    segmentation_depth:      int   = Field(4,  ge=1,  le=6)
    content_personalization: float = Field(75, ge=0,  le=100)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Behavioral Personalization Engine",
    description="Ingests customer activity data, builds dynamic behavioral profiles, and drives targeted marketing decisions.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_EXPORT_PATH = ROOT / "output" / "dashboard.html"


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse, summary="Full dashboard (HTML)", tags=["Dashboard"])
def get_dashboard():
    data = build_dashboard(CUSTOMERS)
    return HTMLResponse(content=render_dashboard(data))


@app.get("/api/overview", summary="KPI overview metrics", tags=["Analytics"])
def api_overview():
    return build_dashboard(CUSTOMERS).overview.to_dict()


@app.get("/api/customers", summary="List customer profiles", tags=["Customers"])
def api_customers(
    segment: Optional[str] = Query(None),
    sort_by: str = Query("score"),
    limit: int = Query(100, ge=1, le=500),
):
    customers = list(CUSTOMERS)
    if segment:
        customers = [c for c in customers if c.segment.value.lower() == segment.lower()]
    sort_map = {
        "score": lambda c: c.engagement_score,
        "aov":   lambda c: c.avg_order_value,
        "freq":  lambda c: c.purchase_freq,
    }
    customers.sort(key=sort_map.get(sort_by, sort_map["score"]), reverse=True)
    return [c.to_dict() for c in customers[:limit]]


@app.get("/api/customers/{customer_id}", summary="Single customer profile", tags=["Customers"])
def api_customer(customer_id: int):
    c = next((c for c in CUSTOMERS if c.id == customer_id), None)
    if not c:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return c.to_dict()


@app.get("/api/segments", summary="Segment summaries", tags=["Analytics"])
def api_segments():
    return [s.to_dict() for s in build_dashboard(CUSTOMERS).segments]


@app.get("/api/heatmap", summary="Session timing heatmap", tags=["Analytics"])
def api_heatmap():
    return build_dashboard(CUSTOMERS).heatmap.to_dict()


@app.get("/api/campaigns", summary="Campaign decisions", tags=["Campaigns"])
def api_campaigns():
    return [c.to_dict() for c in build_dashboard(CUSTOMERS).campaigns]


@app.get("/api/rules", summary="All rules and content matrix", tags=["Rules"])
def api_rules():
    data = build_dashboard(CUSTOMERS)
    return {
        "timing_rules":   [r.to_dict() for r in data.timing_rules],
        "segment_rules":  [r.to_dict() for r in data.segment_rules],
        "content_matrix": [r.to_dict() for r in data.content_matrix],
    }


@app.post("/api/simulate", summary="Run engagement & revenue simulation", tags=["Simulation"])
def api_simulate(body: SimulationRequest):
    inputs = SimulationInputs(
        discount_aggressiveness=body.discount_aggressiveness,
        send_time_optimization=body.send_time_optimization,
        segmentation_depth=body.segmentation_depth,
        content_personalization=body.content_personalization,
    )
    return run_simulation(inputs).to_dict()


@app.get("/api/export", summary="Download generated HTML dashboard", tags=["Dashboard"])
def api_export():
    data = build_dashboard(CUSTOMERS)
    render_dashboard(data, output_path=_EXPORT_PATH)
    return FileResponse(path=str(_EXPORT_PATH), filename="dashboard.html", media_type="text/html")
