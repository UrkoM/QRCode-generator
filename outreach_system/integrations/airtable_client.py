from __future__ import annotations
import logging
from typing import Optional
from pyairtable import Api
from config import config
from models.prospect import Prospect, ProspectStatus
from models.persona import LinkedInPersona

logger = logging.getLogger(__name__)


class AirtableClient:
    def __init__(self):
        self.api = Api(config.AIRTABLE_API_KEY)
        base = self.api.base(config.AIRTABLE_BASE_ID)
        self.prospects = base.table(config.AIRTABLE_PROSPECTS_TABLE)
        self.personas = base.table(config.AIRTABLE_PERSONAS_TABLE)
        self.messages = base.table(config.AIRTABLE_MESSAGES_TABLE)

    # ── Prospects ────────────────────────────────────────────────────────────

    def create_prospect(self, prospect: Prospect) -> Prospect:
        record = self.prospects.create(prospect.to_airtable_fields())
        prospect.airtable_id = record["id"]
        logger.info(f"Created prospect {prospect.name} ({prospect.airtable_id})")
        return prospect

    def update_prospect(self, prospect: Prospect, fields: dict) -> None:
        if not prospect.airtable_id:
            raise ValueError("Prospect has no airtable_id")
        self.prospects.update(prospect.airtable_id, fields)
        for k, v in fields.items():
            if hasattr(prospect, k):
                setattr(prospect, k, v)

    def update_status(self, prospect: Prospect, status: ProspectStatus) -> None:
        self.update_prospect(prospect, {"status": status.value})
        prospect.status = status

    def get_prospects_by_status(self, status: ProspectStatus) -> list[Prospect]:
        records = self.prospects.all(formula=f"{{status}}='{status.value}'")
        return [Prospect.from_airtable(r) for r in records]

    def get_prospects_due_for_followup(self) -> list[Prospect]:
        """Returns prospects whose next_action_at <= now."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        formula = f"AND({{next_action_at}}<={now!r}, {{status}}!='ARCHIVED', {{status}}!='DONE')"
        records = self.prospects.all(formula=formula)
        return [Prospect.from_airtable(r) for r in records]

    def prospect_exists(self, linkedin_url: str) -> bool:
        records = self.prospects.all(formula=f"{{linkedin_url}}='{linkedin_url}'")
        return len(records) > 0

    # ── Personas (Modo A) ─────────────────────────────────────────────────────

    def create_persona(self, persona: LinkedInPersona) -> LinkedInPersona:
        record = self.personas.create(persona.to_airtable_fields())
        persona.airtable_id = record["id"]
        logger.info(f"Created persona {persona.persona_name} ({persona.airtable_id})")
        return persona

    def update_persona(self, persona: LinkedInPersona, fields: dict) -> None:
        if not persona.airtable_id:
            raise ValueError("Persona has no airtable_id")
        self.personas.update(persona.airtable_id, fields)

    def get_active_personas(self) -> list[LinkedInPersona]:
        records = self.personas.all(formula="OR({status}='ACTIVE', {status}='WARMING')")
        return [LinkedInPersona.from_airtable(r) for r in records]

    def get_persona_with_capacity(self) -> Optional[LinkedInPersona]:
        """Returns an active persona that hasn't hit weekly invite limit."""
        personas = self.get_active_personas()
        for p in personas:
            if p.invites_this_week < config.MAX_INVITES_PER_DAY_AUTONOMOUS * 5:
                return p
        return None

    # ── Messages Log ──────────────────────────────────────────────────────────

    def log_message(
        self,
        prospect: Prospect,
        touchpoint: int,
        message_body: str,
        channel: str = "linkedin",
    ) -> None:
        from datetime import datetime
        self.messages.create({
            "prospect_id": prospect.airtable_id or prospect.name,
            "prospect_name": prospect.name,
            "channel": channel,
            "touchpoint": touchpoint,
            "message_body": message_body,
            "sent_at": datetime.now().isoformat(),
            "replied": False,
        })

    def mark_replied(self, prospect: Prospect, reply_content: str) -> None:
        records = self.messages.all(
            formula=f"AND({{prospect_id}}='{prospect.airtable_id}', {{replied}}=FALSE())"
        )
        if records:
            latest = records[-1]
            self.messages.update(latest["id"], {
                "replied": True,
                "reply_content": reply_content,
            })
