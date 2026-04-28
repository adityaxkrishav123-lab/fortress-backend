"""
dispatch/monitor_agent.py
==========================
Agent 5: The Monitor — The Passive Watcher.

Always running in the background across 1:50 regions.
Does NOT send cards. Only watches and updates them.

Responsibilities:
  1. Count accepted volunteers on volunteer request cards.
  2. Build and push the live accepted-volunteer profile list to the NGO.
  3. Flag cards that have been ACTIVE too long → trigger EscalationAgent.
  4. Auto-close expired ACTIVE cards (after 24 hrs).

This agent is started once at app startup via main.py and runs on a loop.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# How often the monitor polls Firestore (in seconds)
POLL_INTERVAL_SECONDS = 30

# How long an ACTIVE card lives before the monitor escalates it
ESCALATION_TIMEOUT_HOURS = 6

# How long before an ACTIVE card is auto-expired (hard cap)
EXPIRY_HOURS = 24


class MonitorAgent:
    """
    Agent 5 — The Passive Watcher.
    Instantiated once at startup. Watches 1:50 regions.
    """

    def __init__(self, monitored_regions: list[str]):
        self.monitored_regions = monitored_regions
        self.logger = logging.getLogger(f"MonitorAgent[{len(monitored_regions)} regions]")

    async def run_forever(self, db) -> None:
        """
        Main loop. Runs indefinitely in the background.
        Called from main.py at startup using asyncio.create_task().
        """
        self.logger.info("[MonitorAgent] Started. Watching regions...")
        while True:
            try:
                await self._scan_active_cards(db)
            except Exception as e:
                self.logger.error(f"[MonitorAgent] Scan error: {e}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _scan_active_cards(self, db) -> None:
        """
        Single scan cycle. Fetches ACTIVE cards within monitored regions.

        BUG-006 FIX: Now filters by sender_region to respect 1:50 region boundaries.
        Firestore `array_contains_any` supports up to 10 values per query,
        so we batch the regions into chunks of 10.
        """
        now = datetime.utcnow()
        docs_seen: set[str] = set()

        # Process monitored_regions in batches of 10 (Firestore limit for array_contains_any)
        region_batches = [
            self.monitored_regions[i:i + 10]
            for i in range(0, len(self.monitored_regions), 10)
        ]

        for batch in region_batches:
            query = (
                db.collection("action_cards")
                  .where("status", "==", "ACTIVE")
                  .where("sender_region", "in", batch)   # ✅ BUG-006 FIX: scoped to region
            )
            docs = await query.get()

            for doc in docs:
                card    = doc.to_dict()
                card_id = card.get("card_id")

                if card_id in docs_seen:
                    continue
                docs_seen.add(card_id)

                try:
                    expires_at = card.get("expires_at")
                    if expires_at and datetime.fromisoformat(expires_at) < now:
                        await self._expire_card(card_id, db)
                        continue

                    if card.get("card_type") == "NGO_VOLUNTEER_REQUEST":
                        await self._update_volunteer_profile_list(card_id, card, db)

                    created_at = card.get("created_at")
                    if created_at:
                        age_hours = (now - datetime.fromisoformat(created_at)).total_seconds() / 3600
                        if age_hours >= ESCALATION_TIMEOUT_HOURS and not card.get("escalated"):
                            await self._flag_for_escalation(card_id, card, db)

                except Exception as e:
                    self.logger.error(f"[MonitorAgent] Error processing card {card_id}: {e}")
                    continue


    async def _update_volunteer_profile_list(self, card_id: str, card: dict, db) -> None:
        """
        Builds a live list of accepted volunteer profiles and updates the card.
        The NGO sees this list grow in real-time as volunteers accept.
        """
        accepted_uids = card.get("accepted_by", [])
        # N-02 FIX: card field is "quantity_needed" (set by BUG-004 fix).
        # Fall back to legacy "quantity" key so old cards still work.
        quantity_needed = card.get("quantity_needed", 0) or card.get("quantity", 0) or 0

        if not accepted_uids:
            return

        # Fetch minimal profile data for each accepted volunteer
        profiles = []
        for uid in accepted_uids:
            user_doc = await db.collection("users").document(uid).get()
            if user_doc.exists:
                u = user_doc.to_dict()
                profiles.append({
                    "uid":        uid,
                    "name":       u.get("name"),
                    "phone":      u.get("phone"),
                    "profession": u.get("profession"),
                    "region":     u.get("region"),
                })

        update_payload = {
            "accepted_profiles": profiles,
            "accepted_count":    len(accepted_uids),
            "last_monitor_sync": datetime.utcnow().isoformat(),
        }

        # If quota is met, close the card AND generate the downloadable volunteer report
        if quantity_needed > 0 and len(accepted_uids) >= quantity_needed:
            update_payload["status"]         = "ACCEPTED"
            update_payload["quota_filled"]   = True
            update_payload["quota_filled_at"] = datetime.utcnow().isoformat()
            self.logger.info(f"[MonitorAgent] Card {card_id}: quota filled ({len(accepted_uids)}/{quantity_needed}). Closing.")

            # Auto-generate the volunteer roster report for the NGO
            try:
                from mailbox.action_card_engine import _generate_volunteer_roster_report
                await _generate_volunteer_roster_report(db, card_id, card, profiles)
            except Exception as e:
                self.logger.error(f"[MonitorAgent] Report generation failed for {card_id}: {e}")


        await db.collection("action_cards").document(card_id).update(update_payload)

    async def _flag_for_escalation(self, card_id: str, card: dict, db) -> None:
        """
        Flags the card as needing escalation and triggers the EscalationAgent.
        """
        self.logger.warning(f"[MonitorAgent] Card {card_id} has been ACTIVE too long. Escalating.")
        await db.collection("action_cards").document(card_id).update({
            "escalated":    True,
            "escalated_at": datetime.utcnow().isoformat(),
        })

        try:
            from dispatch.escalation_agent import EscalationAgent
            await EscalationAgent().escalate_stale_card(card_id, card, db)
        except Exception as e:
            self.logger.error(f"[MonitorAgent] Escalation trigger failed for {card_id}: {e}")

    async def _expire_card(self, card_id: str, db) -> None:
        """
        Hard-expires a card that passed the 24-hour limit with no response.
        """
        self.logger.info(f"[MonitorAgent] Card {card_id} expired. Auto-closing.")
        await db.collection("action_cards").document(card_id).update({
            "status":     "REJECTED",
            "expired":    True,
            "expired_at": datetime.utcnow().isoformat(),
        })
