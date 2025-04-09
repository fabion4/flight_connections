import streamlit as st
from flight_search import find_best_routes, get_airports
from utils import save_to_excel, get_airport_choices
from localization import get_translation

# Set page configuration (must be the first Streamlit command)
st.set_page_config(layout="wide")

# Language selection
language = st.sidebar.selectbox("Select Language / Seleziona Lingua / Seleziona Limba", ["it", "en", "sc"])

st.title(get_translation(language, "title"))
# Breve spiegazione
st.markdown(get_translation(language, "intro_text"))

# Retrieve airports
airports = get_airports()
airport_choices = get_airport_choices(airports)

# Airport selection
start_airport_code, start_airport_name = zip(*airport_choices)
start_airport = st.selectbox(get_translation(language, "select_departure"), start_airport_name)

end_airport_code, end_airport_name = zip(*airport_choices)
end_airport = st.selectbox(get_translation(language, "select_arrival"), end_airport_name)

date = st.date_input(get_translation(language, "departure_date"))
max_layover_days = st.slider(get_translation(language, "max_layover"), 1, 5, 3)

# Check if the table is already in session state
if "df_routes" not in st.session_state:
    st.session_state.df_routes = None

if st.button(get_translation(language, "search_flights")):
    st.write(get_translation(language, "searching"))
    df_routes = find_best_routes(
        start_airport_code[start_airport_name.index(start_airport)],
        end_airport_code[end_airport_name.index(end_airport)],
        str(date),
        max_layover_days
    )

    if df_routes.empty:
        st.error(get_translation(language, "no_connections"))
        st.session_state.df_routes = None
    else:
        st.success(get_translation(language, "connections_found", count=len(df_routes)))
        st.session_state.df_routes = df_routes  # Save the dataframe in session state

# If results exist, show the table and download button
if st.session_state.df_routes is not None:
    st.dataframe(st.session_state.df_routes)

    filename = save_to_excel(st.session_state.df_routes)
    with open(filename, "rb") as f:
        st.download_button(
            get_translation(language, "download_excel"),
            data=f,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
