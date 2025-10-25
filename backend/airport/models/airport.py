"""
Airport-related Pydantic models for the airport workshop application.

This module contains models for airport information with proper validation
and field constraints.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AirportModel(BaseModel):
    """Airport information model."""
    model_config = ConfigDict(from_attributes=True)
    
    airport_id: int
    iata: Optional[str] = Field(None, max_length=3, description="IATA airport code")
    icao: str = Field(..., max_length=4, description="ICAO airport code")
    name: str = Field(..., max_length=50, description="Airport name")