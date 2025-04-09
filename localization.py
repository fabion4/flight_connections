translations = {
    "it": {
        "title": "Trova il volo più economico ✈️",
        "intro_text": "Questa applicazione ti aiuta a trovare i voli più economici tra due aeroporti. Seleziona gli aeroporti di partenza e arrivo, il mese di partenza e il tempo massimo di scalo per iniziare la ricerca.",
        "select_departure": "Seleziona aeroporto di partenza",
        "select_arrival": "Seleziona aeroporto di arrivo",
        "departure_date": "Seleziona il mese di partenza:",
        "max_layover": "Tempo massimo di scalo (giorni):",
        "search_flights": "Cerca voli",
        "searching": "🔍 Cercando i voli migliori...",
        "no_connections": "❌ Nessuna connessione trovata!",
        "connections_found": "✅ {count} connessioni trovate!",
        "download_excel": "📥 Scarica Excel"
    },
    "en": {
        "title": "Find the cheapest flight ✈️",
        "intro_text": "This application helps you find the cheapest flights between two airports. Select the departure and arrival airports, the departure month, and the maximum layover time to start your search.",
        "select_departure": "Select departure airport",
        "select_arrival": "Select arrival airport",
        "departure_date": "Select the departure month:",
        "max_layover": "Maximum layover time (days):",
        "search_flights": "Search flights",
        "searching": "🔍 Searching for the best flights...",
        "no_connections": "❌ No connections found!",
        "connections_found": "✅ {count} connections found!",
        "download_excel": "📥 Download Excel"
    },
    "sc": {
        "title": "Tròva su bigliettu prusòriu ✈️",
        "intro_text": "Cust'applicatzioni ti agiudat a tròvai is bigliettus prusòrius tra duus aeroportus. Seleziona is aeroportus de partenza e arrivu, su mese de partenza e su tempu màssimu de scalu pro cumintzai sa chirca.",
        "select_departure": "Seleziona aeroportu de partenza",
        "select_arrival": "Seleziona aeroportu de arrivo",
        "departure_date": "Seleziona su mese de partenza:",
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