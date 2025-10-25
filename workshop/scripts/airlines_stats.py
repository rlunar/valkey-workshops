#!/usr/bin/env python3
"""
Display statistics about airlines in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select, func
    from models.database import DatabaseManager
    from models.airline import Airline
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def show_airline_statistics():
    """Display comprehensive airline statistics"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("✈️  Airline Database Statistics")
        print("=" * 35)
        
        with Session(db_manager.engine) as session:
            # Basic counts
            total_airlines = session.exec(select(func.count(Airline.airline_id))).first()
            active_airlines = session.exec(select(func.count(Airline.airline_id)).where(Airline.active == True)).first()
            inactive_airlines = session.exec(select(func.count(Airline.airline_id)).where(Airline.active == False)).first()
            
            with_iata = session.exec(select(func.count(Airline.airline_id)).where(Airline.iata.is_not(None))).first()
            with_icao = session.exec(select(func.count(Airline.airline_id)).where(Airline.icao.is_not(None))).first()
            with_callsign = session.exec(select(func.count(Airline.airline_id)).where(Airline.callsign.is_not(None))).first()
            
            print(f"📊 Overview:")
            print(f"  Total airlines: {total_airlines:,}")
            print(f"  Active airlines: {active_airlines:,}")
            print(f"  Inactive airlines: {inactive_airlines:,}")
            print(f"  With IATA codes: {with_iata:,}")
            print(f"  With ICAO codes: {with_icao:,}")
            print(f"  With callsigns: {with_callsign:,}")
            
            # Top countries by airline count
            print(f"\n🌍 Top 10 Countries by Airline Count:")
            country_stats = session.exec(
                select(Airline.country, func.count(Airline.airline_id).label('count'))
                .where(Airline.country.is_not(None))
                .group_by(Airline.country)
                .order_by(func.count(Airline.airline_id).desc())
                .limit(10)
            ).all()
            
            for country, count in country_stats:
                print(f"  {country}: {count:,} airlines")
            
            # Sample active airlines with IATA codes
            print(f"\n✈️  Sample Active Airlines with IATA Codes:")
            sample_airlines = session.exec(
                select(Airline)
                .where(Airline.active == True)
                .where(Airline.iata.is_not(None))
                .limit(10)
            ).all()
            
            for airline in sample_airlines:
                country_info = f" ({airline.country})" if airline.country else ""
                icao_info = f" [{airline.icao}]" if airline.icao else ""
                print(f"  {airline.iata} - {airline.name}{icao_info}{country_info}")
            
            # Airlines by status
            print(f"\n📈 Airlines by Status:")
            print(f"  Active: {active_airlines:,} ({active_airlines/total_airlines*100:.1f}%)")
            print(f"  Inactive: {inactive_airlines:,} ({inactive_airlines/total_airlines*100:.1f}%)")
            
            return True
            
    except Exception as e:
        print(f"✗ Failed to get airline statistics: {e}")
        return False

def main():
    """Main function"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    return show_airline_statistics()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)