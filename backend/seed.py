"""Seed the database with demo data."""
import sys
sys.path.insert(0, '.')

from database import init_db, SessionLocal, Rider, WeeklyContribution, DisruptionAlert, ClaimPayout, ZoneData
from datetime import datetime, timedelta
import random

random.seed(42)

DEMO_RIDERS = [
    {"name": "Ravi Kumar", "phone": "9876543210", "city": "Hyderabad", "city_tier": 1, "platform": "Swiggy", "zone_id": "HYD_500001", "pincode": "500001", "upi_id": "ravi@upi"},
    {"name": "Priya Sharma", "phone": "9876543211", "city": "Bengaluru", "city_tier": 1, "platform": "Zomato", "zone_id": "BLR_560001", "pincode": "560001", "upi_id": "priya@upi"},
    {"name": "Arjun Reddy", "phone": "9876543212", "city": "Mumbai", "city_tier": 1, "platform": "Swiggy", "zone_id": "MUM_400001", "pincode": "400001", "upi_id": "arjun@upi"},
    {"name": "Sunita Devi", "phone": "9876543213", "city": "Pune", "city_tier": 2, "platform": "Dunzo", "zone_id": "PUN_411001", "pincode": "411001", "upi_id": "sunita@upi"},
    {"name": "Mohammed Farhan", "phone": "9876543214", "city": "Chennai", "city_tier": 1, "platform": "Zomato", "zone_id": "CHN_600001", "pincode": "600001", "upi_id": "farhan@upi"},
]

def seed():
    init_db()
    db = SessionLocal()

    # Clear existing
    db.query(ClaimPayout).delete()
    db.query(WeeklyContribution).delete()
    db.query(DisruptionAlert).delete()
    db.query(ZoneData).delete()
    db.query(Rider).delete()
    db.commit()

    # Create riders
    riders = []
    for rd in DEMO_RIDERS:
        r = Rider(
            **rd,
            policy_active=True,
            weeks_contributed=random.randint(4, 18),
            total_days_claimed=random.randint(0, 5),
            no_claim_streak=random.randint(0, 10),
            loyalty_discount=random.choice([False, False, False, True]),
            created_at=datetime.utcnow() - timedelta(weeks=random.randint(4, 20)),
            last_delivery_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48))
        )
        db.add(r)
        riders.append(r)
    db.commit()

    # Weekly contributions for each rider (last 8 weeks)
    for rider in riders:
        db.refresh(rider)
        base_rate = {1: 1.00, 2: 0.75, 3: 0.50}[rider.city_tier]
        for w in range(8):
            week_start = datetime.utcnow() - timedelta(weeks=w)
            deliveries = random.randint(60, 130)
            perf = random.uniform(0.8, 1.2)
            wc = WeeklyContribution(
                rider_id=rider.id,
                week_start=week_start,
                deliveries=deliveries,
                base_rate=base_rate,
                performance_ratio=round(perf, 3),
                zone_risk_score=random.uniform(0.4, 0.7),
                weather_score=random.uniform(0.0, 0.3),
                contribution_amount=round(deliveries * base_rate * perf * random.uniform(0.95, 1.10), 2),
                zone_anomaly_applied=False
            )
            db.add(wc)

    # Active disruption alerts
    alerts_data = [
        {
            "zone_id": "HYD_500001",
            "event_type": "flood",
            "severity": 4,
            "affected_pincodes": ["500001", "500002", "500003"],
            "confidence": 0.91,
            "sources_confirmed": ["IMD_RSS", "Open-Meteo"],
            "estimated_duration_days": 3,
            "is_active": True,
        },
        {
            "zone_id": "MUM_400001",
            "event_type": "strike",
            "severity": 3,
            "affected_pincodes": ["400001", "400002", "400003"],
            "confidence": 0.85,
            "sources_confirmed": ["NewsAPI", "NDMA_RSS"],
            "estimated_duration_days": 2,
            "is_active": True,
        },
        {
            "zone_id": "BLR_560001",
            "event_type": "curfew",
            "severity": 4,
            "affected_pincodes": ["560001", "560002"],
            "confidence": 0.93,
            "sources_confirmed": ["NewsAPI", "NDMA_RSS"],
            "estimated_duration_days": 1,
            "is_active": False,
            "resolved_at": datetime.utcnow() - timedelta(days=2)
        },
    ]
    alert_objs = []
    for ad in alerts_data:
        a = DisruptionAlert(**ad)
        db.add(a)
        alert_objs.append(a)
    db.commit()

    # Payout record for first rider (active claim)
    for alert in alert_objs:
        db.refresh(alert)

    ravi = riders[0]
    db.refresh(ravi)
    hyderabad_alert = db.query(DisruptionAlert).filter(DisruptionAlert.zone_id == "HYD_500001").first()
    if hyderabad_alert:
        cp = ClaimPayout(
            rider_id=ravi.id,
            alert_id=hyderabad_alert.id,
            daily_amount=480.0,
            days_paid=2,
            total_paid=960.0,
            fraud_score=12.5,
            status="active"
        )
        db.add(cp)

    db.commit()
    db.close()
    print("✅ Database seeded successfully with demo data.")

if __name__ == "__main__":
    seed()