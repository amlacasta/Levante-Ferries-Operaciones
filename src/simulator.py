from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


ROUTES = pd.DataFrame(
    [
        ("DEN-IBZ", "DEN", "IBZ", 57, 135, 1.05, 0.95),
        ("DEN-FOR", "DEN", "FOR", 61, 150, 1.00, 0.90),
        ("DEN-PMI", "DEN", "PMI", 125, 300, 1.15, 1.05),
        ("VAL-IBZ", "VAL", "IBZ", 95, 315, 1.18, 1.12),
        ("VAL-PMI", "VAL", "PMI", 140, 450, 1.20, 1.15),
        ("BCN-PMI", "BCN", "PMI", 112, 450, 1.25, 1.18),
        ("BCN-IBZ", "BCN", "IBZ", 150, 540, 1.28, 1.22),
        ("MAH-BCN", "MAH", "BCN", 130, 420, 1.20, 1.10),
    ],
    columns=["route_id", "origin", "destination", "distance_nm", "duration_min", "fare_factor", "delay_factor"],
)

VESSEL_TYPES = pd.DataFrame(
    [
        ("FAST", 450, 1.25, 28.0, 35),
        ("ECO", 850, 0.95, 20.0, 45),
        ("RO_PAX", 1200, 1.10, 23.0, 60),
    ],
    columns=["vessel_type", "capacity_pax", "fuel_factor", "delay_cost_per_min", "turnaround_min"],
)

FLEET = pd.concat(
    [
        pd.DataFrame({"vessel_id": [f"FAST-{i:02d}" for i in range(1, 11)], "vessel_type": "FAST"}),
        pd.DataFrame({"vessel_id": [f"ECO-{i:02d}" for i in range(1, 11)], "vessel_type": "ECO"}),
        pd.DataFrame({"vessel_id": [f"ROPAX-{i:02d}" for i in range(1, 11)], "vessel_type": "RO_PAX"}),
    ],
    ignore_index=True,
).merge(VESSEL_TYPES, on="vessel_type", how="left")


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 42
    n_services: int = 12_000
    start_date: str = "2025-01-01"
    end_date: str = "2025-12-31"
    on_time_threshold_min: int = 15
    network_name: str = "Mediterranean Ferries Demo"

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SimulationConfig":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in values.items() if k in allowed})


def _weather(rng: np.random.Generator, months: np.ndarray) -> np.ndarray:
    result = []
    for month in months:
        if month in (11, 12, 1, 2, 3):
            probs = [0.43, 0.30, 0.20, 0.07]
        elif month in (6, 7, 8, 9):
            probs = [0.70, 0.21, 0.08, 0.01]
        else:
            probs = [0.58, 0.27, 0.12, 0.03]
        result.append(rng.choice(["CALM", "WINDY", "ROUGH", "STORM"], p=probs))
    return np.asarray(result)


def _reasons(rng: np.random.Generator, weather: np.ndarray, maintenance: np.ndarray) -> np.ndarray:
    reasons = []
    labels = ["NONE", "WEATHER", "TECHNICAL", "PORT_CONGESTION", "LATE_BOARDING", "CREW", "SUPPLY_ISSUE"]
    for w, maint in zip(weather, maintenance):
        if w == "STORM":
            probs = np.array([0.10, 0.57, 0.12, 0.10, 0.04, 0.04, 0.03])
        elif w == "ROUGH":
            probs = np.array([0.22, 0.35, 0.12, 0.14, 0.08, 0.05, 0.04])
        elif w == "WINDY":
            probs = np.array([0.42, 0.18, 0.11, 0.13, 0.08, 0.05, 0.03])
        else:
            probs = np.array([0.55, 0.03, 0.11, 0.13, 0.10, 0.05, 0.03])
        if maint:
            probs[0] -= 0.05
            probs[2] += 0.05
        reasons.append(rng.choice(labels, p=probs / probs.sum()))
    return np.asarray(reasons)


def _type_weights(duration_min: float) -> dict[str, float]:
    if duration_min <= 180:
        return {"FAST": 0.55, "ECO": 0.27, "RO_PAX": 0.18}
    if duration_min <= 360:
        return {"FAST": 0.24, "ECO": 0.40, "RO_PAX": 0.36}
    return {"FAST": 0.10, "ECO": 0.44, "RO_PAX": 0.46}


def _assign_fleet(rng: np.random.Generator, scheduled_start: pd.Series, scheduled_duration: np.ndarray) -> pd.DataFrame:
    n = len(scheduled_start)
    vessel_id = np.empty(n, dtype=object)
    vessel_type = np.empty(n, dtype=object)
    capacity = np.zeros(n, dtype=int)
    fuel_factor = np.zeros(n, dtype=float)
    delay_cost_per_min = np.zeros(n, dtype=float)
    turnaround_min = np.zeros(n, dtype=int)
    schedule_conflict = np.zeros(n, dtype=bool)

    next_available = {row.vessel_id: pd.Timestamp.min for row in FLEET.itertuples(index=False)}
    fleet_by_id = FLEET.set_index("vessel_id")
    order = np.argsort(scheduled_start.to_numpy())

    for pos in order:
        start = pd.Timestamp(scheduled_start.iloc[pos])
        available_ids = [vid for vid, available_at in next_available.items() if available_at <= start]
        if not available_ids:
            earliest = min(next_available, key=next_available.get)
            available_ids = [earliest]
            schedule_conflict[pos] = True

        candidates = fleet_by_id.loc[available_ids].copy()
        weights_by_type = _type_weights(float(scheduled_duration[pos]))
        type_counts = candidates["vessel_type"].value_counts().to_dict()
        weights = candidates["vessel_type"].map(lambda t: weights_by_type[t] / max(type_counts.get(t, 1), 1)).to_numpy(dtype=float)
        weights = weights / weights.sum()
        selected_id = rng.choice(candidates.index.to_numpy(), p=weights)
        selected = fleet_by_id.loc[selected_id]

        vessel_id[pos] = selected_id
        vessel_type[pos] = selected["vessel_type"]
        capacity[pos] = int(selected["capacity_pax"])
        fuel_factor[pos] = float(selected["fuel_factor"])
        delay_cost_per_min[pos] = float(selected["delay_cost_per_min"])
        turnaround_min[pos] = int(selected["turnaround_min"])
        next_available[selected_id] = start + pd.to_timedelta(float(scheduled_duration[pos]), unit="m") + pd.to_timedelta(int(selected["turnaround_min"]), unit="m")

    return pd.DataFrame({
        "vessel_id": vessel_id,
        "vessel_type": vessel_type,
        "capacity_pax": capacity,
        "fuel_factor": fuel_factor,
        "delay_cost_per_min": delay_cost_per_min,
        "turnaround_min": turnaround_min,
        "schedule_conflict_flag": schedule_conflict,
    })


def _apply_rotation_propagation(
    scheduled_start: pd.Series,
    scheduled_duration: np.ndarray,
    actual_duration: np.ndarray,
    base_delay: np.ndarray,
    canceled: np.ndarray,
    reason: np.ndarray,
    vessel_id: np.ndarray,
    turnaround_min: np.ndarray,
    operation_id: np.ndarray,
) -> dict[str, Any]:
    n = len(scheduled_start)
    final_delay = base_delay.copy()
    propagated_delay = np.zeros(n, dtype=float)
    actual_start = pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    actual_end = pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    previous_operation_id = np.full(n, None, dtype=object)
    rotation_sequence = np.zeros(n, dtype=int)
    scheduled_gap_min = np.full(n, np.nan, dtype=float)

    work = pd.DataFrame({
        "pos": np.arange(n),
        "vessel_id": vessel_id,
        "scheduled_start": scheduled_start.to_numpy(),
        "scheduled_duration": scheduled_duration,
    }).sort_values(["vessel_id", "scheduled_start", "pos"])

    for _, group in work.groupby("vessel_id", sort=False):
        previous_ready: pd.Timestamp | None = None
        previous_scheduled_end: pd.Timestamp | None = None
        previous_op: str | None = None
        for seq, row in enumerate(group.itertuples(index=False), start=1):
            pos = int(row.pos)
            start = pd.Timestamp(row.scheduled_start)
            scheduled_end = start + pd.to_timedelta(float(scheduled_duration[pos]), unit="m")
            rotation_sequence[pos] = seq
            previous_operation_id[pos] = previous_op
            if previous_scheduled_end is not None:
                scheduled_gap_min[pos] = (start - previous_scheduled_end).total_seconds() / 60

            inherited = 0.0
            if previous_ready is not None:
                inherited = max(0.0, (previous_ready - start).total_seconds() / 60)
            if not canceled[pos]:
                original = float(base_delay[pos])
                final_delay[pos] = max(original, inherited)
                propagated_delay[pos] = max(0.0, final_delay[pos] - original)
                start_actual = start + pd.to_timedelta(final_delay[pos], unit="m")
                end_actual = start_actual + pd.to_timedelta(float(actual_duration[pos]), unit="m")
                actual_start.iloc[pos] = start_actual
                actual_end.iloc[pos] = end_actual
                previous_ready = end_actual + pd.to_timedelta(int(turnaround_min[pos]), unit="m")
            else:
                final_delay[pos] = np.nan
                extra_recovery = 120 if reason[pos] == "TECHNICAL" else 0
                previous_ready = scheduled_end + pd.to_timedelta(int(turnaround_min[pos]) + extra_recovery, unit="m")

            previous_scheduled_end = scheduled_end
            previous_op = str(operation_id[pos])

    return {
        "delay": final_delay,
        "propagated_delay": propagated_delay,
        "actual_start": actual_start,
        "actual_end": actual_end,
        "previous_operation_id": previous_operation_id,
        "rotation_sequence": rotation_sequence,
        "scheduled_gap_min": scheduled_gap_min,
    }


def simulate_operations(config: SimulationConfig = SimulationConfig()) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed)
    n = config.n_services

    start = pd.Timestamp(config.start_date)
    end = pd.Timestamp(config.end_date)
    days = (end - start).days + 1
    dates = start + pd.to_timedelta(rng.integers(0, days, n), unit="D")
    hours = rng.choice(np.arange(6, 23), n, p=np.array([3, 4, 5, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6, 5, 4, 3]) / 99)
    minutes = rng.choice([0, 15, 30, 45], n, p=[0.45, 0.20, 0.20, 0.15])
    scheduled_start = pd.Series(dates + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m"))

    route_idx = rng.choice(len(ROUTES), n, p=[0.17, 0.14, 0.12, 0.13, 0.12, 0.12, 0.10, 0.10])
    route = ROUTES.iloc[route_idx].reset_index(drop=True)
    scheduled_duration = route["duration_min"].to_numpy(dtype=float)
    fleet = _assign_fleet(rng, scheduled_start, scheduled_duration)

    vessel_type = fleet["vessel_type"].to_numpy()
    capacity = fleet["capacity_pax"].to_numpy(dtype=int)
    month = scheduled_start.dt.month.to_numpy()
    high_season = np.isin(month, [6, 7, 8, 9])
    low_season = np.isin(month, [11, 12, 1, 2, 3])
    season = np.where(high_season, "HIGH", np.where(low_season, "LOW", "SHOULDER"))
    weather = _weather(rng, month)
    maintenance = rng.random(n) < (0.045 + 0.035 * low_season + 0.02 * (vessel_type == "RO_PAX"))
    reason = _reasons(rng, weather, maintenance)

    weather_demand = pd.Series(weather).map({"CALM": 0.02, "WINDY": -0.02, "ROUGH": -0.10, "STORM": -0.25}).to_numpy()
    hour_demand = np.where(np.isin(hours, [8, 9, 17, 18, 19]), 0.05, 0.0)
    base_occ = 0.52 + 0.20 * high_season - 0.07 * low_season + weather_demand + hour_demand
    occupancy = np.clip(base_occ + rng.normal(0, 0.10, n), 0.12, 0.98)
    passengers = np.maximum(10, np.rint(capacity * occupancy).astype(int))

    fare = 55 * route["fare_factor"].to_numpy() * np.where(high_season, 1.22, np.where(low_season, 0.92, 1.0))
    fare *= 1 + 0.22 * (occupancy - 0.55)
    fare = np.clip(fare + rng.normal(0, 5, n), 25, 135)

    reason_severity = pd.Series(reason).map({
        "NONE": 0.4,
        "WEATHER": 1.7,
        "TECHNICAL": 1.9,
        "PORT_CONGESTION": 1.25,
        "LATE_BOARDING": 1.0,
        "CREW": 1.4,
        "SUPPLY_ISSUE": 1.3,
    }).to_numpy()
    weather_severity = pd.Series(weather).map({"CALM": 0.75, "WINDY": 1.0, "ROUGH": 1.45, "STORM": 2.4}).to_numpy()
    mean_delay = 5.5 * route["delay_factor"].to_numpy() * reason_severity * weather_severity * np.where(maintenance, 1.12, 1.0)
    base_delay = rng.gamma(shape=2.1, scale=np.maximum(mean_delay, 0.5) / 2.1)
    early = rng.random(n) < 0.12
    base_delay = np.maximum(-5, base_delay - early * rng.uniform(1, 5, n))

    cancel_prob = 0.004 + 0.07 * (weather == "STORM") + 0.025 * (reason == "TECHNICAL") + 0.012 * (reason == "CREW")
    canceled = rng.random(n) < cancel_prob
    base_delay = np.round(base_delay, 1)

    sailing_extension = scheduled_duration * pd.Series(weather).map({"CALM": 0.0, "WINDY": 0.03, "ROUGH": 0.10, "STORM": 0.22}).to_numpy()
    actual_duration = np.maximum(45, scheduled_duration + sailing_extension + rng.normal(0, 8, n))
    operation_id = np.asarray([f"OP{i:06d}" for i in range(1, n + 1)], dtype=object)
    rotation = _apply_rotation_propagation(
        scheduled_start=scheduled_start,
        scheduled_duration=scheduled_duration,
        actual_duration=actual_duration,
        base_delay=base_delay,
        canceled=canceled,
        reason=reason,
        vessel_id=fleet["vessel_id"].to_numpy(),
        turnaround_min=fleet["turnaround_min"].to_numpy(dtype=int),
        operation_id=operation_id,
    )
    delay = np.round(rotation["delay"], 1)
    recovery = np.minimum(np.nan_to_num(delay, nan=0) * rng.uniform(0.05, 0.25, n), 20)
    arrival_delay = np.maximum(-5, np.nan_to_num(delay, nan=0) + actual_duration - scheduled_duration - recovery)
    arrival_delay[canceled] = np.nan

    scheduled_end = scheduled_start + pd.to_timedelta(scheduled_duration, unit="m")
    actual_start = rotation["actual_start"]
    actual_end = rotation["actual_end"]

    revenue = passengers * fare
    revenue[canceled] = 0
    fuel = route["distance_nm"].to_numpy() * 19.0 * fleet["fuel_factor"].to_numpy() * (1 + 0.10 * (weather == "ROUGH") + 0.25 * (weather == "STORM"))
    crew = (scheduled_duration / 60) * (620 + 90 * (vessel_type == "RO_PAX"))
    port_fees = 2600 + 4.5 * capacity + rng.normal(0, 250, n)
    maintenance_cost = np.where(maintenance, rng.normal(2200, 450, n), 0)
    delay_cost = np.nan_to_num(np.maximum(delay, 0), nan=0) * (fleet["delay_cost_per_min"].to_numpy() + 0.05 * passengers)
    cancellation_cost = np.where(canceled, 0.35 * passengers * fare + 0.4 * port_fees, 0)
    total_cost = fuel + crew + port_fees + maintenance_cost + delay_cost + cancellation_cost
    margin = revenue - total_cost

    df = pd.DataFrame({
        "operation_id": operation_id,
        "route_id": route["route_id"],
        "origin": route["origin"],
        "destination": route["destination"],
        "vessel_id": fleet["vessel_id"],
        "vessel_type": vessel_type,
        "rotation_sequence": rotation["rotation_sequence"],
        "previous_operation_id": rotation["previous_operation_id"],
        "turnaround_min": fleet["turnaround_min"],
        "scheduled_gap_min": np.round(rotation["scheduled_gap_min"], 1),
        "schedule_conflict_flag": fleet["schedule_conflict_flag"],
        "scheduled_start": scheduled_start,
        "actual_start": actual_start,
        "scheduled_end": scheduled_end,
        "actual_end": actual_end,
        "scheduled_duration_min": scheduled_duration.astype(int),
        "base_delay_min": base_delay,
        "propagated_delay_min": np.round(rotation["propagated_delay"], 1),
        "delay_min": delay,
        "arrival_delay_min": np.round(arrival_delay, 1),
        "on_time_5": (~canceled) & (np.nan_to_num(delay, nan=999) <= 5),
        "on_time_15": (~canceled) & (np.nan_to_num(delay, nan=999) <= config.on_time_threshold_min),
        "canceled": canceled,
        "weather": weather,
        "disruption_reason": reason,
        "maintenance_flag": maintenance,
        "season": season,
        "capacity_pax": capacity,
        "passengers": passengers,
        "occupancy": np.round(occupancy, 3),
        "avg_ticket_eur": np.round(fare, 2),
        "revenue_eur": np.round(revenue, 2),
        "fuel_cost_eur": np.round(fuel, 2),
        "crew_cost_eur": np.round(crew, 2),
        "port_fees_eur": np.round(port_fees, 2),
        "maintenance_cost_eur": np.round(maintenance_cost, 2),
        "delay_cost_eur": np.round(delay_cost, 2),
        "cancellation_cost_eur": np.round(cancellation_cost, 2),
        "total_cost_eur": np.round(total_cost, 2),
        "margin_eur": np.round(margin, 2),
    })
    df["month"] = df["scheduled_start"].dt.month
    df["weekday"] = df["scheduled_start"].dt.day_name()
    df["hour"] = df["scheduled_start"].dt.hour
    return df
