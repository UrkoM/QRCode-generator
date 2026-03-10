from __future__ import annotations
import logging
from agents.base_agent import BaseAgent
from integrations.playwright_linkedin import LinkedInClient
from integrations.airtable_client import AirtableClient
from models.prospect import Prospect, OutreachMode
from config import config

logger = logging.getLogger(__name__)


class SearchAgent(BaseAgent):
    """
    Searches LinkedIn for prospects matching the ICP.
    Deduplicates against Airtable before adding.
    """

    def __init__(self, mode: OutreachMode, proxy: str = None):
        super().__init__(model=self.HAIKU)
        self.mode = mode
        self.proxy = proxy
        self.db = AirtableClient()

    def run_search(self, strategy: dict, max_results: int = 100) -> list[Prospect]:
        """
        Uses the strategy JSON to search LinkedIn and return new prospects.
        """
        keywords = strategy.get("search_keywords", [])
        icp = strategy.get("icp", {})
        locations = icp.get("locations", [""])
        campaign_id = strategy.get("campaign_name", config.CAMPAIGN_ID)

        cookies_file = (
            config.LINKEDIN_COOKIES_FILE
            if self.mode == OutreachMode.COPILOT
            else f"linkedin_session_{self.proxy}.json"
        )

        new_prospects: list[Prospect] = []

        with LinkedInClient(cookies_file=cookies_file, proxy=self.proxy) as li:
            for location in locations[:2]:  # Max 2 locations per run
                results = li.search_people(
                    keywords=keywords[:5],
                    location=location,
                    max_results=max_results // len(locations[:2]),
                )
                for r in results:
                    url = r.get("linkedin_url", "")
                    if not url or self.db.prospect_exists(url):
                        continue
                    p = Prospect(
                        name=r.get("name", ""),
                        linkedin_url=url,
                        title=r.get("title", ""),
                        company=r.get("company", ""),
                        mode=self.mode,
                        campaign_id=campaign_id,
                    )
                    p = self.db.create_prospect(p)
                    new_prospects.append(p)

        logger.info(f"SearchAgent: added {len(new_prospects)} new prospects")
        return new_prospects
