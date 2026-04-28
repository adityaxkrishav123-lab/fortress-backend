import logging
import uuid
from typing import List
from models.shared import OrderItem, RequestCategory
from models.ngo_profile import NGOProfile
from models.citizen_profile import DisasterRequest
from models.dispatch_core import DispatchOrder 

from utils import haversine
from standards import SPECIFIC_HELP_TAGS, CITIZEN_TRANSLATIONS

class CommunityMaster:
    """
    AGENT 5: The 1:50 Philanthropist (Multilingual).
    Maintains the 'English Core, Local Face' strategy.
    Matches local language requests to English NGO profiles.
    """
    def __init__(self, master_id: str, regions: List[str]):
        self.master_id = master_id
        self.regions = regions
        self.logger = logging.getLogger(f"CommunityMaster-{master_id}")

    def _identify_pillar(self, item_name: str, lang: str = "en") -> str:
        """Categorizes a request, aware of both English and Local keywords."""
        clean_item = item_name.strip().lower()
        
        # 1. Check English Standards
        for pillar, keywords in SPECIFIC_HELP_TAGS.items():
            if any(k.lower() in clean_item for k in keywords):
                return pillar
        
        # 2. Check if the input IS a translated pillar name (e.g. "शिक्षा")
        if lang in CITIZEN_TRANSLATIONS:
            for pillar, local_name in CITIZEN_TRANSLATIONS[lang].items():
                if local_name.split('(')[0].strip().lower() in clean_item:
                    return pillar
                    
        return "GENERAL_AID"

    async def match_citizen_need(
        self,
        request: DisasterRequest,
        ngo_profiles: List[NGOProfile],
        ngo_locations: dict,
        lang: str = "en"  # Inherited from CitizenUser.preferred_language
    ) -> List[DispatchOrder]:
        """
        Multilingual Matching:
        - Understands the need (local or English).
        - Matches to NGO Profile (English).
        - Returns localized context for the Citizen Dashboard.
        """
        if request.category != RequestCategory.COMMUNITY:
            return []

        # Categorize the need using the dual-language lookup
        request_pillar = self._identify_pillar(request.item_type, lang)
        
        # Localized Pillar Name for the log/dashboard
        display_pillar = CITIZEN_TRANSLATIONS.get(lang, {}).get(request_pillar, request_pillar)
        self.logger.info(f"CITIZEN MATCH [{lang}]: '{request.item_type}' -> '{display_pillar}'")

        matches = []
        for profile in ngo_profiles:
            # Expertise match (NGO Profiles are in English)
            expertise_match = any(
                request_pillar.lower() in sector.lower() or 
                request.item_type.lower() in sector.lower()
                for sector in profile.sectors
            )
            
            if not expertise_match:
                continue

            loc = ngo_locations.get(profile.ngo_id)
            if not loc: continue

            dist = haversine(
                request.location_gps.lat, request.location_gps.lng,
                loc["lat"], loc["lng"]
            )
            
            score = 1000 / (dist + 1)
            if profile.region == request.region:
                score += 500
            
            matches.append((score, dist, profile))

        if not matches:
            return []

        matches.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, dist, profile in matches[:5]:
            # The NGO sees 'School Books' (English), but the Citizen sees the localized Pillar
            results.append(DispatchOrder(
                order_id=f"KND-{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                ngo_id=profile.ngo_id,
                ngo_b_phone="HIDDEN",
                ngo_b_email="HIDDEN",
                items=[OrderItem(item=request.item_type, qty=request.quantity_needed)],
                status="COMMUNITY_AWAITING_NGO_RESPONSE"
            ))

        return results
