from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import (
    cause_pareto,
    delay_attribution_summary,
    enrich,
    executive_kpis,
    hotspots,
    route_scorecard,
    scenarios,
    vessel_rotation_scorecard,
)
from src.simulator import SimulationConfig, simulate_operations


def _ensure_directories() -> None:
    for relative in [
        "data/raw",
        "data/processed",
        "reports/tables",
        "reports/figures",
        "simulator",
        "deliverables",
    ]:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)


def _save_figures(outputs: dict) -> None:
    score = outputs["route_scorecard"].sort_values("avg_delay_min", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(score["route_id"], score["avg_delay_min"])
    ax.set(title="Retraso medio por ruta — datos sintéticos", ylabel="Minutos", xlabel="Ruta")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/route_delay.png", dpi=160)
    plt.close(fig)

    reliability = outputs["route_scorecard"].sort_values("operational_reliability_pct")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(reliability["route_id"], reliability["operational_reliability_pct"])
    ax.axvline(90, linestyle="--", linewidth=1)
    ax.set(
        title="Fiabilidad operacional por ruta — OTR≤15 sobre servicios programados",
        xlabel="Fiabilidad operacional (%)",
        ylabel="Ruta",
        xlim=(80, 100),
    )
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/route_reliability.png", dpi=160)
    plt.close(fig)

    pareto = outputs["cause_pareto"]
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(pareto["disruption_reason"], pareto["total_delay_min"])
    ax1.set(title="Pareto de retraso atribuible — datos sintéticos", ylabel="Minutos agregados")
    ax1.tick_params(axis="x", rotation=35)
    ax2 = ax1.twinx()
    ax2.plot(pareto["disruption_reason"], pareto["cumulative_share_pct"], marker="o")
    ax2.set(ylabel="Acumulado (%)", ylim=(0, 110))
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/cause_pareto.png", dpi=160)
    plt.close(fig)

    hotspot = outputs["hotspots"].head(12).sort_values("actionability_index_0_100")
    if not hotspot.empty:
        labels = hotspot["route_id"] + " · " + hotspot["hour"].astype(str).str.zfill(2) + "h · " + hotspot["disruption_reason"]
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.barh(labels, hotspot["actionability_index_0_100"])
        ax.set(title="Hotspots priorizados por impacto y controlabilidad", xlabel="Índice de accionabilidad (0–100)")
        fig.tight_layout()
        fig.savefig(ROOT / "reports/figures/hotspot_priority.png", dpi=160)
        plt.close(fig)

    vessels = outputs["vessel_rotation_scorecard"].head(12).sort_values("total_propagated_delay_min")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(vessels["vessel_id"], vessels["total_propagated_delay_min"])
    ax.set(title="Buques con mayor retraso propagado entre rotaciones", xlabel="Minutos propagados")
    fig.tight_layout()
    fig.savefig(ROOT / "reports/figures/vessel_propagation.png", dpi=160)
    plt.close(fig)


def main() -> None:
    _ensure_directories()
    config = SimulationConfig.from_dict(json.loads((ROOT / "config/simulation.json").read_text(encoding="utf-8")))
    raw = simulate_operations(config)
    enriched = enrich(raw)

    raw.to_csv(ROOT / "data/raw/ferry_operations_synthetic.csv", index=False)
    enriched.to_csv(ROOT / "data/processed/ferry_operations_enriched.csv", index=False)

    outputs = {
        "executive_kpis": executive_kpis(enriched),
        "route_scorecard": route_scorecard(enriched),
        "vessel_rotation_scorecard": vessel_rotation_scorecard(enriched),
        "cause_pareto": cause_pareto(enriched),
        "delay_attribution_summary": delay_attribution_summary(enriched),
        "hotspots": hotspots(enriched),
        "scenarios": scenarios(enriched),
    }
    for name, table in outputs.items():
        table.to_csv(ROOT / f"reports/tables/{name}.csv", index=False)

    _save_figures(outputs)

    print(outputs["executive_kpis"].to_string(index=False))
    print("Pipeline completado:", ROOT)


if __name__ == "__main__":
    main()
