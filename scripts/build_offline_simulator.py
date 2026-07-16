from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "simulator/operational_scenario_simulator.html"
target = ROOT / "simulator/operational_scenario_simulator_offline.html"

if not source.exists():
    raise RuntimeError("Ejecuta primero scripts/build_simulator.py")
html = source.read_text(encoding="utf-8")
if "Plotly está incrustado" not in html or "PLOTLY_START" not in html:
    raise RuntimeError("El simulador principal no es autosuficiente")
target.write_text(html, encoding="utf-8")
print(target, target.stat().st_size)
