"""
Module 4: Fraud Detection Engine
XGBoost Classifier — scores each claim 0–100
GPS spoofing detection, behavioural signals, cluster analysis
"""
import numpy as np
import xgboost as xgb
import logging

logger = logging.getLogger(__name__)

# --- Train on synthetic data ---
np.random.seed(77)
N = 3000

# Genuine claims (label 0)
n_genuine = 2700
genuine = {
    'mock_provider_flag': np.zeros(n_genuine),
    'accel_gps_mismatch': np.random.uniform(0, 0.15, n_genuine),
    'coordinate_jitter_std': np.random.uniform(0.5, 3.0, n_genuine),
    'battery_drain_consistency': np.random.uniform(0.7, 1.0, n_genuine),
    'cell_tower_distance_km': np.random.uniform(0.2, 5.0, n_genuine),
    'ip_geolocation_distance_km': np.random.uniform(0.5, 10.0, n_genuine),
    'location_history_consistency': np.random.uniform(0.75, 1.0, n_genuine),
    'days_since_last_delivery': np.random.randint(0, 5, n_genuine).astype(float),
    'claim_history_count': np.random.choice([0, 1, 2], n_genuine, p=[0.7, 0.2, 0.1]).astype(float),
    'cluster_size': np.random.randint(5, 200, n_genuine).astype(float),
    'order_count_during_event': np.zeros(n_genuine),
    'weeks_contributed': np.random.randint(3, 26, n_genuine).astype(float),
}

# Fraudulent claims (label 1)
n_fraud = 300
fraud = {
    'mock_provider_flag': np.random.choice([0, 1], n_fraud, p=[0.3, 0.7]).astype(float),
    'accel_gps_mismatch': np.random.uniform(0.4, 1.0, n_fraud),
    'coordinate_jitter_std': np.random.uniform(0.0, 0.2, n_fraud),  # unnaturally smooth
    'battery_drain_consistency': np.random.uniform(0.0, 0.4, n_fraud),
    'cell_tower_distance_km': np.random.uniform(15.0, 80.0, n_fraud),
    'ip_geolocation_distance_km': np.random.uniform(30.0, 200.0, n_fraud),
    'location_history_consistency': np.random.uniform(0.0, 0.3, n_fraud),
    'days_since_last_delivery': np.random.randint(10, 60, n_fraud).astype(float),
    'claim_history_count': np.random.choice([0, 1, 2, 3, 4], n_fraud, p=[0.1, 0.1, 0.2, 0.3, 0.3]).astype(float),
    'cluster_size': np.random.randint(1, 4, n_fraud).astype(float),  # isolated claimants
    'order_count_during_event': np.random.randint(1, 15, n_fraud).astype(float),
    'weeks_contributed': np.random.randint(3, 6, n_fraud).astype(float),
}

FEATURES = list(genuine.keys())

def _build_matrix(d):
    return np.column_stack([d[f] for f in FEATURES])

X_genuine = _build_matrix(genuine)
X_fraud = _build_matrix(fraud)
X_train = np.vstack([X_genuine, X_fraud])
y_train = np.array([0] * n_genuine + [1] * n_fraud)

_fraud_model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=4,
    learning_rate=0.1,
    scale_pos_weight=(n_genuine / n_fraud),  # handle class imbalance
    random_state=42,
    verbosity=0,
    eval_metric='logloss'
)
_fraud_model.fit(X_train, y_train)


def compute_fraud_score(
    rider_id: int,
    mock_provider_flag: int = 0,
    accel_gps_mismatch: float = 0.05,
    coordinate_jitter_std: float = 1.5,
    battery_drain_consistency: float = 0.9,
    cell_tower_distance_km: float = 2.0,
    ip_geolocation_distance_km: float = 5.0,
    location_history_consistency: float = 0.9,
    days_since_last_delivery: int = 1,
    claim_history_count: int = 0,
    cluster_size: int = 50,
    order_count_during_event: int = 0,
    weeks_contributed: int = 10,
) -> dict:
    """
    Compute a fraud score 0–100 for a claim.
    Score 0–30   → Auto-approved
    Score 31–60  → 24-hour soft hold
    Score 61–100 → Rejected, account flagged
    """
    features = np.array([[
        mock_provider_flag,
        accel_gps_mismatch,
        coordinate_jitter_std,
        battery_drain_consistency,
        cell_tower_distance_km,
        ip_geolocation_distance_km,
        location_history_consistency,
        float(days_since_last_delivery),
        float(claim_history_count),
        float(cluster_size),
        float(order_count_during_event),
        float(weeks_contributed),
    ]])

    fraud_proba = float(_fraud_model.predict_proba(features)[0][1])
    raw_score = round(fraud_proba * 100, 1)

    if raw_score <= 30:
        decision = "auto_approved"
        action = "Payout triggered immediately"
    elif raw_score <= 60:
        decision = "soft_hold"
        action = "24-hour silent review pending"
    else:
        decision = "rejected"
        action = "Claim rejected. Account flagged for review."

    # Top risk signals for explainability (SHAP-like manual explanation)
    risk_signals = []
    if mock_provider_flag:
        risk_signals.append("Mock location provider detected")
    if accel_gps_mismatch > 0.3:
        risk_signals.append("Accelerometer-GPS mismatch")
    if coordinate_jitter_std < 0.3:
        risk_signals.append("Unnaturally smooth GPS coordinates")
    if cell_tower_distance_km > 10:
        risk_signals.append("Cell tower distance inconsistency")
    if claim_history_count > 2:
        risk_signals.append("High historical claim frequency")
    if order_count_during_event > 0:
        risk_signals.append("Active deliveries during claimed disruption")
    if cluster_size < 3:
        risk_signals.append("Isolated claim (low cluster size)")

    return {
        "rider_id": rider_id,
        "fraud_score": raw_score,
        "fraud_probability": round(fraud_proba, 4),
        "decision": decision,
        "action": action,
        "risk_signals": risk_signals,
        "explainable": True
    }


def simulate_realistic_fraud_score(
    rider_id: int,
    weeks_contributed: int,
    claim_history: int,
    is_in_disruption_zone: bool,
    active_orders: int = 0
) -> dict:
    """
    Simplified fraud score for demo — uses realistic defaults
    based on rider's profile, simulating what real GPS signals would produce.
    """
    # Genuine rider in disruption zone = low fraud score
    base_mismatch = 0.05 if is_in_disruption_zone else 0.45
    base_jitter = 1.8 if is_in_disruption_zone else 0.1
    base_cell_dist = 2.0 if is_in_disruption_zone else 25.0
    base_consistency = 0.92 if is_in_disruption_zone else 0.2

    return compute_fraud_score(
        rider_id=rider_id,
        accel_gps_mismatch=base_mismatch,
        coordinate_jitter_std=base_jitter,
        battery_drain_consistency=0.85,
        cell_tower_distance_km=base_cell_dist,
        ip_geolocation_distance_km=base_cell_dist * 1.5,
        location_history_consistency=base_consistency,
        days_since_last_delivery=1,
        claim_history_count=claim_history,
        cluster_size=80 if is_in_disruption_zone else 2,
        order_count_during_event=active_orders,
        weeks_contributed=weeks_contributed,
    )
