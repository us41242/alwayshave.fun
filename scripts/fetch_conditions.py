import os
import json
import csv
import requests
from datetime import datetime, timezone

AIRNOW_KEY = os.environ.get("AIRNOW_KEY", "")

def load_trails(path="seeds/trails.csv"):
    trails = []
    with open(path, newline="", encoding="utf-8") as f:
        next(f)
        reader = csv.DictReader(f)
        for row in reader:
            trails.append(row)
    return trails

def fetch_weather(lat, lng):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        f"&current=temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,precipitation_probability"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max"
        f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  weather error: {e}")
        return None

def fetch_aqi(lat, lng):
    url = (
        f"https://www.airnowapi.org/aq/observation/latLong/current/"
        f"?format=application/json&latitude={lat}&longitude={lng}"
        f"&distance=25&API_KEY={AIRNOW_KEY}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data:
            best = sorted(data, key=lambda x: x.get("AQI", 0), reverse=True)[0]
            return {
                "aqi": best.get("AQI"),
                "category": best.get("Category", {}).get("Name", "Unknown"),
                "pollutant": best.get("ParameterName", "")
            }
    except Exception as e:
        print(f"  AQI error: {e}")
    return {"aqi": None, "category": "Unknown", "pollutant": ""}

def compute_score(weather, aqi_data):
    score = 0
    if weather and "current" in weather:
        c = weather["current"]
        temp  = c.get("temperature_2m", 999)
        wind  = c.get("wind_speed_10m", 999)
        rain  = c.get("precipitation_probability", 100)
        if 50 <= temp <= 75 and wind < 15 and rain < 10:
            score += 40
        elif 40 <= temp <= 85 and wind <= 25 and rain <= 30:
            score += 28
        elif 35 <= temp <= 95 and wind <= 35 and rain <= 60:
            score += 10
    aqi = aqi_data.get("aqi") or 999
    if aqi <= 50:   score += 30
    elif aqi <= 100: score += 20
    elif aqi <= 150: score += 10
    score += 20
    score += 10
    return min(score, 100)

def score_label(score):
    if score >= 85: return "Great day to go"
    if score >= 70: return "Good conditions"
    if score >= 50: return "Use caution"
    if score >= 30: return "Conditions poor"
    return "Stay home"

def gear_flags(weather, aqi_data):
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
    if aqi > 100:  flags.append("N95 mask recommended")
    elif aqi > 50: flags.append("mask for sensitive groups")
    return flags

def process_trail(trail):
    slug = trail.get("slug", "").strip()
    lat  = trail.get("lat", "").strip()
    lng  = trail.get("lng", "").strip()
    if not slug or not lat or not lng:
        print(f"  skipping {trail.get('name')} — missing slug/coords")
        return
    print(f"  fetching: {trail.get('name')}")
    weather  = fetch_weather(lat, lng)
    aqi_data = fetch_aqi(lat, lng)
    score    = compute_score(weather, aqi_data)
    current = {}
    forecast = []
    if weather:
        c = weather.get("current", {})
        current = {
            "temp_f":       round(c.get("temperature_2m", 0)),
            "feels_like_f": round(c.get("apparent_temperature", 0)),
            "wind_mph":     round(c.get("wind_speed_10m", 0)),
            "gusts_mph":    round(c.get("wind_gusts_10m", 0)),
            "rain_pct":     round(c.get("precipitation_probability", 0)),
        }
        daily = weather.get("daily", {})
        for i, day in enumerate(daily.get("time", [])):
            forecast.append({
                "date":     day,
                "high_f":   round(daily.get("temperature_2m_max", [0]*10)[i]),
                "low_f":    round(daily.get("temperature_2m_min",  [0]*10)[i]),
                "rain_pct": round(daily.get("precipitation_probability_max", [0]*10)[i]),
                "uv":       round(daily.get("uv_index_max", [0]*10)[i]),
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
        "status":      trail.get("trail_status", "Unknown"),
        "score":       score,
        "score_label": score_label(score),
        "gear_flags":  gear_flags(weather, aqi_data),
        "current":     current,
        "aqi":         aqi_data,
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
    meta = {"last_run": datetime.now(timezone.utc).isoformat(), "trail_count": len(trails)}
    with open("data/meta/last_updated.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    main()
