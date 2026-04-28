from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .shared import GPSLocation, UrgencyLevel, RequestCategory, CitizenRequestStatus

class CitizenUser(BaseModel):
    user_id: str
    name: str
    email: str
    phone: str
    home_region: str
    preferred_language: str = "en" # "en", "hi", "mr"
    account_created: datetime = Field(default_factory=datetime.now)
    last_fire_time: Optional[datetime] = None  # Tracks 2h cooldown for Firing NGOs

class DisasterRequest(BaseModel):
    """
    A Citizen's Request for Help.
    Can be used by both the NGO Dispatch (for high-volume) and Citizen AI (for local help).
    """
    request_id: str
    citizen_id: str
    category: RequestCategory = RequestCategory.SUPPLIES
    item_type: str
    quantity_needed: int = Field(..., gt=0)
    severity: int = Field(ge=1, le=10)
    people_affected: int = 1
    urgency: UrgencyLevel
    location_gps: GPSLocation
    region: str
    status: CitizenRequestStatus = CitizenRequestStatus.AWAITING_NGO
    ngo_id: Optional[str] = None  # The NGO that accepted the request
    citizen_confirmed: bool = False
    ngo_confirmed: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    signed_undertaking_url: Optional[str] = None
    ngo_accepted_at: Optional[datetime] = None  # Tracks the 30m Initial Lock
