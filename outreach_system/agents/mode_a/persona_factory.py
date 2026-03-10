from __future__ import annotations
import json
import logging
import re
import requests
from agents.base_agent import BaseAgent
from models.persona import LinkedInPersona

logger = logging.getLogger(__name__)


class PersonaFactory(BaseAgent):
    """
    Generates synthetic LinkedIn identities for Mode A.
    Uses Claude to create coherent professional profiles and
    fetches a synthetic photo from generated.photos or thispersondoesnotexist.com.
    """

    def __init__(self):
        super().__init__(model=self.SONNET)

    def create_persona(self, strategy: dict) -> LinkedInPersona:
        """Generate a full synthetic persona based on campaign strategy."""
        system = self._load_prompt("persona_generation.txt")
        icp = strategy.get("icp", {})
        location = icp.get("locations", ["Spain"])[0] if icp.get("locations") else "Spain"
        language = strategy.get("language", "español")

        user_msg = f"""Campaña: {strategy.get('campaign_name', 'outreach campaign')}
Sector objetivo: {', '.join(icp.get('industries', ['B2B']))}
Ubicación del target: {location}
Idioma: {language}

Genera una identidad de SDR/BDM que sería creíble para este target."""

        raw = self.run(system, user_msg, max_tokens=2048)
        data = self._parse_json(raw)

        if not data:
            raise ValueError("PersonaFactory: failed to parse persona JSON from Claude")

        # Download synthetic photo
        photo_url = self._get_synthetic_photo()

        # Generate account email (use temp domain pattern)
        import random
        import string
        suffix = "".join(random.choices(string.digits, k=4))
        first = data.get("first_name", "user").lower()
        last = data.get("last_name", "name").lower()
        account_email = f"{first}.{last}{suffix}@protonmail.com"

        persona = LinkedInPersona(
            persona_name=f"{data.get('first_name', '')} {data.get('last_name', '')}",
            persona_title=data.get("current_position", {}).get("title", "Business Development Manager"),
            persona_company=data.get("current_position", {}).get("company", ""),
            persona_bio=data.get("about", ""),
            account_email=account_email,
            photo_url=photo_url,
            work_history=[data.get("current_position", {})] + data.get("previous_positions", []),
            skills=data.get("skills", []),
        )
        logger.info(f"Created persona: {persona.persona_name} | {persona.persona_title}")
        return persona

    def _get_synthetic_photo(self) -> str:
        """
        Downloads a synthetic face photo.
        Tries generated.photos API first, falls back to thispersondoesnotexist.com.
        Returns local file path.
        """
        import os
        import random

        os.makedirs("assets/photos", exist_ok=True)
        filename = f"assets/photos/persona_{random.randint(10000, 99999)}.jpg"

        # thispersondoesnotexist.com (free, no API key needed)
        try:
            resp = requests.get("https://thispersondoesnotexist.com", timeout=15)
            if resp.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Downloaded synthetic photo: {filename}")
                return filename
        except Exception as e:
            logger.warning(f"Could not download synthetic photo: {e}")

        return ""

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
