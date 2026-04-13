from playwright.sync_api import sync_playwright
import time

BASE = "/Users/joshuaedrake/Documents/alwayshave-fun/screenshots"

def capture(page, url, output_path):
    page.goto(url, wait_until='networkidle', timeout=30000)
    time.sleep(3)
    page.screenshot(path=output_path, full_page=False)
    print(f"Saved: {output_path}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Try a valid trail slug
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        capture(page, 'https://alwayshave.fun/trail.html?trail=angels-landing-zion-ut', f'{BASE}/trail_desktop_1920_v2.png')
        page.close()

        page = browser.new_page(viewport={'width': 375, 'height': 812})
        capture(page, 'https://alwayshave.fun/trail.html?trail=angels-landing-zion-ut', f'{BASE}/trail_mobile_375_v2.png')
        page.close()

        browser.close()
        print("Done.")

main()
