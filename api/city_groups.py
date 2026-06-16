CITY_GROUPS: dict[str, list[str]] = {
    "ROM": ["FCO", "CIA"],
    "LON": ["LHR", "LGW", "STN", "LTN", "LCY"],
    "MIL": ["MXP", "LIN", "BGY"],
    "PAR": ["CDG", "ORY", "BVA"],
    "NYC": ["JFK", "LGA", "EWR"],
    "CHI": ["ORD", "MDW"],
    "LAX": ["LAX", "BUR", "LGB", "ONT", "SNA"],
    "TYO": ["NRT", "HND"],
    "OSA": ["KIX", "ITM"],
}

AIRPORT_TO_GROUP: dict[str, list[str]] = {}

for group, iatas in CITY_GROUPS.items():
    AIRPORT_TO_GROUP[group] = iatas
    for iata in iatas:
        AIRPORT_TO_GROUP[iata] = iatas

def expand_airport(iata: str) -> list[str]:
    """Dato un codice IATA, restituisce tutti gli aeroporti della stessa area metropolitana."""
    return AIRPORT_TO_GROUP.get(iata.upper(), [iata])
