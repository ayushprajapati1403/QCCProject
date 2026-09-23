"""The committed research notebooks must be exactly what notebooks/build/build_notebook.py generates from src/."""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOKS = ["quantum_inspired_cloud_scheduler.ipynb", "quantum_inspired_MRFO_cloud_scheduler.ipynb"]


def build_into(tmp_path, builder):
    """Run notebooks/build/<builder> with --root tmp_path (a copy of src/), so the committed notebooks are not touched."""
    os.makedirs(tmp_path / "src", exist_ok=True)
    for f in ["qi_core.py", "qi_quantum.py", "qi_dynamic.py"]:
        shutil.copy(os.path.join(ROOT, "src", f), tmp_path / "src" / f)
    subprocess.run([sys.executable, os.path.join(ROOT, "notebooks", "build", builder), "--root", str(tmp_path)],
                   check=True, capture_output=True)


def test_notebooks_match_builder(tmp_path):
    build_into(tmp_path, "build_notebook.py")
    for nb in NOTEBOOKS:
        built = json.load(open(tmp_path / "notebooks" / "research" / nb, encoding="utf-8"))
        committed = json.load(open(os.path.join(ROOT, "notebooks", "research", nb), encoding="utf-8"))
        assert built == committed, f"{nb} is out of sync with the modules: run `python notebooks/build/build_notebook.py`"
