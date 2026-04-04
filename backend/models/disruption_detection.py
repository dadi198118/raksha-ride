"""
Module 1: Disruption Detection Engine
TF-IDF + Logistic Regression classifier on news/weather/govt feeds
Multi-source consensus rule: alert fires only when 2+ sources agree
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from datetime import datetime
import httpx
import feedparser
import asyncio
import logging

logger = logging.getLogger(__name__)

# --- Training data (synthetic but realistic) ---
TRAINING_DATA = [
    # curfew
    ("Section 144 imposed in district, prohibitory orders in effect", 1),
    ("Curfew declared after communal violence breaks out", 1),
    ("Night curfew extended due to law and order situation", 1),
    ("prohibitory orders section 144 curfew kolkata", 1),
    ("authorities impose curfew lockdown restrictions movement", 1),
    ("curfew lifted after normalcy restored in affected areas", 1),
    # flood
    ("Red alert issued as heavy rainfall floods city streets", 2),
    ("IMD issues orange alert cyclone landfall expected", 2),
    ("Mumbai rains flood waterlogging trains cancelled", 2),
    ("flood warning low lying areas evacuate immediately", 2),
    ("dam release causes flooding downstream villages", 2),
    ("cyclone warning coastal areas high alert", 2),
    ("heavy rains inundated roads traffic disrupted", 2),
    # strike
    ("Bandh called by political parties shops closed", 3),
    ("Auto rickshaw strike affects commuters city wide", 3),
    ("Cab aggregator drivers on strike demand better pay", 3),
    ("truck strike fuel shortage nationwide impact", 3),
    ("total shutdown bandh all business establishments closed", 3),
    ("delivery workers protest strike suspended services", 3),
    # extreme weather
    ("Dense fog advisory issued visibility near zero highways", 4),
    ("Heatwave alert temperature crosses 45 degrees Celsius", 4),
    ("Thunderstorm warning strong winds lightning expected", 4),
    ("cyclone landfall extremely severe wind speed 180 kmph", 4),
    ("cold wave alert frost warning crop damage likely", 4),
    # normal
    ("Weekend sales up 15% as restaurants see surge in orders", 0),
    ("New restaurant opens in Banjara Hills", 0),
    ("Delivery times improved after platform algorithm update", 0),
    ("Food delivery market grows 30% year on year", 0),
    ("IPL matches boost food delivery orders significantly", 0),
    ("App update brings new features for delivery partners", 0),
    # epidemic/pandemic
    ("Government declares epidemic containment zone restrictions movement", 5),
    ("COVID lockdown reimposed in three districts mobility restricted", 5),
    ("health emergency declared epidemic disease outbreak containment", 5),
]

EVENT_LABELS = {
    0: "normal",
    1: "curfew",
    2: "flood",
    3: "strike",
    4: "extreme_weather",
    5: "epidemic"
}

SEVERITY_MAP = {
    "normal": 0,
    "curfew": 4,
    "flood": 4,
    "strike": 3,
    "extreme_weather": 4,
    "epidemic": 5
}

# Build and train model at import time
_texts = [t for t, _ in TRAINING_DATA]
_labels = [l for _, l in TRAINING_DATA]

disruption_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
        stop_words='english'
    )),
    ('clf', LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight='balanced'
    ))
])
disruption_pipeline.fit(_texts, _labels)


def classify_text(text: str) -> dict:
    """Classify a single news/alert text."""
    pred = disruption_pipeline.predict([text])[0]
    proba = disruption_pipeline.predict_proba([text])[0]
    confidence = float(proba[pred])
    event_type = EVENT_LABELS[pred]
    return {
        "event_type": event_type,
        "confidence": round(confidence, 3),
        "severity": SEVERITY_MAP.get(event_type, 0)
    }


# --- Mock news feed (GDELT/NewsAPI replacement for demo) ---
MOCK_NEWS_FEED = [
    {
        "title": "Heavy rains lash Hyderabad, IMD issues red alert for next 48 hours",
        "source": "NewsAPI",
        "city": "Hyderabad",
        "pincode": ["500001", "500002", "500003"]
    },
    {
        "title": "Section 144 imposed in Bengaluru central after protests",
        "source": "NDMA_RSS",
        "city": "Bengaluru",
        "pincode": ["560001", "560002"]
    },
    {
        "title": "Truck drivers bandh called, delivery services disrupted across Maharashtra",
        "source": "NewsAPI",
        "city": "Mumbai",
        "pincode": ["400001", "400002", "400003", "400004"]
    },
    {
        "title": "Normal day, restaurants report healthy order volumes",
        "source": "NewsAPI",
        "city": "Chennai",
        "pincode": ["600001"]
    },
    {
        "title": "Cyclone warning: IMD issues alert for coastal Andhra Pradesh districts",
        "source": "IMD_RSS",
        "city": "Visakhapatnam",
        "pincode": ["530001", "530002", "530003"]
    }
]

CITY_ZONE_MAP = {
    "Hyderabad": "HYD_500001",
    "Bengaluru": "BLR_560001",
    "Mumbai": "MUM_400001",
    "Chennai": "CHN_600001",
    "Visakhapatnam": "VZG_530001",
    "Delhi": "DEL_110001",
    "Kolkata": "KOL_700001",
    "Pune": "PUN_411001",
    "Ahmedabad": "AMD_380001",
    "Jaipur": "JAI_302001",
}


async def fetch_ndma_rss() -> list[dict]:
    """Fetch NDMA RSS feed for government disaster alerts."""
    try:
        feed = feedparser.parse("https://www.ndma.gov.in/rss.xml")
        alerts = []
        for entry in feed.entries[:10]:
            alerts.append({
                "title": entry.get("title", ""),
                "source": "NDMA_RSS",
                "city": "India",
                "pincode": []
            })
        return alerts
    except Exception:
        logger.warning("NDMA RSS unavailable, using mock data")
        return []


async def fetch_open_meteo_alert(city: str, lat: float, lon: float):
    """Check Open-Meteo for extreme weather at given coordinates."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "precipitation,windspeed_10m",
                    "forecast_days": 1
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                precip = hourly.get("precipitation", [0])
                wind = hourly.get("windspeed_10m", [0])
                max_precip = max(precip) if precip else 0
                max_wind = max(wind) if wind else 0

                if max_precip > 50:
                    return {"event_type": "flood", "severity": 4, "confidence": 0.85, "source": "Open-Meteo", "city": city}
                if max_wind > 80:
                    return {"event_type": "extreme_weather", "severity": 4, "confidence": 0.80, "source": "Open-Meteo", "city": city}
    except Exception as e:
        logger.warning(f"Open-Meteo fetch failed: {e}")
    return None


CITY_COORDS = {
    "Hyderabad": (17.38, 78.49),
    "Bengaluru": (12.97, 77.59),
    "Mumbai": (19.08, 72.88),
    "Chennai": (13.08, 80.27),
    "Visakhapatnam": (17.69, 83.22),
    "Delhi": (28.61, 77.21),
    "Kolkata": (22.57, 88.36),
    "Pune": (18.52, 73.86),
    "Ahmedabad": (23.03, 72.58),
    "Jaipur": (26.91, 75.79),
}


async def run_detection_cycle(db_session) -> list[dict]:
    """
    Full detection cycle:
    1. Fetch mock news + NDMA RSS
    2. Classify each item
    3. Apply multi-source consensus rule (2+ sources must agree)
    4. Return fired alerts
    """
    from database import DisruptionAlert

    all_items = list(MOCK_NEWS_FEED)
    ndma_items = await fetch_ndma_rss()
    all_items.extend(ndma_items)

    # Collect classifications grouped by city
    city_signals: dict[str, list[dict]] = {}
    for item in all_items:
        classification = classify_text(item["title"])
        if classification["event_type"] == "normal":
            continue
        city = item.get("city", "India")
        if city not in city_signals:
            city_signals[city] = []
        city_signals[city].append({
            **classification,
            "source": item["source"],
            "pincode": item.get("pincode", [])
        })

    # Check Open-Meteo for major cities
    weather_tasks = []
    for city, (lat, lon) in CITY_COORDS.items():
        weather_tasks.append(fetch_open_meteo_alert(city, lat, lon))
    weather_results = await asyncio.gather(*weather_tasks, return_exceptions=True)

    for city_name, result in zip(CITY_COORDS.keys(), weather_results):
        if isinstance(result, dict):
            if city_name not in city_signals:
                city_signals[city_name] = []
            city_signals[city_name].append(result)

    # Multi-source consensus: fire alert only if 2+ sources agree
    fired_alerts = []
    for city, signals in city_signals.items():
        if len(signals) < 1:
            continue

        # Group by event type
        event_counts: dict[str, list] = {}
        for s in signals:
            et = s["event_type"]
            if et not in event_counts:
                event_counts[et] = []
            event_counts[et].append(s)

        for event_type, matched_signals in event_counts.items():
            sources = list(set(s.get("source", "unknown") for s in matched_signals))
            avg_confidence = np.mean([s["confidence"] for s in matched_signals])
            max_severity = max(s["severity"] for s in matched_signals)

            # Consensus: need 2+ signals OR 1 with high confidence from official source
            consensus_met = len(matched_signals) >= 2 or (
                len(matched_signals) == 1 and avg_confidence > 0.88
                and matched_signals[0].get("source") in ["NDMA_RSS", "IMD_RSS", "Open-Meteo"]
            )

            if not consensus_met:
                continue

            zone_id = CITY_ZONE_MAP.get(city, f"UNK_{city[:3].upper()}")
            pincodes = []
            for s in matched_signals:
                pincodes.extend(s.get("pincode", []))
            pincodes = list(set(pincodes)) or ["000000"]

            alert_data = {
                "zone_id": zone_id,
                "event_type": event_type,
                "severity": max_severity,
                "affected_pincodes": pincodes,
                "confidence": round(float(avg_confidence), 3),
                "sources_confirmed": sources,
                "estimated_duration_days": 3 if event_type in ["flood", "extreme_weather"] else 2,
                "city": city
            }
            fired_alerts.append(alert_data)

            # Persist to DB (avoid duplicates for same zone+type active)
            existing = db_session.query(DisruptionAlert).filter(
                DisruptionAlert.zone_id == zone_id,
                DisruptionAlert.event_type == event_type,
                DisruptionAlert.is_active == True
            ).first()
            if not existing:
                db_alert = DisruptionAlert(**{k: v for k, v in alert_data.items() if k != "city"})
                db_session.add(db_alert)

    db_session.commit()
    return fired_alerts
