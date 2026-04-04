"""
Routers: Alerts + Claims
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db, DisruptionAlert, Rider, ClaimPayout
from models.disruption_detection import run_detection_cycle
from models.payout_engine import check_eligibility
from models.dynamic_pricing import estimate_payout, TIER_RATES

router = APIRouter(prefix="/alerts", tags=["alerts"])
claims_router = APIRouter(prefix="/claims", tags=["claims"])

PINCODE_MAP = {
    "HYD_500001": ["500001", "500002", "500003"],
    "BLR_560001": ["560001", "560002"],
    "MUM_400001": ["400001", "400002", "400003"],
    "CHN_600001": ["600001"],
    "VZG_530001": ["530001", "530002"],
    "DEL_110001": ["110001", "110002"],
    "KOL_700001": ["700001"],
    "PUN_411001": ["411001"],
}


@router.get("/")
def get_alerts(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(DisruptionAlert)
    if active_only:
        query = query.filter(DisruptionAlert.is_active == True)
    alerts = query.order_by(DisruptionAlert.created_at.desc()).limit(50).all()
    return [
        {
            "id": a.id,
            "zone_id": a.zone_id,
            "event_type": a.event_type,
            "severity": a.severity,
            "confidence": a.confidence,
            "sources_confirmed": a.sources_confirmed or [],
            "affected_pincodes": a.affected_pincodes or [],
            "estimated_duration_days": a.estimated_duration_days,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/trigger-detection")
async def trigger_detection(db: Session = Depends(get_db)):
    alerts = await run_detection_cycle(db)
    return {
        "alerts_fired": len(alerts),
        "alerts": alerts,
        "message": f"Detection cycle complete. {len(alerts)} alert(s) fired."
    }


@router.post("/mock-disaster")
def mock_disaster(
    zone_id: str = "HYD_500001",
    event_type: str = "flood",
    severity: int = 4,
    db: Session = Depends(get_db)
):
    pincodes = PINCODE_MAP.get(zone_id, ["000000"])

    alert = DisruptionAlert(
        zone_id=zone_id,
        event_type=event_type,
        severity=severity,
        affected_pincodes=pincodes,
        confidence=0.95,
        sources_confirmed=["MockDisaster", "Demo"],
        estimated_duration_days=3,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    eligible_riders = db.query(Rider).filter(
        Rider.zone_id == zone_id,
        Rider.policy_active == True
    ).all()

    claims_created = []
    for rider in eligible_riders:
        existing = db.query(ClaimPayout).filter(
            ClaimPayout.rider_id == rider.id,
            ClaimPayout.alert_id == alert.id
        ).first()
        if existing:
            continue

        payout = estimate_payout(
            avg_weekly_contribution=80.0,
            city_tier=rider.city_tier,
            avg_performance_ratio=1.0,
            base_rate=TIER_RATES.get(rider.city_tier, 1.0)
        )

        claim = ClaimPayout(
            rider_id=rider.id,
            alert_id=alert.id,
            status="processing",
            daily_amount=payout["daily_payout"],
            days_paid=0,
            total_paid=0.0,
            fraud_score=8.5,
            fraud_decision="auto_approved",
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)

        claims_created.append({
            "claim_id": claim.id,
            "rider_name": rider.name,
            "daily_payout": claim.daily_amount,
            "fraud_score": claim.fraud_score,
            "status": claim.status,
        })

    return {
        "alert": {
            "id": alert.id,
            "zone_id": alert.zone_id,
            "event_type": alert.event_type,
            "severity": alert.severity,
        },
        "riders_processed": len(eligible_riders),
        "claims_created": claims_created,
    }


@claims_router.get("/rider/{rider_id}")
def get_rider_claims(rider_id: int, db: Session = Depends(get_db)):
    claims = db.query(ClaimPayout).filter(
        ClaimPayout.rider_id == rider_id
    ).order_by(ClaimPayout.created_at.desc()).all()

    result = []
    for c in claims:
        alert = db.query(DisruptionAlert).filter(DisruptionAlert.id == c.alert_id).first()
        result.append({
            "claim_id": c.id,
            "alert_id": c.alert_id,
            "event_type": alert.event_type if alert else "unknown",
            "zone_id": alert.zone_id if alert else "unknown",
            "status": c.status,
            "daily_amount": c.daily_amount,
            "days_paid": c.days_paid,
            "total_paid": c.total_paid,
            "fraud_score": c.fraud_score,
            "fraud_decision": getattr(c, 'fraud_decision', 'auto_approved'),
            "rejection_reason": getattr(c, 'rejection_reason', None),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


@claims_router.post("/process-payouts")
def process_pending_payouts(db: Session = Depends(get_db)):
    from models.payout_engine import MAX_DAYS_PER_EVENT, MAX_TOTAL_DAYS_PER_PERIOD

    claims = db.query(ClaimPayout).filter(
        ClaimPayout.status.in_(["processing", "active"])
    ).all()

    results = []
    for claim in claims:
        rider = db.query(Rider).filter(Rider.id == claim.rider_id).first()
        if not rider:
            continue

        days_allowed = min(
            MAX_DAYS_PER_EVENT - claim.days_paid,
            MAX_TOTAL_DAYS_PER_PERIOD - rider.total_days_claimed
        )
        if days_allowed <= 0:
            claim.status = "completed"
            claim.last_updated = datetime.utcnow()
            db.commit()
            continue

        claim.status = "active"
        claim.days_paid += 1
        claim.total_paid += claim.daily_amount
        rider.total_days_claimed += 1
        claim.last_updated = datetime.utcnow()

        if claim.days_paid >= MAX_DAYS_PER_EVENT:
            claim.status = "completed"

        db.commit()
        results.append({
            "claim_id": claim.id,
            "rider_id": claim.rider_id,
            "days_paid": claim.days_paid,
            "total_paid": claim.total_paid,
            "status": claim.status,
        })

    return {"processed": len(results), "claims": results}


@claims_router.post("/check-eligibility/{rider_id}/{alert_id}")
def check_claim_eligibility(rider_id: int, alert_id: int, db: Session = Depends(get_db)):
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found.")

    alert = db.query(DisruptionAlert).filter(DisruptionAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    existing_claims = db.query(ClaimPayout).filter(
        ClaimPayout.rider_id == rider_id
    ).all()
    total_days_claimed = sum(c.days_paid for c in existing_claims)
    claim_history = len(existing_claims)

    result = check_eligibility(
        rider_id=rider.id,
        policy_active=rider.policy_active,
        weeks_contributed=rider.weeks_contributed,
        total_days_claimed_this_period=total_days_claimed,
        rider_pincode=rider.pincode,
        alert_affected_pincodes=alert.affected_pincodes or [],
        city_tier=rider.city_tier,
        avg_weekly_contribution=80.0,
        avg_performance_ratio=getattr(rider, 'avg_performance_ratio', 1.0),
        claim_history_count=claim_history,
        active_order_count=0,
        simulated_in_zone=True,
    )

    return {
        "eligible": result.eligible,
        "rejection_reasons": result.rejection_reasons,
        "daily_payout": result.daily_payout,
        "estimated_total_payout": result.estimated_total_event_payout,
        "fraud_score": result.fraud_score,
        "fraud_decision": result.fraud_decision,
        "days_remaining_period": result.days_remaining_this_period,
    }