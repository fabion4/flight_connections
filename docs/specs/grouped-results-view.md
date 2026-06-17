# Spec: Vista Sintetica Risultati con Espansione per Rotta

- **ID Backlog**: B-08
- **Branch**: `feature/results-grouped-by-route`
- **Stato**: da iniziare
- **Dipendenze**: nessuna (tutto lato frontend)
- **File coinvolti**: `app.js`, `style.css` — nessuna modifica backend

---

## Obiettivo

Raggruppare i risultati di ricerca per coppia di rotta (campo `Connection`), offrendo:
1. **Pannello laterale sintetico** — indice delle rotte con range di prezzo e checkbox di filtro
2. **Lista principale ad accordion** — ogni gruppo è collassato di default, espandibile per vedere le singole opzioni di orario

---

## Comportamento atteso

### Stato iniziale dopo la ricerca
- Il pannello laterale appare a sinistra della lista risultati
- Tutti i gruppi nell'accordion sono **collassati** di default
- Tutte le checkbox nel pannello sono **selezionate** (tutti i gruppi visibili)
- I gruppi sono ordinati per **prezzo minimo crescente**

### Pannello laterale
Ogni riga del pannello mostra:
```
☑  OLB → KRW → CIA    €50 – €60   (3)
☑  OLB → PAL → CIA    €54         (1)
☑  OLB → FCO          €89 – €120  (5)  ← volo diretto
```
- `☑` checkbox: deselezionare nasconde il gruppo dalla lista principale
- Range prezzo: min€ – max€ (se min == max mostra solo il valore)
- `(n)` numero di opzioni nel gruppo
- Click sulla riga (non sulla checkbox) → scrolla alla sezione nella lista e la espande

### Lista principale — accordion
Ogni gruppo ha un header e un body collassabile:

**Header (sempre visibile)**:
```
▶  OLB → KRW → CIA     3 opzioni     da €50
```
Click sull'header → espande/collassa il body

**Body (espanso)**:
Le card volo esistenti, invariate nel formato, ordinate per prezzo crescente.

---

## Layout

### Desktop
```
┌─────────────────┬──────────────────────────────────────┐
│  ROTTE (n)      │  RISULTATI                           │
│                 │                                      │
│ ☑ OLB-KRW-CIA  │  ▶ OLB → KRW → CIA  3 opt  da €50  │
│   €50–€60 (3)  │                                      │
│                 │  ▶ OLB → PAL → CIA  1 opt  da €54  │
│ ☑ OLB-PAL-CIA  │                                      │
│   €54    (1)   │  ▼ OLB → FCO        5 opt  da €89  │
│                 │    ┌──────────────────────────────┐  │
│ ☑ OLB-FCO      │    │ card volo 1                  │  │
│   €89–€120 (5) │    │ card volo 2                  │  │
│                 │    │ ...                          │  │
│ Seleziona tutti │    └──────────────────────────────┘  │
│ Deseleziona     │                                      │
└─────────────────┴──────────────────────────────────────┘
```
Larghezza pannello: `220px` fissa, lista occupa il resto.

### Mobile (< 768px)
Il pannello laterale si nasconde. Appare un bottone `☰ Filtra rotte` in cima ai risultati che apre il pannello come overlay/drawer dal basso. La lista usa l'accordion invariata.

---

## Specifiche tecniche

### Struttura dati JS (groupBy)
```javascript
// Da generare da results[] dopo la ricerca
const groups = {};
results.forEach(r => {
    const key = r.Connection;
    if (!groups[key]) groups[key] = { connections: [], minPrice: Infinity, maxPrice: -Infinity };
    groups[key].connections.push(r);
    groups[key].minPrice = Math.min(groups[key].minPrice, r["Total Price (€)"]);
    groups[key].maxPrice = Math.max(groups[key].maxPrice, r["Total Price (€)"]);
});
// Ordina per minPrice
const sortedGroups = Object.entries(groups).sort((a, b) => a[1].minPrice - b[1].minPrice);
```

### Rendering pannello
- Contenitore: `<div id="route-panel">` con `position: sticky; top: 1rem`
- Scroll indipendente dalla lista: `overflow-y: auto; max-height: calc(100vh - 200px)`
- Bottoni "Seleziona tutti" / "Deseleziona tutti" in fondo al pannello

### Rendering accordion
- Ogni gruppo: `<div class="route-group" data-route="OLB-KRW-CIA">`
- Header: `<div class="route-group-header">` con freccia rotante via CSS transform
- Body: `<div class="route-group-body">` con `max-height: 0; overflow: hidden` collassato, animazione CSS su espansione
- Nessun framework: toggle class `expanded` via JS

### Interazione pannello → lista
Click su riga pannello:
1. Espande il gruppo corrispondente nella lista (se collassato)
2. `scrollIntoView({ behavior: 'smooth', block: 'start' })`

### Interazione checkbox → lista
`change` sulla checkbox:
- Deselezionata → `route-group` corrispondente: `display: none`
- Riselezionata → `display: block`

### Compatibilità con filtro compagnia esistente
Il filtro compagnia attuale agisce sulle singole card. Con i gruppi, una card nascosta dal filtro compagnia non deve far sparire l'intero gruppo — solo quella card. Se tutte le card di un gruppo sono nascoste, nascondere anche l'header del gruppo.

---

## CSS da aggiungere

```css
/* Layout split */
#results-container { display: flex; gap: 1rem; align-items: flex-start; }
#route-panel { width: 220px; flex-shrink: 0; position: sticky; top: 1rem; ... }
#results-list { flex: 1; min-width: 0; }

/* Accordion */
.route-group-header { cursor: pointer; display: flex; justify-content: space-between; ... }
.route-group-header .arrow { transition: transform 0.2s; }
.route-group.expanded .arrow { transform: rotate(90deg); }
.route-group-body { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
.route-group.expanded .route-group-body { max-height: 9999px; }

/* Pannello */
.panel-route-row { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; ... }
.panel-route-row:hover { background: rgba(255,255,255,0.05); }
```

---

## Cosa NON cambia
- Formato delle card volo esistenti
- Logica di ricerca e streaming
- Filtro per compagnia aerea (rimane, agisce sulle card dentro i gruppi)
- Export Excel (esporta tutti i risultati, indipendentemente dallo stato accordion)

---

## Ordine di implementazione consigliato

1. Funzione `groupResults(results)` → struttura dati gruppi
2. Rendering accordion nella lista principale (senza pannello)
3. Rendering pannello laterale
4. Collegamento pannello → accordion (click + scroll)
5. Collegamento checkbox → visibilità gruppi
6. Compatibilità filtro compagnia esistente
7. Comportamento mobile (drawer)
