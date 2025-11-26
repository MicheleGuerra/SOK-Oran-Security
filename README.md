
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


