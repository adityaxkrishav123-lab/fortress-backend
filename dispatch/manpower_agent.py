"""
dispatch/manpower_agent.py  (UPGRADED)
========================================
Agent 2: The Volunteer Recruiter.

When an NGO posts an NGO_VOLUNTEER_REQUEST card:
  1. Reads the required profession_tags and quantity from the card.
  2. Searches for volunteers in the NGO's Taluka ONLY
     (1 Taluka if big area, up to 3 Talukas if small area).
  3. Sends the Action Card to ALL matched volunteers in that zone.
  4. Stops — it does NOT wait for responses.
  5. MonitorAgent takes over to count accepts and build the profile list.

Region: Taluka level (hyperlocal).
PRO volunteers get priority for specialized tasks (Medical, Rescue, Technical).
GENERAL volunteers are eligible for SUPPORT and GENERAL tagged requests only.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from auth_gate.catalog import is_valid_profession_tag, get_profession_group
from region_config import get_volunteer_talukas_for_region

logger = logging.getLogger(__name__)


class ManpowerAgent:
    """
    Agent 2 — Volunteer Recruiter.
    Background worker. Called by action_card_engine._trigger_agent().
    """

    async def dispatch(self, card_id: str, card_doc: dict, db) -> None:
        """Main entry point."""
        ngo_id           = card_doc.get("ngo_id")
        required_tags    = card_doc.get("ngo_tags", [])     # profession tags requested by NGO
        quantity_needed  = card_doc.get("quantity", 0) or 0

        if not ngo_id or not required_tags:
            logger.error(f"[ManpowerAgent] Card {card_id}: missing ngo_id or tags. Aborting.")
            return

        # Validate all requested tags against the catalog
        invalid_tags = [t for t in required_tags if not is_valid_profession_tag(t)]
        if invalid_tags:
            logger.error(f"[ManpowerAgent] Card {card_id}: invalid tags {invalid_tags}.")
            return

        # Determine if any requested tags are "specialized" (non-GENERAL/SUPPORT)
        is_specialized = any(
            get_profession_group(tag) in ("MEDICAL", "TECHNICAL", "RESCUE")
            for tag in required_tags
        )

        # Get the NGO's region, then derive its Talukas
        ngo_doc = await db.collection("ngos").document(ngo_id).get()
        if not ngo_doc.exists:
            logger.error(f"[ManpowerAgent] NGO {ngo_id} not found.")
            return

        ngo_region = ngo_doc.to_dict().get("region")
        talukas    = get_volunteer_talukas_for_region(ngo_region)   # 1 or up to 3

        logger.info(f"[ManpowerAgent] Card {card_id}: searching {talukas} for tags={required_tags}, "
                    f"specialized={is_specialized}")

        matched_volunteer_uids = await self._find_volunteers(
            db, talukas, required_tags, is_specialized
        )

        if not matched_volunteer_uids:
            logger.warning(f"[ManpowerAgent] No volunteers found for card {card_id}.")
            # Write a note on the card but do NOT escalate — volunteers are hyper-local
            await db.collection("action_cards").document(card_id).update({
                "no_volunteers_found": True,
                "talukas_searched":    talukas,
            })
            return

        # Address the card to ALL matched volunteers
        await db.collection("action_cards").document(card_id).update({
            "addressed_to":    matched_volunteer_uids,
            "talukas_searched": talukas,
            "dispatched_at":   datetime.utcnow().isoformat(),
            "quantity":        quantity_needed,
            "accepted_by":     [],      # MonitorAgent will populate this
        })
        
        # Trigger the GLOW for all matched volunteers
        for uid in matched_volunteer_uids:
            try:
                await db.collection("users").document(uid).update({"has_unread_updates": True})
            except Exception as e:
                logger.error(f"[ManpowerAgent] Failed to trigger glow for {uid}: {e}")

        logger.info(f"[ManpowerAgent] Card {card_id}: dispatched to "
                    f"{len(matched_volunteer_uids)} volunteers across {talukas}. Glow Activated.")

    async def _find_volunteers(
        self,
        db,
        talukas:       list[str],
        required_tags: list[str],
        is_specialized: bool,
    ) -> list[str]:
        """
        Searches Firestore for volunteers in the given Talukas.

        Rules:
        - Volunteer must be verified (is_verified = True).
        - Volunteer must have at least ONE matching profession tag.
        - If the task is specialized (Medical/Rescue/Technical),
          only PRO volunteers (volunteer_type = PRO) are eligible.
        - GENERAL tasks accept both GENERAL and PRO volunteers.
        """
        matched = []

        for taluka in talukas:
            query = (
                db.collection("users")
                  .where("role", "==", "VOLUNTEER")
                  .where("region", "==", taluka)
                  .where("is_verified", "==", True)
            )
            # BUG-005 FIX: Removed volunteer_type == "PRO" filter.
            # volunteer_type is never set in the registration flow.
            # Profession tag presence IS the qualification gate.
            # Specialized tags (Medical/Rescue/Technical) are only granted
            # to volunteers who uploaded valid skill certificates at signup.

            docs = await query.get()
            for doc in docs:
                v = doc.to_dict()
                volunteer_tags = v.get("profession_tags", [])
                if any(tag in volunteer_tags for tag in required_tags):
                    uid = v.get("uid")
                    if uid and uid not in matched:  # ✅ BUG-010 FIX: dedup
                        matched.append(uid)

        return matched
