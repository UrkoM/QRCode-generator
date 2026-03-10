"""
Master Orchestrator — entry point for the autonomous outreach system.

Usage:
    python orchestrator.py --mode copilot          # Use real LinkedIn account
    python orchestrator.py --mode autonomous       # Use AI synthetic persona
    python orchestrator.py --mode copilot --dry-run
    python orchestrator.py --mode copilot --action followup   # Only run follow-ups
    python orchestrator.py --mode copilot --action inbox      # Only check inbox
    python orchestrator.py --mode autonomous --create-persona # Create new persona
    python orchestrator.py --mode autonomous --health-check   # Check account health
"""
from __future__ import annotations
import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("orchestrator")

# ── Arg parsing ───────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LinkedIn Outreach Agent System")
    parser.add_argument(
        "--mode", choices=["copilot", "autonomous"], default="copilot",
        help="copilot = real account, autonomous = AI synthetic persona"
    )
    parser.add_argument(
        "--action",
        choices=["full", "search", "qualify", "outreach", "followup", "inbox"],
        default="full",
        help="Which part of the pipeline to run (default: full)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate messages but do not send")
    parser.add_argument("--create-persona", action="store_true", help="[Modo A] Create a new persona")
    parser.add_argument("--health-check", action="store_true", help="[Modo A] Run account health checks")
    parser.add_argument("--max-prospects", type=int, default=50, help="Max prospects to search per run")
    return parser.parse_args()


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run_copilot_pipeline(args: argparse.Namespace, strategy: dict) -> None:
    from models.prospect import ProspectStatus, OutreachMode
    from agents.mode_b.session_manager import SessionManager
    from agents.shared.search_agent import SearchAgent
    from agents.shared.qualification_agent import QualificationAgent
    from agents.shared.connection_agent import ConnectionAgent
    from agents.shared.followup_agent import FollowupAgent
    from agents.shared.meeting_closer import MeetingCloserAgent
    from integrations.airtable_client import AirtableClient

    mode = OutreachMode.COPILOT
    db = AirtableClient()

    # Ensure LinkedIn session is valid
    session = SessionManager()
    if not session.ensure_session():
        logger.error("Cannot start: LinkedIn session invalid. Run --force-login first.")
        return

    action = args.action

    if action in ("full", "search"):
        logger.info("=== SEARCH: Finding new prospects ===")
        searcher = SearchAgent(mode=mode)
        new_prospects = searcher.run_search(strategy, max_results=args.max_prospects)
        logger.info(f"Found {len(new_prospects)} new prospects")
    else:
        new_prospects = []

    if action in ("full", "qualify"):
        logger.info("=== QUALIFY: Scoring prospects ===")
        from agents.shared.qualification_agent import QualificationAgent
        qualifier = QualificationAgent(mode=mode)
        new_raw = db.get_prospects_by_status(ProspectStatus.NEW)
        qualified = qualifier.run_qualification(new_raw, strategy)
        logger.info(f"Qualified {len(qualified)} prospects")
    else:
        qualified = []

    if action in ("full", "outreach"):
        logger.info("=== OUTREACH: Sending connection requests ===")
        connector = ConnectionAgent(mode=mode)
        ready = db.get_prospects_by_status(ProspectStatus.QUALIFIED)
        sent = connector.run_outreach(ready, strategy)
        logger.info(f"Sent {sent} connection requests")

    if action in ("full", "followup"):
        logger.info("=== FOLLOW-UP: Processing scheduled follow-ups ===")
        followup = FollowupAgent(mode=mode)
        accepted = followup.check_new_acceptances(strategy)
        scheduled = followup.run_scheduled_followups(strategy)
        logger.info(f"Follow-ups: {accepted} new acceptances, {scheduled} scheduled messages")

    if action in ("full", "inbox"):
        logger.info("=== INBOX: Checking replies ===")
        closer = MeetingCloserAgent(mode=mode)
        processed = closer.run_inbox_check()
        logger.info(f"Processed {processed} inbox replies")


def run_autonomous_pipeline(args: argparse.Namespace, strategy: dict) -> None:
    from models.prospect import ProspectStatus, OutreachMode
    from agents.mode_a.persona_factory import PersonaFactory
    from agents.mode_a.account_setup import AccountSetupAgent
    from agents.mode_a.account_manager import AccountManager
    from agents.shared.search_agent import SearchAgent
    from agents.shared.qualification_agent import QualificationAgent
    from agents.shared.connection_agent import ConnectionAgent
    from agents.shared.followup_agent import FollowupAgent
    from agents.shared.meeting_closer import MeetingCloserAgent
    from integrations.airtable_client import AirtableClient

    mode = OutreachMode.AUTONOMOUS
    db = AirtableClient()
    manager = AccountManager()

    if args.health_check:
        logger.info("=== HEALTH CHECK: Checking all autonomous accounts ===")
        summary = manager.check_all_accounts()
        logger.info(f"Results: {summary}")
        return

    if args.create_persona:
        logger.info("=== CREATING NEW PERSONA ===")
        factory = PersonaFactory()
        persona = factory.create_persona(strategy)
        setup = AccountSetupAgent()
        persona = setup.setup_account(persona)
        db.create_persona(persona)
        logger.info(f"New persona created: {persona.persona_name} @ {persona.linkedin_url}")
        return

    # Get an active persona to operate with
    persona = db.get_persona_with_capacity()
    if not persona:
        logger.error("No active personas with capacity. Create one with --create-persona.")
        return

    cookies_file = f"linkedin_session_{persona.persona_name.replace(' ', '_')}.json"
    proxy = f"http://{persona.proxy_ip}" if persona.proxy_ip else None

    action = args.action

    if action in ("full", "search"):
        logger.info(f"=== SEARCH as {persona.persona_name} ===")
        searcher = SearchAgent(mode=mode, proxy=persona.proxy_ip)
        new_prospects = searcher.run_search(strategy, max_results=args.max_prospects)
        logger.info(f"Found {len(new_prospects)} new prospects")

    if action in ("full", "qualify"):
        logger.info("=== QUALIFY ===")
        qualifier = QualificationAgent(mode=mode, proxy=persona.proxy_ip)
        raw = db.get_prospects_by_status(ProspectStatus.NEW)
        qualified = qualifier.run_qualification(raw, strategy)
        logger.info(f"Qualified {len(qualified)} prospects")

    if action in ("full", "outreach"):
        logger.info(f"=== OUTREACH as {persona.persona_name} ===")
        connector = ConnectionAgent(mode=mode, proxy=persona.proxy_ip, cookies_file=cookies_file)
        ready = db.get_prospects_by_status(ProspectStatus.QUALIFIED)
        sent = connector.run_outreach(ready, strategy)
        db.update_persona(persona, {
            "invites_this_week": persona.invites_this_week + sent
        })

    if action in ("full", "followup"):
        logger.info("=== FOLLOW-UP ===")
        followup = FollowupAgent(mode=mode, proxy=persona.proxy_ip, cookies_file=cookies_file)
        followup.check_new_acceptances(strategy)
        followup.run_scheduled_followups(strategy)

    if action in ("full", "inbox"):
        logger.info("=== INBOX CHECK ===")
        closer = MeetingCloserAgent(mode=mode, proxy=persona.proxy_ip, cookies_file=cookies_file)
        closer.run_inbox_check()


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    # Apply dry-run globally
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        logger.info("DRY RUN mode enabled — no messages will be sent")

    # Validate input files exist
    if not os.path.exists("input/positioning_strategy.md"):
        logger.error("Missing: input/positioning_strategy.md")
        sys.exit(1)
    if not os.path.exists("input/icp_description.txt"):
        logger.error("Missing: input/icp_description.txt")
        sys.exit(1)

    # Build strategy (shared between both modes)
    logger.info("=== STRATEGY: Building campaign strategy ===")
    from agents.shared.strategy_agent import StrategyAgent
    strategy_agent = StrategyAgent()
    strategy = strategy_agent.run_strategy()
    logger.info(f"Campaign: {strategy.get('campaign_name', 'unknown')}")

    if args.mode == "copilot":
        run_copilot_pipeline(args, strategy)
    else:
        run_autonomous_pipeline(args, strategy)

    logger.info("=== Orchestrator run complete ===")


if __name__ == "__main__":
    main()
