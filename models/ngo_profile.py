from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from standards import NGO_TYPES, HELP_SECTORS

class NGOProfile(BaseModel):
    """
    The Public Face of an NGO.
    Matches against 'standards.py' to ensure ground-level Indian NGO compatibility.
    """
    ngo_id: str
    ngo_name: str
    ngo_type: str      # E.g., "Local Registered Trust"
    sectors: List[str] # E.g., ["Education & Stationery", "Ration Kits"]
    region: str        # E.g., "MUMBAI"
    trustees: List[str]
    description: str
    verified_since: datetime = Field(default_factory=datetime.now)
    # trust_score: int = 0  # Future: Add reputation ranking here
