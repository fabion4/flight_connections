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
        "checking_routes": "🔄 Controllando le rotte disponibili...",
        "no_connections": "❌ Nessuna connessione trovata!",
        "connections_found": "✅ {count} connessioni trovate!",
        "download_excel": "📥 Scarica Excel",
        "search_error": "Errore durante la ricerca",
        "error_airports": "Impossibile recuperare l'elenco degli aeroporti",
        "config_options": "Opzioni di configurazione",
        "verify_ssl": "Verifica certificati SSL",
        "currency": "Valuta",
        "feedback_form": "Inviaci i tuoi suggerimenti",
        "feedback_intro": "Aiutaci a migliorare questa applicazione con i tuoi suggerimenti!",
        "feedback_name": "Nome (opzionale)",
        "feedback_email": "Email (opzionale)",
        "feedback_type": "Tipo di feedback",
        "feedback_bug": "Segnalazione bug",
        "feedback_feature": "Suggerimento funzionalità",
        "feedback_other": "Altro",
        "feedback_message": "Il tuo messaggio",
        "submit_feedback": "Invia feedback",
        "feedback_success": "Grazie per il tuo feedback!",
        "feedback_empty": "Per favore, inserisci un messaggio."
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
        "checking_routes": "🔄 Checking available routes...",
        "no_connections": "❌ No connections found!",
        "connections_found": "✅ {count} connections found!",
        "download_excel": "📥 Download Excel",
        "search_error": "Error during search",
        "error_airports": "Unable to retrieve airport list",
        "config_options": "Configuration Options",
        "verify_ssl": "Verify SSL certificates",
        "currency": "Currency",
        "feedback_form": "Send us your suggestions",
        "feedback_intro": "Help us improve this application with your suggestions!",
        "feedback_name": "Name (optional)",
        "feedback_email": "Email (optional)",
        "feedback_type": "Feedback type",
        "feedback_bug": "Bug report",
        "feedback_feature": "Feature suggestion",
        "feedback_other": "Other",
        "feedback_message": "Your message",
        "submit_feedback": "Submit feedback",
        "feedback_success": "Thank you for your feedback!",
        "feedback_empty": "Please enter a message."
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
        "checking_routes": "🔄 Controlende is tratas disponìbiles...",
        "no_connections": "❌ Connessionis no agiòbius!",
        "connections_found": "✅ {count} connessionis agiòbius!",
        "download_excel": "📥 Scariga Excel",
        "search_error": "Errore durante sa chirca",
        "error_airports": "Impossìbile a recuperare sa lista de is aeroportus",
        "config_options": "Optziones de cunfiguratzione",
        "verify_ssl": "Verìfica tzertificadus SSL",
        "currency": "Moneda",
        "feedback_form": "Imbia·nos is suggerimentos tuos",
        "feedback_intro": "Agiuda·nos a megiorare custa aplicatzione cun is suggerimentos tuos!",
        "feedback_name": "Nòmine (optzionale)",
        "feedback_email": "Email (optzionale)",
        "feedback_type": "Tipu de feedback",
        "feedback_bug": "Sinnalu de bug",
        "feedback_feature": "Suggerimentu de funtzionalidade",
        "feedback_other": "Àteru",
        "feedback_message": "Su messaggiu tuo",
        "submit_feedback": "Imbia feedback",
        "feedback_success": "Gràtzias pro su feedback tuo!",
        "feedback_empty": "Pro praghere, inserta unu messaggiu."
    }
}

def get_translation(language, key, **kwargs):
    """Retrieve the translation for a given key and language."""
    # Fallback to English if the language is not supported
    if language not in translations:
        language = "en"
        
    # Fallback to the key itself if the key is not found
    text = translations.get(language, {}).get(key, key)
    
    # Format the text with the provided kwargs
    try:
        return text.format(**kwargs)
    except KeyError as e:
        # Handle missing format parameters
        return f"{text} (Missing format parameter: {e})"
    except Exception:
        # Return the raw text if formatting fails
        return text
