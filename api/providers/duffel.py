import os
import requests
import time
from datetime import datetime
from api.models import FlightLeg
from api.providers.base import FlightProvider
from api.city_groups import expand_airport

GLOBAL_HUBS = [
    "ATL", "PEK", "LAX", "HND", "ORD", "LHR", "PVG", "CDG", "DFW", "AMS",
    "FRA", "IST", "CAN", "SIN", "ICN", "DEN", "BKK", "SFO", "DEL", "KUL",
    "MAD", "IAH", "CTU", "SZX", "MUC", "SYD", "MCO", "LAS", "FUK", "FCO",
    "EWR", "NRT", "ARN", "OSL", "CPH", "HEL", "ATH", "LIS", "VIE", "ZRH",
    "BRU", "DUB", "MAN", "MXP", "LIN", "BGY", "CIA", "LGW", "STN", "LTN",
    "LCY", "ORY", "BVA", "JFK", "LGA", "EWR", "MDW", "BUR", "LGB", "ONT",
    "SNA", "KIX", "ITM", "SEA", "MSP", "DTW", "PHL", "CLT", "BOS", "FLL",
    "BWI", "SLC", "SAN", "IAD", "TPA", "DOH", "DXB", "AUH", "MCT", "RUH",
    "JED", "KWI", "BAH", "AMM", "BEY", "CAI", "ADD", "NBO", "JNB", "CPT",
    "LOS", "ABV", "DKR", "CMN", "TUN", "GRU", "GIG", "EZE", "SCL", "LIM",
    "BOG", "CCS", "PTY", "SAL", "MEX", "CUN", "YYZ", "YVR", "YUL", "YYC",
    "YEG", "AKL", "MEL", "BNE", "PER", "HKG", "TPE", "MNL", "CGK", "SGN",
    "HAN", "BOM", "BLR", "MAA", "CCU"
]
GLOBAL_HUBS = list(dict.fromkeys(GLOBAL_HUBS))

def _get_place_name(place: dict) -> str:
    if not place:
        return ""
    city_name = place.get("city_name")
    if city_name:
        return city_name
    city_obj = place.get("city")
    if isinstance(city_obj, dict):
        city_name = city_obj.get("name")
        if city_name:
            return city_name
    return place.get("name", place.get("iata_code", ""))

class DuffelProvider(FlightProvider):
    def __init__(self, start_airport: str = None, end_airport: str = None, dates: list[str] = None, progress_callback = None):
        self.token = os.getenv("DUFFEL_ACCESS_TOKEN")
        self.start_airport = start_airport
        self.end_airport = end_airport
        self.dates = dates
        self.progress_callback = progress_callback
        self._cache = {}
        self._cache_initialized = False

    def _initialize_cache(self):
        if self._cache_initialized:
            return
        self._cache_initialized = True
        
        if not self.token or not self.start_airport or not self.end_airport or not self.dates:
            return

        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        total_days = len(self.dates)
        if total_days == 0:
            return
            
        max_workers = min(total_days, 3)
        completed_days = 0
        
        # Duffel gestisce la ricerca globale tra le coppie di aeroporti espansi
        start_expanded = expand_airport(self.start_airport)
        end_expanded = expand_airport(self.end_airport)
        
        # Generiamo le combinazioni di origini e destinazioni espanse da interrogare per ciascuna data
        queries = []
        for d in self.dates:
            for s in start_expanded:
                for e in end_expanded:
                    queries.append((s, e, d))
                    
        if not queries:
            return
            
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._fetch_and_decompose, s, e, d): (s, e, d)
                for s, e, d in queries
            }
            
            for future in as_completed(futures):
                completed_days += 1
                s, e, d = futures[future]
                try:
                    legs = future.result()
                    for leg in legs:
                        date_key = leg.departure.strftime("%Y-%m-%d")
                        key = (leg.from_code.upper(), leg.to_code.upper(), date_key)
                        if key not in self._cache:
                            self._cache[key] = []
                        self._cache[key].append(leg)
                except Exception as ex:
                    print(f"Errore cache Duffel per {s}->{e} in data {d}: {ex}")
                    
                if self.progress_callback:
                    percent = 20 + int((completed_days / len(queries)) * 75)
                    self.progress_callback(percent, f"Ricerca Duffel: volo {completed_days}/{len(queries)} completato")

    def get_destinations(self, airport_code: str) -> list[str]:
        self._initialize_cache()
        if self._cache:
            # Restituisce aeroporti connessi in entrambe le direzioni: FROM e TO.
            # Necessario perché i segmenti decomposit da offerte 2-leg (es. CAG→BCN→MUC)
            # sono nel cache come (CAG,BCN) e (BCN,MUC). Quando il router chiama
            # get_destinations("MUC") per trovare via_candidates, deve trovare BCN
            # cercando chi arriva a MUC, non solo chi parte da MUC.
            code = airport_code.upper()
            connected = set()
            for (f_code, t_code, _) in self._cache.keys():
                if f_code == code:
                    connected.add(t_code)
                elif t_code == code:
                    connected.add(f_code)
            return list(connected)
        return [hub for hub in GLOBAL_HUBS if hub.upper() != airport_code.upper()]

    def get_flights(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        if not self.dates:
            return self._fetch_and_decompose(from_code, to_code, date_str)
            
        self._initialize_cache()
        key = (from_code.upper(), to_code.upper(), date_str)
        return self._cache.get(key, [])

    def _fetch_and_decompose(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        if not self.token:
            print("Duffel API non configurata. Manca DUFFEL_ACCESS_TOKEN.")
            return []

        url = "https://api.duffel.com/air/offer_requests"
        headers = {
            "Authorization": f"Bearer {self.token}",
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

        max_retries = 4
        backoff_time = 2.0

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                
                if response.status_code == 201:
                    data = response.json()
                    offers = data.get("data", {}).get("offers", [])
                    
                    results = []
                    for offer in offers:
                        total_price = float(offer.get("total_amount", 0.0))
                        for slice_item in offer.get("slices", []):
                            segments = slice_item.get("segments", [])
                            
                            if len(segments) == 1:
                                seg = segments[0]
                                dep_dt = datetime.fromisoformat(seg.get("departing_at", "").replace("Z", ""))
                                arr_dt = datetime.fromisoformat(seg.get("arriving_at", "").replace("Z", ""))
                                
                                results.append(
                                    FlightLeg(
                                        from_code=seg.get("origin", {}).get("iata_code", ""),
                                        to_code=seg.get("destination", {}).get("iata_code", ""),
                                        from_city=_get_place_name(seg.get("origin")),
                                        to_city=_get_place_name(seg.get("destination")),
                                        departure=dep_dt,
                                        arrival=arr_dt,
                                        price=total_price,
                                        carrier=seg.get("operating_carrier", {}).get("name", "Unknown"),
                                        flight_number=f"{seg.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg.get('flight_number', '999')}"
                                    )
                                )
                                
                            elif len(segments) == 2:
                                seg1 = segments[0]
                                seg2 = segments[1]
                                
                                dep_dt1 = datetime.fromisoformat(seg1.get("departing_at", "").replace("Z", ""))
                                arr_dt1 = datetime.fromisoformat(seg1.get("arriving_at", "").replace("Z", ""))
                                dep_dt2 = datetime.fromisoformat(seg2.get("departing_at", "").replace("Z", ""))
                                arr_dt2 = datetime.fromisoformat(seg2.get("arriving_at", "").replace("Z", ""))
                                
                                dur1 = (arr_dt1 - dep_dt1).total_seconds()
                                dur2 = (arr_dt2 - dep_dt2).total_seconds()
                                total_dur = dur1 + dur2
                                
                                if total_dur > 0:
                                    price1 = total_price * (dur1 / total_dur)
                                    price2 = total_price * (dur2 / total_dur)
                                else:
                                    price1 = total_price / 2.0
                                    price2 = total_price / 2.0
                                    
                                results.append(
                                    FlightLeg(
                                        from_code=seg1.get("origin", {}).get("iata_code", ""),
                                        to_code=seg1.get("destination", {}).get("iata_code", ""),
                                        from_city=_get_place_name(seg1.get("origin")),
                                        to_city=_get_place_name(seg1.get("destination")),
                                        departure=dep_dt1,
                                        arrival=arr_dt1,
                                        price=price1,
                                        carrier=seg1.get("operating_carrier", {}).get("name", "Unknown"),
                                        flight_number=f"{seg1.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg1.get('flight_number', '999')}"
                                    )
                                )
                                
                                results.append(
                                    FlightLeg(
                                        from_code=seg2.get("origin", {}).get("iata_code", ""),
                                        to_code=seg2.get("destination", {}).get("iata_code", ""),
                                        from_city=_get_place_name(seg2.get("origin")),
                                        to_city=_get_place_name(seg2.get("destination")),
                                        departure=dep_dt2,
                                        arrival=arr_dt2,
                                        price=price2,
                                        carrier=seg2.get("operating_carrier", {}).get("name", "Unknown"),
                                        flight_number=f"{seg2.get('operating_carrier', {}).get('iata_code', 'ZZ')}{seg2.get('flight_number', '999')}"
                                    )
                                )
                    return results

                elif response.status_code == 429:
                    reset_after = response.headers.get("ratelimit-reset")
                    wait_time = float(reset_after) if reset_after else backoff_time
                    print(f"[Duffel Rate Limit 429] Rilevato per la data {date_str}. Tentativo {attempt + 1}/{max_retries}. Attesa di {wait_time:.1f} secondi prima del retry...")
                    time.sleep(wait_time)
                    backoff_time *= 2.0
                    continue
                
                else:
                    print(f"Duffel API Error (Status {response.status_code}) per la data {date_str}: {response.text}")
                    return []

            except Exception as e:
                print(f"Errore di connessione a Duffel per la data {date_str} (Tentativo {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return []
                time.sleep(backoff_time)
                backoff_time *= 2.0

        return []
