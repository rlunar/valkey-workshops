"""Employee model."""

from typing import Optional
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlmodel import SQLModel, Field


class DepartmentEnum(str, Enum):
    """Employee department types."""
    MARKETING = "marketing"
    ACCOUNTING = "accounting"
    MANAGEMENT = "management"
    LOGISTICS = "logistics"
    AIRFIELD = "airfield"


class Employee(SQLModel, table=True):
    """Employee with department and credentials."""
    
    __tablename__ = "employee"
    
    employee_id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)
    birthdate: date
    sex: Optional[str] = Field(default=None, max_length=1)
    street: str = Field(max_length=100)
    city: str = Field(max_length=100)
    zip: int
    country: str = Field(max_length=100)
    emailaddress: Optional[str] = Field(default=None, max_length=120)
    telephoneno: Optional[str] = Field(default=None, max_length=30)
    salary: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=2)
    department: Optional[DepartmentEnum] = None
    username: Optional[str] = Field(default=None, max_length=20, unique=True)
    password: Optional[str] = Field(default=None, max_length=32)
