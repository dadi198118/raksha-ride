from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db, Rider, WeeklyContribution, DisruptionAlert, ClaimPayout
from models.zone_anomaly import compute_zone_delivery_index, should_apply_context_adjustment
from models.disruption_detection import classify_text
from data_ingestion.platform_webhook import simulate_current_week_volume, get_zone_baseline

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/zone/{zone_id}/anomaly")
def check_zone_anomaly(zone_id: str, current_deliveries: int = 500):
    baseline = get_zone_baseline(zone_id)
    zdi = compute_zone_delivery_index(zone_id, current_deliveries, baseline)
    return zdi


@router.get("/zone/{zone_id}/simulate-volume")
def simulate_zone_volume(zone_id: str, disruption_factor: float = 1.0):
    """Simulate zone volume for demo. disruption_factor=0.3 means 70% drop."""
    result = simulate_current_week_volume(zone_id, disruption_factor)
    zdi = compute_zone_delivery_index(
        zone_id, result["current_deliveries"], result["baseline_history"]
    )
    return {**result, "zone_delivery_index": zdi}


@router.post("/classify-text")
def classify_news_text(text: str):
    """Classify any text through the disruption detection model."""
    return classify_text(text)


@router.get("/system-stats")
def get_system_stats(db: Session = Depends(get_db)):
    """System-wide statistics for ops dashboard."""
    total_riders = db.query(Rider).count()
    active_policies = db.query(Rider).filter(Rider.policy_active == True).count()
    total_alerts = db.query(DisruptionAlert).count()
    active_alerts = db.query(DisruptionAlert).filter(DisruptionAlert.is_active == True).count()
    total_claims = db.query(ClaimPayout).count()
    active_claims = db.query(ClaimPayout).filter(ClaimPayout.status.in_(["active", "processing"])).count()

    # Total payout disbursed
    from sqlalchemy import func
    total_disbursed = db.query(func.sum(ClaimPayout.total_paid)).scalar() or 0

    # Average contribution
    avg_contribution = db.query(func.avg(WeeklyContribution.contribution_amount)).scalar() or 0

    # Fraud breakdown
    auto_approved = db.query(ClaimPayout).filter(ClaimPayout.fraud_score < 31).count()
    held = db.query(ClaimPayout).filter(
        ClaimPayout.fraud_score >= 31, ClaimPayout.fraud_score < 61
    ).count()
    rejected = db.query(ClaimPayout).filter(ClaimPayout.fraud_score >= 61).count()

    return {
        "riders": {"total": total_riders, "active_policies": active_policies},
        "alerts": {"total": total_alerts, "active": active_alerts},
        "claims": {
            "total": total_claims,
            "active": active_claims,
            "fraud_breakdown": {
                "auto_approved": auto_approved,
                "soft_hold": held,
                "rejected": rejected
            }
        },
        "financials": {
            "total_disbursed": round(float(total_disbursed), 2),
            "avg_weekly_contribution": round(float(avg_contribution), 2),
        },
        "ai_modules": [
            {"name": "Disruption Detection", "model": "TF-IDF + Logistic Regression", "status": "active"},
            {"name": "Zone Anomaly Engine", "model": "Z-score + Isolation Forest", "status": "active"},
            {"name": "Dynamic Pricing", "model": "XGBoost Regressor", "status": "active"},
            {"name": "Fraud Detection", "model": "XGBoost Classifier", "status": "active"},
            {"name": "Payout Engine", "model": "Rule-based (deterministic)", "status": "active"},
        ]
    }


# ─── Triggers endpoint ────────────────────────────────────────────────────────
@router.get("/triggers/run")
async def run_triggers(
    city: str = "Hyderabad",
    zone_id: str = "HYD_500001",
    current_deliveries: int = 500,
    disruption_factor: float = 1.0,
):
    """Run all 5 automated triggers and return consolidated results."""
    from data_ingestion.triggers import run_all_triggers
    return await run_all_triggers(
        city=city,
        zone_id=zone_id,
        current_deliveries=current_deliveries,
        disruption_factor=disruption_factor,
    )

@router.get("/triggers/demo-disaster")
async def demo_disaster_triggers(city: str = "Hyderabad", zone_id: str = "HYD_500001"):
    """
    Demo mode: simulate a severe disruption (disruption_factor=0.25).
    All 5 triggers will fire — shows the full pipeline for demo video.
    """
    from data_ingestion.triggers import run_all_triggers
    headlines = [
        "Heavy rains lash Hyderabad, IMD issues red alert for next 48 hours",
        "Section 144 imposed in city after violent protests",
        "Truck drivers bandh declared, delivery services disrupted",
        "Cyclone warning issued for coastal districts",
    ]
    return await run_all_triggers(
        city=city,
        zone_id=zone_id,
        current_deliveries=180,
        disruption_factor=0.25,
        custom_headlines=headlines,
    )