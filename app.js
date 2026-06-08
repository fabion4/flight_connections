// Stato Globale dell'Applicazione
let airportsList = [];
let selectedDepCode = "";
let selectedArrCode = "";
let currentResults = [];

// Stato del Filtro Compagnie
let activeCarriers = new Set(); // Set dei carrier attualmente selezionati

// Elementi DOM
const depInput = document.getElementById("departure-input");
const depDropdown = document.getElementById("departure-dropdown");
const clearDepBtn = document.getElementById("clear-dep-btn");

const arrInput = document.getElementById("arrival-input");
const arrDropdown = document.getElementById("arrival-dropdown");
const clearArrBtn = document.getElementById("clear-arr-btn");

const dateStartInput = document.getElementById("departure-date-start");
const dateEndInput = document.getElementById("departure-date-end");
const dateInputText = document.getElementById("departure-date-input");
const dateIconTrigger = document.getElementById("date-icon-trigger");
const calendarDropdown = document.getElementById("calendar-dropdown");
const calendarMonthYear = document.getElementById("calendar-month-year");
const calendarDaysGrid = document.getElementById("calendar-days-grid");
const prevMonthBtn = document.getElementById("prev-month-btn");
const nextMonthBtn = document.getElementById("next-month-btn");

const layoverSlider = document.getElementById("layover-slider");
const layoverVal = document.getElementById("layover-val");

const searchForm = document.getElementById("search-form");
const searchBtn = document.getElementById("search-btn");

const welcomeState = document.getElementById("welcome-state");
const loaderState = document.getElementById("loader-state");
const errorState = document.getElementById("error-state");
const resultsSection = document.getElementById("results-section");
const resultsList = document.getElementById("results-list");

const resultsCount = document.getElementById("results-count");
const bestPriceSpan = document.getElementById("results-best-price");
const exportBtn = document.getElementById("export-btn");

// Elementi DOM Filtro Compagnie
const carrierFilterPanel = document.getElementById("carrier-filter-panel");
const carrierChipsContainer = document.getElementById("carrier-chips");
const filteredCountBadge = document.getElementById("filtered-count");
const selectAllBtn = document.getElementById("select-all-carriers");
const deselectAllBtn = document.getElementById("deselect-all-carriers");

// Stato del Calendario Custom
let calendarCurrentDate = new Date(); // Data correntemente visualizzata sul calendario
let selectedStartDate = null; // Data inizio selezionata dall'utente
let selectedEndDate = null; // Data fine selezionata dall'utente

// Inizializzazione della Pagina
document.addEventListener("DOMContentLoaded", () => {
    // Imposta la data di default a domani e dopodomani
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const afterTomorrow = new Date();
    afterTomorrow.setDate(afterTomorrow.getDate() + 3);
    
    // Imposta lo stato iniziale
    selectedStartDate = tomorrow;
    selectedEndDate = afterTomorrow;
    calendarCurrentDate = new Date(tomorrow);
    
    updateDateInputFields(tomorrow, afterTomorrow);

    // Carica gli aeroporti dal backend
    loadAirports();

    // Carica lo stato del sistema (health status)
    loadSystemStatus();

    // Eventi Slider
    layoverSlider.addEventListener("input", (e) => {
        const val = e.target.value;
        layoverVal.textContent = val + (val == 1 ? " giorno" : " giorni");
    });

    // Registra gli eventi per l'autocomplete
    setupAutocomplete(depInput, depDropdown, clearDepBtn, (code) => { selectedDepCode = code; });
    setupAutocomplete(arrInput, arrDropdown, clearArrBtn, (code) => { selectedArrCode = code; });

    // Gestione Eventi Calendario Custom
    dateInputText.addEventListener("click", toggleCalendar);
    dateIconTrigger.addEventListener("click", toggleCalendar);
    
    prevMonthBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        changeMonth(-1);
    });
    
    nextMonthBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        changeMonth(1);
    });

    // Click al di fuori dei dropdown per chiuderli
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#dep-container")) hideDropdown(depDropdown);
        if (!e.target.closest("#arr-container")) hideDropdown(arrDropdown);
        if (!e.target.closest("#date-container")) hideCalendar();
    });

    // Invio form ricerca
    searchForm.addEventListener("submit", handleSearch);

    // Esportazione Excel
    exportBtn.addEventListener("click", handleExport);

    // Filtro compagnie — Seleziona tutto / Deseleziona tutto
    selectAllBtn.addEventListener("click", () => {
        activeCarriers = new Set(getAllCarriers());
        updateChipsUI();
        applyCarrierFilter();
    });

    deselectAllBtn.addEventListener("click", () => {
        activeCarriers.clear();
        updateChipsUI();
        applyCarrierFilter();
    });
});

// Aggiorna i valori nei campi input reali e visibili
function updateDateInputFields(start, end) {
    if (!start) return;
    
    // Formattazione locale per data inizio
    const startY = start.getFullYear();
    const startM = String(start.getMonth() + 1).padStart(2, '0');
    const startD = String(start.getDate()).padStart(2, '0');
    const startYMD = `${startY}-${startM}-${startD}`;
    dateStartInput.value = startYMD;
    
    if (end) {
        // Formattazione locale per data fine
        const endY = end.getFullYear();
        const endM = String(end.getMonth() + 1).padStart(2, '0');
        const endD = String(end.getDate()).padStart(2, '0');
        const endYMD = `${endY}-${endM}-${endD}`;
        dateEndInput.value = endYMD;
        
        dateInputText.value = `${startD}/${startM}/${startY} - ${endD}/${endM}/${endY}`;
    } else {
        dateEndInput.value = "";
        dateInputText.value = `${startD}/${startM}/${startY} - Scegli fine...`;
    }
}

// Funzioni Calendario Custom
function toggleCalendar(e) {
    e.stopPropagation();
    const dateContainer = document.getElementById("date-container");
    if (calendarDropdown.style.display === "none") {
        renderCalendar();
        calendarDropdown.style.display = "block";
        dateContainer.classList.add("active-picker");
    } else {
        hideCalendar();
    }
}

function hideCalendar() {
    calendarDropdown.style.display = "none";
    const dateContainer = document.getElementById("date-container");
    if (dateContainer) {
        dateContainer.classList.remove("active-picker");
    }
}

function changeMonth(direction) {
    calendarCurrentDate.setMonth(calendarCurrentDate.getMonth() + direction);
    renderCalendar();
}

function renderCalendar() {
    const year = calendarCurrentDate.getFullYear();
    const month = calendarCurrentDate.getMonth();
    
    const monthNames = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ];
    
    calendarMonthYear.textContent = `${monthNames[month]} ${year}`;
    
    calendarDaysGrid.innerHTML = "";
    
    // Calcola il primo giorno del mese (0 = Domenica, 1 = Lunedì... 6 = Sabato)
    let firstDayIndex = new Date(year, month, 1).getDay();
    // Conversione a settimana che inizia da Lunedì (0 = Lunedì ... 6 = Domenica)
    firstDayIndex = firstDayIndex === 0 ? 6 : firstDayIndex - 1;
    
    const totalDays = new Date(year, month + 1, 0).getDate();
    
    // Giorni vuoti prima del primo giorno del mese
    for (let i = 0; i < firstDayIndex; i++) {
        const emptyDiv = document.createElement("div");
        emptyDiv.className = "calendar-day empty";
        calendarDaysGrid.appendChild(emptyDiv);
    }
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Genera i giorni
    for (let dayNum = 1; dayNum <= totalDays; dayNum++) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "calendar-day";
        dayDiv.textContent = dayNum;
        
        const thisDate = new Date(year, month, dayNum);
        
        // Verifica se la data è passata (disabilitata)
        if (thisDate < today) {
            dayDiv.classList.add("disabled");
        } else {
            // Oggi
            if (thisDate.getTime() === today.getTime()) {
                dayDiv.classList.add("today");
            }
            
            // Selezionato (inizio o fine)
            if (selectedStartDate && thisDate.getTime() === selectedStartDate.getTime()) {
                dayDiv.classList.add("selected");
                dayDiv.classList.add("start-date");
            }
            if (selectedEndDate && thisDate.getTime() === selectedEndDate.getTime()) {
                dayDiv.classList.add("selected");
                dayDiv.classList.add("end-date");
            }
            
            // In range (compreso tra inizio e fine)
            if (selectedStartDate && selectedEndDate && thisDate > selectedStartDate && thisDate < selectedEndDate) {
                dayDiv.classList.add("in-range");
            }
            
            dayDiv.addEventListener("click", (e) => {
                e.stopPropagation();
                
                if (!selectedStartDate || (selectedStartDate && selectedEndDate)) {
                    // Reset e seleziona nuova data inizio
                    selectedStartDate = thisDate;
                    selectedEndDate = null;
                    updateDateInputFields(selectedStartDate, null);
                    renderCalendar(); // Ridisegna per mostrare la selezione iniziale
                } else {
                    // C'è già una data d'inizio ma non di fine
                    if (thisDate < selectedStartDate) {
                        // Se clicca una data precedente all'inizio corrente, sposta l'inizio
                        selectedStartDate = thisDate;
                        updateDateInputFields(selectedStartDate, null);
                        renderCalendar();
                    } else {
                        // Imposta la data di fine e chiude il calendario
                        selectedEndDate = thisDate;
                        updateDateInputFields(selectedStartDate, selectedEndDate);
                        hideCalendar();
                    }
                }
            });
        }
        
        calendarDaysGrid.appendChild(dayDiv);
    }
}

// Funzione per caricare gli aeroporti
async function loadAirports() {
    try {
        const response = await fetch("/api/airports");
        if (!response.ok) throw new Error("Errore nel caricamento aeroporti");
        airportsList = await response.json();
    } catch (err) {
        console.error(err);
        showSystemError("Errore del Server", "Impossibile caricare gli aeroporti. Verifica che il backend sia attivo.");
    }
}

// Funzione per caricare lo stato del sistema (Ryanair e Duffel API)
async function loadSystemStatus() {
    const ledRyanair = document.getElementById("led-ryanair");
    const ryanairDesc = document.getElementById("ryanair-desc");
    const ledDuffel = document.getElementById("led-duffel");
    const duffelDesc = document.getElementById("duffel-desc");
    const duffelModeBadge = document.getElementById("duffel-mode-badge");

    try {
        const response = await fetch("/api/status");
        if (!response.ok) throw new Error("Errore nel caricamento dello stato API");
        const status = await response.json();

        // 1. Aggiorna Ryanair
        ledRyanair.className = "status-led"; // Reset classes
        if (status.ryanair.status === "active") {
            ledRyanair.classList.add("led-active");
            ryanairDesc.textContent = status.ryanair.message;
        } else {
            ledRyanair.classList.add("led-error");
            ryanairDesc.textContent = status.ryanair.message || "Errore di connessione";
        }

        // 2. Aggiorna Duffel
        ledDuffel.className = "status-led"; // Reset classes
        if (status.duffel.status === "active") {
            ledDuffel.classList.add("led-active");
            duffelDesc.textContent = status.duffel.message;
        } else if (status.duffel.status === "inactive") {
            ledDuffel.classList.add("led-inactive");
            duffelDesc.textContent = status.duffel.message;
        } else if (status.duffel.status === "error" && status.duffel.message.includes("403")) {
            ledDuffel.classList.add("led-warning"); // Giallo per problemi di permessi
            duffelDesc.textContent = status.duffel.message;
        } else {
            ledDuffel.classList.add("led-error");
            duffelDesc.textContent = status.duffel.message || "Errore API Duffel";
        }

        // Badge della modalità Duffel (Live/Sandbox)
        if (status.duffel.mode && status.duffel.mode !== "none") {
            duffelModeBadge.textContent = status.duffel.mode;
            duffelModeBadge.className = `mode-badge ${status.duffel.mode}`;
            duffelModeBadge.style.display = "inline-block";
        } else {
            duffelModeBadge.style.display = "none";
        }

    } catch (err) {
        console.error(err);
        if (ledRyanair) ledRyanair.className = "status-led led-error";
        if (ryanairDesc) ryanairDesc.textContent = "Errore di connettività backend";
        if (ledDuffel) ledDuffel.className = "status-led led-error";
        if (duffelDesc) duffelDesc.textContent = "Errore di connettività backend";
        if (duffelModeBadge) duffelModeBadge.style.display = "none";
    }
}

// Configurazione della logica di Autocomplete
function setupAutocomplete(inputEl, dropdownEl, clearBtnEl, setSelectionCallback) {
    let debounceTimer = null;

    // Evento Input: debounce 300ms poi fetch dinamico
    inputEl.addEventListener("input", () => {
        const query = inputEl.value.trim();
        if (!query) {
            clearBtnEl.style.display = "none";
            hideDropdown(dropdownEl);
            setSelectionCallback("");
            clearTimeout(debounceTimer);
            return;
        }

        clearBtnEl.style.display = "block";
        setSelectionCallback(""); // Azzera la selezione reale finché non si clicca un elemento

        // Mostra subito "Ricerca in corso..."
        dropdownEl.innerHTML = `<div class="dropdown-item" style="cursor:default;opacity:0.6;">🔍 Ricerca in corso...</div>`;
        showDropdown(dropdownEl);

        // Debounce: aspetta 300ms prima di chiamare il backend
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            try {
                const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
                if (!response.ok) throw new Error("Errore fetch aeroporti");
                const airports = await response.json();
                // Aggiorna anche la lista globale con i nuovi dati per i helper di rendering
                airports.forEach(a => {
                    if (!airportsList.find(x => x.code === a.code)) airportsList.push(a);
                });
                renderDropdownItems(airports, dropdownEl, inputEl, clearBtnEl, setSelectionCallback);
            } catch (err) {
                console.error(err);
                dropdownEl.innerHTML = `<div class="dropdown-item" style="cursor:default;opacity:0.6;">Errore nel caricamento</div>`;
            }
        }, 300);
    });

    // Focus input: se vuoto mostra aeroporti popolari
    inputEl.addEventListener("focus", async () => {
        const query = inputEl.value.trim();
        if (query) {
            // Riesegue la ricerca se c'è già del testo
            inputEl.dispatchEvent(new Event("input"));
        } else {
            // Mostra aeroporti popolari (senza query)
            dropdownEl.innerHTML = `<div class="dropdown-item" style="cursor:default;opacity:0.6;">⭐ Aeroporti popolari</div>`;
            showDropdown(dropdownEl);
            try {
                const response = await fetch("/api/airports");
                if (!response.ok) throw new Error("Errore fetch aeroporti");
                const popular = await response.json();
                // Aggiorna la lista globale
                popular.forEach(a => {
                    if (!airportsList.find(x => x.code === a.code)) airportsList.push(a);
                });
                renderDropdownItems(popular, dropdownEl, inputEl, clearBtnEl, setSelectionCallback);
            } catch (err) {
                hideDropdown(dropdownEl);
            }
        }
    });

    // Pulisci input
    clearBtnEl.addEventListener("click", () => {
        inputEl.value = "";
        clearBtnEl.style.display = "none";
        setSelectionCallback("");
        hideDropdown(dropdownEl);
        clearTimeout(debounceTimer);
        inputEl.focus();
    });
}

function renderDropdownItems(items, dropdownEl, inputEl, clearBtnEl, setSelectionCallback) {
    dropdownEl.innerHTML = "";
    if (items.length === 0) {
        dropdownEl.innerHTML = `<div class="dropdown-item" style="cursor: default; opacity: 0.6;">Nessun aeroporto trovato</div>`;
        showDropdown(dropdownEl);
        return;
    }

    items.forEach(airport => {
        const div = document.createElement("div");
        div.className = "dropdown-item";
        div.innerHTML = `
            <div class="airport-name">${airport.city} (${airport.name})</div>
            <div class="airport-code">${airport.code}</div>
        `;
        const selectItem = (e) => {
            e.preventDefault();
            e.stopPropagation();
            inputEl.value = `${airport.city} (${airport.code})`;
            clearBtnEl.style.display = "block";
            setSelectionCallback(airport.code);
            hideDropdown(dropdownEl);
        };
        div.addEventListener("mousedown", selectItem);
        div.addEventListener("touchstart", selectItem, { passive: false });
        dropdownEl.appendChild(div);
    });

    showDropdown(dropdownEl);
}

function showDropdown(el) { el.style.display = "block"; }
function hideDropdown(el) { el.style.display = "none"; }

// Esecuzione della Ricerca Voli
async function handleSearch() {
    // Validazione
    if (!selectedDepCode) {
        alert("Seleziona un aeroporto di partenza valido dall'elenco.");
        depInput.focus();
        return;
    }
    if (!selectedArrCode) {
        alert("Seleziona un aeroporto di arrivo valido dall'elenco.");
        arrInput.focus();
        return;
    }
    if (selectedDepCode === selectedArrCode) {
        alert("L'aeroporto di partenza e quello di arrivo non possono coincidere.");
        return;
    }

    const dateStart = dateStartInput.value;
    const dateEnd = dateEndInput.value;
    const layover = layoverSlider.value;

    if (!dateStart || !dateEnd) {
        alert("Seleziona un intervallo completo (data di inizio e fine) sul calendario.");
        return;
    }

    // Cambia stato dell'interfaccia (mostra loader, nascondi risultati)
    welcomeState.style.display = "none";
    errorState.style.display = "none";
    resultsSection.style.display = "none";
    loaderState.style.display = "flex";
    resetCarrierFilter(); // Reset filtro compagnie ad ogni nuova ricerca
    
    // Disabilita pulsante
    searchBtn.disabled = true;
    searchBtn.querySelector(".btn-text").textContent = "Cercando...";
    searchBtn.querySelector(".btn-loader").style.display = "block";

    try {
        const queryParams = new URLSearchParams({
            start: selectedDepCode,
            end: selectedArrCode,
            start_date: dateStart,
            end_date: dateEnd,
            max_layover_days: layover
        });
        
        const response = await fetch(`/api/search?${queryParams}`);
        if (!response.ok) throw new Error("Errore del server durante la ricerca.");

        const results = await response.json();
        currentResults = results; // Salviamo per esportazione

        if (results.length === 0) {
            showSystemError("Nessuna connessione trovata ❌", "Non ci sono voli diretti o con scalo disponibili tra questi due aeroporti per la data inserita.");
        } else {
            renderResults(results);
        }
    } catch (err) {
        console.error(err);
        showSystemError("Errore di Connessione ❌", "Si è verificato un errore nel comunicare con il server. Riprova più tardi.");
    } finally {
        // Ripristina pulsante e stato loader
        searchBtn.disabled = false;
        searchBtn.querySelector(".btn-text").textContent = "Cerca Connessioni";
        searchBtn.querySelector(".btn-loader").style.display = "none";
        loaderState.style.display = "none";
    }
}

// ─── FILTRO COMPAGNIE ───────────────────────────────────────────────────────

/** Estrae tutti i carrier unici dalla lista completa dei risultati */
function getAllCarriers() {
    const carriers = new Set();
    currentResults.forEach(r => {
        if (r["First Leg Carrier"] && r["First Leg Carrier"] !== "-") carriers.add(r["First Leg Carrier"]);
        if (r["Second Leg Carrier"] && r["Second Leg Carrier"] !== "-") carriers.add(r["Second Leg Carrier"]);
    });
    return [...carriers].sort();
}

/** Conta quanti risultati sono visibili con il filtro corrente */
function countFilteredResults() {
    return currentResults.filter(r => routeMatchesFilter(r)).length;
}

/** Ritorna true se tutti i carrier del risultato sono nel set attivo */
function routeMatchesFilter(route) {
    const c1 = route["First Leg Carrier"];
    const c2 = route["Second Leg Carrier"];
    
    // Se il primo carrier è presente ma non attivo, escludi la rotta
    if (c1 && c1 !== "-" && !activeCarriers.has(c1)) return false;
    
    // Se il secondo carrier è presente ma non attivo, escludi la rotta
    if (c2 && c2 !== "-" && !activeCarriers.has(c2)) return false;
    
    return true;
}

/** Costruisce i chip delle compagnie e mostra il pannello filtro */
function buildCarrierFilter() {
    const carriers = getAllCarriers();
    if (carriers.length <= 1) {
        // Con una sola compagnia il filtro non serve
        carrierFilterPanel.style.display = "none";
        return;
    }

    // Seleziona tutti di default
    activeCarriers = new Set(carriers);

    // Svuota e ricostruisce i chip
    carrierChipsContainer.innerHTML = "";
    carriers.forEach(carrier => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "carrier-chip active";
        chip.dataset.carrier = carrier;

        // Conta i voli per questa compagnia
        const count = currentResults.filter(r =>
            r["First Leg Carrier"] === carrier || r["Second Leg Carrier"] === carrier
        ).length;

        chip.innerHTML = `<span class="chip-name">${carrier}</span><span class="chip-count">${count}</span>`;
        chip.addEventListener("click", () => toggleCarrier(carrier, chip));
        carrierChipsContainer.appendChild(chip);
    });

    updateFilteredCount();
    carrierFilterPanel.style.display = "block";
}

/** Attiva/disattiva un singolo carrier */
function toggleCarrier(carrier, chipEl) {
    if (activeCarriers.has(carrier)) {
        activeCarriers.delete(carrier);
        chipEl.classList.remove("active");
        chipEl.classList.add("inactive");
    } else {
        activeCarriers.add(carrier);
        chipEl.classList.remove("inactive");
        chipEl.classList.add("active");
    }
    updateFilteredCount();
    applyCarrierFilter();
}

/** Sincronizza lo stato visivo di tutti i chip con activeCarriers */
function updateChipsUI() {
    carrierChipsContainer.querySelectorAll(".carrier-chip").forEach(chip => {
        const carrier = chip.dataset.carrier;
        if (activeCarriers.has(carrier)) {
            chip.classList.add("active");
            chip.classList.remove("inactive");
        } else {
            chip.classList.remove("active");
            chip.classList.add("inactive");
        }
    });
    updateFilteredCount();
}

/** Aggiorna il badge con il conteggio dei risultati filtrati */
function updateFilteredCount() {
    const visible = countFilteredResults();
    const total = currentResults.length;
    if (visible === total) {
        filteredCountBadge.textContent = `${total} risultat${total === 1 ? "o" : "i"}`;
        filteredCountBadge.className = "filtered-count-badge";
    } else {
        filteredCountBadge.textContent = `${visible} / ${total} risultat${total === 1 ? "o" : "i"}`;
        filteredCountBadge.className = "filtered-count-badge filtered-active";
    }
}

/** Applica il filtro corrente e ridisegna la lista */
function applyCarrierFilter() {
    const filtered = currentResults.filter(r => routeMatchesFilter(r));
    renderResults(filtered, /* updateFilter= */ false);
    updateFilteredCount();
}

/** Nasconde e resetta il pannello filtro */
function resetCarrierFilter() {
    activeCarriers.clear();
    carrierChipsContainer.innerHTML = "";
    carrierFilterPanel.style.display = "none";
}

// ────────────────────────────────────────────────────────────────────────────

// Rendering dei Risultati
// updateFilter=true (default) → ricostruisce il pannello carrier; false → solo aggiorna la lista
function renderResults(routes, updateFilter = true) {
    resultsList.innerHTML = "";
    
    // Aggiorna le statistiche in alto
    resultsCount.textContent = `Trovate ${routes.length} connession${routes.length === 1 ? "e" : "i"}`;
    if (routes.length > 0) {
        const bestPrice = routes[0]["Total Price (€)"];
        bestPriceSpan.textContent = `Miglior prezzo: €${bestPrice.toFixed(2)}`;
    } else {
        bestPriceSpan.textContent = "Miglior prezzo: €-";
    }

    // Costruisce/aggiorna il pannello filtro SOLO al primo render (non durante i re-render da filtro)
    if (updateFilter) {
        buildCarrierFilter();
    }


    routes.forEach(route => {
        const isDirect = route["Connection"].includes("Diretto");
        const card = document.createElement("div");
        card.className = `flight-card glass ${isDirect ? "direct" : "connecting"}`;

        // Estraiamo i dettagli delle compagnie e numeri di volo
        const carrier1 = route["First Leg Carrier"] || "Ryanair";
        const fn1 = route["First Leg Flight Number"] || "-";
        
        const carrier2 = route["Second Leg Carrier"] || "-";
        const fn2 = route["Second Leg Flight Number"] || "-";

        // Costruiamo il layout HTML per ciascun volo
        let routeHtml = `
            <div class="flight-type-badge">${isDirect ? "Diretto" : "Scalo"}</div>
            <div class="itinerary-details">
                <!-- Primo Volo (o Volo Diretto) -->
                <div class="flight-segment">
                    <div class="airport-info">
                        <span class="code">${getAirportCityAndCodeEnriched(route["Connection"].split("-")[0].trim(), route["First Leg Origin City"])}</span>
                        <span class="carrier-badge">${carrier1} <small>${fn1}</small></span>
                    </div>
                    <div class="segment-line-container">
                        <span class="duration-label">${route["First Leg Departure"] !== "-" ? "Partenza" : ""}</span>
                        <div class="flight-line">
                            <span class="plane-indicator">✈️</span>
                        </div>
                    </div>
                    <div class="time-info">
                        <span class="time">🛫 ${formatTime(route["First Leg Departure"])}</span>
                        <span class="date">${formatDate(route["First Leg Departure"])}</span>
                    </div>
                    <div class="time-info" style="margin-left: 1rem;">
                        <span class="time">🛬 ${formatTime(route["First Leg Arrival"])}</span>
                        <span class="date">${formatDate(route["First Leg Arrival"])}</span>
                    </div>
                    <div class="airport-info" style="text-align: right;">
                        <span class="code">${getAirportCityAndCodeEnriched(route["Connection"].split("-")[1].split("(")[0].split("|")[0].trim(), route["First Leg Destination City"])}</span>
                    </div>
                </div>
        `;

        // Se c'è uno scalo, aggiungiamo la barra informativa dello scalo e il secondo volo
        if (!isDirect) {
            const layoverHours = route["Layover (h)"];
            const layoverAirport = route["Connection"].split("|")[0].split("-")[1].trim();

            routeHtml += `
                <!-- Barra Scalo -->
                <div class="layover-bar">
                    <span>🕒 Scalo a <strong>${getAirportCityEnriched(layoverAirport, route["First Leg Destination City"])} (${layoverAirport})</strong> per <strong>${layoverHours} ore</strong></span>
                </div>

                <!-- Secondo Volo -->
                <div class="flight-segment">
                    <div class="airport-info">
                        <span class="code">${getAirportCityAndCodeEnriched(layoverAirport, route["Second Leg Origin City"])}</span>
                        <span class="carrier-badge">${carrier2} <small>${fn2}</small></span>
                    </div>
                    <div class="segment-line-container">
                        <span class="duration-label">Coincidenza</span>
                        <div class="flight-line">
                            <span class="plane-indicator">✈️</span>
                        </div>
                    </div>
                    <div class="time-info">
                        <span class="time">🛫 ${formatTime(route["Second Leg Departure"])}</span>
                        <span class="date">${formatDate(route["Second Leg Departure"])}</span>
                    </div>
                    <div class="time-info" style="margin-left: 1rem;">
                        <span class="time">🛬 ${formatTime(route["Second Leg Arrival"])}</span>
                        <span class="date">${formatDate(route["Second Leg Arrival"])}</span>
                    </div>
                    <div class="airport-info" style="text-align: right;">
                        <span class="code">${getAirportCityAndCodeEnriched(route["Connection"].split("|")[1].split("-")[1].trim(), route["Second Leg Destination City"])}</span>
                    </div>
                </div>
            `;
        }

        // Chiusura tag itinerario e container prezzi
        routeHtml += `
            </div>
            <div class="price-container">
                <span class="price">€${route["Total Price (€)"].toFixed(2)}</span>
                <span class="price-subtitle">Totale tasse incluse</span>
                <span class="duration-label" style="margin-top:0.25rem;">Durata totale: ${route["Total Duration (h)"]}h</span>
            </div>
        `;

        card.innerHTML = routeHtml;
        resultsList.appendChild(card);
    });

    resultsSection.style.display = "block";
}

// Helper per ottenere città e codice formattato
function getAirportCityAndCodeEnriched(iataCode, cityName) {
    if (cityName && cityName !== "-") {
        return `${cityName} (${iataCode})`;
    }
    const airport = airportsList.find(a => a.code === iataCode);
    return airport ? `${airport.city} (${iataCode})` : iataCode;
}

function getAirportCityEnriched(iataCode, cityName) {
    if (cityName && cityName !== "-") {
        return cityName;
    }
    const airport = airportsList.find(a => a.code === iataCode);
    return airport ? airport.city : iataCode;
}

// Formattazione Date e Ore
function formatTime(dateTimeStr) {
    if (!dateTimeStr || dateTimeStr === "-") return "-";
    return dateTimeStr.split(" ")[1];
}

function formatDate(dateTimeStr) {
    if (!dateTimeStr || dateTimeStr === "-") return "-";
    const datePart = dateTimeStr.split(" ")[0];
    const [year, month, day] = datePart.split("-");
    return `${day}/${month}/${year}`;
}

// Mostra lo stato di Errore
function showSystemError(title, description) {
    welcomeState.style.display = "none";
    loaderState.style.display = "none";
    resultsSection.style.display = "none";
    
    errorState.querySelector("h3").textContent = title;
    errorState.querySelector("p").textContent = description;
    errorState.style.display = "flex";
}

// Gestione dell'esportazione Excel
async function handleExport() {
    if (currentResults.length === 0) return;

    // Disabilita pulsante
    exportBtn.disabled = true;
    const originalContent = exportBtn.innerHTML;
    exportBtn.innerHTML = `<span>⏳ Generazione...</span>`;

    try {
        const response = await fetch("/api/export", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(currentResults)
        });

        if (!response.ok) throw new Error("Impossibile generare l'esportazione Excel.");

        // Riceviamo il blob binario
        const blob = await response.blob();
        
        // Creiamo un URL temporaneo per far scattare il download nel browser
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = "itinerari_voli_ryanair.xlsx";
        document.body.appendChild(a);
        a.click();
        
        // Pulizia
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
        console.error(err);
        alert("Si è verificato un errore nel download dell'Excel.");
    } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = originalContent;
    }
}
