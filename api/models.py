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
        """Serializza nel formato colonne atteso dal frontend."""
        return {
            "Connection": self.connection_label,
            "First Leg Departure": self.first_leg.departure.strftime("%Y-%m-%d %H:%M"),
            "First Leg Arrival": self.first_leg.arrival.strftime("%Y-%m-%d %H:%M"),
            "First Leg Carrier": self.first_leg.carrier,
            "First Leg Flight Number": self.first_leg.flight_number,
            "Second Leg Departure": self.second_leg.departure.strftime("%Y-%m-%d %H:%M") if self.second_leg else None,
            "Second Leg Arrival": self.second_leg.arrival.strftime("%Y-%m-%d %H:%M") if self.second_leg else None,
            "Second Leg Carrier": self.second_leg.carrier if self.second_leg else None,
            "Second Leg Flight Number": self.second_leg.flight_number if self.second_leg else None,
            "Layover (h)": self.layover_h,
            "Total Duration (h)": self.total_duration_h,
            "Total Price (€)": self.total_price,
            "First Leg Origin City": self.first_leg.from_city,
            "First Leg Destination City": self.first_leg.to_city,
            "Second Leg Origin City": self.second_leg.from_city if self.second_leg else None,
            "Second Leg Destination City": self.second_leg.to_city if self.second_leg else None
        }
