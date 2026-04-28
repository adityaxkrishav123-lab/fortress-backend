"""
dispatch/regional_agent.py  (UPGRADED)
========================================
Agent 3: The Regional Dispatcher — Dual Mode.

MODE A — NGO_SERVICE:
  An NGO needs resources from another NGO (blankets, blood, trucks).
  Searches the entire District for matching NGOs.
  If no match in district → EscalationAgent (1:5 districts).

MODE B — INSTANT_HELP:
  A Citizen picked physical items from the INSTANT_HELP_ITEMS list.
  Searches NGO inventory across the district.
  Can split the fulfillment across multiple NGOs (e.g. 60 from B + 40 from C).

Region: District level for primary search.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Literal

from region_config import get_district_for_region, get_ngo_service_search_regions

logger = logging.getLogger(__name__)


class RegionalAgent:
    """
    Agent 3 — NGO-to-NGO Dispatcher (Dual Mode).
    Background worker. Called by action_card_engine._trigger_agent().
    """

    def __init__(self, mode: Literal["NGO_SERVICE", "INSTANT_HELP"] = "NGO_SERVICE"):
        self.mode = mode

    async def dispatch(self, card_id: str, card_doc: dict, db) -> None:
        """Main entry point. Routes to correct mode handler."""
        if self.mode == "NGO_SERVICE":
            await self._handle_ngo_service(card_id, card_doc, db)
        elif self.mode == "INSTANT_HELP":
            await self._handle_instant_help(card_id, card_doc, db)

    # ------------------------------------------------------------------
    # MODE A: NGO → NGO Service Request
    # ------------------------------------------------------------------

    async def _handle_ngo_service(self, card_id: str, card_doc: dict, db) -> None:
        """
        Finds a matching NGO in the same district that can supply what
        the requesting NGO needs.
        """
        requesting_ngo_id = card_doc.get("ngo_id")
        ngo_type          = card_doc.get("ngo_type")
        ngo_tags          = card_doc.get("ngo_tags", [])

        if not requesting_ngo_id or not ngo_type:
            logger.error(f"[RegionalAgent:NGO_SERVICE] Card {card_id}: missing ngo_id or ngo_type.")
            return

        # Get the requesting NGO's district
        ngo_doc = await db.collection("ngos").document(requesting_ngo_id).get()
        if not ngo_doc.exists:
            logger.error(f"[RegionalAgent:NGO_SERVICE] NGO {requesting_ngo_id} not found.")
            return

        ngo_region = ngo_doc.to_dict().get("region")
        district   = get_district_for_region(ngo_region)

        logger.info(f"[RegionalAgent:NGO_SERVICE] Card {card_id}: searching district '{district}' "
                    f"for ngo_type='{ngo_type}', tags={ngo_tags}")

        # Search all NGOs in the same district (excluding the requester)
        search_regions = get_ngo_service_search_regions(district)
        matched_ngo_admin_uids = []

        for region in search_regions:
            query = (
                db.collection("ngos")
                  .where("region", "==", region)
                  .where("ngo_type", "==", ngo_type)
            )
            docs = await query.get()
            for doc in docs:
                data = doc.to_dict()
                if data.get("ngo_id") == requesting_ngo_id:
                    continue    # Skip self
                ngo_registered_tags = data.get("ngo_tags", [])
                if any(tag in ngo_registered_tags for tag in ngo_tags):
                    matched_ngo_admin_uids.append(data.get("admin_uid"))

        if not matched_ngo_admin_uids:
            logger.warning(f"[RegionalAgent:NGO_SERVICE] No match in district. Escalating card {card_id}.")
            await self._escalate(card_id, card_doc, ngo_region, db)
            return

        await db.collection("action_cards").document(card_id).update({
            "addressed_to":    matched_ngo_admin_uids,
            "district_searched": district,
            "dispatched_at":   datetime.utcnow().isoformat(),
        })
        logger.info(f"[RegionalAgent:NGO_SERVICE] Card {card_id}: addressed to {len(matched_ngo_admin_uids)} NGOs.")

    # ------------------------------------------------------------------
    # MODE B: Instant Help — Physical Goods Matching
    # ------------------------------------------------------------------

    async def _handle_instant_help(self, card_id: str, card_doc: dict, db) -> None:
        """
        Citizen requested specific physical items from INSTANT_HELP_ITEMS.
        Finds NGOs with matching inventory in the district.
        Can split fulfillment across multiple NGOs.
        """
        sender_uid    = card_doc.get("sender_uid")
        items_needed  = card_doc.get("items_needed", [])   # list of item names

        if not items_needed:
            logger.error(f"[RegionalAgent:INSTANT_HELP] Card {card_id}: no items listed.")
            return

        sender_doc = await db.collection("users").document(sender_uid).get()
        if not sender_doc.exists:
            return

        sender_region = sender_doc.to_dict().get("region")
        district      = get_district_for_region(sender_region)

        logger.info(f"[RegionalAgent:INSTANT_HELP] Card {card_id}: finding {items_needed} in district '{district}'.")

        # --- GAP 1 FIX: Splitter Engine (Intelligent Fragmentation) ---
        # Find NGOs with inventory and dynamically split the requested quantity
        search_regions = get_ngo_service_search_regions(district)
        matched_uids = []
        fragmented_cards = []
        quantity_needed = card_doc.get("quantity_needed", 0)
        remaining_to_allocate = quantity_needed

        for region in search_regions:
            inv_query = (
                db.collection("ngo_inventory")
                  .where("region", "==", region)
                  .where("available", "==", True)
            )
            inv_docs = await inv_query.get()
            for doc in inv_docs:
                if quantity_needed > 0 and remaining_to_allocate <= 0:
                    break
                    
                inv = doc.to_dict()
                if any(item in inv.get("item_name", "") for item in items_needed):
                    ngo_uid = inv.get("admin_uid")
                    inv_qty = inv.get("quantity", 0)
                    
                    if ngo_uid and inv_qty > 0 and ngo_uid not in matched_uids:
                        allocation = min(remaining_to_allocate, inv_qty) if quantity_needed > 0 else 0
                        
                        # Create a Fragmented Action Card specifically for this NGO
                        frag_card_id = f"FRAG-{uuid.uuid4().hex[:8].upper()}"
                        frag_doc = dict(card_doc)
                        frag_doc.update({
                            "card_id": frag_card_id,
                            "parent_card_id": card_id,
                            "addressed_to": [ngo_uid],
                            "quantity_needed": allocation if allocation > 0 else card_doc.get("quantity_needed"),
                            "fragmented": True,
                            "dispatched_at": datetime.utcnow().isoformat()
                        })
                        fragmented_cards.append(frag_doc)
                        matched_uids.append(ngo_uid)
                        remaining_to_allocate -= allocation

        if not matched_uids:
            logger.warning(f"[RegionalAgent:INSTANT_HELP] No inventory match for card {card_id}. Escalating.")
            await self._escalate(card_id, card_doc, sender_region, db)
            return

        # Save all Fragmented Cards to the database
        for frag in fragmented_cards:
            await db.collection("action_cards").document(frag["card_id"]).set(frag)

        # Update the main Parent Card to track the fragments
        await db.collection("action_cards").document(card_id).update({
            "addressed_to":  matched_uids,
            "dispatched_at": datetime.utcnow().isoformat(),
            "fragmented_into": [f["card_id"] for f in fragmented_cards]
        })
        logger.info(f"[RegionalAgent:INSTANT_HELP] Card {card_id} fragmented into {len(fragmented_cards)} sub-cards for {len(matched_uids)} NGOs.")

    # ------------------------------------------------------------------
    # PARTIAL FULFILLMENT RESUME — Called after an NGO commits partial supply
    # ------------------------------------------------------------------

    async def continue_partial(self, card_id: str, card: dict, db) -> str:
        """
        Resumes the Instant Help search after a partial commitment.
        Skips NGOs already in the fulfillment_log (already committed).
        Returns "EXHAUSTED" when all escalation districts have been searched.
        """
        sender_uid   = card.get("sender_uid")
        items_needed = card.get("items_needed", [])
        already_committed_uids = {
            entry["supplier_uid"]
            for entry in card.get("fulfillment_log", [])
        }
        already_addressed = set(card.get("addressed_to", []))

        citizen_doc = await db.collection("users").document(sender_uid).get()
        if not citizen_doc.exists:
            return "EXHAUSTED"

        origin_region = citizen_doc.to_dict().get("region", "")
        from region_config import get_escalation_districts, get_ngo_service_search_regions

        all_districts = get_escalation_districts(origin_region, max_districts=5)
        newly_found   = []

        for district in all_districts:
            regions = get_ngo_service_search_regions(district)
            for region in regions:
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
                        if uid and uid not in already_committed_uids and uid not in already_addressed:
                            newly_found.append(uid)

        if not newly_found:
            return "EXHAUSTED"

        await db.collection("action_cards").document(card_id).update({
            "addressed_to": list(already_addressed) + newly_found,
            "last_updated": datetime.utcnow().isoformat(),
        })
        logger.info(f"[RegionalAgent:PARTIAL] Card {card_id}: found {len(newly_found)} more NGOs to contact.")
        return "CONTINUED"

    async def _escalate(self, card_id: str, card_doc: dict, region: str, db) -> None:
        try:
            from dispatch.escalation_agent import EscalationAgent
            await EscalationAgent().escalate_regional_card(card_id, card_doc, region, db)
        except Exception as e:
            logger.error(f"[RegionalAgent] Escalation failed for {card_id}: {e}")
