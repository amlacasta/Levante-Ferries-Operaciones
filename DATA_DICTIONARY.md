# Diccionario de datos

Cada fila representa un **servicio programado**. Los datos son completamente sintéticos.

## Identificación y planificación

- `operation_id`: identificador único del servicio.
- `route_id`: código origen-destino.
- `origin`, `destination`: puertos ficticios/codificados.
- `vessel_id`: buque físico ficticio asignado al servicio.
- `vessel_type`: categoría FAST, ECO o RO_PAX.
- `rotation_sequence`: posición del servicio dentro de la secuencia anual del buque.
- `previous_operation_id`: servicio anterior del mismo buque.
- `turnaround_min`: tiempo mínimo programado de escala y preparación.
- `scheduled_gap_min`: minutos entre el final programado anterior y la siguiente salida.
- `schedule_conflict_flag`: control de calidad; debe ser falso en la base entregada.
- `scheduled_start`, `scheduled_end`: horarios programados.
- `actual_start`, `actual_end`: horarios reales; vacíos en cancelaciones.
- `scheduled_duration_min`: duración planificada.

## Contexto

- `weather`: CALM, WINDY, ROUGH o STORM.
- `disruption_reason`: causa principal o `NONE` cuando no existe una causa atribuida.
- `maintenance_flag`: indicador sintético de intervención o contexto de mantenimiento.
- `season`: LOW, SHOULDER o HIGH.
- `hour`, `month`, `weekday`: atributos temporales.

## Operación

- `base_delay_min`: retraso generado antes de considerar la rotación del buque.
- `propagated_delay_min`: retraso adicional heredado del servicio anterior.
- `delay_min`: retraso final de salida; vacío si se cancela.
- `arrival_delay_min`: retraso de llegada.
- `on_time_5`, `on_time_15`: puntualidad según umbral; una cancelación no cuenta como puntual.
- `canceled`: indicador de cancelación.
- `capacity_pax`, `passengers`, `occupancy`: capacidad y demanda.

## Economía

- `avg_ticket_eur`, `revenue_eur`: precio e ingresos.
- `fuel_cost_eur`, `crew_cost_eur`, `port_fees_eur`: costes base.
- `maintenance_cost_eur`: coste de mantenimiento.
- `delay_cost_eur`: coste incremental del retraso.
- `cancellation_cost_eur`: coste de cancelación y reubicación.
- `total_cost_eur`, `margin_eur`: coste total y margen.

## Variables enriquecidas

- `completed`: servicio no cancelado.
- `positive_delay_min`: retraso de salida truncado a cero para agregaciones.
- `operational_reliability`: servicio completado dentro de 15 minutos; las cancelaciones cuentan como incumplimiento.
- `attributed_disruption`: existe una causa distinta de `NONE`.
- `rotation_impacted`: el servicio ha heredado retraso de la rotación anterior.
- `margin_per_passenger_eur`, `cost_per_passenger_eur`: ratios unitarios.
