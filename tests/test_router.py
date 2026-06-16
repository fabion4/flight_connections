from datetime import datetime
from api.models import FlightLeg
from api.providers.base import FlightProvider
from api.router import find_connections

class MockProvider(FlightProvider):
    def __init__(self, destinations=None, flights=None):
        self.destinations_map = destinations or {}
        self.flights_map = flights or {}

    def get_destinations(self, airport_code: str) -> list[str]:
        return self.destinations_map.get(airport_code, [])

    def get_flights(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        return self.flights_map.get((from_code, to_code, date_str), [])

def test_direct_flight_found():
    # Direct flight exists on date "2026-06-16"
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 30), 50.0, "Carrier", "CR123")
    prov = MockProvider(
        destinations={"FCO": ["AMS"]},
        flights={("FCO", "AMS", "2026-06-16"): [f1]}
    )
    res = find_connections(prov, "FCO", "AMS", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    assert len(res) == 1
    assert res[0].connection_label == "FCO-AMS (Diretto)"
    assert res[0].total_price == 50.0

def test_one_stop_connection():
    # FCO -> AMS -> JFK connection
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 50.0, "Carrier", "CR123")
    f2 = FlightLeg("AMS", "JFK", "Amsterdam", "New York", datetime(2026, 6, 16, 15, 0), datetime(2026, 6, 16, 23, 0), 200.0, "Carrier", "CR456")
    prov = MockProvider(
        destinations={"FCO": ["AMS"], "JFK": ["AMS"]}, # Note: symmetric lookup uses end destinations
        flights={
            ("FCO", "AMS", "2026-06-16"): [f1],
            ("AMS", "JFK", "2026-06-16"): [f2]
        }
    )
    res = find_connections(prov, "FCO", "JFK", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    # Filter out direct (none found), so only connection should remain
    assert len(res) == 1
    assert res[0].connection_label == "FCO-AMS | AMS-JFK"
    assert res[0].layover_h == 3.0
    assert res[0].total_price == 250.0

def test_layover_too_long_excluded():
    # Layover is 15 hours, max is 10
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 50.0, "Carrier", "CR123")
    f2 = FlightLeg("AMS", "JFK", "Amsterdam", "New York", datetime(2026, 6, 17, 3, 0), datetime(2026, 6, 17, 11, 0), 200.0, "Carrier", "CR456")
    prov = MockProvider(
        destinations={"FCO": ["AMS"], "JFK": ["AMS"]},
        flights={
            ("FCO", "AMS", "2026-06-16"): [f1],
            ("AMS", "JFK", "2026-06-16"): [f2]
        }
    )
    res = find_connections(prov, "FCO", "JFK", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    assert len(res) == 0

def test_layover_negative_excluded():
    # second flight departs before first flight arrives
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 50.0, "Carrier", "CR123")
    f2 = FlightLeg("AMS", "JFK", "Amsterdam", "New York", datetime(2026, 6, 16, 11, 0), datetime(2026, 6, 16, 19, 0), 200.0, "Carrier", "CR456")
    prov = MockProvider(
        destinations={"FCO": ["AMS"], "JFK": ["AMS"]},
        flights={
            ("FCO", "AMS", "2026-06-16"): [f1],
            ("AMS", "JFK", "2026-06-16"): [f2]
        }
    )
    res = find_connections(prov, "FCO", "JFK", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    assert len(res) == 0

def test_city_group_cross_airport():
    # Rome group has FCO and CIA. We have flights FCO->AMS and CIA->AMS.
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 60.0, "Carrier", "CR1")
    f2 = FlightLeg("CIA", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 11, 0), datetime(2026, 6, 16, 13, 0), 40.0, "Carrier", "CR2")
    prov = MockProvider(
        destinations={"FCO": ["AMS"], "CIA": ["AMS"]},
        flights={
            ("FCO", "AMS", "2026-06-16"): [f1],
            ("CIA", "AMS", "2026-06-16"): [f2]
        }
    )
    res = find_connections(prov, "FCO", "AMS", ["2026-06-16"], max_layover_h=10.0, use_city_groups=True)
    # Both direct flights should be found and sorted by price
    assert len(res) == 2
    assert res[0].first_leg.from_code == "CIA"
    assert res[1].first_leg.from_code == "FCO"

def test_city_group_disabled():
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 60.0, "Carrier", "CR1")
    f2 = FlightLeg("CIA", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 11, 0), datetime(2026, 6, 16, 13, 0), 40.0, "Carrier", "CR2")
    prov = MockProvider(
        destinations={"FCO": ["AMS"], "CIA": ["AMS"]},
        flights={
            ("FCO", "AMS", "2026-06-16"): [f1],
            ("CIA", "AMS", "2026-06-16"): [f2]
        }
    )
    res = find_connections(prov, "FCO", "AMS", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    # Only FCO flight should be found
    assert len(res) == 1
    assert res[0].first_leg.from_code == "FCO"

def test_price_ordering():
    f1 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 10, 0), datetime(2026, 6, 16, 12, 0), 100.0, "Carrier", "CR1")
    f2 = FlightLeg("FCO", "AMS", "Rome", "Amsterdam", datetime(2026, 6, 16, 14, 0), datetime(2026, 6, 16, 16, 0), 50.0, "Carrier", "CR2")
    prov = MockProvider(
        destinations={"FCO": ["AMS"]},
        flights={("FCO", "AMS", "2026-06-16"): [f1, f2]}
    )
    res = find_connections(prov, "FCO", "AMS", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    assert len(res) == 2
    assert res[0].total_price == 50.0
    assert res[1].total_price == 100.0

def test_ryanair_monthly_date_filter():
    # Simula il caso Ryanair: dates=["2026-06-01"] (primo del mese) ma il volo
    # è il 17 giugno. Senza filter_start/filter_end il volo veniva eliminato.
    f1 = FlightLeg("CAG", "STN", "Cagliari", "London Stansted", datetime(2026, 6, 17, 21, 0), datetime(2026, 6, 17, 22, 45), 31.97, "Ryanair", "FR3197")
    prov = MockProvider(
        destinations={"CAG": ["STN"]},
        flights={("CAG", "STN", "2026-06-01"): [f1]}
    )
    # Con date mensili ma filter_range corretto deve trovare il volo
    res = find_connections(prov, "CAG", "STN", ["2026-06-01"], max_layover_h=120.0,
                           use_city_groups=False, filter_start="2026-06-16", filter_end="2026-06-30")
    assert len(res) == 1
    assert res[0].first_leg.flight_number == "FR3197"

def test_ryanair_monthly_date_filter_excludes_out_of_range():
    # Volo il 17 giugno ma range richiesto solo dal 20 in poi: deve essere escluso
    f1 = FlightLeg("CAG", "STN", "Cagliari", "London Stansted", datetime(2026, 6, 17, 21, 0), datetime(2026, 6, 17, 22, 45), 31.97, "Ryanair", "FR3197")
    prov = MockProvider(
        destinations={"CAG": ["STN"]},
        flights={("CAG", "STN", "2026-06-01"): [f1]}
    )
    res = find_connections(prov, "CAG", "STN", ["2026-06-01"], max_layover_h=120.0,
                           use_city_groups=False, filter_start="2026-06-20", filter_end="2026-06-30")
    assert len(res) == 0

def test_empty_intersection():
    prov = MockProvider(
        destinations={"FCO": ["CDG"], "JFK": ["DXB"]},
        flights={}
    )
    res = find_connections(prov, "FCO", "JFK", ["2026-06-16"], max_layover_h=10.0, use_city_groups=False)
    assert len(res) == 0
