"""
THE INDIA GROUND-LEVEL STANDARDS (V2)
=====================================
Standardizing non-perishable aid and local trust-based support.
"""

# 1. GROUND-LEVEL NGO TYPES
NGO_TYPES = [
    "Local Registered Trust (Mandal/Samiti)",
    "Scholarship & Education Foundation",
    "Medical Relief & Ambulance Trust",
    "Neighborhood Volunteer Collective",
    "Corporate CSR Disaster Wing"
]

# 2. THE SECTORS OF SERVICE
HELP_SECTORS = [
    "Education & Stationery",
    "Medical & First-Aid",
    "Non-Perishable Ration Kits",
    "Disaster Recovery & Tools",
    "WASH (Water & Hygiene)"
]

# 3. GROUND-LEVEL HELP TAGS (Focus on Non-Perishables & Long-Term Support)
SPECIFIC_HELP_TAGS = {
    "EDUCATION": ["Scholarships", "School Books", "Stationery", "Uniforms", "Exam Fees"],
    "RATION_KITS": ["Rice", "Dal/Pulses", "Wheat/Atta", "Cooking Oil", "Biscuits", "Milk Powder"],
    "MEDICAL": ["Oxygen Cylinders", "Emergency Meds", "Ambulance", "Wheelchairs", "First Aid"],
    "SHELTER_STUFF": ["Tents", "Blankets", "Plastic Sheets", "Clothes", "Utensils"],
    "ACCIDENT_SUPPORT": ["Immediate Cash Aid", "Emergency Transport", "Legal Help"],
    "RECOVERY": ["Home Repair Tools", "Small Business Grants", "Seed Kits", "Debris Removal"],
    "WASH": ["Clean Drinking Water", "Soap & Sanitizer", "Sanitary Pads", "Buckets/Mugs"]
}

# 4. CITIZEN UI TRANSLATIONS (For 'English Core, Local Face' Strategy)
CITIZEN_TRANSLATIONS = {
    "hi": {  # Hindi
        "EDUCATION": "शिक्षा और स्टेशनरी (Education)",
        "RATION_KITS": "सूखा राशन किट (Ration Kits)",
        "MEDICAL": "चिकित्सा और प्राथमिक उपचार (Medical)",
        "SHELTER_STUFF": "आवास और कपड़े (Shelter)",
        "ACCIDENT_SUPPORT": "आकस्मिक सहायता (Accident Support)",
        "RECOVERY": "पुनर्प्राप्ति और उपकरण (Recovery)",
        "WASH": "स्वच्छता और पानी (WASH)",
        "GENERAL_AID": "सामान्य सहायता (General Help)"
    },
    "mr": {  # Marathi
        "EDUCATION": "शिक्षण आणि स्टेशनरी (Education)",
        "RATION_KITS": "कोरडा शिधा किट (Ration Kits)",
        "MEDICAL": "वैद्यकीय मदत (Medical)",
        "SHELTER_STUFF": "निवारा आणि कपडे (Shelter)",
        "ACCIDENT_SUPPORT": "अपघात मदत (Accident Support)",
        "RECOVERY": "पुनर्प्राप्ती आणि साधने (Recovery)",
        "WASH": "स्वच्छता आणि पाणी (WASH)",
        "GENERAL_AID": "सामान्य मदत (General Help)"
    }
}
