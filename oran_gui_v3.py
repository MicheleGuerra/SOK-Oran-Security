
# -*- coding: utf-8 -*-
"""
O-RAN Security — LLM Extraction GUI (v3)
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import oran_llm_engine as engine
from oran_csv_utils import merge_academic_csvs
from oran_pipeline import run_full_pipeline

DEFAULT_OUTPUT_DIR = Path.cwd() / "outputs"

class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SOK: O-RAN Security — LLM Extraction GUI (v3)")
        self.geometry("1100x740")

        # State
        self._run_thread: Optional[threading.Thread] = None
        self._run_active: bool = False
        self.selected_run_dir: Optional[Path] = None

        # Vars
        self.api_key_var = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
        self.model_var   = tk.StringVar(value="gpt-5")
        self.strict_var  = tk.BooleanVar(value=True)
        self.effort_var  = tk.StringVar(value="medium")
        self.verb_var    = tk.StringVar(value="low")
        self.output_dir  = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.mode_var    = tk.StringVar(value="dry-run")  # moved to next steps
        self.api_show    = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        root.grid(row=0, column=0, sticky="nsew")

        # Left panel: documents list
        left = ttk.Frame(root)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Documents").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.docs_list = tk.Listbox(left, height=16)
        self.docs_list.grid(row=1, column=0, sticky="nsew", padx=8)
        ttk.Button(left, text="Add PDFs...", command=self._add_pdfs).grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        root.add(left, weight=1)

        # Right panel: LLM controls (top), log, next steps
        right = ttk.Frame(root)
        right.columnconfigure(0, weight=1)
        root.add(right, weight=3)

        # --- LLM section (TOP) ---
        llm = ttk.LabelFrame(right, text="LLM — Analysis")
        for c in range(8):
            llm.columnconfigure(c, weight=1 if c in (1,3,5,7) else 0)

        # API key + model row
        ttk.Label(llm, text="API key:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.api_entry = ttk.Entry(llm, textvariable=self.api_key_var, show="•")
        self.api_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=6)
        def _toggle():
            self.api_show.set(not self.api_show.get())
            self.api_entry.config(show="" if self.api_show.get() else "•")
            btn_show.config(text="Hide" if self.api_show.get() else "Show")
        btn_show = ttk.Button(llm, text="Show", command=_toggle)
        btn_show.grid(row=0, column=4, padx=6)
        ttk.Label(llm, text="Model:").grid(row=0, column=5, sticky="e", padx=6)
        ttk.Combobox(llm, textvariable=self.model_var, values=["gpt-5","gpt-4.1","gpt-4o"], state="readonly", width=14).grid(row=0, column=6, sticky="w", padx=6)

        # Strict + effort + verbosity row
        ttk.Checkbutton(llm, text="Strict schema prompts (fix columns/values)", variable=self.strict_var).grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=4)
        ttk.Label(llm, text="Reasoning effort:").grid(row=1, column=3, sticky="e", padx=6)
        ttk.Combobox(llm, textvariable=self.effort_var, values=["low","medium","high"], state="readonly", width=12).grid(row=1, column=4, sticky="w", padx=6)
        ttk.Label(llm, text="Verbosity:").grid(row=1, column=5, sticky="e", padx=6)
        ttk.Combobox(llm, textvariable=self.verb_var, values=["low","medium","high"], state="readonly", width=12).grid(row=1, column=6, sticky="w", padx=6)

        # Output + Analyze row
        ttk.Label(llm, text="Output folder:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(llm, textvariable=self.output_dir).grid(row=2, column=1, columnspan=4, sticky="ew", padx=6)
        ttk.Button(llm, text="Browse...", command=self._browse_output).grid(row=2, column=5, padx=6)
        btn_analyze = ttk.Button(llm, text="Analyze (LLM only)", command=self._on_run)
        btn_analyze.grid(row=2, column=6, sticky="e", padx=6)
        llm.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        # --- Log ---
        self.log = tk.Text(right, height=16, bg="#0c1a2b", fg="#d7e6ff")
        self.log.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        right.rowconfigure(1, weight=1)

        # --- Next steps (pipeline mode + previous runs + actions) ---
        next_box = ttk.LabelFrame(right, text="Next steps")
        for c in range(6):
            next_box.columnconfigure(c, weight=1 if c in (1,3,5) else 0)

        # Pipeline mode (moved here)
        ttk.Label(next_box, text="Pipeline mode:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        for i,(txt,val) in enumerate([("append","append"),("rebuild","rebuild"),("dry-run","dry-run")]):
            ttk.Radiobutton(next_box, text=txt, variable=self.mode_var, value=val).grid(row=0, column=i+1, sticky="w")

        # Previous run selector
        ttk.Label(next_box, text="Selected run:").grid(row=1, column=0, sticky="e", padx=6)
        self.sel_run_var = tk.StringVar(value="— none —")
        ttk.Label(next_box, textvariable=self.sel_run_var).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Button(next_box, text="Select previous run...", command=self._select_prev_run).grid(row=1, column=3, padx=6)

        # Actions
        self.btn_merge = ttk.Button(next_box, text="Merge academic CSVs", command=self._merge_csvs, state="disabled")
        self.btn_merge.grid(row=2, column=0, padx=6, pady=8, sticky="w")

        self.btn_graph = ttk.Button(next_box, text="Run full graph pipeline", command=self._run_graph, state="disabled")
        self.btn_graph.grid(row=2, column=1, padx=6, pady=8, sticky="w")

        ttk.Button(next_box, text="Reset", command=self._on_reset).grid(row=2, column=5, padx=6, pady=8, sticky="e")

        next_box.grid(row=2, column=0, sticky="ew", padx=8, pady=8)

    # ---------- callbacks ----------
    def _add_pdfs(self) -> None:
        files = filedialog.askopenfilenames(title="Select PDFs", filetypes=[("PDF","*.pdf")])
        for f in files:
            self.docs_list.insert(tk.END, f)

    def _browse_output(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_dir.get())
        if d:
            self.output_dir.set(d)

    def _set_selected_run(self, run_dir: Path) -> None:
        self.selected_run_dir = run_dir
        self.sel_run_var.set(str(run_dir))
        self.btn_merge.config(state="normal")
        self.btn_graph.config(state="normal")

    def _on_run(self) -> None:
        if self._run_active:
            return
        outdir = Path(self.output_dir.get())
        outdir.mkdir(parents=True, exist_ok=True)
        pdfs = [self.docs_list.get(i) for i in range(self.docs_list.size())]
        if not pdfs:
            messagebox.showwarning("No PDFs", "Please add one or more PDFs first.")
            return
        self._run_active = True
        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, "[Init] Starting LLM analysis...\n"); self.log.see(tk.END)
        t = threading.Thread(target=self._worker_run, args=(pdfs, outdir), daemon=True)
        t.start()
        self._run_thread = t

    def _worker_run(self, pdfs: List[str], outdir: Path) -> None:
        try:
            cfg = dict(
                api_key=self.api_key_var.get(),
                model=self.model_var.get(),
                effort=self.effort_var.get(),
                verbosity=self.verb_var.get(),
                strict=self.strict_var.get(),
                mode=self.mode_var.get(),
                output_dir=str(outdir),
            )
            self.log.insert(tk.END, f"[Config] {cfg}\n"); self.log.see(tk.END)
            run_dir = engine.run_llm_pipeline(pdfs, **cfg)
            self.log.insert(tk.END, f"[Done] LLM analysis finished. Results at: {run_dir}\n"); self.log.see(tk.END)
            self._set_selected_run(Path(run_dir))
        except Exception as e:
            self.log.insert(tk.END, f"[Error] {e}\n"); self.log.see(tk.END)
            messagebox.showerror("Run error", str(e))
        finally:
            self._run_active = False

    def _on_reset(self) -> None:
        self.docs_list.delete(0, tk.END)
        self.log.delete("1.0", tk.END)
        self.sel_run_var.set("— none —")
        self.selected_run_dir = None
        self.btn_merge.config(state="disabled")
        self.btn_graph.config(state="disabled")

    def _select_prev_run(self) -> None:
        # 1) Try selecting a FOLDER (preferred)
        d = filedialog.askdirectory(parent=self, title="Select a previous run folder", initialdir=self.output_dir.get(), mustexist=True)
        run_dir = None
        if d:
            run_dir = Path(d)
        else:
            # 2) Or let the user pick a CSV file from a previous run
            f = filedialog.askopenfilename(parent=self, title="Select a CSV from a previous run", initialdir=self.output_dir.get(),
                                           filetypes=[("CSV files","*.csv"), ("All files","*")])
            if f:
                run_dir = Path(f).parent

        if not run_dir:
            return

        # Basic validation: ensure there is at least one CSV inside
        csvs = list(run_dir.rglob("*.csv"))
        if not csvs:
            messagebox.showwarning("No CSVs found", f"No CSV files found in:\n{run_dir}\nSelect a run folder that contains LLM outputs.")
            return

        self._set_selected_run(run_dir)
        self.log.insert(tk.END, f"[Prev] Selected previous run: {run_dir}\n"); self.log.see(tk.END)

    def _merge_csvs(self) -> None:
        if not self.selected_run_dir:
            messagebox.showwarning("No run selected", "Run the LLM or select a previous run first.")
            return
        try:
            merged = merge_academic_csvs(self.selected_run_dir)
            self.log.insert(tk.END, f"[Merge] Created: {merged}\n"); self.log.see(tk.END)
            messagebox.showinfo("Merge complete", f"Academic CSVs merged into:\n{merged}")
        except Exception as e:
            self.log.insert(tk.END, f"[Error] Merge failed: {e}\n"); self.log.see(tk.END)
            messagebox.showerror("Merge failed", str(e))

    def _run_graph(self) -> None:
        if not self.selected_run_dir:
            messagebox.showwarning("No run selected", "Run the LLM or select a previous run first.")
            return
        try:
            summary = run_full_pipeline(self.selected_run_dir, method=self.mode_var.get())
            self.log.insert(tk.END, f"[Graph] {summary}\n"); self.log.see(tk.END)
            messagebox.showinfo("Graph pipeline", summary)
        except Exception as e:
            self.log.insert(tk.END, f"[Error] Graph pipeline failed: {e}\n"); self.log.see(tk.END)
            messagebox.showerror("Graph pipeline failed", str(e))

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
