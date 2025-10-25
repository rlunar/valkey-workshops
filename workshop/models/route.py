from typing import Optional
from sqlmodel import SQLModel, Field


class Route(SQLModel, table=True):
    __tablename__ = "route"
    
    route_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Airline information
    airline_code: Optional[str] = Field(max_length=3, index=True)  # IATA or ICAO code
    airline_id_openflights: Optional[int] = Field(index=True)  # OpenFlights airline ID
    
    # Source airport information
    source_airport_code: Optional[str] = Field(max_length=4, index=True)  # IATA or ICAO code
    source_airport_id_openflights: Optional[int] = Field(index=True)  # OpenFlights airport ID
    
    # Destination airport information
    destination_airport_code: Optional[str] = Field(max_length=4, index=True)  # IATA or ICAO code
    destination_airport_id_openflights: Optional[int] = Field(index=True)  # OpenFlights airport ID
    
    # Route details
    codeshare: Optional[bool] = Field(default=False)  # True if codeshare flight
    stops: Optional[int] = Field(default=0)  # Number of stops (0 for direct)
    equipment: Optional[str] = Field(max_length=200, default=None)  # Aircraft types used
    
    # Metadata
    data_source: Optional[str] = Field(max_length=50, default="OpenFlights")