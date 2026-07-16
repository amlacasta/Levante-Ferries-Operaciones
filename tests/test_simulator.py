import pandas as pd

from src.analysis import (
    cause_pareto,
    delay_attribution_summary,
    enrich,
    executive_kpis,
    hotspots,
    route_scorecard,
)
from src.simulator import SimulationConfig, simulate_operations


def sample(n_services: int = 700) -> pd.DataFrame:
    return simulate_operations(SimulationConfig(seed=7, n_services=n_services))


def test_reproducible() -> None:
    a = simulate_operations(SimulationConfig(seed=9, n_services=50))
    b = simulate_operations(SimulationConfig(seed=9, n_services=50))
    pd.testing.assert_frame_equal(a, b)


def test_integrity_rules() -> None:
    df = sample()
    assert len(df) == 700
    assert df["operation_id"].is_unique
    assert df["occupancy"].between(0, 1).all()
    assert (df["passengers"] <= df["capacity_pax"]).all()
    assert df.loc[df["canceled"], "actual_start"].isna().all()
    assert df.loc[~df["canceled"], "actual_start"].notna().all()
    assert not df["schedule_conflict_flag"].any()


def test_physical_vessels_do_not_overlap() -> None:
    df = sample(2_000)
    for _, group in df.groupby("vessel_id"):
        ordered = group.sort_values("scheduled_start")
        previous_ready = None
        for row in ordered.itertuples(index=False):
            if previous_ready is not None:
                assert row.scheduled_start >= previous_ready
            previous_ready = row.scheduled_end + pd.to_timedelta(row.turnaround_min, unit="m")


def test_rotation_fields_are_consistent() -> None:
    df = sample()
    first_rotation = df["rotation_sequence"].eq(1)
    assert df.loc[first_rotation, "previous_operation_id"].isna().all()
    assert (df["propagated_delay_min"].fillna(0) >= 0).all()
    assert (df["rotation_sequence"] >= 1).all()


def test_weather_reason_coherence() -> None:
    df = sample(2_000)
    calm_weather_events = df.loc[df["weather"] == "CALM", "disruption_reason"].eq("WEATHER").mean()
    storm_weather_events = df.loc[df["weather"] == "STORM", "disruption_reason"].eq("WEATHER").mean()
    assert storm_weather_events > calm_weather_events


def test_kpis_have_valid_rates_and_counts() -> None:
    enriched = enrich(sample())
    kpis = executive_kpis(enriched).iloc[0]
    assert kpis["scheduled_services"] == len(enriched)
    assert kpis["completed_services"] + kpis["canceled_services"] == kpis["scheduled_services"]
    for metric in [
        "cancel_rate_pct",
        "otr_5_completed_pct",
        "otr_15_completed_pct",
        "operational_reliability_pct",
        "rotation_impacted_pct",
    ]:
        assert 0 <= kpis[metric] <= 100
    assert kpis["otr_15_completed_pct"] >= kpis["otr_5_completed_pct"]
    assert kpis["operational_reliability_pct"] <= kpis["otr_15_completed_pct"]


def test_route_scorecard_reconciles_programmed_services() -> None:
    enriched = enrich(sample())
    score = route_scorecard(enriched)
    assert score["scheduled_services"].sum() == len(enriched)
    assert score["completed_services"].sum() == enriched["completed"].sum()
    assert score["canceled_services"].sum() == enriched["canceled"].sum()


def test_unattributed_delay_is_separated() -> None:
    enriched = enrich(sample())
    pareto = cause_pareto(enriched)
    attribution = delay_attribution_summary(enriched)
    assert "NONE" not in set(pareto["disruption_reason"])
    assert "UNATTRIBUTED / NORMAL VARIABILITY" in set(attribution["delay_attribution"])


def test_hotspots_are_actionable_and_attributed() -> None:
    result = hotspots(enrich(sample(2_000)), min_services=3)
    assert "NONE" not in set(result["disruption_reason"])
    assert result["impact_index_0_100"].between(0, 100).all()
    assert result["actionability_index_0_100"].between(0, 100).all()
