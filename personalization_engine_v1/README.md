# Behavioral Personalization Engine

A Python backend that ingests customer shopping activity from a SQLite database, builds dynamic behavioral profiles, and uses a rule-based prediction engine to classify customers into segments and recommend targeted marketing strategies. Includes a self-contained two-tab interactive dashboard — no frontend build step required.

---

## Architecture

```
data/
├── seed.py              ← 40-customer sample dataset (run to populate DB)
├── db.py                ← SQLite loader (SQLAlchemy)
└── customers.db         ← SQLite database (gitignored — see Setup)

models/
└── customer.py          ← All data models (stdlib dataclasses)

engine/
├── profiler.py          ← KPIs, segment summaries, rule engine, dashboard builder
├── predictor.py         ← Rule-based segment classifier + strategy recommender
└── html_generator.py    ← Jinja2 renderer → self-contained HTML

api/
└── app.py               ← FastAPI REST API

templates/
└── dashboard.html       ← Two-tab interactive dashboard

main.py                  ← CLI entry point
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Seed the database

The database file (`customers.db`) is not included in the repo. Generate it from the sample data:

```bash
python data/seed.py
```

This creates `customers.db` with 40 customers spread across all 6 behavioral segments.

### 3. Start the server

```bash
python main.py --serve
```

- **Dashboard** → http://localhost:8000/dashboard
- **API docs** → http://localhost:8000/docs

### 4. Export a static dashboard (no server needed)

```bash
python main.py --export
# opens output/dashboard.html in any browser
```

---

## CLI Options

```
python main.py [--export] [--serve] [--host HOST] [--port PORT] [--reload]

  --export        Write output/dashboard.html
  --serve         Start the FastAPI server
  --host HOST     Bind host (default: 127.0.0.1)
  --port PORT     Bind port (default: 8000)
  --reload        Enable hot-reload for development
```

---

## Prediction Engine

`engine/predictor.py` is the core intelligence layer. It is fully deterministic — no external API calls.

### How it works

Each customer is scored against all 6 segments on a 0–100 scale using behavioral signals:

| Signal | Used by |
|--------|---------|
| `discount_usage > 0.80` | SALE_SHOPPER (+55) |
| `session_hours` contains late-night hours | NIGHT_STREETWEAR (+40) |
| `session_hours` contains lunch hours | LUNCH_SHOPPER (+45) |
| `avg_order_value > 350` | FORMAL_RARE (+35) |
| `purchase_freq > 3` + morning sessions | ATHLETIC_REGULAR (+40) |
| `avg_order_value > 150` + low discount use | FULL_PRICE (+40) |

The segment with the highest score becomes the **predicted segment**. Confidence is computed as:

```
confidence = min(100, best_score × 0.6 + gap × 0.8)
```

where `gap` = best score − second-best score. High confidence requires both a strong absolute score and a clear separation from competing segments.

### Behavioral Drift

When a customer's predicted segment differs from their assigned segment, they are flagged as **drifted**. The dashboard surfaces these customers for potential re-segmentation.

### Strategy Recommendations

Each predicted segment maps to a recommended marketing strategy:

| Segment | Channel | Send Time | Offer |
|---------|---------|-----------|-------|
| FULL_PRICE | Email | Evening (8 PM) | New arrivals, no discount |
| NIGHT_STREETWEAR | Push notification | Late night (10 PM) | Limited drop alert |
| LUNCH_SHOPPER | Email | Lunch (12 PM) | Free shipping threshold |
| SALE_SHOPPER | SMS | Payday (25th, 1 PM) | Flash sale, max discount |
| ATHLETIC_REGULAR | Email | Morning (7 AM) | Loyalty reward |
| FORMAL_RARE | Email | Weekend morning | Exclusive new season preview |

---

## Dashboard

Two-tab layout:

### Metrics tab
- Overview KPIs: total customers, average AOV, engagement score, sale dependency
- Prediction accuracy % and behavioral drift %
- Category breakdown (Streetwear / Athletic / Formal)
- Session timing heatmap (day × hour)
- Segment distribution
- Timing, segment, and content rules

### Users & Campaigns tab
- All 40 customers with segment, AOV, engagement, discount usage
- **Match / Drift badge** per customer (predicted vs assigned segment)
- Confidence % for each prediction
- Filter: "Show drift only" toggle
- Sort by: Name, AOV, Engagement, Discount, Confidence
- Per-customer detail panel:
  - Segment score breakdown (all 6 scores as bars)
  - Predicted best-fit strategy (channel, send time, offer, full action)
  - Confidence bar with color coding
  - Drift warning if predicted ≠ assigned segment

---

## REST API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Full rendered HTML dashboard |
| GET | `/api/overview` | KPI metrics |
| GET | `/api/customers` | Customer list — filterable by segment, sortable |
| GET | `/api/customers/{id}` | Single customer profile |
| GET | `/api/segments` | Segment distribution summaries |
| GET | `/api/heatmap` | Session timing heatmap matrix (7×7) |
| GET | `/api/rules` | Timing rules, segment rules, content matrix |
| GET | `/api/campaigns` | Rule-based campaign decisions |
| GET | `/api/export` | Download generated HTML dashboard |

---

## Database

SQLite by default (`customers.db` in the project root). The file is gitignored — run `python data/seed.py` after cloning.

To switch to PostgreSQL:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"
```

`data/db.py` uses SQLAlchemy so the same code works across both.

**`customers` table** — one row per customer, all behavioral profile fields.

---

## Segments

| Segment | Behavior |
|---------|----------|
| FULL_PRICE | High AOV, low discount use, evening sessions |
| NIGHT_STREETWEAR | Late-night browsers, streetwear focus |
| LUNCH_SHOPPER | 12pm purchase windows, free-shipping driven |
| SALE_SHOPPER | Only converts on discount, payday-sensitive |
| ATHLETIC_REGULAR | Morning sessions, high frequency, loyalty-responsive |
| FORMAL_RARE | Very high AOV, infrequent, weekend browsers |

---

## Customer Profile Fields

| Field | Type | Description |
|-------|------|-------------|
| `segment` | enum | Assigned behavioral segment (6 types) |
| `timing` | enum | Dominant session window |
| `session_hours` | list[int] | Active hours of day (0–23) |
| `purchase_freq` | float | Average purchases per month |
| `avg_order_value` | float | Average basket value (USD) |
| `categories` | list | streetwear / formal / athletic |
| `size_consistent` | float | 0–1: how consistently same size is ordered |
| `discount_usage` | float | 0–1: fraction of orders using a discount |
| `engagement_score` | int | 0–100: composite behavioral score |
