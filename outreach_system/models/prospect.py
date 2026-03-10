from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProspectStatus(str, Enum):
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    INVITE_SENT = "INVITE_SENT"
    INVITE_EXPIRED = "INVITE_EXPIRED"
    CONNECTED = "CONNECTED"
    MSG_1_SENT = "MSG_1_SENT"
    MSG_2_SENT = "MSG_2_SENT"
    MSG_3_SENT = "MSG_3_SENT"
    BREAK_UP_SENT = "BREAK_UP_SENT"
    REPLIED = "REPLIED"
    INTERESTED = "INTERESTED"
    OBJECTION = "OBJECTION"
    NOT_INTERESTED = "NOT_INTERESTED"
    MEETING_SCHEDULED = "MEETING_SCHEDULED"
    DONE = "DONE"
    ARCHIVED = "ARCHIVED"


class OutreachMode(str, Enum):
    AUTONOMOUS = "autonomous"
    COPILOT = "copilot"


@dataclass
class Prospect:
    name: str
    linkedin_url: str
    title: str = ""
    company: str = ""
    score: int = 0
    status: ProspectStatus = ProspectStatus.NEW
    mode: OutreachMode = OutreachMode.COPILOT
    persona_id: Optional[str] = None          # Solo Modo A
    airtable_id: Optional[str] = None
    invite_sent_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    last_msg_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    replied: bool = False
    meeting_booked: bool = False
    meeting_date: Optional[datetime] = None
    notes: str = ""                            # Datos scrapeados del perfil
    campaign_id: str = ""

    def to_airtable_fields(self) -> dict:
        return {
            "name": self.name,
            "linkedin_url": self.linkedin_url,
            "title": self.title,
            "company": self.company,
            "score": self.score,
            "status": self.status.value,
            "mode": self.mode.value,
            "persona_id": self.persona_id or "",
            "invite_sent_at": self.invite_sent_at.isoformat() if self.invite_sent_at else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_msg_at": self.last_msg_at.isoformat() if self.last_msg_at else None,
            "next_action_at": self.next_action_at.isoformat() if self.next_action_at else None,
            "replied": self.replied,
            "meeting_booked": self.meeting_booked,
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else None,
            "notes": self.notes,
            "campaign_id": self.campaign_id,
        }

    @classmethod
    def from_airtable(cls, record: dict) -> Prospect:
        f = record.get("fields", {})
        return cls(
            name=f.get("name", ""),
            linkedin_url=f.get("linkedin_url", ""),
            title=f.get("title", ""),
            company=f.get("company", ""),
            score=f.get("score", 0),
            status=ProspectStatus(f.get("status", "NEW")),
            mode=OutreachMode(f.get("mode", "copilot")),
            persona_id=f.get("persona_id") or None,
            airtable_id=record.get("id"),
            replied=f.get("replied", False),
            meeting_booked=f.get("meeting_booked", False),
            notes=f.get("notes", ""),
            campaign_id=f.get("campaign_id", ""),
        )
