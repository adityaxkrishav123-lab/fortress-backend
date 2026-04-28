import logging
import math
import uuid
from datetime import datetime
from typing import List, Optional
from models.dispatch_models import DisasterRequest, DispatchOrder, RequestCategory, NGOProfile

class CommunityMaster:
    """
    AGENT 5: The 1:50 Philanthropist.
    High-efficiency AI bridging 50 regions for citizen-level needs.
    """
    def __init__(self, master_id: str, regions: List[str]):
        self.master_id = master_id
        self.regions = regions # 50 Regions
        self.logger = logging.getLogger(f"CommunityMaster-{master_id}")

    def _haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def match_citizen_need(self, request: DisasterRequest, ngo_profiles: List[NGOProfile], ngo_locations: dict) -> List[DispatchOrder]:
        """
        Scans 50 regions to find the perfect specialized NGO for a citizen.
        """
        if request.category != RequestCategory.COMMUNITY:
            return []

        matches = []
        for profile in ngo_profiles:
            # Check if NGO is within our 50-region master zone
            # (Assuming the locations dict has regional data or we filter here)
            
            if any(sector.lower() in request.item_type.lower() for sector in profile.sectors):
                loc = ngo_locations.get(profile.ngo_id)
                if not loc: continue
                
                dist = self._haversine(
                    request.location_gps["lat"], request.location_gps["lng"],
                    loc["lat"], loc["lng"]
                )
                matches.append((dist, profile))
        
        matches.sort(key=lambda x: x[0])
        
        results = []
        for dist, profile in matches[:5]: # More options for community requests
            self.logger.info(f"KINDNESS BRIDGE: NGO {profile.ngo_name} matched in Master Zone {self.master_id}")
            
            results.append(DispatchOrder(
                order_id=f"KND-{uuid.uuid4().hex[:8]}",
                request_id=request.request_id,
                ngo_id=profile.ngo_id,
                ngo_b_phone="HIDDEN",
                ngo_b_email="HIDDEN",
                items=[{"item": request.item_type, "qty": request.quantity_needed}],
                status="COMMUNITY_AWAITING_NGO_RESPONSE"
            ))
            
        return results
