from playwright.sync_api import sync_playwright
import time

BASE = "/Users/joshuaedrake/Documents/alwayshave-fun/screenshots"

def capture(page, url, output_path):
    page.goto(url, wait_until='networkidle', timeout=30000)
    time.sleep(2)
    page.screenshot(path=output_path, full_page=False)
    print(f"Saved: {output_path}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop 1920x1080
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        capture(page, 'https://alwayshave.fun', f'{BASE}/homepage_desktop_1920.png')
        page.close()

        # Laptop 1366x768
        page = browser.new_page(viewport={'width': 1366, 'height': 768})
        capture(page, 'https://alwayshave.fun', f'{BASE}/homepage_laptop_1366.png')
        page.close()

        # Tablet 768x1024
        page = browser.new_page(viewport={'width': 768, 'height': 1024})
        capture(page, 'https://alwayshave.fun', f'{BASE}/homepage_tablet_768.png')
        page.close()

        # Mobile 375x812
        page = browser.new_page(viewport={'width': 375, 'height': 812})
        capture(page, 'https://alwayshave.fun', f'{BASE}/homepage_mobile_375.png')
        page.close()

        # Trail page - Desktop
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        capture(page, 'https://alwayshave.fun/trail.html?trail=red-rock-canyon', f'{BASE}/trail_desktop_1920.png')
        page.close()

        # Trail page - Mobile
        page = browser.new_page(viewport={'width': 375, 'height': 812})
        capture(page, 'https://alwayshave.fun/trail.html?trail=red-rock-canyon', f'{BASE}/trail_mobile_375.png')
        page.close()

        browser.close()
        print("All screenshots captured.")

main()
