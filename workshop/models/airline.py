from typing import Optional
from sqlmodel import SQLModel, Field


class Airline(SQLModel, table=True):
    __tablename__ = "airline"
    
    airline_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    alias: Optional[str] = Field(max_length=200, default=None)
    iata: Optional[str] = Field(max_length=2, default=None, index=True)
    icao: Optional[str] = Field(max_length=3, default=None, index=True)
    callsign: Optional[str] = Field(max_length=100, default=None)
    country: Optional[str] = Field(max_length=100, default=None)
    active: Optional[bool] = Field(default=True)
    openflights_id: Optional[int] = Field(default=None, unique=True, index=True)
    data_source: Optional[str] = Field(max_length=50, default="OpenFlights")