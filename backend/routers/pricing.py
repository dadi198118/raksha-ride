from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db, Rider, WeeklyContribution
from models.dynamic_pricing import compute_weekly_contribution, estimate_payout, TIER_RATES
from models.zone_anomaly import should_apply_context_adjustment
from data_ingestion.weather_feed import get_weather_for_city
from datetime import datetime

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingRequest(BaseModel):
    rider_id: int
    deliveries: int
    zone_deliveries: Optional[int] = None
    zone_baseline: Optional[list[int]] = None


@router.post("/compute")
async def compute_pricing(req: PricingRequest, db: Session = Depends(get_db)):
    rider = db.query(Rider).filter(Rider.id == req.rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Get last 8 weeks contributions for performance ratio
    prev_contribs = (
        db.query(WeeklyContribution)
        .filter(WeeklyContribution.rider_id == rider.id)
        .order_by(WeeklyContribution.week_start.desc())
        .limit(8)
        .all()
    )

    avg_deliveries = (
        sum(c.deliveries for c in prev_contribs) / len(prev_contribs)
        if prev_contribs else 80
    )
    performance_ratio = req.deliveries / avg_deliveries if avg_deliveries > 0 else 1.0

    # Weather severity
    weather_data = await get_weather_for_city(rider.city)
    weather_severity = weather_data["severity_score"]

    # Zone anomaly check
    zone_anomaly_result = {"apply_adjustment": False}
    if req.zone_deliveries and req.zone_baseline:
        zone_anomaly_result = should_apply_context_adjustment(
            zone_id=rider.zone_id,
            rider_deliveries=req.deliveries,
            zone_deliveries=req.zone_deliveries,
            zone_baseline=req.zone_baseline,
            weather_severity=weather_severity
        )

    # Compute contribution
    result = compute_weekly_contribution(
        rider_id=rider.id,
        city_tier=rider.city_tier,
        deliveries=req.deliveries,
        zone_id=rider.zone_id,
        weather_severity=weather_severity,
        performance_ratio=round(performance_ratio, 3),
        has_loyalty_discount=rider.loyalty_discount,
        zone_anomaly_applied=zone_anomaly_result["apply_adjustment"]
    )

    # Estimate payout if ever needed
    base_rate = TIER_RATES[rider.city_tier]
    payout_est = estimate_payout(
        avg_weekly_contribution=result["contribution_amount"],
        city_tier=rider.city_tier,
        avg_performance_ratio=performance_ratio,
        base_rate=base_rate
    )

    # Persist to DB
    wc = WeeklyContribution(
        rider_id=rider.id,
        week_start=datetime.utcnow(),
        deliveries=req.deliveries,
        base_rate=base_rate,
        performance_ratio=round(performance_ratio, 3),
        zone_risk_score=result["breakdown"]["zone_risk_score"],
        weather_score=weather_severity,
        contribution_amount=result["contribution_amount"],
        zone_anomaly_applied=zone_anomaly_result["apply_adjustment"]
    )
    db.add(wc)
    rider.weeks_contributed += 1
    if rider.weeks_contributed >= 3:
        rider.policy_active = True
    db.commit()

    return {
        **result,
        "weather": weather_data,
        "zone_anomaly": zone_anomaly_result,
        "payout_estimate_if_claimed": payout_est,
        "weeks_contributed_now": rider.weeks_contributed,
        "policy_active": rider.policy_active
    }


@router.get("/preview/{rider_id}")
async def preview_pricing(
    rider_id: int,
    deliveries: int = 90,
    db: Session = Depends(get_db)
):
    """Preview this week's contribution without saving."""
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    prev_contribs = (
        db.query(WeeklyContribution)
        .filter(WeeklyContribution.rider_id == rider.id)
        .order_by(WeeklyContribution.week_start.desc())
        .limit(4)
        .all()
    )
    avg_deliveries = (
        sum(c.deliveries for c in prev_contribs) / len(prev_contribs)
        if prev_contribs else 80
    )
    performance_ratio = deliveries / avg_deliveries if avg_deliveries > 0 else 1.0
    weather_data = await get_weather_for_city(rider.city)

    result = compute_weekly_contribution(
        rider_id=rider.id,
        city_tier=rider.city_tier,
        deliveries=deliveries,
        zone_id=rider.zone_id,
        weather_severity=weather_data["severity_score"],
        performance_ratio=round(performance_ratio, 3),
        has_loyalty_discount=rider.loyalty_discount,
        zone_anomaly_applied=False
    )

    return {
        **result,
        "weather": weather_data,
        "zone_anomaly": {"apply_adjustment": False},
        "payout_estimate_if_claimed": estimate_payout(
            result["contribution_amount"],
            rider.city_tier,
            performance_ratio,
            TIER_RATES[rider.city_tier]
        )
    }