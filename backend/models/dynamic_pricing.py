"""
Module 3: Dynamic Pricing Engine
XGBoost Regressor — computes each rider's weekly contribution
Factors: zone risk score, live weather severity, performance ratio
"""
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

# City tier base rates (₹ per delivery)
TIER_RATES = {1: 1.00, 2: 0.75, 3: 0.50}

# Payout floors and ceilings per tier (₹/day)
PAYOUT_FLOOR = {1: 400, 2: 325, 3: 250}
PAYOUT_CEILING = {1: 900, 2: 700, 3: 550}
COVERAGE_RATIO = {1: 0.70, 2: 0.68, 3: 0.65}

AVG_DELIVERY_EARNING = 25.0  # ₹ per delivery avg earning

# Zone risk scores (historical + static for demo)
ZONE_RISK_SCORES = {
    "HYD_500001": 0.62,  "BLR_560001": 0.45, "MUM_400001": 0.71,
    "CHN_600001": 0.55,  "DEL_110001": 0.58, "KOL_700001": 0.65,
    "PUN_411001": 0.42,  "AMD_380001": 0.48, "JAI_302001": 0.40,
    "VZG_530001": 0.68,
}

# --- Train XGBoost on synthetic data ---
np.random.seed(99)
N = 2000

city_tiers = np.random.choice([1, 2, 3], N)
base_rates = np.array([TIER_RATES[t] for t in city_tiers])
deliveries = np.random.randint(40, 160, N).astype(float)
zone_risk = np.random.uniform(0.3, 0.8, N)
weather_score = np.random.uniform(0.0, 1.0, N)
performance_ratio = np.clip(np.random.normal(1.0, 0.2, N), 0.4, 1.6)
loyalty_discount = np.random.choice([0, 1], N, p=[0.85, 0.15])

# Target: base_contribution * risk_multiplier * weather_adj * perf_adj * loyalty_adj
base_contribution = deliveries * base_rates
risk_multiplier = 1.0 + (zone_risk - 0.5) * 0.4
weather_adj = 1.0 + weather_score * 0.15
perf_adj = np.clip(performance_ratio, 0.6, 1.4)
loyalty_adj = np.where(loyalty_discount == 1, 0.85, 1.0)

target = base_contribution * risk_multiplier * weather_adj * perf_adj * loyalty_adj
target = np.clip(target, 30, 350)

X_train = np.column_stack([
    city_tiers, deliveries, zone_risk, weather_score,
    performance_ratio, loyalty_discount, base_rates
])

_pricing_model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbosity=0
)
_pricing_model.fit(X_train, target)


def compute_weekly_contribution(
    rider_id: int,
    city_tier: int,
    deliveries: int,
    zone_id: str,
    weather_severity: float = 0.0,
    performance_ratio: float = 1.0,
    has_loyalty_discount: bool = False,
    zone_anomaly_applied: bool = False
) -> dict:
    """
    Compute this week's contribution for a rider.
    Returns the amount, breakdown, and explanation.
    """
    base_rate = TIER_RATES.get(city_tier, 1.00)
    zone_risk = ZONE_RISK_SCORES.get(zone_id, 0.50)

    # If zone anomaly detected, use baseline performance ratio to protect rider
    effective_perf_ratio = 1.0 if zone_anomaly_applied else performance_ratio
    loyalty_flag = 1 if has_loyalty_discount else 0

    features = np.array([[
        city_tier,
        deliveries,
        zone_risk,
        weather_severity,
        effective_perf_ratio,
        loyalty_flag,
        base_rate
    ]])

    predicted = float(_pricing_model.predict(features)[0])
    predicted = max(30.0, min(350.0, predicted))

    # Component breakdown for transparency
    base_contribution = deliveries * base_rate
    risk_adj = round((zone_risk - 0.5) * 0.4 * base_contribution, 2)
    weather_adj = round(weather_severity * 0.15 * base_contribution, 2)
    perf_adj = round((effective_perf_ratio - 1.0) * base_contribution * 0.5, 2)
    loyalty_adj = round(-0.15 * predicted if has_loyalty_discount else 0.0, 2)
    zone_discount = "Zone anomaly — baseline rate applied" if zone_anomaly_applied else None

    return {
        "rider_id": rider_id,
        "contribution_amount": round(predicted, 2),
        "breakdown": {
            "base_deliveries": deliveries,
            "base_rate_per_delivery": base_rate,
            "base_contribution": round(base_contribution, 2),
            "zone_risk_score": zone_risk,
            "zone_risk_adjustment": risk_adj,
            "weather_severity_score": round(weather_severity, 3),
            "weather_adjustment": weather_adj,
            "performance_ratio": round(effective_perf_ratio, 3),
            "performance_adjustment": perf_adj,
            "loyalty_discount_applied": has_loyalty_discount,
            "loyalty_adjustment": loyalty_adj,
            "zone_anomaly_protection": zone_discount,
        },
        "weekly_earning_estimate": round(deliveries * AVG_DELIVERY_EARNING, 2),
        "contribution_pct_of_earning": round(predicted / (deliveries * AVG_DELIVERY_EARNING) * 100, 2)
    }


def estimate_payout(
    avg_weekly_contribution: float,
    city_tier: int,
    avg_performance_ratio: float,
    base_rate: float
) -> dict:
    """
    Estimate daily payout if rider becomes eligible for a claim.
    """
    if base_rate == 0 or avg_performance_ratio == 0:
        return {"daily_payout": PAYOUT_FLOOR[city_tier]}

    est_weekly_deliveries = avg_weekly_contribution / (base_rate * avg_performance_ratio)
    est_weekly_earning = est_weekly_deliveries * AVG_DELIVERY_EARNING
    est_daily_earning = est_weekly_earning / 7
    coverage = COVERAGE_RATIO[city_tier]
    daily_payout = est_daily_earning * coverage
    daily_payout = max(daily_payout, PAYOUT_FLOOR[city_tier])
    daily_payout = min(daily_payout, PAYOUT_CEILING[city_tier])

    return {
        "daily_payout": round(daily_payout, 2),
        "coverage_ratio": coverage,
        "est_daily_earning": round(est_daily_earning, 2),
        "floor": PAYOUT_FLOOR[city_tier],
        "ceiling": PAYOUT_CEILING[city_tier]
    }
