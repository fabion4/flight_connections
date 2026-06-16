# Specifica: Refactor API-Agnostic + Layover Multi-Giorno Duffel

- **ID Backlog**: B-01
- **Branch**: `feature/api-agnostic-router`
- **Stato**: da iniziare
- **Dipendenze**: nessuna
- **Sblocca**: B-02 (city groups), B-03 (Duffel destinations), B-04 (2 scali)

---

## Obiettivo

Estrarre la logica di routing (intersezione aeroporti intermedi, combinazione tratte, filtraggio layover) dai moduli provider-specifici in un layer condiviso, così che Ryanair e Duffel condividano lo stesso algoritmo. Prerequisito per estendere Duffel con layover multi-giorno e scali cross-airport.

**Problema attuale**: la logica di combinazione tratte esiste solo in `flight_search.py` (Ryanair). `duffel_search.py` delega la costruzione delle connessioni all'API Duffel, che restituisce solo itinerari standard senza layover multi-giorno. Il parametro `max_layover_days` è sostanzialmente inerte sul ramo Duffel.

---

## Struttura target

```
api/
├── providers/
│   ├── __init__.py
│   ├── base.py           # Protocol/ABC con le due primitive
│   ├── ryanair.py        # Migrato da flight_search.py
│   └── duffel.py         # Migrato da duffel_search.py
├── router.py             # Algoritmo di routing condiviso
├── city_groups.py        # Mappa città → lista IATA
├── models.py             # FlightLeg, Connection (dataclass)
├── utils.py              # Invariato
└── index.py              # Aggiornato per usare router
```

I file `flight_search.py` e `duffel_search.py` vanno eliminati dopo la migrazione.

---

## Contratto dei provider (`api/providers/base.py`)

```python
from typing import Protocol
from api.models import FlightLeg

@runtime_checkable
class FlightProvider(Protocol):
    def get_destinations(self, airport_code: str) -> list[str]:
        """Restituisce i codici IATA raggiungibili da airport_code."""
        ...

    def get_flights(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        """
        Restituisce i voli diretti da from_code a to_code nella data date_str (YYYY-MM-DD).
        Ogni elemento è un singolo segmento di volo, non una connessione composta.
        """
        ...
```

---

## Schema comune (`api/models.py`)

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FlightLeg:
    from_code: str
    to_code: str
    from_city: str
    to_city: str
    departure: datetime
    arrival: datetime
    price: float
    carrier: str
    flight_number: str

@dataclass
class Connection:
    connection_label: str          # "FCO-AMS | AMS-JFK"
    first_leg: FlightLeg
    second_leg: FlightLeg | None   # None = volo diretto
    layover_h: float
    total_duration_h: float
    total_price: float

    def to_dict(self) -> dict:
        """Serializza nel formato colonne atteso dal frontend (invariato rispetto ad oggi)."""
        ...
```

`to_dict()` deve produrre esattamente le stesse chiavi che il frontend si aspetta oggi:

```
Connection, First Leg Departure, First Leg Arrival, First Leg Carrier, First Leg Flight Number,
Second Leg Departure, Second Leg Arrival, Second Leg Carrier, Second Leg Flight Number,
Layover (h), Total Duration (h), Total Price (€),
First Leg Origin City, First Leg Destination City, Second Leg Origin City, Second Leg Destination City
```

Per i voli diretti, i campi `Second Leg *` devono essere `None` (non la stringa `"-"`).

---

## Mappa città → aeroporti (`api/city_groups.py`)

```python
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
    # espandere con le principali aree metropolitane
}

AIRPORT_TO_GROUP: dict[str, list[str]] = {}  # costruito a runtime da CITY_GROUPS

def expand_airport(iata: str) -> list[str]:
    """Dato un codice IATA, restituisce tutti gli aeroporti della stessa area metropolitana."""
    return AIRPORT_TO_GROUP.get(iata, [iata])
```

---

## Router condiviso (`api/router.py`)

```python
def find_connections(
    provider: FlightProvider,
    start_airport: str,
    end_airport: str,
    dates: list[str],           # lista date YYYY-MM-DD già calcolata dal chiamante
    max_layover_h: float,
    use_city_groups: bool = True,
) -> list[Connection]:
```

**Algoritmo**:

1. Espandi `start_airport` e `end_airport` con `expand_airport()` se `use_city_groups=True`
2. Calcola destinazioni raggiungibili da tutti gli aeroporti di partenza espansi → `reachable_from_start`
3. Calcola origini che raggiungono tutti gli aeroporti di arrivo espansi → `reachable_to_end`
4. Intersezione → `via_candidates`
5. Per ogni `via_airport` in `via_candidates`:
   - Per ogni `date` in `dates`:
     - Chiama `provider.get_flights(start_expanded, via_airport, date)` → `first_legs`
     - Chiama `provider.get_flights(via_airport, end_expanded, date)` → `second_legs`
   - `product(first_legs, second_legs)` → filtra per `0 < layover_h <= max_layover_h`
6. Aggiungi voli diretti: `provider.get_flights(start_expanded, end_expanded, date)` per ogni `date`
7. Restituisci lista `Connection` ordinata per `total_price`

Il router non contiene logica HTTP, rate limiting o threading. Quella logica resta nei provider.

---

## Migrazione provider Ryanair (`api/providers/ryanair.py`)

- `get_destinations(airport_code)` ← corpo di `get_available_destinations()`
- `get_flights(from_code, to_code, date_str)` ← corpo di `get_flight_data()`, restituisce `list[FlightLeg]`
- `get_airports()` e `airport_lookup` rimangono interni (usati per popolare `from_city`/`to_city`)
- La generazione dei mesi dal range di date si sposta in `index.py` prima di chiamare il router
- `find_best_routes()` viene eliminata

---

## Migrazione provider Duffel (`api/providers/duffel.py`)

- `get_destinations(airport_code)` → **da implementare**: chiama Duffel Places API o usa lista statica ~150 hub globali come fallback
- `get_flights(from_code, to_code, date_str)` ← corpo di `get_flight_data_duffel()`, ma restituisce **solo segmenti singoli** (`FlightLeg`). I 2-segment offers di Duffel vanno decomposed: primo e secondo segmento diventano due `FlightLeg` separati, il prezzo totale viene diviso proporzionalmente alla durata. Il router li ricombinerà.
- Rate limiting e threading rimangono nel provider
- `find_best_routes_duffel()` viene eliminata

---

## Aggiornamento `index.py`

```python
from api.providers.ryanair import RyanairProvider
from api.providers.duffel import DuffelProvider
from api.router import find_connections

# Nel body di search_flights:
dates_ryanair = _generate_monthly_dates(start_date, end_date)
dates_duffel  = _generate_daily_dates(start_date, end_date)

connections_ryanair = find_connections(RyanairProvider(), start, end, dates_ryanair, max_layover_days * 24)
connections_duffel  = find_connections(DuffelProvider(),  start, end, dates_duffel,  max_layover_days * 24)

records = [c.to_dict() for c in sorted(connections_ryanair + connections_duffel, key=lambda c: c.total_price)]
```

---

## Test (`tests/`)

### Struttura

```
tests/
├── conftest.py
├── test_models.py
├── test_city_groups.py
├── test_router.py
├── test_provider_ryanair.py
└── test_provider_duffel.py
```

### Test obbligatori per il merge

**`test_router.py`** — provider mockato deterministico, zero HTTP:

| Test | Verifica |
|------|----------|
| `test_direct_flight_found` | volo diretto restituito se esiste |
| `test_one_stop_connection` | connessione con scalo valida combinata correttamente |
| `test_layover_too_long_excluded` | scalo oltre max_layover_h non compare |
| `test_layover_negative_excluded` | f2.departure < f1.arrival escluso |
| `test_city_group_cross_airport` | FCO→AMS + CIA→AMS entrambi trovati con start=FCO e city_groups=True |
| `test_city_group_disabled` | con `use_city_groups=False` solo FCO usato |
| `test_price_ordering` | risultati ordinati per total_price crescente |
| `test_empty_intersection` | nessun via_airport comune → solo diretti o lista vuota |

**`test_models.py`**:

| Test | Verifica |
|------|----------|
| `test_to_dict_direct_flight` | chiavi frontend invariate per volo diretto |
| `test_to_dict_one_stop` | chiavi frontend invariate per volo con scalo |
| `test_to_dict_second_leg_none` | campi seconda tratta valorizzati a `None` |

**`test_city_groups.py`**:

| Test | Verifica |
|------|----------|
| `test_expand_known_airport` | FCO → [FCO, CIA] |
| `test_expand_unknown_airport` | XYZ → [XYZ] (passthrough) |
| `test_no_duplicates_in_group` | nessun IATA duplicato nei gruppi |
| `test_inverse_index_complete` | ogni IATA in CITY_GROUPS è nel reverse index |

**`test_provider_ryanair.py`** — HTTP mockato con `responses` library:

| Test | Verifica |
|------|----------|
| `test_get_destinations_returns_list` | lista di IATA stringhe |
| `test_get_flights_returns_flight_legs` | tipo `FlightLeg`, campi non None |
| `test_get_flights_empty_on_404` | lista vuota, no eccezione |
| `test_get_flights_parses_dates` | `departure` e `arrival` sono `datetime` |

**`test_provider_duffel.py`** — HTTP mockato con `responses` library:

| Test | Verifica |
|------|----------|
| `test_get_flights_direct` | 1-segment offer → 1 FlightLeg |
| `test_get_flights_2segment_decomposed` | 2-segment offer → 2 FlightLeg separati |
| `test_get_flights_empty_on_no_token` | lista vuota, no eccezione |
| `test_get_flights_retries_on_429` | dopo rate limit ritenta e restituisce risultato |

### Criterio di merge

```
pytest tests/ -v  →  0 failures, 0 errors
```

Il comportamento osservabile dal frontend deve essere identico a `main` per tutti i casi coperti.

---

## Cosa NON va cambiato

- `api/utils.py`
- Logica di streaming in `index.py`
- Schema colonne JSON finale (chiavi identiche a oggi)
- Frontend (`app.js`, `index.html`, `style.css`)

---

## Ordine di esecuzione consigliato

1. `models.py` + `city_groups.py` + test relativi
2. `router.py` con MockProvider + test
3. `providers/ryanair.py` + test provider
4. `providers/duffel.py` + test provider
5. Aggiorna `index.py`
6. Elimina `flight_search.py` e `duffel_search.py`
7. `pytest tests/ -v` tutto verde → PR verso `main`
