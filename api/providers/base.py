from typing import Protocol, runtime_checkable
from api.models import FlightLeg

@runtime_checkable
class FlightProvider(Protocol):
    def get_destinations(self, airport_code: str) -> list[str]:
        """Restituisce i codici IATA raggiungibili da airport_code."""
        ...

    def get_flights(self, from_code: str, to_code: str, date_str: str) -> list[FlightLeg]:
        """
        Restituisce i voli diretti da from_code a to_code nella data date_str (YYYY-MM-DD).
        Ogni elemento è un singolo segmento di volo, non una connessione composta.
        """
        ...
