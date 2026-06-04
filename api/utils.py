import pandas as pd
import io

def save_to_excel_in_memory(df):
    """Salva il DataFrame in un buffer Excel in memoria (BytesIO) per compatibilità serverless."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Connessioni Voli")
    output.seek(0)
    return output

def get_airport_choices(airports):
    """Estrae codice IATA e nome degli aeroporti."""
    airport_choices = []
    for airport in airports:
        airport_choices.append((airport["iataCode"], airport["name"]))
    return airport_choices
