"""
Raksha Ride — 5 Automated Trigger System
Each trigger independently detects a different class of disruption.
Triggers 1-3 use real public APIs. Triggers 4-5 use simulation.
"""
import httpx
import feedparser
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── TRIGGER 1: Open-Meteo Weather API (Real, Free, No Key) ──────────────────
# Fires when rainfall > 50mm/hr OR wind > 80 km/h in rider's city

CITY_COORDS = {
    "Hyderabad":     {"lat": 17.38, "lon": 78.49},
    "Bengaluru":     {"lat": 12.97, "lon": 77.59},
    "Mumbai":        {"lat": 19.08, "lon": 72.88},
    "Chennai":       {"lat": 13.08, "lon": 80.27},
    "Delhi":         {"lat": 28.61, "lon": 77.21},
    "Kolkata":       {"lat": 22.57, "lon": 88.36},
    "Pune":          {"lat": 18.52, "lon": 73.86},
    "Ahmedabad":     {"lat": 23.03, "lon": 72.58},
    "Jaipur":        {"lat": 26.91, "lon": 75.79},
    "Visakhapatnam": {"lat": 17.69, "lon": 83.22},
}

async def trigger_1_weather(city: str) -> dict:
    """
    TRIGGER 1 — Open-Meteo Weather API
    Real API, no key needed. Fires on extreme rainfall or wind.
    """
    coords = CITY_COORDS.get(city, {"lat": 17.38, "lon": 78.49})
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":  coords["lat"],
                    "longitude": coords["lon"],
                    "hourly":    "precipitation,windspeed_10m",
                    "current":   "precipitation,windspeed_10m,weathercode",
                    "forecast_days": 1,
                }
            )
            if resp.status_code == 200:
                data    = resp.json()
                hourly  = data.get("hourly", {})
                current = data.get("current", {})
                max_precip = max(hourly.get("precipitation", [0]) or [0])
                max_wind   = max(hourly.get("windspeed_10m",  [0]) or [0])
                cur_precip = current.get("precipitation", 0) or 0
                cur_wind   = current.get("windspeed_10m",  0) or 0

                fired  = max_precip > 50 or max_wind > 80
                reason = []
                if max_precip > 50: reason.append(f"Rainfall {max_precip:.1f}mm/hr > 50mm threshold")
                if max_wind   > 80: reason.append(f"Wind {max_wind:.1f}km/h > 80km/h threshold")

                severity_score = min(max(max_precip/80, max_wind/100), 1.0)

                return {
                    "trigger": "T1_WEATHER",
                    "source":  "Open-Meteo (live API)",
                    "fired":   fired,
                    "city":    city,
                    "event_type": "extreme_weather" if max_wind > 80 else "flood",
                    "severity_score": round(severity_score, 3),
                    "current_precipitation_mm": cur_precip,
                    "current_windspeed_kmh":    cur_wind,
                    "max_hourly_precip":  round(max_precip, 2),
                    "max_hourly_wind":    round(max_wind,   2),
                    "reason": reason if reason else ["Within normal range"],
                    "timestamp": datetime.utcnow().isoformat(),
                }
    except Exception as e:
        logger.warning(f"T1 Weather trigger failed: {e}")

    return {
        "trigger": "T1_WEATHER", "source": "Open-Meteo (fallback)",
        "fired": False, "city": city, "error": str(e) if 'e' in dir() else "timeout",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── TRIGGER 2: NDMA RSS Feed (Real Government Feed) ─────────────────────────
# Fires when National Disaster Management Authority posts new alerts

DISASTER_KEYWORDS = [
    "flood", "cyclone", "earthquake", "landslide", "alert",
    "warning", "disaster", "emergency", "evacuation", "curfew"
]

async def trigger_2_ndma_rss() -> dict:
    """
    TRIGGER 2 — NDMA Government RSS Feed
    Real public RSS from India's disaster authority.
    """
    try:
        feed = feedparser.parse("https://www.ndma.gov.in/rss.xml")
        alerts_found = []
        for entry in feed.entries[:10]:
            title = entry.get("title", "").lower()
            summary = entry.get("summary", "").lower()
            text = title + " " + summary
            matched = [kw for kw in DISASTER_KEYWORDS if kw in text]
            if matched:
                alerts_found.append({
                    "title":    entry.get("title", ""),
                    "keywords": matched,
                    "link":     entry.get("link", ""),
                })

        fired = len(alerts_found) > 0
        return {
            "trigger":      "T2_NDMA_RSS",
            "source":       "NDMA Government RSS Feed",
            "fired":        fired,
            "alerts_count": len(alerts_found),
            "alerts":       alerts_found[:3],
            "reason":       f"{len(alerts_found)} disaster keywords matched in NDMA feed" if fired
                            else "No disaster keywords in NDMA feed",
            "timestamp":    datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"T2 NDMA trigger failed: {e}")
        return {
            "trigger": "T2_NDMA_RSS", "source": "NDMA RSS (unavailable)",
            "fired": False, "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ─── TRIGGER 3: Zone Order Volume Drop (Platform Webhook Simulation) ──────────
# Fires when simulated platform data shows >65% drop in 2-hour window

ZONE_HOURLY_BASELINES = {
    "HYD_500001": 155, "BLR_560001": 180, "MUM_400001": 210,
    "CHN_600001": 140, "DEL_110001": 240, "KOL_700001": 130,
    "PUN_411001": 110, "AMD_380001": 100, "VZG_530001": 95,
}

def trigger_3_order_volume_drop(zone_id: str, disruption_factor: float = 1.0) -> dict:
    """
    TRIGGER 3 — Platform Order Volume Drop
    Simulates Swiggy/Zomato webhook: if zone volume drops >65% in 2 hrs, trigger fires.
    In production this would be a real webhook from the platform.
    disruption_factor: 1.0 = normal, 0.3 = severe drop
    """
    import random
    random.seed(42)
    baseline = ZONE_HOURLY_BASELINES.get(zone_id, 120)
    current  = int(baseline * disruption_factor * random.uniform(0.92, 1.08))
    drop_pct = round((1 - current / baseline) * 100, 1)
    fired    = drop_pct > 65

    return {
        "trigger":       "T3_ORDER_VOLUME",
        "source":        "Platform Webhook (Swiggy/Zomato simulation)",
        "fired":         fired,
        "zone_id":       zone_id,
        "baseline_hourly": baseline,
        "current_hourly":  current,
        "drop_pct":       drop_pct,
        "threshold_pct":  65,
        "reason":        f"Volume dropped {drop_pct}% — exceeds 65% threshold" if fired
                         else f"Volume within normal range (drop: {drop_pct}%)",
        "event_type":    "zone_volume_crash",
        "timestamp":     datetime.utcnow().isoformat(),
    }


# ─── TRIGGER 4: News Keyword Classifier (TF-IDF ML model) ────────────────────
# Fires when news text is classified as a disruption event by the ML model

def trigger_4_news_classifier(headlines: list[str]) -> dict:
    """
    TRIGGER 4 — AI News Classifier
    Runs headlines through the TF-IDF + Logistic Regression model.
    In production: polls NewsAPI/GDELT every 30 min. Here we use mock headlines.
    """
    from models.disruption_detection import classify_text, MOCK_NEWS_FEED

    # Use mock feed headlines if no headlines provided
    if not headlines:
        headlines = [item["title"] for item in MOCK_NEWS_FEED]

    results   = []
    triggered = []
    for headline in headlines:
        classification = classify_text(headline)
        result = {
            "headline":   headline[:80],
            "event_type": classification["event_type"],
            "confidence": classification["confidence"],
            "severity":   classification["severity"],
        }
        results.append(result)
        if classification["event_type"] != "normal" and classification["confidence"] > 0.20:
            triggered.append(result)

    fired = len(triggered) > 0
    return {
        "trigger":          "T4_NEWS_CLASSIFIER",
        "source":           "TF-IDF + Logistic Regression (AI model)",
        "fired":            fired,
        "headlines_scanned": len(headlines),
        "disruptions_found": len(triggered),
        "classified":       results,
        "triggered_events": triggered,
        "reason":           f"{len(triggered)} disruption headlines detected" if fired
                            else "All headlines classified as normal",
        "timestamp":        datetime.utcnow().isoformat(),
    }


# ─── TRIGGER 5: Zone Anomaly Statistical Detector ────────────────────────────
# Fires when zone ZDI drops below 0.60 (Z-score + Isolation Forest)

def trigger_5_zone_anomaly(zone_id: str, current_deliveries: int) -> dict:
    """
    TRIGGER 5 — Zone Anomaly Engine
    Computes ZDI from 8-week rolling baseline.
    Confirms with Isolation Forest. Fires if significant anomaly detected.
    """
    from models.zone_anomaly import (
        compute_zone_delivery_index,
        run_isolation_forest,
    )
    from data_ingestion.platform_webhook import get_zone_baseline

    baseline = get_zone_baseline(zone_id)
    zdi_result = compute_zone_delivery_index(zone_id, current_deliveries, baseline)

    # Run Isolation Forest with simulated zone-level features
    baseline_avg  = sum(baseline) / len(baseline)
    active_riders = max(1, int(current_deliveries / 12))
    drop_ratio    = current_deliveries / baseline_avg if baseline_avg > 0 else 1.0
    weather_sev   = 0.8 if drop_ratio < 0.5 else 0.1
    cancel_rate   = 0.30 if drop_ratio < 0.5 else 0.04

    iso_result = run_isolation_forest(
        total_deliveries=current_deliveries,
        active_riders=active_riders,
        avg_order_value=280.0,
        weather_severity=weather_sev,
        cancellation_rate=cancel_rate,
    )

    fired = zdi_result["anomaly"] and iso_result["is_anomaly"]
    return {
        "trigger":   "T5_ZONE_ANOMALY",
        "source":    "Z-score + Isolation Forest (AI model)",
        "fired":     fired,
        "zone_id":   zone_id,
        "zdi":       zdi_result["zdi"],
        "zdi_status": zdi_result["status"],
        "z_score":   zdi_result["z_score"],
        "baseline_avg": zdi_result["baseline_mean"],
        "current_deliveries": current_deliveries,
        "isolation_confirmed": iso_result["is_anomaly"],
        "likely_cause": iso_result["likely_cause"],
        "context_protection": fired,
        "reason":    f"ZDI={zdi_result['zdi']} + Isolation Forest confirms anomaly: {iso_result['likely_cause']}"
                     if fired else f"ZDI={zdi_result['zdi']} — zone normal",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─── Run All Triggers ─────────────────────────────────────────────────────────

async def run_all_triggers(
    city: str = "Hyderabad",
    zone_id: str = "HYD_500001",
    current_deliveries: int = 500,
    disruption_factor: float = 1.0,
    custom_headlines: list = None,
) -> dict:
    """Run all 5 triggers and return consolidated result."""
    t1, t2 = await asyncio.gather(
        trigger_1_weather(city),
        trigger_2_ndma_rss(),
        return_exceptions=True
    )
    t3 = trigger_3_order_volume_drop(zone_id, disruption_factor)
    t4 = trigger_4_news_classifier(custom_headlines or [])
    t5 = trigger_5_zone_anomaly(zone_id, current_deliveries)

    triggers = [
        t1 if isinstance(t1, dict) else {"trigger": "T1_WEATHER", "fired": False, "error": str(t1)},
        t2 if isinstance(t2, dict) else {"trigger": "T2_NDMA_RSS", "fired": False, "error": str(t2)},
        t3, t4, t5
    ]

    fired_count = sum(1 for t in triggers if t.get("fired"))
    return {
        "summary": {
            "total_triggers": 5,
            "fired": fired_count,
            "all_clear": fired_count == 0,
            "consensus_alert": fired_count >= 2,
        },
        "triggers": triggers,
        "timestamp": datetime.utcnow().isoformat(),
    }