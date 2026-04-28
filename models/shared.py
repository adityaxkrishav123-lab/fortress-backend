from pydantic import BaseModel, Field
from enum import Enum

class GPSLocation(BaseModel):
    """STRICT GPS VALIDATION: Used for static proximity ranking."""
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    ESSENTIAL = "essential"
    SUPPORT = "support"

class RequestCategory(str, Enum):
    SUPPLIES = "supplies"
    MANPOWER = "manpower"
    COMMUNITY = "community"

class CitizenRequestStatus(str, Enum):
    AWAITING_NGO = "awaiting_ngo"
    NGO_ACCEPTED = "ngo_accepted"
    STALLED = "stalled"
    COMPLETED = "completed"

class OrderItem(BaseModel):
    item: str
    qty: int = Field(..., gt=0)
