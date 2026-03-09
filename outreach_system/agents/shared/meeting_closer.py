from __future__ import annotations
import json
import logging
import re
from agents.base_agent import BaseAgent
from integrations.playwright_linkedin import LinkedInClient
from integrations.airtable_client import AirtableClient
from models.prospect import Prospect, ProspectStatus, OutreachMode
from config import config

logger = logging.getLogger(__name__)


class MeetingCloserAgent(BaseAgent):
    """
    Monitors LinkedIn inbox for replies and handles them:
    - INTERESTED → send Calendly link
    - OBJECTION → handle with contextual response
    - NOT_INTERESTED → archive gracefully
    """

    def __init__(self, mode: OutreachMode, proxy: str = None, cookies_file: str = None):
        super().__init__(model=self.SONNET)
        self.mode = mode
        self.proxy = proxy
        self.cookies_file = cookies_file or config.LINKEDIN_COOKIES_FILE
        self.db = AirtableClient()

    def run_inbox_check(self) -> int:
        """
        Checks inbox for new messages and handles them.
        Returns number of replies processed.
        """
        processed = 0
        system = self._load_prompt("meeting_closer.txt").replace(
            "{{CALENDLY_LINK}}", config.CALENDLY_LINK
        )

        with LinkedInClient(cookies_file=self.cookies_file, proxy=self.proxy) as li:
            new_messages = li.get_new_messages()
            for msg in new_messages:
                sender_name = msg.get("sender_name", "")
                reply_text = msg.get("preview", "")

                # Find prospect in DB
                records = self.db.prospects.all(
                    formula=f"{{name}}='{sender_name}'"
                )
                if not records:
                    continue

                prospect = Prospect.from_airtable(records[0])
                if prospect.status in (ProspectStatus.ARCHIVED, ProspectStatus.DONE,
                                       ProspectStatus.NOT_INTERESTED):
                    continue

                # Classify reply and generate response
                user_msg = f"""Respuesta del prospecto:
\"{reply_text}\"

Datos del prospecto:
- Nombre: {prospect.name}
- Cargo: {prospect.title}
- Empresa: {prospect.company}"""

                raw = self.run(system, user_msg)
                result = self._parse_json(raw)

                classification = result.get("classification", "UNRESPONSIVE")
                response_body = result.get("response_body", "")
                next_action = result.get("next_action", "WAIT")

                logger.info(f"Reply from {prospect.name}: {classification}")

                # Send response if needed
                if response_body:
                    li.send_direct_message(prospect.linkedin_url, response_body)
                    self.db.log_message(prospect, touchpoint=99, message_body=response_body)

                # Update prospect status
                new_status = {
                    "INTERESTED": ProspectStatus.INTERESTED,
                    "MEETING_SCHEDULED": ProspectStatus.MEETING_SCHEDULED,
                    "NOT_INTERESTED": ProspectStatus.NOT_INTERESTED,
                    "OBJECTION": ProspectStatus.OBJECTION,
                    "QUESTION": ProspectStatus.REPLIED,
                }.get(classification, ProspectStatus.REPLIED)

                if next_action == "MEETING_SCHEDULED":
                    new_status = ProspectStatus.MEETING_SCHEDULED
                elif next_action == "ARCHIVE":
                    new_status = ProspectStatus.ARCHIVED

                self.db.update_status(prospect, new_status)
                self.db.mark_replied(prospect, reply_text)
                processed += 1

        logger.info(f"MeetingCloser: processed {processed} replies")
        return processed

    def _parse_json(self, text: str) -> dict:
        match = re.search(r"```json\s*([\s\S]+?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        try:
            return json.loads(text)
        except Exception:
            return {}
