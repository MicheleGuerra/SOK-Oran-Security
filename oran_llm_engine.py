
# -*- coding: utf-8 -*-
"""
oran_llm_engine.py
------------------
LLM extraction engine for O-RAN security contributions.
Designed to be imported by the Tkinter GUI (oran_gui.py).

Key entry points:
- run_llm_extraction(file_path, doc_type, scope, options) -> (records, logs, runtime_sec)
- records_to_csv(records, *, doc_type, out_dir, base) -> [csv_paths]

Requirements:
  pip install openai pypdf pdfminer.six
"""

from __future__ import annotations
import os, io, re, csv, json, time, warnings
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# ----------------------------
# Config (overridable)
# ----------------------------
MAX_CONTEXT_CHARS = 180_000
MAX_OUTPUT_TOKENS = 8000
DEFAULT_MODEL = "gpt-5"

# ----------------------------
# Prompt
# ----------------------------
PROMPT = r"""Developer: Begin with a concise checklist (3-7 bullets) describing what you will do; keep items conceptual, not implementation-level.

Extract only first-party contributions from the provided PDF paper(s) about O-RAN security. You must identify concrete Attack, Defense, or Preventative Measures introduced, implemented, evaluated, or evidenced by the authors themselves. Use only information present in the paper text (no web browsing).

Your output must consist of two fenced code blocks, in this order:

1. An academic.csv block with the exact header below
2. An audit.jsonl block, with one line per CSV row

If you find no valid rows, output only the header in the CSV block; the audit.jsonl block should be empty.

CSV Header (must match exactly and in order):
Name,Type,Description,Target Components / Interfaces,Affected Components / Interfaces,Reference

Scope & inclusion criteria:
- Include a row only if the authors introduce, implement, evaluate, or empirically evidence a specific Attack, Defense, or Preventative Measure.
- Exclude baselines, background, or techniques merely referenced or restated from other work without new contribution or evidence.
- If there are multiple distinct contributions, output one row per contribution.

Field instructions:
- Name: concise (≤ 8 words); use the paper’s terminology if available. Otherwise, create a stable, descriptive label (no hype).
- Type: specify only one of {Attack, Defense, Preventative Measure} (use exact spelling).
- Description: ≤ 25 words; summarize the action and validation method. If applicable, append a tag: [Theory], [Code], or [Testbed].
- Target Components / Interfaces: comma-separated list of O-RAN canonical components/interfaces most directly acted upon (e.g., "A1, E2, SMO, Near-RT RIC"). Normalize to canonical O-RAN terms when clearly indicated. Omit non-canonical terms if normalization is not possible.
- Affected Components / Interfaces: comma-separated list of assets expected to be impacted. If not stated, leave blank. Normalize as above.
- Reference: DOI if present in text; else, leave blank.

Output format example (structure only; content is illustrative):

```academic.csv
Name,Type,Description,Target Components / Interfaces,Affected Components / Interfaces,Reference
E2 Subscription Flood,Attack,Exhausts E2 event handlers via adversarial subscriptions,Near-RT RIC; E2,Near-RT RIC; O-DU,10.1145/XXXX
RIC App Sandboxing,Defense,Constrain xApps via WASI sandboxing [Code],Near-RT RIC,,10.1109/XXXX
Secure A1 Policy,Preventative Measure,Restrict policy updates with signed tokens [Testbed],A1,Near-RT RIC;
```
```audit.jsonl
{"row":1,"evidence":"Figure 3; §4.2 describes attack rate; Table 2 shows success."}
{"row":2,"evidence":"§5.1 sandbox design; GitHub link; evaluation §6."}
{"row":3,"evidence":"Policy tokens §3; testbed details in §5."}
```

Now read the provided PDF text and produce the two-code-block output exactly as specified.
"""

# ----------------------------
# Data structures
# ----------------------------
@dataclass
class RunOptions:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    strict_prompt: bool = True
    reasoning_effort: str = "medium"  # low/medium/high
    verbosity: str = "low"            # low/medium/high

# ----------------------------
# PDF loading
# ----------------------------
def load_pdf_text(path: Path, *, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Load text from a PDF using pypdf first, then pdfminer.six as fallback."""
    text = ""
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        text = "\n".join(p.extract_text() or "" for p in r.pages)
    except Exception as e:
        warnings.warn(f"pypdf failed on {path.name}: {e}")
    if not text or len(text.strip()) < 32:
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(str(path))
        except Exception as e:
            raise RuntimeError(f"Could not extract text from PDF {path}: {e}")
    text = text or ""
    if len(text) > max_chars:
        text = text[:max_chars] + "\n…(truncated)…"
    return text

# ----------------------------
# LLM call
# ----------------------------
def call_llm(prompt: str, *, api_key: str, model: str, reasoning_effort: str, max_output_tokens: int = MAX_OUTPUT_TOKENS) -> str:
    """Call OpenAI responses API (>=1.0)."""
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("OpenAI SDK not available. Install with: pip install openai") from e

    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        raise RuntimeError("Missing OpenAI API key (set options.api_key or OPENAI_API_KEY).")

    extra = {}
    if reasoning_effort in {"low", "medium", "high"}:
        extra["reasoning"] = {"effort": reasoning_effort}

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You are a precise research assistant. Follow formatting instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        max_output_tokens=max_output_tokens,
        **extra,
    )
    parts = []
    for out in resp.output or []:
        if out.get("type") == "output_text":
            parts.append(out.get("content", ""))
    text = "".join(parts).strip()
    if not text:
        try:
            text = resp.output_text
        except Exception:
            pass
    if not text:
        raise RuntimeError("LLM returned empty content; check model/limits.")
    return text

# ----------------------------
# Response parsing
# ----------------------------
import re as _re

_BLOCK_RE = _re.compile(
    r"```academic\.csv\s*(?P<csv>.*?)\s*```\s*```audit\.jsonl\s*(?P<audit>.*?)\s*```",
    _re.IGNORECASE | _re.DOTALL,
)

def extract_blocks(llm_text: str):
    m = _BLOCK_RE.search(llm_text)
    if not m:
        m2 = _re.search(r"```academic\.csv\s*(?P<csv>.*?)\s*```", llm_text, _re.IGNORECASE | _re.DOTALL)
        csv_block = m2.group("csv") if m2 else ""
        audit_block = ""
    else:
        csv_block = m.group("csv") or ""
        audit_block = m.group("audit") or ""
    csv_text = csv_block.strip().replace("\r\n", "\n").replace("\r", "\n")
    audit_text = audit_block.strip().replace("\r\n", "\n").replace("\r", "\n")
    csv_lines = [ln for ln in csv_text.split("\n") if ln.strip() != ""]
    audit_lines = [ln for ln in audit_text.split("\n") if ln.strip() != ""]
    return csv_lines, audit_lines

def parse_academic_csv(csv_lines):
    import io, csv as _csv
    reader = _csv.reader(io.StringIO("\n".join(csv_lines)), delimiter=",", quotechar='"', escapechar="\\")
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], []
    header, body = rows[0], rows[1:]
    return header, body

def csv_rows_to_records(header, rows, *, doc_type: str, source: str):
    recs = []
    for i, r in enumerate(rows, start=1):
        row = {header[j]: (r[j] if j < len(r) else "") for j in range(len(header))}
        obj = {
            "ID": f"{source}-{i:03d}",
            "Name": row.get("Name", ""),
            "Type": row.get("Type", ""),
            "Description": row.get("Description", ""),
            "Target Components / Interfaces": row.get("Target Components / Interfaces", ""),
            "Affected Components / Interfaces": row.get("Affected Components / Interfaces", ""),
            "Reference": row.get("Reference", ""),
            "Source": source,
            "DocType": doc_type,
        }
        recs.append(obj)
    return recs

# ----------------------------
# Public API: run one file
# ----------------------------
def build_full_prompt(pdf_text: str, *, scope: str, strict: bool) -> str:
    preface = ""
    if scope and scope.lower() != "both (risks+threats)":
        preface = f"(Focus scope: {scope})\n"
    strict_hint = "Follow the CSV header exactly and emit only the required fields." if strict else "If unsure, still emit your best-effort rows."
    return f"{preface}{strict_hint}\n\n{PROMPT}\n\n---\nPDF Content (truncated if very long):\n{pdf_text}"

def run_llm_extraction(file_path: Path, doc_type: str, scope: str, options: RunOptions):
    t0 = time.time()
    pdf_text = load_pdf_text(file_path)
    full_prompt = build_full_prompt(pdf_text, scope=scope, strict=options.strict_prompt)
    llm_text = call_llm(full_prompt, api_key=options.api_key, model=options.model or DEFAULT_MODEL, reasoning_effort=options.reasoning_effort, max_output_tokens=MAX_OUTPUT_TOKENS)
    csv_lines, audit_lines = extract_blocks(llm_text)
    header, rows = parse_academic_csv(csv_lines)
    if not header and csv_lines:
        header = csv_lines[0].split(",")
        rows = [ln.split(",") for ln in csv_lines[1:]]
    source = file_path.stem
    records = csv_rows_to_records(header, rows, doc_type=doc_type, source=source)
    logs = [
        f"[LLM] file={file_path.name} scope={scope} model={options.model or DEFAULT_MODEL}",
        f"[LLM] prompt_chars={len(full_prompt):,} output_chars={len(llm_text):,} rows={len(records)}",
    ]
    if audit_lines:
        logs.append(f"[Audit] {len(audit_lines)} evidence rows captured.")
    runtime = time.time() - t0
    return records, "\\n".join(logs), runtime

# ----------------------------
# Validation
# ----------------------------
ACADEMIC_REQUIRED = ["Name", "Type", "Description", "Target Components / Interfaces"]

def validate_records(records, *, doc_type: str, strict: bool):
    errors = []
    req = ACADEMIC_REQUIRED
    for i, r in enumerate(records):
        for k in req:
            if k not in r or (isinstance(r[k], str) and not r[k].strip()):
                errors.append(f"record[{i}] missing/empty required field '{k}'")
    return (len(errors) == 0) or (not strict), errors

# ----------------------------
# CSV writer
# ----------------------------
ACADEMIC_COLUMNS = ["Name","Type","Description","Target Components / Interfaces","Affected Components / Interfaces","Reference"]

def records_to_csv(records, *, doc_type: str, out_dir: Path, base: str):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{base}.csv"
    import csv as _csv
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=ACADEMIC_COLUMNS)
        w.writeheader()
        for r in records:
            row = {k: r.get(k, "") for k in ACADEMIC_COLUMNS}
            w.writerow(row)
    return [csv_path]
