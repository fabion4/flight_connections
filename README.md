# FlyConnect ✈️

A modern, fast web application that helps you discover the cheapest flight connections — both direct and with layovers — between any two airports. 

Formerly built on Streamlit, the project has been updated to a premium HTML/JS/CSS frontend with a serverless Python backend deployed on Vercel.

## Features
* ✅ Live airport selection via modern autocomplete dropdown
* ✅ Custom interactive calendar date picker popup
* ✅ Ranks both direct and 1-stop connections by total price
* ✅ Displays layover times and full travel duration
* ✅ Easy download of results as an Excel file
* ✅ Fully responsive glassmorphism layout, optimized for both desktop and mobile

## Links
* **GitHub Repository:** [https://github.com/fabion4/flight_connections](https://github.com/fabion4/flight_connections)
* **Vercel Web App:** [https://flight-connections-one.vercel.app/](https://flight-connections-one.vercel.app/)

## Local Run Instructions

To run the application locally (e.g., using the **Portable Python** console via `Console-Launcher.exe`), follow these steps:

### First-Time Setup (Only needed once)
If you haven't set up the project yet, run the following commands to create the virtual environment and install the required dependencies:
```bash
# Create the virtual environment using uv
uv venv

# Activate it
.venv\Scripts\activate

# Install requirements
uv pip install -r requirements.txt
```

### Daily Run (Subsequent runs)
1. **Activate the virtual environment**:
   ```bash
   .venv\Scripts\activate
   ```
2. **Start the local development server**:
   Use `uv` to run the FastAPI backend (which also serves the static frontend files):
   ```bash
   uv run uvicorn api.index:app --reload
   ```
3. **Access the application**: Open your browser and navigate to `http://127.0.0.1:8000`.
