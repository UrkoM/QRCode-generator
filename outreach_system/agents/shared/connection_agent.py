from __future__ import annotations
import logging
import random
import time
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from agents.shared.personalization_agent import PersonalizationAgent
from integrations.playwright_linkedin import LinkedInClient
from integrations.airtable_client import AirtableClient
from models.prospect import Prospect, ProspectStatus, OutreachMode
from config import config

logger = logging.getLogger(__name__)


class ConnectionAgent(BaseAgent):
    """
    Sends LinkedIn connection requests with personalized notes.
    Respects rate limits per mode.
    """

    def __init__(self, mode: OutreachMode, proxy: str = None, cookies_file: str = None):
        super().__init__(model=self.HAIKU)
        self.mode = mode
        self.proxy = proxy
        self.cookies_file = cookies_file or config.LINKEDIN_COOKIES_FILE
        self.db = AirtableClient()
        self.personalizer = PersonalizationAgent()

        self.daily_limit = (
            config.MAX_INVITES_PER_DAY_AUTONOMOUS
            if mode == OutreachMode.AUTONOMOUS
            else config.MAX_INVITES_PER_DAY_COPILOT
        )

    def run_outreach(self, prospects: list[Prospect], strategy: dict) -> int:
        """
        Send connection requests to a batch of qualified prospects.
        Returns number of invites sent.
        """
        sent = 0
        batch = prospects[: self.daily_limit]

        with LinkedInClient(cookies_file=self.cookies_file, proxy=self.proxy) as li:
            for prospect in batch:
                try:
                    note = self.personalizer.generate_invite_note(prospect, strategy)
                    logger.info(f"Sending invite to {prospect.name} | note: {note[:60]}...")

                    success = li.send_connection_request(prospect.linkedin_url, note)
                    if success:
                        now = datetime.now()
                        self.db.update_prospect(prospect, {
                            "status": ProspectStatus.INVITE_SENT.value,
                            "invite_sent_at": now.isoformat(),
                            # Expire if not accepted within 21 days
                            "next_action_at": (now + timedelta(days=21)).isoformat(),
                        })
                        self.db.log_message(prospect, touchpoint=0, message_body=note)
                        sent += 1

                    # Human-like delay between invites
                    delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
                    logger.debug(f"Waiting {delay:.0f}s before next action...")
                    if not config.DRY_RUN:
                        time.sleep(delay)

                except Exception as e:
                    logger.error(f"Error sending invite to {prospect.name}: {e}")

        logger.info(f"ConnectionAgent: {sent}/{len(batch)} invites sent")
        return sent
