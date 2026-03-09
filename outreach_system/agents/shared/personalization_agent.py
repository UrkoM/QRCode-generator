from __future__ import annotations
import json
import logging
import re
from agents.base_agent import BaseAgent
from models.prospect import Prospect

logger = logging.getLogger(__name__)


class PersonalizationAgent(BaseAgent):
    """
    Generates personalized LinkedIn invite note and DM sequence for each prospect.
    """

    def __init__(self):
        super().__init__(model=self.SONNET)

    def generate_invite_note(self, prospect: Prospect, strategy: dict) -> str:
        """Generate a personalized connection request note (max 300 chars)."""
        system = self._load_prompt("personalization_invite.txt")
        profile_data = json.loads(prospect.notes) if prospect.notes else {}

        user_msg = f"""## ESTRATEGIA Y MESSAGING
Tono: {strategy.get('tone', 'profesional')}
Hook: {strategy.get('messaging_framework', {}).get('hook', '')}
Value proposition: {strategy.get('messaging_framework', {}).get('core_message', '')}
CTA: {strategy.get('messaging_framework', {}).get('cta', '')}

## DATOS DEL PROSPECTO
Nombre: {prospect.name}
Cargo: {prospect.title}
Empresa: {prospect.company}
About: {profile_data.get('about', '')[:300]}
Posts recientes: {str(profile_data.get('recent_posts', []))[:200]}
Ubicación: {profile_data.get('location', '')}

Idioma a usar: {strategy.get('language', 'español')}"""

        note = self.run(system, user_msg, max_tokens=200)
        note = note.strip().strip('"').strip("'")
        return note[:300]

    def generate_dm_sequence(self, prospect: Prospect, strategy: dict) -> dict:
        """Generate the full DM sequence (msgs 1-4) after connection is accepted."""
        system = self._load_prompt("personalization_dm.txt")
        profile_data = json.loads(prospect.notes) if prospect.notes else {}

        user_msg = f"""## ESTRATEGIA
{json.dumps(strategy.get('messaging_framework', {}), ensure_ascii=False)}
Value propositions: {json.dumps(strategy.get('value_propositions', []), ensure_ascii=False)}
Tono: {strategy.get('tone', 'profesional')}
Calendly: {__import__('config').config.CALENDLY_LINK}

## DATOS DEL PROSPECTO
Nombre: {prospect.name}
Cargo: {prospect.title}
Empresa: {prospect.company}
About: {profile_data.get('about', '')[:400]}
Posts recientes: {str(profile_data.get('recent_posts', []))[:300]}

Idioma: {strategy.get('language', 'español')}"""

        raw = self.run(system, user_msg, max_tokens=2048)
        return self._parse_json(raw)

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
