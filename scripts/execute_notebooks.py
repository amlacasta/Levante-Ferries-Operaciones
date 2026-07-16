from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]

for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    nb = nbformat.read(path, as_version=4)
    executor = ExecutePreprocessor(timeout=240, kernel_name="python3")
    executor.preprocess(nb, {"metadata": {"path": str(ROOT)}})
    nbformat.write(nb, path)
    print("Ejecutado", path.name)
