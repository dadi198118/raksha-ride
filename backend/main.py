"""
Raksha Ride — AI-powered income protection for food delivery partners
FastAPI backend with 5 AI modules
"""
import sys
sys.path.insert(0, '.')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from database import init_db, SessionLocal
from routers.riders import router as riders_router
from routers.pricing import router as pricing_router
from routers.alerts import router as alerts_router, claims_router
from data_ingestion.weather_feed import get_weather_for_city

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_detection():
    """Runs every 30 minutes: AI detection cycle."""
    from models.disruption_detection import run_detection_cycle
    db = SessionLocal()
    try:
        alerts = await run_detection_cycle(db)
        if alerts:
            logger.info(f"Scheduler: {len(alerts)} disruption alerts fired")
    finally:
        db.close()


def scheduled_payout():
    """
    Runs every 60 seconds (demo) / daily (production).
    Automatically advances all processing/active claims by one day.
    """
    from models.payout_engine import MAX_DAYS_PER_EVENT, MAX_TOTAL_DAYS_PER_PERIOD
    from database import ClaimPayout, Rider
    from datetime import datetime

    db = SessionLocal()
    try:
        claims = db.query(ClaimPayout).filter(
            ClaimPayout.status.in_(["processing", "active"])
        ).all()

        if not claims:
            return

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
                continue

            claim.status = "active"
            claim.days_paid += 1
            claim.total_paid += claim.daily_amount
            rider.total_days_claimed += 1
            claim.last_updated = datetime.utcnow()

            if claim.days_paid >= MAX_DAYS_PER_EVENT:
                claim.status = "completed"

            logger.info(
                f"Auto-payout: Rider #{rider.id} — "
                f"₹{claim.daily_amount} paid (day {claim.days_paid}) "
                f"total ₹{claim.total_paid}"
            )

        db.commit()
    except Exception as e:
        logger.error(f"Payout scheduler error: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialising Raksha Ride backend...")
    init_db()

    # Seed if empty
    db = SessionLocal()
    from database import Rider
    if db.query(Rider).count() == 0:
        db.close()
        import seed
        seed.seed()
    else:
        db.close()

    # Start scheduler
    scheduler.add_job(scheduled_detection, "interval", minutes=30, id="detection_cycle")

    # Auto payout every 60 seconds for demo (change to hours=24 for production)
    scheduler.add_job(scheduled_payout, "interval", seconds=60, id="payout_cycle")

    scheduler.start()
    logger.info("✅ Raksha Ride backend ready")
    yield

    # Shutdown
    scheduler.shutdown()


app = FastAPI(
    title="Raksha Ride API",
    description="AI-powered income protection insurance for food delivery partners",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(riders_router)
app.include_router(pricing_router)
app.include_router(alerts_router)
app.include_router(claims_router)


@app.get("/")
def root():
    return {
        "service": "Raksha Ride API",
        "version": "1.0.0",
        "status": "running",
        "modules": [
            "Disruption Detection (TF-IDF + Logistic Regression)",
            "Zone Anomaly Engine (Z-score + Isolation Forest)",
            "Dynamic Pricing (XGBoost Regressor)",
            "Fraud Detection (XGBoost Classifier)",
            "Eligibility & Payout (Rule-based)"
        ]
    }


@app.get("/health")
async def health():
    weather = await get_weather_for_city("Hyderabad")
    return {
        "status": "healthy",
        "weather_api": "connected" if weather["source"] == "Open-Meteo" else "fallback",
        "scheduler": "running" if scheduler.running else "stopped"
    }


@app.get("/cities")
def get_cities():
    from data_ingestion.weather_feed import CITY_COORDS
    return [
        {"name": city, "tier": info["tier"]}
        for city, info in CITY_COORDS.items()
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)