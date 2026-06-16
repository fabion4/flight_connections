from datetime import datetime
from api.models import FlightLeg, Connection

def test_to_dict_direct_flight():
    leg = FlightLeg(
        from_code="FCO",
        to_code="AMS",
        from_city="Rome",
        to_city="Amsterdam",
        departure=datetime(2026, 6, 16, 10, 0),
        arrival=datetime(2026, 6, 16, 12, 30),
        price=50.0,
        carrier="Ryanair",
        flight_number="FR1234"
    )
    conn = Connection(
        connection_label="FCO-AMS (Diretto)",
        first_leg=leg,
        second_leg=None,
        layover_h=0.0,
        total_duration_h=2.5,
        total_price=50.0
    )
    d = conn.to_dict()
    assert d["Connection"] == "FCO-AMS (Diretto)"
    assert d["First Leg Departure"] == "2026-06-16 10:00"
    assert d["First Leg Arrival"] == "2026-06-16 12:30"
    assert d["First Leg Carrier"] == "Ryanair"
    assert d["First Leg Flight Number"] == "FR1234"
    assert d["Second Leg Departure"] is None
    assert d["Second Leg Arrival"] is None
    assert d["Second Leg Carrier"] is None
    assert d["Second Leg Flight Number"] is None
    assert d["Layover (h)"] == 0.0
    assert d["Total Duration (h)"] == 2.5
    assert d["Total Price (€)"] == 50.0
    assert d["First Leg Origin City"] == "Rome"
    assert d["First Leg Destination City"] == "Amsterdam"
    assert d["Second Leg Origin City"] is None
    assert d["Second Leg Destination City"] is None

def test_to_dict_one_stop():
    leg1 = FlightLeg(
        from_code="FCO",
        to_code="AMS",
        from_city="Rome",
        to_city="Amsterdam",
        departure=datetime(2026, 6, 16, 10, 0),
        arrival=datetime(2026, 6, 16, 12, 30),
        price=50.0,
        carrier="Ryanair",
        flight_number="FR1234"
    )
    leg2 = FlightLeg(
        from_code="AMS",
        to_code="JFK",
        from_city="Amsterdam",
        to_city="New York",
        departure=datetime(2026, 6, 16, 15, 0),
        arrival=datetime(2026, 6, 16, 23, 0),
        price=200.0,
        carrier="Duffel Air",
        flight_number="ZZ999"
    )
    conn = Connection(
        connection_label="FCO-AMS | AMS-JFK",
        first_leg=leg1,
        second_leg=leg2,
        layover_h=2.5,
        total_duration_h=13.0,
        total_price=250.0
    )
    d = conn.to_dict()
    assert d["Connection"] == "FCO-AMS | AMS-JFK"
    assert d["First Leg Departure"] == "2026-06-16 10:00"
    assert d["First Leg Arrival"] == "2026-06-16 12:30"
    assert d["Second Leg Departure"] == "2026-06-16 15:00"
    assert d["Second Leg Arrival"] == "2026-06-16 23:00"
    assert d["Second Leg Carrier"] == "Duffel Air"
    assert d["Second Leg Flight Number"] == "ZZ999"
    assert d["Layover (h)"] == 2.5
    assert d["Total Duration (h)"] == 13.0
    assert d["Total Price (€)"] == 250.0
    assert d["First Leg Origin City"] == "Rome"
    assert d["First Leg Destination City"] == "Amsterdam"
    assert d["Second Leg Origin City"] == "Amsterdam"
    assert d["Second Leg Destination City"] == "New York"
