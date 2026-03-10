from __future__ import annotations
import logging
import os
from integrations.playwright_linkedin import LinkedInClient
from config import config

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages the LinkedIn session for Mode B (real user profile).
    Handles login, cookie persistence and session health checks.
    """

    def __init__(self):
        self.cookies_file = config.LINKEDIN_COOKIES_FILE

    def ensure_session(self) -> bool:
        """
        Verifies the session is valid. Re-authenticates if needed.
        Returns True if session is active.
        """
        try:
            with LinkedInClient(cookies_file=self.cookies_file) as li:
                li.page.goto("https://www.linkedin.com/feed/")
                current_url = li.page.url
                if "feed" in current_url or "mynetwork" in current_url:
                    logger.info("LinkedIn session is active")
                    return True
                logger.warning("Session invalid, attempting re-login...")
                li.login(config.LINKEDIN_EMAIL, config.LINKEDIN_PASSWORD)
                return True
        except RuntimeError as e:
            if "challenge" in str(e).lower():
                logger.error("Manual LinkedIn verification required. Open browser and complete challenge.")
                return False
            raise

    def force_login(self) -> None:
        """Force a fresh login, discarding existing cookies."""
        if os.path.exists(self.cookies_file):
            os.remove(self.cookies_file)
            logger.info(f"Cleared old session: {self.cookies_file}")
        with LinkedInClient(cookies_file=self.cookies_file) as li:
            li.login(config.LINKEDIN_EMAIL, config.LINKEDIN_PASSWORD)
            logger.info("Fresh login completed")
