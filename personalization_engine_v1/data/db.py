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

from sqlalchemy import create_engine, text

from models.customer import (
    Category, CustomerProfile, Segment, SessionTiming,
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
