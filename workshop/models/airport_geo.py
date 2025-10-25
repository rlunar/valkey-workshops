from typing import Optional
from decimal import Decimal
from enum import Enum
from sqlmodel import SQLModel, Field


class DSTType(str, Enum):
    """Daylight Saving Time types"""
    EUROPE = "E"  # Europe
    AMERICA = "A"  # US/Canada
    SOUTH = "S"   # South America
    AUSTRALIA = "O"  # Australia
    ASIA = "Z"    # Asia
    NONE = "N"    # No DST
    UNKNOWN = "U"  # Unknown


class AirportGeo(SQLModel, table=True):
    """Geographic data for airports, normalized from the main Airport table"""
    __tablename__ = "airport_geo"
    
    airport_id: int = Field(primary_key=True, foreign_key="airport.airport_id")
    city: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)  # Raw country name from airports.dat
    country_id: int = Field(foreign_key="country.country_id", index=True)
    iso_a3: Optional[str] = Field(default=None, max_length=3, index=True)
    latitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    longitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    altitude: Optional[int] = Field(default=None)
    timezone_offset: Optional[Decimal] = Field(default=None, max_digits=4, decimal_places=2)
    dst: Optional[DSTType] = Field(default=None)
    timezone_name: Optional[str] = Field(default=None, max_length=50)