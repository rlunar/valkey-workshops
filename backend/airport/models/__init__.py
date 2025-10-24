"""
Airport workshop Pydantic models package.

This package contains all Pydantic v2 models used throughout the airport workshop
application for data validation, serialization, and type safety.
"""

# Enums
from .enums import (
    FlightStatus,
    SeatStatus,
    SeatClass,
    WeatherCondition,
)

# Core flight and passenger models
from .flight import (
    AirportModel,
    AirlineModel,
    FlightScheduleModel,
    FlightStatusModel,
    FlightModel,
)

from .passenger import (
    PassengerModel,
    BookingModel,
)

# Seat reservation models
from .seat import (
    SeatModel,
    SeatReservationModel,
    FlightSeatMapModel,
)

# Cache and performance models
from .cache import (
    CacheMetricsModel,
    TTLDistributionModel,
    APICacheEntryModel,
    WeatherModel,
)

# Simulation models
from .simulation import (
    ConcurrentBookingSimulationModel,
    UserSimulationModel,
    PerformanceTestResultModel,
    LoadTestConfigModel,
)

# Russian doll cache and manifest models
from .manifest import (
    PassengerManifestEntryModel,
    FlightManifestModel,
    AirportDailyFlightsModel,
    NestedFlightDataModel,
)

# Cache dependency models
from .cache_dependency import (
    InvalidationType,
    DependencyType,
    CacheDependencyModel,
    InvalidationEventModel,
    CacheDependencyGraphModel,
    WriteBehindQueueEntryModel,
    CacheCoherenceModel,
    CacheInvalidationStrategyModel,
)

__all__ = [
    # Enums
    "FlightStatus",
    "SeatStatus", 
    "SeatClass",
    "WeatherCondition",
    
    # Core models
    "AirportModel",
    "AirlineModel",
    "FlightScheduleModel",
    "FlightStatusModel",
    "FlightModel",
    "PassengerModel",
    "BookingModel",
    
    # Seat models
    "SeatModel",
    "SeatReservationModel",
    "FlightSeatMapModel",
    
    # Cache models
    "CacheMetricsModel",
    "TTLDistributionModel",
    "APICacheEntryModel",
    "WeatherModel",
    
    # Simulation models
    "ConcurrentBookingSimulationModel",
    "UserSimulationModel",
    "PerformanceTestResultModel",
    "LoadTestConfigModel",
    
    # Manifest models
    "PassengerManifestEntryModel",
    "FlightManifestModel",
    "AirportDailyFlightsModel",
    "NestedFlightDataModel",
    
    # Dependency models
    "InvalidationType",
    "DependencyType",
    "CacheDependencyModel",
    "InvalidationEventModel",
    "CacheDependencyGraphModel",
    "WriteBehindQueueEntryModel",
    "CacheCoherenceModel",
    "CacheInvalidationStrategyModel",
]
