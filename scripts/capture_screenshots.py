"""Capture the real local Swagger and Streamlit pages for the lab report.

Run both servers first, then install a Playwright browser with
`python -m playwright install chromium` and run this script.
Set CHROMIUM_PATH to use a system Chromium instead.
"""

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "screenshots"


def capture():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        options = {"headless": True}
        if os.getenv("CHROMIUM_PATH"):
            options["executable_path"] = os.environ["CHROMIUM_PATH"]
        browser = playwright.chromium.launch(**options)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.goto("http://127.0.0.1:8000/docs", wait_until="networkidle")
        page.locator(".swagger-ui .opblock").first.wait_for()
        page.screenshot(path=str(OUTPUT / "swagger.png"), full_page=True)

        get_rooms = page.locator(".opblock-get").filter(has=page.locator('[data-path="/rooms"]'))
        get_rooms.locator(".opblock-summary").click()
        get_rooms.get_by_role("button", name="Try it out").click()
        get_rooms.locator("button.execute").click()
        get_rooms.locator(".live-responses-table").wait_for()
        assert "200" in get_rooms.locator(".live-responses-table").inner_text()
        get_rooms.screenshot(path=str(OUTPUT / "swagger_get.png"))
        get_rooms.locator(".opblock-summary").click()

        post_rooms = page.locator(".opblock-post").filter(has=page.locator('[data-path="/rooms"]'))
        post_rooms.locator(".opblock-summary").click()
        post_rooms.get_by_role("button", name="Try it out").click()
        post_rooms.locator("textarea").fill(json.dumps({
            "category_id": 1, "room_number": "DEMO", "price_per_night": -100, "capacity": 2,
        }))
        post_rooms.locator("button.execute").click()
        post_rooms.locator(".live-responses-table").wait_for()
        assert "422" in post_rooms.locator(".live-responses-table").inner_text()
        post_rooms.screenshot(path=str(OUTPUT / "swagger_validation.png"))

        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("heading", name="Нөмірлер каталогы").wait_for(timeout=30000)
        page.locator('[data-testid="stDataFrame"]').first.wait_for()
        assert page.locator('[data-testid="stException"]').count() == 0
        page.screenshot(path=str(OUTPUT / "frontend.png"), full_page=True)
        page.get_by_text("Брондаулар", exact=True).first.click()
        page.get_by_role("heading", name="Брондаулар").wait_for()
        assert page.locator('[data-testid="stException"]').count() == 0
        page.screenshot(path=str(OUTPUT / "frontend_bookings.png"), full_page=True)
        browser.close()
    print("Captured Swagger GET 200, invalid POST 422, and both Streamlit screens.")


if __name__ == "__main__":
    capture()
