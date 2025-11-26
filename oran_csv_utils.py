
# -*- coding: utf-8 -*-
"""CSV utilities that work *with or without* pandas installed.
- find_academic_csvs(run_dir): recursively lists academic CSVs
- merge_academic_csvs(run_dir, merged_filename="academics_merged.csv"): merge and write merged/academics_merged.csv
Detection:
- Prefer column 'doc_type'/'type'/'source_type' containing 'academic' (if pandas available)
- Fallback: filename contains academic|paper|papers|academics
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Dict

try:
    import pandas as pd  # type: ignore
    _HAS_PANDAS = True
except Exception:
    pd = None  # type: ignore
    _HAS_PANDAS = False

ACADEMIC_NAME_PATTERNS = re.compile(r"(academic|paper|papers|academics)", re.IGNORECASE)
DEFAULT_MERGED_NAME = "academics_merged.csv"

def _is_academic_csv_path(csv_path: Path) -> bool:
    return bool(ACADEMIC_NAME_PATTERNS.search(csv_path.name))

def _is_academic_csv_with_pandas(csv_path: Path) -> bool:
    if not _HAS_PANDAS:
        return _is_academic_csv_path(csv_path)
    try:
        head = pd.read_csv(csv_path, nrows=25)
        lower_cols = [c.lower().strip() for c in head.columns]
        for cnm in ("doc_type","type","source_type","source"):
            if cnm in lower_cols:
                col = head.columns[lower_cols.index(cnm)]
                if head[col].astype(str).str.lower().str.contains("academic").any():
                    return True
    except Exception:
        pass
    return _is_academic_csv_path(csv_path)

def find_academic_csvs(run_dir: Path) -> List[Path]:
    run_dir = Path(run_dir)
    csvs: List[Path] = []
    for p in run_dir.rglob("*.csv"):
        if _is_academic_csv_with_pandas(p):
            csvs.append(p)
    return csvs

def _merge_with_pandas(csv_paths: List[Path], out_csv: Path) -> Path:
    import pandas as pd  # type: ignore
    frames = []
    for p in csv_paths:
        try:
            df = pd.read_csv(p)
        except Exception:
            try:
                df = pd.read_csv(p, sep=";")
            except Exception:
                continue
        df["__source_file"] = str(p.resolve())
        df["__source_doc"]  = p.parent.name
        frames.append(df)
    if not frames:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            f.write("NOTE,Files were found but could not be parsed\n")
        return out_csv
    merged = pd.concat(frames, ignore_index=True, sort=False).drop_duplicates()
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_csv, index=False)
    return out_csv

def _merge_with_stdlib(csv_paths: List[Path], out_csv: Path) -> Path:
    headers_order: List[str] = []
    headers_set = set()
    rows: List[Dict[str,str]] = []

    for p in csv_paths:
        try:
            # try comma then semicolon
            picked = None
            for sep in (",",";"):
                try:
                    with open(p, newline="", encoding="utf-8") as f:
                        r = csv.DictReader(f, delimiter=sep)
                        collected = list(r)
                        if r.fieldnames:
                            fieldnames = [h.strip() for h in r.fieldnames]
                            picked = (fieldnames, collected)
                            break
                except Exception:
                    continue
            if not picked:
                continue
            fieldnames, collected = picked
            for h in fieldnames:
                if h not in headers_set:
                    headers_set.add(h)
                    headers_order.append(h)
            for row in collected:
                row = {k: (v if v is not None else "") for k,v in row.items()}
                row["__source_file"] = str(p.resolve())
                row["__source_doc"]  = p.parent.name
                rows.append(row)
        except Exception:
            continue

    for col in ["__source_file","__source_doc"]:
        if col not in headers_set:
            headers_set.add(col)
            headers_order.append(col)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers_order)
        w.writeheader()
        for row in rows:
            for k in headers_order:
                row.setdefault(k, "")
            w.writerow(row)
    return out_csv

def merge_academic_csvs(run_dir: Path, merged_filename: str = DEFAULT_MERGED_NAME) -> Path:
    run_dir = Path(run_dir)
    out_dir = run_dir / "merged"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / merged_filename
    csv_paths = find_academic_csvs(run_dir)
    if not csv_paths:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            f.write("NOTE,No academic CSVs found in this run\n")
        return out_csv
    if _HAS_PANDAS:
        return _merge_with_pandas(csv_paths, out_csv)
    else:
        return _merge_with_stdlib(csv_paths, out_csv)
