from unittest.mock import patch, MagicMock
from datetime import datetime
from api.models import FlightLeg
from api.providers.ryanair import RyanairProvider

@patch("api.providers.ryanair.requests.get")
def test_get_destinations_returns_list(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"arrivalAirport": {"code": "AMS"}},
        {"arrivalAirport": {"code": "JFK"}}
    ]
    mock_get.return_value = mock_response

    provider = RyanairProvider()
    res = provider.get_destinations("FCO")
    assert isinstance(res, list)
    assert "AMS" in res
    assert "JFK" in res

@patch("api.providers.ryanair.requests.get")
def test_get_flights_returns_flight_legs(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "outbound": {
            "fares": [
                {
                    "departureDate": "2026-06-16T10:00:00",
                    "arrivalDate": "2026-06-16T12:30:00",
                    "price": {"value": 50.0},
                    "flightNumber": "FR1234",
                    "unavailable": False
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    provider = RyanairProvider()
    # Mock airport lookup to avoid real HTTP call during tests
    provider._airport_lookup = {"FCO": "Rome", "AMS": "Amsterdam"}
    
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert len(res) == 1
    leg = res[0]
    assert isinstance(leg, FlightLeg)
    assert leg.from_code == "FCO"
    assert leg.to_code == "AMS"
    assert leg.from_city == "Rome"
    assert leg.to_city == "Amsterdam"
    assert leg.price == 50.0
    assert leg.flight_number == "FR1234"

@patch("api.providers.ryanair.requests.get")
def test_get_flights_empty_on_404(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    provider = RyanairProvider()
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert res == []

@patch("api.providers.ryanair.requests.get")
def test_get_flights_parses_dates(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "outbound": {
            "fares": [
                {
                    "departureDate": "2026-06-16T10:00:00.000Z",
                    "arrivalDate": "2026-06-16T12:30:00.000Z",
                    "price": {"value": 50.0},
                    "flightNumber": "FR1234",
                    "unavailable": False
                }
            ]
        }
    }
    mock_get.return_value = mock_response

    provider = RyanairProvider()
    provider._airport_lookup = {"FCO": "Rome", "AMS": "Amsterdam"}
    
    res = provider.get_flights("FCO", "AMS", "2026-06-16")
    assert len(res) == 1
    assert isinstance(res[0].departure, datetime)
    assert isinstance(res[0].arrival, datetime)
    assert res[0].departure == datetime(2026, 6, 16, 10, 0)
    assert res[0].arrival == datetime(2026, 6, 16, 12, 30)
