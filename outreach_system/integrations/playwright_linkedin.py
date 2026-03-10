"""
LinkedIn browser automation via Playwright.
Handles: login, session persistence, profile scraping, search, invites, DMs.
"""
from __future__ import annotations
import json
import logging
import os
import random
import time
from typing import Optional

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

from config import config

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"


def _human_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Randomized delay to simulate human behavior."""
    time.sleep(random.uniform(min_s, max_s))


class LinkedInClient:
    """
    Manages a persistent LinkedIn browser session.
    Use as a context manager:

        with LinkedInClient() as li:
            li.search_people(keywords=["CTO", "startup"])
    """

    def __init__(
        self,
        cookies_file: str = None,
        proxy: Optional[str] = None,
        headless: bool = True,
    ):
        self.cookies_file = cookies_file or config.LINKEDIN_COOKIES_FILE
        self.proxy = proxy
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def __enter__(self) -> LinkedInClient:
        self._playwright = sync_playwright().start()
        launch_args = {
            "headless": self.headless,
            "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        }
        if self.proxy:
            launch_args["proxy"] = {"server": self.proxy}

        self._browser = self._playwright.chromium.launch(**launch_args)
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self.page = self._context.new_page()
        self._load_or_create_session()
        return self

    def __exit__(self, *args) -> None:
        self._save_session()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    # ── Session management ────────────────────────────────────────────────────

    def _load_or_create_session(self) -> None:
        if os.path.exists(self.cookies_file):
            with open(self.cookies_file, "r") as f:
                cookies = json.load(f)
            self._context.add_cookies(cookies)
            self.page.goto(f"{LINKEDIN_BASE}/feed/")
            _human_delay(2, 4)
            if "feed" in self.page.url or "mynetwork" in self.page.url:
                logger.info("Loaded existing LinkedIn session")
                return
        # Session expired or not found — need to log in
        logger.info("No valid session found, logging in...")
        self.login(config.LINKEDIN_EMAIL, config.LINKEDIN_PASSWORD)

    def _save_session(self) -> None:
        if self._context:
            cookies = self._context.cookies()
            with open(self.cookies_file, "w") as f:
                json.dump(cookies, f)
            logger.info(f"Session saved to {self.cookies_file}")

    def login(self, email: str, password: str) -> None:
        self.page.goto(f"{LINKEDIN_BASE}/login")
        _human_delay(1, 2)
        self.page.fill("#username", email)
        _human_delay(0.5, 1)
        self.page.fill("#password", password)
        _human_delay(0.5, 1.5)
        self.page.click('[type="submit"]')
        _human_delay(3, 5)
        if "checkpoint" in self.page.url or "challenge" in self.page.url:
            logger.warning("LinkedIn security challenge detected — manual intervention required")
            raise RuntimeError("LinkedIn security challenge: check browser manually")
        if "feed" not in self.page.url and "mynetwork" not in self.page.url:
            raise RuntimeError(f"Login failed. Current URL: {self.page.url}")
        logger.info("Logged in successfully")
        self._save_session()

    # ── Profile scraping ──────────────────────────────────────────────────────

    def scrape_profile(self, profile_url: str) -> dict:
        """
        Scrapes key info from a LinkedIn profile.
        Returns: {name, headline, about, company, location, recent_posts}
        """
        self.page.goto(profile_url)
        _human_delay(2, 4)

        data: dict = {"linkedin_url": profile_url}
        try:
            data["name"] = self.page.locator("h1").first.inner_text(timeout=5000)
        except Exception:
            data["name"] = ""

        try:
            data["headline"] = self.page.locator(".text-body-medium.break-words").first.inner_text(timeout=3000)
        except Exception:
            data["headline"] = ""

        try:
            about_section = self.page.locator("#about ~ div .visually-hidden").first
            data["about"] = about_section.inner_text(timeout=3000)
        except Exception:
            data["about"] = ""

        try:
            data["location"] = self.page.locator(".text-body-small.inline").first.inner_text(timeout=3000)
        except Exception:
            data["location"] = ""

        # Scrape recent posts (visible on profile)
        try:
            posts = self.page.locator(".feed-shared-update-v2__description").all()
            data["recent_posts"] = [p.inner_text() for p in posts[:3]]
        except Exception:
            data["recent_posts"] = []

        logger.debug(f"Scraped profile: {data.get('name')} @ {data.get('headline')}")
        return data

    # ── Search ────────────────────────────────────────────────────────────────

    def search_people(
        self,
        keywords: list[str],
        location: str = "",
        max_results: int = 50,
    ) -> list[dict]:
        """
        Searches LinkedIn for people matching keywords.
        Returns list of {name, title, company, linkedin_url}.
        """
        query = " ".join(keywords)
        url = f"{LINKEDIN_BASE}/search/results/people/?keywords={query}"
        if location:
            url += f"&geoUrn=%5B%22{location}%22%5D"

        self.page.goto(url)
        _human_delay(2, 4)

        results = []
        page_num = 1

        while len(results) < max_results:
            # Extract result cards
            cards = self.page.locator(".reusable-search__result-container").all()
            for card in cards:
                try:
                    name = card.locator(".entity-result__title-text a span[aria-hidden='true']").first.inner_text()
                    link = card.locator(".app-aware-link").first.get_attribute("href")
                    title = card.locator(".entity-result__primary-subtitle").first.inner_text()
                    company = ""
                    try:
                        company = card.locator(".entity-result__secondary-subtitle").first.inner_text()
                    except Exception:
                        pass
                    if link and "/in/" in link:
                        results.append({
                            "name": name.strip(),
                            "title": title.strip(),
                            "company": company.strip(),
                            "linkedin_url": link.split("?")[0],
                        })
                except Exception:
                    continue

            if len(results) >= max_results:
                break

            # Next page
            next_btn = self.page.locator("button[aria-label='Next']")
            if not next_btn.is_visible():
                break
            next_btn.click()
            _human_delay(3, 6)
            page_num += 1

        logger.info(f"Search found {len(results)} profiles")
        return results[:max_results]

    # ── Connection requests ───────────────────────────────────────────────────

    def send_connection_request(self, profile_url: str, note: str = "") -> bool:
        """
        Sends a connection request with optional note (max 300 chars).
        Returns True if sent, False if already connected or failed.
        """
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would send connection to {profile_url}: {note[:50]}...")
            return True

        self.page.goto(profile_url)
        _human_delay(2, 4)

        # Check if already connected
        try:
            connected = self.page.locator("button[aria-label*='Message']").is_visible(timeout=2000)
            if connected:
                logger.info(f"Already connected: {profile_url}")
                return False
        except Exception:
            pass

        # Find and click Connect button
        try:
            connect_btn = self.page.locator("button:has-text('Connect')").first
            if not connect_btn.is_visible(timeout=3000):
                # Try More actions menu
                more_btn = self.page.locator("button:has-text('More')").first
                more_btn.click()
                _human_delay(1, 2)
                connect_btn = self.page.locator("li-icon[type='connect'] + span").first
            connect_btn.click()
            _human_delay(1, 2)
        except Exception as e:
            logger.warning(f"Could not find Connect button on {profile_url}: {e}")
            return False

        # Add note if provided
        if note:
            try:
                add_note_btn = self.page.locator("button:has-text('Add a note')").first
                add_note_btn.click()
                _human_delay(0.5, 1)
                note_field = self.page.locator("textarea[name='message']")
                note_field.fill(note[:300])
                _human_delay(0.5, 1)
            except Exception:
                pass  # Send without note

        # Send
        try:
            send_btn = self.page.locator("button:has-text('Send')").first
            send_btn.click()
            _human_delay(1, 2)
            logger.info(f"Connection request sent: {profile_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to send connection to {profile_url}: {e}")
            return False

    # ── Direct messages ───────────────────────────────────────────────────────

    def send_direct_message(self, profile_url: str, message: str) -> bool:
        """
        Sends a direct message to an existing connection.
        """
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would DM {profile_url}: {message[:60]}...")
            return True

        self.page.goto(profile_url)
        _human_delay(2, 4)

        try:
            msg_btn = self.page.locator("button:has-text('Message')").first
            msg_btn.click()
            _human_delay(1, 2)

            msg_box = self.page.locator(".msg-form__contenteditable").first
            msg_box.click()
            msg_box.type(message, delay=random.randint(30, 80))
            _human_delay(0.5, 1.5)

            send_btn = self.page.locator("button.msg-form__send-button").first
            send_btn.click()
            _human_delay(1, 2)
            logger.info(f"DM sent to {profile_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to DM {profile_url}: {e}")
            return False

    # ── Inbox monitoring ──────────────────────────────────────────────────────

    def get_new_messages(self) -> list[dict]:
        """
        Checks LinkedIn inbox for unread messages.
        Returns list of {sender_url, sender_name, message_text, timestamp}.
        """
        self.page.goto(f"{LINKEDIN_BASE}/messaging/")
        _human_delay(2, 4)

        messages = []
        try:
            unread = self.page.locator(".msg-conversation-listitem__unread-count").all()
            for item in unread:
                try:
                    thread = item.locator("xpath=ancestor::li")
                    sender = thread.locator(".msg-conversation-listitem__participant-names").inner_text()
                    preview = thread.locator(".msg-conversation-card__message-snippet").inner_text()
                    link = thread.locator("a").first.get_attribute("href")
                    messages.append({
                        "sender_name": sender.strip(),
                        "preview": preview.strip(),
                        "thread_url": f"{LINKEDIN_BASE}{link}",
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Error reading inbox: {e}")

        return messages

    def get_connection_acceptances(self) -> list[str]:
        """
        Checks notifications for recently accepted connection requests.
        Returns list of LinkedIn profile URLs.
        """
        self.page.goto(f"{LINKEDIN_BASE}/notifications/")
        _human_delay(2, 3)
        accepted = []
        try:
            notifications = self.page.locator(".nt-card__text").all()
            for n in notifications:
                text = n.inner_text().lower()
                if "accepted" in text or "aceptó" in text:
                    link_el = n.locator("xpath=ancestor::*//a[contains(@href, '/in/')]").first
                    href = link_el.get_attribute("href")
                    if href:
                        accepted.append(href.split("?")[0])
        except Exception as e:
            logger.warning(f"Error checking acceptances: {e}")
        return accepted
