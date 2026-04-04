"""
Weather feed: Open-Meteo (no API key required)
IMD mock alerts for Indian cities
"""
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CITY_COORDS = {
    "Hyderabad": {"lat": 17.38, "lon": 78.49, "tier": 1},
    "Bengaluru": {"lat": 12.97, "lon": 77.59, "tier": 1},
    "Mumbai": {"lat": 19.08, "lon": 72.88, "tier": 1},
    "Chennai": {"lat": 13.08, "lon": 80.27, "tier": 1},
    "Delhi": {"lat": 28.61, "lon": 77.21, "tier": 1},
    "Kolkata": {"lat": 22.57, "lon": 88.36, "tier": 1},
    "Pune": {"lat": 18.52, "lon": 73.86, "tier": 2},
    "Ahmedabad": {"lat": 23.03, "lon": 72.58, "tier": 2},
    "Jaipur": {"lat": 26.91, "lon": 75.79, "tier": 2},
    "Visakhapatnam": {"lat": 17.69, "lon": 83.22, "tier": 2},
    "Surat": {"lat": 21.17, "lon": 72.83, "tier": 2},
    "Lucknow": {"lat": 26.85, "lon": 80.95, "tier": 2},
    "Nagpur": {"lat": 21.15, "lon": 79.09, "tier": 3},
    "Coimbatore": {"lat": 11.02, "lon": 76.96, "tier": 3},
    "Bhubaneswar": {"lat": 20.30, "lon": 85.83, "tier": 3},
}


async def get_weather_for_city(city: str) -> dict:
    """Fetch current weather severity from Open-Meteo."""
    coords = CITY_COORDS.get(city, {"lat": 20.59, "lon": 78.96})
    lat, lon = coords["lat"], coords["lon"]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "precipitation,windspeed_10m,weathercode",
                    "hourly": "precipitation,windspeed_10m",
                    "forecast_days": 1
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                hourly = data.get("hourly", {})

                precip = current.get("precipitation", 0) or 0
                wind = current.get("windspeed_10m", 0) or 0
                wcode = current.get("weathercode", 0) or 0
                max_hourly_precip = max(hourly.get("precipitation", [0]) or [0])

                # Compute severity 0–1
                precip_score = min(max_hourly_precip / 80.0, 1.0)
                wind_score = min(wind / 100.0, 1.0)
                severity = round(max(precip_score, wind_score * 0.7), 3)

                alert_level = "none"
                if severity > 0.75:
                    alert_level = "red"
                elif severity > 0.45:
                    alert_level = "orange"
                elif severity > 0.20:
                    alert_level = "yellow"

                return {
                    "city": city,
                    "severity_score": severity,
                    "alert_level": alert_level,
                    "precipitation_mm": round(precip, 2),
                    "windspeed_kmh": round(wind, 1),
                    "max_hourly_precip": round(max_hourly_precip, 2),
                    "weather_code": wcode,
                    "source": "Open-Meteo",
                    "fetched_at": datetime.utcnow().isoformat()
                }
    except Exception as e:
        logger.warning(f"Open-Meteo fetch failed for {city}: {e}")

    # Fallback: return neutral
    return {
        "city": city,
        "severity_score": 0.1,
        "alert_level": "none",
        "precipitation_mm": 0,
        "windspeed_kmh": 10,
        "max_hourly_precip": 0,
        "weather_code": 0,
        "source": "fallback",
        "fetched_at": datetime.utcnow().isoformat()
    }


async def get_weather_severity_score(city: str) -> float:
    """Convenience function: returns just the 0–1 severity score."""
    result = await get_weather_for_city(city)
    return result["severity_score"]


def get_all_cities() -> list[str]:
    return list(CITY_COORDS.keys())


def get_city_tier(city: str) -> int:
    return CITY_COORDS.get(city, {}).get("tier", 2)