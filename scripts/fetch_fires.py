"""
fetch_fires.py — NASA FIRMS fire hotspot data for trail proximity scoring.

Queries the FIRMS NRT (Near Real-Time) VIIRS I-Band 375m dataset for the
Southwest/Mountain West bounding box, then computes fire proximity for every
trail in seeds/trails.csv and writes per-trail JSON to data/fires/{slug}.json.

Risk → score contribution mapping (feeds into fetch_conditions.py):
  low      — no fires within 100km  → 20 pts
  moderate — 1+ fires 50–100km      → 12 pts
  elevated — 1+ fires within 50km   → 6 pts
  high     — 1+ fires within 20km   → 0 pts
"""

import os
import csv
import json
import math
import requests
from datetime import datetime, timezone

NASA_FIRMS_KEY = os.environ.get("NASA_FIRMS_KEY", "")

# Bounding box covering NV, UT, AZ, CO, CA, NM (west, south, east, north)
BBOX = "-124,32,-102,42"

# Days of data to pull (1 = past 24 hours; max 10 for NRT)
LOOK_BACK_DAYS = 1

# Dataset: VIIRS_SNPP_NRT or MODIS_NRT
DATASET = "VIIRS_SNPP_NRT"


def load_trails(path="seeds/trails.csv"):
    trails = []
    with open(path, newline="", encoding="utf-8") as f:
        next(f)  # skip header comment row
        reader = csv.DictReader(f)
        for row in reader:
            trails.append(row)
    return trails


def fetch_firms_csv():
    """Download FIRMS hotspot CSV for the bounding box."""
    if not NASA_FIRMS_KEY:
        print("  WARNING: NASA_FIRMS_KEY not set — skipping live fire fetch")
        return []

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
        f"/{NASA_FIRMS_KEY}/{DATASET}/{BBOX}/{LOOK_BACK_DAYS}"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        text = r.text.strip()
        if not text or text.startswith("Error") or text.startswith("You"):
            print(f"  FIRMS returned non-data response: {text[:120]}")
            return []
        lines = text.splitlines()
        if len(lines) < 2:
            return []
        reader = csv.DictReader(lines)
        hotspots = []
        for row in reader:
            try:
                hotspots.append({
                    "lat": float(row.get("latitude", 0)),
                    "lng": float(row.get("longitude", 0)),
                    "frp": float(row.get("frp", 0)),      # fire radiative power (MW)
                    "confidence": row.get("confidence", ""),
                })
            except (ValueError, KeyError):
                continue
        print(f"  FIRMS: {len(hotspots)} hotspots fetched")
        return hotspots
    except Exception as e:
        print(f"  FIRMS fetch error: {e}")
        return []


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_risk(hotspots, trail_lat, trail_lng):
    """
    Return (risk_level, nearest_km, count_20km, count_50km, count_100km, score_pts).
    Filters to high-confidence detections only to reduce false positives.
    """
    high_conf = [h for h in hotspots if str(h.get("confidence", "")).lower() in ("high", "h", "nominal", "n", "100", "99", "98", "97", "96", "95")]
    # Fall back to all hotspots if no high-confidence ones
    pool = high_conf if high_conf else hotspots

    nearest_km = float("inf")
    count_20  = 0
    count_50  = 0
    count_100 = 0

    for h in pool:
        d = haversine_km(trail_lat, trail_lng, h["lat"], h["lng"])
        if d < nearest_km:
            nearest_km = d
        if d <= 20:
            count_20 += 1
        if d <= 50:
            count_50 += 1
        if d <= 100:
            count_100 += 1

    if nearest_km == float("inf"):
        nearest_km = None

    if count_20 > 0:
        risk = "high"
        pts  = 0
    elif count_50 > 0:
        risk = "elevated"
        pts  = 6
    elif count_100 > 0:
        risk = "moderate"
        pts  = 12
    else:
        risk = "low"
        pts  = 20

    return {
        "risk_level":        risk,
        "score_pts":         pts,
        "nearest_fire_km":   round(nearest_km, 1) if nearest_km is not None else None,
        "fire_count_20km":   count_20,
        "fire_count_50km":   count_50,
        "fire_count_100km":  count_100,
    }


def process_trail(trail, hotspots):
    slug = trail.get("slug", "").strip()
    lat  = trail.get("lat", "").strip()
    lng  = trail.get("lng", "").strip()

    if not slug or not lat or not lng:
        return

    trail_lat = float(lat)
    trail_lng = float(lng)

    risk_data = classify_risk(hotspots, trail_lat, trail_lng)

    output = {
        "slug":       slug,
        "name":       trail.get("name", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **risk_data,
    }

    out_path = f"data/fires/{slug}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    label = risk_data["risk_level"].upper()
    nearest = risk_data.get("nearest_fire_km")
    dist_str = f"{nearest}km" if nearest else "no fires nearby"
    print(f"    {slug}: {label} ({dist_str})")


def write_summary(trails, hotspots):
    """Write a region-level summary used by the frontend fire/smoke map."""
    regions = {}
    for trail in trails:
        region = trail.get("region", "Unknown")
        slug   = trail.get("slug", "").strip()
        lat    = trail.get("lat", "").strip()
        lng    = trail.get("lng", "").strip()
        if not lat or not lng:
            continue
        risk = classify_risk(hotspots, float(lat), float(lng))
        regions.setdefault(region, []).append(risk["score_pts"])

    summary = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_hotspots": len(hotspots),
        "regions": {}
    }
    for region, pts_list in regions.items():
        avg_pts = sum(pts_list) / len(pts_list)
        if avg_pts >= 18:   level = "low"
        elif avg_pts >= 10: level = "moderate"
        elif avg_pts >= 3:  level = "elevated"
        else:               level = "high"
        summary["regions"][region] = {
            "risk_level":       level,
            "avg_score_pts":    round(avg_pts, 1),
            "trails_monitored": len(pts_list),
        }

    with open("data/fires/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary written → data/fires/summary.json")


def main():
    print(f"fetch_fires.py — {datetime.now(timezone.utc).isoformat()}")
    trails   = load_trails()
    hotspots = fetch_firms_csv()

    print(f"  Processing {len(trails)} trails against {len(hotspots)} hotspots…")
    for trail in trails:
        process_trail(trail, hotspots)

    write_summary(trails, hotspots)
    print("Done.")


if __name__ == "__main__":
    main()
