// Stato Globale dell'Applicazione
let airportsList = [];
let selectedDepCode = "";
let selectedArrCode = "";
let currentResults = [];

// Elementi DOM
const depInput = document.getElementById("departure-input");
const depDropdown = document.getElementById("departure-dropdown");
const clearDepBtn = document.getElementById("clear-dep-btn");

const arrInput = document.getElementById("arrival-input");
const arrDropdown = document.getElementById("arrival-dropdown");
const clearArrBtn = document.getElementById("clear-arr-btn");

const dateInput = document.getElementById("departure-date");
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

// Inizializzazione della Pagina
document.addEventListener("DOMContentLoaded", () => {
    // Imposta la data di default a domani
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    dateInput.value = tomorrow.toISOString().split("T")[0];
    dateInput.min = new Date().toISOString().split("T")[0]; // Impedisce date passate

    // Carica gli aeroporti dal backend
    loadAirports();

    // Eventi Slider
    layoverSlider.addEventListener("input", (e) => {
        const val = e.target.value;
        layoverVal.textContent = val + (val == 1 ? " giorno" : " giorni");
    });

    // Registra gli eventi per l'autocomplete
    setupAutocomplete(depInput, depDropdown, clearDepBtn, (code) => { selectedDepCode = code; });
    setupAutocomplete(arrInput, arrDropdown, clearArrBtn, (code) => { selectedArrCode = code; });

    // Click al di fuori dei dropdown per chiuderli
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#dep-container")) hideDropdown(depDropdown);
        if (!e.target.closest("#arr-container")) hideDropdown(arrDropdown);
    });

    // Invio form ricerca
    searchForm.addEventListener("submit", handleSearch);

    // Esportazione Excel
    exportBtn.addEventListener("click", handleExport);
});

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

// Configurazione della logica di Autocomplete
function setupAutocomplete(inputEl, dropdownEl, clearBtnEl, setSelectionCallback) {
    // Evento Input
    inputEl.addEventListener("input", () => {
        const query = inputEl.value.trim().toLowerCase();
        if (!query) {
            clearBtnEl.style.display = "none";
            hideDropdown(dropdownEl);
            setSelectionCallback("");
            return;
        }

        clearBtnEl.style.display = "block";
        setSelectionCallback(""); // Azzera la selezione reale finché non si clicca un elemento

        // Filtra gli aeroporti per nome, città o codice IATA
        const filtered = airportsList.filter(a => 
            a.name.toLowerCase().includes(query) || 
            a.city.toLowerCase().includes(query) || 
            a.code.toLowerCase().includes(query) ||
            a.country.toLowerCase().includes(query)
        ).slice(0, 10); // Limita a 10 risultati per leggibilità

        renderDropdownItems(filtered, dropdownEl, inputEl, clearBtnEl, setSelectionCallback);
    });

    // Focus input
    inputEl.addEventListener("focus", () => {
        const query = inputEl.value.trim().toLowerCase();
        if (query) {
            // Riesegue il filtro se c'è testo
            const filtered = airportsList.filter(a => 
                a.name.toLowerCase().includes(query) || 
                a.city.toLowerCase().includes(query) || 
                a.code.toLowerCase().includes(query) ||
                a.country.toLowerCase().includes(query)
            ).slice(0, 10);
            renderDropdownItems(filtered, dropdownEl, inputEl, clearBtnEl, setSelectionCallback);
        } else {
            // Mostra i primi 8 aeroporti popolari di default
            const popular = airportsList.slice(0, 8);
            renderDropdownItems(popular, dropdownEl, inputEl, clearBtnEl, setSelectionCallback);
        }
    });

    // Pulisci input
    clearBtnEl.addEventListener("click", () => {
        inputEl.value = "";
        clearBtnEl.style.display = "none";
        setSelectionCallback("");
        hideDropdown(dropdownEl);
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
        div.addEventListener("click", () => {
            inputEl.value = `${airport.city} (${airport.code})`;
            clearBtnEl.style.display = "block";
            setSelectionCallback(airport.code);
            hideDropdown(dropdownEl);
        });
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

    const date = dateInput.value;
    const layover = layoverSlider.value;

    // Cambia stato dell'interfaccia (mostra loader, nascondi risultati)
    welcomeState.style.display = "none";
    errorState.style.display = "none";
    resultsSection.style.display = "none";
    loaderState.style.display = "flex";
    
    // Disabilita pulsante
    searchBtn.disabled = true;
    searchBtn.querySelector(".btn-text").textContent = "Cercando...";
    searchBtn.querySelector(".btn-loader").style.display = "block";

    try {
        const queryParams = new URLSearchParams({
            start: selectedDepCode,
            end: selectedArrCode,
            date: date,
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

// Rendering dei Risultati
function renderResults(routes) {
    resultsList.innerHTML = "";
    
    // Aggiorna le statistiche in alto
    resultsCount.textContent = `Trovate ${routes.length} connession${routes.length === 1 ? "e" : "i"}`;
    const bestPrice = routes[0]["Total Price (€)"];
    bestPriceSpan.textContent = `Miglior prezzo: €${bestPrice.toFixed(2)}`;

    routes.forEach(route => {
        const isDirect = route["Connection"].includes("Diretto");
        const card = document.createElement("div");
        card.className = `flight-card glass ${isDirect ? "direct" : "connecting"}`;

        // Costruiamo il layout HTML per ciascun volo
        let routeHtml = `
            <div class="flight-type-badge">${isDirect ? "Diretto" : "Scalo"}</div>
            <div class="itinerary-details">
                <!-- Primo Volo (o Volo Diretto) -->
                <div class="flight-segment">
                    <div class="airport-info">
                        <span class="code">${getAirportCityAndCode(route["Connection"].split("-")[0].trim())}</span>
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
                        <span class="code">${getAirportCityAndCode(route["Connection"].split("-")[1].split("(")[0].split("|")[0].trim())}</span>
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
                    <span>🕒 Scalo a <strong>${getAirportCity(layoverAirport)} (${layoverAirport})</strong> per <strong>${layoverHours} ore</strong></span>
                </div>

                <!-- Secondo Volo -->
                <div class="flight-segment">
                    <div class="airport-info">
                        <span class="code">${getAirportCityAndCode(layoverAirport)}</span>
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
                        <span class="code">${getAirportCityAndCode(route["Connection"].split("|")[1].split("-")[1].trim())}</span>
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
function getAirportCityAndCode(iataCode) {
    const airport = airportsList.find(a => a.code === iataCode);
    return airport ? `${airport.city} (${iataCode})` : iataCode;
}

function getAirportCity(iataCode) {
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
