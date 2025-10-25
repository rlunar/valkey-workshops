#!/usr/bin/env python3
"""
Example script showing how to use Route data with Airport and Airline data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select, func
    from models.database import DatabaseManager
    from models import Route, Airport, Airline
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def show_route_examples():
    """Show examples of using Route data with Airport and Airline data"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("🛫 Route Data Examples")
        print("=" * 22)
        
        with Session(db_manager.engine) as session:
            # Check if we have data
            route_count = len(session.exec(select(Route)).all())
            airport_count = len(session.exec(select(Airport)).all())
            airline_count = len(session.exec(select(Airline)).all())
            
            print(f"Database contains:")
            print(f"- {route_count:,} routes")
            print(f"- {airport_count:,} airports")
            print(f"- {airline_count:,} airlines")
            
            if route_count == 0:
                print("\n⚠ No route data found. Run: python scripts/download_routes.py")
                return False
            
            print("\n" + "=" * 50)
            
            # Example 1: Find routes for specific airports
            print("\n1. Routes from major airports:")
            
            major_airports = ["JFK", "LAX", "LHR", "CDG", "NRT"]
            
            for airport_code in major_airports:
                routes_from_airport = session.exec(
                    select(Route)
                    .where(Route.source_airport_code == airport_code)
                    .limit(5)
                ).all()
                
                if routes_from_airport:
                    print(f"\n  Routes from {airport_code}:")
                    for route in routes_from_airport:
                        codeshare_info = " (Codeshare)" if route.codeshare else ""
                        stops_info = f" ({route.stops} stops)" if route.stops > 0 else " (Direct)"
                        equipment_info = f" [{route.equipment}]" if route.equipment else ""
                        print(f"    {route.airline_code}: {route.source_airport_code} → {route.destination_airport_code}{codeshare_info}{stops_info}{equipment_info}")
            
            # Example 2: Find routes for specific airlines
            print(f"\n2. Routes operated by major airlines:")
            
            major_airlines = ["AA", "UA", "DL", "BA", "LH"]
            
            for airline_code in major_airlines:
                route_count = session.exec(
                    select(func.count(Route.route_id))
                    .where(Route.airline_code == airline_code)
                ).first()
                
                sample_routes = session.exec(
                    select(Route)
                    .where(Route.airline_code == airline_code)
                    .limit(3)
                ).all()
                
                if sample_routes:
                    print(f"\n  {airline_code} operates {route_count} routes (sample):")
                    for route in sample_routes:
                        codeshare_info = " (Codeshare)" if route.codeshare else ""
                        stops_info = f" ({route.stops} stops)" if route.stops > 0 else " (Direct)"
                        print(f"    {route.source_airport_code} → {route.destination_airport_code}{codeshare_info}{stops_info}")
            
            # Example 3: Find popular city pairs
            print(f"\n3. Popular city pairs (routes between same airports):")
            
            popular_pairs = session.exec(
                select(Route.source_airport_code, Route.destination_airport_code, func.count(Route.route_id).label('route_count'))
                .group_by(Route.source_airport_code, Route.destination_airport_code)
                .having(func.count(Route.route_id) > 5)
                .order_by(func.count(Route.route_id).desc())
                .limit(10)
            ).all()
            
            for source, dest, count in popular_pairs:
                print(f"  {source} ↔ {dest}: {count} routes")
            
            # Example 4: Codeshare vs own-operated routes
            print(f"\n4. Codeshare analysis:")
            
            total_routes = session.exec(select(func.count(Route.route_id))).first()
            codeshare_routes = session.exec(
                select(func.count(Route.route_id))
                .where(Route.codeshare == True)
            ).first()
            
            print(f"  Total routes: {total_routes:,}")
            print(f"  Codeshare routes: {codeshare_routes:,} ({codeshare_routes/total_routes*100:.1f}%)")
            print(f"  Own-operated routes: {total_routes - codeshare_routes:,} ({(total_routes - codeshare_routes)/total_routes*100:.1f}%)")
            
            # Show sample codeshare routes
            print(f"\n  Sample codeshare routes:")
            codeshare_samples = session.exec(
                select(Route)
                .where(Route.codeshare == True)
                .limit(5)
            ).all()
            
            for route in codeshare_samples:
                equipment_info = f" [{route.equipment}]" if route.equipment else ""
                print(f"    {route.airline_code}: {route.source_airport_code} → {route.destination_airport_code} (Codeshare){equipment_info}")
            
            # Example 5: Routes with stops
            print(f"\n5. Routes with stops (non-direct flights):")
            
            routes_with_stops = session.exec(
                select(Route)
                .where(Route.stops > 0)
                .order_by(Route.stops.desc())
                .limit(10)
            ).all()
            
            if routes_with_stops:
                print(f"  Found {len(routes_with_stops)} routes with stops:")
                for route in routes_with_stops:
                    stops_label = f"{route.stops} stop{'s' if route.stops > 1 else ''}"
                    equipment_info = f" [{route.equipment}]" if route.equipment else ""
                    print(f"    {route.airline_code}: {route.source_airport_code} → {route.destination_airport_code} ({stops_label}){equipment_info}")
            else:
                print("  No routes with stops found in sample")
            
            # Example 6: Equipment analysis
            print(f"\n6. Aircraft equipment analysis:")
            
            # Count routes by equipment type
            equipment_stats = session.exec(
                select(Route.equipment, func.count(Route.route_id).label('count'))
                .where(Route.equipment.is_not(None))
                .group_by(Route.equipment)
                .order_by(func.count(Route.route_id).desc())
                .limit(10)
            ).all()
            
            print(f"  Top aircraft types by route count:")
            for equipment, count in equipment_stats:
                # Handle multiple aircraft types in one field
                aircraft_types = equipment.split() if equipment else []
                aircraft_display = ", ".join(aircraft_types[:3])  # Show first 3 types
                if len(aircraft_types) > 3:
                    aircraft_display += f" (+{len(aircraft_types)-3} more)"
                print(f"    {aircraft_display}: {count:,} routes")
            
            # Example 7: Route lookup functionality
            print(f"\n7. Route lookup examples:")
            
            # Find all routes between specific airports
            route_pairs = [("JFK", "LAX"), ("LHR", "JFK"), ("CDG", "NRT")]
            
            for source, dest in route_pairs:
                routes = session.exec(
                    select(Route)
                    .where(Route.source_airport_code == source)
                    .where(Route.destination_airport_code == dest)
                ).all()
                
                if routes:
                    print(f"\n  Routes from {source} to {dest} ({len(routes)} found):")
                    for route in routes[:5]:  # Show first 5
                        codeshare_info = " (Codeshare)" if route.codeshare else ""
                        equipment_info = f" [{route.equipment}]" if route.equipment else ""
                        print(f"    {route.airline_code}{codeshare_info}{equipment_info}")
                else:
                    print(f"\n  No direct routes found from {source} to {dest}")
            
            print(f"\n✅ Route data examples completed!")
            return True
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = show_route_examples()
    sys.exit(0 if success else 1)