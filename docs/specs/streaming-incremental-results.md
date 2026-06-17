# Spec: Risultati Incrementali in Streaming

- **ID Backlog**: B-05
- **Branch**: `feature/streaming-incremental-results`
- **Stato**: implementato
- **Dipendenze**: nessuna
- **File coinvolti**: `api/index.py`, `app.js`

---

## Obiettivo

Mostrare i risultati Ryanair appena disponibili (circa al 20% della progress bar), senza aspettare il completamento della ricerca Duffel. L'utente vede subito le prime opzioni mentre la ricerca continua in background.

---

## Comportamento atteso

### Flusso eventi (backend → frontend)

```
progress  5%   "Inizializzazione..."
progress  10%  "Ricerca Ryanair..."
progress  20%  "Ryanair completato. N rotte trovate."
partial_results  [connessioni Ryanair ordinate per prezzo]   ← NUOVO
progress  25%  "Ricerca Duffel in corso..." (dalla coda Duffel)
...
progress  95%  "Duffel completato."
progress  96%  "Unione e ordinamento risultati..."
progress  100% "Fatto!"
results   [tutte le connessioni ordinate per prezzo]         ← finale
```

### UX

- Al primo `partial_results`: la sezione risultati **appare** (accordion grouped) mentre il loader rimane visibile in sovrapposizione ridotta (solo progress bar + testo, senza bloccare la vista)
- Al `results` finale: il loader sparisce, i risultati vengono aggiornati con l'elenco completo riordinato (Ryanair + Duffel insieme)
- Se Ryanair trova 0 connessioni, nessun `partial_results` viene inviato e il comportamento rimane invariato
- Il filtro compagnie viene costruito solo al `results` finale (non sui parziali) per evitare rebuild multipli

---

## Modifiche backend (`api/index.py`)

Dopo la riga che emette il progress "Ryanair completato":

```python
# Invia subito i risultati Ryanair parziali (se presenti)
if connections_ryanair:
    partial_records = sorted(
        [c.to_dict() for c in connections_ryanair],
        key=lambda r: r["Total Price (€)"]
    )
    yield json.dumps({"type": "partial_results", "data": partial_records}) + "\n"
```

---

## Modifiche frontend (`app.js`)

Nel loop di lettura dello stream, aggiungere il case `partial_results`:

```javascript
} else if (parsed.type === "partial_results") {
    currentResults = parsed.data;
    renderResults(parsed.data, /* updateFilter= */ false);
    // Mantieni il loader visibile ma in modalità compatta
    loaderState.classList.add("loader-compact");
}
```

Al `results` finale, rimuovere la classe `loader-compact` prima di nascondere il loader.

---

## CSS

```css
/* Loader compatto sovrapposto ai risultati */
.loader-compact {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    width: auto;
    padding: 0.75rem 1rem;
    border-radius: 12px;
    flex-direction: row;
    gap: 0.75rem;
    z-index: 150;
    /* spinner e testo principale nascosti, solo barra + percentuale */
}
.loader-compact .spinner { display: none; }
.loader-compact #loader-text { display: none; }
.loader-compact .progress-bar-container { width: 120px; margin: 0; }
```

---

## Cosa NON cambia

- Schema dati output (invariante)
- Logica di raggruppamento accordion
- Filtro compagnie (rebuild solo al `results` finale)
- Export Excel (usa sempre `currentResults` aggiornato)
