"""
Airline-related Pydantic models for the airport workshop application.

This module contains models for airline information with proper validation
and field constraints.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AirlineModel(BaseModel):
    """Airline information model."""
    model_config = ConfigDict(from_attributes=True)
    
    airline_id: int
    iata: str = Field(..., max_length=2, description="IATA airline code")
    airlinename: Optional[str] = Field(None, max_length=30, description="Airline name")
    base_airport: int = Field(..., description="Base airport ID")