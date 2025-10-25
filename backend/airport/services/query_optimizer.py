"""
Database query optimization service with cache-aside pattern.

This module implements expensive database query optimization using Valkey caching
with cache-aside pattern, performance measurement, and cache effectiveness demonstration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, text

from ..database.models import Flight, Airport, Airline, Passenger, Booking
from ..database.config import get_db_session_context
from ..cache.manager import CacheManager
from ..cache.utils import key_manager
from ..models.flight import FlightModel, FlightScheduleModel, FlightStatusModel
from ..models.airport import AirportModel
from ..models.airline import AirlineModel
from ..models.passenger import PassengerModel, BookingModel
from ..models.enums import FlightStatus

logger = logging.getLogger(__name__)


@dataclass
class FlightSearchCriteria:
    """Flight search criteria for complex queries."""
    departure_airport: Optional[str] = None  # IATA or ICAO code
    arrival_airport: Optional[str] = None    # IATA or ICAO code
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    passenger_count: int = 1
    airline_preference: Optional[str] = None  # IATA code
    max_price: Optional[float] = None
    min_departure_time: Optional[str] = None  # HH:MM format
    max_departure_time: Optional[str] = None  # HH:MM format


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for query execution."""
    query_type: str
    cache_key: str
    execution_time_ms: float
    cache_hit: bool
    result_count: int
    database_query_time_ms: float = 0.0
    cache_operation_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "query_type": self.query_type,
            "cache_key": self.cache_key,
            "execution_time_ms": self.execution_time_ms,
            "cache_hit": self.cache_hit,
            "result_count": self.result_count,
            "database_query_time_ms": self.database_query_time_ms,
            "cache_operation_time_ms": self.cache_operation_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "performance_improvement": (
                self.database_query_time_ms / self.execution_time_ms 
                if self.execution_time_ms > 0 and self.cache_hit else 1.0
            )
        }


class QueryOptimizer:
    """
    Database query optimizer with cache-aside pattern and performance measurement.
    
    Features:
    - Complex flight search queries with multiple table joins
    - Cache-aside pattern with configurable TTL values
    - Query execution time measurement for cached vs non-cached requests
    - Performance metrics collection and analysis
    """
    
    def __init__(self, cache_manager: CacheManager, lock_manager: Optional['DistributedLockManager'] = None):
        """
        Initialize query optimizer.
        
        Args:
            cache_manager: CacheManager instance for caching operations
            lock_manager: Optional DistributedLockManager for stampede prevention
        """
        self.cache = cache_manager
        self.lock_manager = lock_manager
        if self.lock_manager is None:
            from .lock_manager import DistributedLockManager
            self.lock_manager = DistributedLockManager(cache_manager)
        self.metrics: List[QueryPerformanceMetrics] = []
        
        # Cache TTL configurations (in seconds)
        self.cache_ttls = {
            "flight_search": 300,      # 5 minutes for flight searches
            "airport_info": 3600,      # 1 hour for airport information
            "airline_info": 3600,      # 1 hour for airline information
            "route_analysis": 1800,    # 30 minutes for route analysis
            "passenger_manifest": 900, # 15 minutes for passenger manifests
            "popular_routes": 7200,    # 2 hours for popular routes
        }
        
        logger.info("QueryOptimizer initialized with cache-aside pattern")
    
    async def search_flights(
        self, 
        criteria: FlightSearchCriteria,
        use_cache: bool = True
    ) -> Tuple[List[FlightModel], QueryPerformanceMetrics]:
        """
        Search flights with complex criteria and caching.
        
        This method demonstrates expensive database queries with multiple joins
        and implements cache-aside pattern for performance optimization.
        
        Args:
            criteria: Flight search criteria
            use_cache: Whether to use caching (for demonstration purposes)
            
        Returns:
            Tuple of (flight list, performance metrics)
        """
        start_time = time.time()
        
        # Generate cache key based on search criteria
        cache_key = self._generate_flight_search_cache_key(criteria)
        
        # Initialize metrics
        metrics = QueryPerformanceMetrics(
            query_type="flight_search",
            cache_key=cache_key,
            execution_time_ms=0.0,
            cache_hit=False,
            result_count=0
        )
        
        flights = []
        
        if use_cache:
            # Try to get from cache first (cache-aside pattern)
            cache_start = time.time()
            cached_result = await self.cache.get(cache_key)
            metrics.cache_operation_time_ms = (time.time() - cache_start) * 1000
            
            if cached_result is not None:
                # Cache hit - deserialize and return
                flights = [FlightModel(**flight_data) for flight_data in cached_result]
                metrics.cache_hit = True
                metrics.result_count = len(flights)
                metrics.execution_time_ms = (time.time() - start_time) * 1000
                
                logger.debug(f"Cache hit for flight search: {cache_key}")
                self.metrics.append(metrics)
                return flights, metrics
        
        # Cache miss or caching disabled - query database
        logger.debug(f"Cache miss for flight search: {cache_key}")
        db_start = time.time()
        
        try:
            with get_db_session_context() as session:
                flights = await self._execute_complex_flight_query(session, criteria)
                
            metrics.database_query_time_ms = (time.time() - db_start) * 1000
            metrics.result_count = len(flights)
            
            # Cache the results if caching is enabled
            if use_cache and flights:
                cache_start = time.time()
                serializable_flights = [flight.model_dump() for flight in flights]
                await self.cache.set(
                    cache_key, 
                    serializable_flights, 
                    ttl=self.cache_ttls["flight_search"]
                )
                metrics.cache_operation_time_ms += (time.time() - cache_start) * 1000
                
        except Exception as e:
            logger.error(f"Error in flight search query: {e}")
            raise
        
        metrics.execution_time_ms = (time.time() - start_time) * 1000
        self.metrics.append(metrics)
        
        return flights, metrics
    
    async def _execute_complex_flight_query(
        self, 
        session: Session, 
        criteria: FlightSearchCriteria
    ) -> List[FlightModel]:
        """
        Execute complex flight search query with multiple joins.
        
        This demonstrates expensive database operations that benefit from caching.
        """
        # Build complex query with multiple joins
        query = session.query(Flight).options(
            joinedload(Flight.airline),
            joinedload(Flight.departure_airport),
            joinedload(Flight.arrival_airport),
            joinedload(Flight.bookings).joinedload(Booking.passenger)
        )
        
        # Apply filters based on search criteria
        filters = []
        
        # Airport filters (support both IATA and ICAO codes)
        if criteria.departure_airport:
            dep_airport_filter = or_(
                Airport.iata == criteria.departure_airport.upper(),
                Airport.icao == criteria.departure_airport.upper()
            )
            query = query.join(Airport, Flight.from_airport == Airport.airport_id)
            filters.append(dep_airport_filter)
        
        if criteria.arrival_airport:
            arr_airport_filter = or_(
                Airport.iata == criteria.arrival_airport.upper(),
                Airport.icao == criteria.arrival_airport.upper()
            )
            # Join with arrival airport (aliased to avoid conflicts)
            from sqlalchemy.orm import aliased
            ArrivalAirport = aliased(Airport)
            query = query.join(ArrivalAirport, Flight.to_airport == ArrivalAirport.airport_id)
            filters.append(or_(
                ArrivalAirport.iata == criteria.arrival_airport.upper(),
                ArrivalAirport.icao == criteria.arrival_airport.upper()
            ))
        
        # Date filters
        if criteria.departure_date:
            start_of_day = datetime.combine(criteria.departure_date, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            filters.append(and_(
                Flight.departure >= start_of_day,
                Flight.departure < end_of_day
            ))
        
        # Time filters
        if criteria.min_departure_time:
            min_time = datetime.strptime(criteria.min_departure_time, "%H:%M").time()
            filters.append(func.time(Flight.departure) >= min_time)
        
        if criteria.max_departure_time:
            max_time = datetime.strptime(criteria.max_departure_time, "%H:%M").time()
            filters.append(func.time(Flight.departure) <= max_time)
        
        # Airline filter
        if criteria.airline_preference:
            query = query.join(Airline, Flight.airline_id == Airline.airline_id)
            filters.append(Airline.iata == criteria.airline_preference.upper())
        
        # Price filter (requires subquery for booking prices)
        if criteria.max_price:
            price_subquery = session.query(Booking.flight_id).filter(
                Booking.price <= criteria.max_price
            ).subquery()
            filters.append(Flight.flight_id.in_(price_subquery))
        
        # Apply all filters
        if filters:
            query = query.filter(and_(*filters))
        
        # Execute query and convert to Pydantic models
        db_flights = query.limit(100).all()  # Limit results for performance
        
        flights = []
        for db_flight in db_flights:
            # Create flight schedule model
            schedule = FlightScheduleModel(
                flight_id=db_flight.flight_id,
                flightno=db_flight.flightno,
                from_airport=db_flight.from_airport,
                to_airport=db_flight.to_airport,
                scheduled_departure=db_flight.departure,
                scheduled_arrival=db_flight.arrival,
                airline_id=db_flight.airline_id,
                airplane_id=db_flight.airplane_id
            )
            
            # Create flight status model (simulated for workshop)
            status = FlightStatusModel(
                flight_id=db_flight.flight_id,
                status=FlightStatus.SCHEDULED,  # Default status
                delay_minutes=0,
                last_updated=datetime.now()
            )
            
            # Create related models
            airline = None
            if db_flight.airline:
                airline = AirlineModel(
                    airline_id=db_flight.airline.airline_id,
                    iata=db_flight.airline.iata,
                    airlinename=db_flight.airline.airlinename,
                    base_airport=db_flight.airline.base_airport
                )
            
            departure_airport = None
            if db_flight.departure_airport:
                departure_airport = AirportModel(
                    airport_id=db_flight.departure_airport.airport_id,
                    iata=db_flight.departure_airport.iata,
                    icao=db_flight.departure_airport.icao,
                    name=db_flight.departure_airport.name
                )
            
            arrival_airport = None
            if db_flight.arrival_airport:
                arrival_airport = AirportModel(
                    airport_id=db_flight.arrival_airport.airport_id,
                    iata=db_flight.arrival_airport.iata,
                    icao=db_flight.arrival_airport.icao,
                    name=db_flight.arrival_airport.name
                )
            
            # Create complete flight model
            flight = FlightModel(
                schedule=schedule,
                status=status,
                airline=airline,
                departure_airport=departure_airport,
                arrival_airport=arrival_airport
            )
            
            flights.append(flight)
        
        return flights
    
    def _generate_flight_search_cache_key(self, criteria: FlightSearchCriteria) -> str:
        """Generate cache key for flight search criteria."""
        key_parts = [
            "flight_search",
            criteria.departure_airport or "any",
            criteria.arrival_airport or "any",
            criteria.departure_date.isoformat() if criteria.departure_date else "any",
            criteria.return_date.isoformat() if criteria.return_date else "none",
            str(criteria.passenger_count),
            criteria.airline_preference or "any",
            str(criteria.max_price) if criteria.max_price else "any",
            criteria.min_departure_time or "any",
            criteria.max_departure_time or "any"
        ]
        return key_manager.key_builder.build_key("query", ":".join(key_parts))
    
    async def get_popular_routes(
        self, 
        limit: int = 10,
        use_cache: bool = True
    ) -> Tuple[List[Dict[str, Any]], QueryPerformanceMetrics]:
        """
        Get popular flight routes with booking statistics.
        
        This demonstrates another expensive query that benefits from caching.
        """
        start_time = time.time()
        cache_key = key_manager.key_builder.build_key("query", f"popular_routes:{limit}")
        
        metrics = QueryPerformanceMetrics(
            query_type="popular_routes",
            cache_key=cache_key,
            execution_time_ms=0.0,
            cache_hit=False,
            result_count=0
        )
        
        if use_cache:
            cache_start = time.time()
            cached_result = await self.cache.get(cache_key)
            metrics.cache_operation_time_ms = (time.time() - cache_start) * 1000
            
            if cached_result is not None:
                metrics.cache_hit = True
                metrics.result_count = len(cached_result)
                metrics.execution_time_ms = (time.time() - start_time) * 1000
                
                self.metrics.append(metrics)
                return cached_result, metrics
        
        # Execute expensive aggregation query
        db_start = time.time()
        
        try:
            with get_db_session_context() as session:
                # Complex query with multiple joins and aggregations
                query = session.query(
                    Airport.name.label('departure_airport'),
                    Airport.iata.label('departure_iata'),
                    func.count(Booking.booking_id).label('booking_count'),
                    func.avg(Booking.price).label('avg_price'),
                    func.count(func.distinct(Flight.flight_id)).label('flight_count')
                ).select_from(Flight)\
                .join(Airport, Flight.from_airport == Airport.airport_id)\
                .join(Booking, Flight.flight_id == Booking.flight_id)\
                .group_by(Airport.airport_id, Airport.name, Airport.iata)\
                .order_by(func.count(Booking.booking_id).desc())\
                .limit(limit)
                
                results = query.all()
                
                routes = []
                for result in results:
                    routes.append({
                        "departure_airport": result.departure_airport,
                        "departure_iata": result.departure_iata,
                        "booking_count": result.booking_count,
                        "avg_price": float(result.avg_price) if result.avg_price else 0.0,
                        "flight_count": result.flight_count
                    })
                
            metrics.database_query_time_ms = (time.time() - db_start) * 1000
            metrics.result_count = len(routes)
            
            # Cache the results
            if use_cache and routes:
                cache_start = time.time()
                await self.cache.set(
                    cache_key, 
                    routes, 
                    ttl=self.cache_ttls["popular_routes"]
                )
                metrics.cache_operation_time_ms += (time.time() - cache_start) * 1000
                
        except Exception as e:
            logger.error(f"Error in popular routes query: {e}")
            raise
        
        metrics.execution_time_ms = (time.time() - start_time) * 1000
        self.metrics.append(metrics)
        
        return routes, metrics
    
    async def get_flight_manifest(
        self, 
        flight_id: int,
        use_cache: bool = True
    ) -> Tuple[Dict[str, Any], QueryPerformanceMetrics]:
        """
        Get complete flight passenger manifest with detailed information.
        
        Another expensive query demonstrating complex joins and data aggregation.
        """
        start_time = time.time()
        cache_key = key_manager.key_builder.build_key("query", f"flight_manifest:{flight_id}")
        
        metrics = QueryPerformanceMetrics(
            query_type="flight_manifest",
            cache_key=cache_key,
            execution_time_ms=0.0,
            cache_hit=False,
            result_count=0
        )
        
        if use_cache:
            cache_start = time.time()
            cached_result = await self.cache.get(cache_key)
            metrics.cache_operation_time_ms = (time.time() - cache_start) * 1000
            
            if cached_result is not None:
                metrics.cache_hit = True
                metrics.result_count = len(cached_result.get("passengers", []))
                metrics.execution_time_ms = (time.time() - start_time) * 1000
                
                self.metrics.append(metrics)
                return cached_result, metrics
        
        # Execute complex manifest query
        db_start = time.time()
        
        try:
            with get_db_session_context() as session:
                # Get flight information with all related data
                flight = session.query(Flight).options(
                    joinedload(Flight.airline),
                    joinedload(Flight.departure_airport),
                    joinedload(Flight.arrival_airport),
                    joinedload(Flight.bookings).joinedload(Booking.passenger)
                ).filter(Flight.flight_id == flight_id).first()
                
                if not flight:
                    manifest = {"error": "Flight not found"}
                else:
                    # Build comprehensive manifest
                    passengers = []
                    for booking in flight.bookings:
                        passenger_data = {
                            "booking_id": booking.booking_id,
                            "seat": booking.seat,
                            "price": float(booking.price),
                            "passenger": {
                                "passenger_id": booking.passenger.passenger_id,
                                "passportno": booking.passenger.passportno,
                                "firstname": booking.passenger.firstname,
                                "lastname": booking.passenger.lastname
                            }
                        }
                        passengers.append(passenger_data)
                    
                    manifest = {
                        "flight_id": flight.flight_id,
                        "flight_number": flight.flightno,
                        "departure": flight.departure.isoformat(),
                        "arrival": flight.arrival.isoformat(),
                        "departure_airport": {
                            "name": flight.departure_airport.name,
                            "iata": flight.departure_airport.iata,
                            "icao": flight.departure_airport.icao
                        } if flight.departure_airport else None,
                        "arrival_airport": {
                            "name": flight.arrival_airport.name,
                            "iata": flight.arrival_airport.iata,
                            "icao": flight.arrival_airport.icao
                        } if flight.arrival_airport else None,
                        "airline": {
                            "name": flight.airline.airlinename,
                            "iata": flight.airline.iata
                        } if flight.airline else None,
                        "total_passengers": len(passengers),
                        "passengers": passengers,
                        "generated_at": datetime.now().isoformat()
                    }
                
            metrics.database_query_time_ms = (time.time() - db_start) * 1000
            metrics.result_count = len(manifest.get("passengers", []))
            
            # Cache the manifest
            if use_cache and "error" not in manifest:
                cache_start = time.time()
                await self.cache.set(
                    cache_key, 
                    manifest, 
                    ttl=self.cache_ttls["passenger_manifest"]
                )
                metrics.cache_operation_time_ms += (time.time() - cache_start) * 1000
                
        except Exception as e:
            logger.error(f"Error in flight manifest query: {e}")
            raise
        
        metrics.execution_time_ms = (time.time() - start_time) * 1000
        self.metrics.append(metrics)
        
        return manifest, metrics
    
    async def analyze_route_performance(
        self, 
        departure_airport: str, 
        arrival_airport: str,
        days_back: int = 30,
        use_cache: bool = True
    ) -> Tuple[Dict[str, Any], QueryPerformanceMetrics]:
        """
        Analyze route performance with complex aggregations and statistics.
        
        Demonstrates expensive analytical queries that greatly benefit from caching.
        """
        start_time = time.time()
        cache_key = key_manager.key_builder.build_key(
            "query", 
            f"route_analysis:{departure_airport}:{arrival_airport}:{days_back}"
        )
        
        metrics = QueryPerformanceMetrics(
            query_type="route_analysis",
            cache_key=cache_key,
            execution_time_ms=0.0,
            cache_hit=False,
            result_count=0
        )
        
        if use_cache:
            cache_start = time.time()
            cached_result = await self.cache.get(cache_key)
            metrics.cache_operation_time_ms = (time.time() - cache_start) * 1000
            
            if cached_result is not None:
                metrics.cache_hit = True
                metrics.result_count = 1
                metrics.execution_time_ms = (time.time() - start_time) * 1000
                
                self.metrics.append(metrics)
                return cached_result, metrics
        
        # Execute complex analytical query
        db_start = time.time()
        
        try:
            with get_db_session_context() as session:
                # Date range for analysis
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                # Complex query with multiple aggregations
                query = session.query(
                    func.count(Flight.flight_id).label('total_flights'),
                    func.count(Booking.booking_id).label('total_bookings'),
                    func.avg(Booking.price).label('avg_price'),
                    func.min(Booking.price).label('min_price'),
                    func.max(Booking.price).label('max_price'),
                    func.count(func.distinct(Passenger.passenger_id)).label('unique_passengers')
                ).select_from(Flight)\
                .join(Airport.query.filter(
                    or_(Airport.iata == departure_airport, Airport.icao == departure_airport)
                ).subquery(), Flight.from_airport == Airport.airport_id)\
                .join(Airport.query.filter(
                    or_(Airport.iata == arrival_airport, Airport.icao == arrival_airport)
                ).subquery(), Flight.to_airport == Airport.airport_id)\
                .outerjoin(Booking, Flight.flight_id == Booking.flight_id)\
                .outerjoin(Passenger, Booking.passenger_id == Passenger.passenger_id)\
                .filter(and_(
                    Flight.departure >= start_date,
                    Flight.departure <= end_date
                ))
                
                result = query.first()
                
                analysis = {
                    "route": f"{departure_airport} -> {arrival_airport}",
                    "analysis_period_days": days_back,
                    "total_flights": result.total_flights or 0,
                    "total_bookings": result.total_bookings or 0,
                    "unique_passengers": result.unique_passengers or 0,
                    "avg_price": float(result.avg_price) if result.avg_price else 0.0,
                    "min_price": float(result.min_price) if result.min_price else 0.0,
                    "max_price": float(result.max_price) if result.max_price else 0.0,
                    "load_factor": (
                        (result.total_bookings / result.total_flights) 
                        if result.total_flights and result.total_bookings else 0.0
                    ),
                    "generated_at": datetime.now().isoformat()
                }
                
            metrics.database_query_time_ms = (time.time() - db_start) * 1000
            metrics.result_count = 1
            
            # Cache the analysis
            if use_cache:
                cache_start = time.time()
                await self.cache.set(
                    cache_key, 
                    analysis, 
                    ttl=self.cache_ttls["route_analysis"]
                )
                metrics.cache_operation_time_ms += (time.time() - cache_start) * 1000
                
        except Exception as e:
            logger.error(f"Error in route analysis query: {e}")
            raise
        
        metrics.execution_time_ms = (time.time() - start_time) * 1000
        self.metrics.append(metrics)
        
        return analysis, metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary and cache effectiveness statistics.
        
        Returns:
            Dictionary with performance metrics and cache effectiveness data
        """
        if not self.metrics:
            return {"message": "No performance data available"}
        
        # Calculate statistics
        total_queries = len(self.metrics)
        cache_hits = sum(1 for m in self.metrics if m.cache_hit)
        cache_misses = total_queries - cache_hits
        
        hit_ratio = cache_hits / total_queries if total_queries > 0 else 0.0
        
        # Performance improvements
        cached_queries = [m for m in self.metrics if m.cache_hit]
        uncached_queries = [m for m in self.metrics if not m.cache_hit]
        
        avg_cached_time = (
            sum(m.execution_time_ms for m in cached_queries) / len(cached_queries)
            if cached_queries else 0.0
        )
        
        avg_uncached_time = (
            sum(m.execution_time_ms for m in uncached_queries) / len(uncached_queries)
            if uncached_queries else 0.0
        )
        
        performance_improvement = (
            avg_uncached_time / avg_cached_time 
            if avg_cached_time > 0 else 1.0
        )
        
        # Query type breakdown
        query_types = {}
        for metric in self.metrics:
            if metric.query_type not in query_types:
                query_types[metric.query_type] = {
                    "total": 0,
                    "cache_hits": 0,
                    "avg_time_ms": 0.0,
                    "avg_db_time_ms": 0.0
                }
            
            query_types[metric.query_type]["total"] += 1
            if metric.cache_hit:
                query_types[metric.query_type]["cache_hits"] += 1
            query_types[metric.query_type]["avg_time_ms"] += metric.execution_time_ms
            query_types[metric.query_type]["avg_db_time_ms"] += metric.database_query_time_ms
        
        # Calculate averages
        for qtype in query_types:
            total = query_types[qtype]["total"]
            query_types[qtype]["avg_time_ms"] /= total
            query_types[qtype]["avg_db_time_ms"] /= total
            query_types[qtype]["hit_ratio"] = query_types[qtype]["cache_hits"] / total
        
        return {
            "summary": {
                "total_queries": total_queries,
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "hit_ratio": hit_ratio,
                "avg_cached_response_time_ms": avg_cached_time,
                "avg_uncached_response_time_ms": avg_uncached_time,
                "performance_improvement_factor": performance_improvement,
                "time_saved_ms": (avg_uncached_time - avg_cached_time) * cache_hits
            },
            "query_types": query_types,
            "recent_metrics": [m.to_dict() for m in self.metrics[-10:]]  # Last 10 queries
        }
    
    def clear_metrics(self) -> None:
        """Clear collected performance metrics."""
        self.metrics.clear()
        logger.info("Performance metrics cleared")
    
    async def search_flights_with_stampede_prevention(
        self,
        criteria: FlightSearchCriteria,
        use_stampede_prevention: bool = True
    ) -> Tuple[List[FlightModel], QueryPerformanceMetrics]:
        """
        Search flights with cache stampede prevention using distributed locking.
        
        This method demonstrates how to prevent cache stampede scenarios where
        multiple concurrent requests try to rebuild the same expensive cache entry.
        
        Args:
            criteria: Flight search criteria
            use_stampede_prevention: Whether to use stampede prevention
            
        Returns:
            Tuple of (flight list, performance metrics)
        """
        if not use_stampede_prevention:
            return await self.search_flights(criteria, use_cache=True)
        
        cache_key = self._generate_flight_search_cache_key(criteria)
        
        async def rebuild_cache():
            """Cache rebuild function for stampede prevention."""
            # Execute the expensive database query
            with get_db_session_context() as session:
                flights = await self._execute_complex_flight_query(session, criteria)
                return [flight.model_dump() for flight in flights]
        
        start_time = time.time()
        
        try:
            # Use distributed locking to prevent stampede
            serializable_flights = await self.lock_manager.prevent_cache_stampede(
                cache_key=cache_key,
                cache_rebuild_func=rebuild_cache,
                cache_ttl=self.cache_ttls["flight_search"],
                lock_ttl=60,  # 1 minute lock TTL
                timeout_seconds=10.0
            )
            
            # Convert back to Pydantic models
            flights = [FlightModel(**flight_data) for flight_data in serializable_flights]
            
            # Create metrics
            metrics = QueryPerformanceMetrics(
                query_type="flight_search_stampede_prevention",
                cache_key=cache_key,
                execution_time_ms=(time.time() - start_time) * 1000,
                cache_hit=True,  # Data came from cache or was just cached
                result_count=len(flights)
            )
            
            self.metrics.append(metrics)
            return flights, metrics
            
        except Exception as e:
            logger.error(f"Error in stampede prevention for flight search: {e}")
            # Fallback to regular search
            return await self.search_flights(criteria, use_cache=True)
    
    async def demonstrate_concurrent_cache_access(
        self,
        criteria: FlightSearchCriteria,
        num_concurrent: int = 10
    ) -> Dict[str, Any]:
        """
        Demonstrate concurrent cache access with and without stampede prevention.
        
        This method shows the difference between regular caching and stampede prevention
        when multiple concurrent requests access the same expensive query.
        
        Args:
            criteria: Flight search criteria for the demonstration
            num_concurrent: Number of concurrent requests to simulate
            
        Returns:
            Dictionary with demonstration results and performance comparison
        """
        cache_key = self._generate_flight_search_cache_key(criteria)
        
        # Clear cache to ensure we start fresh
        await self.cache.delete(cache_key)
        
        async def regular_search(request_id: int) -> Dict[str, Any]:
            """Regular cache search without stampede prevention."""
            start_time = time.time()
            flights, metrics = await self.search_flights(criteria, use_cache=True)
            
            return {
                "request_id": request_id,
                "method": "regular_caching",
                "execution_time_ms": (time.time() - start_time) * 1000,
                "cache_hit": metrics.cache_hit,
                "result_count": len(flights),
                "database_query_time_ms": metrics.database_query_time_ms
            }
        
        async def stampede_prevention_search(request_id: int) -> Dict[str, Any]:
            """Search with stampede prevention."""
            start_time = time.time()
            flights, metrics = await self.search_flights_with_stampede_prevention(
                criteria, use_stampede_prevention=True
            )
            
            return {
                "request_id": request_id,
                "method": "stampede_prevention",
                "execution_time_ms": (time.time() - start_time) * 1000,
                "cache_hit": metrics.cache_hit,
                "result_count": len(flights),
                "database_query_time_ms": getattr(metrics, 'database_query_time_ms', 0.0)
            }
        
        # Test regular caching (clear cache first)
        await self.cache.delete(cache_key)
        regular_start = time.time()
        regular_tasks = [regular_search(i) for i in range(num_concurrent)]
        regular_results = await asyncio.gather(*regular_tasks, return_exceptions=True)
        regular_total_time = (time.time() - regular_start) * 1000
        
        # Wait a bit and clear cache for stampede prevention test
        await asyncio.sleep(0.5)
        await self.cache.delete(cache_key)
        
        # Test with stampede prevention
        stampede_start = time.time()
        stampede_tasks = [stampede_prevention_search(i) for i in range(num_concurrent)]
        stampede_results = await asyncio.gather(*stampede_tasks, return_exceptions=True)
        stampede_total_time = (time.time() - stampede_start) * 1000
        
        # Analyze results
        def analyze_results(results, method_name):
            valid_results = [r for r in results if isinstance(r, dict)]
            if not valid_results:
                return {"error": "No valid results"}
            
            cache_hits = sum(1 for r in valid_results if r.get("cache_hit", False))
            cache_misses = len(valid_results) - cache_hits
            
            execution_times = [r["execution_time_ms"] for r in valid_results]
            db_query_times = [r.get("database_query_time_ms", 0) for r in valid_results]
            
            return {
                "method": method_name,
                "total_requests": len(valid_results),
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "hit_ratio": cache_hits / len(valid_results),
                "avg_execution_time_ms": sum(execution_times) / len(execution_times),
                "min_execution_time_ms": min(execution_times),
                "max_execution_time_ms": max(execution_times),
                "total_db_query_time_ms": sum(db_query_times),
                "avg_db_query_time_ms": sum(db_query_times) / len(valid_results)
            }
        
        regular_analysis = analyze_results(regular_results, "regular_caching")
        stampede_analysis = analyze_results(stampede_results, "stampede_prevention")
        
        # Calculate performance improvement
        performance_improvement = {
            "total_time_improvement": (
                (regular_total_time - stampede_total_time) / regular_total_time * 100
                if regular_total_time > 0 else 0
            ),
            "avg_response_time_improvement": (
                (regular_analysis.get("avg_execution_time_ms", 0) - 
                 stampede_analysis.get("avg_execution_time_ms", 0)) /
                regular_analysis.get("avg_execution_time_ms", 1) * 100
                if regular_analysis.get("avg_execution_time_ms", 0) > 0 else 0
            ),
            "database_load_reduction": (
                (regular_analysis.get("total_db_query_time_ms", 0) - 
                 stampede_analysis.get("total_db_query_time_ms", 0)) /
                regular_analysis.get("total_db_query_time_ms", 1) * 100
                if regular_analysis.get("total_db_query_time_ms", 0) > 0 else 0
            )
        }
        
        return {
            "demonstration_summary": {
                "cache_key": cache_key,
                "concurrent_requests": num_concurrent,
                "regular_total_time_ms": regular_total_time,
                "stampede_prevention_total_time_ms": stampede_total_time,
                "performance_improvement": performance_improvement
            },
            "regular_caching_results": regular_analysis,
            "stampede_prevention_results": stampede_analysis,
            "detailed_results": {
                "regular": [r for r in regular_results if isinstance(r, dict)],
                "stampede_prevention": [r for r in stampede_results if isinstance(r, dict)]
            }
        }
    
    async def warm_cache_for_popular_routes(self) -> Dict[str, Any]:
        """
        Warm cache for popular routes and common searches.
        
        This method pre-loads frequently accessed data into the cache
        to improve performance for common queries.
        """
        start_time = time.time()
        warmed_keys = []
        
        try:
            # Get popular routes first
            popular_routes, _ = await self.get_popular_routes(limit=5, use_cache=False)
            
            # Warm cache for each popular route
            for route in popular_routes:
                if route.get("departure_iata"):
                    # Create search criteria for this route
                    criteria = FlightSearchCriteria(
                        departure_airport=route["departure_iata"],
                        departure_date=date.today()
                    )
                    
                    # Execute search to warm cache
                    _, metrics = await self.search_flights(criteria, use_cache=True)
                    warmed_keys.append(metrics.cache_key)
            
            # Warm cache for today's flights from major airports
            major_airports = ["LAX", "JFK", "LHR", "CDG", "NRT"]  # Example major airports
            for airport in major_airports:
                criteria = FlightSearchCriteria(
                    departure_airport=airport,
                    departure_date=date.today()
                )
                
                _, metrics = await self.search_flights(criteria, use_cache=True)
                warmed_keys.append(metrics.cache_key)
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "status": "success",
                "warmed_keys": len(warmed_keys),
                "execution_time_ms": execution_time,
                "cache_keys": warmed_keys
            }
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }