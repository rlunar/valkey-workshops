from typing import Optional
from datetime import date
from datetime import time as time_type
from decimal import Decimal
from enum import Enum
from sqlmodel import SQLModel, Field


class WeatherCondition(str, Enum):
    FOG_SNOW = "Nebel-Schneefall"
    SNOW = "Schneefall"
    RAIN = "Regen"
    RAIN_SNOW = "Regen-Schneefall"
    FOG_RAIN = "Nebel-Regen"
    FOG_RAIN_STORM = "Nebel-Regen-Gewitter"
    STORM = "Gewitter"
    FOG = "Nebel"
    RAIN_STORM = "Regen-Gewitter"


class WeatherData(SQLModel, table=True):
    __tablename__ = "weatherdata"
    
    log_date: date = Field(primary_key=True)
    time: time_type = Field(primary_key=True)
    station: int = Field(primary_key=True)
    temp: Decimal = Field(max_digits=3, decimal_places=1)
    humidity: Decimal = Field(max_digits=4, decimal_places=1)
    airpressure: Decimal = Field(max_digits=10, decimal_places=2)
    wind: Decimal = Field(max_digits=5, decimal_places=2)
    weather: Optional[WeatherCondition] = None
    winddirection: int = Field(ge=0, le=360)  # smallint for wind direction in degrees