from itertools import product
from datetime import datetime
from api.models import FlightLeg, Connection
from api.providers.base import FlightProvider
from api.city_groups import expand_airport

def find_connections(
    provider: FlightProvider,
    start_airport: str,
    end_airport: str,
    dates: list[str],
    max_layover_h: float,
    use_city_groups: bool = True,
    filter_start: str = None,
    filter_end: str = None,
) -> list[Connection]:
    """
    Algoritmo di routing condiviso tra i diversi provider di voli.
    Trova voli diretti e connessioni con 1 scalo intermedio.

    dates: date usate per interrogare il provider (es. primo del mese per Ryanair, giornaliere per Duffel)
    filter_start/filter_end: range reale richiesto dall'utente per filtrare i voli restituiti
    """
    if filter_start and filter_end:
        from datetime import date as date_type
        _filter_start = datetime.strptime(filter_start, "%Y-%m-%d").date()
        _filter_end = datetime.strptime(filter_end, "%Y-%m-%d").date()
        def in_range(dt: datetime) -> bool:
            return _filter_start <= dt.date() <= _filter_end
    else:
        valid_dates = set(dates)
        def in_range(dt: datetime) -> bool:
            return dt.strftime("%Y-%m-%d") in valid_dates
    
    # 1. Espandi gli aeroporti
    start_expanded = expand_airport(start_airport) if use_city_groups else [start_airport]
    end_expanded = expand_airport(end_airport) if use_city_groups else [end_airport]
    
    # 2. Calcola destinazioni raggiungibili da start
    reachable_from_start = set()
    for start_apt in start_expanded:
        reachable_from_start.update(provider.get_destinations(start_apt))
        
    # 3. Calcola origini che raggiungono end
    reachable_to_end = set()
    for end_apt in end_expanded:
        reachable_to_end.update(provider.get_destinations(end_apt))
        
    # 4. Intersezione per trovare candidati di scalo
    via_candidates = reachable_from_start & reachable_to_end
    
    connections = []
    
    # 5. Cerca connessioni con scalo per ciascun via_airport
    for via_airport in via_candidates:
        first_legs = []
        second_legs = []
        for date in dates:
            for start_apt in start_expanded:
                first_legs.extend(provider.get_flights(start_apt, via_airport, date))
            for end_apt in end_expanded:
                second_legs.extend(provider.get_flights(via_airport, end_apt, date))
                
        # Filtra i primi voli solo per le date richieste
        first_legs = [f for f in first_legs if in_range(f.departure)]
        
        # Deduplica le tratte per evitare duplicati causati dalle risposte cumulative dei provider (es. Ryanair mensile)
        seen_first = set()
        dedup_first = []
        for f in first_legs:
            key = (f.from_code, f.to_code, f.departure, f.arrival, f.flight_number)
            if key not in seen_first:
                seen_first.add(key)
                dedup_first.append(f)
                
        seen_second = set()
        dedup_second = []
        for f in second_legs:
            key = (f.from_code, f.to_code, f.departure, f.arrival, f.flight_number)
            if key not in seen_second:
                seen_second.add(key)
                dedup_second.append(f)
                
        for f1, f2 in product(dedup_first, dedup_second):
            layover_time = (f2.departure - f1.arrival).total_seconds() / 3600
            if 0 < layover_time <= max_layover_h:
                total_duration = (f2.arrival - f1.departure).total_seconds() / 3600
                total_price = f1.price + f2.price
                connections.append(
                    Connection(
                        connection_label=f"{f1.from_code}-{f1.to_code} | {f2.from_code}-{f2.to_code}",
                        first_leg=f1,
                        second_leg=f2,
                        layover_h=round(layover_time, 1),
                        total_duration_h=round(total_duration, 1),
                        total_price=total_price
                    )
                )
                
    # 6. Cerca voli diretti
    for date in dates:
        for start_apt in start_expanded:
            for end_apt in end_expanded:
                flights = provider.get_flights(start_apt, end_apt, date)
                for f in flights:
                    if in_range(f.departure):
                        duration_h = (f.arrival - f.departure).total_seconds() / 3600
                        connections.append(
                            Connection(
                                connection_label=f"{f.from_code}-{f.to_code} (Diretto)",
                                first_leg=f,
                                second_leg=None,
                                layover_h=0.0,
                                total_duration_h=round(duration_h, 1),
                                total_price=f.price
                            )
                        )
                        
    # 7. Ordina per prezzo totale crescente
    connections.sort(key=lambda c: c.total_price)
    return connections
