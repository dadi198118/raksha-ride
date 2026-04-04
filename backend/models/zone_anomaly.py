"""
Module 2: Zone Anomaly Engine
Z-score for fast statistical detection + Isolation Forest for confirmation
Protects riders from being penalised for zone-wide external disruptions
"""
import numpy as np
from sklearn.ensemble import IsolationForest
import logging

logger = logging.getLogger(__name__)

# Isolation Forest trained on synthetic zone weekly data
_iso_forest = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

# Generate synthetic training data: [deliveries, rider_count, avg_order_val, weather_severity, cancellation_rate]
np.random.seed(42)
n_normal = 500
_normal_data = np.column_stack([
    np.random.normal(1000, 150, n_normal),   # deliveries
    np.random.normal(80, 10, n_normal),      # active riders
    np.random.normal(280, 40, n_normal),     # avg order value
    np.random.uniform(0, 1, n_normal),       # weather severity (0-1)
    np.random.uniform(0.02, 0.08, n_normal), # cancellation rate
])
n_anomaly = 25
_anomaly_data = np.column_stack([
    np.random.normal(300, 100, n_anomaly),   # low deliveries
    np.random.normal(30, 15, n_anomaly),     # few active riders
    np.random.normal(180, 50, n_anomaly),    # lower order values
    np.random.uniform(0.7, 1.0, n_anomaly),  # high weather severity
    np.random.uniform(0.20, 0.40, n_anomaly),# high cancellation rate
])
_train_data = np.vstack([_normal_data, _anomaly_data])
_iso_forest.fit(_train_data)


def compute_zone_delivery_index(
    zone_id: str,
    current_week_deliveries: int,
    baseline_history: list[int]
) -> dict:
    """
    Step 1: Z-score based Zone Delivery Index (ZDI)
    ZDI > 0.85  → normal week
    ZDI 0.60–0.85 → mild anomaly, investigate
    ZDI < 0.60  → significant anomaly, context adjustment applied
    """
    if not baseline_history or len(baseline_history) < 2:
        return {"zdi": 1.0, "z_score": 0.0, "status": "insufficient_history", "anomaly": False}

    baseline_mean = np.mean(baseline_history)
    baseline_std = np.std(baseline_history)

    if baseline_std == 0:
        baseline_std = 1.0

    z_score = float((current_week_deliveries - baseline_mean) / baseline_std)
    zdi = float(current_week_deliveries / baseline_mean) if baseline_mean > 0 else 1.0

    if zdi > 0.85:
        status = "normal"
        anomaly = False
    elif zdi > 0.60:
        status = "mild_anomaly"
        anomaly = True
    else:
        status = "significant_anomaly"
        anomaly = True

    return {
        "zone_id": zone_id,
        "zdi": round(zdi, 3),
        "z_score": round(z_score, 3),
        "status": status,
        "anomaly": anomaly,
        "baseline_mean": round(float(baseline_mean), 1),
        "current": current_week_deliveries
    }


def run_isolation_forest(
    total_deliveries: int,
    active_riders: int,
    avg_order_value: float,
    weather_severity: float,
    cancellation_rate: float
) -> dict:
    """
    Step 2: Isolation Forest on richer features for anomaly confirmation and classification.
    Returns anomaly score and whether it's an external cause.
    """
    features = np.array([[
        total_deliveries,
        active_riders,
        avg_order_value,
        weather_severity,
        cancellation_rate
    ]])

    prediction = _iso_forest.predict(features)[0]   # 1 = normal, -1 = anomaly
    score = _iso_forest.score_samples(features)[0]  # lower = more anomalous

    is_anomaly = prediction == -1

    # Infer likely cause from feature ratios
    cause = "unknown"
    if is_anomaly:
        if weather_severity > 0.7:
            cause = "extreme_weather"
        elif cancellation_rate > 0.20:
            cause = "platform_or_external_disruption"
        elif active_riders < 40:
            cause = "low_rider_availability"
        else:
            cause = "zone_level_disruption"

    return {
        "is_anomaly": is_anomaly,
        "isolation_score": round(float(score), 4),
        "likely_cause": cause,
        "context_adjustment_recommended": is_anomaly
    }


def should_apply_context_adjustment(
    zone_id: str,
    rider_deliveries: int,
    zone_deliveries: int,
    zone_baseline: list[int],
    weather_severity: float = 0.0,
    cancellation_rate: float = 0.05
) -> dict:
    """
    Combined decision: should this rider be protected from reduced contribution
    because the zone itself was disrupted (not their individual performance)?
    """
    if not zone_baseline:
        return {"apply_adjustment": False, "reason": "no_baseline"}

    zdi_result = compute_zone_delivery_index(zone_id, zone_deliveries, zone_baseline)

    active_riders = max(1, zone_deliveries // max(rider_deliveries, 1))
    iso_result = run_isolation_forest(
        total_deliveries=zone_deliveries,
        active_riders=active_riders,
        avg_order_value=280.0,
        weather_severity=weather_severity,
        cancellation_rate=cancellation_rate
    )

    apply = zdi_result["anomaly"] and iso_result["is_anomaly"]
    reason = iso_result["likely_cause"] if apply else "zone_performing_normally"

    return {
        "zone_id": zone_id,
        "apply_adjustment": apply,
        "reason": reason,
        "zdi": zdi_result["zdi"],
        "zdi_status": zdi_result["status"],
        "isolation_confirmed": iso_result["is_anomaly"],
        "likely_cause": iso_result["likely_cause"]
    }
