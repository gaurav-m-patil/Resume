import os
import re
import time
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("NAUKRI_EMAIL")
PASSWORD = os.environ.get("NAUKRI_PASSWORD")
RESUME_PATH = os.path.abspath("resume.pdf")

if not os.path.exists(RESUME_PATH):
    raise FileNotFoundError("resume.pdf not found in root directory!")

def open_headline_editor(page):
    edit_btn = page.locator(
        "div.widgetHead:has-text('Resume headline') span.edit, span.editRow.icon:has-text('editOneTheme')"
    ).first
    edit_btn.wait_for(state="visible", timeout=15000)
    edit_btn.click()
    page.wait_for_selector("#resumeHeadlineTxt", state="visible", timeout=15000)

def save_headline(page):
    save_btn = page.locator("button:has-text('Save')").first
    save_btn.click()
    page.wait_for_timeout(3000)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        # Step 0: Login
        print("Logging into Naukri...")
        page.goto("https://www.naukri.com/nlogin/login", wait_until="load", timeout=60000)
        page.fill("#usernameField", EMAIL)
        page.fill("#passwordField", PASSWORD)
        page.click("button[type='submit']")

        page.wait_for_url(re.compile(r".*(mnjuser|homepage).*"), timeout=40000)
        print("Logged in successfully.")

        page.goto("https://www.naukri.com/mnjuser/profile", wait_until="load", timeout=60000)
        page.wait_for_timeout(4000)

        # Step 1: Remove 'e' from 'yoe' and save
        print("Step 1: Removing 'E' from 'YOE'...")
        open_headline_editor(page)
        headline_input = page.locator("#resumeHeadlineTxt")
        text = headline_input.input_value()

        temp_text = re.sub(r"(?i)\byoe\b", lambda m: m.group(0)[:-1], text, count=1)
        headline_input.fill(temp_text)
        save_headline(page)
        print(f"Saved headline: '{temp_text}'")
        page.wait_for_timeout(2500)

        # Step 2: Add 'e' back to 'yo' and save
        print("Step 2: Adding 'E' back to 'YO'...")
        open_headline_editor(page)
        headline_input = page.locator("#resumeHeadlineTxt")
        text = headline_input.input_value()

        restored_text = re.sub(r"\byo\b", "yoe", text, count=1)
        restored_text = re.sub(r"\bYO\b", "YOE", restored_text, count=1)
        headline_input.fill(restored_text)
        save_headline(page)
        print(f"Restored headline: '{restored_text}'")
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
        else:
            print("No delete button visible. Proceeding directly to upload.")

        # Step 4: Upload fresh resume and save
        print("Step 4: Uploading fresh resume...")
        file_input = page.locator("input#attachCV")
        file_input.set_input_files(RESUME_PATH)
        page.wait_for_timeout(7000)
        print("Resume uploaded successfully.")

        browser.close()

if __name__ == "__main__":
    run()
