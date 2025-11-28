"""Airport-related models."""

from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field


class Airport(SQLModel, table=True):
    """Airport entity with IATA/ICAO codes."""
    
    __tablename__ = "airport"
    
    airport_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    iata: Optional[str] = Field(default=None, max_length=3, index=True)
    icao: str = Field(max_length=4, unique=True)
    name: str = Field(max_length=50, index=True)


class AirportGeo(SQLModel, table=True):
    """Geographic information for airports with spatial data."""
    
    __tablename__ = "airport_geo"
    
    airport_id: int = Field(foreign_key="airport.airport_id", primary_key=True, index=True)
    name: str = Field(max_length=50)
    city: Optional[str] = Field(default=None, max_length=50)
    country: Optional[str] = Field(default=None, max_length=50)
    latitude: Decimal = Field(max_digits=11, decimal_places=8)
    longitude: Decimal = Field(max_digits=11, decimal_places=8)
    # Note: geolocation POINT field requires special handling with GeoAlchemy2


class AirportReachable(SQLModel, table=True):
    """In-memory table for airport reachability calculations."""
    
    __tablename__ = "airport_reachable"
    
    airport_id: int = Field(primary_key=True)
    hops: Optional[int] = None
