from __future__ import annotations
import json
import logging
import re
from agents.base_agent import BaseAgent
from integrations.airtable_client import AirtableClient
from integrations.playwright_linkedin import LinkedInClient
from models.prospect import Prospect, ProspectStatus, OutreachMode
from config import config

logger = logging.getLogger(__name__)


class QualificationAgent(BaseAgent):
    """
    Scores and qualifies prospects. Enriches with scraped profile data.
    Filters out disqualified prospects.
    """

    def __init__(self, mode: OutreachMode, proxy: str = None):
        super().__init__(model=self.HAIKU)
        self.mode = mode
        self.proxy = proxy
        self.db = AirtableClient()

    def run_qualification(self, prospects: list[Prospect], strategy: dict) -> list[Prospect]:
        """Qualify and score a list of NEW prospects."""
        system = self._load_prompt("qualification.txt")
        icp_summary = json.dumps(strategy.get("icp", {}), ensure_ascii=False)
        qualified = []

        cookies_file = (
            config.LINKEDIN_COOKIES_FILE if self.mode == OutreachMode.COPILOT
            else f"linkedin_session_{self.proxy}.json"
        )

        with LinkedInClient(cookies_file=cookies_file, proxy=self.proxy) as li:
            for prospect in prospects:
                try:
                    profile_data = li.scrape_profile(prospect.linkedin_url)
                    prospect.notes = json.dumps(profile_data, ensure_ascii=False)

                    user_msg = f"""## ICP
{icp_summary}

## PERFIL DEL PROSPECTO
Nombre: {prospect.name}
Cargo: {prospect.title}
Empresa: {prospect.company}
About: {profile_data.get('about', '')}
Posts recientes: {profile_data.get('recent_posts', [])}
Ubicación: {profile_data.get('location', '')}"""

                    raw = self.run(system, user_msg)
                    result = self._parse_json(raw)

                    if result.get("disqualified"):
                        logger.info(f"Disqualified {prospect.name}: {result.get('disqualification_reason')}")
                        self.db.update_status(prospect, ProspectStatus.ARCHIVED)
                        continue

                    score = result.get("score", 0)
                    prospect.score = score
                    self.db.update_prospect(prospect, {
                        "score": score,
                        "notes": prospect.notes,
                        "status": ProspectStatus.QUALIFIED.value,
                    })
                    prospect.status = ProspectStatus.QUALIFIED
                    qualified.append(prospect)
                    logger.info(f"Qualified {prospect.name} — score: {score}")
                except Exception as e:
                    logger.error(f"Error qualifying {prospect.name}: {e}")

        # Sort by score descending
        qualified.sort(key=lambda p: p.score, reverse=True)
        return qualified

    def _parse_json(self, text: str) -> dict:
        match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
        if match:
            return json.loads(match.group(1))
        try:
            return json.loads(text)
        except Exception:
            return {}
