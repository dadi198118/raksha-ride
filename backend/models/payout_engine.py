"""
Module 5: Eligibility & Payout Engine
Rule-based, fully deterministic and auditable.
Takes output of all 4 modules and makes final payout decision.
"""
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import logging

from models.dynamic_pricing import estimate_payout, TIER_RATES
from models.fraud_detection import simulate_realistic_fraud_score

logger = logging.getLogger(__name__)

# Policy rules
MIN_WEEKS_CONTRIBUTED = 3
MAX_DAYS_PER_EVENT = 14
MAX_TOTAL_DAYS_PER_PERIOD = 30  # 6-month rolling cap
MIN_FRAUD_SCORE_REJECT = 61


@dataclass
class EligibilityResult:
    eligible: bool
    rejection_reasons: list[str]
    daily_payout: float
    fraud_score: float
    fraud_decision: str
    days_remaining_this_period: int
    estimated_total_event_payout: float


def check_eligibility(
    rider_id: int,
    policy_active: bool,
    weeks_contributed: int,
    total_days_claimed_this_period: int,
    rider_pincode: str,
    alert_affected_pincodes: list[str],
    city_tier: int,
    avg_weekly_contribution: float,
    avg_performance_ratio: float,
    claim_history_count: int,
    active_order_count: int = 0,
    simulated_in_zone: bool = True,
) -> EligibilityResult:
    """
    Hard eligibility gate — all rules must pass.
    Returns full decision with payout amount.
    """
    rejections = []

    # Rule 1: Policy must be active
    if not policy_active:
        rejections.append("Policy is not active. Minimum 3 weeks of contributions required to activate.")

    # Rule 2: Minimum contribution weeks
    if weeks_contributed < MIN_WEEKS_CONTRIBUTED:
        rejections.append(
            f"Insufficient contribution history: {weeks_contributed} weeks contributed, "
            f"minimum {MIN_WEEKS_CONTRIBUTED} required."
        )

    # Rule 3: Rider must be in affected zone
    if rider_pincode not in alert_affected_pincodes and not simulated_in_zone:
        rejections.append(
            f"Rider pincode {rider_pincode} not in affected zone "
            f"({', '.join(alert_affected_pincodes[:3])}...)."
        )

    # Rule 4: No active deliveries during disruption
    if active_order_count > 0:
        rejections.append(
            f"Rider has {active_order_count} active orders — deliveries occurring during claimed disruption."
        )

    # Rule 5: Total days cap for period
    days_remaining = MAX_TOTAL_DAYS_PER_PERIOD - total_days_claimed_this_period
    if days_remaining <= 0:
        rejections.append(
            f"Annual claim cap reached: {MAX_TOTAL_DAYS_PER_PERIOD} days already claimed this period."
        )

    # Fraud check
    fraud_result = simulate_realistic_fraud_score(
        rider_id=rider_id,
        weeks_contributed=weeks_contributed,
        claim_history=claim_history_count,
        is_in_disruption_zone=simulated_in_zone,
        active_orders=active_order_count
    )

    if fraud_result["fraud_score"] >= MIN_FRAUD_SCORE_REJECT:
        rejections.append(
            f"Fraud risk detected (score: {fraud_result['fraud_score']}). "
            f"Signals: {', '.join(fraud_result['risk_signals'][:2])}."
        )

    # Payout calculation (even if rejected, for display)
    base_rate = TIER_RATES.get(city_tier, 1.00)
    payout_result = estimate_payout(
        avg_weekly_contribution=avg_weekly_contribution,
        city_tier=city_tier,
        avg_performance_ratio=avg_performance_ratio,
        base_rate=base_rate
    )

    eligible_days = min(MAX_DAYS_PER_EVENT, days_remaining)
    total_event_payout = payout_result["daily_payout"] * eligible_days

    return EligibilityResult(
        eligible=len(rejections) == 0,
        rejection_reasons=rejections,
        daily_payout=payout_result["daily_payout"],
        fraud_score=fraud_result["fraud_score"],
        fraud_decision=fraud_result["decision"],
        days_remaining_this_period=days_remaining,
        estimated_total_event_payout=total_event_payout
    )


def process_payout_day(
    db,
    claim_payout,
    rider
) -> dict:
    """
    Process one day's payout for an active claim.
    Called by scheduler daily.
    """
    from database import ClaimPayout, Rider
    from datetime import datetime

    if claim_payout.status not in ["active", "processing"]:
        return {"status": "skipped", "reason": f"claim status is {claim_payout.status}"}

    days_allowed = min(
        MAX_DAYS_PER_EVENT - claim_payout.days_paid,
        MAX_TOTAL_DAYS_PER_PERIOD - rider.total_days_claimed
    )

    if days_allowed <= 0:
        claim_payout.status = "completed"
        claim_payout.last_updated = datetime.utcnow()
        db.commit()
        return {"status": "completed", "reason": "cap_reached"}

    # Simulate UPI transfer
    daily = claim_payout.daily_amount
    claim_payout.days_paid += 1
    claim_payout.total_paid += daily
    rider.total_days_claimed += 1

    if claim_payout.days_paid >= MAX_DAYS_PER_EVENT:
        claim_payout.status = "completed"
    else:
        claim_payout.status = "active"

    claim_payout.last_updated = datetime.utcnow()
    db.commit()

    logger.info(f"Payout ₹{daily} to rider {rider.id} — day {claim_payout.days_paid}")
    return {
        "status": "paid",
        "daily_amount": daily,
        "day_number": claim_payout.days_paid,
        "total_paid": claim_payout.total_paid,
        "upi_simulated": True
    }
