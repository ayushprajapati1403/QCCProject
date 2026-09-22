"""The committed notebooks must be exactly what build_notebook.py generates from the current modules."""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["qi_core.py", "qi_quantum.py", "qi_dynamic.py", "build_notebook.py"]
NOTEBOOKS = ["quantum_inspired_cloud_scheduler.ipynb", "quantum_inspired_MRFO_cloud_scheduler.ipynb"]


def test_notebooks_match_builder(tmp_path):
    for f in FILES:
        shutil.copy(os.path.join(ROOT, f), tmp_path / f)
    subprocess.run([sys.executable, "build_notebook.py"], cwd=tmp_path, check=True, capture_output=True)
    for nb in NOTEBOOKS:
        built = json.load(open(tmp_path / nb, encoding="utf-8"))
        committed = json.load(open(os.path.join(ROOT, nb), encoding="utf-8"))
        assert built == committed, f"{nb} is out of sync with the modules: run `python build_notebook.py`"
