# Simulador HTML Plotly

El simulador se alimenta automáticamente de `executive_kpis.csv` y `route_scorecard.csv`.

## Abrir el simulador

- [Simulador renderizado](https://raw.githack.com/amlacasta/Levante-Ferries-Operaciones/gh-pages/index.html)
- [GitHub Pages](https://amlacasta.github.io/Levante-Ferries-Operaciones/)

GitHub no ejecuta HTML desde la vista `blob`. Para usarlo localmente, descarga `operational_scenario_simulator_offline.html` y ábrelo con un navegador.

## Regeneración

```bash
python scripts/run_pipeline.py
python scripts/build_simulator.py
python scripts/build_offline_simulator.py
```

Ambos archivos contienen Plotly incrustado y funcionan sin conexión.
