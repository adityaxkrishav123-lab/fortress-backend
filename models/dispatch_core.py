from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
from .shared import GPSLocation, OrderItem

class InventoryItem(BaseModel):
    """INTERNAL ONLY: The private stock of an NGO."""
    item_name: str
    quantity_available: int
    quantity_committed: int = 0
    ngo_id: str
    region: str
    location_gps: GPSLocation
    verification_tier: int = 1
    expiry_date: Optional[datetime] = None
    contact_phone: str
    contact_email: str
    has_internal_transport: bool = False
    is_locked: bool = False
    lock_timestamp: Optional[datetime] = None
    lock_request_id: Optional[str] = None

class VehicleType(str, Enum):
    TRUCK = "truck"
    CAR = "car"
    BIKE = "bike"

class Volunteer(BaseModel):
    """INTERNAL ONLY: The private volunteer pool."""
    volunteer_id: str
    name: str
    profession: str
    skills: List[str] = []
    vehicle_type: VehicleType
    region: str
    location_gps: GPSLocation
    is_available: bool = True
    current_order_id: Optional[str] = None

class DispatchOrder(BaseModel):
    """INTERNAL ONLY: Tracking for active dispatches."""
    order_id: str
    request_id: str
    ngo_id: str
    volunteer_id: Optional[str] = None
    ngo_b_phone: str
    ngo_b_email: str
    items: List[OrderItem]
    status: str = "AWAITING_CONFIRMATION" 
    contact_shared: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    estimated_arrival: Optional[datetime] = None
