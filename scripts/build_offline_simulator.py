from pathlib import Path

from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "simulator/operational_scenario_simulator.html"
target = ROOT / "simulator/operational_scenario_simulator_offline.html"

html = source.read_text(encoding="utf-8")
needle = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
if needle not in html:
    raise RuntimeError("No se ha encontrado la referencia CDN esperada")

offline = html.replace(needle, f"<script>\n{get_plotlyjs()}\n</script>", 1)
offline = offline.replace("Plotly se carga desde CDN", "Plotly está incrustado: funciona sin conexión")
target.write_text(offline, encoding="utf-8")
print(target, target.stat().st_size)
