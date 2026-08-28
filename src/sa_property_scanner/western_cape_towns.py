"""Comprehensive list of Western Cape towns and localities.

Used for location-based filtering to ensure only Western Cape properties are returned.
"""

# Major towns and localities across all Western Cape regions
WESTERN_CAPE_TOWNS: set[str] = {
    # Cape Town Metro
    "atlantis",
    "belhar",
    "bellville",
    "blouberg",
    "bloubergstrand",
    "brackenfell",
    "cape town",
    "constantia",
    "durbanville",
    "eelsteen river",
    "fish hoek",
    "goodwood",
    "grassy park",
    "hout bay",
    "khayelitsha",
    "kraaifontein",
    "lansdowne",
    "lentegeur",
    "mafikeng",
    "melkbosstrand",
    "mitchells plain",
    "muizenberg",
    "newlands",
    "observatory",
    "parow",
    "peninsula",
    "pinelands",
    "plumstead",
    "rondebosch",
    "sea point",
    "simons town",
    "somerset west",
    "strand",
    "table view",
    "tokai",
    "wetton",
    "woodstock",
    "wynberg",
    # Winelands
    "franschhoek",
    "paarl",
    "robertson",
    "stellenbosch",
    "tulbagh",
    "wellington",
    # Overberg
    "arniston",
    "bettys bay",
    "bredasdorp",
    "caledon",
    "gansbaai",
    "grabouw",
    "greyton",
    "hermanus",
    "kleinmond",
    "napier",
    "pringle bay",
    "stanford",
    "struisbaai",
    "swellendam",
    "villiersdorp",
    # Garden Route
    "george",
    "great brak river",
    "hartenbos",
    "herolds bay",
    "knysna",
    "mossel bay",
    "oudtshoorn",
    "plettenberg bay",
    "sedgefield",
    "wilderness",
    # West Coast
    "darling",
    "langebaan",
    "malmesbury",
    "moorreesburg",
    "paternoster",
    "piketberg",
    "saldanha",
    "velddrif",
    "vredenburg",
    "vredendal",
    "yzerfontein",
    # Swartland
    "aurora",
    "koringberg",
    "rietpoort",
    # Karoo / Central
    "beaufort west",
    "laingsburg",
    "matjiesfontein",
    "prince albert",
    # Cederberg / Namaqualite
    "cederberg",
    "citrusdal",
    "clanwilliam",
    "lamberts bay",
    "nuwerus",
    # Breede Valley
    "ashton",
    "bonnievale",
    "ceres",
    "de doorns",
    "mcgregor",
    "montagu",
    "rawsonville",
    "robertson",
    "touws river",
    "worcester",
    # Cape Agulhas
    "bredasdorp",
    "l'agulhas",
    "napier",
    "struisbaai",
    "suiderstrand",
    # Hessequa
    "albertinia",
    "gouritsmond",
    "heidelberg",
    "jongensfontein",
    "riversdale",
    "stilbaai",
    "still bay",
    # Kannaland
    "calitzdorp",
    "ladismith",
    "vanwyksdorp",
    # Other
    "dysselsdorp",
    "herolds bay",
    "keurboomstrand",
    "natures valley",
    "noordhoek",
    "onrus",
    "plettenberg bay",
    "sedgefield",
    "witsand",
}

# Province names and abbreviations that indicate Western Cape
WESTERN_CAPE_IDENTIFIERS: set[str] = {
    "western cape",
    "w.cape",
    "wc",
    "westkaap",
    "west coast",
    "overberg",
    "winelands",
    "garden route",
    "karoo",
    "breede valley",
    "cederberg",
    "swartland",
}


def is_western_cape_location(location: str | None) -> bool:
    """Check if a location string indicates a Western Cape property.

    Args:
        location: The location string from a listing (e.g., "House in Stellenbosch").

    Returns:
        True if the location appears to be in the Western Cape.
    """
    if not location:
        return True  # Allow listings without explicit location (conservative)

    location_lower = location.lower()

    # Check for explicit Western Cape identifiers
    for identifier in WESTERN_CAPE_IDENTIFIERS:
        if identifier in location_lower:
            return True

    # Check for specific town names
    for town in WESTERN_CAPE_TOWNS:
        if town in location_lower:
            return True

    # Check for common Western Cape postal code prefixes (8000-8099 for Cape Town metro)
    # This is a heuristic and may not be present in all listings
    import re

    if re.search(r"\b8[0-1]\d{3}\b", location):
        return True

    return False
