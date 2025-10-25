from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field


class Airport(SQLModel, table=True):
    __tablename__ = "airport"
    
    airport_id: Optional[int] = Field(default=None, primary_key=True)
    iata: Optional[str] = Field(max_length=3, index=True)
    icao: str = Field(max_length=4, unique=True)
    name: str = Field(max_length=50, index=True)


class AirportGeo(SQLModel, table=True):
    __tablename__ = "airport_geo"
    
    airport_id: int = Field(primary_key=True, foreign_key="airport.airport_id")
    name: str = Field(max_length=50)
    city: Optional[str] = Field(max_length=50)
    country: Optional[str] = Field(max_length=50)
    latitude: Decimal = Field(max_digits=11, decimal_places=8)
    longitude: Decimal = Field(max_digits=11, decimal_places=8)
    # Note: geolocation point field not directly supported in SQLModel


class AirportReachable(SQLModel, table=True):
    __tablename__ = "airport_reachable"
    
    airport_id: int = Field(primary_key=True)
    hops: Optional[int] = None