from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
errors = []
for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    nb = nbformat.read(path, as_version=4)
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]
    unexecuted = [i for i, cell in enumerate(code_cells) if cell.execution_count is None]
    error_outputs = [
        output
        for cell in code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    if unexecuted:
        errors.append(f"{path.name}: {len(unexecuted)} celdas sin ejecutar")
    if error_outputs:
        errors.append(f"{path.name}: {len(error_outputs)} errores guardados")
    print(f"{path.name}: {len(nb.cells)} celdas, {len(code_cells)} de código, ejecutado")

if errors:
    raise RuntimeError("\n".join(errors))
print("Notebooks validados")
