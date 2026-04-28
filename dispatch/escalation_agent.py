"""
dispatch/escalation_agent.py  (UPGRADED)
==========================================
Agent 4: The Escalation Expander.

Triggered when:
  a) CitizenAgent finds zero matching NGOs in 10 regions.
  b) RegionalAgent finds zero matching NGOs/inventory in a district.
  c) MonitorAgent flags a card that has been ACTIVE too long.

Expands outward by 1:5 districts and re-dispatches the card.
If still no match after expansion → card is marked ESCALATION_FAILED
and the Admin is notified.
"""

from __future__ import annotations

import logging
from datetime import datetime

from region_config import (
    get_escalation_districts,       # returns up to 5 adjacent districts
    get_ngo_service_search_regions,
)

logger = logging.getLogger(__name__)

MAX_ESCALATION_DISTRICTS = 5


class EscalationAgent:
    """
    Agent 4 — The Escalation Expander.
    Background worker. Not exposed as an HTTP endpoint.
    """

    async def escalate_citizen_card(
        self, card_id: str, card_doc: dict, origin_region: str, db
    ) -> None:
        """
        Escalates a CITIZEN_SOS or CITIZEN_SERVICE card.
        Expands the NGO search across 5 adjacent districts.
        """
        ngo_type = card_doc.get("ngo_type")
        ngo_tags = card_doc.get("ngo_tags", [])

        logger.info(f"[EscalationAgent] Escalating citizen card {card_id} from region '{origin_region}'.")

        districts_to_search = get_escalation_districts(origin_region, max_districts=MAX_ESCALATION_DISTRICTS)
        matched_uids = []

        for district in districts_to_search:
            regions = get_ngo_service_search_regions(district)
            for region in regions:
                query = (
                    db.collection("ngos")
                      .where("region", "==", region)
                      .where("ngo_type", "==", ngo_type)
                      .where("is_tier2_verified", "==", True)
                )
                docs = await query.get()
                for doc in docs:
                    data = doc.to_dict()
                    if any(tag in data.get("ngo_tags", []) for tag in ngo_tags):
                        uid = data.get("admin_uid")
                        if uid:
                            matched_uids.append(uid)

        await self._apply_escalation_result(card_id, matched_uids, districts_to_search, db)

    async def escalate_regional_card(
        self, card_id: str, card_doc: dict, origin_region: str, db
    ) -> None:
        """
        Escalates a NGO_TO_NGO_SERVICE or INSTANT_HELP card.
        Expands the search across 5 adjacent districts.
        """
        ngo_type = card_doc.get("ngo_type")
        ngo_tags = card_doc.get("ngo_tags", [])
        items_needed = card_doc.get("items_needed", [])
        card_type = card_doc.get("card_type")

        logger.info(f"[EscalationAgent] Escalating regional card {card_id} from '{origin_region}'.")

        districts_to_search = get_escalation_districts(origin_region, max_districts=MAX_ESCALATION_DISTRICTS)
        matched_uids = []

        for district in districts_to_search:
            regions = get_ngo_service_search_regions(district)
            for region in regions:
                if card_type == "INSTANT_HELP":
                    inv_query = (
                        db.collection("ngo_inventory")
                          .where("region", "==", region)
                          .where("available", "==", True)
                    )
                    inv_docs = await inv_query.get()
                    for doc in inv_docs:
                        inv = doc.to_dict()
                        if any(item in inv.get("item_name", "") for item in items_needed):
                            uid = inv.get("admin_uid")
                            if uid and uid not in matched_uids:
                                matched_uids.append(uid)
                else:
                    query = (
                        db.collection("ngos")
                          .where("region", "==", region)
                          .where("ngo_type", "==", ngo_type)
                    )
                    docs = await query.get()
                    for doc in docs:
                        data = doc.to_dict()
                        if any(tag in data.get("ngo_tags", []) for tag in ngo_tags):
                            uid = data.get("admin_uid")
                            if uid and uid not in matched_uids:
                                matched_uids.append(uid)

        await self._apply_escalation_result(card_id, matched_uids, districts_to_search, db)

    async def escalate_stale_card(self, card_id: str, card_doc: dict, db) -> None:
        """
        Called by MonitorAgent when a card has been ACTIVE too long.
        Re-runs the appropriate escalation based on card type.
        """
        card_type     = card_doc.get("card_type", "")
        origin_region = card_doc.get("sender_region", "")

        # N-05 FIX: Guard against empty region before calling get_escalation_districts().
        # An empty region would raise ValueError inside escalate_citizen/regional_card,
        # bubble up to MonitorAgent's except, and silently skip escalation with no trace.
        # Instead, log a clear message so the issue is visible in logs.
        if not origin_region:
            logger.warning(
                f"[EscalationAgent] Card {card_id}: sender_region is empty — "
                f"cannot escalate. This card was likely created before the N-03 fix. "
                f"Skipping escalation."
            )
            return

        logger.info(f"[EscalationAgent] Stale card {card_id} (type={card_type}). Re-escalating.")

        if card_type in ("CITIZEN_SOS", "CITIZEN_SERVICE"):
            await self.escalate_citizen_card(card_id, card_doc, origin_region, db)
        elif card_type in ("NGO_TO_NGO_SERVICE", "INSTANT_HELP"):
            await self.escalate_regional_card(card_id, card_doc, origin_region, db)
        else:
            logger.warning(f"[EscalationAgent] Unknown card type '{card_type}' for {card_id}.")

    async def _apply_escalation_result(
        self, card_id: str, matched_uids: list[str], districts_searched: list[str], db
    ) -> None:
        """Applies the result of an escalation — either addresses new NGOs or marks failure."""
        if matched_uids:
            await db.collection("action_cards").document(card_id).update({
                "addressed_to":       matched_uids,
                "escalated":          True,
                "escalation_districts": districts_searched,
                "dispatched_at":      datetime.utcnow().isoformat(),
            })
            logger.info(f"[EscalationAgent] Card {card_id}: escalation succeeded. "
                        f"Addressed to {len(matched_uids)} NGOs across {len(districts_searched)} districts.")
        else:
            await db.collection("action_cards").document(card_id).update({
                "escalation_failed":    True,
                "escalation_failed_at": datetime.utcnow().isoformat(),
                "status":               "ACTIVE",   # Keep active for manual admin review
            })
            logger.error(f"[EscalationAgent] Card {card_id}: escalation FAILED. "
                         f"No match in {len(districts_searched)} districts.")
