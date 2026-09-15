import os
import re
import time
from playwright.sync_api import sync_playwright

STATE_JSON_CONTENT = os.environ.get("NAUKRI_STATE_JSON")
RESUME_PATH = os.path.abspath("resume.pdf")

if not os.path.exists(RESUME_PATH):
    raise FileNotFoundError("resume.pdf not found in root directory!")

if not STATE_JSON_CONTENT:
    raise ValueError("NAUKRI_STATE_JSON secret is missing or empty!")

def open_headline_editor(page):
    edit_btn = page.locator(
        "div.widgetHead:has-text('Resume headline') span.edit, span.editRow.icon:has-text('editOneTheme')"
    ).first
    edit_btn.wait_for(state="visible", timeout=20000)
    edit_btn.click()
    page.wait_for_selector("#resumeHeadlineTxt", state="visible", timeout=20000)

def save_headline(page):
    save_btn = page.locator("button:has-text('Save')").first
    save_btn.click()
    page.wait_for_timeout(3000)

def run():
    # Save the session json to a temporary file for Playwright
    with open("session_state.json", "w", encoding="utf-8") as f:
        f.write(STATE_JSON_CONTENT)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        # Load the pre-authenticated session state
        context = browser.new_context(
            storage_state="session_state.json",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        try:
            print("Navigating directly to profile using saved session...")
            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="load", timeout=60000)
            page.wait_for_timeout(5000)

            # Check if session is expired or redirected to login
            if "login" in page.url or "Access Denied" in page.title():
                raise PermissionError(f"Session expired or blocked. Page title: {page.title()}, URL: {page.url}")

            # ----------------------------------------------------
            # Step 1: Remove 'E'/'e' from 'YOE'/'yoe' and save
            # ----------------------------------------------------
            print("Step 1: Removing 'E' from 'YOE'...")
            open_headline_editor(page)
            headline_input = page.locator("#resumeHeadlineTxt")
            text = headline_input.input_value()

            temp_text = re.sub(r"(?i)\byoe\b", lambda m: m.group(0)[:-1], text, count=1)
            headline_input.fill(temp_text)
            save_headline(page)
            print(f"Step 1 Complete: Saved as '{temp_text}'")
            page.wait_for_timeout(2500)

            # ----------------------------------------------------
            # Step 2: Add 'E'/'e' back to 'YO'/'yo' and save
            # ----------------------------------------------------
            print("Step 2: Adding 'E' back to 'YO'...")
            open_headline_editor(page)
            headline_input = page.locator("#resumeHeadlineTxt")
            text = headline_input.input_value()

            restored_text = re.sub(r"\byo\b", "yoe", text, count=1)
            restored_text = re.sub(r"\bYO\b", "YOE", restored_text, count=1)
            headline_input.fill(restored_text)
            save_headline(page)
            print(f"Step 2 Complete: Restored and saved as '{restored_text}'")
            page.wait_for_timeout(3500)

            # ----------------------------------------------------
            # Step 3: Delete existing resume
            # ----------------------------------------------------
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
            else:
                print("No delete button found. Proceeding to upload.")

            # ----------------------------------------------------
            # Step 4: Upload fresh resume
            # ----------------------------------------------------
            print("Step 4: Uploading fresh resume...")
            file_input = page.locator("input#attachCV")
            file_input.set_input_files(RESUME_PATH)
            page.wait_for_timeout(7000)
            print("Step 4 Complete: Fresh resume uploaded successfully.")

        finally:
            # Clean up local session file from the runner
            if os.path.exists("session_state.json"):
                os.remove("session_state.json")
            browser.close()

if __name__ == "__main__":
    run()
