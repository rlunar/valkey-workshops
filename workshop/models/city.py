from typing import Optional
from decimal import Decimal
from sqlmodel import SQLModel, Field


class City(SQLModel, table=True):
    """City model based on GeoNames dataset for flight planning and population analysis"""
    __tablename__ = "city"
    
    # Primary key and GeoNames identifier
    city_id: Optional[int] = Field(default=None, primary_key=True)
    geonames_id: Optional[int] = Field(default=None, unique=True, index=True)
    
    # Basic city information
    name: str = Field(max_length=200, index=True)
    ascii_name: Optional[str] = Field(default=None, max_length=200, index=True)
    alternate_names: Optional[str] = Field(default=None, max_length=10000)  # Comma-separated alternate names
    
    # Geographic coordinates
    latitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    longitude: Optional[Decimal] = Field(default=None, max_digits=11, decimal_places=8)
    
    # Administrative divisions
    country_code: Optional[str] = Field(default=None, max_length=2, index=True)
    country_id: Optional[int] = Field(default=None, index=True)  # Reference to country, no FK constraint
    admin1_code: Optional[str] = Field(default=None, max_length=20)  # State/Province
    admin2_code: Optional[str] = Field(default=None, max_length=80)  # County/District
    admin3_code: Optional[str] = Field(default=None, max_length=20)  # Municipality
    admin4_code: Optional[str] = Field(default=None, max_length=20)  # Neighborhood
    
    # Population data for flight planning
    population: Optional[int] = Field(default=None, index=True)
    elevation: Optional[int] = Field(default=None)  # Meters above sea level
    
    # GeoNames feature classification
    feature_class: Optional[str] = Field(default=None, max_length=1)  # P for populated places
    feature_code: Optional[str] = Field(default=None, max_length=10)  # PPL, PPLA, PPLC, etc.
    
    # Timezone information
    timezone: Optional[str] = Field(default=None, max_length=40)
    
    # Flight planning metrics
    flight_demand_score: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=2)  # Calculated demand score
    recommended_daily_flights: Optional[int] = Field(default=None)  # Recommended flights per day
    peak_season_multiplier: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)  # Peak season adjustment
    
    # Data source and quality
    data_source: Optional[str] = Field(default="GeoNames", max_length=50)
    last_updated: Optional[str] = Field(default=None, max_length=19)  # ISO format timestamp
    
    # Indexes for efficient querying
    class Config:
        indexes = [
            ("country_code", "population"),
            ("latitude", "longitude"),
            ("population", "flight_demand_score"),
        ]


class CityAirportRelation(SQLModel, table=True):
    """Many-to-many relationship between cities and airports for flight planning"""
    __tablename__ = "city_airport_relation"
    
    relation_id: Optional[int] = Field(default=None, primary_key=True)
    city_id: int = Field(index=True)  # Reference to city, no FK constraint
    airport_id: int = Field(index=True)  # Reference to airport, no FK constraint
    
    # Distance and accessibility metrics
    distance_km: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=2)
    is_primary_airport: bool = Field(default=False)  # Main airport serving this city
    accessibility_score: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)  # 0-10 scale
    
    # Flight planning data
    estimated_passenger_share: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=4)  # 0-1 percentage
    seasonal_variation: Optional[Decimal] = Field(default=None, max_digits=3, decimal_places=2)  # Seasonal multiplier
    
    class Config:
        indexes = [
            ("city_id", "is_primary_airport"),
            ("airport_id", "estimated_passenger_share"),
        ]