
# SoK: O‑RAN Security — A Queryable Graph Database for Threat Analysis and Component–Interface Systematization

> Companion codebase for the WiSec26 submission **“SoK: O‑RAN Security — A Queryable Graph Database for Threat Analysis and Component‑Interface Systematization.”**  
> This repo provides a **GUI** for PDF analysis + a **pipeline** to normalize CSVs and **(re)populate** a local **Neo4j** graph.

---

## 🚀 Quick Start

```bash
# 1) Clone (anonymous 4open link)
git clone https://anonymous.4open.science/r/SOK-Oran-Security-2E90/
cd SOK-Oran-Security-2E90/

# 2) Python env (uv is recommended)
# If you don't have uv yet:
# curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
uv pip install -r requirements.txt

# 3) (Optional) LLM API key for the analysis step
export OPENAI_API_KEY="sk-...your key..."     # PowerShell: $env:OPENAI_API_KEY="..."
```

> The **Neo4j Desktop** database must be configured once (manually) before you can import graph data. See the section **Neo4j Setup (manual, first time)** below.

---

## 🧭 Repository Layout

```
.
├─ data/
│  └─ academic.csv               # master CSV the pipeline appends to
│  └─ components.csv             
│  └─ cves.csv               
│  └─ cwes.csv               
│  └─ government.csv               
│  └─ interfaces.csv               
│  └─ risks.csv               
│  └─ software.csv   
│  └─ threats.csv          
├─ graph_scripts/                # database population stack (runs as-is)
│  ├─ import_data.py             # main graph import script
│  ├─ drop_database.py           # wipes the graph
│  ├─ database.py                # connection credentials and driver init
│  ├─ helpers.py                 # helpers used by import scripts
│  └─ mapping.py                 # canonicalization of component/interface names
├─ runs/                         # (optional) analysis runs with per-paper CSVs
│  └─ <run_id>/...
├─ oran_gui.py                # GUI (LLM analysis + Next steps)
├─ oran_pipeline.py              # wrapper: append rows + run graph import
├─ oran_csv_utils.py             # tools to find/merge “academic” CSVs
└─ oran_merge_academics.py       # CLI to merge run CSVs (optional)
```

---

## 🧱 Neo4j Setup (manual, first time — required)

1. **Install Neo4j Desktop**  
   Download: <https://neo4j.com/download/>
2. **Create a Local DBMS**  
   - In Neo4j Desktop → **Add** → **Local DBMS**
   - **Version:** `5.26.8`  
   - **Password:** `securesecure`
   - Click **Create** and wait for provisioning
3. **Start & Open**  
   - Click **Start** to boot the DB  
   - Click **Open** to launch the visual browser (optional)

> You’ll continue starting/stopping the DB from **Neo4j Desktop**. The GUI only **updates** the graph; it does **not** manage the DB lifecycle.

---

## 🖥️ GUI Usage

Launch the GUI:

```bash
uv run python oran_gui.py
```

### 1) LLM — Analysis (top section)

Add PDFs (papers/specifications) and tune these options:

| Control | What it does |
|---|---|
| **Model** (`gpt-5`, `gpt-4.1`, `gpt-4o`) | Select the LLM backend. Use the strongest model available to you for best extraction quality. |
| **Strict schema prompts** | Enforces column/value normalization. Turn **on** to reduce drift in CSV headers and enumerations. |
| **Reasoning effort** (`low` / `medium` / `high`) | Trades latency for deeper extraction. `high` attempts more context consolidation. |
| **Verbosity** (`low` / `medium` / `high`) | Controls how verbose the LLM logs/explanations are. |
| **Output folder** | Where per‑paper CSVs are written (a **run** folder will be created inside). |
| **Analyze (LLM only)** | Runs the extraction. When it finishes successfully, “Next steps” buttons are enabled. |

> Set `OPENAI_API_KEY` in your shell prior to launch if you plan to use LLM analysis.

### 2) Next steps (graph update)

- **Select previous run…**  
  Choose a **run folder** (or directly a CSV within a run); the GUI will infer the run directory. The run must contain the CSVs you wish to integrate.

- **Pipeline mode**  
  Choose how to update the graph and master dataset:

| Mode | What happens |
|---|---|
| **append** | Appends rows from the selected run (all `*.csv` found recursively) into **`data/academic.csv`** (row‑wise de‑dup + header union). Then runs **`graph_scripts/import_data.py`** to load the graph. |
| **rebuild** | Runs **`graph_scripts/drop_database.py`** to wipe the DB, appends rows into **`data/academic.csv`**, then imports via **`graph_scripts/import_data.py`**. |
| **dry‑run** | No changes. Prints how many CSVs/rows would be appended and which master CSV would be used. Useful for previewing. |

- **Merge academic CSVs** (optional)  
  Creates `<run>/merged/academics_merged.csv` from all per‑paper CSVs. Helpful for quick inspection.

- **Run full graph pipeline**  
  Executes the chosen mode. The GUI shows the **tail of the import logs** (from `import_data.py`).

> The pipeline assumes the canonical master file is **`data/academic.csv`**. You can override via `ORAN_MASTER_CSV`, or change the data folder with `ORAN_DATA_DIR`.

---

## ⚙️ Configuration & Environment Variables

```bash
# LLM key (for analysis step)
export OPENAI_API_KEY="sk-...your key..."

# Optional: master CSV override (default is data/academic.csv)
export ORAN_MASTER_CSV="data/academic.csv"

# Optional: data directory override
export ORAN_DATA_DIR="data"

# Optional: hint to downstream scripts (usually set by the GUI)
export ORAN_RUN_DIR="runs/<your_run_folder>"
```

---

## 🧪 Command‑Line Alternatives (without GUI)

**Dry‑run preview:**

```bash
uv run python - <<'PY'
from oran_pipeline import run_full_pipeline
from pathlib import Path
print(run_full_pipeline(Path("runs/<your_run_folder>"), method="dry-run"))
PY
```

**Append rows + import:**

```bash
uv run python - <<'PY'
from oran_pipeline import run_full_pipeline
from pathlib import Path
print(run_full_pipeline(Path("runs/<your_run_folder>"), method="append"))
PY
```

**Rebuild graph:**

```bash
uv run python - <<'PY'
from oran_pipeline import run_full_pipeline
from pathlib import Path
print(run_full_pipeline(Path("runs/<your_run_folder>"), method="rebuild"))
PY
```

**Merge the run’s academic CSVs only:**

```bash
uv run python oran_merge_academics.py runs/<your_run_folder> --out academics_merged.csv
```

**Manual graph population (what the GUI automates for you):**

```bash
cd graph_scripts
uv run python drop_database.py         # optional
uv run python import_data.py           # or: python import_data.py
```

---

## 🧩 Notes on Data Handling

- The pipeline collects all `*.csv` under the selected **run** (recursively).
- When appending to **`data/academic.csv`** the pipeline performs:
  - **header union** (merges columns across inputs; missing values filled as empty strings), and
  - **row‑wise de‑duplication** (exact row match).  
  If you need a custom de‑dup key (e.g., `Name+Reference`), open an issue or update `oran_pipeline.py` accordingly.

---

## 🛠️ Troubleshooting

- **Neo4j connection fails**: ensure the DB is **started** in Desktop, credentials in `graph_scripts/database.py` match (**password:** `securesecure`), and Desktop version is **5.26.8**.  
- **No CSVs found**: ensure you select a folder that actually contains CSVs (recursively), or pick a CSV file inside the run.

## Prompt design and refinement

Our prompting strategy is corpus-aware and follows an iterative refinement process. We started from a minimal instruction set, inspected the systematic failure modes (missing fields, schema drift, malformed CSV/JSON), and then gradually layered on constraints and clarifications until the behavior stabilized. In the final iteration, we used OpenAI’s prompt optimizer to regularize the order of instructions, tighten format guarantees, and keep outputs compact under the chosen configuration (GPT-5, `reasoning.effort=medium`, `verbosity=low`).

Each prompt is tailored to a specific document family and schema:

- **O-RAN specifications and risk/threat tables**  
  We use strict, schema-restating prompts that repeat the canonical CSV header byte-for-byte, so that exported columns remain stable over time and across runs.

- **Academic PDFs**  
  We use a schema-enforced prompt that enumerates the allowed `Type` values, constrains component/interface tags to a controlled O-RAN vocabulary, and requires that every CSV row be backed by an explicit evidence quote in the accompanying `audit.jsonl` block.

- **Risk and Threat inventories**  
  Risks and threats are handled by two dedicated prompts to avoid label leakage between the two concepts. In practice, the model is already capable of extracting the correct set of risks (or threats) with a very simple instruction such as:

  > “Within the document I provided, there are structured entries for both risks and threats. For now, I only want the risks. Read the entire document and extract the structured information for all risks—every single one, not just a subset. Generate a complete CSV in English with the data, preserving the original structure. Do not include threats in the CSV.”

  This works well on the current O-RAN security specification and shows that the model can follow the conceptual distinction between risks and threats. However, across different revisions of the same O-RAN security documents we observed that the way risks and threats are tabulated changes (field names, column sets, and table layouts differ between versions). To ensure robustness to these format changes—and to future versions of the documents—we adopted more structured, schema-enforcing prompts that (i) map heterogeneous source headers onto a fixed canonical schema, and (ii) explicitly exclude out-of-scope rows (risk-only rows from the threat extractor and threat-only rows from the risk extractor).

Across all prompts, the model is instructed to **keep source values verbatim**, leave fields **blank rather than invented** when evidence is missing, normalize multi-line cells into a single line, and use controlled vocabularies only where an exact mapping exists. Where JSON is involved (e.g., the `audit.jsonl` block), we rely on structured model outputs to keep the format machine-checkable; CSV outputs are validated by a lightweight post-processor that enforces header correctness, column counts, required fields, and basic type checks.

This combination of corpus-specific prompting plus a thin validation layer ensures that the generated CSVs and JSONL files preserve the semantics of the original manual pipeline and can be fed directly into the existing graph-building code without further adaptation.


### Prompt 1 – Academic papers

```text
Developer: Begin with a concise checklist (3-7 bullets) of what you will do; keep items conceptual, not implementation-level.

Extract only first-party contributions from the provided PDF paper—specifically, what the paper’s authors themselves propose, implement, demonstrate, or empirically identify. Do not include facts from prior work merely cited or discussed; use only information present in the paper text (no web browsing).

Your output must consist of two fenced code blocks, in this order:

1. An academic.csv block with the exact header below
2. An audit.jsonl block, with one line per CSV row

If you find no valid rows, output only the header in the CSV block; the audit.jsonl block should be empty.

CSV Header (must match exactly and in order):
Name,Type,Description,Target Components / Interfaces,Affected Components / Interfaces,Reference

Scope & inclusion criteria:
- Include a row only if the authors introduce, implement, evaluate, or directly evidence a specific Attack, Defense, or Preventative Measure.
- Exclude baselines, background, or techniques merely referenced or restated from other work without new contribution or evidence.
- If there are multiple distinct contributions, output one row per contribution.

Field instructions:
- Name: concise (≤ 8 words); use the paper’s terminology if available. Otherwise, create a stable, descriptive label (no hype).
- Type: specify only one of {Attack, Defense, Preventative Measure} (use exact spelling).
- Description: ≤ 25 words; summarize the action and validation method. If applicable, append a tag: [Theory], [Code], or [Testbed].
- Target Components / Interfaces: comma-separated list of O-RAN Components/Interfaces directly involved, using canonical terms per the Translation Map if provided. Omit non-canonical terms if normalization is not possible.
- Affected Components / Interfaces: comma-separated list of assets shown to be impacted. If not stated, leave blank. Normalize as above.
- Reference: DOI or canonical URL from the paper text; if not present, leave blank.

Canonical vocabularies & normalization (if provided):
- Treat Components and Interfaces as closed lists where available. Use the provided Translation Map to normalize synonyms.
- Omit any item that cannot be mapped to a canonical value; do not guess.
- For non-O-RAN interfaces (e.g., 3GPP N2/NGAP), either leave the field blank or use 'External Components' if that exists in the component list.

Quality checks (before output):
- Evidence: Each row must be supported by explicit content in the paper.
- No invention: Leave cells blank if information is not directly supported. Do not infer CVEs, components, or interfaces.
- Vocabulary: Ensure all Target and Affected fields use normalized canonical terms where possible.
- CSV formatting: Print the header only once with 0 or more rows. If fields include commas or quotes, enclose them with "..." and escape quotes as "". Don’t add extra columns.

After producing your output, validate that each row in academic.csv is supported by an explicit quote and pointer in the audit.jsonl block. If validation fails, self-correct before returning final output.

Audit block: For each CSV row, add a corresponding audit.jsonl line with dataset="academic.csv", key="<Reference>|<Name>", source_pointer (e.g., page/section/figure), and an evidence_quote (≤ 40 words).

If no text from the paper is provided, output only the CSV header and an empty audit.jsonl block.

(Optional) Canonical Components:
O-Cloud, SMO, Non-RT RIC, Near-RT RIC, O-CU, O-DU, O-RU, UE, External Components. Consider also: xApps or others if relevant.

(Optional) Canonical Interfaces:
A1 Interface, O1 Interface, O2 Interface, E2 Interface, Y1 Interface, R1 Interface, E1 Interface, F1 Interface, Airlink, External Interfaces, Fronthaul Interface.

(Optional) Translation Map:
{"Near Real-Time RIC":"Near-RT RIC","OFH":"Fronthaul Interface","Open Fronthaul":"Fronthaul Interface","gNB DU":"O-DU","gNB CU":"O-CU"}

## Output Format
- Output two fenced code blocks in this order:

1. academic.csv

Name,Type,Description,Target Components / Interfaces,Affected Components / Interfaces,Reference
<zero or more rows, or only header if no data extracted>


2. audit.jsonl

{"dataset":"academic.csv","key":"<Reference>|<Name>","source_pointer":"p.X / §Y / Fig.Z","evidence_quote":"...≤40 words..."}
<one line per CSV row, or empty if no data extracted>


## Strict fence labeling (to help parsing)
Return only two fenced code blocks after the initial checklist.
Use code fences labeled exactly: ```academic.csv and ```audit.jsonl (lowercase).
Do not use ```csv or generic fences. Do not add extra text outside the two blocks.
```

### Prompt 2 – Risks

```text
Goal:
Read the entire document end-to-end (all sections, tables, appendices, figures, footnotes) and extract only the risks. Do not include threats (except an optional Threat ID reference if a risk row explicitly links to one).

Deliverable: Canonical CSV (exact header, exact order)
Produce a single UTF-8 CSV (comma separator, double-quote text fields, include header row, no BOM) in English with exactly these columns in this exact order (case & punctuation must match):
	1	Risk ID
	2	Threat ID
	3	Risk Title
	4	Risk Description
	5	Severity
	6	Likelihood
	7	Risk Level / Evaluation
	8	Impact Types
	9	Affected Assets
	10	Affected Components
	11	Vulnerabilities
	12	Notes / Comments

Exact header line (must match byte-for-byte):
Risk ID,Threat ID,Risk Title,Risk Description,Severity,Likelihood,Risk Level / Evaluation,Impact Types,Affected Assets,Affected Components,Vulnerabilities,Notes / Comments

What counts as a “risk”
A structured entry that evaluates potential loss/impact and includes at least one of: Severity, Likelihood, or overall Risk Level/Evaluation. Items that only describe threats (title/type/description) with no risk evaluation must be excluded.

Where to find risks
Parse every table/list that contains risk evaluations (e.g., “Risk Assessment”, “Risk Matrix”, “Risk Evaluation”), including continued tables and appendix tables. Do not stop after the first table.

Column mapping (force to canonical schema)
Map source headers to the canonical columns above. Treat these variants as equivalent:
	•	Risk ID ⇄ ID, RID, Item #
	•	Threat ID ⇄ TID, Reference Threat ID, Threat Ref
	•	Risk Title ⇄ Title, Name, Risk Item
	•	Risk Description ⇄ Description, Details, Summary
	•	Severity ⇄ Impact (severity), Impact Rating
	•	Likelihood ⇄ Probability, Occurrence Likelihood, Frequency
	•	Risk Level / Evaluation ⇄ Overall Risk, Risk Rating, Risk Score/Level, Evaluation
	•	Impact Types ⇄ Impact Type(s), Impact Category
	•	Affected Assets ⇄ Assets, Targets, Affected Systems
	•	Affected Components ⇄ Components, Sub-systems, Modules
	•	Vulnerabilities ⇄ Vulns, Weaknesses
	•	Notes / Comments ⇄ Notes, Comments, Rationale, Justification

Normalization & hygiene (to keep outputs homogeneous)
	•	Keep cell values verbatim (do not infer, translate scales, or recompute ratings).
	•	Translate non-English narrative text to English while preserving technical terms/acronyms.
	•	Trim whitespace; convert multi-line cells to a single line using ; as the separator.
	•	If a value is missing in the source, leave the canonical column blank. Do not fabricate IDs.
	•	If a risk row explicitly references a Threat ID, populate Threat ID; otherwise leave it blank.
	•	De-duplicate identical risks; keep a single row and prefer the most complete one.
	•	Ignore “rating legends,” “scales,” or color heatmap matrices unless they appear as actual risk rows.

Quality gates (must pass)
	•	The CSV contains every risk in the document (no sampling).
	•	The CSV has exactly 12 columns with the exact header above—no extra/renamed columns.
	•	Every row has at least Risk Title or Risk Description, and ≥1 of {Severity, Likelihood, Risk Level / Evaluation}.
	•	If no risks are found, output only the header row (no data rows).

Output constraints
	•	File encoding: UTF-8 (no BOM).
	•	Separator: comma (,). Text fields must be wrapped in double quotes.
	•	One CSV only; do not include threats or free-text summaries in the CSV.
	•	Do not reorder columns; do not change header capitalization or punctuation.
```

### Prompt 3 – Threats

```text
Goal
Read the entire document end-to-end (all sections, tables, appendices, figures, footnotes) and extract only the Threats. Exclude Risks entirely (rows that include ratings like Severity, Likelihood, Risk Level/Evaluation).

Deliverable: Canonical CSV (exact header, exact order)
Produce one UTF-8 CSV (comma separator, double-quote text fields, include header row, no BOM) in English with exactly these columns in this exact order (case/punctuation must match):

Exact header line (must match byte-for-byte):
Threat ID,Threat title,Threat agent,Vulnerability,Threatened Asset,Affected Components

What counts as a “Threat”
A structured entry describing a potential adverse action/event (e.g., a specific attack, abuse, or exploitation scenario), typically identified by a Threat ID and/or Threat title, often linked to a Vulnerability, Threatened Asset, and Affected Components.
Items that primarily evaluate risk (e.g., contain Severity, Likelihood, Risk Level/Score) are not Threats and must be excluded.

Where to find Threats
Parse every table/list that inventories threats (often titled “Threat Inventory,” “Threat Catalog,” “Threat List,” etc.). Include continued tables and appendix tables. Do not stop after the first table.

Column mapping (force to canonical schema)
Map source headers to the canonical columns below. Treat these variants as equivalent:
	•	Threat ID ⇄ ID, TID, Threat Ref, Reference ID, Item #
	•	Threat title ⇄ Threat, Title, Name, Threat Name, Scenario
	•	Threat agent ⇄ Threat Actor, Attacker, Adversary, Source, Actor
	•	Vulnerability ⇄ Vulnerabilities, Weakness, Weaknesses, CWE, Vuln Description
	•	Threatened Asset ⇄ Asset, Assets, Target, Affected Asset(s), Protected Resource
	•	Affected Components ⇄ Component(s), Subsystems, Modules, Interfaces, O-RAN Functions (e.g., SMO, O-Cloud, O-RU/O-DU/O-CU, Near-RT RIC, Non-RT RIC, E2/A1/O1)

Normalization & hygiene (to keep outputs homogeneous)
	•	Keep values verbatim from the document (do not infer, rewrite, or normalize taxonomies).
	•	Translate non-English narrative text to English while preserving technical terms/acronyms.
	•	Trim whitespace; convert multi-line cells to a single line using ; as the separator.
	•	If a source table includes extra fields (e.g., Threat type, Impact type, Mitigations, Controls), ignore them—only populate the six canonical columns.
	•	If a Threat appears in multiple places, merge into one row: keep the most complete ID/title and union multi-value fields (e.g., multiple assets/components) using ; within the same cell.
	•	If a value is missing in the source, leave the canonical column blank. Do not fabricate IDs or titles.

Quality gates (must pass)
	•	The CSV contains every Threat in the document (no sampling).
	•	The CSV has exactly 6 columns with the exact header above—no extra/renamed/reordered columns.
	•	Each row has at least one of {Threat ID, Threat title}.
	•	No Risk-only rows (those with Severity/Likelihood/Risk Level) are included.
	•	Multi-value cells are ; -separated; no newline characters in cells.

Output constraints
	•	Encoding: UTF-8 (no BOM). Separator: comma. Quote all text fields with double quotes.
	•	One CSV only; do not include narrative summaries or risk tables in the output.
	•	Preserve punctuation, capitalization, and IDs exactly as written in the source.
```


