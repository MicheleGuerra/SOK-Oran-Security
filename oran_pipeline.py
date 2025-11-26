
# -*- coding: utf-8 -*-
"""
oran_pipeline.py
----------------
Wrapper to update an existing Neo4j graph using your local scripts in ./graph_scripts.
Behavior:
- BEFORE importing to the graph, append the LLM output rows (academics) into a master CSV in ./data.
- Modes:
    * append  : append rows to master CSV, then run graph_scripts/import_data.py
    * rebuild : drop DB (graph_scripts/drop_database.py), then append rows, then import
    * dry-run : do not touch DB; summarize counts and show which master CSV would be used

Configuration:
- ORAN_RUN_DIR      : (set by GUI) path to the selected run with CSV outputs
- ORAN_MASTER_CSV   : override master CSV path; default auto-detect in ./data
- ORAN_DATA_DIR     : override data dir; default ./data
"""
from __future__ import annotations

import csv
import os
import sys
import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple, Optional

# Canonical academic columns seen in the extraction step (fallback if we need headers)
ACADEMIC_COLUMNS = [
    "Name","Type","Description",
    "Target Components / Interfaces","Affected Components / Interfaces","Reference"
]

def _count_csv_rows(run_dir: Path) -> Tuple[int,int]:
    files = 0
    rows = 0
    for p in Path(run_dir).rglob("*.csv"):
        files += 1
        # try comma then semicolon
        for sep in (",",";"):
            try:
                with open(p, newline='', encoding='utf-8') as f:
                    r = csv.reader(f, delimiter=sep)
                    rc = sum(1 for _ in r)
                    if rc:
                        rows += max(0, rc-1)
                        break
            except Exception:
                continue
    return files, rows

def _detect_master_csv(data_dir: Path) -> Path:
    # 1) env override
    env_csv = os.getenv("ORAN_MASTER_CSV")
    if env_csv:
        return Path(env_csv)

    # 2) prefer names including 'academic' or 'paper'
    candidates = list(data_dir.glob("*.csv"))
    for pat in ("academic","academics","paper","papers"):
        for p in candidates:
            if pat in p.name.lower():
                return p

    # 3) fallback default
    return data_dir / "academics.csv"

def _read_header(csv_path: Path) -> List[str]:
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            r = csv.reader(f)
            return next(r)  # type: ignore
    except Exception:
        return []

def _union_headers(existing: List[str], incoming: List[str]) -> List[str]:
    out = list(existing) if existing else []
    seen = set(h for h in out)
    for h in incoming:
        if h not in seen:
            out.append(h); seen.add(h)
    # ensure provenance cols at end if present
    for prov in ["__source_file","__source_doc"]:
        if prov in out:
            out.remove(prov); out.append(prov)
    return out if out else list(ACADEMIC_COLUMNS)

def _iter_run_rows(run_dir: Path) -> Tuple[List[str], List[dict]]:
    """Return (header, rows) from all CSVs under run_dir, concatenated."""
    headers_union: List[str] = []
    rows: List[dict] = []
    for p in Path(run_dir).rglob("*.csv"):
        # pick a separator
        sep = ","
        try_first = True
        for trial in (",",";"):
            try:
                with open(p, newline='', encoding='utf-8') as f:
                    r = csv.DictReader(f, delimiter=trial)
                    items = list(r)
                    if r.fieldnames:
                        header = [h.strip() for h in r.fieldnames]
                        headers_union = _union_headers(headers_union, header)
                        # normalize row values to strings
                        for row in items:
                            clean = {k: ("" if v is None else str(v)) for k,v in row.items()}
                            rows.append(clean)
                        break
            except Exception:
                continue
    if not headers_union:
        headers_union = list(ACADEMIC_COLUMNS)
    return headers_union, rows

def _append_to_master(master_csv: Path, headers: List[str], new_rows: List[dict]) -> Tuple[int,int]:
    """Ensure master exists with headers; append rows not already present.
    Returns (added, total_after).
    Dedup strategy: skip exact-duplicate row dicts (all columns equal)."""
    master_csv.parent.mkdir(parents=True, exist_ok=True)
    existing_rows: List[dict] = []
    existing_headers = []
    if master_csv.exists():
        existing_headers = _read_header(master_csv)
        # Refresh union of headers
        headers = _union_headers(existing_headers, headers)
        # Load existing for simple dedup
        try:
            with open(master_csv, newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                existing_rows = [{k: (v if v is not None else "") for k,v in row.items()} for row in r]
        except Exception:
            existing_rows = []

    # Build a set of serialized rows for quick dedup
    def _norm_row(row: dict, cols: List[str]) -> Tuple[str,...]:
        return tuple((row.get(c, "") or "").strip() for c in cols)

    seen = {_norm_row(r, headers) for r in existing_rows}
    to_add: List[dict] = []
    for r in new_rows:
        # fill missing keys
        for k in headers:
            r.setdefault(k, "")
        key = _norm_row(r, headers)
        if key not in seen:
            to_add.append(r); seen.add(key)

    total_after = len(existing_rows) + len(to_add)

    # Write back full file (simpler and safe)
    with open(master_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in existing_rows:
            # ensure all headers exist
            for k in headers:
                row.setdefault(k, "")
            w.writerow(row)
        for row in to_add:
            for k in headers:
                row.setdefault(k, "")
            w.writerow(row)

    return len(to_add), total_after

def run_full_pipeline(run_dir: Path, method: str = "append") -> str:
    run_dir = Path(run_dir).resolve()
    data_dir = Path(os.getenv("ORAN_DATA_DIR", "data")).resolve()
    master_csv = _detect_master_csv(data_dir)

    if method not in {"append","rebuild","dry-run"}:
        raise ValueError(f"Unknown method: {method}")

    # Prepare rows from the selected run
    headers, new_rows = _iter_run_rows(run_dir)

    if method == "dry-run":
        files, rows = _count_csv_rows(run_dir)
        return (
            f"[Dry-run] Would append ~{rows} rows from {files} CSV files\n"
            f"Target master CSV: {master_csv}"
        )

    # 1) Optional DB reset
    if method == "rebuild":
        # Run the drop script from graph_scripts without importing it
        subprocess.run([sys.executable, "-u", "drop_database.py"], cwd="graph_scripts", check=True)

    # 2) Append to master CSV inside ./data
    added, total = _append_to_master(master_csv, headers, new_rows)

    # 3) Import into Neo4j by calling graph_scripts/import_data.py
    env = dict(os.environ)
    env.setdefault("ORAN_RUN_DIR", str(run_dir))     # provided for downstream scripts if needed
    env.setdefault("ORAN_MASTER_CSV", str(master_csv))
    proc = subprocess.run([sys.executable, "-u", "import_data.py"], cwd="graph_scripts", env=env,
                          check=True, capture_output=True, text=True)
    tail_out = "\n".join(proc.stdout.splitlines()[-40:])
    tail_err = "\n".join(proc.stderr.splitlines()[-10:]) if proc.stderr else ""

    label = "Rebuilt" if method == "rebuild" else "Appended"
    summary = (
        f"[{label}] Added {added} new rows to master CSV (now {total} rows)\n"
        f"Master: {master_csv}\n"
        f"Run dir: {run_dir}\n"
        f"--- graph_scripts/import_data.py (tail) ---\n{tail_out}"
    )
    if tail_err:
        summary += f"\n[stderr]\n{tail_err}"
    return summary
