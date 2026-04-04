from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from database import get_db, Rider, WeeklyContribution
from data_ingestion.weather_feed import get_city_tier, CITY_COORDS

router = APIRouter(prefix="/riders", tags=["riders"])


class RiderRegistration(BaseModel):
    name: str
    phone: str
    city: str
    platform: str
    pincode: str
    upi_id: Optional[str] = None


class RiderResponse(BaseModel):
    id: int
    name: str
    phone: str
    city: str
    city_tier: int
    platform: str
    zone_id: str
    pincode: str
    upi_id: Optional[str]
    policy_active: bool
    weeks_contributed: int
    total_days_claimed: int
    no_claim_streak: int
    loyalty_discount: bool
    created_at: datetime

    class Config:
        from_attributes = True


CITY_ZONE_MAP = {
    "Hyderabad": "HYD_500001", "Bengaluru": "BLR_560001",
    "Mumbai": "MUM_400001", "Chennai": "CHN_600001",
    "Delhi": "DEL_110001", "Kolkata": "KOL_700001",
    "Pune": "PUN_411001", "Ahmedabad": "AMD_380001",
    "Jaipur": "JAI_302001", "Visakhapatnam": "VZG_530001",
    "Surat": "SUR_395001", "Lucknow": "LKO_226001",
    "Nagpur": "NGP_440001", "Coimbatore": "CBE_641001",
}


@router.post("/register", response_model=RiderResponse)
def register_rider(data: RiderRegistration, db: Session = Depends(get_db)):
    existing = db.query(Rider).filter(Rider.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered.")

    city_tier = get_city_tier(data.city)
    zone_id = CITY_ZONE_MAP.get(data.city, f"GEN_{data.pincode[:3]}000")

    rider = Rider(
        name=data.name,
        phone=data.phone,
        city=data.city,
        city_tier=city_tier,
        platform=data.platform,
        zone_id=zone_id,
        pincode=data.pincode,
        upi_id=data.upi_id,
        policy_active=False,  # activates after 3 weeks
        weeks_contributed=0,
        total_days_claimed=0,
        no_claim_streak=0,
        loyalty_discount=False,
    )
    db.add(rider)
    db.commit()
    db.refresh(rider)
    return rider


@router.get("/{rider_id}", response_model=RiderResponse)
def get_rider(rider_id: int, db: Session = Depends(get_db)):
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider


@router.get("/")
def list_riders(db: Session = Depends(get_db)):
    riders = db.query(Rider).all()
    return riders


@router.get("/{rider_id}/contributions")
def get_contributions(rider_id: int, db: Session = Depends(get_db)):
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    contribs = (
        db.query(WeeklyContribution)
        .filter(WeeklyContribution.rider_id == rider_id)
        .order_by(WeeklyContribution.week_start.desc())
        .limit(8)
        .all()
    )
    return {
        "rider_id": rider_id,
        "city_tier": rider.city_tier,
        "weeks_contributed": rider.weeks_contributed,
        "contributions": [
            {
                "week_start": c.week_start,
                "deliveries": c.deliveries,
                "contribution_amount": c.contribution_amount,
                "performance_ratio": c.performance_ratio,
                "zone_risk_score": c.zone_risk_score,
                "weather_score": c.weather_score,
                "zone_anomaly_applied": c.zone_anomaly_applied,
            }
            for c in contribs
        ]
    }


@router.get("/{rider_id}/dashboard")
def get_dashboard(rider_id: int, db: Session = Depends(get_db)):
    from database import ClaimPayout, DisruptionAlert

    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    contribs = (
        db.query(WeeklyContribution)
        .filter(WeeklyContribution.rider_id == rider_id)
        .order_by(WeeklyContribution.week_start.desc())
        .all()
    )

    # Active claims
    active_claims = (
        db.query(ClaimPayout)
        .filter(ClaimPayout.rider_id == rider_id, ClaimPayout.status.in_(["active", "processing"]))
        .all()
    )

    # Zone alerts
    zone_alerts = (
        db.query(DisruptionAlert)
        .filter(DisruptionAlert.zone_id == rider.zone_id, DisruptionAlert.is_active == True)
        .all()
    )

    avg_contribution = sum(c.contribution_amount for c in contribs) / len(contribs) if contribs else 0
    days_remaining = 30 - rider.total_days_claimed

    return {
        "rider": {
            "id": rider.id,
            "name": rider.name,
            "city": rider.city,
            "city_tier": rider.city_tier,
            "platform": rider.platform,
            "zone_id": rider.zone_id,
            "policy_active": rider.policy_active,
            "weeks_contributed": rider.weeks_contributed,
            "total_days_claimed": rider.total_days_claimed,
            "days_remaining_period": days_remaining,
            "loyalty_discount": rider.loyalty_discount,
            "no_claim_streak": rider.no_claim_streak,
        },
        "policy": {
            "status": "active" if rider.policy_active else "pending",
            "weeks_to_activation": max(0, 3 - rider.weeks_contributed),
            "period_days_cap": 30,
            "days_used": rider.total_days_claimed,
            "days_remaining": days_remaining,
            "loyalty_discount_eligible": rider.no_claim_streak >= 24,  # ~6 months no claim
        },
        "contributions": {
            "avg_weekly": round(avg_contribution, 2),
            "total_contributions": len(contribs),
            "last_week": contribs[0].contribution_amount if contribs else 0,
        },
        "active_claims": [
            {
                "claim_id": c.id,
                "daily_amount": c.daily_amount,
                "days_paid": c.days_paid,
                "total_paid": c.total_paid,
                "status": c.status
            }
            for c in active_claims
        ],
        "zone_alerts": [
            {
                "alert_id": a.id,
                "event_type": a.event_type,
                "severity": a.severity,
                "confidence": a.confidence,
                "sources": a.sources_confirmed,
                "estimated_days": a.estimated_duration_days,
                "created_at": a.created_at,
            }
            for a in zone_alerts
        ]
    }