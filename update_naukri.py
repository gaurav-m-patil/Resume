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
    edit_btn.wait_for(state="visible", timeout=20000)
    edit_btn.click()
    page.wait_for_selector("#resumeHeadlineTxt", state="visible", timeout=20000)

def save_headline(page):
    save_btn = page.locator("button:has-text('Save')").first
    save_btn.click()
    page.wait_for_timeout(3000)

def run():
    with sync_playwright() as p:
        # Launch Chromium with anti-detection flags
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US"
        )

        page = context.new_page()

        # Mask webdriver property to bypass automated bot checks
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print("Logging into Naukri...")
            page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=60000)
            
            # Wait for either the ID selector or alternate placeholder selectors
            email_selector = "#usernameField, input[placeholder*='Email'], input[placeholder*='Username']"
            page.wait_for_selector(email_selector, state="visible", timeout=30000)

            # Fill credentials
            page.locator(email_selector).first.fill(EMAIL)
            
            pwd_selector = "#passwordField, input[type='password']"
            page.locator(pwd_selector).first.fill(PASSWORD)

            # Submit
            submit_btn = page.locator("button[type='submit'], button:has-text('Login')").first
            submit_btn.click()

            # Wait for dashboard navigation
            page.wait_for_url(re.compile(r".*(mnjuser|homepage).*"), timeout=40000)
            print("Login successful.")

            page.goto("https://www.naukri.com/mnjuser/profile", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

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

        except Exception as e:
            # Capture what the browser saw for diagnostic debugging
            page.screenshot(path="error_screen.png", full_page=True)
            print(f"Page title during error: {page.title()}")
            print(f"Current URL: {page.url}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    run()
