"""CLI orchestrator for the two-source bronze/silver/gold data lake simulation.

Usage:
    python run.py --stage all      [--source all|orders|invoicing] [--reset]
    python run.py --stage generate [--source orders]
    python run.py --stage bronze   [--source invoicing]
    python run.py --stage silver
    python run.py --stage gold

`generate` and `bronze` are scoped by --source. `silver` and `gold` are
cross-source and always consume everything in bronze.
"""

from __future__ import annotations

import argparse
import os
import sys

# Make the src/ package importable regardless of where run.py is called from.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from common import log, reset_lake  # noqa: E402
import generate_orders  # noqa: E402
import generate_invoices  # noqa: E402
import bronze_orders  # noqa: E402
import bronze_invoices  # noqa: E402
import silver  # noqa: E402
import gold  # noqa: E402

STAGES = ("generate", "bronze", "silver", "gold")
SOURCES = ("orders", "invoicing")


def _wants(source_arg: str, source: str) -> bool:
    return source_arg in ("all", source)


def run_stage(stage: str, source_arg: str) -> None:
    if stage == "generate":
        if _wants(source_arg, "orders"):
            generate_orders.generate()
        if _wants(source_arg, "invoicing"):
            generate_invoices.generate()
    elif stage == "bronze":
        if _wants(source_arg, "orders"):
            bronze_orders.ingest()
        if _wants(source_arg, "invoicing"):
            bronze_invoices.ingest()
    elif stage == "silver":
        silver.build()
    elif stage == "gold":
        gold.build()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Two-source Bronze/Silver/Gold data lake simulation (pure stdlib).",
    )
    parser.add_argument(
        "--stage",
        choices=("all",) + STAGES,
        default="all",
        help="Which stage to run (default: all).",
    )
    parser.add_argument(
        "--source",
        choices=("all",) + SOURCES,
        default="all",
        help="Which source to generate/ingest (default: all). Ignored by silver/gold.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the data/ lake before running for a clean start.",
    )
    args = parser.parse_args(argv)

    if args.reset:
        reset_lake()
        log("run", "reset: cleared data/ directory")

    stages = STAGES if args.stage == "all" else (args.stage,)
    for stage in stages:
        run_stage(stage, args.source)

    log("run", "done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
