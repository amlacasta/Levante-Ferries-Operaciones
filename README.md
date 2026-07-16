# Levante-Ferries: Operaciones

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-lightgrey)
![Operations](https://img.shields.io/badge/Use%20Case-Operations%20Analytics-green)
![Fleet](https://img.shields.io/badge/Flota-30%20buques-blueviolet)
![Control Tower](https://img.shields.io/badge/Control%20Tower-Operational-orange)
![Simulator](https://img.shields.io/badge/Simulator-Plotly.js-brightgreen)
![Tests](https://img.shields.io/badge/Tests-9%20passed-success)
![Status](https://img.shields.io/badge/Status-Portfolio%20Project-success)

Sistema reproducible de **control operativo, fiabilidad y eficiencia económica** para una red ficticia de ferries.

El proyecto simula **12.000 servicios**, ocho rutas y una flota de **30 buques físicos ficticios**. A partir de esos datos construye KPIs, scorecards de rutas y buques, análisis de causas, hotspots, escenarios de sensibilidad, un simulador HTML y una presentación ejecutiva.

> Los datos son completamente sintéticos y no representan la operación real de ninguna compañía.

---

## Simulador interactivo

- [Abrir simulador online](simulator/operational_scenario_simulator.html)
- [Abrir simulador offline](simulator/operational_scenario_simulator_offline.html)
- [Abrir presentación ejecutiva](deliverables/Proyecto_Control_Operativo_Ferries.pptx)

El simulador permite modificar demanda, precio, meteorología, incidencias técnicas, congestión portuaria y costes de implementación. Recalcula puntualidad, ocupación, margen y resultados por ruta.

---

## Resumen ejecutivo

| Indicador | Resultado |
|---|---:|
| Servicios programados | 12.000 |
| Servicios completados | 11.886 |
| Servicios cancelados | 114 |
| Cancel Rate | 0,95% |
| OTR ≤ 5 min — completados | 62,43% |
| OTR ≤ 15 min — completados | 89,06% |
| Fiabilidad operacional | 88,22% |
| Delay medio de salida | 6,59 min |
| P95 delay de salida | 23,60 min |
| Ocupación media | 55,54% |
| Servicios afectados por rotación | 944 |
| Retraso propagado | 8.914,8 min |
| Coste total del retraso | 3,52 M€ |
| Margen total simulado | 243,71 M€ |

Los focos principales aparecen en las rutas **BCN–PMI**, **BCN–IBZ**, **DEN–PMI** y **VAL–IBZ**, junto con causas como **WEATHER**, **TECHNICAL** y **PORT_CONGESTION**.

---

## Problema de negocio

En una red de ferries no basta con saber qué servicio salió tarde. Es necesario entender:

```text
qué rutas fallan + cuándo fallan + por qué fallan + cómo se propaga el retraso + cuánto impacta en negocio
```

El proyecto responde a preguntas como:

- ¿Cuál es la puntualidad de los servicios completados?
- ¿Cuál es la fiabilidad real cuando una cancelación cuenta como incumplimiento?
- ¿Qué rutas y buques concentran mayor riesgo?
- ¿Qué retrasos proceden de rotaciones anteriores?
- ¿Qué causas explican la mayor parte del impacto?
- ¿Qué hotspots son realmente accionables?
- ¿Qué escenarios ofrecen mayor ahorro potencial?

---

## Unidad de análisis

```text
1 fila = 1 servicio programado de ferry
```

Cada registro contiene planificación, ejecución, buque, rotación, meteorología, causa de disrupción, capacidad, pasajeros, ingresos, costes y margen.

Variables destacadas:

| Categoría | Variables |
|---|---|
| Identificación | `operation_id`, `route_id`, `origin`, `destination` |
| Flota | `vessel_id`, `vessel_type`, `rotation_sequence` |
| Rotaciones | `previous_operation_id`, `turnaround_min`, `propagated_delay_min` |
| Planificación | `scheduled_start`, `scheduled_end` |
| Ejecución | `actual_start`, `actual_end`, `delay_min`, `arrival_delay_min` |
| Estado | `completed`, `canceled`, `on_time_5`, `on_time_15` |
| Disrupción | `weather`, `disruption_reason`, `maintenance_flag` |
| Economía | `revenue_eur`, `total_cost_eur`, `delay_cost_eur`, `margin_eur` |

Consulta el detalle en [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

---

## Arquitectura

```text
configuración
    ↓
simulación reproducible
    ↓
flota física y rotaciones
    ↓
calidad y enriquecimiento
    ↓
KPIs y scorecards
    ↓
diagnóstico y escenarios
    ↓
gráficos + simulador + presentación
```

La generación de entregables está automatizada mediante **GitHub Actions**, por lo que los notebooks, gráficos, tablas, simuladores y presentación se reconstruyen desde una única fuente de verdad.

---

## Estructura del repositorio

```text
Levante-Ferries-Operaciones/
├── .github/workflows/       # Automatización de entregables
├── config/                  # Parámetros de simulación
├── data/                    # Datos generados localmente
├── notebooks/               # Análisis narrativo ejecutado
├── reports/
│   ├── figures/             # Visualizaciones
│   └── tables/              # Resultados analíticos
├── simulator/               # Simulador online y offline
├── deliverables/            # Presentación ejecutiva
├── scripts/                 # Pipeline y generadores
├── src/                     # Lógica de simulación y análisis
├── tests/                   # Pruebas automáticas
├── DATA_DICTIONARY.md
├── METHODOLOGY.md
├── requirements.txt
└── README.md
```

---

## KPIs principales

| KPI | Definición |
|---|---|
| Cancel Rate | Cancelados / servicios programados |
| OTR ≤ 5 | Completados con retraso máximo de 5 minutos / completados |
| OTR ≤ 15 | Completados con retraso máximo de 15 minutos / completados |
| Fiabilidad operacional | Servicios programados completados dentro de 15 minutos / programados |
| Average Delay | Media del retraso de salida de servicios completados |
| P95 Delay | Percentil 95 del retraso |
| Rotation Impact | Servicios que heredan retraso del viaje anterior |
| Occupancy | Pasajeros / capacidad |
| Margin | Ingresos − costes totales |

La separación entre **OTR de completados** y **fiabilidad sobre programados** evita que las cancelaciones desaparezcan del análisis.

---

## Flota y rotaciones

La versión mejorada utiliza 30 activos individuales:

- `FAST-01` a `FAST-10`
- `ECO-01` a `ECO-10`
- `ROPAX-01` a `ROPAX-10`

Reglas principales:

- no existen servicios programados solapados para un mismo buque;
- cada tipo de buque tiene un tiempo mínimo de escala;
- se registra el servicio anterior del activo;
- el retraso puede propagarse a la siguiente salida;
- las pruebas bloquean conflictos de programación.

Esta lógica permite analizar rutas y también activos concretos.

---

## Diagnóstico

### Rutas prioritarias

El scorecard combina servicios programados, completados, cancelaciones, OTR, fiabilidad, retraso, ocupación, margen y coste del retraso.

### Pareto de causas

El Pareto principal excluye `NONE` y analiza únicamente causas atribuidas. El retraso no atribuido se informa por separado.

### Hotspots

Los hotspots combinan:

- volumen;
- retraso total;
- P95;
- brecha de fiabilidad;
- coste económico;
- retraso propagado;
- controlabilidad de la causa.

Se generan dos indicadores: `impact_index_0_100` y `actionability_index_0_100`.

### Escenarios de sensibilidad

| Escenario | Ahorro estimado |
|---|---:|
| WEATHER + TECHNICAL −10% | 3.910,0 min |
| WEATHER −10% | 2.347,3 min |
| Propagación de rotaciones −20% | 1.783,0 min |
| TECHNICAL −10% | 1.562,7 min |
| PORT_CONGESTION −10% | 1.106,0 min |

Los escenarios son sensibilidades proporcionales, no predicciones causales.

---

## Reproducir el proyecto

### Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Pipeline completo

```bash
python scripts/run_pipeline.py
python scripts/build_simulator.py
python scripts/build_offline_simulator.py
python scripts/build_presentation.py
python scripts/create_notebooks.py
python scripts/execute_notebooks.py
python scripts/validate_notebooks.py
python -m pytest -q
```

Resultado esperado:

```text
9 passed
```

---

## Pruebas automáticas

Las pruebas verifican:

- integridad del dataset;
- identificadores únicos;
- pasajeros dentro de capacidad;
- reconciliación de programados, completados y cancelados;
- ausencia de solapamientos;
- coherencia de las rotaciones;
- denominadores de los KPIs;
- separación de `NONE` en el diagnóstico;
- consistencia del simulador.

---

## Recomendaciones operativas

1. Definir protocolos específicos para `WINDY`, `ROUGH` y `STORM`.
2. Priorizar mantenimiento preventivo en activos con mayor retraso propagado.
3. Revisar tiempos de escala y secuencias con baja capacidad de recuperación.
4. Coordinar ventanas portuarias en rutas y horas críticas.
5. Crear una Control Tower semanal con fiabilidad, OTR, cancelaciones, P95, costes, rotaciones y hotspots.

---

## Limitaciones

- datos, flota, rutas, meteorología, ingresos y costes sintéticos;
- ausencia de restricciones portuarias reales;
- escenarios no causales;
- simplificación de tiempos de recuperación;
- sin datos históricos reales para validación externa.

---

## Próximos pasos

- meteorología y operación reales;
- optimización de rotaciones;
- predicción de retrasos;
- forecasting de demanda;
- optimización de pricing;
- alertas automáticas;
- integración con Power BI o Streamlit;
- simulación avanzada de eventos discretos.

---

## Autor

**Álvaro Lacasta**  
Portfolio de Data Analytics aplicado a operaciones, transporte y toma de decisiones.
