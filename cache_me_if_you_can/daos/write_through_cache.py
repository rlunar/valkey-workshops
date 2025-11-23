"""
Write-Through Cache Pattern Implementation

In write-through caching, updates are written to both the database
and cache simultaneously, ensuring consistency.

This module provides:
- WriteThroughCache: Main class for write-through cache operations
- Cache-aside reads with automatic cache population
- Write-through updates with database and cache synchronization
- Data consistency verification between database and cache
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import text

from core import get_db_engine, get_cache_client


class WriteThroughCache:
    """Write-through cache implementation for flight data."""
    
    def __init__(self, verbose: bool = False):
        """Initialize database and cache connections.
        
        Args:
            verbose: If True, print SQL queries and cache keys
        """
        self.db_engine = get_db_engine()
        self.cache = get_cache_client()
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))
        self.verbose = verbose
    
    def _generate_cache_key(self, entity_type: str, entity_id: int) -> str:
        """Generate cache key for entity."""
        return f"{entity_type}:{entity_id}"
    
    def get_flight(self, flight_id: int) -> tuple[Optional[Dict], str, float, str, str]:
        """
        Get flight data using cache-aside pattern.
        
        Args:
            flight_id: Flight ID to retrieve
        
        Returns:
            Tuple of (flight_data, source, latency_ms, cache_key, query_str)
            - flight_data: Flight data dictionary or None if not found
            - source: "CACHE_HIT" or "CACHE_MISS"
            - latency_ms: Query latency in milliseconds
            - cache_key: Cache key used
            - query_str: SQL query executed (empty string if cache hit)
        """
        import time
        
        cache_key = self._generate_cache_key("flight", flight_id)
        
        # Try cache first
        start_time = time.perf_counter()
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            latency_ms = (time.perf_counter() - start_time) * 1000
            if not self.verbose:
                print(f"   ✓ Cache HIT for flight {flight_id}")
            return json.loads(cached_data), "CACHE_HIT", latency_ms, cache_key, ""
        
        # Cache miss - query database
        if not self.verbose:
            print(f"   ✗ Cache MISS for flight {flight_id}")
        
        query_str = """
            SELECT 
                f.flight_id,
                f.flightno,
                f.departure,
                f.arrival,
                f.airline_id,
                f.airplane_id,
                dep.iata as from_airport,
                arr.iata as to_airport,
                al.airlinename
            FROM flight f
            JOIN airport dep ON f.from = dep.airport_id
            JOIN airport arr ON f.to = arr.airport_id
            JOIN airline al ON f.airline_id = al.airline_id
            WHERE f.flight_id = :flight_id
        """
        
        query = text(query_str)
        
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"flight_id": flight_id})
            row = result.fetchone()
            
            if not row:
                latency_ms = (time.perf_counter() - start_time) * 1000
                return None, "CACHE_MISS", latency_ms, cache_key, query_str.strip()
            
            flight_data = dict(row._mapping)
            
            # Convert datetime objects to strings for JSON serialization
            for key, value in flight_data.items():
                if isinstance(value, datetime):
                    flight_data[key] = value.isoformat()
            
            # Store in cache
            self.cache.set(cache_key, json.dumps(flight_data), self.default_ttl)
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            return flight_data, "CACHE_MISS", latency_ms, cache_key, query_str.strip()
    
    def update_flight_departure(
        self, 
        flight_id: int, 
        new_departure: datetime,
        new_arrival: datetime,
        user: str = "system",
        comment: Optional[str] = None
    ) -> tuple[bool, list[str]]:
        """
        Update flight departure/arrival times using write-through pattern.
        
        This ensures data consistency by:
        1. Writing to the database first (source of truth)
        2. Updating the cache immediately
        3. Logging the change in flight_log
        
        Args:
            flight_id: Flight ID to update
            new_departure: New departure datetime
            new_arrival: New arrival datetime
            user: Username making the change
            comment: Optional comment explaining the change
        
        Returns:
            Tuple of (success, queries_executed)
            - success: True if update successful, False otherwise
            - queries_executed: List of SQL queries executed
        """
        queries_executed = []
        
        try:
            with self.db_engine.begin() as conn:
                # Get current flight data for logging
                select_query_str = """
                    SELECT flight_id, flightno, `from`, `to`, 
                           departure, arrival, airline_id, airplane_id
                    FROM flight
                    WHERE flight_id = :flight_id
                """
                queries_executed.append(select_query_str.strip())
                
                query = text(select_query_str)
                result = conn.execute(query, {"flight_id": flight_id})
                old_data = result.fetchone()
                
                if not old_data:
                    print(f"   ✗ Flight {flight_id} not found")
                    return False, queries_executed
                
                old_dict = dict(old_data._mapping)
                
                # Update flight in database
                update_query_str = """
                    UPDATE flight
                    SET departure = :new_departure,
                        arrival = :new_arrival
                    WHERE flight_id = :flight_id
                """
                queries_executed.append(update_query_str.strip())
                
                update_query = text(update_query_str)
                conn.execute(update_query, {
                    "flight_id": flight_id,
                    "new_departure": new_departure,
                    "new_arrival": new_arrival
                })
                
                # Log the change
                log_query_str = """
                    INSERT INTO flight_log (
                        log_date, user, flight_id,
                        flightno_old, flightno_new,
                        from_old, from_new,
                        to_old, to_new,
                        departure_old, departure_new,
                        arrival_old, arrival_new,
                        airplane_id_old, airplane_id_new,
                        airline_id_old, airline_id_new,
                        comment
                    ) VALUES (
                        NOW(), :user, :flight_id,
                        :flightno, :flightno,
                        :from_id, :from_id,
                        :to_id, :to_id,
                        :departure_old, :departure_new,
                        :arrival_old, :arrival_new,
                        :airplane_id, :airplane_id,
                        :airline_id, :airline_id,
                        :comment
                    )
                """
                queries_executed.append(log_query_str.strip())
                
                log_query = text(log_query_str)
                conn.execute(log_query, {
                    "user": user,
                    "flight_id": flight_id,
                    "flightno": old_dict["flightno"],
                    "from_id": old_dict["from"],
                    "to_id": old_dict["to"],
                    "departure_old": old_dict["departure"],
                    "departure_new": new_departure,
                    "arrival_old": old_dict["arrival"],
                    "arrival_new": new_arrival,
                    "airplane_id": old_dict["airplane_id"],
                    "airline_id": old_dict["airline_id"],
                    "comment": comment or "Flight time updated"
                })
                
                if not self.verbose:
                    print(f"   ✓ Database updated for flight {flight_id}")
            
            # Write-through: Update cache immediately after database
            cache_key = self._generate_cache_key("flight", flight_id)
            
            # Delete old cache entry first to ensure fresh data
            self.cache.delete(cache_key)
            
            # Get fresh data from database to update cache (will be cache miss)
            updated_flight = self.get_flight(flight_id)
            if updated_flight and not self.verbose:
                print(f"   ✓ Cache updated for flight {flight_id}")
            
            return True, queries_executed
            
        except Exception as e:
            print(f"   ✗ Update failed: {e}")
            return False, queries_executed
    
    def verify_consistency(self, flight_id: int) -> Dict:
        """
        Verify data consistency between database and cache.
        
        Args:
            flight_id: Flight ID to verify
        
        Returns:
            Dictionary with consistency check results
        """
        cache_key = self._generate_cache_key("flight", flight_id)
        
        # Get from cache
        cached_data = self.cache.get(cache_key)
        cache_flight = json.loads(cached_data) if cached_data else None
        
        # Get from database
        query_str = """
            SELECT 
                f.flight_id,
                f.flightno,
                f.departure,
                f.arrival,
                f.airline_id,
                f.airplane_id,
                dep.iata as from_airport,
                arr.iata as to_airport,
                al.airlinename
            FROM flight f
            JOIN airport dep ON f.from = dep.airport_id
            JOIN airport arr ON f.to = arr.airport_id
            JOIN airline al ON f.airline_id = al.airline_id
            WHERE f.flight_id = :flight_id
        """
        
        query = text(query_str)
        
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"flight_id": flight_id})
            row = result.fetchone()
            
            if not row:
                return {"consistent": False, "error": "Flight not found in database", "query": query_str.strip(), "cache_key": cache_key}
            
            db_flight = dict(row._mapping)
            for key, value in db_flight.items():
                if isinstance(value, datetime):
                    db_flight[key] = value.isoformat()
        
        # Compare
        if not cache_flight:
            return {
                "consistent": False,
                "reason": "Data exists in database but not in cache",
                "db_data": db_flight,
                "cache_data": None,
                "query": query_str.strip(),
                "cache_key": cache_key
            }
        
        # Check key fields
        consistent = (
            cache_flight.get("departure") == db_flight.get("departure") and
            cache_flight.get("arrival") == db_flight.get("arrival")
        )
        
        return {
            "consistent": consistent,
            "db_data": db_flight,
            "cache_data": cache_flight,
            "query": query_str.strip(),
            "cache_key": cache_key
        }
    
    def close(self):
        """Close database and cache connections."""
        self.db_engine.dispose()
        self.cache.close()
