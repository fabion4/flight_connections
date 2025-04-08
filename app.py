import streamlit as st
from flight_search import find_best_routes, get_airports
from utils import save_to_excel, get_airport_choices

st.set_page_config(layout="wide")
st.title("Trova il volo più economico ✈️")

# Recupera gli aeroporti
airports = get_airports()
airport_choices = get_airport_choices(airports)

# Selezione aeroporti
start_airport_code, start_airport_name = zip(*airport_choices)
start_airport = st.selectbox("Seleziona aeroporto di partenza", start_airport_name)

end_airport_code, end_airport_name = zip(*airport_choices)
end_airport = st.selectbox("Seleziona aeroporto di arrivo", end_airport_name)

date = st.date_input("Data di partenza:")
max_layover_days = st.slider("Tempo massimo di scalo (giorni):", 1, 5, 3)

# Verifica se la tabella è già nello stato della sessione
if "df_routes" not in st.session_state:
    st.session_state.df_routes = None

if st.button("Cerca voli"):
    st.write("🔍 Cercando i voli migliori...")
    df_routes = find_best_routes(
        start_airport_code[start_airport_name.index(start_airport)],
        end_airport_code[end_airport_name.index(end_airport)],
        str(date),
        max_layover_days
    )

    if df_routes.empty:
        st.error("❌ Nessuna connessione trovata!")
        st.session_state.df_routes = None
    else:
        st.success(f"✅ {len(df_routes)} connessioni trovate!")
        st.session_state.df_routes = df_routes  # Salva il dataframe nello stato della sessione

# Se esistono risultati, mostra la tabella e il download
if st.session_state.df_routes is not None:
    st.dataframe(st.session_state.df_routes)

    filename = save_to_excel(st.session_state.df_routes)
    with open(filename, "rb") as f:
        st.download_button("📥 Scarica Excel", data=f, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
