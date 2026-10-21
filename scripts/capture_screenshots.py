"""
Script to capture the 3 required PR screenshots for Centralized Incident Manager:
1. incident-summary.png: Metrics summary panel with loaded KPI cards
2. incident-list.png: Incident list with filter toolbar and live table rows
3. incident-form-validation.png: Create form showing visible inline validation errors
"""

import functools
import http.server
import os
import sys
import threading
import time
from pathlib import Path

# Ensure monorepo root is in sys.path and set JWT settings
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ["JWT_SECRET_KEY"] = "a" * 64
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"

import uvicorn
from playwright.sync_api import sync_playwright

from scripts.seed_incidents import seed_incidents
from services.api.main import app

SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"
BACKOFFICE_DIR = REPO_ROOT / "uis" / "backoffice"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def start_backend():
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server


def start_frontend():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(BACKOFFICE_DIR))
    httpd = http.server.HTTPServer(("127.0.0.1", 5502), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def capture_all():
    print("[1/5] Ensuring database is seeded...")
    seed_incidents()

    print("[2/5] Starting backend and frontend servers...")
    backend = start_backend()
    frontend = start_frontend()
    time.sleep(2)  # Give servers time to bind

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[3/5] Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})

        print("[4/5] Navigating to backoffice...")
        page.goto("http://127.0.0.1:5502/#incidencias", wait_until="networkidle")

        # Wait for summary KPI to be populated
        page.wait_for_selector("#sum-total:has-text('96')", timeout=15000)
        page.wait_for_timeout(1000)

        # 1. Capture Summary Panel
        print(" -> Capturing incident-summary.png...")
        summary_el = page.locator("#incident-summary-panel")
        summary_path = SCREENSHOTS_DIR / "incident-summary.png"
        summary_el.screenshot(path=str(summary_path))
        print(f"    Saved: {summary_path}")

        # 2. Capture Incident List
        print(" -> Capturing incident-list.png...")
        page.wait_for_selector(".incidents-table tbody tr", timeout=10000)
        list_section = page.locator(".incidents-list-section")
        list_path = SCREENSHOTS_DIR / "incident-list.png"
        list_section.screenshot(path=str(list_path))
        print(f"    Saved: {list_path}")

        # 3. Capture Form with Validation Errors
        print(" -> Capturing incident-form-validation.png...")
        # Trigger validation by submitting empty form
        page.click("#btn-submit-incident")
        page.wait_for_selector("#create-form-feedback.error", timeout=5000)
        page.wait_for_timeout(500)

        form_box = page.locator(".incident-create-box")
        form_path = SCREENSHOTS_DIR / "incident-form-validation.png"
        form_box.screenshot(path=str(form_path))
        print(f"    Saved: {form_path}")

        browser.close()

    print("[5/5] Cleaning up servers...")
    frontend.shutdown()
    backend.should_exit = True
    print("Done! All 3 PR screenshots successfully captured.")


if __name__ == "__main__":
    capture_all()

