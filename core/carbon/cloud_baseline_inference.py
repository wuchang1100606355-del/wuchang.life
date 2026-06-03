# 五常智慧雲｜Google Workspace 月度碳足跡反推雲端功耗基準
CARBON_FACTOR_KGCO2E_PER_KWH = 0.494

def infer_cloud_power_from_workspace_report(monthly_kgco2e: float = 1.05931, days: int = 31, carbon_factor: float = CARBON_FACTOR_KGCO2E_PER_KWH):
    monthly_kwh = monthly_kgco2e / carbon_factor if carbon_factor else 0
    daily_kgco2e = monthly_kgco2e / days
    daily_kwh = monthly_kwh / days
    hourly_kgco2e = daily_kgco2e / 24
    hourly_kwh = daily_kwh / 24
    average_watt = hourly_kwh * 1000

    return {
        "version": "Wuchang-CloudBaselineInference-v1",
        "source": "Google Workspace Admin Carbon Footprint monthly report",
        "monthly_kgco2e": round(monthly_kgco2e, 8),
        "carbon_factor_kgco2e_per_kwh": carbon_factor,
        "inferred_monthly_kwh": round(monthly_kwh, 8),
        "inferred_daily_kgco2e": round(daily_kgco2e, 8),
        "inferred_daily_kwh": round(daily_kwh, 8),
        "inferred_hourly_kgco2e": round(hourly_kgco2e, 8),
        "inferred_hourly_kwh": round(hourly_kwh, 8),
        "inferred_average_watt": round(average_watt, 4),
        "limitation": "This is monthly allocation inference, not real-time Google cloud power telemetry and not per-request measurement."
    }
