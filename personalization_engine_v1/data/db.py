"""
data/db.py
──────────
Database-backed customer loader.

Replaces data/seed.py for production use. Queries a real database and
maps rows onto CustomerProfile objects — the rest of the engine is unchanged.

Supported databases (swap the connection string):
  SQLite   (dev)  →  sqlite:///customers.db
  PostgreSQL       →  postgresql://user:password@host:5432/dbname
  MySQL            →  mysql+pymysql://user:password@host:3306/dbname

Install the driver for your database:
  pip install sqlalchemy              # core (required)
  pip install psycopg2-binary         # PostgreSQL
  pip install pymysql                 # MySQL

Expected table schema (customers):
─────────────────────────────────────────────────────────────────────────
  id               INTEGER   PRIMARY KEY
  name             TEXT
  initials         TEXT
  color            TEXT      hex color, e.g. "#534AB7"
  segment          TEXT      must match Segment enum values exactly
  timing           TEXT      must match SessionTiming enum values exactly
  session_hours    TEXT      JSON array, e.g. "[18, 19, 20]"
  purchase_freq    REAL
  avg_order_value  REAL
  categories       TEXT      JSON array of Category values, e.g. '["formal"]'
  size_consistent  REAL      0.0 – 1.0
  discount_usage   REAL      0.0 – 1.0
  engagement_score INTEGER   0 – 100
─────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

import numpy as np
from sqlalchemy import create_engine, text

from models.customer import (
    Category, CustomerProfile, HeatmapData, Segment, SessionTiming,
)


# ── Connection string ─────────────────────────────────────────────────────────
# Set DATABASE_URL in your environment, e.g.:
#   export DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"
#   export DATABASE_URL="sqlite:///./customers.db"

DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./customers.db")

_engine = create_engine(DATABASE_URL, pool_pre_ping=True)


# ── Row → CustomerProfile ─────────────────────────────────────────────────────

def _row_to_profile(row) -> CustomerProfile:
    """Map a database row (dict or Row) onto a CustomerProfile."""
    r = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return CustomerProfile(
        id=r["id"],
        name=r["name"],
        initials=r["initials"],
        color=r["color"],
        segment=Segment(r["segment"]),
        timing=SessionTiming(r["timing"]),
        session_hours=json.loads(r["session_hours"]),
        purchase_freq=float(r["purchase_freq"]),
        avg_order_value=float(r["avg_order_value"]),
        categories=[Category(c) for c in json.loads(r["categories"])],
        size_consistent=float(r["size_consistent"]),
        discount_usage=float(r["discount_usage"]),
        engagement_score=int(r["engagement_score"]),
    )


# ── Public loader ─────────────────────────────────────────────────────────────

def load_customers(
    segment: str | None = None,
    limit: int = 10_000,
) -> list[CustomerProfile]:
    """
    Load customers from the database and return as CustomerProfile objects.

    Args:
        segment: Optional Segment value to filter by (e.g. "Sale Hunter").
        limit:   Maximum number of rows to return.
    """
    if segment:
        query = text(
            "SELECT * FROM customers WHERE segment = :seg LIMIT :lim"
        )
        params = {"seg": segment, "lim": limit}
    else:
        query = text("SELECT * FROM customers LIMIT :lim")
        params = {"lim": limit}

    with _engine.connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [_row_to_profile(r) for r in rows]


# ── Cached list (mirrors the seed.py CUSTOMERS constant) ─────────────────────

@lru_cache(maxsize=1)
def _cached_customers() -> tuple[CustomerProfile, ...]:
    """
    Returns a cached tuple of all customers.
    Cache is invalidated on process restart (suitable for batch jobs).
    For live/streaming data, call load_customers() directly each request.
    """
    return tuple(load_customers())


# Drop-in replacement for seed.CUSTOMERS
CUSTOMERS: list[CustomerProfile] = list(_cached_customers())


# ── Campaign history ──────────────────────────────────────────────────────────

def _ensure_campaign_runs_table() -> None:
    """Create campaign_runs table (and any missing outcome columns) if needed."""
    with _engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaign_runs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at          TEXT    NOT NULL,
                agent_mode          TEXT    NOT NULL,
                decisions           TEXT    NOT NULL,
                context             TEXT,
                actual_ctr_pct      REAL,
                actual_conv_pct     REAL,
                revenue_lift_pct    REAL,
                outcome_notes       TEXT,
                outcome_recorded_at TEXT
            )
        """))
        # Migrate tables created before outcome columns were added
        for col, col_type in [
            ("actual_ctr_pct",      "REAL"),
            ("actual_conv_pct",     "REAL"),
            ("revenue_lift_pct",    "REAL"),
            ("outcome_notes",       "TEXT"),
            ("outcome_recorded_at", "TEXT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE campaign_runs ADD COLUMN {col} {col_type}"))
            except Exception:
                pass  # column already exists


def save_campaign_run(
    agent_mode: str,
    decisions: dict,
    context: dict | None = None,
) -> int:
    """
    Persist a campaign run to the database.
    Returns the new run's integer ID.
    """
    import json as _json
    from datetime import datetime, timezone

    _ensure_campaign_runs_table()
    with _engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO campaign_runs (created_at, agent_mode, decisions, context)
                VALUES (:ts, :mode, :dec, :ctx)
            """),
            {
                "ts":   datetime.now(timezone.utc).isoformat(),
                "mode": agent_mode,
                "dec":  _json.dumps(decisions),
                "ctx":  _json.dumps(context) if context else None,
            },
        )
        return result.lastrowid


def get_recent_runs(limit: int = 5) -> list[dict]:
    """
    Return the N most recent campaign runs as plain dicts, including any
    recorded outcomes so the Strategist agent can learn from past performance.
    """
    import json as _json

    _ensure_campaign_runs_table()
    with _engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM campaign_runs ORDER BY id DESC LIMIT :lim"),
            {"lim": limit},
        ).fetchall()

    result = []
    for r in rows:
        m = r._mapping
        run = {
            "id":         m["id"],
            "created_at": m["created_at"],
            "agent_mode": m["agent_mode"],
            "decisions":  _json.loads(m["decisions"]),
            "context":    _json.loads(m["context"]) if m["context"] else None,
            "outcome":    None,
        }
        if m["actual_ctr_pct"] is not None:
            run["outcome"] = {
                "actual_ctr_pct":      m["actual_ctr_pct"],
                "actual_conv_pct":     m["actual_conv_pct"],
                "revenue_lift_pct":    m["revenue_lift_pct"],
                "outcome_notes":       m["outcome_notes"],
                "outcome_recorded_at": m["outcome_recorded_at"],
            }
        result.append(run)
    return result


# ── Session heatmap ───────────────────────────────────────────────────────────

# Day-of-week activity weights per session timing type.
# Index 0 = Monday … 6 = Sunday.
_DAY_WEIGHTS: dict[SessionTiming, list[float]] = {
    SessionTiming.MORNING:    [0.20, 0.20, 0.20, 0.20, 0.15, 0.03, 0.02],
    SessionTiming.LUNCH:      [0.20, 0.20, 0.20, 0.20, 0.15, 0.03, 0.02],
    SessionTiming.AFTERNOON:  [0.18, 0.18, 0.20, 0.18, 0.15, 0.06, 0.05],
    SessionTiming.EVENING:    [0.15, 0.15, 0.18, 0.18, 0.18, 0.08, 0.08],
    SessionTiming.LATE_NIGHT: [0.14, 0.14, 0.16, 0.16, 0.16, 0.12, 0.12],
    SessionTiming.VARIED:     [0.143, 0.143, 0.143, 0.143, 0.143, 0.143, 0.142],
    SessionTiming.WEEKEND:    [0.05, 0.05, 0.05, 0.05, 0.05, 0.375, 0.375],
}

# Map heatmap display slots → the hours of day they cover.
_SLOT_HOURS: list[tuple[str, list[int]]] = [
    ("6am",  [6, 7, 8]),
    ("9am",  [9, 10, 11]),
    ("12pm", [12, 13, 14]),
    ("3pm",  [15, 16, 17]),
    ("6pm",  [18, 19, 20]),
    ("9pm",  [21]),
    ("12am", [22, 23, 0, 1, 2]),
]


def _ensure_session_counts_table() -> None:
    with _engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS session_counts (
                hour        INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                count       INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (hour, day_of_week)
            )
        """))


def seed_session_counts(customers: list[CustomerProfile], force: bool = False) -> None:
    """
    Populate session_counts from the customer list.

    Each customer contributes sessions proportional to their purchase_freq
    (used as a proxy for browsing activity) spread across their session_hours
    and weighted by day-of-week patterns derived from their timing type.

    The table is only seeded once unless force=True.
    """
    _ensure_session_counts_table()

    with _engine.connect() as conn:
        row_count = conn.execute(text("SELECT COUNT(*) FROM session_counts")).scalar()

    if row_count and not force:
        return  # already seeded

    # Accumulate counts into a (24 × 7) numpy array
    counts = np.zeros((24, 7), dtype=np.float64)

    for c in customers:
        day_w = _DAY_WEIGHTS[c.timing]
        # Sessions per month ≈ purchase_freq × 10 (browsing is ~10× purchasing)
        sessions_per_hour = c.purchase_freq * 10 / max(len(c.session_hours), 1)
        for hour in c.session_hours:
            for day, w in enumerate(day_w):
                counts[hour, day] += sessions_per_hour * w

    # Write to DB — upsert so force=True works cleanly
    rows = [
        {"hour": int(h), "day": int(d), "count": int(round(counts[h, d]))}
        for h in range(24)
        for d in range(7)
        if counts[h, d] > 0
    ]

    with _engine.begin() as conn:
        conn.execute(text("DELETE FROM session_counts"))
        conn.execute(
            text("INSERT INTO session_counts (hour, day_of_week, count) VALUES (:hour, :day, :count)"),
            rows,
        )


def build_heatmap_from_db() -> HeatmapData:
    """
    Query session_counts and return a HeatmapData with a 7×7 intensity
    matrix (time slots × days) scaled to 1–9.

    Falls back to a flat mid-range matrix if the table is empty.
    """
    _ensure_session_counts_table()

    with _engine.connect() as conn:
        rows = conn.execute(
            text("SELECT hour, day_of_week, count FROM session_counts")
        ).fetchall()

    if not rows:
        # Fallback: flat matrix — surface the gap in monitoring
        matrix = [[5] * 7 for _ in range(7)]
        return HeatmapData(
            time_labels=["6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"],
            day_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            matrix=matrix,
        )

    # Build lookup: raw[(hour, day)] = count
    raw: dict[tuple[int, int], int] = {}
    for r in rows:
        raw[(r.hour, r.day_of_week)] = r.count

    # Aggregate by display slot
    slot_matrix: list[list[float]] = []
    for _, hours in _SLOT_HOURS:
        row = []
        for day in range(7):
            total = sum(raw.get((h, day), 0) for h in hours)
            row.append(float(total))
        slot_matrix.append(row)

    # Normalise to 1–9
    flat = [v for row in slot_matrix for v in row]
    lo, hi = min(flat), max(flat)
    span = hi - lo if hi > lo else 1.0

    scaled = [
        [int(round(1 + (v - lo) / span * 8)) for v in row]
        for row in slot_matrix
    ]

    return HeatmapData(
        time_labels=["6am", "9am", "12pm", "3pm", "6pm", "9pm", "12am"],
        day_labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        matrix=scaled,
    )


def record_outcome(
    run_id: int,
    actual_ctr_pct: float | None = None,
    actual_conv_pct: float | None = None,
    revenue_lift_pct: float | None = None,
    outcome_notes: str | None = None,
) -> None:
    """
    Attach real-world campaign results to a past run.
    The Strategist agent reads these on subsequent pipeline calls and adjusts
    its predictions and decisions based on what actually worked.
    """
    from datetime import datetime, timezone

    _ensure_campaign_runs_table()
    with _engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE campaign_runs
                SET actual_ctr_pct      = :ctr,
                    actual_conv_pct     = :conv,
                    revenue_lift_pct    = :rev,
                    outcome_notes       = :notes,
                    outcome_recorded_at = :ts
                WHERE id = :id
            """),
            {
                "id":    run_id,
                "ctr":   actual_ctr_pct,
                "conv":  actual_conv_pct,
                "rev":   revenue_lift_pct,
                "notes": outcome_notes,
                "ts":    datetime.now(timezone.utc).isoformat(),
            },
        )
