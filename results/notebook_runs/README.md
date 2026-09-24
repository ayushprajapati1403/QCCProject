# Executed standalone notebooks (full mode)

The two standalone notebooks in `notebooks/colab/`, executed in full mode with `jupyter nbconvert` (4 processes), and
every file they wrote.

| Path | What it is |
|---|---|
| `QI_DMO_Colab_executed_full.ipynb` | `QI_DMO_Colab.ipynb` with all outputs: tables, figures, statistics and the summary. |
| `QI_MRFO_Colab_executed_full.ipynb` | `QI_MRFO_Colab.ipynb` with all outputs, including Part 3 (changing cloud). |
| `QI_DMO_results/full_run/`, `QI_MRFO_results/full_run/` | Everything each notebook saved: one CSV row per run (`*_runs.csv`), every table as CSV and in `all_tables.xlsx`, the figures (`*.png`), `settings.json` and `summary.txt`. |

**How they were made.** The only settings changed from the committed notebooks are `MODE = "full"` and
`N_WORKERS = 4`. Outside Colab the notebooks save to a local folder instead of Google Drive.
* **The runs** were made by earlier builds of the same notebooks, which resumed after two container restarts. Only
  texts, tables and figures changed since then, not the run code. A clean quick run with the same run code
  reproduced 176 of these runs bit for bit.
* **The executed copies** come from a last pass with the final notebooks. It read every saved run back, ran 0 new
  runs, and recomputed the tables, figures and summary.
* **Paths** printed in the outputs are those of the machine that ran them.

**Checks** (details in `docs/lab_log.md`, *Standalone QI-DMO and QI-MRFO notebooks*):
* Every run that also exists in a committed study is bit-identical to it: 1 100 of 1 100 QI-DMO runs, and 1 340 of
  1 340 checked QI-MRFO values (1 220 runs).
* The rest are new runs: 580 for QI-DMO and 820 for QI-MRFO.
* Summed run times: 3.25 h (QI-DMO, 1 680 runs) and 4.35 h (QI-MRFO, 2 040 runs).

These files are results and are not edited by hand. To run a notebook again without touching them, run it elsewhere
(for example on Colab), or set `RUN_NAME` in its Section 1 to a new folder name.
