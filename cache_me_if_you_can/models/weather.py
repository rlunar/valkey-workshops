"""Weather data model."""

from typing import Optional
from datetime import date, time
from decimal import Decimal
from enum import Enum
from sqlmodel import SQLModel, Field


class WeatherConditionEnum(str, Enum):
    """Weather condition types."""
    FOG_SNOWFALL = "fog-snowfall"
    SNOWFALL = "snowfall"
    RAIN = "rain"
    RAIN_SNOWFALL = "rain-snowfall"
    FOG_RAIN = "fog-rain"
    FOG_RAIN_THUNDERSTORM = "fog-rain-thunderstorm"
    THUNDERSTORM = "thunderstorm"
    FOG = "fog"
    RAIN_THUNDERSTORM = "rain-thunderstorm"


class WeatherData(SQLModel, table=True):
    """Weather observations at stations."""
    
    __tablename__ = "weatherdata"
    
    log_date: date = Field(primary_key=True)
    time: time = Field(primary_key=True)
    station: int = Field(primary_key=True)
    temp: Decimal = Field(max_digits=3, decimal_places=1)
    humidity: Decimal = Field(max_digits=4, decimal_places=1)
    airpressure: Decimal = Field(max_digits=10, decimal_places=2)
    wind: Decimal = Field(max_digits=5, decimal_places=2)
    weather: Optional[WeatherConditionEnum] = None
    winddirection: int
