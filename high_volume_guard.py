import logging
from models.dispatch_models import DisasterRequest, InventoryItem, UrgencyLevel

logger = logging.getLogger("HighVolumeGuard")

HIGH_VOLUME_THRESHOLD = 500  # Requests above this require extra verification

def check_volume_clearance(request: DisasterRequest, ngo: InventoryItem) -> bool:
    """
    STRICT SECURITY LAYER:
    Checks if the NGO and the Request meet high-volume safety standards.
    """
    if request.quantity_needed < HIGH_VOLUME_THRESHOLD:
        return True  # Standard volume — always cleared

    # 1. Verification Check
    if ngo.verification_tier < 2:
        if request.urgency != UrgencyLevel.CRITICAL:
            logger.warning(f"SECURITY BLOCK: Tier-1 NGO {ngo.ngo_id} attempted to handle {request.quantity_needed} units.")
            return False
        else:
            logger.warning(f"URGENCY OVERRIDE: Allowing Tier-1 NGO due to CRITICAL status.")

    # 2. Logistics Undertaking Check
    if not request.signed_undertaking_url:
        logger.error(f"DOCUMENTATION MISSING: Request {request.request_id} needs a Signed Undertaking Form for volume >500.")
        return False
        
    return True
