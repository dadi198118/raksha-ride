from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./raksha_ride.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Rider(Base):
    __tablename__ = "riders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    city = Column(String, nullable=False)
    city_tier = Column(Integer, nullable=False)
    platform = Column(String, nullable=False)
    zone_id = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    upi_id = Column(String, nullable=True)
    policy_active = Column(Boolean, default=False)
    weeks_contributed = Column(Integer, default=0)
    total_days_claimed = Column(Integer, default=0)
    no_claim_streak = Column(Integer, default=0)
    loyalty_discount = Column(Boolean, default=False)
    avg_performance_ratio = Column(Float, default=1.0)
    has_loyalty_discount = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_delivery_at = Column(DateTime, nullable=True)


class WeeklyContribution(Base):
    __tablename__ = "weekly_contributions"
    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, nullable=False)
    week_start = Column(DateTime, nullable=False)
    deliveries = Column(Integer, nullable=False)
    base_rate = Column(Float, default=1.0)
    performance_ratio = Column(Float, default=1.0)
    zone_risk_score = Column(Float, default=0.5)
    weather_score = Column(Float, default=0.0)
    contribution_amount = Column(Float, nullable=False)
    zone_anomaly_applied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DisruptionAlert(Base):
    __tablename__ = "disruption_alerts"
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    severity = Column(Integer, nullable=False)
    affected_pincodes = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    sources_confirmed = Column(JSON, nullable=False)
    estimated_duration_days = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class ClaimPayout(Base):
    __tablename__ = "claim_payouts"
    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, nullable=False)
    alert_id = Column(Integer, nullable=False)
    daily_amount = Column(Float, nullable=False)
    days_paid = Column(Integer, default=0)
    total_paid = Column(Float, default=0.0)
    fraud_score = Column(Float, default=0.0)
    fraud_decision = Column(String, default="auto_approved")
    status = Column(String, default="processing")
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)


class ZoneData(Base):
    __tablename__ = "zone_data"
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(String, nullable=False)
    week_start = Column(DateTime, nullable=False)
    total_deliveries = Column(Integer, nullable=False)
    active_riders = Column(Integer, nullable=False)
    avg_order_value = Column(Float, nullable=False)
    weather_severity = Column(Float, nullable=False)
    zdi = Column(Float, nullable=False)
    anomaly_detected = Column(Boolean, default=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)