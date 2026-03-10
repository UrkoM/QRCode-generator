from __future__ import annotations
import logging
from models.persona import LinkedInPersona, PersonaStatus
from integrations.airtable_client import AirtableClient
from integrations.playwright_linkedin import LinkedInClient

logger = logging.getLogger(__name__)


class AccountManager:
    """
    Monitors health of synthetic LinkedIn accounts (Mode A).
    Detects bans, restrictions and CAPTCHA challenges.
    Rotates to backup accounts when needed.
    """

    def __init__(self):
        self.db = AirtableClient()

    def health_check(self, persona: LinkedInPersona) -> PersonaStatus:
        """
        Opens a browser session and checks if the account is healthy.
        Returns the detected status.
        """
        cookies_file = f"linkedin_session_{persona.persona_name.replace(' ', '_')}.json"
        proxy = f"http://{persona.proxy_ip}" if persona.proxy_ip else None

        try:
            with LinkedInClient(
                cookies_file=cookies_file,
                proxy=proxy,
                headless=True,
            ) as li:
                li.page.goto("https://www.linkedin.com/feed/")
                url = li.page.url

                if "checkpoint" in url or "challenge" in url:
                    logger.warning(f"Account {persona.persona_name}: RESTRICTED (challenge)")
                    status = PersonaStatus.RESTRICTED
                elif "login" in url or "authwall" in url:
                    logger.warning(f"Account {persona.persona_name}: BANNED (redirected to login)")
                    status = PersonaStatus.BANNED
                elif "feed" in url:
                    logger.info(f"Account {persona.persona_name}: ACTIVE")
                    status = PersonaStatus.ACTIVE
                else:
                    logger.warning(f"Account {persona.persona_name}: unknown URL {url}")
                    status = PersonaStatus.RESTRICTED

        except Exception as e:
            logger.error(f"Health check failed for {persona.persona_name}: {e}")
            status = PersonaStatus.RESTRICTED

        # Update in Airtable
        self.db.update_persona(persona, {"status": status.value})
        persona.status = status
        return status

    def check_all_accounts(self) -> dict:
        """
        Runs health checks on all active/warming personas.
        Returns summary dict: {active: N, restricted: N, banned: N}
        """
        personas = self.db.get_active_personas()
        summary = {"active": 0, "restricted": 0, "banned": 0}

        for persona in personas:
            status = self.health_check(persona)
            if status == PersonaStatus.ACTIVE:
                summary["active"] += 1
            elif status == PersonaStatus.RESTRICTED:
                summary["restricted"] += 1
            elif status == PersonaStatus.BANNED:
                summary["banned"] += 1

        logger.info(f"Account health summary: {summary}")
        return summary

    def reset_weekly_invites(self) -> None:
        """Reset weekly invite counters for all personas (call every Monday)."""
        personas = self.db.get_active_personas()
        for persona in personas:
            self.db.update_persona(persona, {"invites_this_week": 0})
        logger.info(f"Reset weekly invite counters for {len(personas)} personas")
