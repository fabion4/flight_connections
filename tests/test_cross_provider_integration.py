"""
Test di integrazione per connessioni cross-provider usando le classi reali
RyanairProvider e DuffelProvider (senza HTTP — cache pre-popolata).

Verifica due scenari:
  HAPPY PATH: Duffel ha in cache i segmenti dell'aeroporto-scalo → mixing funziona.
  GAP: Duffel non ha il segmento rilevante in cache → mixing NON avviene.

Il gap si verifica quando Duffel, nella ricerca OLB→CIA, non ha restituito offerte
via BCN. In quel caso DuffelProvider._cache non contiene ("BCN","CIA",date),
quindi get_flights("BCN","CIA",date) restituisce [] anche se Duffel vola BCN→CIA
come rotta standalone.
"""
from datetime import datetime
from api.models import FlightLeg
from api.providers.ryanair import RyanairProvider
from api.providers.duffel import DuffelProvider
from api.router import find_connections


def _make_ryanair_provider(cache: dict) -> RyanairProvider:
    p = RyanairProvider()
    p._destinations_cache = {
        k: list({leg.to_code for leg in legs})
        for k, legs in cache.items()
        if isinstance(k, str)
    }
    p._flights_cache = {k: v for k, v in cache.items() if isinstance(k, tuple)}
    return p


def _make_duffel_provider(cache: dict) -> DuffelProvider:
    p = DuffelProvider(start_airport="OLB", end_airport="CIA", dates=["2026-07-10"])
    p.token = "fake"
    p._cache_initialized = True
    p._cache = cache
    return p


LEG_OLB_BCN_RYR = FlightLeg(
    "OLB", "BCN", "Olbia", "Barcelona",
    datetime(2026, 7, 10, 7, 0), datetime(2026, 7, 10, 9, 15),
    49.0, "Ryanair", "FR4701"
)
LEG_BCN_CIA_VY = FlightLeg(
    "BCN", "CIA", "Barcelona", "Roma Ciampino",
    datetime(2026, 7, 12, 14, 0), datetime(2026, 7, 12, 16, 10),
    65.0, "Vueling", "VY6609"
)


def test_cross_provider_happy_path():
    """
    Duffel ha in cache il segmento BCN→CIA (trovato via decomposizione 2-segment).
    RyanairProvider ha OLB→BCN.
    Il router deve produrre una connessione cross-provider Ryanair+Vueling.
    """
    ryanair = RyanairProvider()
    ryanair._destinations_cache = {
        "OLB": ["BCN"],
        "CIA": ["BCN"],
    }
    ryanair._flights_cache = {
        ("OLB", "BCN", "2026-07-01"): [LEG_OLB_BCN_RYR],
        ("BCN", "CIA", "2026-07-01"): [],  # Ryanair non vola BCN→CIA in questo scenario
    }

    duffel = _make_duffel_provider({
        ("BCN", "CIA", "2026-07-10"): [LEG_BCN_CIA_VY],
        ("OLB", "BCN", "2026-07-10"): [],
    })

    res = find_connections(
        [(ryanair, ["2026-07-01"]), (duffel, ["2026-07-10"])],
        "OLB", "CIA",
        max_layover_h=120.0,
        use_city_groups=False,
        filter_start="2026-07-10", filter_end="2026-07-12",
    )

    cross = [c for c in res if c.first_leg.carrier != c.second_leg.carrier]
    assert len(cross) >= 1, "Attesa almeno 1 connessione cross-provider"
    assert cross[0].first_leg.carrier == "Ryanair"
    assert cross[0].second_leg.carrier == "Vueling"
    assert cross[0].total_price == 114.0


def test_cross_provider_gap_when_duffel_cache_incomplete():
    """
    Duffel ha in cache solo la rotta OLB→CIA diretta (nessun segmento via BCN).
    RyanairProvider ha OLB→BCN ma NON ha BCN→CIA.

    In questo caso il prodotto cartesiano non può produrre connessioni cross-provider
    perché second_legs da Duffel per BCN→CIA è vuoto (cache miss).
    Questo test documenta il gap attuale: il mixing NON avviene in questo scenario.
    """
    ryanair = RyanairProvider()
    ryanair._destinations_cache = {
        "OLB": ["BCN"],
        "CIA": ["BCN"],
    }
    ryanair._flights_cache = {
        ("OLB", "BCN", "2026-07-01"): [LEG_OLB_BCN_RYR],
        ("BCN", "CIA", "2026-07-01"): [],  # Ryanair non vola BCN→CIA in questo scenario
    }

    # Duffel ha solo la rotta diretta OLB→CIA, nessun segmento via BCN in cache
    duffel = _make_duffel_provider({
        ("OLB", "CIA", "2026-07-10"): [],  # nessun volo diretto trovato
        # ("BCN", "CIA", ...) non presente → cache miss → get_flights ritorna []
    })

    res = find_connections(
        [(ryanair, ["2026-07-01"]), (duffel, ["2026-07-10"])],
        "OLB", "CIA",
        max_layover_h=120.0,
        use_city_groups=False,
        filter_start="2026-07-10", filter_end="2026-07-12",
    )

    # Nessuna connessione: Ryanair ha leg1 (OLB→BCN) ma nessuno ha leg2 (BCN→CIA)
    assert len(res) == 0, (
        "GAP documentato: il mixing non avviene se il segmento Duffel non è in cache. "
        "Fix richiede query proattiva a Duffel per i via-candidates mancanti."
    )
