from typing import Optional
from sqlmodel import SQLModel, Field


class AirplaneType(SQLModel, table=True):
    """Aircraft type/model information from OpenFlights planes database"""
    __tablename__ = "airplane_type"
    
    type_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)  # Full name of the aircraft
    iata: Optional[str] = Field(default=None, max_length=3)  # IATA code (3 letters)
    icao: Optional[str] = Field(default=None, max_length=4)  # ICAO code (4 letters)
    data_source: Optional[str] = Field(default=None, max_length=50)  # Source of the data