from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import pandas as pd

# Caricamento variabili d'ambiente per sviluppo locale
from dotenv import load_dotenv
load_dotenv()

# Import robusti per supportare sia l'esecuzione locale che Vercel Serverless
try:
    from api.providers.ryanair import RyanairProvider, get_airports
    from api.providers.duffel import DuffelProvider
    from api.router import find_connections
    from api.utils import save_to_excel_in_memory
    from api.city_groups import CITY_GROUPS, METRO_GROUPS, AIRPORT_TO_METRO
except ImportError:
    from providers.ryanair import RyanairProvider, get_airports
    from providers.duffel import DuffelProvider
    from router import find_connections
    from utils import save_to_excel_in_memory
    from city_groups import CITY_GROUPS, METRO_GROUPS, AIRPORT_TO_METRO

app = FastAPI(title="Flight Connection API", description="API per la ricerca di voli e connessioni Ryanair e Duffel")

# Configurazione CORS per sviluppo locale su porte differenti
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- ENDPOINTS API -----------------

import requests as http_requests

@app.get("/api/status")
def get_status():
    status_ryanair = {"status": "unknown", "message": ""}
    status_duffel = {"status": "unknown", "message": "", "mode": "none"}
    
    # 1. Check Ryanair
    try:
        airports = get_airports()
        if airports:
            status_ryanair["status"] = "active"
            status_ryanair["message"] = f"Connesso con successo ({len(airports)} aeroporti attivi)"
        else:
            status_ryanair["status"] = "error"
            status_ryanair["message"] = "Nessun dato restituito dall'API Ryanair"
    except Exception as e:
        status_ryanair["status"] = "error"
        status_ryanair["message"] = f"Errore di connessione: {str(e)}"

    # 2. Check Duffel
    duffel_token = os.getenv("DUFFEL_ACCESS_TOKEN")
    if not duffel_token:
        status_duffel["status"] = "inactive"
        status_duffel["message"] = "Nessun token Duffel configurato nel file .env"
    else:
        if duffel_token.startswith("duffel_live_"):
            status_duffel["mode"] = "live"
        elif duffel_token.startswith("duffel_test_"):
            status_duffel["mode"] = "sandbox"
        else:
            status_duffel["mode"] = "custom"
            
        try:
            url = "https://api.duffel.com/air/airlines"
            headers = {
                "Authorization": f"Bearer {duffel_token}",
                "Duffel-Version": "v2",
                "Accept": "application/json"
            }
            res = http_requests.get(url, params={"limit": 1}, headers=headers)
            
            if res.status_code == 200:
                status_duffel["status"] = "active"
                status_duffel["message"] = "Token valido e connessione a Duffel attiva"
            elif res.status_code == 401:
                status_duffel["status"] = "error"
                status_duffel["message"] = "Token non valido o scaduto (401 Unauthorized)"
            elif res.status_code == 403:
                status_duffel["status"] = "error"
                status_duffel["message"] = "Permessi insufficienti (403 Forbidden). Verifica che sia Read-Write"
            else:
                status_duffel["status"] = "error"
                status_duffel["message"] = f"Errore API Duffel (Stato {res.status_code})"
        except Exception as e:
            status_duffel["status"] = "error"
            status_duffel["message"] = f"Errore di connettività: {str(e)}"
            
    return {
        "ryanair": status_ryanair,
        "duffel": status_duffel
    }

@app.get("/api/airports")
def read_airports(q: Optional[str] = Query(None, description="Query di ricerca aeroporto/città/codice IATA")):
    """Recupera aeroporti con ricerca dinamica. Senza query restituisce i 30 più popolari da Ryanair.
    Con query filtra Ryanair localmente e interroga Duffel Places API per risultati globali."""

    # --- 1. Carica e formatta gli aeroporti Ryanair ---
    ryanair_raw = get_airports()
    ryanair_all = []
    for a in (ryanair_raw or []):
        if "iataCode" in a and "name" in a:
            ryanair_all.append({
                "code": a["iataCode"],
                "name": a["name"],
                "city": a.get("city", {}).get("name", a["name"]),
                "country": a.get("country", {}).get("name", "")
            })

    # --- 2. Nessuna query: restituisce i primi 30 aeroporti Ryanair ("popolari") ---
    if not q or not q.strip():
        ryanair_all.sort(key=lambda x: x["name"])
        return ryanair_all[:30]

    # --- 3. Con query: filtra Ryanair localmente ---
    query_lower = q.strip().lower()
    ryanair_filtered = [
        a for a in ryanair_all
        if query_lower in a["name"].lower()
        or query_lower in a["city"].lower()
        or query_lower in a["code"].lower()
        or query_lower in a["country"].lower()
    ]

    # --- 4. Interroga Duffel Places API ---
    duffel_results = []
    duffel_token = os.getenv("DUFFEL_ACCESS_TOKEN")
    if duffel_token:
        try:
            url = "https://api.duffel.com/places/suggestions"
            headers = {
                "Authorization": f"Bearer {duffel_token}",
                "Duffel-Version": "v2",
                "Accept": "application/json"
            }
            res = http_requests.get(url, params={"query": q.strip()}, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                for place in data:
                    iata = place.get("iata_code", "")
                    # Escludiamo city/metro codes (es. RMA, LON) che non sono aeroporti reali
                    if place.get("type") == "airport" and iata and iata not in CITY_GROUPS:
                        duffel_results.append({
                            "code": iata,
                            "name": place.get("name", iata),
                            "city": place.get("city_name", place.get("name", iata)),
                            "country": place.get("country_name", "")
                        })
        except Exception:
            pass  # Fallback silenzioso: usiamo solo i risultati Ryanair

    # --- 5. Unione con deduplicazione per codice IATA ---
    seen_codes = set()
    flat = []
    for a in ryanair_filtered:
        if a["code"] not in seen_codes:
            seen_codes.add(a["code"])
            flat.append(a)
    for a in duffel_results:
        if a["code"] not in seen_codes:
            seen_codes.add(a["code"])
            flat.append(a)

    # --- 6. Raggruppa aeroporti dello stesso metro in sottoalbero ---
    result = []
    added_codes = set()
    added_metros = set()

    for a in flat:
        metro = AIRPORT_TO_METRO.get(a["code"])
        if metro and metro not in added_metros:
            # Inserisce prima l'header del gruppo
            info = METRO_GROUPS[metro]
            result.append({
                "code": metro,
                "name": info["label"],
                "city": info["city"],
                "country": info["country"],
                "group": info["airports"]
            })
            added_metros.add(metro)
            # Inserisce subito dopo tutti gli aeroporti del gruppo presenti in flat
            for child_code in info["airports"]:
                child = next((x for x in flat if x["code"] == child_code), None)
                if child and child_code not in added_codes:
                    child["parent_group"] = metro
                    result.append(child)
                    added_codes.add(child_code)
        elif a["code"] not in added_codes:
            result.append(a)
            added_codes.add(a["code"])

    return result[:25]  # Limite leggermente più alto per accomodare gli header gruppo

def _generate_monthly_dates(start_date: str, end_date: str) -> list[str]:
    from datetime import datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    months = []
    curr = start_dt
    while curr <= end_dt:
        month_first_day = curr.replace(day=1)
        month_str = month_first_day.strftime("%Y-%m-%d")
        if month_str not in months:
            months.append(month_str)
        if curr.month == 12:
            curr = curr.replace(year=curr.year + 1, month=1, day=1)
        else:
            curr = curr.replace(month=curr.month + 1, day=1)
    return months

def _generate_daily_dates(start_date: str, end_date: str) -> list[str]:
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    delta_days = (end_dt - start_dt).days
    if delta_days < 0:
        return []
    elif delta_days > 29:
        end_dt = start_dt + timedelta(days=29)
    
    dates = []
    curr = start_dt
    while curr <= end_dt:
        dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return dates

@app.get("/api/search")
def search_flights(
    start: str = Query(..., description="Codice IATA aeroporto di partenza"),
    end: str = Query(..., description="Codice IATA aeroporto di arrivo"),
    start_date: str = Query(..., description="Data di partenza iniziale (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data di partenza finale (YYYY-MM-DD)"),
    max_layover_days: int = Query(3, ge=1, le=5, description="Tempo massimo di scalo in giorni")
):
    """Cerca le migliori rotte dirette e con 1 scalo per il range di date specificato (Ryanair + Duffel) con aggiornamenti di progresso in tempo reale."""
    import json
    import queue
    import threading

    def generate():
        try:
            print(f"\n[Search Stream] Richiesta ricevuta: {start} -> {end} dal {start_date} al {end_date} (Max scalo: {max_layover_days}gg)")
            
            # 1. Ricerca Ryanair (istanza unica — dati cached per la chiamata combinata finale)
            yield json.dumps({"type": "progress", "percent": 5, "message": "Inizializzazione ricerca..."}) + "\n"
            yield json.dumps({"type": "progress", "percent": 10, "message": "Ricerca connessioni Ryanair in corso..."}) + "\n"

            dates_ryanair = _generate_monthly_dates(start_date, end_date)
            ryanair_provider = RyanairProvider()
            connections_ryanair = find_connections(
                [(ryanair_provider, dates_ryanair)],
                start, end, max_layover_days * 24,
                filter_start=start_date, filter_end=end_date
            )
            print(f"[Search Stream] Ryanair ha completato con {len(connections_ryanair)} combinazioni.")
            yield json.dumps({"type": "progress", "percent": 20, "message": f"Ryanair completato. Trovate {len(connections_ryanair)} rotte."}) + "\n"

            # Invia subito i risultati Ryanair mentre Duffel parte
            if connections_ryanair:
                partial_records = [c.to_dict() for c in connections_ryanair]
                yield json.dumps({"type": "partial_results", "data": partial_records}) + "\n"

            # 2. Ricerca Duffel con coda sincronizzata — salva riferimento al provider per la chiamata combinata
            q = queue.Queue()
            dates_duffel = _generate_daily_dates(start_date, end_date)
            duffel_provider_ref = []

            def duffel_progress_callback(percent, message):
                q.put({"type": "progress", "percent": percent, "message": message})

            def run_duffel_thread():
                try:
                    provider = DuffelProvider(start, end, dates_duffel, progress_callback=duffel_progress_callback)
                    # Esegue la ricerca Duffel-only per popolare il cache interno del provider
                    find_connections(
                        [(provider, dates_duffel)],
                        start, end, max_layover_days * 24,
                        filter_start=start_date, filter_end=end_date
                    )
                    duffel_provider_ref.append(provider)
                except Exception as ex:
                    print(f"[Search Stream] Errore Duffel thread: {ex}")
                    q.put({"type": "error", "message": str(ex)})
                finally:
                    q.put(None)

            t = threading.Thread(target=run_duffel_thread)
            t.start()

            while True:
                item = q.get()
                if item is None:
                    break
                if item.get("type") == "error":
                    yield json.dumps({"type": "progress", "percent": 90, "message": f"Duffel non disponibile: {item['message']}"}) + "\n"
                else:
                    yield json.dumps(item) + "\n"

            t.join()

            # 3. Ricerca combinata cross-provider (entrambi i provider usano il proprio cache — nessuna nuova HTTP)
            yield json.dumps({"type": "progress", "percent": 96, "message": "Ricerca connessioni cross-provider..."}) + "\n"

            providers_for_combined = [(ryanair_provider, dates_ryanair)]
            if duffel_provider_ref:
                providers_for_combined.append((duffel_provider_ref[0], dates_duffel))
                print(f"[Search Stream] Avvio ricerca combinata con {len(providers_for_combined)} provider.")
            else:
                print("[Search Stream] Duffel non disponibile — risultati solo Ryanair.")

            combined_connections = find_connections(
                providers_for_combined,
                start, end, max_layover_days * 24,
                filter_start=start_date, filter_end=end_date
            )
            records = [c.to_dict() for c in combined_connections]

            yield json.dumps({"type": "progress", "percent": 100, "message": "Fatto!"}) + "\n"
            yield json.dumps({"type": "results", "data": records}) + "\n"
            print(f"[Search Stream] Risultati totali inviati: {len(records)}\n")
            
        except Exception as e:
            print(f"[Search Stream ERROR] Errore: {str(e)}")
            yield json.dumps({"type": "error", "message": f"Errore ricerca: {str(e)}"}) + "\n"
            
    return StreamingResponse(generate(), media_type="application/x-ndjson")

# Modello dati per l'esportazione in Excel
class FlightRecord(BaseModel):
    Connection: str
    First_Leg_Departure: Optional[str] = Query(None, alias="First Leg Departure")
    First_Leg_Arrival: Optional[str] = Query(None, alias="First Leg Arrival")
    First_Leg_Carrier: Optional[str] = Query(None, alias="First Leg Carrier")
    First_Leg_Flight_Number: Optional[str] = Query(None, alias="First Leg Flight Number")
    Second_Leg_Departure: Optional[str] = Query(None, alias="Second Leg Departure")
    Second_Leg_Arrival: Optional[str] = Query(None, alias="Second Leg Arrival")
    Second_Leg_Carrier: Optional[str] = Query(None, alias="Second Leg Carrier")
    Second_Leg_Flight_Number: Optional[str] = Query(None, alias="Second Leg Flight Number")
    Layover_h: Optional[float] = Query(None, alias="Layover (h)")
    Total_Duration_h: Optional[float] = Query(None, alias="Total Duration (h)")
    Total_Price_EUR: Optional[float] = Query(None, alias="Total Price (€)")

    class Config:
        populate_by_name = True

@app.post("/api/export")
def export_to_excel(flights: List[FlightRecord]):
    """Genera ed esporta un file Excel a partire dai voli passati in formato JSON."""
    if not flights:
        raise HTTPException(status_code=400, detail="Nessun dato fornito per l'esportazione")
    
    try:
        # Convertiamo la lista di record Pydantic in DataFrame
        data = []
        for f in flights:
            data.append({
                "Connection": f.Connection,
                "First Leg Departure": f.First_Leg_Departure or "-",
                "First Leg Arrival": f.First_Leg_Arrival or "-",
                "First Leg Carrier": f.First_Leg_Carrier or "-",
                "First Leg Flight Number": f.First_Leg_Flight_Number or "-",
                "Second Leg Departure": f.Second_Leg_Departure or "-",
                "Second Leg Arrival": f.Second_Leg_Arrival or "-",
                "Second Leg Carrier": f.Second_Leg_Carrier or "-",
                "Second Leg Flight Number": f.Second_Leg_Flight_Number or "-",
                "Layover (h)": f.Layover_h if f.Layover_h is not None else 0,
                "Total Duration (h)": f.Total_Duration_h if f.Total_Duration_h is not None else 0,
                "Total Price (€)": f.Total_Price_EUR
            })
        
        df = pd.DataFrame(data)
        
        # Generiamo il file in memoria
        excel_buffer = save_to_excel_in_memory(df)
        
        # Restituiamo il file Excel come StreamingResponse per il download
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=voli_trovati.xlsx",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la generazione dell'Excel: {str(e)}")

# ----------------- SERVIZIO FILE STATICI IN LOCALE -----------------
# Serve il frontend in locale. Su Vercel questa parte viene saltata 
# perché le regole in vercel.json gestiscono il routing dei file statici.
root_path = os.path.dirname(os.path.dirname(__file__))
if os.path.exists(root_path):
    app.mount("/", StaticFiles(directory=root_path, html=True), name="static")

