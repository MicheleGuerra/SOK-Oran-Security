
# -*- coding: utf-8 -*-
"""CLI to merge *academic* CSVs for a given run directory.
Usage:
    python oran_merge_academics.py <run_dir> [--out merged.csv]
"""
import argparse
from pathlib import Path
from oran_csv_utils import merge_academic_csvs

def main():
    ap = argparse.ArgumentParser(description="Merge academic CSVs in a run directory")
    ap.add_argument("run_dir", type=Path, help="Path to the run directory containing CSVs")
    ap.add_argument("--out", type=str, default="academics_merged.csv", help="Output filename (inside <run_dir>/merged/)")
    args = ap.parse_args()
    out = merge_academic_csvs(args.run_dir, merged_filename=args.out)
    print(out)

if __name__ == "__main__":
    main()
