import requests
import pandas as pd
from itertools import product
from datetime import datetime, timedelta
import logging
import streamlit as st
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global configuration
config = {
    "verify_ssl": False,  # Default value, can be changed
    "currency": "EUR"
}

def set_ssl_verification(verify=True):
    """Set whether SSL certificates should be verified in API requests."""
    config["verify_ssl"] = verify
    logger.info(f"SSL verification set to: {verify}")

def set_currency(currency_code="EUR"):
    """Set currency for price display."""
    config["currency"] = currency_code
    logger.info(f"Currency set to: {currency_code}")

@st.cache_data(ttl=3600)  # Cache valida per 1 ora
def get_airports():
    """Retrieve the list of active airports from Ryanair API."""
    url = "https://www.ryanair.com/api/views/locate/3/airports/en/active"
    try:
        response = requests.get(url, verify=config["verify_ssl"])
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching airports: {e}")
        return []

@st.cache_data(ttl=3600)  # Cache valida per 1 ora
def get_available_destinations(airport_code):
    """Retrieve available destinations from a given airport."""
    url = f"https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/{airport_code}"
    try:
        response = requests.get(url, verify=config["verify_ssl"])
        response.raise_for_status()
        data = response.json()
        return [route["arrivalAirport"]["code"] for route in data]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching destinations from {airport_code}: {e}")
        return []

def parse_datetime(date_str):
    """Convert a date string to datetime object handling different formats."""
    formats = ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    logger.error(f"Unrecognized date format: {date_str}")
    raise ValueError(f"Unrecognized date format: {date_str}")

@st.cache_data(ttl=3600)  # Cache valida per 1 ora
def get_flight_data(from_code, to_code, date):
    """Retrieve available flights between two airports for a specific date."""
    # Check if there's a direct route available
    destinations = get_available_destinations(from_code)
    if to_code not in destinations:
        logger.info(f"No direct route exists from {from_code} to {to_code}")
        return []
        
    url = f"https://www.ryanair.com/api/farfnd/v4/oneWayFares/{from_code}/{to_code}/cheapestPerDay?outboundMonthOfDate={date}&currency={config['currency']}"
    try:
        response = requests.get(url, verify=config["verify_ssl"])
        response.raise_for_status()
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
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching flights from {from_code} to {to_code}: {e}")
        return []

@st.cache_data(ttl=3600)  # Cache valida per 1 ora
def find_best_routes(start_airport, end_airport, date, max_layover_days=3):
    """Find all optimal connections between start_airport and end_airport, including direct flights."""
    
    # Inizio del timer
    start_time = time.time()
    
    routes = []
    logger.info(f"Searching routes from {start_airport} to {end_airport} for {date}")

    # Check if the direct route exists before attempting to fetch flights
    direct_destinations = get_available_destinations(start_airport)
    if end_airport in direct_destinations:
        # 🔹 1. Check for direct flights
        direct_flights = get_flight_data(start_airport, end_airport, date)
        for flight in direct_flights:
            routes.append({
                "Connection": f"{flight['from']}-{flight['to']} (Direct)",
                "First Leg Departure": flight["departure"].strftime("%Y-%m-%d %H:%M"),
                "First Leg Arrival": flight["arrival"].strftime("%Y-%m-%d %H:%M"),
                "Second Leg Departure": "-",
                "Second Leg Arrival": "-",
                "Layover (h)": 0,
                "Total Duration (h)": (flight["arrival"] - flight["departure"]).total_seconds() / 3600,
                "Total Price (€)": flight["price"]
            })
        logger.info(f"Found {len(direct_flights)} direct flights")
    else:
        logger.info(f"No direct route from {start_airport} to {end_airport}")

    # 🔹 2. Search for flights with layovers
    first_leg_airports = get_available_destinations(start_airport)
    second_leg_airports = []
    
    # Get all airports that have flights to the destination
    for airport in get_airports():
        if airport["iataCode"] != end_airport:  # Exclude the destination itself
            airport_destinations = get_available_destinations(airport["iataCode"])
            if end_airport in airport_destinations:
                second_leg_airports.append(airport["iataCode"])
    
    # Find valid connecting airports
    valid_airports = set(first_leg_airports) & set(second_leg_airports)
    logger.info(f"Found {len(valid_airports)} potential connecting airports")

    for via_airport in valid_airports:
        if via_airport == start_airport or via_airport == end_airport:
            continue  # Skip if connecting airport is same as start or end

        first_leg = get_flight_data(start_airport, via_airport, date)
        if not first_leg:
            continue
            
        second_leg = get_flight_data(via_airport, end_airport, date)
        if not second_leg:
            continue

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

    # 🔹 3. Create sorted DataFrame by price
    df = pd.DataFrame(routes).sort_values(by="Total Price (€)")
    logger.info(f"Found total of {len(df)} possible routes")

    # Fine del timer
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Execution time for find_best_routes: {execution_time:.2f} seconds")

    return df
