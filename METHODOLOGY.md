# Metodología, supuestos y límites

## 1. Simulación de red y flota

El proyecto genera servicios de una red ficticia de ocho rutas. La configuración general se encuentra en `config/simulation.json` y utiliza una semilla fija para reproducibilidad.

La versión mejorada incorpora **30 buques físicos ficticios**. Cada servicio se asigna a un activo disponible respetando duración programada, tiempo mínimo de escala, compatibilidad pedagógica y ausencia de solapamientos.

Después se ordenan los servicios de cada buque como una rotación. Cuando la finalización real del servicio anterior supera la disponibilidad prevista, el exceso se propaga a la siguiente salida mediante `propagated_delay_min`.

## 2. Demanda, incidencias y economía

La demanda depende de temporada, horario y clima. El clima modifica la probabilidad de incidencias, retraso, duración y cancelación. Las incidencias técnicas aumentan en presencia del indicador de mantenimiento.

El retraso base usa una distribución gamma para conservar una cola derecha. El resultado económico incluye ingresos por pasajeros, combustible, tripulación, tasas portuarias, mantenimiento, retrasos y cancelaciones.

## 3. Definiciones de servicio

- **OTR≤15 de completados:** porcentaje de servicios completados con retraso máximo de 15 minutos.
- **Fiabilidad operacional:** porcentaje de todos los programados que se completan y cumplen OTR≤15. Una cancelación cuenta como incumplimiento.

## 4. Diagnóstico

- El Pareto principal excluye `NONE`.
- El retraso no atribuido se informa por separado.
- Los hotspots combinan volumen, P95, brecha de fiabilidad y coste.
- La accionabilidad pondera el impacto por el grado de controlabilidad.
- Los escenarios son sensibilidades, no predicciones causales.

## 5. Límites

- No representa datos reales de ninguna naviera.
- No demuestra causalidad.
- No optimiza rutas, horarios ni dimensionamiento de flota.
- No estima demanda futura.
- Los costes, capacidades y relaciones son supuestos pedagógicos.
