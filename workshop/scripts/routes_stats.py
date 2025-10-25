#!/usr/bin/env python3
"""
Display statistics about routes in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select, func
    from models.database import DatabaseManager
    from models.route import Route
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def show_route_statistics():
    """Display comprehensive route statistics"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("🛫 Route Database Statistics")
        print("=" * 30)
        
        with Session(db_manager.engine) as session:
            # Basic counts
            total_routes = session.exec(select(func.count(Route.route_id))).first()
            codeshare_routes = session.exec(select(func.count(Route.route_id)).where(Route.codeshare == True)).first()
            direct_routes = session.exec(select(func.count(Route.route_id)).where(Route.stops == 0)).first()
            
            with_equipment = session.exec(select(func.count(Route.route_id)).where(Route.equipment.is_not(None))).first()
            
            print(f"📊 Overview:")
            print(f"  Total routes: {total_routes:,}")
            print(f"  Codeshare routes: {codeshare_routes:,}")
            print(f"  Direct routes: {direct_routes:,}")
            print(f"  Routes with equipment info: {with_equipment:,}")
            
            # Routes by number of stops
            print(f"\n🛬 Routes by Number of Stops:")
            stops_stats = session.exec(
                select(Route.stops, func.count(Route.route_id).label('count'))
                .group_by(Route.stops)
                .order_by(Route.stops)
                .limit(10)
            ).all()
            
            for stops, count in stops_stats:
                stops_label = "Direct" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
                print(f"  {stops_label}: {count:,} routes")
            
            # Top airlines by route count
            print(f"\n✈️  Top 10 Airlines by Route Count:")
            airline_stats = session.exec(
                select(Route.airline_code, func.count(Route.route_id).label('count'))
                .where(Route.airline_code.is_not(None))
                .group_by(Route.airline_code)
                .order_by(func.count(Route.route_id).desc())
                .limit(10)
            ).all()
            
            for airline_code, count in airline_stats:
                print(f"  {airline_code}: {count:,} routes")
            
            # Top source airports by route count
            print(f"\n🛫 Top 10 Source Airports by Route Count:")
            source_stats = session.exec(
                select(Route.source_airport_code, func.count(Route.route_id).label('count'))
                .where(Route.source_airport_code.is_not(None))
                .group_by(Route.source_airport_code)
                .order_by(func.count(Route.route_id).desc())
                .limit(10)
            ).all()
            
            for airport_code, count in source_stats:
                print(f"  {airport_code}: {count:,} routes")
            
            # Top destination airports by route count
            print(f"\n🛬 Top 10 Destination Airports by Route Count:")
            dest_stats = session.exec(
                select(Route.destination_airport_code, func.count(Route.route_id).label('count'))
                .where(Route.destination_airport_code.is_not(None))
                .group_by(Route.destination_airport_code)
                .order_by(func.count(Route.route_id).desc())
                .limit(10)
            ).all()
            
            for airport_code, count in dest_stats:
                print(f"  {airport_code}: {count:,} routes")
            
            # Sample routes
            print(f"\n🗺️  Sample Routes:")
            sample_routes = session.exec(
                select(Route)
                .limit(10)
            ).all()
            
            for route in sample_routes:
                codeshare_info = " (Codeshare)" if route.codeshare else ""
                stops_info = f" ({route.stops} stops)" if route.stops > 0 else " (Direct)"
                equipment_info = f" [{route.equipment}]" if route.equipment else ""
                print(f"  {route.airline_code}: {route.source_airport_code} → {route.destination_airport_code}{codeshare_info}{stops_info}{equipment_info}")
            
            # Route type breakdown
            print(f"\n📈 Route Type Breakdown:")
            print(f"  Direct routes: {direct_routes:,} ({direct_routes/total_routes*100:.1f}%)")
            print(f"  Routes with stops: {total_routes - direct_routes:,} ({(total_routes - direct_routes)/total_routes*100:.1f}%)")
            print(f"  Codeshare routes: {codeshare_routes:,} ({codeshare_routes/total_routes*100:.1f}%)")
            print(f"  Own-operated routes: {total_routes - codeshare_routes:,} ({(total_routes - codeshare_routes)/total_routes*100:.1f}%)")
            
            return True
            
    except Exception as e:
        print(f"✗ Failed to get route statistics: {e}")
        return False

def main():
    """Main function"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    return show_route_statistics()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)