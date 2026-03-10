from __future__ import annotations
import logging
import time
from datetime import datetime, timedelta
from integrations.airtable_client import AirtableClient
from models.prospect import Prospect
from config import config

logger = logging.getLogger(__name__)


class ApprovalGate:
    """
    Optional human-in-the-loop gate for Mode B.
    Writes pending messages to Airtable for user review.
    Auto-sends after APPROVAL_TIMEOUT_HOURS if not reviewed.
    Only active when APPROVAL_GATE_ENABLED=true in config.
    """

    def __init__(self):
        self.db = AirtableClient()
        self.enabled = config.APPROVAL_GATE_ENABLED
        self.timeout_hours = config.APPROVAL_TIMEOUT_HOURS

    def submit_for_approval(
        self,
        prospect: Prospect,
        message_body: str,
        touchpoint: int,
    ) -> str:
        """
        Submits a message for approval. Returns 'approved', 'rejected', or 'timeout'.
        If gate is disabled, returns 'approved' immediately.
        """
        if not self.enabled:
            return "approved"

        # Write to Airtable with status pending_approval
        record = self.db.messages.create({
            "prospect_id": prospect.airtable_id or prospect.name,
            "prospect_name": prospect.name,
            "channel": "linkedin",
            "touchpoint": touchpoint,
            "message_body": message_body,
            "sent_at": None,
            "replied": False,
            "approval_status": "pending_approval",
            "submitted_at": datetime.now().isoformat(),
        })
        record_id = record["id"]
        deadline = datetime.now() + timedelta(hours=self.timeout_hours)

        logger.info(
            f"Message submitted for approval (record {record_id}). "
            f"Auto-send in {self.timeout_hours}h if not reviewed."
        )

        # Poll for approval
        while datetime.now() < deadline:
            time.sleep(60)  # Check every minute
            updated = self.db.messages.get(record_id)
            status = updated.get("fields", {}).get("approval_status", "pending_approval")
            if status == "approved":
                logger.info(f"Message approved by user for {prospect.name}")
                return "approved"
            if status == "rejected":
                logger.info(f"Message rejected by user for {prospect.name}")
                return "rejected"

        # Timeout → auto-approve
        self.db.messages.update(record_id, {"approval_status": "auto_approved"})
        logger.info(f"Approval timeout reached for {prospect.name} — auto-sending")
        return "approved"
