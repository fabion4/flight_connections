import streamlit as st
import pandas as pd
import os
import json
import logging
from datetime import datetime
from flight_search import find_best_routes, get_airports, set_ssl_verification, set_currency
from utils import save_to_excel, get_airport_choices, clear_old_files
from localization import get_translation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set page configuration (must be the first Streamlit command)
st.set_page_config(layout="wide")

# Create directory for feedback if it doesn't exist
os.makedirs("feedback", exist_ok=True)

# Language selection
language = st.sidebar.selectbox("Select Language / Seleziona Lingua / Seleziona Limba", ["it", "en", "sc"])

# Configuration options in sidebar
with st.sidebar.expander(get_translation(language, "config_options")):
    verify_ssl = st.checkbox(get_translation(language, "verify_ssl"), value=False)
    currency = st.selectbox(get_translation(language, "currency"), ["EUR", "USD", "GBP"])
    
    # Apply configuration
    set_ssl_verification(verify_ssl)
    set_currency(currency)

st.title(get_translation(language, "title"))
# Short explanation
st.markdown(get_translation(language, "intro_text"))

# Clean up old Excel files
clear_old_files()

# Retrieve airports with error handling
try:
    airports = get_airports()
    if not airports:
        st.error(get_translation(language, "error_airports"))
        airport_choices = []
    else:
        airport_choices = get_airport_choices(airports)
except Exception as e:
    st.error(f"{get_translation(language, 'error_airports')}: {str(e)}")
    airport_choices = []

# Only show airport selection if we have airports
if airport_choices:
    # Airport selection
    col1, col2 = st.columns(2)
    
    with col1:
        start_airport_code, start_airport_name = zip(*airport_choices)
        start_airport = st.selectbox(get_translation(language, "select_departure"), start_airport_name)
    
    with col2:
        end_airport_code, end_airport_name = zip(*airport_choices)
        end_airport = st.selectbox(get_translation(language, "select_arrival"), end_airport_name)
    
    # Date selection with improved UX - show first day of month
    today = datetime.now()
    date = st.date_input(get_translation(language, "departure_date"), value=today.replace(day=1))
    
    # Format date as YYYY-MM-DD for the API
    formatted_date = date.strftime("%Y-%m-%d")
    
    # Additional options
    col1, col2 = st.columns(2)
    with col1:
        max_layover_days = st.slider(get_translation(language, "max_layover"), 1, 5, 3)
    
    # Check if the table is already in session state
    if "df_routes" not in st.session_state:
        st.session_state.df_routes = None
    
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    
    search_button = st.button(get_translation(language, "search_flights"))
    
    if search_button:
        # Reset error message
        st.session_state.error_message = None
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(get_translation(language, "searching"))
        
        try:
            # Get selected airport codes
            selected_start_code = start_airport_code[start_airport_name.index(start_airport)]
            selected_end_code = end_airport_code[end_airport_name.index(end_airport)]
            
            # Update progress
            progress_bar.progress(25)
            status_text.text(get_translation(language, "checking_routes"))
            
            # Find routes
            df_routes = find_best_routes(
                selected_start_code,
                selected_end_code,
                formatted_date,
                max_layover_days
            )
            
            # Update progress
            progress_bar.progress(100)
            
            if df_routes.empty:
                st.error(get_translation(language, "no_connections"))
                st.session_state.df_routes = None
            else:
                st.success(get_translation(language, "connections_found", count=len(df_routes)))
                st.session_state.df_routes = df_routes  # Save the dataframe in session state
                
        except Exception as e:
            st.session_state.error_message = str(e)
            st.error(f"{get_translation(language, 'search_error')}: {str(e)}")
        finally:
            # Hide progress elements
            status_text.empty()
            progress_bar.empty()
    
    # If there was an error from a previous search, display it
    if st.session_state.error_message:
        st.error(f"{get_translation(language, 'search_error')}: {st.session_state.error_message}")
    
    # If results exist, show the table and download button
    if st.session_state.df_routes is not None and not st.session_state.df_routes.empty:
        st.dataframe(st.session_state.df_routes)
        
        filename = save_to_excel(st.session_state.df_routes)
        with open(filename, "rb") as f:
            st.download_button(
                get_translation(language, "download_excel"),
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Feedback form
with st.expander(get_translation(language, "feedback_form")):
    st.write(get_translation(language, "feedback_intro"))
    
    feedback_name = st.text_input(get_translation(language, "feedback_name"))
    feedback_email = st.text_input(get_translation(language, "feedback_email"))
    feedback_type = st.selectbox(
        get_translation(language, "feedback_type"),
        [
            get_translation(language, "feedback_bug"),
            get_translation(language, "feedback_feature"),
            get_translation(language, "feedback_other")
        ]
    )
    feedback_text = st.text_area(get_translation(language, "feedback_message"))
    
    if st.button(get_translation(language, "submit_feedback")):
        if feedback_text:
            # Save feedback to a file
            feedback_data = {
                "name": feedback_name,
                "email": feedback_email,
                "type": feedback_type,
                "message": feedback_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            feedback_file = f"feedback/feedback_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            with open(feedback_file, "w") as f:
                json.dump(feedback_data, f, indent=4)
            
            # Log the feedback
            logging.info(
                "User feedback received: Name=%s, Email=%s, Type=%s, Message=%s",
                feedback_name, feedback_email, feedback_type, feedback_text
            )
            
            # Show success message
            st.success(get_translation(language, "feedback_success"))
        else:
            st.warning(get_translation(language, "feedback_empty"))

# Show version info in footer
st.sidebar.markdown("---")
st.sidebar.text("v1.1.0")
