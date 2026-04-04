"""
Data Ingestion: Platform Webhook Simulator
Simulates delivery volume data from platforms like Swiggy/Zomato
"""
import random

ZONE_BASELINES = {
    "HYD_500001": [980, 1020, 1050, 990, 1010, 1030, 970, 1000],
    "BLR_560001": [850, 890, 910, 870, 900, 880, 920, 895],
    "MUM_400001": [1100, 1080, 1120, 1090, 1070, 1110, 1060, 1095],
    "CHN_600001": [780, 800, 820, 790, 810, 795, 815, 800],
    "VZG_530001": [620, 640, 660, 630, 650, 635, 645, 640],
    "DEL_110001": [1200, 1180, 1220, 1190, 1210, 1195, 1205, 1200],
    "KOL_700001": [900, 920, 910, 930, 905, 915, 925, 915],
    "PUN_411001": [700, 720, 710, 730, 705, 715, 725, 715],
}


def get_zone_baseline(zone_id: str) -> list:
    return ZONE_BASELINES.get(zone_id, [800, 820, 810, 830, 800, 815, 825, 810])


def simulate_current_week_volume(zone_id: str, disruption_factor: float = 1.0) -> dict:
    """
    Simulate this week's delivery volume.
    disruption_factor=1.0 → normal week
    disruption_factor=0.3 → 70% drop (major disruption)
    """
    baseline = get_zone_baseline(zone_id)
    baseline_avg = round(sum(baseline) / len(baseline))
    normal_volume = baseline_avg + random.randint(-50, 50)
    current_deliveries = max(10, round(normal_volume * disruption_factor))
    volume_drop_pct = round((1 - disruption_factor) * 100, 1)
    anomaly_flag = disruption_factor < 0.7

    return {
        "zone_id": zone_id,
        "baseline_avg": baseline_avg,
        "baseline_history": baseline,
        "current_deliveries": current_deliveries,
        "volume_drop_pct": volume_drop_pct,
        "anomaly_flag": anomaly_flag,
        "disruption_factor": disruption_factor,
    }
