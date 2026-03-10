from __future__ import annotations
import logging
import os
import random
import time
from playwright.sync_api import sync_playwright, Page
from models.persona import LinkedInPersona, PersonaStatus
from integrations.airtable_client import AirtableClient
from integrations.proxy_manager import ProxyManager
from config import config

logger = logging.getLogger(__name__)

LINKEDIN_SIGNUP = "https://www.linkedin.com/signup"


class AccountSetupAgent:
    """
    Creates and configures a LinkedIn account for a synthetic persona (Mode A).
    Steps:
    1. Register account with persona email
    2. Upload profile photo
    3. Fill in all profile sections
    4. Save cookies for future sessions
    """

    def __init__(self):
        self.db = AirtableClient()
        self.proxy_mgr = ProxyManager()

    def setup_account(self, persona: LinkedInPersona) -> LinkedInPersona:
        """
        Full setup flow for a new LinkedIn account.
        Returns the persona with linkedin_url and proxy_ip filled in.
        """
        proxy = self.proxy_mgr.get_available_proxy()
        proxy_str = f"http://{proxy}" if proxy else None

        launch_args = {
            "headless": False,  # Use visible browser for setup (easier to handle captchas)
            "args": ["--no-sandbox"],
        }
        if proxy_str:
            launch_args["proxy"] = {"server": proxy_str}

        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_args)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            try:
                self._register_account(page, persona)
                self._fill_profile(page, persona)
                profile_url = self._get_profile_url(page)
                persona.linkedin_url = profile_url
                persona.proxy_ip = proxy
                persona.status = PersonaStatus.WARMING

                # Save session cookies
                cookies_file = f"linkedin_session_{persona.persona_name.replace(' ', '_')}.json"
                import json
                with open(cookies_file, "w") as f:
                    json.dump(context.cookies(), f)
                logger.info(f"Saved session for {persona.persona_name}: {cookies_file}")
            finally:
                context.close()
                browser.close()

        # Save to Airtable
        persona = self.db.create_persona(persona)
        return persona

    def _register_account(self, page: Page, persona: LinkedInPersona) -> None:
        first, *rest = persona.persona_name.split()
        last = " ".join(rest) if rest else "User"
        password = self._generate_password()

        page.goto(LINKEDIN_SIGNUP)
        self._delay()

        page.fill("#email-address", persona.account_email)
        self._delay(0.5, 1)
        page.fill("#password", password)
        self._delay(0.5, 1)
        page.click('[data-id="join-form-submit"]')
        self._delay(2, 4)

        # First / last name step
        try:
            page.fill("#first-name", first, timeout=5000)
            page.fill("#last-name", last)
            self._delay(0.5, 1)
            page.click('[data-id="join-form-submit"]')
            self._delay(2, 4)
        except Exception:
            pass

        logger.info(f"Registration submitted for {persona.persona_name}")

    def _fill_profile(self, page: Page, persona: LinkedInPersona) -> None:
        # Navigate to profile edit
        page.goto("https://www.linkedin.com/in/me/")
        self._delay(2, 3)

        # Upload photo if available
        if persona.photo_url and os.path.exists(persona.photo_url):
            try:
                photo_btn = page.locator("button.profile-photo-edit__edit-btn").first
                photo_btn.click()
                self._delay(1, 2)
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(persona.photo_url)
                self._delay(2, 3)
                save_btn = page.locator("button:has-text('Save photo')").first
                save_btn.click()
                self._delay(2, 3)
                logger.info("Profile photo uploaded")
            except Exception as e:
                logger.warning(f"Could not upload photo: {e}")

        # Edit intro section
        try:
            page.goto("https://www.linkedin.com/in/me/edit/intro/")
            self._delay(2, 3)
            headline_field = page.locator("input[id*='headline']").first
            headline_field.fill(persona.persona_title)
            save_btn = page.locator("button:has-text('Save')").first
            save_btn.click()
            self._delay(1, 2)
        except Exception as e:
            logger.warning(f"Could not fill headline: {e}")

        logger.info(f"Profile setup completed for {persona.persona_name}")

    def _get_profile_url(self, page: Page) -> str:
        try:
            page.goto("https://www.linkedin.com/in/me/")
            self._delay(2, 3)
            return page.url.split("?")[0]
        except Exception:
            return ""

    def _generate_password(self) -> str:
        import string
        chars = string.ascii_letters + string.digits + "!@#$"
        return "".join(random.choices(chars, k=16))

    def _delay(self, min_s: float = 1.0, max_s: float = 3.0) -> None:
        time.sleep(random.uniform(min_s, max_s))
