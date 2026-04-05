#!/usr/bin/env python3
"""
main.py
───────
Entry point for the Behavioral Personalization Engine.

Usage
-----
  # Generate the HTML dashboard file only (no server needed):
  python main.py --export

  # Start the FastAPI server (dashboard available at http://localhost:8000):
  python main.py --serve

  # Do both — generate the file AND start the server:
  python main.py --export --serve

  # Serve on a custom host/port:
  python main.py --serve --host 0.0.0.0 --port 9000

The generated HTML file is written to:
  output/dashboard.html

The FastAPI interactive docs are at:
  http://localhost:8000/docs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Make project root importable ─────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from data.db import CUSTOMERS
from engine.profiler import build_dashboard, SimulationInputs
from engine.html_generator import render_dashboard


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Behavioral Personalization Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--export", action="store_true",
                   help="Generate dashboard.html to output/")
    p.add_argument("--serve",  action="store_true",
                   help="Start the FastAPI API server")
    p.add_argument("--host",   default="127.0.0.1",
                   help="Host to bind (default: 127.0.0.1)")
    p.add_argument("--port",   type=int, default=8000,
                   help="Port to bind (default: 8000)")
    p.add_argument("--reload", action="store_true",
                   help="Enable auto-reload for development")
    return p.parse_args()


# ── Export ────────────────────────────────────────────────────────────────────

def export_dashboard() -> Path:
    print("Building dashboard data…")
    data = build_dashboard(CUSTOMERS, sim_inputs=SimulationInputs())

    output_path = ROOT / "output" / "dashboard.html"
    print(f"Rendering HTML → {output_path}")
    render_dashboard(data, output_path=output_path)

    print(f"\n✓ Dashboard written to: {output_path.resolve()}")
    print(f"  Open it in your browser: file://{output_path.resolve()}")
    return output_path


# ── Print summary ─────────────────────────────────────────────────────────────

def print_summary() -> None:
    data = build_dashboard(CUSTOMERS)
    ov   = data.overview

    print("\n── Dashboard Summary ───────────────────────────────")
    print(f"  Total customers    : {ov.total_customers:,}")
    print(f"  Avg order value    : ${ov.avg_order_value:.2f}")
    print(f"  Engagement score   : {ov.engagement_score}")
    print(f"  Sale dependency    : {ov.sale_dependency_pct}%")
    print(f"\n  Segments ({len(data.segments)}):")
    for seg in data.segments:
        bar = "█" * int(seg.percentage / 2)
        print(f"    {seg.name.value:<25} {bar} {seg.percentage}%")
    print(f"\n  Campaigns generated: {len(data.campaigns)}")
    for c in data.campaigns:
        print(f"    [{c.action.value.upper():<4}] {c.segment.value:<25} → {c.send_window}")
    print("────────────────────────────────────────────────────\n")


# ── Serve ─────────────────────────────────────────────────────────────────────

def serve(host: str, port: int, reload: bool) -> None:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    print(f"\n✓ Starting API server at http://{host}:{port}")
    print(f"  Dashboard  → http://{host}:{port}/dashboard")
    print(f"  API docs   → http://{host}:{port}/docs\n")

    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=reload,
        app_dir=str(ROOT),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Default: if no flags are given, do both export and summary
    if not args.export and not args.serve:
        print_summary()
        export_dashboard()
        return

    if args.export:
        print_summary()
        export_dashboard()

    if args.serve:
        serve(args.host, args.port, args.reload)


if __name__ == "__main__":
    main()
