"""
build_index.py — regenerate data/trails-index.json from seeds/trails.csv.
Run after adding new trails to the CSV.
"""
import csv
import json

INDEX_FIELDS = [
    "trail_id", "name", "slug", "state", "region",
    "difficulty", "length_mi", "park_name",
]

def main():
    trails = []
    with open("seeds/trails.csv", newline="", encoding="utf-8") as f:
        next(f)  # skip comment header row
        reader = csv.DictReader(f)
        for row in reader:
            entry = {k: row[k] for k in INDEX_FIELDS}
            entry["status"] = row["trail_status"]
            trails.append(entry)

    with open("data/trails-index.json", "w") as f:
        json.dump(trails, f, indent=2)
    print(f"data/trails-index.json — {len(trails)} trails")

if __name__ == "__main__":
    main()
