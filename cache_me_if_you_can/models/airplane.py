"""Airplane-related models."""

from typing import Optional
from sqlmodel import SQLModel, Field


class AirplaneType(SQLModel, table=True):
    """Aircraft type/model information."""
    
    __tablename__ = "airplane_type"
    
    type_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    identifier: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None


class Airplane(SQLModel, table=True):
    """Individual airplane with capacity and type."""
    
    __tablename__ = "airplane"
    
    airplane_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    capacity: int = Field(ge=0)
    type_id: int = Field(foreign_key="airplane_type.type_id")
    airline_id: int = Field(foreign_key="airline.airline_id")
