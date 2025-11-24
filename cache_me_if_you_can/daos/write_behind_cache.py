"""
Write-Behind Cache Pattern Implementation

In write-behind (write-back) caching, updates are written to the cache immediately
and queued for asynchronous database updates. This provides:
- Fast write performance (cache-speed writes)
- Eventual consistency with the database
- Batch processing of database updates

This module provides:
- WriteBehindCache: Main class for write-behind cache operations
- Queue-based asynchronous database updates using Valkey Lists
- Cache-aside reads with automatic cache population
- Background worker to process queued updates
"""

import os
import sys
from pathlib import Path

# Add parent directory to path when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import time
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import text

from core import get_db_engine, get_cache_client


class WriteBehindCache:
    """Write-behind cache implementation for flight data."""
    
    QUEUE_KEY = "flight_updates_queue"
    
    def __init__(self):
        """Initialize database and cache connections."""
        self.db_engine = get_db_engine()
        self.cache = get_cache_client()
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))
    
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
        cache_key = self._generate_cache_key("flight", flight_id)
        
        # Try cache first
        start_time = time.perf_counter()
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return json.loads(cached_data), "CACHE_HIT", latency_ms, cache_key, ""
        
        # Cache miss - query database
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
    ) -> tuple[bool, str]:
        """
        Update flight departure/arrival times using write-behind pattern.
        
        This provides fast writes by:
        1. Updating the cache immediately (fast)
        2. Queuing the database update for async processing
        3. Returning immediately without waiting for database
        
        Args:
            flight_id: Flight ID to update
            new_departure: New departure datetime
            new_arrival: New arrival datetime
            user: Username making the change
            comment: Optional comment explaining the change
        
        Returns:
            Tuple of (success, cache_key)
            - success: True if cache update and queue successful
            - cache_key: Cache key that was updated
        """
        cache_key = self._generate_cache_key("flight", flight_id)
        
        try:
            # Get current flight data from cache or database
            flight_data, _, _, _, _ = self.get_flight(flight_id)
            
            if not flight_data:
                return False, cache_key
            
            # Update cache immediately (write-behind: cache first)
            flight_data["departure"] = new_departure.isoformat()
            flight_data["arrival"] = new_arrival.isoformat()
            
            self.cache.set(cache_key, json.dumps(flight_data), self.default_ttl)
            
            # Queue the database update for async processing
            update_task = {
                "flight_id": flight_id,
                "new_departure": new_departure.isoformat(),
                "new_arrival": new_arrival.isoformat(),
                "user": user,
                "comment": comment or "Flight time updated",
                "queued_at": datetime.now().isoformat()
            }
            
            # Push to Valkey List (queue)
            self.cache.client.rpush(self.QUEUE_KEY, json.dumps(update_task))
            
            return True, cache_key
            
        except Exception as e:
            return False, cache_key
    
    def get_queue_length(self) -> int:
        """
        Get the number of pending updates in the queue.
        
        Returns:
            Number of items in the queue
        """
        return self.cache.client.llen(self.QUEUE_KEY)
    
    def process_queue(self, batch_size: int = 10) -> tuple[int, int, List[str]]:
        """
        Process queued database updates in batches.
        
        This is the background worker that:
        1. Dequeues update tasks from Valkey List
        2. Executes database updates
        3. Logs changes to flight_log table
        
        Args:
            batch_size: Maximum number of updates to process in one batch
        
        Returns:
            Tuple of (processed_count, failed_count, queries_executed)
            - processed_count: Number of successfully processed updates
            - failed_count: Number of failed updates
            - queries_executed: List of SQL queries executed
        """
        processed = 0
        failed = 0
        queries_executed = []
        
        for _ in range(batch_size):
            # Pop from left (FIFO queue)
            task_json = self.cache.client.lpop(self.QUEUE_KEY)
            
            if not task_json:
                break  # Queue is empty
            
            try:
                task = json.loads(task_json)
                
                flight_id = task["flight_id"]
                new_departure = datetime.fromisoformat(task["new_departure"])
                new_arrival = datetime.fromisoformat(task["new_arrival"])
                user = task["user"]
                comment = task["comment"]
                
                # Execute database update
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
                        failed += 1
                        continue
                    
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
                        "comment": comment
                    })
                
                processed += 1
                
            except Exception as e:
                failed += 1
                # Re-queue failed task (optional - could implement retry logic)
                # self.cache.client.rpush(self.QUEUE_KEY, task_json)
        
        return processed, failed, queries_executed
    
    def flush_queue(self) -> int:
        """
        Process all pending updates in the queue.
        
        Returns:
            Total number of updates processed
        """
        total_processed = 0
        
        while self.get_queue_length() > 0:
            processed, failed, _ = self.process_queue(batch_size=100)
            total_processed += processed
            
            if processed == 0:
                break  # No more items to process
        
        return total_processed
    
    def verify_consistency(self, flight_id: int) -> Dict:
        """
        Verify data consistency between database and cache.
        
        Note: In write-behind pattern, inconsistency is expected
        until the queue is processed.
        
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
                return {
                    "consistent": False, 
                    "error": "Flight not found in database", 
                    "query": query_str.strip(), 
                    "cache_key": cache_key
                }
            
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
            "cache_key": cache_key,
            "queue_length": self.get_queue_length()
        }
    
    def close(self):
        """Close database and cache connections."""
        self.db_engine.dispose()
        self.cache.close()


# Example usage
if __name__ == "__main__":
    from datetime import timedelta
    
    # Initialize write-behind cache handler
    cache = WriteBehindCache()
    
    # Use a specific flight ID
    flight_id = 115
    
    print("=" * 60)
    print("Write-Behind Cache Pattern Demo")
    print("=" * 60)
    
    # Step 1: Initial read (cache miss)
    print("\n1. First read (should be CACHE_MISS ❌):")
    flight, source, latency, cache_key, query = cache.get_flight(flight_id)
    print(f"   Source: {source}")
    print(f"   Latency: {latency:.3f} ms")
    print(f"   Cache Key: {cache_key}")
    if flight:
        print(f"   Flight: {flight['flightno']} - {flight['from_airport']} → {flight['to_airport']}")
    
    if flight:
        # Step 2: Update flight times (write-behind)
        print("\n2. Update flight times (write-behind - fast!):")
        current_departure = datetime.fromisoformat(flight["departure"])
        current_arrival = datetime.fromisoformat(flight["arrival"])
        
        new_departure = current_departure + timedelta(hours=2)
        new_arrival = current_arrival + timedelta(hours=2)
        
        print(f"   Old departure: {current_departure}")
        print(f"   New departure: {new_departure}")
        
        start = time.perf_counter()
        success, cache_key = cache.update_flight_departure(
            flight_id=flight_id,
            new_departure=new_departure,
            new_arrival=new_arrival,
            user="demo_user",
            comment="Flight delayed by 2 hours"
        )
        write_latency = (time.perf_counter() - start) * 1000
        
        if success:
            print(f"   ✓ Update successful (write latency: {write_latency:.3f} ms)")
            print(f"   ✓ Cache updated immediately")
            print(f"   ✓ Database update queued")
        else:
            print(f"   ✗ Update failed")
        
        # Step 3: Check queue
        print("\n3. Check queue status:")
        queue_length = cache.get_queue_length()
        print(f"   Queue length: {queue_length} pending update(s)")
        
        # Step 4: Verify consistency (should be inconsistent)
        print("\n4. Verify consistency (before queue processing):")
        consistency = cache.verify_consistency(flight_id)
        if consistency["consistent"]:
            print(f"   ✓ Data is CONSISTENT")
        else:
            print(f"   ⚠ Data INCONSISTENCY detected (expected in write-behind)")
            print(f"   Cache has new data, database update is queued")
        
        # Step 5: Process queue
        print("\n5. Process queue (background worker simulation):")
        processed, failed, queries = cache.process_queue()
        print(f"   ✓ Processed: {processed} update(s)")
        print(f"   ✗ Failed: {failed} update(s)")
        print(f"   Queries executed: {len(queries)}")
        
        # Step 6: Verify consistency (should be consistent now)
        print("\n6. Verify consistency (after queue processing):")
        consistency = cache.verify_consistency(flight_id)
        if consistency["consistent"]:
            print(f"   ✓ Data is now CONSISTENT")
        else:
            print(f"   ✗ Data still INCONSISTENT")
        
        # Step 7: Restore original times
        print("\n7. Restore original times:")
        success, cache_key = cache.update_flight_departure(
            flight_id=flight_id,
            new_departure=current_departure,
            new_arrival=current_arrival,
            user="demo_user",
            comment="Restoring original times"
        )
        
        if success:
            print(f"   ✓ Restore queued")
            # Flush queue to apply immediately
            processed = cache.flush_queue()
            print(f"   ✓ Queue flushed ({processed} update(s) processed)")
        else:
            print(f"   ✗ Restore failed")
    
    # Cleanup
    cache.close()
    print("\n" + "=" * 60)
