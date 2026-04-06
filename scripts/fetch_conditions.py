import os
import json
import csv
import requests
from datetime import datetime, timezone

AIRNOW_KEY = os.environ.get("AIRNOW_KEY", "")
WAQI_KEY   = os.environ.get("WAQI_KEY", "")

def load_trails(path="seeds/trails.csv"):
    trails = []
    with open(path, newline="", encoding="utf-8") as f:
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            trails.append(row)
    return trails

def fetch_weather(lat, lng, retries=3, backoff=5):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        f"&current=temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,precipitation_probability"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max,sunrise,sunset"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5"
    )
    import time
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            if "current" in data:
                return data
            print(f"  weather: no 'current' in response (attempt {attempt+1}): {str(data)[:120]}")
        except Exception as e:
            print(f"  weather error (attempt {attempt+1}): {e}")
        if attempt < retries - 1:
            time.sleep(backoff * (attempt + 1))
    return None

def _aqi_category(aqi):
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Moderate"
    if aqi <= 150:  return "Unhealthy for Sensitive Groups"
    if aqi <= 200:  return "Unhealthy"
    if aqi <= 300:  return "Very Unhealthy"
    return "Hazardous"

def fetch_aqi(lat, lng):
    # Primary: AirNow (ground-level monitors, US only)
    if AIRNOW_KEY:
        url = (
            f"https://www.airnowapi.org/aq/observation/latLong/current/"
            f"?format=application/json&latitude={lat}&longitude={lng}"
            f"&distance=75&API_KEY={AIRNOW_KEY}"
        )
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data:
                best = sorted(data, key=lambda x: x.get("AQI", 0), reverse=True)[0]
                return {
                    "aqi":       best.get("AQI"),
                    "category":  best.get("Category", {}).get("Name", "Unknown"),
                    "pollutant": best.get("ParameterName", ""),
                    "source":    "airnow"
                }
        except Exception as e:
            print(f"  AQI (AirNow) error: {e}")

    # Fallback: Open-Meteo Air Quality (CAMS satellite, global coverage, no key required)
    try:
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lng}"
            f"&current=us_aqi,pm2_5"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        aqi_val = data.get("current", {}).get("us_aqi")
        if aqi_val is not None:
            aqi_int = round(aqi_val)
            return {
                "aqi":       aqi_int,
                "category":  _aqi_category(aqi_int),
                "pollutant": "PM2.5",
                "source":    "open-meteo"
            }
    except Exception as e:
        print(f"  AQI (Open-Meteo fallback) error: {e}")

    return {"aqi": None, "category": "Unknown", "pollutant": "", "source": "none"}

def fetch_river(gauge_id):
    if not gauge_id or not gauge_id.strip():
        return None
    url = (
        f"https://waterservices.usgs.gov/nwis/iv/"
        f"?sites={gauge_id.strip()}&parameterCd=00060&format=json"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        series = data["value"]["timeSeries"]
        if not series:
            return None
        values = series[0]["values"][0]["value"]
        if not values:
            return None
        cfs = float(values[-1]["value"])
        if cfs < 100:   stage = "low"
        elif cfs < 500: stage = "normal"
        elif cfs < 2000: stage = "high"
        else:            stage = "flood"
        return {"cfs": round(cfs), "stage": stage}
    except Exception as e:
        print(f"  river error ({gauge_id}): {e}")
        return None

def load_fire_data(slug):
    """Load fire proximity data written by fetch_fires.py, fallback to 20 pts."""
    path = f"data/fires/{slug}.json"
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"score_pts": 20, "risk_level": "unknown"}


def compute_score(weather, aqi_data, fire_data=None):
    score = 0

    # Weather — 40 pts
    if weather and "current" in weather:
        c    = weather["current"]
        temp = c.get("temperature_2m", 999)
        wind = c.get("wind_speed_10m", 999)
        rain = c.get("precipitation_probability", 100)
        if 50 <= temp <= 75 and wind < 15 and rain < 10:
            score += 40
        elif 40 <= temp <= 85 and wind <= 25 and rain <= 30:
            score += 28
        elif 35 <= temp <= 95 and wind <= 35 and rain <= 60:
            score += 10

    # AQI — 30 pts
    aqi = aqi_data.get("aqi") or 999
    if aqi <= 50:    score += 30
    elif aqi <= 100: score += 20
    elif aqi <= 150: score += 10

    # Fire risk — 20 pts (from fetch_fires.py; fallback 20 if no data)
    score += (fire_data or {}).get("score_pts", 20)

    # Closure status — 10 pts (hardcoded open until USFS scraper is integrated)
    score += 10

    return min(score, 100)

def _forecast_score(high_f, rain_pct, current_aqi=999, current_fire_pts=20):
    """Simplified daily score from forecast data — no per-day wind or AQI."""
    score = 0
    if 50 <= high_f <= 75 and rain_pct < 10:       score += 40
    elif 40 <= high_f <= 85 and rain_pct <= 30:    score += 28
    elif 35 <= high_f <= 95 and rain_pct <= 60:    score += 10
    aqi = current_aqi if current_aqi < 999 else 999
    if aqi <= 50:    score += 30
    elif aqi <= 100: score += 20
    elif aqi <= 150: score += 10
    score += current_fire_pts  # carry forward current fire data
    score += 10                # assume open
    return min(score, 100)

def score_label(score):
    if score >= 85: return "Great day to go"
    if score >= 70: return "Good conditions"
    if score >= 50: return "Use caution"
    if score >= 30: return "Conditions poor"
    return "Stay home"

def gear_flags(weather, aqi_data, fire_data=None):
    flags = []
    if weather and "current" in weather:
        c = weather["current"]
        if c.get("wind_gusts_10m", 0) > 20:
            flags.append("wind layer recommended")
        if c.get("temperature_2m", 70) < 45:
            flags.append("insulation layer required")
        if c.get("precipitation_probability", 0) > 40:
            flags.append("rain gear recommended")
    aqi = aqi_data.get("aqi") or 0
    if aqi > 100:
        flags.append("N95 mask recommended")
    elif aqi > 50:
        flags.append("mask for sensitive groups")
    if fire_data and fire_data.get("risk_level") in ("elevated", "high"):
        flags.append("N95 mask recommended for wildfire smoke")
    return list(dict.fromkeys(flags))  # deduplicate, preserve order

def process_trail(trail):
    slug      = trail.get("slug", "").strip()
    lat       = trail.get("lat", "").strip()
    lng       = trail.get("lng", "").strip()
    gauge_id  = trail.get("usgs_gauge_id", "").strip()

    if not slug or not lat or not lng:
        print(f"  skipping {trail.get('name')} — missing slug/coords")
        return

    print(f"  fetching: {trail.get('name')}")

    # Load existing data so we can fall back to it if API fails
    existing = {}
    existing_path = f"data/conditions/{slug}.json"
    try:
        with open(existing_path) as f:
            existing = json.load(f)
    except Exception:
        pass

    weather   = fetch_weather(lat, lng)
    aqi_data  = fetch_aqi(lat, lng)
    river     = fetch_river(gauge_id)
    fire_data = load_fire_data(slug)
    score     = compute_score(weather, aqi_data, fire_data)

    current  = existing.get("current", {})  # preserve last-known data on failure
    forecast = []  # always rebuild forecast fresh — never accumulate across runs

    if weather:
        c = weather.get("current", {})
        current = {
            "temp_f":       round(c.get("temperature_2m", 0)),
            "feels_like_f": round(c.get("apparent_temperature", 0)),
            "wind_mph":     round(c.get("wind_speed_10m", 0)),
            "gusts_mph":    round(c.get("wind_gusts_10m", 0)),
            "rain_pct":     round(c.get("precipitation_probability", 0)),
        }
        daily   = weather.get("daily", {})
        sunrise = daily.get("sunrise", [])
        sunset  = daily.get("sunset",  [])
        aqi_val      = aqi_data.get("aqi") or 999
        fire_pts     = (fire_data or {}).get("score_pts", 20)
        for i, day in enumerate(daily.get("time", [])):
            hi       = round(daily.get("temperature_2m_max",          [0]*10)[i])
            rain     = round(daily.get("precipitation_probability_max",[0]*10)[i])
            day_score = _forecast_score(hi, rain, aqi_val, fire_pts)
            forecast.append({
                "date":            day,
                "high_f":          hi,
                "low_f":           round(daily.get("temperature_2m_min", [0]*10)[i]),
                "rain_pct":        rain,
                "uv":              round(daily.get("uv_index_max",        [0]*10)[i]),
                "sunrise":         sunrise[i] if i < len(sunrise) else "",
                "sunset":          sunset[i]  if i < len(sunset)  else "",
                "predicted_score": day_score,
                "score_label":     score_label(day_score),
            })

    output = {
        "trail_id":    trail.get("trail_id"),
        "name":        trail.get("name"),
        "slug":        slug,
        "state":       trail.get("state"),
        "region":      trail.get("region"),
        "lat":         lat,
        "lng":         lng,
        "difficulty":  trail.get("difficulty"),
        "length_mi":   trail.get("length_mi"),
        "gain_ft":     trail.get("gain_ft"),
        "best_months": trail.get("best_months"),
        "trail_type":  trail.get("trail_type"),
        "park_name":   trail.get("park_name"),
        "alerts_url":  trail.get("alerts_url"),
        "status":      trail.get("trail_status", "Unknown"),
        "notes":        trail.get("notes"),
        "dog_friendly": trail.get("dog_friendly", ""),
        "vehicle_req":  trail.get("vehicle_req", "Any"),
        "score":       score,
        "score_label": score_label(score),
        "gear_flags":  gear_flags(weather, aqi_data, fire_data),
        "current":     current,
        "aqi":         aqi_data,
        "fire":        {"risk_level": fire_data.get("risk_level", "unknown"),
                        "nearest_fire_km": fire_data.get("nearest_fire_km"),
                        "fire_count_50km": fire_data.get("fire_count_50km", 0)},
        "river":       river,
        "forecast":    forecast,
        "updated_at":  datetime.now(timezone.utc).isoformat(),
    }

    out_path = f"data/conditions/{slug}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"    saved -> {out_path}")

def main():
    print(f"Starting fetch — {datetime.now(timezone.utc).isoformat()}")
    trails = load_trails()
    print(f"Loaded {len(trails)} trails")
    for trail in trails:
        process_trail(trail)
    meta = {
        "last_run":    datetime.now(timezone.utc).isoformat(),
        "trail_count": len(trails)
    }
    with open("data/meta/last_updated.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()