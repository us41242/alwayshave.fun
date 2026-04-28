"""
indexnow.py — Ping Bing and Yandex with updated URLs via IndexNow protocol.

Runs after every conditions update. Submits all trail URLs + state pages
so Bing/Yandex index fresh conditions data without waiting for a crawl.

Key is read from env INDEXNOW_KEY (set as GitHub Actions secret).
The key file must exist at /{key}.txt on the domain — we write it to repo root.
"""

import os
import json
import glob
import requests

BASE_URL     = "https://alwayshave.fun"
DATA_DIR     = "data/conditions"
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

STATES = ["nv", "ut", "az", "co", "ca"]


def collect_urls():
    urls = [BASE_URL + "/", f"{BASE_URL}/dog-friendly"]
    for state in STATES:
        urls.append(f"{BASE_URL}/{state}")

    for path in glob.glob(f"{DATA_DIR}/*.json"):
        try:
            with open(path) as f:
                d = json.load(f)
            slug  = d.get("slug", "")
            state = (d.get("state") or "").lower()
            if slug and state:
                urls.append(f"{BASE_URL}/{state}/{slug}")
        except Exception:
            pass

    return urls


def ensure_key_file():
    """Write the IndexNow key verification file to repo root."""
    if not INDEXNOW_KEY:
        return
    key_path = f"{INDEXNOW_KEY}.txt"
    if not os.path.exists(key_path):
        with open(key_path, "w") as f:
            f.write(INDEXNOW_KEY)
        print(f"  Created key file: {key_path}")


def submit_batch(urls, host):
    if not INDEXNOW_KEY:
        print("  INDEXNOW_KEY not set — skipping IndexNow submission")
        return

    payload = {
        "host":    host,
        "key":     INDEXNOW_KEY,
        "keyLocation": f"https://{host}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    try:
        r = requests.post(
            INDEXNOW_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        print(f"  IndexNow → {r.status_code} ({len(urls)} URLs)")
    except Exception as e:
        print(f"  IndexNow error: {e}")


def main():
    host = BASE_URL.replace("https://", "")
    ensure_key_file()
    urls = collect_urls()
    print(f"IndexNow: submitting {len(urls)} URLs to Bing/Yandex")
    # IndexNow accepts up to 10,000 URLs per batch; we're well under that
    submit_batch(urls, host)


if __name__ == "__main__":
    main()
