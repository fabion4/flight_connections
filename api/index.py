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
    from api.flight_search import find_best_routes, get_airports
    from api.duffel_search import find_best_routes_duffel
    from api.utils import save_to_excel_in_memory
except ImportError:
    from flight_search import find_best_routes, get_airports
    from duffel_search import find_best_routes_duffel
    from utils import save_to_excel_in_memory

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
                    # Duffel restituisce sia airports che cities; filtriamo solo airports
                    if place.get("type") == "airport" and place.get("iata_code"):
                        duffel_results.append({
                            "code": place["iata_code"],
                            "name": place.get("name", place["iata_code"]),
                            "city": place.get("city_name", place.get("name", place["iata_code"])),
                            "country": place.get("country_name", "")
                        })
        except Exception:
            pass  # Fallback silenzioso: usiamo solo i risultati Ryanair

    # --- 5. Unione con deduplicazione per codice IATA ---
    seen_codes = set()
    combined = []
    # Prima i risultati Ryanair (hanno priorità)
    for a in ryanair_filtered:
        if a["code"] not in seen_codes:
            seen_codes.add(a["code"])
            combined.append(a)
    # Poi Duffel
    for a in duffel_results:
        if a["code"] not in seen_codes:
            seen_codes.add(a["code"])
            combined.append(a)

    return combined[:20]  # Limita a 20 risultati per leggibilità del dropdown

@app.get("/api/search")
def search_flights(
    start: str = Query(..., description="Codice IATA aeroporto di partenza"),
    end: str = Query(..., description="Codice IATA aeroporto di arrivo"),
    date: str = Query(..., description="Data di partenza (YYYY-MM-DD)"),
    max_layover_days: int = Query(3, ge=1, le=5, description="Tempo massimo di scalo in giorni")
):
    """Cerca le migliori rotte dirette e con 1 scalo per la data specificata (Ryanair + Duffel)."""
    try:
        # Cerca i voli Ryanair
        df_ryanair = find_best_routes(start, end, date, max_layover_days)
        
        # Cerca i voli Duffel (Sandbox/Live)
        df_duffel = find_best_routes_duffel(start, end, date, max_layover_days)
        
        # Uniamo i risultati
        if df_ryanair.empty and df_duffel.empty:
            return []
        elif df_ryanair.empty:
            df_combined = df_duffel
        elif df_duffel.empty:
            df_combined = df_ryanair
        else:
            df_combined = pd.concat([df_ryanair, df_duffel], ignore_index=True)
            
        # Ordina per prezzo totale crescente
        df_combined = df_combined.sort_values(by="Total Price (€)")
        
        # Convertiamo il DataFrame in JSON-friendly
        df_combined = df_combined.replace({"-": None})
        records = df_combined.to_dict(orient="records")
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la ricerca: {str(e)}")

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

