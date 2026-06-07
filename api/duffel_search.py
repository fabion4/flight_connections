import os
import requests
from datetime import datetime
import pandas as pd
from typing import List, Dict

# Recuperiamo il token Duffel leggendo dal file d'ambiente
DUFFEL_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN")

def get_flight_data_duffel(from_code: str, to_code: str, date_str: str) -> List[Dict]:
    """
    Interroga Duffel API v2 per cercare voli tra due aeroporti
    per una specifica data (formato YYYY-MM-DD).
    Supporta voli diretti e voli con 1 scalo restituiti direttamente da Duffel.
    """
    if not DUFFEL_TOKEN:
        print("Duffel API non configurata. Manca DUFFEL_ACCESS_TOKEN in .env.")
        return []

    url = "https://api.duffel.com/air/offer_requests"
    headers = {
        "Authorization": f"Bearer {DUFFEL_TOKEN}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "data": {
            "slices": [
                {
                    "origin": from_code,
                    "destination": to_code,
                    "departure_date": date_str
                }
            ],
            "passengers": [
                {"type": "adult"}
            ],
            "cabin_class": "economy"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 201:
            print(f"Duffel API Error (Status {response.status_code}): {response.text}")
            return []

        data = response.json()
        offers = data.get("data", {}).get("offers", [])
        
        results = []
        for offer in offers:
            # Duffel restituisce le offerte per la slice richiesta
            for slice_item in offer.get("slices", []):
                segments = slice_item.get("segments", [])
                
                # Gestiamo voli diretti (1 segmento)
                if len(segments) == 1:
                    seg = segments[0]
                    dep_dt = datetime.fromisoformat(seg.get("departing_at", "").replace("Z", ""))
                    arr_dt = datetime.fromisoformat(seg.get("arriving_at", "").replace("Z", ""))
                    
                    results.append({
                        "Connection": f"{seg.get('origin', {}).get('iata_code')}-{seg.get('destination', {}).get('iata_code')} (Diretto)",
                        "First Leg Departure": dep_dt.strftime("%Y-%m-%d %H:%M"),
                        "First Leg Arrival": arr_dt.strftime("%Y-%m-%d %H:%M"),
                        "First Leg Carrier": seg.get("operating_carrier", {}).get("name", "Unknown"),
                        "First Leg Flight Number": f"{seg.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg.get('flight_number', '999')}",
                        "Second Leg Departure": "-",
                        "Second Leg Arrival": "-",
                        "Second Leg Carrier": "-",
                        "Second Leg Flight Number": "-",
                        "Layover (h)": 0.0,
                        "Total Duration (h)": round((arr_dt - dep_dt).total_seconds() / 3600, 1),
                        "Total Price (€)": float(offer.get("total_amount", 0.0))
                    })
                
                # Gestiamo voli con 1 scalo (2 segmenti)
                elif len(segments) == 2:
                    seg1 = segments[0]
                    seg2 = segments[1]
                    
                    dep_dt1 = datetime.fromisoformat(seg1.get("departing_at", "").replace("Z", ""))
                    arr_dt1 = datetime.fromisoformat(seg1.get("arriving_at", "").replace("Z", ""))
                    dep_dt2 = datetime.fromisoformat(seg2.get("departing_at", "").replace("Z", ""))
                    arr_dt2 = datetime.fromisoformat(seg2.get("arriving_at", "").replace("Z", ""))
                    
                    layover_time = (dep_dt2 - arr_dt1).total_seconds() / 3600
                    total_duration = (arr_dt2 - dep_dt1).total_seconds() / 3600
                    
                    results.append({
                        "Connection": f"{seg1.get('origin', {}).get('iata_code')}-{seg1.get('destination', {}).get('iata_code')} | {seg2.get('origin', {}).get('iata_code')}-{seg2.get('destination', {}).get('iata_code')}",
                        "First Leg Departure": dep_dt1.strftime("%Y-%m-%d %H:%M"),
                        "First Leg Arrival": arr_dt1.strftime("%Y-%m-%d %H:%M"),
                        "First Leg Carrier": seg1.get("operating_carrier", {}).get("name", "Unknown"),
                        "First Leg Flight Number": f"{seg1.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg1.get('flight_number', '999')}",
                        "Second Leg Departure": dep_dt2.strftime("%Y-%m-%d %H:%M"),
                        "Second Leg Arrival": arr_dt2.strftime("%Y-%m-%d %H:%M"),
                        "Second Leg Carrier": seg2.get("operating_carrier", {}).get("name", "Unknown"),
                        "Second Leg Flight Number": f"{seg2.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg2.get('flight_number', '999')}",
                        "Layover (h)": round(layover_time, 1),
                        "Total Duration (h)": round(total_duration, 1),
                        "Total Price (€)": float(offer.get("total_amount", 0.0))
                    })
        
        return results

    except Exception as e:
        print(f"Errore durante l'interrogazione di Duffel: {str(e)}")
        return []

def find_best_routes_duffel(start_airport: str, end_airport: str, date: str, max_layover_days: int = 3) -> pd.DataFrame:
    """
    Trova rotte dirette e con 1 scalo interpellando Duffel API v2.
    Filtra i voli con scalo che superano max_layover_days.
    """
    routes = get_flight_data_duffel(start_airport, end_airport, date)
    
    # Filtriamo eventuali voli con scalo che superano il tempo massimo richiesto
    filtered_routes = []
    for r in routes:
        if r["Layover (h)"] > (max_layover_days * 24):
            continue
        filtered_routes.append(r)
        
    if not filtered_routes:
        return pd.DataFrame()
        
    return pd.DataFrame(filtered_routes).sort_values(by="Total Price (€)")
