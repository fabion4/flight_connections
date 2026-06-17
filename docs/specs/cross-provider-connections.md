# Spec: Connessioni Cross-Provider

- **ID Backlog**: B-14
- **Branch**: `feature/cross-provider-connections`
- **Stato**: implementato
- **Dipendenze**: B-01 (architettura api-agnostic)
- **File coinvolti**: `api/router.py`, `api/providers/ryanair.py`, `api/index.py`

---

## Problema

Il router accettava un singolo provider: ogni chiamata usava Ryanair O Duffel per entrambe le tratte. Connessioni ibride (primo volo Ryanair + secondo volo Duffel, o viceversa) erano impossibili — paradossale per un servizio che promuove il city break multi-giorno.

---

## Soluzione

### `router.py` — firma multi-provider

```python
# PRIMA
find_connections(provider, start, end, dates, max_layover_h, ...)

# DOPO
find_connections(providers_with_dates, start, end, max_layover_h, ...)
# providers_with_dates: list[tuple[FlightProvider, list[str]]]
```

La funzione unisce destinazioni e voli da **tutti i provider**. Il prodotto cartesiano `(first_legs × second_legs)` include automaticamente combinazioni cross-provider.

### `ryanair.py` — cache in-memory per istanza

`get_destinations` e `get_flights` memorizzano le risposte su dizionari dell'istanza. Permette di riutilizzare la stessa istanza `RyanairProvider` nella ricerca parziale e in quella combinata finale senza doppi HTTP.

### `index.py` — flusso aggiornato

```
1. Crea ryanair_provider (istanza unica)
2. find_connections([(ryanair_provider, dates_ryanair)]) → partial_results
3. Thread Duffel: crea duffel_provider, popola cache, salva riferimento
4. find_connections([(ryanair_provider, dates_ryanair),
                     (duffel_provider, dates_duffel)]) → risultati finali
   ↳ Ryanair: da cache (istantaneo)
   ↳ Duffel: da cache (istantaneo)
   ↳ Cross: primo volo da un provider, secondo dall'altro
```

---

## Cosa NON cambia

- Formato output (schema dati invariante)
- Provider Protocol (nessuna modifica a `base.py` o `duffel.py`)
- Logica di deduplica flight legs nel router
- Frontend (nessuna modifica)
