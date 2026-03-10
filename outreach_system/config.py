import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Airtable
    AIRTABLE_API_KEY: str = os.getenv("AIRTABLE_API_KEY", "")
    AIRTABLE_BASE_ID: str = os.getenv("AIRTABLE_BASE_ID", "")
    AIRTABLE_PROSPECTS_TABLE: str = os.getenv("AIRTABLE_PROSPECTS_TABLE", "Prospects")
    AIRTABLE_PERSONAS_TABLE: str = os.getenv("AIRTABLE_PERSONAS_TABLE", "LinkedIn_Personas")
    AIRTABLE_MESSAGES_TABLE: str = os.getenv("AIRTABLE_MESSAGES_TABLE", "Messages_Log")

    # LinkedIn credentials (Modo B — perfil real)
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    LINKEDIN_COOKIES_FILE: str = os.getenv("LINKEDIN_COOKIES_FILE", "linkedin_session.json")

    # Phantombuster (opcional, alternativa a Playwright para scraping)
    PHANTOMBUSTER_API_KEY: str = os.getenv("PHANTOMBUSTER_API_KEY", "")

    # Calendly
    CALENDLY_LINK: str = os.getenv("CALENDLY_LINK", "")

    # Rate limits
    MAX_INVITES_PER_DAY_AUTONOMOUS: int = int(os.getenv("MAX_INVITES_PER_DAY_AUTONOMOUS", "20"))
    MAX_INVITES_PER_DAY_COPILOT: int = int(os.getenv("MAX_INVITES_PER_DAY_COPILOT", "30"))
    MIN_DELAY_SECONDS: int = int(os.getenv("MIN_DELAY_SECONDS", "120"))   # 2 min
    MAX_DELAY_SECONDS: int = int(os.getenv("MAX_DELAY_SECONDS", "480"))   # 8 min

    # Campaign
    CAMPAIGN_ID: str = os.getenv("CAMPAIGN_ID", "campaign_001")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"

    # Follow-up delays (días)
    FOLLOWUP_1_DAYS: int = int(os.getenv("FOLLOWUP_1_DAYS", "3"))
    FOLLOWUP_2_DAYS: int = int(os.getenv("FOLLOWUP_2_DAYS", "7"))
    FOLLOWUP_3_DAYS: int = int(os.getenv("FOLLOWUP_3_DAYS", "14"))

    # Approval gate (Modo B)
    APPROVAL_GATE_ENABLED: bool = os.getenv("APPROVAL_GATE_ENABLED", "false").lower() == "true"
    APPROVAL_TIMEOUT_HOURS: int = int(os.getenv("APPROVAL_TIMEOUT_HOURS", "24"))

    # Proxies (Modo A)
    PROXY_LIST_FILE: str = os.getenv("PROXY_LIST_FILE", "proxies.txt")


config = Config()
