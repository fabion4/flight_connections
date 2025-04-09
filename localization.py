translations = {
    "it": {
        "title": "Trova il volo più economico ✈️",
        "select_departure": "Seleziona aeroporto di partenza",
        "select_arrival": "Seleziona aeroporto di arrivo",
        "departure_date": "Data di partenza:",
        "max_layover": "Tempo massimo di scalo (giorni):",
        "search_flights": "Cerca voli",
        "searching": "🔍 Cercando i voli migliori...",
        "no_connections": "❌ Nessuna connessione trovata!",
        "connections_found": "✅ {count} connessioni trovate!",
        "download_excel": "📥 Scarica Excel"
    },
    "en": {
        "title": "Find the cheapest flight ✈️",
        "select_departure": "Select departure airport",
        "select_arrival": "Select arrival airport",
        "departure_date": "Departure date:",
        "max_layover": "Maximum layover time (days):",
        "search_flights": "Search flights",
        "searching": "🔍 Searching for the best flights...",
        "no_connections": "❌ No connections found!",
        "connections_found": "✅ {count} connections found!",
        "download_excel": "📥 Download Excel"
    },
    "sc": {
        "title": "Tròva su bigliettu prusòriu ✈️",
        "select_departure": "Seleziona aeroportu de partenza",
        "select_arrival": "Seleziona aeroportu de arrivo",
        "departure_date": "Data de partenza:",
        "max_layover": "Tempu màssimu de scalu (dies):",
        "search_flights": "Chirca bigliettus",
        "searching": "🔍 Chirchende is bigliettus mègius...",
        "no_connections": "❌ Connessionis no agiòbius!",
        "connections_found": "✅ {count} connessionis agiòbius!",
        "download_excel": "📥 Scariga Excel"
    }
}

def get_translation(language, key, **kwargs):
    """Retrieve the translation for a given key and language."""
    text = translations.get(language, {}).get(key, key)
    return text.format(**kwargs)