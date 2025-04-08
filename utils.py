import pandas as pd

def save_to_excel(df, filename="flights.xlsx"):
    """Salva il DataFrame in un file Excel."""
    df.to_excel(filename, index=False)
    return filename

def get_airport_choices(airports):
    airport_choices = []
    for airport in airports:
        airport_choices.append((airport["iataCode"], airport["name"]))
    return airport_choices
