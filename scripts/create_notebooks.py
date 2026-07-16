from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(parents=True, exist_ok=True)


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


def save(name: str, cells: list) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["metadata"]["language_info"] = {"name": "python", "version": "3.11"}
    nbf.write(nb, NB_DIR / name)
    print("Creado", name)


save(
    "01_simulation.ipynb",
    [
        md("""# 01 — Simulación reproducible de ferries

## Pregunta de negocio
¿Cómo construir una base sintética que permita probar una torre de control sin utilizar datos confidenciales?

El notebook genera servicios, asigna buques físicos, construye rotaciones y valida que no existan solapamientos programados."""),
        md("""## Decisiones de modelado

- Una fila representa un servicio programado.
- La red incluye ocho rutas ficticias.
- La flota contiene 30 activos individuales.
- Cada activo necesita tiempo de escala.
- El retraso puede propagarse a la siguiente rotación.
- La semilla fija garantiza reproducibilidad."""),
        code("""from pathlib import Path
import json, sys
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
from src.simulator import FLEET, ROUTES, SimulationConfig, simulate_operations"""),
        code("""config = SimulationConfig.from_dict(json.loads((ROOT / 'config/simulation.json').read_text(encoding='utf-8')))
display(ROUTES)
display(FLEET.groupby('vessel_type').agg(buques=('vessel_id','count'), capacidad=('capacity_pax','first'), escala_min=('turnaround_min','first')))"""),
        code("""df = simulate_operations(config)
print(f'Servicios: {len(df):,}')
print(f'Buques: {df.vessel_id.nunique()}')
df.head()"""),
        md("## Controles de integridad"),
        code("""checks = {
    'operation_id único': df.operation_id.is_unique,
    'ocupación 0–1': df.occupancy.between(0,1).all(),
    'pasajeros ≤ capacidad': (df.passengers <= df.capacity_pax).all(),
    'cancelados sin hora real': df.loc[df.canceled, 'actual_start'].isna().all(),
    'sin conflictos programados': not df.schedule_conflict_flag.any(),
}
pd.Series(checks, name='resultado')"""),
        code("""completed = df.loc[~df.canceled]
fig, axes = plt.subplots(1,2,figsize=(12,4))
completed.delay_min.clip(upper=60).hist(bins=30, ax=axes[0])
axes[0].set(title='Distribución del retraso', xlabel='Minutos')
completed.occupancy.hist(bins=25, ax=axes[1])
axes[1].set(title='Distribución de ocupación', xlabel='Ocupación')
plt.tight_layout(); plt.show()"""),
        code("""summary = pd.Series({
    'servicios afectados': int((completed.propagated_delay_min > 0).sum()),
    'porcentaje afectado': 100 * (completed.propagated_delay_min > 0).mean(),
    'minutos propagados': completed.propagated_delay_min.sum(),
})
summary.round(2)"""),
        md("## Conclusión\nLa base representa activos físicos y secuencias operativas, no servicios independientes sin relación."),
        code("""out = ROOT / 'data/raw/ferry_operations_synthetic.csv'
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
out"""),
    ],
)


save(
    "02_operational_kpis.ipynb",
    [
        md("""# 02 — KPIs operativos y scorecards

## Pregunta de negocio
¿Qué rutas y buques muestran peor desempeño cuando las cancelaciones forman parte del denominador?"""),
        md("""## Definiciones

- **OTR≤15 de completados:** puntuales / completados.
- **Fiabilidad operacional:** puntuales / programados.
- **Cancel Rate:** cancelados / programados."""),
        code("""from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
from src.analysis import enrich, executive_kpis, route_scorecard, vessel_rotation_scorecard"""),
        code("""df = pd.read_csv(ROOT / 'data/raw/ferry_operations_synthetic.csv', parse_dates=['scheduled_start','actual_start','scheduled_end','actual_end'])
df = enrich(df)
print(df.shape)"""),
        code("""kpis = executive_kpis(df)
display(kpis.T.rename(columns={0:'valor'}))"""),
        code("""routes = route_scorecard(df)
cols = ['route_id','scheduled_services','completed_services','canceled_services','cancel_rate_pct','otr_15_completed_pct','operational_reliability_pct','avg_delay_min','p95_delay_min','avg_margin_eur','status']
display(routes[cols])"""),
        code("""plot_df = routes.sort_values('operational_reliability_pct')
ax = plot_df.plot(x='route_id', y=['otr_15_completed_pct','operational_reliability_pct'], kind='bar', figsize=(11,5), title='OTR frente a fiabilidad total')
ax.set_ylabel('%'); plt.xticks(rotation=35); plt.tight_layout(); plt.show()"""),
        code("""vessels = vessel_rotation_scorecard(df)
display(vessels.head(12))
vessels.head(12).sort_values('total_propagated_delay_min').plot(x='vessel_id', y='total_propagated_delay_min', kind='barh', figsize=(9,5), legend=False, title='Buques con mayor retraso propagado')
plt.xlabel('Minutos'); plt.tight_layout(); plt.show()"""),
        md("## Conclusión\nLa fiabilidad operacional ofrece una lectura más exigente que el OTR de completados porque incorpora cancelaciones."),
    ],
)


save(
    "03_diagnostics_scenarios.ipynb",
    [
        md("""# 03 — Diagnóstico, hotspots y escenarios

## Pregunta de negocio
¿Qué causas y combinaciones operativas concentran mayor impacto y cuáles son más accionables?"""),
        code("""from pathlib import Path
import sys
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))
from src.analysis import enrich, cause_pareto, delay_attribution_summary, hotspots, scenarios"""),
        code("""df = pd.read_csv(ROOT / 'data/raw/ferry_operations_synthetic.csv', parse_dates=['scheduled_start','actual_start','scheduled_end','actual_end'])
df = enrich(df)"""),
        code("""pareto = cause_pareto(df)
display(pareto)
ax = pareto.plot(x='disruption_reason', y='total_delay_min', kind='bar', figsize=(10,5), legend=False, title='Pareto de retraso atribuible')
ax.set_ylabel('Minutos'); plt.xticks(rotation=35); plt.tight_layout(); plt.show()"""),
        code("""display(delay_attribution_summary(df))"""),
        code("""hot = hotspots(df)
cols = ['route_id','hour','disruption_reason','services','p95_delay_min','otr_15_pct','total_delay_cost_eur','impact_index_0_100','actionability_index_0_100','priority']
display(hot[cols].head(15))"""),
        code("""display(scenarios(df))"""),
        code("""weather = df.loc[df.completed].groupby('weather').agg(servicios=('operation_id','count'), delay_medio=('delay_min','mean'), p95=('delay_min',lambda s:s.quantile(.95)), otr15=('on_time_15',lambda s:100*s.mean())).reset_index()
display(weather)
weather.plot(x='weather', y=['delay_medio','p95'], kind='bar', figsize=(9,5), title='Impacto de la meteorología')
plt.ylabel('Minutos'); plt.xticks(rotation=0); plt.tight_layout(); plt.show()"""),
        md("""## Conclusión

El Pareto separa causas atribuidas de variabilidad no atribuida. Los hotspots combinan impacto y controlabilidad, mientras que los escenarios deben interpretarse como sensibilidades y no como predicciones causales."""),
    ],
)
