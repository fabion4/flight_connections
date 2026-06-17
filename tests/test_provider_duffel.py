import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from api.models import FlightLeg
from api.providers.duffel import DuffelProvider

@patch("api.providers.duffel.requests.post")
def test_get_flights_direct(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "data": {
            "offers": [
                {
                    "total_amount": "150.00",
                    "slices": [
                        {
                            "segments": [
                                {
                                    "origin": {"iata_code": "FCO", "city_name": "Rome"},
                                    "destination": {"iata_code": "AMS", "city_name": "Amsterdam"},
                                    "departing_at": "2026-06-16T10:00:00Z",
                                    "arriving_at": "2026-06-16T12:30:00Z",
                                    "operating_carrier": {"name": "Duffel Air", "iata_code": "ZZ"},
                                    "flight_number": "123"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    mock_post.return_value = mock_response

    provider = DuffelProvider()
    provider.token = "fake_token"
    
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert len(res) == 1
    assert res[0].from_code == "FCO"
    assert res[0].to_code == "AMS"
    assert res[0].price == 150.0
    assert res[0].carrier == "Duffel Air"
    assert res[0].flight_number == "ZZ123"

@patch("api.providers.duffel.requests.post")
def test_get_flights_2segment_decomposed(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "data": {
            "offers": [
                {
                    "total_amount": "300.00",
                    "slices": [
                        {
                            "segments": [
                                {
                                    "origin": {"iata_code": "FCO", "city_name": "Rome"},
                                    "destination": {"iata_code": "AMS", "city_name": "Amsterdam"},
                                    "departing_at": "2026-06-16T10:00:00Z",
                                    "arriving_at": "2026-06-16T12:00:00Z",
                                    "operating_carrier": {"name": "Duffel Air", "iata_code": "ZZ"},
                                    "flight_number": "123"
                                },
                                {
                                    "origin": {"iata_code": "AMS", "city_name": "Amsterdam"},
                                    "destination": {"iata_code": "JFK", "city_name": "New York"},
                                    "departing_at": "2026-06-16T15:00:00Z",
                                    "arriving_at": "2026-06-16T23:00:00Z",
                                    "operating_carrier": {"name": "Duffel Air", "iata_code": "ZZ"},
                                    "flight_number": "456"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    mock_post.return_value = mock_response

    provider = DuffelProvider()
    provider.token = "fake_token"
    
    res = provider.get_flights("FCO", "JFK", "2026-06-16")
    assert len(res) == 2
    
    assert res[0].from_code == "FCO"
    assert res[0].to_code == "AMS"
    assert res[0].price == 60.0  # 300 * (2h / 10h)
    
    assert res[1].from_code == "AMS"
    assert res[1].to_code == "JFK"
    assert res[1].price == 240.0  # 300 * (8h / 10h)

def test_get_destinations_from_decomposed_cache():
    """
    Verifica che get_destinations restituisca aeroporti in ENTRAMBE le direzioni.
    Caso reale: Duffel restituisce CAG→BCN→MUC come offerta 2-segment.
    Dopo la decomposizione il cache ha (CAG,BCN) e (BCN,MUC).
    get_destinations("MUC") deve restituire BCN (trovandolo come to_code=MUC → from_code=BCN),
    altrimenti il router non costruisce mai la connessione via BCN.
    """
    provider = DuffelProvider()
    provider.token = "fake_token"
    provider._cache_initialized = True
    from datetime import datetime
    from api.models import FlightLeg
    leg1 = FlightLeg("CAG", "BCN", "Cagliari", "Barcelona", datetime(2026, 6, 17, 10, 0), datetime(2026, 6, 17, 12, 0), 60.0, "Vueling", "VY100")
    leg2 = FlightLeg("BCN", "MUC", "Barcelona", "Munich", datetime(2026, 6, 17, 14, 0), datetime(2026, 6, 17, 16, 0), 100.0, "Vueling", "VY200")
    provider._cache = {
        ("CAG", "BCN", "2026-06-17"): [leg1],
        ("BCN", "MUC", "2026-06-17"): [leg2],
    }
    # get_destinations("CAG") deve trovare BCN (CAG vola verso BCN)
    assert "BCN" in provider.get_destinations("CAG")
    # get_destinations("MUC") deve trovare BCN (BCN vola verso MUC)
    assert "BCN" in provider.get_destinations("MUC")
    # L'intersezione dei due set produce il via_candidate BCN
    via = set(provider.get_destinations("CAG")) & set(provider.get_destinations("MUC"))
    assert "BCN" in via

def test_get_destinations_router_integration_2segment():
    """
    Test end-to-end (senza HTTP) che verifica che una connessione Duffel 2-segment
    decomposita venga ricostruita correttamente dal router.
    """
    from api.router import find_connections
    provider = DuffelProvider(start_airport="CAG", end_airport="MUC", dates=["2026-06-17"])
    provider.token = "fake_token"
    provider._cache_initialized = True
    from api.models import FlightLeg
    leg1 = FlightLeg("CAG", "BCN", "Cagliari", "Barcelona", datetime(2026, 6, 17, 10, 0), datetime(2026, 6, 17, 12, 0), 60.0, "Vueling", "VY100")
    leg2 = FlightLeg("BCN", "MUC", "Barcelona", "Munich", datetime(2026, 6, 17, 14, 0), datetime(2026, 6, 17, 16, 0), 100.0, "Vueling", "VY200")
    provider._cache = {
        ("CAG", "BCN", "2026-06-17"): [leg1],
        ("BCN", "MUC", "2026-06-17"): [leg2],
    }
    res = find_connections([(provider, ["2026-06-17"])], "CAG", "MUC", max_layover_h=120.0,
                           use_city_groups=False, filter_start="2026-06-17", filter_end="2026-06-17")
    assert len(res) == 1
    assert res[0].connection_label == "CAG-BCN | BCN-MUC"
    assert res[0].total_price == 160.0
    assert res[0].layover_h == 2.0

def test_get_flights_empty_on_no_token():
    provider = DuffelProvider()
    provider.token = None
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert res == []

@patch("api.providers.duffel.time.sleep")
@patch("api.providers.duffel.requests.post")
def test_get_flights_retries_on_429(mock_post, mock_sleep):
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"ratelimit-reset": "0.1"}
    
    mock_201 = MagicMock()
    mock_201.status_code = 201
    mock_201.json.return_value = {
        "data": {
            "offers": [
                {
                    "total_amount": "100.00",
                    "slices": [
                        {
                            "segments": [
                                {
                                    "origin": {"iata_code": "FCO"},
                                    "destination": {"iata_code": "AMS"},
                                    "departing_at": "2026-06-16T10:00:00Z",
                                    "arriving_at": "2026-06-16T12:00:00Z",
                                    "operating_carrier": {"name": "Carrier"},
                                    "flight_number": "123"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    # First request returns 429, second returns 201
    mock_post.side_effect = [mock_429, mock_201]
    
    provider = DuffelProvider()
    provider.token = "fake_token"
    
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert len(res) == 1
    assert res[0].price == 100.0
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(0.1)
