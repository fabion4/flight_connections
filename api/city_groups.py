CITY_GROUPS: dict[str, list[str]] = {
    "ROM": ["FCO", "CIA"],
    "RMA": ["FCO", "CIA"],
    "LON": ["LHR", "LGW", "STN", "LTN", "LCY"],
    "MIL": ["MXP", "LIN", "BGY"],
    "PAR": ["CDG", "ORY", "BVA"],
    "NYC": ["JFK", "LGA", "EWR"],
    "CHI": ["ORD", "MDW"],
    "LAX": ["LAX", "BUR", "LGB", "ONT", "SNA"],
    "TYO": ["NRT", "HND"],
    "OSA": ["KIX", "ITM"],
}

# Gruppi metropolitani per il dropdown: un solo entry per area, con il codice canonico
METRO_GROUPS: dict[str, dict] = {
    "RMA": {"label": "Roma — tutti gli aeroporti", "city": "Roma", "country": "Italia", "airports": ["FCO", "CIA"]},
    "LON": {"label": "Londra — tutti gli aeroporti", "city": "London", "country": "United Kingdom", "airports": ["LHR", "LGW", "STN", "LTN", "LCY"]},
    "MIL": {"label": "Milano — tutti gli aeroporti", "city": "Milano", "country": "Italia", "airports": ["MXP", "LIN", "BGY"]},
    "PAR": {"label": "Parigi — tutti gli aeroporti", "city": "Paris", "country": "France", "airports": ["CDG", "ORY", "BVA"]},
    "NYC": {"label": "New York — tutti gli aeroporti", "city": "New York", "country": "United States", "airports": ["JFK", "LGA", "EWR"]},
    "CHI": {"label": "Chicago — tutti gli aeroporti", "city": "Chicago", "country": "United States", "airports": ["ORD", "MDW"]},
    "TYO": {"label": "Tokyo — tutti gli aeroporti", "city": "Tokyo", "country": "Japan", "airports": ["NRT", "HND"]},
    "OSA": {"label": "Osaka — tutti gli aeroporti", "city": "Osaka", "country": "Japan", "airports": ["KIX", "ITM"]},
}

# Indice inverso: IATA aeroporto → codice metro canonico
AIRPORT_TO_METRO: dict[str, str] = {
    iata: metro
    for metro, info in METRO_GROUPS.items()
    for iata in info["airports"]
}

AIRPORT_TO_GROUP: dict[str, list[str]] = {}
for group, iatas in CITY_GROUPS.items():
    AIRPORT_TO_GROUP[group] = iatas
    for iata in iatas:
        AIRPORT_TO_GROUP[iata] = iatas

def expand_airport(iata: str) -> list[str]:
    """Dato un codice IATA o metro, restituisce tutti gli aeroporti dell'area metropolitana."""
    return AIRPORT_TO_GROUP.get(iata.upper(), [iata])
