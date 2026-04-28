"""
region_config.py — REGION TOPOLOGY (Full Rewrite v2)
======================================================
Single Source of Truth for ALL geographic routing in the system.

HIERARCHY (small → large):
  Taluka     → Volunteer search boundary      (ManpowerAgent)
  Cluster    → NGO-to-NGO district boundary   (RegionalAgent / EscalationAgent)
  Zone       → Citizen search boundary        (CitizenAgent — up to 10 sub-regions)

RULES:
  ✅ Every region belongs to EXACTLY ONE Cluster.
  ✅ Every region belongs to EXACTLY ONE Zone.
  ✅ No region appears in two clusters or two zones.
  ✅ CLUSTERS cover ALL regions — no CLUSTER_UNKNOWN fallback.
  ✅ BIG_CITIES only contains cities that exist in ALL_REGIONS.

HOW TO ADD A NEW REGION:
  1. Add to ALL_REGIONS.
  2. Add to the correct CLUSTER.
  3. That's it — Zone is auto-derived from Cluster.
"""

from __future__ import annotations

# ===========================================================================
# ALL VALID REGIONS — Canonical names, always UPPERCASE
# ===========================================================================
ALL_REGIONS: list[str] = [
    # Maharashtra (15)
    "MUMBAI", "PUNE", "NASHIK", "THANE", "RAIGAD",
    "AURANGABAD", "KOLHAPUR", "SOLAPUR", "NAGPUR", "AMRAVATI",
    "NANDED", "JALGAON", "DHULE", "SANGLI", "SATARA",

    # Delhi-NCR + Punjab + Haryana Core (15)
    "DELHI", "GURGAON", "NOIDA", "FARIDABAD", "GHAZIABAD",
    "MEERUT", "SONIPAT", "ROHTAK", "PANIPAT", "KARNAL",
    "AMBALA", "LUDHIANA", "AMRITSAR", "CHANDIGARH", "JALANDHAR",

    # Gujarat (15)
    "AHMEDABAD", "SURAT", "VADODARA", "RAJKOT", "GANDHINAGAR",
    "BHAVNAGAR", "JAMNAGAR", "JUNAGADH", "ANAND", "MEHSANA",
    "PATAN", "BOTAD", "MORBI", "SURENDRANAGAR", "BHARUCH",

    # Karnataka (15)
    "BANGALORE", "MYSORE", "HUBLI", "MANGALORE", "BELGAUM",
    "DAVANGERE", "SHIMOGA", "TUMKUR", "RAICHUR", "BELLARY",
    "BIJAPUR", "GULBARGA", "BIDAR", "HASSAN", "MANDYA",

    # Tamil Nadu (15)
    "CHENNAI", "COIMBATORE", "MADURAI", "TRICHY", "SALEM",
    "VELLORE", "ERODE", "TIRUNELVELI", "THOOTHUKUDI", "TIRUPPUR",
    "DINDIGUL", "THANJAVUR", "CUDDALORE", "KANCHIPURAM", "NAMAKKAL",

    # Rajasthan (10)
    "JAIPUR", "JODHPUR", "UDAIPUR", "KOTA", "AJMER",
    "BIKANER", "ALWAR", "BHILWARA", "SIKAR", "BARMER",

    # Goa (2)
    "GOA_PANAJI", "GOA_MARGAO",

    # Madhya Pradesh (10)
    "INDORE", "BHOPAL", "GWALIOR", "JABALPUR", "UJJAIN",
    "SAGAR", "RATLAM", "REWA", "SATNA", "CHHINDWARA",

    # Uttar Pradesh (10)
    "LUCKNOW", "AGRA", "VARANASI", "KANPUR", "ALLAHABAD",
    "GORAKHPUR", "ALIGARH", "BAREILLY", "MORADABAD", "SAHARANPUR",

    # Kerala (10)
    "KOCHI", "THIRUVANANTHAPURAM", "KOZHIKODE", "THRISSUR", "KOLLAM",
    "KANNUR", "PALAKKAD", "ALAPPUZHA", "MALAPPURAM", "KOTTAYAM",

    # Andhra Pradesh (10)
    "VIZAG", "VIJAYAWADA", "TIRUPATI", "GUNTUR", "NELLORE",
    "KURNOOL", "KAKINADA", "RAJAHMUNDRY", "ANANTAPUR", "KADAPA",

    # North Hills — Uttarakhand + HP + J&K (8)
    "DEHRADUN", "HARIDWAR", "ROORKEE", "SHIMLA", "MANALI",
    "JAMMU", "SRINAGAR", "MUSSOORIE",

    # Haryana Extra (3)
    "HISAR", "YAMUNANAGAR", "SIRSA",

    # Bihar (5)
    "PATNA", "GAYA", "MUZAFFARPUR", "BHAGALPUR", "DARBHANGA",
]

# Validate no duplicates in ALL_REGIONS at import time
_all_regions_set = set(ALL_REGIONS)
assert len(_all_regions_set) == len(ALL_REGIONS), \
    f"DUPLICATE regions found in ALL_REGIONS: " \
    f"{[r for r in ALL_REGIONS if ALL_REGIONS.count(r) > 1]}"


# ===========================================================================
# CLUSTERS — District-level boundaries (for NGO-to-NGO + Escalation search)
#
# ✅ EVERY region in ALL_REGIONS must appear in EXACTLY ONE cluster.
# ✅ CLUSTERS now covers all 13 state groups — no "CLUSTER_UNKNOWN" fallback.
# ===========================================================================
CLUSTERS: dict[str, list[str]] = {

    "CLUSTER_MAHARASHTRA": [
        "MUMBAI", "PUNE", "NASHIK", "THANE", "RAIGAD",
        "AURANGABAD", "KOLHAPUR", "SOLAPUR", "NAGPUR", "AMRAVATI",
        "NANDED", "JALGAON", "DHULE", "SANGLI", "SATARA",
    ],

    "CLUSTER_NORTH_INDIA": [                # Delhi-NCR + Punjab + Core Haryana
        "DELHI", "GURGAON", "NOIDA", "FARIDABAD", "GHAZIABAD",
        "MEERUT", "SONIPAT", "ROHTAK", "PANIPAT", "KARNAL",
        "AMBALA", "LUDHIANA", "AMRITSAR", "CHANDIGARH", "JALANDHAR",
    ],

    "CLUSTER_GUJARAT": [
        "AHMEDABAD", "SURAT", "VADODARA", "RAJKOT", "GANDHINAGAR",
        "BHAVNAGAR", "JAMNAGAR", "JUNAGADH", "ANAND", "MEHSANA",
        "PATAN", "BOTAD", "MORBI", "SURENDRANAGAR", "BHARUCH",
    ],

    "CLUSTER_KARNATAKA": [
        "BANGALORE", "MYSORE", "HUBLI", "MANGALORE", "BELGAUM",
        "DAVANGERE", "SHIMOGA", "TUMKUR", "RAICHUR", "BELLARY",
        "BIJAPUR", "GULBARGA", "BIDAR", "HASSAN", "MANDYA",
    ],

    "CLUSTER_TAMILNADU": [
        "CHENNAI", "COIMBATORE", "MADURAI", "TRICHY", "SALEM",
        "VELLORE", "ERODE", "TIRUNELVELI", "THOOTHUKUDI", "TIRUPPUR",
        "DINDIGUL", "THANJAVUR", "CUDDALORE", "KANCHIPURAM", "NAMAKKAL",
    ],

    "CLUSTER_RAJASTHAN": [                  # ✅ All 10 Rajasthan cities — no split
        "JAIPUR", "JODHPUR", "UDAIPUR", "KOTA", "AJMER",
        "BIKANER", "ALWAR", "BHILWARA", "SIKAR", "BARMER",
    ],

    "CLUSTER_GOA": [                        # ✅ Goa isolated — no blending
        "GOA_PANAJI", "GOA_MARGAO",
    ],

    "CLUSTER_MADHYA_PRADESH": [             # ✅ All 10 MP cities — no split
        "INDORE", "BHOPAL", "GWALIOR", "JABALPUR", "UJJAIN",
        "SAGAR", "RATLAM", "REWA", "SATNA", "CHHINDWARA",
    ],

    "CLUSTER_UTTAR_PRADESH": [
        "LUCKNOW", "AGRA", "VARANASI", "KANPUR", "ALLAHABAD",
        "GORAKHPUR", "ALIGARH", "BAREILLY", "MORADABAD", "SAHARANPUR",
    ],

    "CLUSTER_KERALA": [
        "KOCHI", "THIRUVANANTHAPURAM", "KOZHIKODE", "THRISSUR", "KOLLAM",
        "KANNUR", "PALAKKAD", "ALAPPUZHA", "MALAPPURAM", "KOTTAYAM",
    ],

    "CLUSTER_ANDHRA_PRADESH": [
        "VIZAG", "VIJAYAWADA", "TIRUPATI", "GUNTUR", "NELLORE",
        "KURNOOL", "KAKINADA", "RAJAHMUNDRY", "ANANTAPUR", "KADAPA",
    ],

    "CLUSTER_NORTH_HILLS": [                # Uttarakhand + HP + J&K + Extra Haryana
        "DEHRADUN", "HARIDWAR", "ROORKEE", "SHIMLA", "MANALI",
        "JAMMU", "SRINAGAR", "MUSSOORIE",
        "HISAR", "YAMUNANAGAR", "SIRSA",    # Extra Haryana belongs here
    ],

    "CLUSTER_BIHAR": [
        "PATNA", "GAYA", "MUZAFFARPUR", "BHAGALPUR", "DARBHANGA",
    ],
}

# Validate ALL regions are covered by EXACTLY ONE cluster at import time
_cluster_all: list[str] = [r for regions in CLUSTERS.values() for r in regions]
_uncovered = _all_regions_set - set(_cluster_all)
_duplicate_in_clusters = [r for r in _cluster_all if _cluster_all.count(r) > 1]
assert not _uncovered, f"Regions NOT in any cluster: {_uncovered}"
assert not _duplicate_in_clusters, f"Regions in MULTIPLE clusters: {set(_duplicate_in_clusters)}"


# ===========================================================================
# CITIZEN ZONES — State-level boundaries (for CitizenAgent — 1:10 search)
#
# ✅ Auto-derived from CLUSTERS — no manual region lists.
# ✅ Every region is in EXACTLY ONE zone (no duplicates possible).
# ✅ Adding a new cluster automatically adds it to a zone.
# ===========================================================================
CITIZEN_ZONES: dict[str, list[str]] = {

    "ZONE_WEST": (                          # Maharashtra + Gujarat + Rajasthan + Goa + MP
        CLUSTERS["CLUSTER_MAHARASHTRA"] +
        CLUSTERS["CLUSTER_GUJARAT"] +
        CLUSTERS["CLUSTER_RAJASTHAN"] +
        CLUSTERS["CLUSTER_GOA"] +
        CLUSTERS["CLUSTER_MADHYA_PRADESH"]
    ),

    "ZONE_SOUTH": (                         # Karnataka + Tamil Nadu + Kerala + Andhra Pradesh
        CLUSTERS["CLUSTER_KARNATAKA"] +
        CLUSTERS["CLUSTER_TAMILNADU"] +
        CLUSTERS["CLUSTER_KERALA"] +
        CLUSTERS["CLUSTER_ANDHRA_PRADESH"]
    ),

    "ZONE_NORTH": (                         # North India + UP + Bihar + North Hills
        CLUSTERS["CLUSTER_NORTH_INDIA"] +
        CLUSTERS["CLUSTER_UTTAR_PRADESH"] +
        CLUSTERS["CLUSTER_BIHAR"] +
        CLUSTERS["CLUSTER_NORTH_HILLS"]
    ),
}

# Validate ALL regions are in EXACTLY ONE zone at import time
_zone_all: list[str] = [r for regions in CITIZEN_ZONES.values() for r in regions]
_zone_uncovered   = _all_regions_set - set(_zone_all)
_zone_duplicates  = [r for r in _zone_all if _zone_all.count(r) > 1]
assert not _zone_uncovered,  f"Regions NOT in any zone: {_zone_uncovered}"
assert not _zone_duplicates, f"Regions in MULTIPLE zones (CRITICAL BUG): {set(_zone_duplicates)}"

# Log zone sizes for awareness (no strict size enforcement)
import logging as _log
_log.getLogger("region_config").info(
    f"Zone sizes — WEST:{len(CITIZEN_ZONES['ZONE_WEST'])} "
    f"SOUTH:{len(CITIZEN_ZONES['ZONE_SOUTH'])} "
    f"NORTH:{len(CITIZEN_ZONES['ZONE_NORTH'])}"
)

# ===========================================================================
# BIG CITIES — For ManpowerAgent Taluka boundary (1 Taluka only)
# ✅ Only cities that EXIST in ALL_REGIONS
# ===========================================================================
BIG_CITIES: frozenset[str] = frozenset({
    "MUMBAI", "DELHI", "BANGALORE", "CHENNAI", "AHMEDABAD",
    "PUNE", "SURAT", "LUCKNOW", "JAIPUR", "KOCHI",
    "NAGPUR", "INDORE", "BHOPAL", "PATNA", "CHANDIGARH",
    # Note: HYDERABAD and KOLKATA are NOT in our region list — intentionally excluded
})

# Validate BIG_CITIES only contains known regions
_invalid_big = BIG_CITIES - _all_regions_set
assert not _invalid_big, f"BIG_CITIES contains unknown regions: {_invalid_big}"


# ===========================================================================
# LOOKUP FUNCTIONS — Used by all agents
# ===========================================================================

def normalize_region(region: str) -> str:
    """Normalize region name to canonical uppercase form."""
    return region.strip().upper()


def is_valid_region(region: str) -> bool:
    """Gate check — rejects unknown region strings before they enter any agent."""
    return normalize_region(region) in _all_regions_set


def get_cluster_for_region(region: str) -> tuple[str, list[str]]:
    """
    Returns (cluster_id, List[regions]) for the given region.
    Used by: RegionalAgent, EscalationAgent, ManpowerAgent.

    ✅ Every region has a guaranteed cluster — no CLUSTER_UNKNOWN fallback.
    """
    r = normalize_region(region)
    for cluster_id, regions in CLUSTERS.items():
        if r in regions:
            return cluster_id, regions
    # Should never happen thanks to the import-time assertion above
    raise ValueError(f"Region '{r}' not found in any cluster. Add it to region_config.py.")


def get_citizen_zone_for_region(region: str) -> tuple[str, list[str]]:
    """
    Returns (zone_id, List[regions]) for citizen philanthropy routing.
    Used by: CitizenAgent.

    ✅ Every region has a guaranteed zone — no ZONE_UNKNOWN fallback.
    """
    r = normalize_region(region)
    for zone_id, regions in CITIZEN_ZONES.items():
        if r in regions:
            return zone_id, list(regions)
    raise ValueError(f"Region '{r}' not found in any zone. Add it to region_config.py.")


def get_citizen_search_regions(region: str, max_regions: int = 10) -> list[str]:
    """
    For CitizenAgent: returns up to max_regions sub-regions in the
    citizen's zone to search for matching NGOs.
    Puts the citizen's own region FIRST for priority matching.
    """
    r = normalize_region(region)
    _, zone_regions = get_citizen_zone_for_region(r)
    ordered = [r] + [reg for reg in zone_regions if reg != r]
    return ordered[:max_regions]


def get_district_for_region(region: str) -> str:
    """
    For RegionalAgent / EscalationAgent: maps a region to its cluster.
    In this system, CLUSTER = DISTRICT.
    """
    cluster_id, _ = get_cluster_for_region(region)
    return cluster_id


def get_ngo_service_search_regions(district: str) -> list[str]:
    """
    For RegionalAgent: returns all regions in a given cluster/district.
    Used for NGO-to-NGO searches at district level.

    ✅ All 13 clusters are covered — no empty [] return.
    """
    regions = CLUSTERS.get(district, [])
    if not regions:
        _log.getLogger("region_config").warning(
            f"get_ngo_service_search_regions: unknown district '{district}'"
        )
    return regions


def get_escalation_districts(region: str, max_districts: int = 5) -> list[str]:
    """
    For EscalationAgent: returns up to max_districts adjacent clusters
    to expand the search when no match is found locally.
    Origin cluster is always first.
    """
    origin_cluster, _ = get_cluster_for_region(region)
    all_clusters = list(CLUSTERS.keys())

    if origin_cluster in all_clusters:
        idx = all_clusters.index(origin_cluster)
        ordered = (
            [origin_cluster] +
            all_clusters[idx + 1:] +
            all_clusters[:idx]
        )
    else:
        ordered = all_clusters

    return ordered[:max_districts]


def get_volunteer_talukas_for_region(region: str) -> list[str]:
    """
    For ManpowerAgent: returns the Taluka(s) to search for volunteers
    for a given NGO region.

    Rule:
    - Big cities → 1 Taluka (city itself only)
    - Smaller towns → up to 3 adjacent regions within the same cluster
    """
    r = normalize_region(region)

    if r in BIG_CITIES:
        return [r]

    _, cluster_regions = get_cluster_for_region(r)
    if r in cluster_regions:
        idx   = cluster_regions.index(r)
        start = max(0, idx - 1)
        end   = min(len(cluster_regions), idx + 2)
        return cluster_regions[start:end]

    return [r]      # Fallback: just itself


def get_all_monitored_regions() -> list[str]:
    """
    For MonitorAgent: returns all regions to watch.
    """
    return list(ALL_REGIONS)


def get_region_from_gps(latitude: float, longitude: float) -> str | None:
    """
    Translates live GPS coordinates into a Region string (e.g., "MUMBAI").
    TODO: Implement reverse geocoding or spatial bounds checking.
    Currently returns None, forcing fallback to the citizen's registered region.
    """
    # In a full implementation, this would use a spatial index or Google Maps API
    # to find which region the lat/lon falls into.
    return None
