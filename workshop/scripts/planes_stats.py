#!/usr/bin/env python3
"""
Display statistics about aircraft types in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import Session, select, func
    from models.database import DatabaseManager
    from models.airplane_type import AirplaneType
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def show_airplane_type_statistics():
    """Display comprehensive aircraft type statistics"""
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("✈️  Aircraft Type Database Statistics")
        print("=" * 40)
        
        with Session(db_manager.engine) as session:
            # Basic counts
            total_types = session.exec(select(func.count(AirplaneType.type_id))).first()
            with_iata = session.exec(select(func.count(AirplaneType.type_id)).where(AirplaneType.iata.is_not(None))).first()
            with_icao = session.exec(select(func.count(AirplaneType.type_id)).where(AirplaneType.icao.is_not(None))).first()
            with_both = session.exec(
                select(func.count(AirplaneType.type_id))
                .where(AirplaneType.iata.is_not(None))
                .where(AirplaneType.icao.is_not(None))
            ).first()
            
            print(f"📊 Overview:")
            print(f"  Total aircraft types: {total_types:,}")
            print(f"  With IATA codes: {with_iata:,}")
            print(f"  With ICAO codes: {with_icao:,}")
            print(f"  With both codes: {with_both:,}")
            
            if total_types > 0:
                print(f"  IATA coverage: {with_iata/total_types*100:.1f}%")
                print(f"  ICAO coverage: {with_icao/total_types*100:.1f}%")
                print(f"  Both codes coverage: {with_both/total_types*100:.1f}%")
            
            # Top manufacturers by aircraft count (based on name patterns)
            print(f"\n🏭 Top Manufacturers by Aircraft Type Count:")
            
            # Get all aircraft names and analyze manufacturers
            all_types = session.exec(select(AirplaneType.name)).all()
            manufacturer_counts = {}
            
            for name in all_types:
                # Extract manufacturer from aircraft name (first word usually)
                if name:
                    manufacturer = name.split()[0] if name.split() else "Unknown"
                    manufacturer_counts[manufacturer] = manufacturer_counts.get(manufacturer, 0) + 1
            
            # Sort by count and show top 10
            sorted_manufacturers = sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True)
            for manufacturer, count in sorted_manufacturers[:10]:
                print(f"  {manufacturer}: {count:,} aircraft types")
            
            # Sample aircraft types with both codes
            print(f"\n✈️  Sample Aircraft Types with Both IATA and ICAO Codes:")
            sample_types = session.exec(
                select(AirplaneType)
                .where(AirplaneType.iata.is_not(None))
                .where(AirplaneType.icao.is_not(None))
                .limit(10)
            ).all()
            
            for aircraft_type in sample_types:
                print(f"  {aircraft_type.iata}/{aircraft_type.icao} - {aircraft_type.name}")
            
            # Aircraft types by code availability
            print(f"\n📈 Code Coverage:")
            iata_only = with_iata - with_both
            icao_only = with_icao - with_both
            no_codes = total_types - with_iata - icao_only
            
            print(f"  Both IATA & ICAO: {with_both:,} ({with_both/total_types*100:.1f}%)")
            print(f"  IATA only: {iata_only:,} ({iata_only/total_types*100:.1f}%)")
            print(f"  ICAO only: {icao_only:,} ({icao_only/total_types*100:.1f}%)")
            print(f"  No codes: {no_codes:,} ({no_codes/total_types*100:.1f}%)")
            
            # Show some examples of aircraft without codes
            if no_codes > 0:
                print(f"\n⚠️  Sample Aircraft Types Without Codes:")
                no_code_types = session.exec(
                    select(AirplaneType.name)
                    .where(AirplaneType.iata.is_(None))
                    .where(AirplaneType.icao.is_(None))
                    .limit(5)
                ).all()
                
                for name in no_code_types:
                    print(f"  {name}")
            
            return True
            
    except Exception as e:
        print(f"✗ Failed to get aircraft type statistics: {e}")
        return False

def main():
    """Main function"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    return show_airplane_type_statistics()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)