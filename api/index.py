from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import pandas as pd

# Import robusti per supportare sia l'esecuzione locale che Vercel Serverless
try:
    from api.flight_search import find_best_routes, get_airports
    from api.utils import save_to_excel_in_memory
except ImportError:
    from flight_search import find_best_routes, get_airports
    from utils import save_to_excel_in_memory

app = FastAPI(title="Flight Connection API", description="API per la ricerca di voli e connessioni Ryanair")

# Configurazione CORS per sviluppo locale su porte differenti
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- ENDPOINTS API -----------------

@app.get("/api/airports")
def read_airports():
    """Recupera la lista degli aeroporti attivi da Ryanair."""
    airports = get_airports()
    if not airports:
        raise HTTPException(status_code=500, detail="Impossibile recuperare gli aeroporti da Ryanair")
    
    # Formattiamo la risposta ordinando gli aeroporti per nome
    result = []
    for a in airports:
        if "iataCode" in a and "name" in a:
            result.append({
                "code": a["iataCode"],
                "name": a["name"],
                "city": a.get("city", {}).get("name", a["name"]),
                "country": a.get("country", {}).get("name", "")
            })
    result.sort(key=lambda x: x["name"])
    return result

@app.get("/api/search")
def search_flights(
    start: str = Query(..., description="Codice IATA aeroporto di partenza"),
    end: str = Query(..., description="Codice IATA aeroporto di arrivo"),
    date: str = Query(..., description="Data di partenza (YYYY-MM-DD)"),
    max_layover_days: int = Query(3, ge=1, le=5, description="Tempo massimo di scalo in giorni")
):
    """Cerca le migliori rotte dirette e con 1 scalo per la data specificata."""
    try:
        df = find_best_routes(start, end, date, max_layover_days)
        if df.empty:
            return []
        
        # Convertiamo il DataFrame in una lista di dizionari JSON-friendly
        # Sostituiamo i valori NaN o '-' con None o stringhe pulite
        df = df.replace({"-": None})
        records = df.to_dict(orient="records")
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la ricerca: {str(e)}")

# Modello dati per l'esportazione in Excel
class FlightRecord(BaseModel):
    Connection: str
    First_Leg_Departure: Optional[str] = Query(None, alias="First Leg Departure")
    First_Leg_Arrival: Optional[str] = Query(None, alias="First Leg Arrival")
    Second_Leg_Departure: Optional[str] = Query(None, alias="Second Leg Departure")
    Second_Leg_Arrival: Optional[str] = Query(None, alias="Second Leg Arrival")
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
                "Second Leg Departure": f.Second_Leg_Departure or "-",
                "Second Leg Arrival": f.Second_Leg_Arrival or "-",
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

