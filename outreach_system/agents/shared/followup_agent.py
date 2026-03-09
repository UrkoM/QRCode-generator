from __future__ import annotations
import json
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

# Maps current status → next status after sending follow-up
FOLLOWUP_PROGRESSION = {
    ProspectStatus.CONNECTED: ProspectStatus.MSG_1_SENT,
    ProspectStatus.MSG_1_SENT: ProspectStatus.MSG_2_SENT,
    ProspectStatus.MSG_2_SENT: ProspectStatus.MSG_3_SENT,
    ProspectStatus.MSG_3_SENT: ProspectStatus.BREAK_UP_SENT,
    ProspectStatus.BREAK_UP_SENT: ProspectStatus.ARCHIVED,
}

TOUCHPOINT_KEY = {
    ProspectStatus.CONNECTED: "msg_1",
    ProspectStatus.MSG_1_SENT: "msg_2",
    ProspectStatus.MSG_2_SENT: "msg_3",
    ProspectStatus.MSG_3_SENT: "msg_4",
}


class FollowupAgent(BaseAgent):
    """
    Monitors connected prospects and sends DM sequences at the right time.
    Also checks for new connection acceptances.
    """

    def __init__(self, mode: OutreachMode, proxy: str = None, cookies_file: str = None):
        super().__init__(model=self.HAIKU)
        self.mode = mode
        self.proxy = proxy
        self.cookies_file = cookies_file or config.LINKEDIN_COOKIES_FILE
        self.db = AirtableClient()
        self.personalizer = PersonalizationAgent()

    def check_new_acceptances(self, strategy: dict) -> int:
        """
        Checks LinkedIn notifications for new connection acceptances.
        Sends MSG_1 immediately after acceptance.
        """
        accepted_count = 0
        with LinkedInClient(cookies_file=self.cookies_file, proxy=self.proxy) as li:
            accepted_urls = li.get_connection_acceptances()
            for url in accepted_urls:
                records = self.db.prospects.all(
                    formula=f"AND({{linkedin_url}}='{url}', {{status}}='INVITE_SENT')"
                )
                if not records:
                    continue
                prospect = Prospect.from_airtable(records[0])
                self._send_followup(li, prospect, strategy, touchpoint_key="msg_1")
                accepted_count += 1

        return accepted_count

    def run_scheduled_followups(self, strategy: dict) -> int:
        """
        Sends follow-ups to all prospects whose next_action_at is due.
        """
        due_prospects = self.db.get_prospects_due_for_followup()
        sent = 0

        with LinkedInClient(cookies_file=self.cookies_file, proxy=self.proxy) as li:
            for prospect in due_prospects:
                if prospect.status not in TOUCHPOINT_KEY:
                    continue
                self._send_followup(li, prospect, strategy)
                sent += 1

                delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
                if not config.DRY_RUN:
                    time.sleep(delay)

        logger.info(f"FollowupAgent: sent {sent} follow-ups")
        return sent

    def _send_followup(
        self,
        li: LinkedInClient,
        prospect: Prospect,
        strategy: dict,
        touchpoint_key: str = None,
    ) -> None:
        key = touchpoint_key or TOUCHPOINT_KEY.get(prospect.status)
        if not key:
            return

        # Generate or load DM sequence
        dm_sequence = self.personalizer.generate_dm_sequence(prospect, strategy)
        msg_data = dm_sequence.get(key, {})
        body = msg_data.get("body", "")
        if not body:
            logger.warning(f"No message body for {prospect.name} touchpoint {key}")
            return

        touchpoint_num = int(key.replace("msg_", ""))
        success = li.send_direct_message(prospect.linkedin_url, body)
        if not success:
            return

        now = datetime.now()
        next_status = FOLLOWUP_PROGRESSION.get(prospect.status, ProspectStatus.ARCHIVED)
        delay_days = {
            ProspectStatus.CONNECTED: config.FOLLOWUP_1_DAYS,
            ProspectStatus.MSG_1_SENT: config.FOLLOWUP_2_DAYS - config.FOLLOWUP_1_DAYS,
            ProspectStatus.MSG_2_SENT: config.FOLLOWUP_3_DAYS - config.FOLLOWUP_2_DAYS,
            ProspectStatus.MSG_3_SENT: 7,
        }.get(prospect.status, 7)

        self.db.update_prospect(prospect, {
            "status": next_status.value,
            "last_msg_at": now.isoformat(),
            "next_action_at": (now + timedelta(days=delay_days)).isoformat(),
        })
        self.db.log_message(prospect, touchpoint=touchpoint_num, message_body=body)
        logger.info(f"Sent {key} to {prospect.name} → status: {next_status.value}")
