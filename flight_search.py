import requests
import pandas as pd
from itertools import product
from datetime import datetime, timedelta

def get_airports():
    url = "https://www.ryanair.com/api/views/locate/3/airports/en/active"
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        return response.json()  # Restituisce la lista degli aeroporti
    else:
        return []

def get_available_destinations(airport_code):
    """Recupera le destinazioni disponibili da un dato aeroporto."""
    url = f"https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/{airport_code}"
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        data = response.json()
        return [route["arrivalAirport"]["code"] for route in data]
    return []

def parse_datetime(date_str):
    """Tenta di convertire una stringa di data in oggetto datetime gestendo diversi formati."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato data non riconosciuto: {date_str}")

def get_flight_data(from_code, to_code, date):
    """Recupera i voli disponibili tra due aeroporti per una data specifica."""
    url = f"https://www.ryanair.com/api/farfnd/v4/oneWayFares/{from_code}/{to_code}/cheapestPerDay?outboundMonthOfDate={date}&currency=EUR"
    response = requests.get(url, verify=False)
    
    if response.status_code == 200:
        flights = response.json().get("outbound", {}).get("fares", [])
        return [
            {
                "from": from_code,
                "to": to_code,
                "departure": parse_datetime(f["departureDate"]),
                "arrival": parse_datetime(f["arrivalDate"]),
                "price": f["price"]["value"] if f["price"] else None
            }
            for f in flights if not f["unavailable"]
        ]
    
    return []

def find_best_routes(start_airport, end_airport, date, max_layover_days=3):
    """Trova tutte le connessioni ottimali tra start_airport e end_airport, includendo voli diretti."""
    
    routes = []

    # 🔹 1. Controlliamo se esiste un volo diretto
    direct_flights = get_flight_data(start_airport, end_airport, date)
    for flight in direct_flights:
        routes.append({
            "Connection": f"{flight['from']}-{flight['to']} (Diretto)",
            "First Leg Departure": flight["departure"].strftime("%Y-%m-%d %H:%M"),
            "First Leg Arrival": flight["arrival"].strftime("%Y-%m-%d %H:%M"),
            "Second Leg Departure": "-",
            "Second Leg Arrival": "-",
            "Layover (h)": 0,
            "Total Duration (h)": (flight["arrival"] - flight["departure"]).total_seconds() / 3600,
            "Total Price (€)": flight["price"]
        })

    # 🔹 2. Cerchiamo voli con scalo
    first_leg_airports = get_available_destinations(start_airport)
    second_leg_airports = get_available_destinations(end_airport)
    valid_airports = set(first_leg_airports) & set(second_leg_airports)

    for via_airport in valid_airports:
        first_leg = get_flight_data(start_airport, via_airport, date)
        second_leg = get_flight_data(via_airport, end_airport, date)

        for f1, f2 in product(first_leg, second_leg):
            layover_time = (f2["departure"] - f1["arrival"]).total_seconds() / 3600
            total_duration = (f2["arrival"] - f1["departure"]).total_seconds() / 3600

            if 0 < layover_time <= max_layover_days * 24:
                total_price = f1["price"] + f2["price"]
                routes.append({
                    "Connection": f"{f1['from']}-{f1['to']} | {f2['from']}-{f2['to']}",
                    "First Leg Departure": f1["departure"].strftime("%Y-%m-%d %H:%M"),
                    "First Leg Arrival": f1["arrival"].strftime("%Y-%m-%d %H:%M"),
                    "Second Leg Departure": f2["departure"].strftime("%Y-%m-%d %H:%M"),
                    "Second Leg Arrival": f2["arrival"].strftime("%Y-%m-%d %H:%M"),
                    "Layover (h)": round(layover_time, 1),
                    "Total Duration (h)": round(total_duration, 1),
                    "Total Price (€)": total_price
                })

    # 🔹 3. Creiamo il DataFrame ordinato per prezzo
    return pd.DataFrame(routes).sort_values(by="Total Price (€)")
