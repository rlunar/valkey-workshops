"""
Write-Through Cache Pattern Demo

Demonstrates data consistency when updating flight information.
In write-through caching, updates are written to both the database
and cache simultaneously, ensuring consistency.

This demo shows:
1. Reading flight data (cache-aside pattern)
2. Updating flight departure time (write-through pattern)
3. Verifying consistency between database and cache
"""

import os
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# Load environment variables
load_dotenv()


class WriteThroughCache:
    """Write-through cache implementation for flight data."""
    
    def __init__(self):
        """Initialize database and cache connections."""
        self.db_engine = self._create_db_engine()
        self.cache_client = self._create_cache_client()
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))
    
    def _create_db_engine(self) -> Engine:
        """Create SQLAlchemy engine based on environment variables."""
        db_type = os.getenv("DB_ENGINE", "mysql").lower()
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "3306")
        db_user = os.getenv("DB_USER", "root")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "flughafendb_large")
        
        if db_type in ["mysql", "mariadb"]:
            connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        elif db_type == "postgresql":
            connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            raise ValueError(f"Unsupported DB_ENGINE: {db_type}")
        
        return create_engine(connection_string)
    
    def _create_cache_client(self) -> Any:
        """Create cache client based on environment variables."""
        cache_type = os.getenv("CACHE_ENGINE", "valkey").lower()
        cache_host = os.getenv("CACHE_HOST", "localhost")
        cache_port = int(os.getenv("CACHE_PORT", "6379"))
        
        if cache_type in ["redis", "valkey"]:
            try:
                import valkey
            except ImportError:
                import redis as valkey
            return valkey.Redis(
                host=cache_host,
                port=cache_port,
                decode_responses=True
            )
        elif cache_type == "memcached":
            from pymemcache.client import base
            return base.Client((cache_host, cache_port))
        else:
            raise ValueError(f"Unsupported CACHE_ENGINE: {cache_type}")
    
    def _generate_cache_key(self, entity_type: str, entity_id: int) -> str:
        """Generate cache key for entity."""
        return f"{entity_type}:{entity_id}"
    
    def _cache_get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        cache_type = os.getenv("CACHE_ENGINE", "valkey").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                return self.cache_client.get(key)
            elif cache_type == "memcached":
                value = self.cache_client.get(key)
                return value.decode() if value else None
        except Exception as e:
            print(f"Cache GET error: {e}")
            return None
    
    def _cache_set(self, key: str, value: str, ttl: int) -> None:
        """Set value in cache with TTL."""
        cache_type = os.getenv("CACHE_ENGINE", "valkey").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                self.cache_client.setex(key, ttl, value)
            elif cache_type == "memcached":
                self.cache_client.set(key, value.encode(), expire=ttl)
        except Exception as e:
            print(f"Cache SET error: {e}")
    
    def _cache_delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache_type = os.getenv("CACHE_ENGINE", "valkey").lower()
        
        try:
            if cache_type in ["redis", "valkey"]:
                return bool(self.cache_client.delete(key))
            elif cache_type == "memcached":
                return self.cache_client.delete(key)
        except Exception as e:
            print(f"Cache DELETE error: {e}")
            return False
    
    def get_flight(self, flight_id: int) -> Optional[Dict]:
        """
        Get flight data using cache-aside pattern.
        
        Args:
            flight_id: Flight ID to retrieve
        
        Returns:
            Flight data dictionary or None if not found
        """
        cache_key = self._generate_cache_key("flight", flight_id)
        
        # Try cache first
        cached_data = self._cache_get(cache_key)
        if cached_data:
            print(f"   ✓ Cache HIT for flight {flight_id}")
            return json.loads(cached_data)
        
        # Cache miss - query database
        print(f"   ✗ Cache MISS for flight {flight_id}")
        query = text("""
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
        """)
        
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"flight_id": flight_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            flight_data = dict(row._mapping)
            
            # Convert datetime objects to strings for JSON serialization
            for key, value in flight_data.items():
                if isinstance(value, datetime):
                    flight_data[key] = value.isoformat()
            
            # Store in cache
            self._cache_set(cache_key, json.dumps(flight_data), self.default_ttl)
            
            return flight_data
    
    def update_flight_departure(
        self, 
        flight_id: int, 
        new_departure: datetime,
        new_arrival: datetime,
        user: str = "system",
        comment: Optional[str] = None
    ) -> bool:
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
            True if update successful, False otherwise
        """
        try:
            with self.db_engine.begin() as conn:
                # Get current flight data for logging
                query = text("""
                    SELECT flight_id, flightno, `from`, `to`, 
                           departure, arrival, airline_id, airplane_id
                    FROM flight
                    WHERE flight_id = :flight_id
                """)
                result = conn.execute(query, {"flight_id": flight_id})
                old_data = result.fetchone()
                
                if not old_data:
                    print(f"   ✗ Flight {flight_id} not found")
                    return False
                
                old_dict = dict(old_data._mapping)
                
                # Update flight in database
                update_query = text("""
                    UPDATE flight
                    SET departure = :new_departure,
                        arrival = :new_arrival
                    WHERE flight_id = :flight_id
                """)
                conn.execute(update_query, {
                    "flight_id": flight_id,
                    "new_departure": new_departure,
                    "new_arrival": new_arrival
                })
                
                # Log the change
                log_query = text("""
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
                """)
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
                
                print(f"   ✓ Database updated for flight {flight_id}")
            
            # Write-through: Update cache immediately after database
            cache_key = self._generate_cache_key("flight", flight_id)
            
            # Delete old cache entry first to ensure fresh data
            self._cache_delete(cache_key)
            
            # Get fresh data from database to update cache (will be cache miss)
            updated_flight = self.get_flight(flight_id)
            if updated_flight:
                print(f"   ✓ Cache updated for flight {flight_id}")
            
            return True
            
        except Exception as e:
            print(f"   ✗ Update failed: {e}")
            return False
    
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
        cached_data = self._cache_get(cache_key)
        cache_flight = json.loads(cached_data) if cached_data else None
        
        # Get from database
        query = text("""
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
        """)
        
        with self.db_engine.connect() as conn:
            result = conn.execute(query, {"flight_id": flight_id})
            row = result.fetchone()
            
            if not row:
                return {"consistent": False, "error": "Flight not found in database"}
            
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
                "cache_data": None
            }
        
        # Check key fields
        consistent = (
            cache_flight.get("departure") == db_flight.get("departure") and
            cache_flight.get("arrival") == db_flight.get("arrival")
        )
        
        return {
            "consistent": consistent,
            "db_data": db_flight,
            "cache_data": cache_flight
        }
    
    def close(self):
        """Close database and cache connections."""
        self.db_engine.dispose()
        
        cache_type = os.getenv("CACHE_ENGINE", "redis").lower()
        if cache_type in ["redis", "valkey"]:
            self.cache_client.close()
        elif cache_type == "memcached":
            self.cache_client.close()


def print_flight_info(flight_data: Dict, title: str):
    """Pretty print flight information."""
    print(f"\n{title}")
    print("-" * 60)
    if flight_data:
        print(f"Flight ID:    {flight_data.get('flight_id')}")
        print(f"Flight No:    {flight_data.get('flightno')}")
        print(f"Route:        {flight_data.get('from_airport')} → {flight_data.get('to_airport')}")
        print(f"Airline:      {flight_data.get('airlinename')}")
        print(f"Departure:    {flight_data.get('departure')}")
        print(f"Arrival:      {flight_data.get('arrival')}")
    else:
        print("No data available")


def main():
    """Run write-through cache demonstration."""
    print("=" * 60)
    print("WRITE-THROUGH CACHE PATTERN DEMO")
    print("Demonstrating Data Consistency for Flight Updates")
    print("=" * 60)
    
    cache = WriteThroughCache()
    
    # Use a specific flight ID (you can change this)
    flight_id = 115
    
    try:
        # Step 1: Initial read (cache miss)
        print("\n[STEP 1] Initial read - Cache-Aside Pattern")
        print("-" * 60)
        flight = cache.get_flight(flight_id)
        print_flight_info(flight, "Initial Flight Data")
        
        if not flight:
            print(f"\n✗ Flight {flight_id} not found. Please use a valid flight_id.")
            return
        
        # Step 2: Second read (cache hit)
        print("\n[STEP 2] Second read - Should hit cache")
        print("-" * 60)
        flight = cache.get_flight(flight_id)
        print_flight_info(flight, "Cached Flight Data")
        
        # Step 3: Update flight times (write-through)
        print("\n[STEP 3] Update flight departure time - Write-Through Pattern")
        print("-" * 60)
        
        # Parse current times and add 2 hours delay
        current_departure = datetime.fromisoformat(flight["departure"])
        current_arrival = datetime.fromisoformat(flight["arrival"])
        
        new_departure = current_departure + timedelta(hours=2)
        new_arrival = current_arrival + timedelta(hours=2)
        
        print(f"Updating flight {flight_id}:")
        print(f"  Old departure: {current_departure}")
        print(f"  New departure: {new_departure}")
        print(f"  Old arrival:   {current_arrival}")
        print(f"  New arrival:   {new_arrival}")
        print()
        
        success = cache.update_flight_departure(
            flight_id=flight_id,
            new_departure=new_departure,
            new_arrival=new_arrival,
            user="demo_user",
            comment="Flight delayed by 2 hours due to weather"
        )
        
        if success:
            print("\n✓ Write-through update completed successfully")
        else:
            print("\n✗ Write-through update failed")
            return
        
        # Step 4: Verify consistency
        print("\n[STEP 4] Verify data consistency")
        print("-" * 60)
        consistency = cache.verify_consistency(flight_id)
        
        if consistency["consistent"]:
            print("✓ Data is CONSISTENT between database and cache")
            print_flight_info(consistency["db_data"], "Database Data")
            print_flight_info(consistency["cache_data"], "Cache Data")
        else:
            print("✗ Data INCONSISTENCY detected!")
            print(f"Reason: {consistency.get('reason', 'Unknown')}")
            print_flight_info(consistency.get("db_data"), "Database Data")
            print_flight_info(consistency.get("cache_data"), "Cache Data")
        
        # Step 5: Read updated data
        print("\n[STEP 5] Read updated flight data")
        print("-" * 60)
        updated_flight = cache.get_flight(flight_id)
        print_flight_info(updated_flight, "Updated Flight Data (from cache)")
        
        # Step 6: Restore original times
        print("\n[STEP 6] Restore original flight times")
        print("-" * 60)
        print("Restoring original departure and arrival times...")
        
        success = cache.update_flight_departure(
            flight_id=flight_id,
            new_departure=current_departure,
            new_arrival=current_arrival,
            user="demo_user",
            comment="Restoring original flight times after demo"
        )
        
        if success:
            print("\n✓ Original times restored")
            restored_flight = cache.get_flight(flight_id)
            print_flight_info(restored_flight, "Restored Flight Data")
        
    finally:
        cache.close()
        print("\n" + "=" * 60)
        print("Demo completed. Connections closed.")
        print("=" * 60)


if __name__ == "__main__":
    main()
