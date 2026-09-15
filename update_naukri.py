import json
import os
import re
import time
from playwright.sync_api import sync_playwright

STATE_JSON_CONTENT = os.environ.get("NAUKRI_STATE_JSON")
RESUME_PATH = os.path.abspath("resume.pdf")

PROXY_HOST = os.environ.get("PROXY_HOST")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USER = os.environ.get("PROXY_USER")
PROXY_PASS = os.environ.get("PROXY_PASS")

if not os.path.exists(RESUME_PATH):
    raise FileNotFoundError("resume.pdf not found in root directory!")

if not STATE_JSON_CONTENT:
    raise ValueError("NAUKRI_STATE_JSON secret is missing or empty!")

def sanitize_cookies(raw_json_str):
    data = json.loads(raw_json_str)
    if isinstance(data, list):
        cookies = data
        state_data = {"cookies": cookies, "origins": []}
    else:
        cookies = data.get("cookies", [])
        state_data = data

    for cookie in cookies:
        raw_same_site = str(cookie.get("sameSite", "")).lower()
        if "strict" in raw_same_site:
            cookie["sameSite"] = "Strict"
        elif "lax" in raw_same_site:
            cookie["sameSite"] = "Lax"
        elif "none" in raw_same_site or "no_restriction" in raw_same_site:
            cookie["sameSite"] = "None"
        else:
            cookie["sameSite"] = "Lax"

    return state_data

def open_headline_editor(page):
    edit_btn = page.locator(
        "div.widgetHead:has-text('Resume headline') span.edit, span.editRow.icon:has-text('editOneTheme')"
    ).first
    edit_btn.wait_for(state="visible", timeout=25000)
    edit_btn.click()
    page.wait_for_selector("#resumeHeadlineTxt", state="visible", timeout=25000)

def save_headline(page):
    save_btn = page.locator("button:has-text('Save')").first
    save_btn.click()
    page.wait_for_timeout(3000)

def run():
    sanitized_state = sanitize_cookies(STATE_JSON_CONTENT)
    with open("session_state.json", "w", encoding="utf-8") as f:
        json.dump(sanitized_state, f)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )

        context_kwargs = {
            "storage_state": "session_state.json",
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        # Configure Webshare proxy if variables are present
        if PROXY_HOST and PROXY_PORT:
            context_kwargs["proxy"] = {
                "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
                "username": PROXY_USER,
                "password": PROXY_PASS
            }
            print(f"Routing through Webshare proxy: {PROXY_HOST}:{PROXY_PORT}")

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        try:
            print("Navigating to profile...")
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="load", timeout=60000)
            page.wait_for_timeout(5000)

            if "Access Denied" in page.title() or "login" in page.url:
                raise PermissionError(f"Access still blocked. Title: {page.title()}, URL: {page.url}")

            # Step 1: Remove 'E'/'e' from 'YOE'/'yoe'
            print("Step 1: Removing 'E' from 'YOE'...")
            open_headline_editor(page)
            headline_input = page.locator("#resumeHeadlineTxt")
            text = headline_input.input_value()
            temp_text = re.sub(r"(?i)\byoe\b", lambda m: m.group(0)[:-1], text, count=1)
            headline_input.fill(temp_text)
            save_headline(page)
            print(f"Step 1 Complete: Saved as '{temp_text}'")
            page.wait_for_timeout(2500)

            # Step 2: Restore 'E'/'e' to 'YO'/'yo'
            print("Step 2: Restoring 'E' to 'YO'...")
            open_headline_editor(page)
            headline_input = page.locator("#resumeHeadlineTxt")
            text = headline_input.input_value()
            restored_text = re.sub(r"\byo\b", "yoe", text, count=1)
            restored_text = re.sub(r"\bYO\b", "YOE", restored_text, count=1)
            headline_input.fill(restored_text)
            save_headline(page)
            print(f"Step 2 Complete: Restored to '{restored_text}'")
            page.wait_for_timeout(3500)

            # Step 3: Delete existing resume
            print("Step 3: Deleting existing resume...")
            delete_btn = page.locator(
                "span.title:has-text('Delete resume'), a:has-text('Delete resume'), span:has-text('Delete')"
            ).first
            if delete_btn.is_visible():
                delete_btn.click()
                page.wait_for_timeout(1500)
                confirm_btn = page.locator(
                    "button:has-text('Delete'), button:has-text('Confirm'), div.lightbox button:has-text('Delete')"
                ).first
                if confirm_btn.is_visible():
                    confirm_btn.click()
                    print("Confirmed deletion of old resume.")
                    page.wait_for_timeout(4000)

            # Step 4: Upload fresh resume
            print("Step 4: Uploading fresh resume...")
            file_input = page.locator("input#attachCV")
            file_input.set_input_files(RESUME_PATH)
            page.wait_for_timeout(7000)
            print("Step 4 Complete: Resume updated successfully.")

        finally:
            if os.path.exists("session_state.json"):
                os.remove("session_state.json")
            browser.close()

if __name__ == "__main__":
    run()
