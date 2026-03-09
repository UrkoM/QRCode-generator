from __future__ import annotations
import json
import logging
import os
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class StrategyAgent(BaseAgent):
    """
    Reads positioning_strategy.md + icp_description.txt and produces
    a structured campaign strategy JSON used by all other agents.
    """

    def __init__(self):
        super().__init__(model=self.SONNET)

    def run_strategy(
        self,
        positioning_path: str = "input/positioning_strategy.md",
        icp_path: str = "input/icp_description.txt",
    ) -> dict:
        positioning = self._read_file(positioning_path)
        icp = self._read_file(icp_path)

        system = self._load_prompt("strategy.txt")
        user_msg = f"""## ESTRATEGIA DE POSICIONAMIENTO
{positioning}

## DESCRIPCIÓN DEL ICP (Ideal Customer Profile)
{icp}"""

        raw = self.run(system, user_msg, max_tokens=4096)

        # Extract JSON from response
        strategy = self._parse_json(raw)
        logger.info(f"Strategy generated: {len(strategy.get('search_keywords', []))} keywords, "
                    f"{len(strategy.get('value_propositions', []))} value props")
        return strategy

    def _read_file(self, path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required input file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json(self, text: str) -> dict:
        # Try to find JSON block in response
        import re
        match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
        if match:
            return json.loads(match.group(1))
        # Try raw JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from strategy agent; returning raw")
            return {"raw": text}
