from __future__ import annotations

import numpy as np
import pandas as pd


CONTROLLABILITY = {
    "WEATHER": 0.25,
    "TECHNICAL": 0.90,
    "PORT_CONGESTION": 0.75,
    "LATE_BOARDING": 0.85,
    "CREW": 0.90,
    "SUPPLY_ISSUE": 0.70,
}


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["completed"] = ~out["canceled"]
    out["positive_delay_min"] = out["delay_min"].clip(lower=0)
    out["operational_reliability"] = out["on_time_15"].astype(bool)
    out["attributed_disruption"] = out["disruption_reason"].ne("NONE")
    out["rotation_impacted"] = out.get("propagated_delay_min", 0).fillna(0).gt(0)
    out["margin_per_passenger_eur"] = np.where(
        out["passengers"] > 0, out["margin_eur"] / out["passengers"], np.nan
    )
    out["cost_per_passenger_eur"] = np.where(
        out["passengers"] > 0, out["total_cost_eur"] / out["passengers"], np.nan
    )
    return out


def executive_kpis(df: pd.DataFrame) -> pd.DataFrame:
    completed = df.loc[df["completed"]]
    scheduled = len(df)
    completed_n = len(completed)
    canceled_n = int(df["canceled"].sum())
    return pd.DataFrame(
        [
            {
                "scheduled_services": scheduled,
                "completed_services": completed_n,
                "canceled_services": canceled_n,
                "cancel_rate_pct": round(100 * canceled_n / scheduled, 2) if scheduled else np.nan,
                "otr_5_completed_pct": round(completed["on_time_5"].mean() * 100, 2),
                "otr_15_completed_pct": round(completed["on_time_15"].mean() * 100, 2),
                "operational_reliability_pct": round(df["on_time_15"].mean() * 100, 2),
                "avg_departure_delay_min": round(completed["delay_min"].mean(), 2),
                "p95_departure_delay_min": round(completed["delay_min"].quantile(0.95), 2),
                "avg_arrival_delay_min": round(completed["arrival_delay_min"].mean(), 2),
                "avg_occupancy_pct": round(completed["occupancy"].mean() * 100, 2),
                "rotation_impacted_services": int(completed.get("rotation_impacted", False).sum()),
                "rotation_impacted_pct": round(completed.get("rotation_impacted", False).mean() * 100, 2),
                "total_propagated_delay_min": round(completed.get("propagated_delay_min", pd.Series(dtype=float)).sum(), 2),
                "total_delay_cost_eur": round(completed["delay_cost_eur"].sum(), 2),
                "total_margin_eur": round(df["margin_eur"].sum(), 2),
            }
        ]
    )


def route_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    all_services = (
        df.groupby("route_id")
        .agg(
            scheduled_services=("operation_id", "count"),
            completed_services=("completed", "sum"),
            canceled_services=("canceled", "sum"),
            cancel_rate_pct=("canceled", lambda s: 100 * s.mean()),
            operational_reliability_pct=("on_time_15", lambda s: 100 * s.mean()),
            avg_margin_eur=("margin_eur", "mean"),
            total_margin_eur=("margin_eur", "sum"),
            total_cancellation_cost_eur=("cancellation_cost_eur", "sum"),
        )
        .reset_index()
    )
    completed = (
        df.loc[df["completed"]]
        .groupby("route_id")
        .agg(
            otr_15_completed_pct=("on_time_15", lambda s: 100 * s.mean()),
            avg_delay_min=("delay_min", "mean"),
            p95_delay_min=("delay_min", lambda s: s.quantile(0.95)),
            avg_arrival_delay_min=("arrival_delay_min", "mean"),
            avg_occupancy_pct=("occupancy", lambda s: 100 * s.mean()),
            avg_margin_completed_eur=("margin_eur", "mean"),
            total_delay_cost_eur=("delay_cost_eur", "sum"),
            rotation_impacted_pct=("rotation_impacted", lambda s: 100 * s.mean()),
            propagated_delay_min=("propagated_delay_min", "sum"),
        )
        .reset_index()
    )
    result = all_services.merge(completed, on="route_id", how="left")
    result["status"] = np.select(
        [
            (result["operational_reliability_pct"] < 85) | (result["cancel_rate_pct"] >= 2),
            (result["operational_reliability_pct"] < 90) | (result["cancel_rate_pct"] >= 1),
        ],
        ["RED", "AMBER"],
        default="GREEN",
    )
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].round(2)
    status_order = pd.Categorical(result["status"], categories=["RED", "AMBER", "GREEN"], ordered=True)
    return result.assign(_status_order=status_order).sort_values(
        ["_status_order", "operational_reliability_pct", "avg_delay_min"],
        ascending=[True, True, False],
    ).drop(columns="_status_order")


def vessel_rotation_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby(["vessel_id", "vessel_type"])
        .agg(
            scheduled_services=("operation_id", "count"),
            completed_services=("completed", "sum"),
            cancel_rate_pct=("canceled", lambda s: 100 * s.mean()),
            avg_delay_min=("delay_min", "mean"),
            p95_delay_min=("delay_min", lambda s: s.quantile(0.95)),
            rotation_impacted_pct=("rotation_impacted", lambda s: 100 * s.mean()),
            total_propagated_delay_min=("propagated_delay_min", "sum"),
            avg_scheduled_gap_min=("scheduled_gap_min", "mean"),
            total_margin_eur=("margin_eur", "sum"),
        )
        .reset_index()
    )
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].round(2)
    return result.sort_values(
        ["total_propagated_delay_min", "p95_delay_min"], ascending=False
    )


def cause_pareto(df: pd.DataFrame, include_unattributed: bool = False) -> pd.DataFrame:
    completed = df.loc[df["completed"]].copy()
    if not include_unattributed:
        completed = completed.loc[completed["disruption_reason"].ne("NONE")]
    result = (
        completed.groupby("disruption_reason")
        .agg(
            services=("operation_id", "count"),
            total_delay_min=("positive_delay_min", "sum"),
            avg_delay_min=("delay_min", "mean"),
            p95_delay_min=("delay_min", lambda s: s.quantile(0.95)),
            total_delay_cost_eur=("delay_cost_eur", "sum"),
        )
        .reset_index()
        .sort_values("total_delay_min", ascending=False)
    )
    total = result["total_delay_min"].sum()
    result["delay_share_pct"] = np.where(total > 0, 100 * result["total_delay_min"] / total, 0)
    result["cumulative_share_pct"] = result["delay_share_pct"].cumsum()
    result["controllability_score"] = result["disruption_reason"].map(CONTROLLABILITY).fillna(0)
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].round(2)
    return result


def delay_attribution_summary(df: pd.DataFrame) -> pd.DataFrame:
    completed = df.loc[df["completed"]].copy()
    completed["delay_attribution"] = np.where(
        completed["disruption_reason"].eq("NONE"), "UNATTRIBUTED / NORMAL VARIABILITY", "ATTRIBUTED CAUSE"
    )
    result = (
        completed.groupby("delay_attribution")
        .agg(
            services=("operation_id", "count"),
            total_delay_min=("positive_delay_min", "sum"),
            avg_delay_min=("delay_min", "mean"),
            total_delay_cost_eur=("delay_cost_eur", "sum"),
        )
        .reset_index()
    )
    total = result["total_delay_min"].sum()
    result["delay_share_pct"] = np.where(total > 0, 100 * result["total_delay_min"] / total, 0)
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].round(2)
    return result.sort_values("total_delay_min", ascending=False)


def _minmax(series: pd.Series) -> pd.Series:
    minimum = series.min()
    maximum = series.max()
    if pd.isna(minimum) or pd.isna(maximum) or np.isclose(maximum, minimum):
        return pd.Series(0.0, index=series.index)
    return (series - minimum) / (maximum - minimum)


def hotspots(df: pd.DataFrame, min_services: int = 15) -> pd.DataFrame:
    completed = df.loc[df["completed"] & df["disruption_reason"].ne("NONE")].copy()
    result = (
        completed.groupby(["route_id", "hour", "disruption_reason"])
        .agg(
            services=("operation_id", "count"),
            total_delay_min=("positive_delay_min", "sum"),
            avg_delay_min=("delay_min", "mean"),
            p95_delay_min=("delay_min", lambda s: s.quantile(0.95)),
            otr_15_pct=("on_time_15", lambda s: 100 * s.mean()),
            total_delay_cost_eur=("delay_cost_eur", "sum"),
            propagated_delay_min=("propagated_delay_min", "sum"),
        )
        .reset_index()
    )
    result = result.loc[result["services"] >= min_services].copy()
    if result.empty:
        return result

    result["reliability_gap_pct"] = (90 - result["otr_15_pct"]).clip(lower=0)
    result["controllability_score"] = result["disruption_reason"].map(CONTROLLABILITY).fillna(0)
    impact = (
        0.35 * _minmax(result["total_delay_min"])
        + 0.20 * _minmax(result["p95_delay_min"])
        + 0.25 * _minmax(result["reliability_gap_pct"])
        + 0.20 * _minmax(result["total_delay_cost_eur"])
    )
    result["impact_index_0_100"] = 100 * impact
    result["actionability_index_0_100"] = result["impact_index_0_100"] * (
        0.40 + 0.60 * result["controllability_score"]
    )
    result["priority"] = pd.cut(
        result["actionability_index_0_100"],
        bins=[-np.inf, 40, 70, np.inf],
        labels=["LOW", "MEDIUM", "HIGH"],
    ).astype(str)
    numeric = result.select_dtypes("number").columns
    result[numeric] = result[numeric].round(2)
    return result.sort_values(
        ["actionability_index_0_100", "impact_index_0_100"], ascending=False
    )


def scenarios(df: pd.DataFrame) -> pd.DataFrame:
    completed = df.loc[df["completed"]]
    by_reason = completed.groupby("disruption_reason").agg(
        delay_min=("positive_delay_min", "sum"),
        delay_cost_eur=("delay_cost_eur", "sum"),
    )
    total_delay = completed["positive_delay_min"].sum()
    definitions = [
        ("WEATHER -10%", {"WEATHER": 0.10}),
        ("TECHNICAL -10%", {"TECHNICAL": 0.10}),
        ("WEATHER y TECHNICAL -10%", {"WEATHER": 0.10, "TECHNICAL": 0.10}),
        ("PORT_CONGESTION -10%", {"PORT_CONGESTION": 0.10}),
        ("PROPAGACIÓN DE ROTACIONES -20%", {"ROTATION_PROPAGATION": 0.20}),
    ]
    rows = []
    for name, reductions in definitions:
        saved_delay = 0.0
        saved_cost = 0.0
        for reason, reduction in reductions.items():
            if reason == "ROTATION_PROPAGATION":
                propagated = completed["propagated_delay_min"].sum()
                saved_delay += propagated * reduction
                per_min_cost = completed["delay_cost_eur"].sum() / max(completed["positive_delay_min"].sum(), 1)
                saved_cost += propagated * reduction * per_min_cost
            elif reason in by_reason.index:
                saved_delay += by_reason.loc[reason, "delay_min"] * reduction
                saved_cost += by_reason.loc[reason, "delay_cost_eur"] * reduction
        rows.append(
            {
                "scenario": name,
                "assumption": "Reducción proporcional hipotética; no es una predicción causal",
                "delay_saved_min": round(saved_delay, 2),
                "delay_saved_pct": round(100 * saved_delay / total_delay, 2) if total_delay else 0,
                "direct_delay_cost_saved_eur": round(saved_cost, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("delay_saved_pct", ascending=False)
