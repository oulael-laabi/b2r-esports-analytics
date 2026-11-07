#!/usr/bin/env python3
"""
Orchestrateur : exécute toute la chaîne P1 -> P7 sans intervention manuelle.

    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --regenerate     # régénère aussi le dataset

En mode CSV (config/db.example.ini, use_csv_fallback = true) tout s'enchaîne
depuis data/generated/. En mode MySQL, penser à importer sql/03 puis, après P4,
data/exports/player_ranking_insert.sql + sql/05_views.sql.
"""
import argparse
import runpy
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
STEPS = [
    "p1_etl_validation.py",
    "p3_match_analysis.py",
    "p4_player_ranking.py",
    "p5_coach_analytics.py",
    "p6_weekly_report.py",
    "p7_studio_sync.py",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerate", action="store_true",
                    help="relance scripts/generate_dataset.py avant la chaîne")
    args = ap.parse_args()

    if args.regenerate:
        print(">>> génération du dataset")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_dataset.py")], check=True)

    import os
    os.chdir(NB)  # les notebooks utilisent Path.cwd().parent
    for step in STEPS:
        print(f"\n{'=' * 64}\n>>> {step}\n{'=' * 64}")
        t = time.perf_counter()
        runpy.run_path(str(NB / step), run_name="__main__")
        print(f"--- {step} OK ({time.perf_counter() - t:.1f} s)")

    print("\nChaîne P1 -> P7 terminée.")
    print("Sorties : data/exports/  ·  outputs/reports/  ·  outputs/studio/")


if __name__ == "__main__":
    main()
