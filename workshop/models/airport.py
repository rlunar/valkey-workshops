from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field


class AirportType(str, Enum):
    AIRPORT = "airport"
    HELIPORT = "heliport"
    SEAPLANE_BASE = "seaplane_base"
    CLOSED = "closed"
    BALLOONPORT = "balloonport"


class Airport(SQLModel, table=True):
    __tablename__ = "airport"
    
    airport_id: Optional[int] = Field(default=None, primary_key=True)
    iata: Optional[str] = Field(max_length=3, index=True)
    icao: str = Field(max_length=4, unique=True)
    name: str = Field(max_length=200, index=True)
    airport_type: Optional[AirportType] = Field(default=AirportType.AIRPORT)
    data_source: Optional[str] = Field(max_length=50)
    openflights_id: Optional[int] = Field(index=True)

