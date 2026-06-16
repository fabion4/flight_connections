import requests
import urllib3
from datetime import datetime
from api.models import FlightLeg
from api.providers.base import FlightProvider

# Disable warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_airports():
    url = "https://www.ryanair.com/api/views/locate/3/airports/en/active"
    try:
        response = requests.get(url, verify=False, timeout=15)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return []

def parse_datetime(date_str):
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato data non riconosciuto: {date_str}")

class RyanairProvider(FlightProvider):
    def __init__(self):
        self._airport_lookup = None

    @property
    def airport_lookup(self) -> dict[str, str]:
        if self._airport_lookup is None:
            try:
                airports = get_airports()
                self._airport_lookup = {
                    a["iataCode"]: a.get("city", {}).get("name", a["name"])
                    for a in airports if "iataCode" in a
                }
            except Exception:
                self._airport_lookup = {}
        return self._airport_lookup

    def get_destinations(self, airport_code: str) -> list[str]:
        url = f"https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/{airport_code}"
        try:
            response = requests.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return [route["arrivalAirport"]["code"] for route in data]
        except Exception:
            pass
        return []

    def get_flights(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        url = f"https://www.ryanair.com/api/farfnd/v4/oneWayFares/{from_code}/{to_code}/cheapestPerDay?outboundMonthOfDate={date_str}&currency=EUR"
        try:
            response = requests.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                flights = response.json().get("outbound", {}).get("fares", [])
                
                results = []
                for f in flights:
                    if f.get("unavailable", False):
                        continue
                    price_val = f["price"]["value"] if f.get("price") else 0.0
                    flight_num = f.get("flightNumber", f"FR{price_val*100:.0f}" if price_val else "FR999")
                    
                    results.append(
                        FlightLeg(
                            from_code=from_code,
                            to_code=to_code,
                            from_city=self.airport_lookup.get(from_code, from_code),
                            to_city=self.airport_lookup.get(to_code, to_code),
                            departure=parse_datetime(f["departureDate"]),
                            arrival=parse_datetime(f["arrivalDate"]),
                            price=float(price_val),
                            carrier="Ryanair",
                            flight_number=flight_num
                        )
                    )
                return results
        except Exception:
            pass
        return []
