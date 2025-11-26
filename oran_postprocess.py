
# -*- coding: utf-8 -*-
"""
oran_postprocess.py
-------------------
Utilities to merge per-file CSVs produced during a run into per-type aggregates.

- merge_run_csvs(run_dir, *, academics_name="academics.all.csv", specs_name="specs.all.csv")
  Scans `run_dir/manifest.jsonl` if present; otherwise globs for *.csv.
  Uses a strict header for Academic CSVs and writes a single combined CSV.
  Specifications are kept separate and combined into a second CSV if present.
"""

from __future__ import annotations
import csv, json
from pathlib import Path
from typing import List, Dict, Any, Tuple

ACADEMIC_HEADER = ["Name","Type","Description","Target Components / Interfaces","Affected Components / Interfaces","Reference"]
SPEC_HEADER = ACADEMIC_HEADER  # placeholder; replace when spec schema differs

def _read_csv(path: Path) -> Tuple[List[str], List[List[str]]]:
    with open(path, "r", encoding="utf-8") as f:
        r = csv.reader(f, delimiter=",", quotechar='"')
        rows = [row for row in r]
    if not rows:
        return [], []
    return rows[0], rows[1:]

def _write_csv(path: Path, header: List[str], rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        w.writerow(header)
        for row in rows:
            # pad/truncate
            fixed = [ (row[i] if i < len(row) else "") for i in range(len(header)) ]
            w.writerow(fixed)

def _load_manifest(run_dir: Path) -> List[Dict[str, Any]]:
    mf = run_dir / "manifest.jsonl"
    items: List[Dict[str,Any]] = []
    if mf.exists():
        for line in mf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line: 
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items

def merge_run_csvs(run_dir: Path, *, academics_name="academics.all.csv", specs_name="specs.all.csv") -> Dict[str, Path]:
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"run_dir not found: {run_dir}")

    manifest = _load_manifest(run_dir)
    csvs_ac: List[Path] = []
    csvs_spec: List[Path] = []

    if manifest:
        for item in manifest:
            path = run_dir / item.get("csv_name","")
            if not path.exists():
                continue
            if item.get("doc_type") == "Academic Paper":
                csvs_ac.append(path)
            elif item.get("doc_type") == "O-RAN Specification":
                csvs_spec.append(path)
    else:
        # Fallback: take all CSVs; assume "spec" in name means spec
        for p in run_dir.glob("*.csv"):
            if "spec" in p.name.lower():
                csvs_spec.append(p)
            else:
                csvs_ac.append(p)

    out: Dict[str, Path] = {}

    # Merge academics
    if csvs_ac:
        rows_all: List[List[str]] = []
        for p in csvs_ac:
            header, rows = _read_csv(p)
            # accept either exact header or a superset; map by index position
            if header != ACADEMIC_HEADER:
                # try to map by names
                idx = [header.index(h) if h in header else -1 for h in ACADEMIC_HEADER]
                for r in rows:
                    rows_all.append([ (r[i] if 0 <= i < len(r) else "") for i in idx ])
            else:
                rows_all.extend(rows)
        out_ac = run_dir / academics_name
        _write_csv(out_ac, ACADEMIC_HEADER, rows_all)
        out["academics"] = out_ac

    # Merge specs (same header placeholder for now)
    if csvs_spec:
        rows_all: List[List[str]] = []
        for p in csvs_spec:
            header, rows = _read_csv(p)
            if header != SPEC_HEADER:
                idx = [header.index(h) if h in header else -1 for h in SPEC_HEADER]
                for r in rows:
                    rows_all.append([ (r[i] if 0 <= i < len(r) else "") for i in idx ])
            else:
                rows_all.extend(rows)
        out_sp = run_dir / specs_name
        _write_csv(out_sp, SPEC_HEADER, rows_all)
        out["specs"] = out_sp

    return out
