from typing import Optional
from datetime import date
from decimal import Decimal
from enum import Enum
from sqlmodel import SQLModel, Field


class Department(str, Enum):
    MARKETING = "Marketing"
    ACCOUNTING = "Buchhaltung"
    MANAGEMENT = "Management"
    LOGISTICS = "Logistik"
    AIRFIELD = "Flugfeld"


class Employee(SQLModel, table=True):
    __tablename__ = "employee"
    
    employee_id: Optional[int] = Field(default=None, primary_key=True)
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)
    birthdate: date
    sex: Optional[str] = Field(max_length=1)
    street: str = Field(max_length=100)
    city: str = Field(max_length=100)
    zip: int = Field(ge=0, le=99999)  # smallint
    country: str = Field(max_length=100)
    emailaddress: Optional[str] = Field(max_length=120)
    telephoneno: Optional[str] = Field(max_length=30)
    salary: Optional[Decimal] = Field(max_digits=8, decimal_places=2)
    department: Optional[Department] = None
    username: Optional[str] = Field(max_length=20, unique=True)
    password: Optional[str] = Field(max_length=32)  # MD5 hash