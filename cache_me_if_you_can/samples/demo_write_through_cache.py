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

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from daos.write_through_cache import WriteThroughCache

# Load environment variables
load_dotenv()


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
