#!/usr/bin/env python3
"""
Aggregate OpenLane PPA metrics.csv files across multiple sweep runs
into a single combined CSV for easy plotting/analysis.

Usage:
    python3 aggregate_ppa.py --runs-dir designs/spm_sweep/runs --out ppa_summary.csv
"""

import argparse
import csv
import glob
import os
import sys


# Columns we care about most for PPA analysis (edit this list freely).
# Set to None to keep ALL columns from metrics.csv instead of a subset.
KEEP_COLUMNS = [
    "design_name",
    "config",
    "flow_status",
    "CLOCK_PERIOD",
    "total_runtime",
    "DIEAREA_mm^2",
    "Final_Util",
    "wns",
    "tns",
    "critical_path_ns",
    "suggested_clock_frequency",
    "power_typical_internal_uW",
    "power_typical_switching_uW",
    "power_typical_leakage_uW",
    "synth_cell_count",
    "TotalCells",
    "wire_length",
    "tritonRoute_violations",
    "lvs_total_errors",
]


def find_metrics_files(runs_dir):
    """Find every metrics.csv (or metrics.csv-like report) under runs_dir/*/reports/."""
    patterns = [
        os.path.join(runs_dir, "*", "reports", "metrics.csv"),
        os.path.join(runs_dir, "*", "metrics.csv"),
    ]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    return sorted(set(files))


def load_metrics(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return None
    return rows[0]  # metrics.csv normally has a single data row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--runs-dir",
        default="designs/spm_sweep/runs",
        help="Path to the OpenLane design's runs/ directory (default: designs/spm_sweep/runs)",
    )
    ap.add_argument(
        "--out",
        default="ppa_summary.csv",
        help="Output CSV path (default: ppa_summary.csv)",
    )
    ap.add_argument(
        "--all-columns",
        action="store_true",
        help="Keep every column found in metrics.csv instead of the curated PPA subset",
    )
    args = ap.parse_args()

    metrics_files = find_metrics_files(args.runs_dir)
    if not metrics_files:
        print(f"No metrics.csv files found under: {args.runs_dir}", file=sys.stderr)
        print("Check the path, or run a sweep first (see previous steps).", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(metrics_files)} run(s):")
    for f in metrics_files:
        print(f"  - {f}")

    all_rows = []
    all_keys = set()
    for path in metrics_files:
        row = load_metrics(path)
        if row is None:
            print(f"  (skipped, empty) {path}", file=sys.stderr)
            continue
        # Tag which run/tag this came from, based on folder name: runs/<tag>/reports/metrics.csv
        run_tag = path.split(os.sep)
        try:
            idx = run_tag.index("runs")
            row["run_tag"] = run_tag[idx + 1]
        except (ValueError, IndexError):
            row["run_tag"] = os.path.basename(os.path.dirname(os.path.dirname(path)))
        all_rows.append(row)
        all_keys.update(row.keys())

    if not all_rows:
        print("No valid rows parsed from any metrics.csv.", file=sys.stderr)
        sys.exit(1)

    if args.all_columns:
        fieldnames = ["run_tag"] + [k for k in sorted(all_keys) if k != "run_tag"]
    else:
        fieldnames = ["run_tag"] + [c for c in KEEP_COLUMNS if c in all_keys]
        missing = [c for c in KEEP_COLUMNS if c not in all_keys]
        if missing:
            print(f"Note: columns not found in metrics.csv (skipped): {missing}", file=sys.stderr)

    # Sort rows by CLOCK_PERIOD if present, for a clean sweep table
    def sort_key(r):
        try:
            return float(r.get("CLOCK_PERIOD", 0))
        except (TypeError, ValueError):
            return 0.0

    all_rows.sort(key=sort_key)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"\nWrote {len(all_rows)} row(s) to {args.out}")


if __name__ == "__main__":
    main()