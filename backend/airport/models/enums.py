"""
Enums for the airport workshop application.

This module contains all enumeration types used throughout the application
for consistent data validation and type safety.
"""

from enum import Enum


class FlightStatus(str, Enum):
    """Flight status enumeration for tracking flight states."""
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    BOARDING = "boarding"
    DEPARTED = "departed"
    ARRIVED = "arrived"


class SeatStatus(str, Enum):
    """Seat availability status for reservation system."""
    AVAILABLE = "available"
    RESERVED = "reserved"      # Temporarily held with lock
    BOOKED = "booked"          # Confirmed booking
    BLOCKED = "blocked"        # Maintenance or unavailable


class SeatClass(str, Enum):
    """Aircraft seat class categories."""
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class WeatherCondition(str, Enum):
    """Weather conditions for airport weather simulation."""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    STORMY = "stormy"