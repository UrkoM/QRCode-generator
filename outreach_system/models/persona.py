from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PersonaStatus(str, Enum):
    CREATED = "CREATED"
    WARMING = "WARMING"
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    BANNED = "BANNED"


@dataclass
class LinkedInPersona:
    """Identidad sintética para Modo A (Agente Autónomo)."""
    persona_name: str
    persona_title: str
    persona_company: str
    persona_bio: str
    account_email: str
    photo_url: str                          # URL de foto sintética descargada
    work_history: list[dict]                # Lista de {company, title, dates, description}
    skills: list[str]
    status: PersonaStatus = PersonaStatus.CREATED
    airtable_id: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_account_email: Optional[str] = None
    proxy_ip: Optional[str] = None
    invites_this_week: int = 0
    total_connections: int = 0
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_airtable_fields(self) -> dict:
        return {
            "persona_name": self.persona_name,
            "persona_title": self.persona_title,
            "persona_company": self.persona_company,
            "account_email": self.account_email,
            "linkedin_url": self.linkedin_url or "",
            "status": self.status.value,
            "invites_this_week": self.invites_this_week,
            "total_connections": self.total_connections,
            "proxy_ip": self.proxy_ip or "",
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_airtable(cls, record: dict) -> LinkedInPersona:
        f = record.get("fields", {})
        return cls(
            persona_name=f.get("persona_name", ""),
            persona_title=f.get("persona_title", ""),
            persona_company=f.get("persona_company", ""),
            persona_bio="",
            account_email=f.get("account_email", ""),
            photo_url="",
            work_history=[],
            skills=[],
            status=PersonaStatus(f.get("status", "CREATED")),
            airtable_id=record.get("id"),
            linkedin_url=f.get("linkedin_url") or None,
            proxy_ip=f.get("proxy_ip") or None,
            invites_this_week=f.get("invites_this_week", 0),
            total_connections=f.get("total_connections", 0),
        )
