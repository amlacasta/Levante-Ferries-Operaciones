from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "simulator/operational_scenario_simulator.html"


def build_simulator() -> Path:
    kpi = pd.read_csv(ROOT / "reports/tables/executive_kpis.csv").iloc[0]
    routes = pd.read_csv(ROOT / "reports/tables/route_scorecard.csv")

    base = {
        "services": int(kpi["scheduled_services"]),
        "completed": int(kpi["completed_services"]),
        "cancel": float(kpi["cancel_rate_pct"]),
        "otr": float(kpi["otr_15_completed_pct"]),
        "delay": float(kpi["avg_departure_delay_min"]),
        "occupancy": float(kpi["avg_occupancy_pct"]),
        "margin": float(kpi["total_margin_eur"]),
    }
    exposure = {
        "DEN-IBZ": 0.95,
        "DEN-FOR": 0.90,
        "DEN-PMI": 1.05,
        "VAL-IBZ": 1.12,
        "VAL-PMI": 1.15,
        "BCN-PMI": 1.18,
        "BCN-IBZ": 1.22,
        "MAH-BCN": 1.10,
    }
    route_rows = []
    for row in routes.itertuples(index=False):
        route_rows.append(
            {
                "route": row.route_id,
                "services": int(row.scheduled_services),
                "otr": float(row.otr_15_completed_pct),
                "delay": float(row.avg_delay_min),
                "occ": float(row.avg_occupancy_pct),
                "margin": float(row.avg_margin_eur),
                "delayCost": float(row.total_delay_cost_eur),
                "exposure": float(exposure.get(row.route_id, 1.0)),
            }
        )

    html = SOURCE.read_text(encoding="utf-8")
    html = re.sub(r"const BASE=\{.*?\};", f"const BASE={json.dumps(base, ensure_ascii=False, separators=(',', ':'))};", html, count=1)
    html = re.sub(r"const ROUTES=\[.*?\];", f"const ROUTES={json.dumps(route_rows, ensure_ascii=False, separators=(',', ':'))};", html, count=1, flags=re.S)
    html = re.sub(
        r"Base = simulación validada de [\d\.]+ servicios\.",
        f"Base = simulación validada de {base['services']:,} servicios.".replace(",", "."),
        html,
        count=1,
    )
    html = html.replace("x.otr<65?'RED':x.otr<75?'AMBER':'GREEN'", "x.otr<85?'RED':x.otr<90?'AMBER':'GREEN'")
    SOURCE.write_text(html, encoding="utf-8")
    print(SOURCE)
    return SOURCE


if __name__ == "__main__":
    build_simulator()
