"""
auth_gate/catalog.py
====================
THE MASTER CATALOG — Single Source of Truth for:

  1. NGO_CATALOG        → NGO Type (1 choice) + Subtypes (multi-select tags)
                          Used at TWO places:
                          a) NGO Admin Signup   → to define the NGO's identity
                          b) Citizen "Make Request" → to tag what they need
                          The AI Agent MATCHES these two to route Action Cards.

  2. INSTANT_HELP_ITEMS → Flat list of physical product names for the
                          "Gift-in-Kind / Instant Help" section only.

HOW TO ADD MORE (no other file needs to change):
  → New NGO Type    : Add a block to NGO_CATALOG
  → New Subtype     : Add a string to the correct "subtypes" list
  → New Instant Item: Add a string to INSTANT_HELP_ITEMS
"""

from __future__ import annotations


# ===========================================================================
# 1.  NGO CATALOG  (also used as Citizen Request Tag Catalog)
#
#     NGO Signup Rule  : ONE ngo_type (permanent, Admin-changeable via OTP)
#                        ONE OR MORE subtypes (permanent)
#
#     Citizen Request  : Picks ONE type + ONE OR MORE subtypes from this
#                        SAME list. AI Agent finds NGOs whose signup tags match.
# ===========================================================================

NGO_CATALOG: dict[str, dict] = {

    "EDUCATION_ACADEMIC": {
        "label": "Education & Academic Development",
        "subtypes": [
            "PRIMARY_EDUCATION",        # School children, basic literacy, dropouts
            "HIGHER_EDUCATION",         # College, Engineering, Medical, GATE/ESE
            "SPECIAL_NEEDS_EDUCATION",  # Differently-abled infrastructure & teaching
            "VOCATIONAL_SKILL",         # Trade skills, coding bootcamps, workshops
        ],
    },

    "FINANCIAL_GRANTS": {
        "label": "Financial Assistance & Grants",
        "subtypes": [
            "EDUCATIONAL_SCHOLARSHIPS",  # Tuition, hostels, exam fees
            "MEDICAL_CROWDFUNDING",      # Surgeries, chronic illness treatments
            "DISASTER_CRISIS_FUNDS",     # Cash relief for disasters/tragedies
        ],
    },

    "HEALTHCARE_MEDICAL": {
        "label": "Healthcare & Medical Relief",
        "subtypes": [
            "BLOOD_ORGAN_STEMCELL_BANK",  # Blood packets, platelets, organ matching
            "DISEASE_SPECIFIC_CARE",      # Cancer, HIV/AIDS, Dialysis
            "MENTAL_HEALTH_COUNSELING",   # Free therapy, psychiatry, suicide prevention
            "MOBILITY_DISABILITY_AID",    # Prosthetics, wheelchairs, physical therapy
            "MEDICAL_EQUIPMENT",          # Oxygen tanks, dialysis machines
            "MEDICINAL_ASSISTANCE",       # Prescription & OTC drug supply
        ],
    },

    "SUSTENANCE_RELIEF": {
        "label": "Sustenance (Poverty & Disaster Relief Camps)",
        "subtypes": [
            "FOOD_SECURITY",        # Dry rations for disaster-affected people
            "SHELTER_HOUSING",      # Orphanages, old-age homes, shelters
            "CLOTHING_ESSENTIALS",  # Clothes, blankets, hygiene kits
        ],
    },

    # -----------------------------------------------------------------------
    # ADD NEW NGO TYPES BELOW THIS LINE
    # "YOUR_TYPE_KEY": {
    #     "label": "Human-readable name",
    #     "subtypes": ["SUBTYPE_KEY_1", "SUBTYPE_KEY_2"],
    # },
    # -----------------------------------------------------------------------
}


# ===========================================================================
# 2.  INSTANT HELP / GIFT-IN-KIND ITEMS
#
#     A flat list of physical product names shown in the "Instant Help"
#     section of the Citizen app. No categories, no sub-tags — just a clean
#     scrollable list. The Citizen picks items and sends directly.
#     The AI Agent reads these product names to find matching NGO inventory.
# ===========================================================================

INSTANT_HELP_ITEMS: list[str] = [
    # Blood
    "Blood Bag - A+",
    "Blood Bag - A-",
    "Blood Bag - B+",
    "Blood Bag - B-",
    "Blood Bag - O+",
    "Blood Bag - O-",
    "Blood Bag - AB+",
    "Blood Bag - AB-",

    # Medical Equipment
    "Oxygen Cylinder",
    "Dialysis Machine (Session)",
    "Wheelchair",
    "Crutches",
    "Hearing Aid",

    # Relief Goods
    "Ration Kit",
    "Cooked Food Packet",
    "Baby Formula",
    "Blanket",
    "Hygiene Kit",
    "Clothing Bundle",

    # -----------------------------------------------------------------------
    # ADD NEW INSTANT HELP ITEMS BELOW THIS LINE (one string per item)
    # -----------------------------------------------------------------------
]


# ===========================================================================
# HELPER FUNCTIONS
# Used by: Auth Gate validators, AI Dispatch Agents, Mailbox system
# ===========================================================================

def get_valid_ngo_types() -> list[str]:
    """All valid NGO type keys — for the NGO signup AND Citizen request dropdown."""
    return list(NGO_CATALOG.keys())


def get_subtypes_for_type(ngo_type: str) -> list[str]:
    """All valid subtype keys for a given type (used by both NGO and Citizen)."""
    entry = NGO_CATALOG.get(ngo_type)
    return entry["subtypes"] if entry else []


def is_valid_ngo_type(ngo_type: str) -> bool:
    return ngo_type in NGO_CATALOG


def is_valid_subtype(ngo_type: str, subtype: str) -> bool:
    return subtype in get_subtypes_for_type(ngo_type)


def is_valid_instant_item(item: str) -> bool:
    return item in INSTANT_HELP_ITEMS


# ===========================================================================
# 3.  VOLUNTEER PROFESSION TAG CATALOG
#
#     Volunteers select 1 to 3 tags at signup (permanent).
#     manpower_agent uses these to find the right volunteer for an NGO request.
#     Admin can change via OTP verification only.
# ===========================================================================

VOLUNTEER_PROFESSION_TAGS: dict[str, list[str]] = {
    "MEDICAL": [
        "Doctor",
        "Nurse",
        "Paramedic",
        "Blood Donor",
        "Pharmacist",
    ],
    "TECHNICAL": [
        "Engineer",
        "Electrician",
        "Plumber",
        "Heavy Vehicle Driver",
        "IT Support",
    ],
    "RESCUE": [
        "Firefighter",
        "Flood Rescue Specialist",
        "Search & Rescue Operative",
        "Mountain Rescue Specialist",
    ],
    "SUPPORT": [
        "Cook / Food Prep",
        "Translator / Interpreter",
        "Counsellor",
        "Teacher / Educator",
        "Logistics Coordinator",
    ],
    "GENERAL": [
        "Socially Active Person",   # Community outreach, awareness drives
        "Labour / Manual Work",
        "Packing & Distribution",
        "Security",
    ],
}

# Flat list for quick lookup
_ALL_PROFESSION_TAGS: list[str] = [
    tag for tags in VOLUNTEER_PROFESSION_TAGS.values() for tag in tags
]


def get_all_profession_tags() -> list[str]:
    """Flat list of every valid profession tag — for signup dropdown."""
    return _ALL_PROFESSION_TAGS


def is_valid_profession_tag(tag: str) -> bool:
    return tag in _ALL_PROFESSION_TAGS


def get_profession_group(tag: str) -> str | None:
    """Returns the group key (e.g. 'MEDICAL') for a given tag, or None."""
    for group, tags in VOLUNTEER_PROFESSION_TAGS.items():
        if tag in tags:
            return group
    return None
