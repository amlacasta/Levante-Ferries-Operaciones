# Simulador HTML Plotly

El simulador se alimenta automáticamente de:

- `reports/tables/executive_kpis.csv`
- `reports/tables/route_scorecard.csv`

Después de ejecutar el pipeline, regenérelo con:

```bash
python scripts/build_simulator.py
python scripts/build_offline_simulator.py
```

La versión online usa Plotly desde CDN. La versión offline incorpora la librería dentro del archivo.

## Controles

- Demanda.
- Precio.
- Severidad meteorológica.
- Reducción técnica.
- Mejora portuaria.
- Coste de implementación.

## Límite

Es una herramienta de sensibilidad sobre datos sintéticos, no un modelo causal validado.
