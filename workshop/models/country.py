from typing import Optional
from sqlmodel import SQLModel, Field


class Country(SQLModel, table=True):
    __tablename__ = "country"
    
    country_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    iso_code: Optional[str] = Field(max_length=2, unique=True, index=True)
    iso_a3: Optional[str] = Field(max_length=3, unique=True, index=True)
    dafif_code: Optional[str] = Field(max_length=2, index=True)
    data_source: Optional[str] = Field(default="OpenFlights", max_length=50)