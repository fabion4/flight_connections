import pandas as pd
import os
import uuid
import time
from datetime import datetime, timedelta

def save_to_excel(df, prefix="flights"):
    """Save DataFrame to Excel with a unique filename."""
    # Create directory if it doesn't exist
    os.makedirs("downloads", exist_ok=True)
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"downloads/{prefix}_{timestamp}_{unique_id}.xlsx"
    
    # Save to Excel with improved formatting
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Flight Results')
        
        # Auto-adjust column width
        worksheet = writer.sheets['Flight Results']
        for i, col in enumerate(df.columns):
            max_width = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            # Add a little extra space
            worksheet.column_dimensions[chr(65 + i)].width = max_width + 2
    
    return filename

def get_airport_choices(airports):
    """Create a list of (code, name) tuples for airport selection."""
    airport_choices = []
    for airport in airports:
        # Only add active airports with a valid IATA code
        if airport.get("iataCode") and airport.get("name"):
            airport_choices.append((airport["iataCode"], f"{airport['name']} ({airport['iataCode']})"))
    
    # Sort by airport name for better UX
    return sorted(airport_choices, key=lambda x: x[1])

def clear_old_files(directory="downloads", max_age_hours=24):
    """Delete files older than the specified age."""
    if not os.path.exists(directory):
        return
        
    # Get current time
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    # Iterate through files in the directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # Check if it's a file (not a directory)
        if os.path.isfile(file_path):
            # Get file modification time
            file_age = now - os.path.getmtime(file_path)
            
            # Remove file if older than max age
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
