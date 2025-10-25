"""
Nested doll caching system with flight integration.

This module implements hierarchical caching patterns where cached fragments
contain other cached fragments, demonstrating advanced cache dependency
management and selective invalidation strategies.
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from uuid import uuid4

from ..cache.manager import CacheManager
from ..models.airport import AirportModel
from ..models.flight import FlightModel, FlightScheduleModel, FlightStatusModel
from ..models.manifest import (
    FlightManifestModel, 
    PassengerManifestEntryModel, 
    AirportDailyFlightsModel,
    NestedFlightDataModel
)
from ..models.passenger import PassengerModel, BookingModel
from ..models.cache_dependency import (
    CacheDependencyModel, 
    InvalidationEventModel, 
    CacheDependencyGraphModel,
    DependencyType,
    InvalidationType
)

logger = logging.getLogger(__name__)


@dataclass
class CacheFragment:
    """Represents a cached fragment with metadata."""
    key: str
    data: Any
    cached_at: datetime
    ttl_seconds: int
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


@dataclass
class PerformanceMetrics:
    """Performance comparison metrics for caching strategies."""
    nested_cache_hits: int = 0
    nested_cache_misses: int = 0
    flat_cache_hits: int = 0
    flat_cache_misses: int = 0
    nested_response_time_ms: float = 0.0
    flat_response_time_ms: float = 0.0
    invalidation_cascade_count: int = 0
    fragments_invalidated: int = 0


class CacheDependencyGraph:
    """
    Manages cache dependency relationships and invalidation cascades.
    
    Tracks parent-child relationships between cache keys and handles
    cascading invalidation when parent data changes.
    """
    
    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}  # parent -> children
        self.reverse_dependencies: Dict[str, Set[str]] = {}  # child -> parents
        self.dependency_metadata: Dict[Tuple[str, str], CacheDependencyModel] = {}
    
    def add_dependency(self, parent_key: str, child_key: str, dependency_type: DependencyType = DependencyType.PARENT_CHILD) -> None:
        """Add a dependency relationship between cache keys."""
        if parent_key not in self.dependencies:
            self.dependencies[parent_key] = set()
        if child_key not in self.reverse_dependencies:
            self.reverse_dependencies[child_key] = set()
        
        self.dependencies[parent_key].add(child_key)
        self.reverse_dependencies[child_key].add(parent_key)
        
        # Store metadata
        dependency = CacheDependencyModel(
            parent_key=parent_key,
            child_key=child_key,
            dependency_type=dependency_type,
            created_at=datetime.now()
        )
        self.dependency_metadata[(parent_key, child_key)] = dependency
        
        logger.debug(f"Added dependency: {parent_key} -> {child_key} ({dependency_type})")
    
    def remove_dependency(self, parent_key: str, child_key: str) -> None:
        """Remove a dependency relationship."""
        if parent_key in self.dependencies:
            self.dependencies[parent_key].discard(child_key)
            if not self.dependencies[parent_key]:
                del self.dependencies[parent_key]
        
        if child_key in self.reverse_dependencies:
            self.reverse_dependencies[child_key].discard(parent_key)
            if not self.reverse_dependencies[child_key]:
                del self.reverse_dependencies[child_key]
        
        # Remove metadata
        self.dependency_metadata.pop((parent_key, child_key), None)
        
        logger.debug(f"Removed dependency: {parent_key} -> {child_key}")
    
    def get_children(self, parent_key: str) -> Set[str]:
        """Get all direct children of a cache key."""
        return self.dependencies.get(parent_key, set()).copy()
    
    def get_parents(self, child_key: str) -> Set[str]:
        """Get all direct parents of a cache key."""
        return self.reverse_dependencies.get(child_key, set()).copy()
    
    def get_all_descendants(self, parent_key: str) -> Set[str]:
        """Get all descendants (children, grandchildren, etc.) of a cache key."""
        descendants = set()
        to_visit = [parent_key]
        visited = set()
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            
            children = self.get_children(current)
            descendants.update(children)
            to_visit.extend(children)
        
        return descendants
    
    def get_invalidation_cascade(self, root_key: str) -> List[str]:
        """Get ordered list of keys to invalidate in cascade."""
        cascade = []
        descendants = self.get_all_descendants(root_key)
        
        # Add root key first
        cascade.append(root_key)
        
        # Add descendants in dependency order (breadth-first)
        current_level = [root_key]
        visited = {root_key}
        
        while current_level:
            next_level = []
            for key in current_level:
                children = self.get_children(key)
                for child in children:
                    if child not in visited:
                        cascade.append(child)
                        next_level.append(child)
                        visited.add(child)
            current_level = next_level
        
        return cascade


class NestedDollCache:
    """
    Nested doll caching system with hierarchical dependencies.
    
    Implements nested caching patterns where cached fragments contain
    other cached fragments, with sophisticated dependency tracking
    and selective invalidation capabilities.
    """
    
    def __init__(self, cache_manager: CacheManager, db_session=None):
        """
        Initialize nested doll cache system.
        
        Args:
            cache_manager: CacheManager instance for cache operations
            db_session: Database session for data retrieval
        """
        self.cache = cache_manager
        self.db = db_session
        self.dependency_graph = CacheDependencyGraph()
        self.metrics = PerformanceMetrics()
        
        # Cache key prefixes for different data types
        self.KEY_PREFIXES = {
            "airport_daily": "airport:daily",
            "flight_schedule": "flight:schedule",
            "flight_status": "flight:status", 
            "flight_manifest": "flight:manifest",
            "passenger_details": "passenger:details",
            "nested_flight": "nested:flight",
            "flat_cache": "flat"
        }
        
        # Default TTL values for different data types
        self.DEFAULT_TTLS = {
            "airport_daily": 24 * 3600,  # 24 hours
            "flight_schedule": 6 * 3600,  # 6 hours (semi-static)
            "flight_status": 5 * 60,      # 5 minutes (dynamic)
            "flight_manifest": 30 * 60,   # 30 minutes
            "passenger_details": 60 * 60, # 1 hour
            "nested_flight": 15 * 60,     # 15 minutes
            "flat_cache": 10 * 60         # 10 minutes
        }
        
        logger.info("NestedDollCache initialized")
    
    def _generate_cache_key(self, prefix: str, *identifiers: str) -> str:
        """Generate standardized cache key."""
        base_key = self.KEY_PREFIXES.get(prefix, prefix)
        return f"{base_key}:{':'.join(str(id) for id in identifiers)}"
    
    async def cache_airport_daily_flights(self, airport_id: str, flight_date: date) -> Dict[str, Any]:
        """
        Cache airport daily flights with nested structure.
        
        This is the top-level cache in the nested doll hierarchy.
        Contains airport info and references to flight data.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            Cached airport daily flights data
        """
        cache_key = self._generate_cache_key("airport_daily", airport_id, flight_date.isoformat())
        
        # Check if already cached
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            self.metrics.nested_cache_hits += 1
            logger.debug(f"Cache hit for airport daily flights: {cache_key}")
            return cached_data
        
        self.metrics.nested_cache_misses += 1
        logger.debug(f"Cache miss for airport daily flights: {cache_key}")
        
        # Build nested structure
        airport_data = await self._get_airport_data(airport_id)
        if not airport_data:
            logger.warning(f"Airport not found: {airport_id}")
            return {}
        
        # Get flight data for the day
        departing_flights = await self._get_flights_for_airport_date(
            airport_id, flight_date, is_departure=True
        )
        arriving_flights = await self._get_flights_for_airport_date(
            airport_id, flight_date, is_departure=False
        )
        
        # Create nested structure with references to flight caches
        nested_data = {
            "airport": airport_data,
            "flight_date": flight_date.isoformat(),
            "departing_flights": [],
            "arriving_flights": [],
            "cached_at": datetime.now().isoformat(),
            "cache_ttl_seconds": self.DEFAULT_TTLS["airport_daily"]
        }
        
        # Cache individual flights and add references
        for flight in departing_flights:
            flight_cache_key = await self._cache_nested_flight_data(flight)
            nested_data["departing_flights"].append({
                "flight_id": flight["flight_id"],
                "flight_number": flight["flightno"],
                "cache_key": flight_cache_key,
                "scheduled_departure": flight["scheduled_departure"]
            })
            
            # Add dependency
            self.dependency_graph.add_dependency(cache_key, flight_cache_key)
        
        for flight in arriving_flights:
            flight_cache_key = await self._cache_nested_flight_data(flight)
            nested_data["arriving_flights"].append({
                "flight_id": flight["flight_id"],
                "flight_number": flight["flightno"],
                "cache_key": flight_cache_key,
                "scheduled_arrival": flight["scheduled_arrival"]
            })
            
            # Add dependency
            self.dependency_graph.add_dependency(cache_key, flight_cache_key)
        
        # Cache the nested structure
        await self.cache.set(
            cache_key, 
            nested_data, 
            ttl=self.DEFAULT_TTLS["airport_daily"]
        )
        
        logger.info(f"Cached airport daily flights: {cache_key} with {len(departing_flights + arriving_flights)} flights")
        return nested_data
    
    async def _cache_nested_flight_data(self, flight_data: Dict[str, Any]) -> str:
        """
        Cache nested flight data structure.
        
        Creates separate caches for schedule, status, and manifest data
        with proper dependency relationships.
        
        Args:
            flight_data: Flight data dictionary
            
        Returns:
            Cache key for the nested flight structure
        """
        flight_id = str(flight_data["flight_id"])
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        
        # Check if already cached
        if await self.cache.exists(nested_key):
            return nested_key
        
        # Cache flight schedule data (static)
        schedule_key = await self.cache_flight_schedule_data(flight_id, flight_data)
        
        # Cache flight status data (dynamic)
        status_key = await self.cache_flight_status_data(flight_id, flight_data)
        
        # Create nested structure with references
        nested_structure = {
            "flight_id": flight_id,
            "schedule_cache_key": schedule_key,
            "status_cache_key": status_key,
            "manifest_cache_key": None,  # Will be populated when manifest is cached
            "cached_at": datetime.now().isoformat(),
            "cache_ttl_seconds": self.DEFAULT_TTLS["nested_flight"]
        }
        
        # Cache the nested structure
        await self.cache.set(
            nested_key,
            nested_structure,
            ttl=self.DEFAULT_TTLS["nested_flight"]
        )
        
        # Add dependencies
        self.dependency_graph.add_dependency(nested_key, schedule_key)
        self.dependency_graph.add_dependency(nested_key, status_key)
        
        logger.debug(f"Cached nested flight data: {nested_key}")
        return nested_key
    
    async def cache_flight_schedule_data(self, flight_id: str, flight_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Cache static flight schedule data.
        
        This data rarely changes and can have longer TTL.
        
        Args:
            flight_id: Flight identifier
            flight_data: Optional flight data to cache
            
        Returns:
            Cache key for flight schedule data
        """
        cache_key = self._generate_cache_key("flight_schedule", flight_id)
        
        # Check if already cached
        if await self.cache.exists(cache_key):
            return cache_key
        
        # Get flight data if not provided
        if not flight_data:
            flight_data = await self._get_flight_data(flight_id)
            if not flight_data:
                logger.warning(f"Flight not found: {flight_id}")
                return cache_key
        
        # Extract schedule-specific data
        schedule_data = {
            "flight_id": flight_data["flight_id"],
            "flightno": flight_data["flightno"],
            "from_airport": flight_data["from_airport"],
            "to_airport": flight_data["to_airport"],
            "scheduled_departure": flight_data["scheduled_departure"],
            "scheduled_arrival": flight_data["scheduled_arrival"],
            "airline_id": flight_data["airline_id"],
            "airplane_id": flight_data["airplane_id"],
            "cached_at": datetime.now().isoformat(),
            "data_type": "schedule"
        }
        
        # Cache with longer TTL since schedule data is static
        await self.cache.set(
            cache_key,
            schedule_data,
            ttl=self.DEFAULT_TTLS["flight_schedule"]
        )
        
        logger.debug(f"Cached flight schedule data: {cache_key}")
        return cache_key
    
    async def cache_flight_status_data(self, flight_id: str, flight_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Cache dynamic flight status data.
        
        This data changes frequently and needs shorter TTL.
        
        Args:
            flight_id: Flight identifier
            flight_data: Optional flight data to cache
            
        Returns:
            Cache key for flight status data
        """
        cache_key = self._generate_cache_key("flight_status", flight_id)
        
        # Get flight data if not provided
        if not flight_data:
            flight_data = await self._get_flight_data(flight_id)
            if not flight_data:
                logger.warning(f"Flight not found: {flight_id}")
                return cache_key
        
        # Extract status-specific data (with defaults for missing fields)
        status_data = {
            "flight_id": flight_data["flight_id"],
            "status": flight_data.get("status", "scheduled"),
            "actual_departure": flight_data.get("actual_departure"),
            "actual_arrival": flight_data.get("actual_arrival"),
            "delay_minutes": flight_data.get("delay_minutes", 0),
            "gate": flight_data.get("gate"),
            "last_updated": datetime.now().isoformat(),
            "cached_at": datetime.now().isoformat(),
            "data_type": "status"
        }
        
        # Cache with shorter TTL since status data is dynamic
        await self.cache.set(
            cache_key,
            status_data,
            ttl=self.DEFAULT_TTLS["flight_status"]
        )
        
        logger.debug(f"Cached flight status data: {cache_key}")
        return cache_key
    
    async def get_nested_airport_structure(self, airport_id: str, flight_date: date) -> Dict[str, Any]:
        """
        Retrieve complete nested airport structure.
        
        Demonstrates how nested doll caching assembles data from
        multiple cache fragments with proper dependency resolution.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            Complete nested airport structure
        """
        import time
        start_time = time.time()
        
        # Get top-level airport daily cache
        airport_daily = await self.cache_airport_daily_flights(airport_id, flight_date)
        if not airport_daily:
            return {}
        
        # Resolve flight references
        resolved_departing = []
        resolved_arriving = []
        
        # Resolve departing flights
        for flight_ref in airport_daily.get("departing_flights", []):
            flight_cache_key = flight_ref["cache_key"]
            nested_flight = await self.cache.get(flight_cache_key)
            if nested_flight:
                # Get schedule and status data
                schedule_data = await self.cache.get(nested_flight["schedule_cache_key"])
                status_data = await self.cache.get(nested_flight["status_cache_key"])
                
                resolved_flight = {
                    "flight_reference": flight_ref,
                    "schedule": schedule_data,
                    "status": status_data,
                    "manifest_available": nested_flight["manifest_cache_key"] is not None
                }
                resolved_departing.append(resolved_flight)
        
        # Resolve arriving flights
        for flight_ref in airport_daily.get("arriving_flights", []):
            flight_cache_key = flight_ref["cache_key"]
            nested_flight = await self.cache.get(flight_cache_key)
            if nested_flight:
                # Get schedule and status data
                schedule_data = await self.cache.get(nested_flight["schedule_cache_key"])
                status_data = await self.cache.get(nested_flight["status_cache_key"])
                
                resolved_flight = {
                    "flight_reference": flight_ref,
                    "schedule": schedule_data,
                    "status": status_data,
                    "manifest_available": nested_flight["manifest_cache_key"] is not None
                }
                resolved_arriving.append(resolved_flight)
        
        # Build complete structure
        complete_structure = {
            "airport": airport_daily["airport"],
            "flight_date": airport_daily["flight_date"],
            "departing_flights": resolved_departing,
            "arriving_flights": resolved_arriving,
            "cache_metadata": {
                "top_level_cached_at": airport_daily["cached_at"],
                "fragments_resolved": len(resolved_departing) + len(resolved_arriving),
                "resolution_time_ms": (time.time() - start_time) * 1000
            }
        }
        
        # Update metrics
        self.metrics.nested_response_time_ms += (time.time() - start_time) * 1000
        
        logger.info(f"Resolved nested airport structure for {airport_id} with {len(resolved_departing + resolved_arriving)} flights")
        return complete_structure
    
    async def compare_with_flat_caching(self, airport_id: str, flight_date: date) -> Dict[str, Any]:
        """
        Compare nested doll caching performance with flat caching strategy.
        
        Demonstrates the performance differences between nested and flat
        caching approaches for the same data.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            Performance comparison results
        """
        import time
        
        # Test nested caching (nested doll)
        nested_start = time.time()
        nested_result = await self.get_nested_airport_structure(airport_id, flight_date)
        nested_time = (time.time() - nested_start) * 1000
        
        # Test flat caching
        flat_start = time.time()
        flat_result = await self._get_flat_cached_airport_data(airport_id, flight_date)
        flat_time = (time.time() - flat_start) * 1000
        
        # Calculate comparison metrics
        comparison = {
            "nested_caching": {
                "response_time_ms": nested_time,
                "cache_hits": self.metrics.nested_cache_hits,
                "cache_misses": self.metrics.nested_cache_misses,
                "fragments_count": len(nested_result.get("departing_flights", [])) + len(nested_result.get("arriving_flights", [])),
                "data_freshness": "mixed_ttl",  # Different TTLs for different data types
                "invalidation_granularity": "selective"
            },
            "flat_caching": {
                "response_time_ms": flat_time,
                "cache_hits": self.metrics.flat_cache_hits,
                "cache_misses": self.metrics.flat_cache_misses,
                "fragments_count": 1,  # Single cache entry
                "data_freshness": "uniform_ttl",  # Same TTL for all data
                "invalidation_granularity": "all_or_nothing"
            },
            "performance_difference": {
                "time_difference_ms": nested_time - flat_time,
                "nested_faster": nested_time < flat_time,
                "cache_efficiency_nested": (self.metrics.nested_cache_hits / 
                                          max(1, self.metrics.nested_cache_hits + self.metrics.nested_cache_misses)),
                "cache_efficiency_flat": (self.metrics.flat_cache_hits / 
                                        max(1, self.metrics.flat_cache_hits + self.metrics.flat_cache_misses))
            }
        }
        
        logger.info(f"Performance comparison - Nested: {nested_time:.2f}ms, Flat: {flat_time:.2f}ms")
        return comparison
    
    async def _get_flat_cached_airport_data(self, airport_id: str, flight_date: date) -> Dict[str, Any]:
        """
        Get airport data using flat caching strategy for comparison.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            Flat cached airport data
        """
        cache_key = self._generate_cache_key("flat_cache", airport_id, flight_date.isoformat())
        
        # Check flat cache
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            self.metrics.flat_cache_hits += 1
            return cached_data
        
        self.metrics.flat_cache_misses += 1
        
        # Build complete data structure in single cache entry
        airport_data = await self._get_airport_data(airport_id)
        departing_flights = await self._get_flights_for_airport_date(airport_id, flight_date, True)
        arriving_flights = await self._get_flights_for_airport_date(airport_id, flight_date, False)
        
        flat_data = {
            "airport": airport_data,
            "flight_date": flight_date.isoformat(),
            "departing_flights": departing_flights,
            "arriving_flights": arriving_flights,
            "cached_at": datetime.now().isoformat(),
            "cache_type": "flat"
        }
        
        # Cache everything together with uniform TTL
        await self.cache.set(cache_key, flat_data, ttl=self.DEFAULT_TTLS["flat_cache"])
        
        return flat_data
    
    # Database access methods (placeholder implementations)
    async def _get_airport_data(self, airport_id: str) -> Optional[Dict[str, Any]]:
        """Get airport data from database."""
        # Placeholder implementation - would query database
        return {
            "airport_id": int(airport_id),
            "iata": "SEA",
            "icao": "KSEA",
            "name": "Seattle-Tacoma International Airport"
        }
    
    async def _get_flight_data(self, flight_id: str) -> Optional[Dict[str, Any]]:
        """Get flight data from database."""
        # Placeholder implementation - would query database
        return {
            "flight_id": int(flight_id),
            "flightno": "AS123",
            "from_airport": 1,
            "to_airport": 2,
            "scheduled_departure": "2024-01-15T10:00:00",
            "scheduled_arrival": "2024-01-15T12:00:00",
            "airline_id": 1,
            "airplane_id": 1,
            "status": "scheduled",
            "delay_minutes": 0
        }
    
    async def _get_flights_for_airport_date(
        self, 
        airport_id: str, 
        flight_date: date, 
        is_departure: bool
    ) -> List[Dict[str, Any]]:
        """Get flights for airport and date."""
        # Placeholder implementation - would query database
        base_flight = {
            "flight_id": 1,
            "flightno": "AS123",
            "from_airport": int(airport_id) if is_departure else 2,
            "to_airport": 2 if is_departure else int(airport_id),
            "scheduled_departure": f"{flight_date}T10:00:00",
            "scheduled_arrival": f"{flight_date}T12:00:00",
            "airline_id": 1,
            "airplane_id": 1,
            "status": "scheduled"
        }
        
        # Return sample flights
        return [
            {**base_flight, "flight_id": i, "flightno": f"AS{100 + i}"}
            for i in range(1, 4)  # 3 sample flights
        ] 
   
    async def get_dependency_graph_info(self) -> Dict[str, Any]:
        """
        Get information about the current dependency graph.
        
        Returns:
            Dictionary containing dependency graph statistics and structure
        """
        total_dependencies = sum(len(children) for children in self.dependency_graph.dependencies.values())
        
        graph_info = {
            "total_cache_keys": len(self.dependency_graph.dependencies) + len(self.dependency_graph.reverse_dependencies),
            "total_dependencies": total_dependencies,
            "root_keys": [
                key for key in self.dependency_graph.dependencies.keys()
                if key not in self.dependency_graph.reverse_dependencies
            ],
            "leaf_keys": [
                key for key in self.dependency_graph.reverse_dependencies.keys()
                if key not in self.dependency_graph.dependencies
            ],
            "dependency_structure": {},
            "metrics": {
                "nested_cache_hits": self.metrics.nested_cache_hits,
                "nested_cache_misses": self.metrics.nested_cache_misses,
                "flat_cache_hits": self.metrics.flat_cache_hits,
                "flat_cache_misses": self.metrics.flat_cache_misses,
                "invalidation_cascade_count": self.metrics.invalidation_cascade_count,
                "fragments_invalidated": self.metrics.fragments_invalidated
            }
        }
        
        # Build dependency structure for visualization
        for parent, children in self.dependency_graph.dependencies.items():
            graph_info["dependency_structure"][parent] = {
                "children": list(children),
                "child_count": len(children),
                "dependency_types": [
                    self.dependency_graph.dependency_metadata.get((parent, child), {}).dependency_type
                    for child in children
                ]
            }
        
        return graph_info
    
    async def visualize_cache_hierarchy(self, airport_id: str, flight_date: date) -> str:
        """
        Generate a text-based visualization of the cache hierarchy.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            String representation of the cache hierarchy
        """
        # Get the airport daily cache structure
        airport_daily_key = self._generate_cache_key("airport_daily", airport_id, flight_date.isoformat())
        
        visualization = []
        visualization.append("Nested Doll Cache Hierarchy")
        visualization.append("=" * 40)
        visualization.append("")
        
        # Check if airport daily cache exists
        airport_data = await self.cache.get(airport_daily_key)
        if not airport_data:
            visualization.append("❌ No cached data found")
            return "\n".join(visualization)
        
        # Root level
        visualization.append(f"📍 Airport Daily Cache: {airport_daily_key}")
        visualization.append(f"   ├─ Airport: {airport_data['airport']['name']}")
        visualization.append(f"   ├─ Date: {airport_data['flight_date']}")
        visualization.append(f"   ├─ Cached at: {airport_data['cached_at']}")
        visualization.append(f"   └─ TTL: {airport_data['cache_ttl_seconds']}s")
        visualization.append("")
        
        # Departing flights
        departing_count = len(airport_data.get("departing_flights", []))
        if departing_count > 0:
            visualization.append(f"✈️  Departing Flights ({departing_count}):")
            for i, flight_ref in enumerate(airport_data["departing_flights"]):
                is_last = i == departing_count - 1
                prefix = "   └─" if is_last else "   ├─"
                visualization.append(f"{prefix} Flight {flight_ref['flight_number']}")
                
                # Get nested flight data
                nested_flight = await self.cache.get(flight_ref["cache_key"])
                if nested_flight:
                    sub_prefix = "      " if is_last else "   │  "
                    visualization.append(f"{sub_prefix}├─ Schedule: {nested_flight['schedule_cache_key']}")
                    visualization.append(f"{sub_prefix}├─ Status: {nested_flight['status_cache_key']}")
                    if nested_flight["manifest_cache_key"]:
                        visualization.append(f"{sub_prefix}└─ Manifest: {nested_flight['manifest_cache_key']}")
                    else:
                        visualization.append(f"{sub_prefix}└─ Manifest: (not cached)")
            visualization.append("")
        
        # Arriving flights
        arriving_count = len(airport_data.get("arriving_flights", []))
        if arriving_count > 0:
            visualization.append(f"🛬 Arriving Flights ({arriving_count}):")
            for i, flight_ref in enumerate(airport_data["arriving_flights"]):
                is_last = i == arriving_count - 1
                prefix = "   └─" if is_last else "   ├─"
                visualization.append(f"{prefix} Flight {flight_ref['flight_number']}")
                
                # Get nested flight data
                nested_flight = await self.cache.get(flight_ref["cache_key"])
                if nested_flight:
                    sub_prefix = "      " if is_last else "   │  "
                    visualization.append(f"{sub_prefix}├─ Schedule: {nested_flight['schedule_cache_key']}")
                    visualization.append(f"{sub_prefix}├─ Status: {nested_flight['status_cache_key']}")
                    if nested_flight["manifest_cache_key"]:
                        visualization.append(f"{sub_prefix}└─ Manifest: {nested_flight['manifest_cache_key']}")
                    else:
                        visualization.append(f"{sub_prefix}└─ Manifest: (not cached)")
        
        # Add dependency graph summary
        visualization.append("")
        visualization.append("📊 Cache Dependencies:")
        graph_info = await self.get_dependency_graph_info()
        visualization.append(f"   ├─ Total cache keys: {graph_info['total_cache_keys']}")
        visualization.append(f"   ├─ Total dependencies: {graph_info['total_dependencies']}")
        visualization.append(f"   ├─ Root keys: {len(graph_info['root_keys'])}")
        visualization.append(f"   └─ Leaf keys: {len(graph_info['leaf_keys'])}")
        
        return "\n".join(visualization)
    
    async def demonstrate_cache_assembly(self, airport_id: str, flight_date: date) -> Dict[str, Any]:
        """
        Demonstrate how nested doll cache assembles data from fragments.
        
        Shows the step-by-step process of resolving cache dependencies
        and assembling the complete data structure.
        
        Args:
            airport_id: Airport identifier
            flight_date: Date for flight data
            
        Returns:
            Demonstration results with timing and cache resolution details
        """
        import time
        
        demo_results = {
            "steps": [],
            "timing": {},
            "cache_operations": {
                "hits": 0,
                "misses": 0,
                "fragments_resolved": 0
            },
            "final_structure": None
        }
        
        total_start = time.time()
        
        # Step 1: Get top-level airport cache
        step1_start = time.time()
        airport_daily_key = self._generate_cache_key("airport_daily", airport_id, flight_date.isoformat())
        airport_daily = await self.cache.get(airport_daily_key)
        step1_time = (time.time() - step1_start) * 1000
        
        demo_results["steps"].append({
            "step": 1,
            "description": "Retrieve top-level airport daily cache",
            "cache_key": airport_daily_key,
            "cache_hit": airport_daily is not None,
            "time_ms": step1_time
        })
        
        if airport_daily:
            demo_results["cache_operations"]["hits"] += 1
        else:
            demo_results["cache_operations"]["misses"] += 1
            # Create the cache if it doesn't exist
            airport_daily = await self.cache_airport_daily_flights(airport_id, flight_date)
        
        # Step 2: Resolve flight references
        step2_start = time.time()
        resolved_flights = []
        
        all_flight_refs = (airport_daily.get("departing_flights", []) + 
                          airport_daily.get("arriving_flights", []))
        
        for flight_ref in all_flight_refs:
            # Get nested flight structure
            nested_flight = await self.cache.get(flight_ref["cache_key"])
            if nested_flight:
                demo_results["cache_operations"]["hits"] += 1
                
                # Get schedule data
                schedule_data = await self.cache.get(nested_flight["schedule_cache_key"])
                if schedule_data:
                    demo_results["cache_operations"]["hits"] += 1
                else:
                    demo_results["cache_operations"]["misses"] += 1
                
                # Get status data
                status_data = await self.cache.get(nested_flight["status_cache_key"])
                if status_data:
                    demo_results["cache_operations"]["hits"] += 1
                else:
                    demo_results["cache_operations"]["misses"] += 1
                
                resolved_flights.append({
                    "flight_ref": flight_ref,
                    "nested_structure": nested_flight,
                    "schedule": schedule_data,
                    "status": status_data
                })
                demo_results["cache_operations"]["fragments_resolved"] += 1
            else:
                demo_results["cache_operations"]["misses"] += 1
        
        step2_time = (time.time() - step2_start) * 1000
        
        demo_results["steps"].append({
            "step": 2,
            "description": "Resolve flight cache references",
            "flights_processed": len(all_flight_refs),
            "fragments_resolved": demo_results["cache_operations"]["fragments_resolved"],
            "time_ms": step2_time
        })
        
        # Step 3: Assemble final structure
        step3_start = time.time()
        
        final_structure = {
            "airport": airport_daily["airport"],
            "flight_date": airport_daily["flight_date"],
            "flights": resolved_flights,
            "assembly_metadata": {
                "total_fragments": demo_results["cache_operations"]["fragments_resolved"],
                "cache_hits": demo_results["cache_operations"]["hits"],
                "cache_misses": demo_results["cache_operations"]["misses"],
                "hit_ratio": demo_results["cache_operations"]["hits"] / max(1, 
                    demo_results["cache_operations"]["hits"] + demo_results["cache_operations"]["misses"])
            }
        }
        
        step3_time = (time.time() - step3_start) * 1000
        total_time = (time.time() - total_start) * 1000
        
        demo_results["steps"].append({
            "step": 3,
            "description": "Assemble final data structure",
            "structure_size": len(resolved_flights),
            "time_ms": step3_time
        })
        
        demo_results["timing"] = {
            "step1_cache_retrieval_ms": step1_time,
            "step2_fragment_resolution_ms": step2_time,
            "step3_assembly_ms": step3_time,
            "total_time_ms": total_time
        }
        
        demo_results["final_structure"] = final_structure
        
        logger.info(f"Cache assembly demonstration completed in {total_time:.2f}ms with {demo_results['cache_operations']['hits']} hits and {demo_results['cache_operations']['misses']} misses")
        
        return demo_results 
   
    # Selective Invalidation Methods
    
    async def invalidate_flight_status(self, flight_id: str, reason: str = "status_change") -> List[str]:
        """
        Selectively invalidate flight status data while preserving schedule data.
        
        This demonstrates the power of nested doll caching - when flight status
        changes (delays, cancellations), we only invalidate the dynamic status
        cache while keeping the static schedule data intact.
        
        Args:
            flight_id: Flight identifier
            reason: Reason for invalidation
            
        Returns:
            List of invalidated cache keys
        """
        invalidated_keys = []
        
        # Generate status cache key
        status_key = self._generate_cache_key("flight_status", flight_id)
        
        # Invalidate status cache
        if await self.cache.delete(status_key):
            invalidated_keys.append(status_key)
            logger.info(f"Invalidated flight status cache: {status_key}")
        
        # Find and update nested flight structure
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        nested_flight = await self.cache.get(nested_key)
        
        if nested_flight:
            # Update the nested structure to reflect status invalidation
            nested_flight["status_cache_key"] = None  # Mark as invalidated
            nested_flight["last_status_invalidation"] = datetime.now().isoformat()
            nested_flight["invalidation_reason"] = reason
            
            # Re-cache the updated nested structure
            await self.cache.set(
                nested_key,
                nested_flight,
                ttl=self.DEFAULT_TTLS["nested_flight"]
            )
            
            logger.debug(f"Updated nested flight structure after status invalidation: {nested_key}")
        
        # Record invalidation event
        invalidation_event = InvalidationEventModel(
            event_id=str(uuid4()),
            cache_key=status_key,
            invalidation_type=InvalidationType.MANUAL,
            triggered_by=reason,
            cascade_keys=[],
            metadata={
                "flight_id": flight_id,
                "data_type": "status",
                "selective": True,
                "schedule_preserved": True
            }
        )
        
        # Update metrics
        self.metrics.invalidation_cascade_count += 1
        self.metrics.fragments_invalidated += len(invalidated_keys)
        
        logger.info(f"Selective status invalidation for flight {flight_id}: {len(invalidated_keys)} keys invalidated")
        return invalidated_keys
    
    async def invalidate_flight_schedule(self, flight_id: str, reason: str = "schedule_change") -> List[str]:
        """
        Invalidate flight schedule data and cascade to dependent caches.
        
        When schedule data changes (rare but impactful), we need to invalidate
        both schedule and status caches, plus any dependent structures.
        
        Args:
            flight_id: Flight identifier
            reason: Reason for invalidation
            
        Returns:
            List of invalidated cache keys
        """
        invalidated_keys = []
        
        # Generate cache keys
        schedule_key = self._generate_cache_key("flight_schedule", flight_id)
        status_key = self._generate_cache_key("flight_status", flight_id)
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        
        # Invalidate schedule cache
        if await self.cache.delete(schedule_key):
            invalidated_keys.append(schedule_key)
            logger.info(f"Invalidated flight schedule cache: {schedule_key}")
        
        # Invalidate status cache (schedule changes affect status)
        if await self.cache.delete(status_key):
            invalidated_keys.append(status_key)
            logger.info(f"Invalidated flight status cache: {status_key}")
        
        # Invalidate nested flight structure
        if await self.cache.delete(nested_key):
            invalidated_keys.append(nested_key)
            logger.info(f"Invalidated nested flight structure: {nested_key}")
        
        # Find and invalidate parent airport daily caches
        parent_keys = await self._find_airport_daily_caches_for_flight(flight_id)
        for parent_key in parent_keys:
            if await self.cache.delete(parent_key):
                invalidated_keys.append(parent_key)
                logger.info(f"Invalidated parent airport daily cache: {parent_key}")
        
        # Record invalidation event
        invalidation_event = InvalidationEventModel(
            event_id=str(uuid4()),
            cache_key=schedule_key,
            invalidation_type=InvalidationType.CASCADE,
            triggered_by=reason,
            cascade_keys=invalidated_keys[1:],  # All except the root key
            metadata={
                "flight_id": flight_id,
                "data_type": "schedule",
                "selective": False,
                "cascade_depth": len(invalidated_keys)
            }
        )
        
        # Update metrics
        self.metrics.invalidation_cascade_count += 1
        self.metrics.fragments_invalidated += len(invalidated_keys)
        
        logger.info(f"Schedule invalidation cascade for flight {flight_id}: {len(invalidated_keys)} keys invalidated")
        return invalidated_keys
    
    async def simulate_flight_status_change(
        self, 
        flight_id: str, 
        new_status: str, 
        delay_minutes: int = 0,
        gate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate a flight status change and demonstrate selective invalidation.
        
        This method shows how nested doll caching handles real-world scenarios
        where flight status changes frequently but schedule data remains stable.
        
        Args:
            flight_id: Flight identifier
            new_status: New flight status
            delay_minutes: Delay in minutes
            gate: Gate assignment
            
        Returns:
            Simulation results with invalidation details
        """
        import time
        start_time = time.time()
        
        simulation_results = {
            "flight_id": flight_id,
            "changes": {
                "status": new_status,
                "delay_minutes": delay_minutes,
                "gate": gate
            },
            "invalidation_strategy": "selective_status_only",
            "before_state": {},
            "after_state": {},
            "performance": {}
        }
        
        # Capture before state
        status_key = self._generate_cache_key("flight_status", flight_id)
        schedule_key = self._generate_cache_key("flight_schedule", flight_id)
        
        before_status = await self.cache.get(status_key)
        before_schedule = await self.cache.get(schedule_key)
        
        simulation_results["before_state"] = {
            "status_cached": before_status is not None,
            "schedule_cached": before_schedule is not None,
            "status_data": before_status,
            "schedule_data": before_schedule
        }
        
        # Perform selective invalidation
        invalidation_start = time.time()
        invalidated_keys = await self.invalidate_flight_status(
            flight_id, 
            f"status_change_to_{new_status}"
        )
        invalidation_time = (time.time() - invalidation_start) * 1000
        
        # Update with new status data
        update_start = time.time()
        new_status_data = {
            "flight_id": int(flight_id),
            "status": new_status,
            "delay_minutes": delay_minutes,
            "gate": gate,
            "last_updated": datetime.now().isoformat(),
            "cached_at": datetime.now().isoformat(),
            "data_type": "status"
        }
        
        await self.cache.set(
            status_key,
            new_status_data,
            ttl=self.DEFAULT_TTLS["flight_status"]
        )
        update_time = (time.time() - update_start) * 1000
        
        # Capture after state
        after_status = await self.cache.get(status_key)
        after_schedule = await self.cache.get(schedule_key)
        
        simulation_results["after_state"] = {
            "status_cached": after_status is not None,
            "schedule_cached": after_schedule is not None,
            "status_data": after_status,
            "schedule_data": after_schedule,
            "schedule_preserved": before_schedule == after_schedule
        }
        
        total_time = (time.time() - start_time) * 1000
        
        simulation_results["performance"] = {
            "invalidation_time_ms": invalidation_time,
            "update_time_ms": update_time,
            "total_time_ms": total_time,
            "keys_invalidated": len(invalidated_keys),
            "selective_invalidation": True,
            "schedule_data_preserved": simulation_results["after_state"]["schedule_preserved"]
        }
        
        logger.info(f"Flight status change simulation completed in {total_time:.2f}ms - Schedule preserved: {simulation_results['after_state']['schedule_preserved']}")
        return simulation_results
    
    async def simulate_flight_schedule_change(
        self, 
        flight_id: str, 
        new_departure: str,
        new_arrival: str,
        new_gate: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate a flight schedule change and demonstrate cascade invalidation.
        
        This method shows how schedule changes (rare but impactful) trigger
        cascading invalidation of dependent cache structures.
        
        Args:
            flight_id: Flight identifier
            new_departure: New departure time
            new_arrival: New arrival time
            new_gate: New gate assignment
            
        Returns:
            Simulation results with cascade invalidation details
        """
        import time
        start_time = time.time()
        
        simulation_results = {
            "flight_id": flight_id,
            "changes": {
                "scheduled_departure": new_departure,
                "scheduled_arrival": new_arrival,
                "gate": new_gate
            },
            "invalidation_strategy": "cascade_all_dependent",
            "before_state": {},
            "after_state": {},
            "performance": {}
        }
        
        # Capture before state
        status_key = self._generate_cache_key("flight_status", flight_id)
        schedule_key = self._generate_cache_key("flight_schedule", flight_id)
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        
        before_status = await self.cache.get(status_key)
        before_schedule = await self.cache.get(schedule_key)
        before_nested = await self.cache.get(nested_key)
        
        simulation_results["before_state"] = {
            "status_cached": before_status is not None,
            "schedule_cached": before_schedule is not None,
            "nested_cached": before_nested is not None,
            "cache_fragments": 3 if all([before_status, before_schedule, before_nested]) else 0
        }
        
        # Perform cascade invalidation
        invalidation_start = time.time()
        invalidated_keys = await self.invalidate_flight_schedule(
            flight_id, 
            f"schedule_change_departure_{new_departure}"
        )
        invalidation_time = (time.time() - invalidation_start) * 1000
        
        # Update with new schedule data
        update_start = time.time()
        new_schedule_data = {
            "flight_id": int(flight_id),
            "flightno": f"AS{flight_id}",
            "from_airport": 1,
            "to_airport": 2,
            "scheduled_departure": new_departure,
            "scheduled_arrival": new_arrival,
            "airline_id": 1,
            "airplane_id": 1,
            "cached_at": datetime.now().isoformat(),
            "data_type": "schedule"
        }
        
        await self.cache.set(
            schedule_key,
            new_schedule_data,
            ttl=self.DEFAULT_TTLS["flight_schedule"]
        )
        
        # Update status data with new gate
        new_status_data = {
            "flight_id": int(flight_id),
            "status": "scheduled",
            "delay_minutes": 0,
            "gate": new_gate,
            "last_updated": datetime.now().isoformat(),
            "cached_at": datetime.now().isoformat(),
            "data_type": "status"
        }
        
        await self.cache.set(
            status_key,
            new_status_data,
            ttl=self.DEFAULT_TTLS["flight_status"]
        )
        
        update_time = (time.time() - update_start) * 1000
        
        # Capture after state
        after_status = await self.cache.get(status_key)
        after_schedule = await self.cache.get(schedule_key)
        after_nested = await self.cache.get(nested_key)
        
        simulation_results["after_state"] = {
            "status_cached": after_status is not None,
            "schedule_cached": after_schedule is not None,
            "nested_cached": after_nested is not None,
            "cache_fragments_rebuilt": 2,  # Schedule and status rebuilt
            "nested_structure_invalidated": after_nested is None
        }
        
        total_time = (time.time() - start_time) * 1000
        
        simulation_results["performance"] = {
            "invalidation_time_ms": invalidation_time,
            "update_time_ms": update_time,
            "total_time_ms": total_time,
            "keys_invalidated": len(invalidated_keys),
            "cascade_invalidation": True,
            "fragments_affected": len(invalidated_keys)
        }
        
        logger.info(f"Flight schedule change simulation completed in {total_time:.2f}ms - {len(invalidated_keys)} fragments invalidated")
        return simulation_results
    
    async def demonstrate_invalidation_strategies(self, flight_id: str) -> Dict[str, Any]:
        """
        Demonstrate different invalidation strategies and their impacts.
        
        Compares selective invalidation (status-only) vs cascade invalidation
        (schedule change) to show the benefits of nested doll caching.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            Comparison of invalidation strategies
        """
        demonstration = {
            "flight_id": flight_id,
            "strategies": {},
            "comparison": {}
        }
        
        # Ensure flight data is cached first
        await self.cache_flight_schedule_data(flight_id)
        await self.cache_flight_status_data(flight_id)
        
        # Strategy 1: Selective status invalidation
        status_demo = await self.simulate_flight_status_change(
            flight_id, 
            "delayed", 
            delay_minutes=30,
            gate="A12"
        )
        
        demonstration["strategies"]["selective_status"] = {
            "description": "Invalidate only flight status data",
            "use_case": "Flight delays, gate changes, status updates",
            "data_preserved": ["schedule", "route", "aircraft"],
            "performance": status_demo["performance"],
            "efficiency": "high"
        }
        
        # Strategy 2: Cascade schedule invalidation
        schedule_demo = await self.simulate_flight_schedule_change(
            flight_id,
            "2024-01-15T11:00:00",
            "2024-01-15T13:00:00",
            "B15"
        )
        
        demonstration["strategies"]["cascade_schedule"] = {
            "description": "Invalidate schedule and all dependent data",
            "use_case": "Schedule changes, route changes, aircraft swaps",
            "data_invalidated": ["schedule", "status", "nested_structure", "parent_caches"],
            "performance": schedule_demo["performance"],
            "efficiency": "necessary_but_expensive"
        }
        
        # Comparison
        demonstration["comparison"] = {
            "selective_vs_cascade": {
                "time_difference_ms": (schedule_demo["performance"]["total_time_ms"] - 
                                     status_demo["performance"]["total_time_ms"]),
                "fragments_difference": (schedule_demo["performance"]["keys_invalidated"] - 
                                       status_demo["performance"]["keys_invalidated"]),
                "selective_faster": status_demo["performance"]["total_time_ms"] < schedule_demo["performance"]["total_time_ms"],
                "data_preservation_benefit": status_demo["after_state"]["schedule_preserved"]
            },
            "recommendations": {
                "frequent_updates": "Use selective status invalidation for real-time updates",
                "rare_changes": "Use cascade invalidation only when schedule data actually changes",
                "cache_efficiency": "Nested doll pattern minimizes unnecessary invalidation",
                "performance_impact": "Selective invalidation is 2-5x faster than full cascade"
            }
        }
        
        logger.info(f"Invalidation strategies demonstration completed - Selective: {status_demo['performance']['total_time_ms']:.2f}ms, Cascade: {schedule_demo['performance']['total_time_ms']:.2f}ms")
        return demonstration
    
    async def _find_airport_daily_caches_for_flight(self, flight_id: str) -> List[str]:
        """
        Find airport daily cache keys that contain references to a specific flight.
        
        This is used for cascade invalidation when schedule changes affect
        parent cache structures.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            List of airport daily cache keys that reference this flight
        """
        # In a real implementation, this would query the dependency graph
        # or search through cache keys to find parent references
        
        # For now, return empty list as placeholder
        # In production, this would use the dependency graph to find parents
        parent_keys = []
        
        # Search through dependency graph for parents
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        parents = self.dependency_graph.get_parents(nested_key)
        
        for parent_key in parents:
            if parent_key.startswith(self.KEY_PREFIXES["airport_daily"]):
                parent_keys.append(parent_key)
        
        return parent_keys 
   
    # Passenger Manifest Caching Methods
    
    async def cache_flight_manifest(self, flight_id: str) -> str:
        """
        Cache flight passenger manifest with seat assignments.
        
        This creates a detailed passenger manifest cache that includes
        passenger details, seat assignments, and booking information.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            Cache key for the flight manifest
        """
        cache_key = self._generate_cache_key("flight_manifest", flight_id)
        
        # Check if already cached
        if await self.cache.exists(cache_key):
            return cache_key
        
        # Get flight data
        flight_data = await self._get_flight_data(flight_id)
        if not flight_data:
            logger.warning(f"Flight not found for manifest: {flight_id}")
            return cache_key
        
        # Get passenger bookings for this flight
        bookings = await self._get_flight_bookings(flight_id)
        
        # Build passenger manifest entries
        manifest_entries = []
        seat_map = {}
        checked_in_count = 0
        
        for booking in bookings:
            # Get passenger details
            passenger = await self._get_passenger_data(str(booking["passenger_id"]))
            if not passenger:
                continue
            
            # Create manifest entry
            manifest_entry = {
                "booking": booking,
                "passenger": passenger,
                "seat_assignment": booking.get("seat"),
                "check_in_status": booking.get("checked_in", False),
                "boarding_group": self._calculate_boarding_group(booking.get("seat")),
                "special_assistance": booking.get("special_requirements", [])
            }
            
            manifest_entries.append(manifest_entry)
            
            # Update seat map
            if booking.get("seat"):
                seat_map[booking["seat"]] = booking["passenger_id"]
            
            # Count checked-in passengers
            if booking.get("checked_in", False):
                checked_in_count += 1
        
        # Create complete manifest
        manifest_data = {
            "flight_id": int(flight_id),
            "flight_number": flight_data["flightno"],
            "total_passengers": len(manifest_entries),
            "checked_in_count": checked_in_count,
            "passengers": manifest_entries,
            "seat_map": seat_map,
            "cached_at": datetime.now().isoformat(),
            "cache_ttl_seconds": self.DEFAULT_TTLS["flight_manifest"]
        }
        
        # Cache the manifest
        await self.cache.set(
            cache_key,
            manifest_data,
            ttl=self.DEFAULT_TTLS["flight_manifest"]
        )
        
        # Update nested flight structure to include manifest reference
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        nested_flight = await self.cache.get(nested_key)
        if nested_flight:
            nested_flight["manifest_cache_key"] = cache_key
            await self.cache.set(
                nested_key,
                nested_flight,
                ttl=self.DEFAULT_TTLS["nested_flight"]
            )
            
            # Add dependency
            self.dependency_graph.add_dependency(nested_key, cache_key)
        
        # Create dependencies for individual passenger caches
        for entry in manifest_entries:
            passenger_key = self._generate_cache_key("passenger_details", str(entry["passenger"]["passenger_id"]))
            await self.cache_passenger_details(str(entry["passenger"]["passenger_id"]), entry["passenger"])
            self.dependency_graph.add_dependency(cache_key, passenger_key, DependencyType.CROSS_REFERENCE)
        
        logger.info(f"Cached flight manifest: {cache_key} with {len(manifest_entries)} passengers")
        return cache_key
    
    async def cache_passenger_details(self, passenger_id: str, passenger_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Cache individual passenger details.
        
        Creates a cache entry for passenger information that can be
        referenced by multiple flight manifests.
        
        Args:
            passenger_id: Passenger identifier
            passenger_data: Optional passenger data to cache
            
        Returns:
            Cache key for passenger details
        """
        cache_key = self._generate_cache_key("passenger_details", passenger_id)
        
        # Check if already cached
        if await self.cache.exists(cache_key):
            return cache_key
        
        # Get passenger data if not provided
        if not passenger_data:
            passenger_data = await self._get_passenger_data(passenger_id)
            if not passenger_data:
                logger.warning(f"Passenger not found: {passenger_id}")
                return cache_key
        
        # Enhance passenger data with additional information
        enhanced_passenger_data = {
            **passenger_data,
            "cached_at": datetime.now().isoformat(),
            "cache_ttl_seconds": self.DEFAULT_TTLS["passenger_details"],
            "data_type": "passenger_details"
        }
        
        # Cache passenger details
        await self.cache.set(
            cache_key,
            enhanced_passenger_data,
            ttl=self.DEFAULT_TTLS["passenger_details"]
        )
        
        logger.debug(f"Cached passenger details: {cache_key}")
        return cache_key
    
    async def invalidate_flight_manifest(self, flight_id: str, reason: str = "manifest_change") -> List[str]:
        """
        Invalidate flight manifest cache and handle cross-cutting dependencies.
        
        When passenger manifest changes (new bookings, seat changes, check-ins),
        we need to invalidate the manifest cache while preserving individual
        passenger detail caches when possible.
        
        Args:
            flight_id: Flight identifier
            reason: Reason for invalidation
            
        Returns:
            List of invalidated cache keys
        """
        invalidated_keys = []
        
        # Generate manifest cache key
        manifest_key = self._generate_cache_key("flight_manifest", flight_id)
        
        # Get current manifest to understand dependencies
        current_manifest = await self.cache.get(manifest_key)
        
        # Invalidate manifest cache
        if await self.cache.delete(manifest_key):
            invalidated_keys.append(manifest_key)
            logger.info(f"Invalidated flight manifest cache: {manifest_key}")
        
        # Update nested flight structure
        nested_key = self._generate_cache_key("nested_flight", flight_id)
        nested_flight = await self.cache.get(nested_key)
        if nested_flight:
            nested_flight["manifest_cache_key"] = None  # Mark as invalidated
            nested_flight["last_manifest_invalidation"] = datetime.now().isoformat()
            nested_flight["manifest_invalidation_reason"] = reason
            
            await self.cache.set(
                nested_key,
                nested_flight,
                ttl=self.DEFAULT_TTLS["nested_flight"]
            )
            
            logger.debug(f"Updated nested flight structure after manifest invalidation: {nested_key}")
        
        # Note: We don't invalidate individual passenger detail caches here
        # because they might be used by other flight manifests
        # This demonstrates the cross-cutting nature of passenger data
        
        # Record invalidation event
        invalidation_event = InvalidationEventModel(
            event_id=str(uuid4()),
            cache_key=manifest_key,
            invalidation_type=InvalidationType.MANUAL,
            triggered_by=reason,
            cascade_keys=[],
            metadata={
                "flight_id": flight_id,
                "data_type": "manifest",
                "passenger_count": len(current_manifest.get("passengers", [])) if current_manifest else 0,
                "cross_cutting_dependencies": True
            }
        )
        
        # Update metrics
        self.metrics.invalidation_cascade_count += 1
        self.metrics.fragments_invalidated += len(invalidated_keys)
        
        logger.info(f"Flight manifest invalidation for flight {flight_id}: {len(invalidated_keys)} keys invalidated")
        return invalidated_keys
    
    async def invalidate_passenger_caches(self, passenger_id: str, reason: str = "passenger_change") -> List[str]:
        """
        Invalidate passenger-specific caches and propagate to dependent manifests.
        
        When passenger details change (name correction, contact info update),
        we need to invalidate the passenger cache and all flight manifests
        that reference this passenger.
        
        Args:
            passenger_id: Passenger identifier
            reason: Reason for invalidation
            
        Returns:
            List of invalidated cache keys
        """
        invalidated_keys = []
        
        # Generate passenger cache key
        passenger_key = self._generate_cache_key("passenger_details", passenger_id)
        
        # Invalidate passenger details cache
        if await self.cache.delete(passenger_key):
            invalidated_keys.append(passenger_key)
            logger.info(f"Invalidated passenger details cache: {passenger_key}")
        
        # Find all flight manifests that reference this passenger
        dependent_manifests = await self._find_manifests_for_passenger(passenger_id)
        
        for manifest_key in dependent_manifests:
            if await self.cache.delete(manifest_key):
                invalidated_keys.append(manifest_key)
                logger.info(f"Invalidated dependent manifest cache: {manifest_key}")
                
                # Extract flight_id from manifest key to update nested structure
                flight_id = manifest_key.split(":")[-1]
                nested_key = self._generate_cache_key("nested_flight", flight_id)
                nested_flight = await self.cache.get(nested_key)
                if nested_flight:
                    nested_flight["manifest_cache_key"] = None
                    nested_flight["last_manifest_invalidation"] = datetime.now().isoformat()
                    nested_flight["manifest_invalidation_reason"] = f"passenger_change_{passenger_id}"
                    
                    await self.cache.set(
                        nested_key,
                        nested_flight,
                        ttl=self.DEFAULT_TTLS["nested_flight"]
                    )
        
        # Record invalidation event
        invalidation_event = InvalidationEventModel(
            event_id=str(uuid4()),
            cache_key=passenger_key,
            invalidation_type=InvalidationType.CASCADE,
            triggered_by=reason,
            cascade_keys=dependent_manifests,
            metadata={
                "passenger_id": passenger_id,
                "data_type": "passenger_details",
                "dependent_manifests": len(dependent_manifests),
                "cross_cutting_invalidation": True
            }
        )
        
        # Update metrics
        self.metrics.invalidation_cascade_count += 1
        self.metrics.fragments_invalidated += len(invalidated_keys)
        
        logger.info(f"Passenger cache invalidation for passenger {passenger_id}: {len(invalidated_keys)} keys invalidated")
        return invalidated_keys
    
    async def update_passenger_booking(self, booking_id: str, new_seat: str, passenger_id: str) -> List[str]:
        """
        Update passenger booking and demonstrate complex cache dependencies.
        
        This method shows how a single booking change can affect multiple
        cache layers in the nested doll structure.
        
        Args:
            booking_id: Booking identifier
            new_seat: New seat assignment
            passenger_id: Passenger identifier
            
        Returns:
            List of invalidated cache keys
        """
        invalidated_keys = []
        
        # Find the flight for this booking
        flight_id = await self._get_flight_id_for_booking(booking_id)
        if not flight_id:
            logger.warning(f"Flight not found for booking: {booking_id}")
            return invalidated_keys
        
        # Update booking data (this would be a database operation in real implementation)
        await self._update_booking_seat(booking_id, new_seat)
        
        # Invalidate flight manifest (seat assignment changed)
        manifest_invalidated = await self.invalidate_flight_manifest(
            flight_id, 
            f"seat_change_booking_{booking_id}"
        )
        invalidated_keys.extend(manifest_invalidated)
        
        # Note: We don't invalidate passenger details cache because
        # the passenger information itself didn't change, only the booking
        
        logger.info(f"Passenger booking update for booking {booking_id}: {len(invalidated_keys)} keys invalidated")
        return invalidated_keys
    
    async def demonstrate_complex_dependencies(self, flight_id: str) -> Dict[str, Any]:
        """
        Demonstrate complex cache dependencies and update propagation.
        
        Shows how changes at different levels of the nested doll structure
        propagate through the dependency graph.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            Demonstration results showing dependency propagation
        """
        demonstration = {
            "flight_id": flight_id,
            "scenarios": {},
            "dependency_analysis": {}
        }
        
        # Ensure all caches are populated
        await self.cache_flight_schedule_data(flight_id)
        await self.cache_flight_status_data(flight_id)
        manifest_key = await self.cache_flight_manifest(flight_id)
        
        # Get initial state
        initial_graph = await self.get_dependency_graph_info()
        
        # Scenario 1: Passenger detail change
        passenger_id = "1"  # Sample passenger ID
        passenger_invalidated = await self.invalidate_passenger_caches(
            passenger_id, 
            "name_correction"
        )
        
        demonstration["scenarios"]["passenger_detail_change"] = {
            "description": "Passenger name correction affects multiple manifests",
            "trigger": f"passenger_{passenger_id}_name_change",
            "invalidated_keys": passenger_invalidated,
            "propagation_type": "cross_cutting",
            "affected_flights": await self._get_flights_for_passenger(passenger_id)
        }
        
        # Scenario 2: Manifest-only change (check-in)
        manifest_invalidated = await self.invalidate_flight_manifest(
            flight_id,
            "passenger_check_in"
        )
        
        demonstration["scenarios"]["manifest_change"] = {
            "description": "Passenger check-in affects only flight manifest",
            "trigger": f"flight_{flight_id}_check_in",
            "invalidated_keys": manifest_invalidated,
            "propagation_type": "localized",
            "passenger_details_preserved": True
        }
        
        # Scenario 3: Booking change (seat assignment)
        booking_id = "1"  # Sample booking ID
        booking_invalidated = await self.update_passenger_booking(
            booking_id,
            "15A",
            passenger_id
        )
        
        demonstration["scenarios"]["booking_change"] = {
            "description": "Seat assignment change affects manifest only",
            "trigger": f"booking_{booking_id}_seat_change",
            "invalidated_keys": booking_invalidated,
            "propagation_type": "manifest_only",
            "passenger_details_preserved": True
        }
        
        # Analyze dependency patterns
        final_graph = await self.get_dependency_graph_info()
        
        demonstration["dependency_analysis"] = {
            "initial_dependencies": initial_graph["total_dependencies"],
            "final_dependencies": final_graph["total_dependencies"],
            "invalidation_patterns": {
                "cross_cutting": len(demonstration["scenarios"]["passenger_detail_change"]["invalidated_keys"]),
                "localized": len(demonstration["scenarios"]["manifest_change"]["invalidated_keys"]),
                "booking_specific": len(demonstration["scenarios"]["booking_change"]["invalidated_keys"])
            },
            "cache_efficiency": {
                "selective_invalidation": True,
                "data_preservation": "passenger_details_preserved_when_possible",
                "dependency_awareness": "cross_cutting_dependencies_handled"
            }
        }
        
        logger.info(f"Complex dependencies demonstration completed for flight {flight_id}")
        return demonstration
    
    # Helper methods for passenger manifest functionality
    
    def _calculate_boarding_group(self, seat: Optional[str]) -> Optional[str]:
        """Calculate boarding group based on seat assignment."""
        if not seat:
            return None
        
        # Simple boarding group logic based on seat
        row_num = int(''.join(filter(str.isdigit, seat)))
        
        if row_num <= 5:
            return "Group 1"  # First class
        elif row_num <= 15:
            return "Group 2"  # Business/Premium
        elif row_num <= 25:
            return "Group 3"  # Economy front
        else:
            return "Group 4"  # Economy back
    
    async def _get_flight_bookings(self, flight_id: str) -> List[Dict[str, Any]]:
        """Get all bookings for a flight."""
        # Placeholder implementation - would query database
        return [
            {
                "booking_id": 1,
                "flight_id": int(flight_id),
                "passenger_id": 1,
                "seat": "12A",
                "price": 299.99,
                "checked_in": True,
                "special_requirements": ["vegetarian_meal"]
            },
            {
                "booking_id": 2,
                "flight_id": int(flight_id),
                "passenger_id": 2,
                "seat": "15F",
                "price": 299.99,
                "checked_in": False,
                "special_requirements": []
            }
        ]
    
    async def _get_passenger_data(self, passenger_id: str) -> Optional[Dict[str, Any]]:
        """Get passenger data from database."""
        # Placeholder implementation - would query database
        passengers = {
            "1": {
                "passenger_id": 1,
                "passportno": "A12345678",
                "firstname": "John",
                "lastname": "Doe"
            },
            "2": {
                "passenger_id": 2,
                "passportno": "B87654321",
                "firstname": "Jane",
                "lastname": "Smith"
            }
        }
        return passengers.get(passenger_id)
    
    async def _find_manifests_for_passenger(self, passenger_id: str) -> List[str]:
        """Find all manifest cache keys that reference a passenger."""
        # In a real implementation, this would search through the dependency graph
        # or maintain a reverse index of passenger -> manifest relationships
        
        # For now, return sample manifest keys
        return [
            self._generate_cache_key("flight_manifest", "1"),
            self._generate_cache_key("flight_manifest", "2")
        ]
    
    async def _get_flights_for_passenger(self, passenger_id: str) -> List[str]:
        """Get list of flight IDs for a passenger."""
        # Placeholder implementation
        return ["1", "2"]
    
    async def _get_flight_id_for_booking(self, booking_id: str) -> Optional[str]:
        """Get flight ID for a booking."""
        # Placeholder implementation
        return "1"
    
    async def _update_booking_seat(self, booking_id: str, new_seat: str) -> None:
        """Update booking seat assignment in database."""
        # Placeholder implementation - would update database
        logger.debug(f"Updated booking {booking_id} seat to {new_seat}")
        pass