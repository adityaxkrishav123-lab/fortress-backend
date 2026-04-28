"""
dispatch/citizen_agent.py
==========================
Agent 1: The Citizen Dispatcher.

Upgraded from community_master.py to use the new catalog-based tag matching.
When a Citizen creates a CITIZEN_SOS or CITIZEN_SERVICE card:
  1. Reads their ngo_type + ngo_tags from the card.
  2. Searches Firestore for NGOs in up to 10 surrounding sub-regions.
  3. Drops the Action Card into every matching NGO's addressed_to list.
  4. If zero matches found → hands off to EscalationAgent.

Region search: State / Sub-State level (1:10 sub-regions max).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from auth_gate.catalog import is_valid_ngo_type
from region_config import get_citizen_search_regions   # returns up to 10 sub-regions

logger = logging.getLogger(__name__)

MAX_REGIONS_TO_SEARCH = 10


class CitizenAgent:
    """
    Agent 1 — Citizen → NGO Dispatcher.
    Background worker. Not exposed as an HTTP endpoint.
    Called by action_card_engine._trigger_agent().
    """

    async def dispatch(self, card_id: str, card_doc: dict, db) -> None:
        """
        Main entry point. Finds matching NGOs and links them to the Action Card.
        """
        sender_uid = card_doc.get("sender_uid")
        ngo_type   = card_doc.get("ngo_type")
        ngo_tags   = card_doc.get("ngo_tags", [])

        if not ngo_type or not is_valid_ngo_type(ngo_type):
            logger.error(f"[CitizenAgent] Card {card_id}: invalid ngo_type '{ngo_type}'. Aborting.")
            return

        # Fetch the Citizen's region from their profile
        citizen_doc = await db.collection("users").document(sender_uid).get()
        if not citizen_doc.exists:
            logger.error(f"[CitizenAgent] Citizen {sender_uid} not found. Aborting.")
            return

        citizen_region = citizen_doc.to_dict().get("region")

        # Try GPS-based live region first
        lat = card_doc.get("latitude")
        lon = card_doc.get("longitude")
        
        live_region = None
        if lat is not None and lon is not None:
            from region_config import get_region_from_gps
            live_region = get_region_from_gps(lat, lon)
            
        search_origin_region = live_region if live_region else citizen_region

        if not search_origin_region:
            logger.error(f"[CitizenAgent] Citizen {sender_uid} has no region and no valid GPS. Aborting.")
            return

        # Get up to 10 surrounding sub-regions to search based on the exact live location
        search_regions = get_citizen_search_regions(search_origin_region, max_regions=MAX_REGIONS_TO_SEARCH)
        logger.info(f"[CitizenAgent] Card {card_id}: searching {len(search_regions)} regions for "
                    f"ngo_type='{ngo_type}', tags={ngo_tags}")

        matched_ngo_ids = await self._find_matching_ngos(db, ngo_type, ngo_tags, search_regions)

        if not matched_ngo_ids:
            logger.warning(f"[CitizenAgent] Card {card_id}: No matching NGOs found. Escalating.")
            await self._escalate(card_id, card_doc, search_origin_region, db)
            return

        # Address the card to all matching NGOs
        await db.collection("action_cards").document(card_id).update({
            "addressed_to":    matched_ngo_ids,
            "regions_searched": search_regions,
            "dispatched_at":   datetime.utcnow().isoformat(),
        })
        
        # Trigger the GLOW for the Admins of matched NGOs
        for nid in matched_ngo_ids:
            try:
                # Find the Admin for this NGO
                admin_query = await db.collection("users").where("ngo_id", "==", nid).where("role", "==", "NGO_ADMIN").limit(1).get()
                if admin_query:
                    admin_uid = admin_query[0].id
                    await db.collection("users").document(admin_uid).update({"has_unread_updates": True})
            except Exception as e:
                logger.error(f"[CitizenAgent] Failed to trigger glow for NGO {nid}: {e}")

        logger.info(f"[CitizenAgent] Card {card_id}: dispatched to {len(matched_ngo_ids)} NGOs. Glow Activated.")

    async def _find_matching_ngos(
        self,
        db,
        ngo_type:    str,
        ngo_tags:    list[str],
        regions:     list[str],
    ) -> list[str]:
        """
        Searches Firestore for verified NGOs that:
          - Are in one of the search regions
          - Have matching ngo_type
          - Have at least ONE matching ngo_tag
        Returns a list of NGO admin UIDs (used as addressed_to on the card).
        """
        matched = []
        for region in regions:
            query = (
                db.collection("ngos")
                  .where("region", "==", region)
                  .where("ngo_type", "==", ngo_type)
                  .where("is_tier2_verified", "==", True)   # Only verified NGOs receive cards
            )
            docs = await query.get()
            for doc in docs:
                ngo_data = doc.to_dict()
                ngo_tags_registered = ngo_data.get("ngo_tags", [])
                # At least one tag must match
                if any(tag in ngo_tags_registered for tag in ngo_tags):
                    matched.append(ngo_data.get("admin_uid"))

        return [uid for uid in matched if uid]  # Filter out any None values

    async def _escalate(self, card_id: str, card_doc: dict, region: str, db) -> None:
        """Hands off to the EscalationAgent when no local NGO is found."""
        from dispatch.escalation_agent import EscalationAgent
        try:
            await EscalationAgent().escalate_citizen_card(card_id, card_doc, region, db)
        except Exception as e:
            logger.error(f"[CitizenAgent] Escalation failed for card {card_id}: {e}")
