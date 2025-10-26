from typing import Optional
from sqlmodel import SQLModel, Field


class Airplane(SQLModel, table=True):
    __tablename__ = "airplane"
    
    airplane_id: Optional[int] = Field(default=None, primary_key=True)
    capacity: int = Field(ge=0)  # mediumint unsigned
    type_id: int = Field(foreign_key="airplane_type.type_id")
    airline_id: Optional[int] = Field(default=None, index=True)  # Reference to airline, no FK constraint