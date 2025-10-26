#!/usr/bin/env python3
"""
Aircraft Fleet Population Script

Generate realistic aircraft fleets for each airline based on airplane types.
Creates dedicated fleets per airline with realistic compositions based on 
airline characteristics (international, regional, low-cost, charter, etc.).
This creates the aircraft data needed for flight generation.
"""

import os
import sys
import random
from typing import Dict, List, Any
from sqlmodel import Session, select, func

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import DatabaseManager
    from models.airplane import Airplane
    from models.airplane_type import AirplaneType
    from models.airline import Airline
    from dotenv import load_dotenv
    from tqdm import tqdm
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False


class AircraftPopulator:
    """Generate realistic aircraft fleets for airlines based on airplane types and airline characteristics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
        # Common aircraft capacity mappings (approximate)
        self.aircraft_capacities = {
            # Wide-body aircraft
            'A380': 550, 'A350': 350, 'A330': 300, 'A340': 320,
            'B777': 350, 'B787': 280, 'B747': 400, 'B767': 250,
            
            # Narrow-body aircraft  
            'A320': 180, 'A321': 220, 'A319': 150, 'A318': 130,
            'B737': 180, 'B738': 180, 'B739': 180, 'B733': 150,
            'B757': 200, 'B752': 200,
            
            # Regional aircraft
            'E190': 100, 'E175': 80, 'E170': 70, 'E145': 50,
            'CRJ': 50, 'CR7': 70, 'CR9': 90, 'AT7': 70,
            'DH8': 80, 'SF3': 50, 'J41': 30,
            
            # Small aircraft
            'BE1': 8, 'BE9': 15, 'C25': 8, 'C56': 10,
            'PA3': 6, 'PC1': 10, 'TBM': 6,
            
            # Default capacities by category
            'default_wide': 300,
            'default_narrow': 150,
            'default_regional': 70,
            'default_small': 20
        }
    
    def estimate_aircraft_capacity(self, aircraft_name: str, iata_code: str = None, icao_code: str = None) -> int:
        """Estimate aircraft capacity based on name and codes"""
        
        name_upper = aircraft_name.upper()
        
        # Try exact matches first
        for code, capacity in self.aircraft_capacities.items():
            if code in name_upper:
                return capacity
        
        # Try IATA/ICAO codes
        if iata_code:
            iata_upper = iata_code.upper()
            for code, capacity in self.aircraft_capacities.items():
                if code == iata_upper:
                    return capacity
        
        if icao_code:
            icao_upper = icao_code.upper()
            for code, capacity in self.aircraft_capacities.items():
                if code == icao_upper:
                    return capacity
        
        # Categorize by common patterns
        if any(x in name_upper for x in ['A380', 'A350', 'A330', 'A340', 'B777', 'B787', 'B747', 'B767']):
            return self.aircraft_capacities['default_wide']
        elif any(x in name_upper for x in ['A320', 'A321', 'A319', 'B737', 'B738', 'B757']):
            return self.aircraft_capacities['default_narrow']
        elif any(x in name_upper for x in ['E1', 'CRJ', 'CR', 'AT', 'DH', 'SF', 'J4']):
            return self.aircraft_capacities['default_regional']
        else:
            return self.aircraft_capacities['default_small']
    
    def get_airplane_types(self, session: Session) -> List[Dict[str, Any]]:
        """Get all airplane types from database"""
        
        types_query = select(AirplaneType)
        airplane_types = []
        
        for airplane_type in session.exec(types_query).all():
            capacity = self.estimate_aircraft_capacity(
                airplane_type.name or "Unknown",
                airplane_type.iata,
                airplane_type.icao
            )
            
            airplane_types.append({
                'type_id': airplane_type.type_id,
                'name': airplane_type.name,
                'iata': airplane_type.iata,
                'icao': airplane_type.icao,
                'estimated_capacity': capacity
            })
        
        return airplane_types
    
    def get_airlines(self, session: Session) -> List[Dict[str, Any]]:
        """Get airlines that can own aircraft"""
        
        airlines_query = select(Airline.airline_id, Airline.name, Airline.iata, Airline.icao).where(
            Airline.active == True
        )
        
        airlines = []
        for airline_id, name, iata, icao in session.exec(airlines_query).all():
            airlines.append({
                'airline_id': airline_id,
                'name': name,
                'iata': iata,
                'icao': icao
            })
        
        return airlines
    
    def categorize_aircraft_types(self, airplane_types: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize aircraft types by size for realistic fleet composition"""
        categories = {
            'wide_body': [],      # 250+ seats - long haul
            'narrow_body': [],    # 120-249 seats - medium haul
            'regional': [],       # 50-119 seats - short haul
            'small': []          # <50 seats - very short haul
        }
        
        for aircraft_type in airplane_types:
            capacity = aircraft_type['estimated_capacity']
            if capacity >= 250:
                categories['wide_body'].append(aircraft_type)
            elif capacity >= 120:
                categories['narrow_body'].append(aircraft_type)
            elif capacity >= 50:
                categories['regional'].append(aircraft_type)
            else:
                categories['small'].append(aircraft_type)
        
        return categories
    
    def determine_airline_fleet_profile(self, airline: Dict[str, Any]) -> Dict[str, int]:
        """Determine realistic fleet composition based on airline characteristics"""
        airline_name = airline['name'].lower()
        
        # Major US/International airlines (800+ aircraft)
        if any(keyword in airline_name for keyword in ['american airlines', 'delta air', 'united airlines', 'southwest']):
            return {
                'wide_body': 80,      # Long-haul fleet
                'narrow_body': 650,   # Main domestic/short-haul fleet
                'regional': 120,      # Regional routes
                'small': 10           # Charter/special ops
            }
        
        # Large international carriers (400-800 aircraft)
        elif any(keyword in airline_name for keyword in ['lufthansa', 'air france', 'british airways', 'emirates', 'qatar', 'singapore', 'klm', 'turkish']):
            return {
                'wide_body': 120,     # Heavy international focus
                'narrow_body': 280,   # European/domestic routes
                'regional': 80,       # Regional connections
                'small': 5            # VIP/charter
            }
        
        # Medium international airlines (200-400 aircraft)
        elif any(keyword in airline_name for keyword in ['air canada', 'qantas', 'japan airlines', 'korean air', 'cathay', 'virgin atlantic', 'alitalia']):
            return {
                'wide_body': 60,      # International routes
                'narrow_body': 180,   # Domestic/regional international
                'regional': 60,       # Regional feeders
                'small': 5            # Special ops
            }
        
        # Low-cost carriers (100-300 aircraft)
        elif any(keyword in airline_name for keyword in ['ryanair', 'easyjet', 'jetblue', 'spirit', 'frontier', 'allegiant', 'wizz']):
            return {
                'wide_body': 5,       # Limited long-haul
                'narrow_body': 180,   # Main fleet
                'regional': 25,       # Smaller markets
                'small': 0            # No small aircraft
            }
        
        # Regional airlines (50-150 aircraft)
        elif any(keyword in airline_name for keyword in ['regional', 'express', 'commuter', 'connection', 'link', 'eagle', 'skywest']):
            return {
                'wide_body': 0,       # No wide-body
                'narrow_body': 20,    # Limited mainline
                'regional': 80,       # Main regional fleet
                'small': 25           # Smaller routes
            }
        
        # Cargo airlines (50-200 aircraft)
        elif any(keyword in airline_name for keyword in ['cargo', 'freight', 'fedex', 'ups', 'dhl']):
            return {
                'wide_body': 60,      # Long-haul cargo
                'narrow_body': 40,    # Medium-haul cargo
                'regional': 15,       # Regional cargo
                'small': 5            # Small package delivery
            }
        
        # Charter/private airlines (10-50 aircraft)
        elif any(keyword in airline_name for keyword in ['charter', 'private', 'executive', 'jet', 'aviation']):
            return {
                'wide_body': 2,       # VIP long-haul
                'narrow_body': 8,     # Charter flights
                'regional': 15,       # Regional charter
                'small': 25           # Private/executive
            }
        
        # Small/startup airlines (20-100 aircraft)
        elif any(keyword in airline_name for keyword in ['air', 'fly', 'wings', 'sky']):
            return {
                'wide_body': 5,       # Limited international
                'narrow_body': 45,    # Main fleet
                'regional': 25,       # Regional routes
                'small': 5            # Niche routes
            }
        
        # Default medium airline (50-150 aircraft)
        return {
            'wide_body': 10,      # Some international
            'narrow_body': 60,    # Main domestic fleet
            'regional': 30,       # Regional connections
            'small': 5            # Special routes
        }
    
    def generate_aircraft_fleet(self, airplane_types: List[Dict[str, Any]], 
                              airlines: List[Dict[str, Any]], 
                              fleet_size_multiplier: float = 1.0) -> List[Airplane]:
        """Generate realistic aircraft fleets for each airline"""
        
        aircraft_list = []
        categorized_types = self.categorize_aircraft_types(airplane_types)
        
        print(f"Generating aircraft fleets per airline...")
        print(f"Airlines: {len(airlines)}")
        print(f"Aircraft categories: Wide-body: {len(categorized_types['wide_body'])}, "
              f"Narrow-body: {len(categorized_types['narrow_body'])}, "
              f"Regional: {len(categorized_types['regional'])}, "
              f"Small: {len(categorized_types['small'])}")
        
        fleet_summary = {}
        
        # Use tqdm for progress tracking
        with tqdm(
            airlines, 
            desc="🏢 Generating fleets", 
            unit="airline",
            colour='blue',
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} airlines ({percentage:3.0f}%) [{elapsed}<{remaining}]'
        ) as pbar:
            for airline in pbar:
                airline_fleet = []
                fleet_profile = self.determine_airline_fleet_profile(airline)
                
                # Scale fleet size by multiplier
                scaled_profile = {
                    category: max(1, int(count * fleet_size_multiplier)) 
                    for category, count in fleet_profile.items()
                }
                
                # Generate aircraft for each category
                for category, target_count in scaled_profile.items():
                    available_types = categorized_types[category]
                    if not available_types:
                        continue
                    
                    # Distribute aircraft across available types in this category
                    for i in range(target_count):
                        # Select aircraft type (prefer variety but allow duplicates)
                        aircraft_type = available_types[i % len(available_types)]
                        
                        # Add some capacity variation (±5% for more realistic fleets)
                        base_capacity = aircraft_type['estimated_capacity']
                        capacity_variation = random.randint(-5, 5) / 100
                        final_capacity = int(base_capacity * (1 + capacity_variation))
                        final_capacity = max(1, final_capacity)  # Minimum 1 seat
                        
                        aircraft = Airplane(
                            capacity=final_capacity,
                            type_id=aircraft_type['type_id'],
                            airline_id=airline['airline_id']
                        )
                        
                        airline_fleet.append(aircraft)
                
                aircraft_list.extend(airline_fleet)
                fleet_summary[airline['name']] = {
                    'total': len(airline_fleet),
                    'profile': scaled_profile
                }
                
                # Update progress bar with current airline info
                pbar.set_postfix({
                    'Current': airline['name'][:20],
                    'Fleet': len(airline_fleet),
                    'Total': len(aircraft_list)
                })
        
        # Print fleet summary for top airlines
        print(f"\nGenerated fleets for {len(airlines)} airlines:")
        sorted_airlines = sorted(fleet_summary.items(), key=lambda x: x[1]['total'], reverse=True)
        for airline_name, summary in sorted_airlines[:10]:  # Show top 10
            print(f"  {airline_name}: {summary['total']} aircraft "
                  f"(W:{summary['profile']['wide_body']}, "
                  f"N:{summary['profile']['narrow_body']}, "
                  f"R:{summary['profile']['regional']}, "
                  f"S:{summary['profile']['small']})")
        
        if len(sorted_airlines) > 10:
            print(f"  ... and {len(sorted_airlines) - 10} more airlines")
        
        print(f"\nTotal aircraft generated: {len(aircraft_list)}")
        return aircraft_list
    
    def populate_aircraft(self, fleet_size_multiplier: float = 1.0, batch_size: int = 1000) -> int:
        """Populate aircraft table with generated aircraft fleets per airline"""
        
        if not DEPENDENCIES_AVAILABLE:
            print("Dependencies not available")
            return 0
        
        with Session(self.db_manager.engine) as session:
            # Get airplane types and airlines
            airplane_types = self.get_airplane_types(session)
            airlines = self.get_airlines(session)
            
            if not airplane_types:
                print("❌ No airplane types found in database")
                return 0
            
            if not airlines:
                print("❌ No airlines found in database")
                return 0
            
            # Check existing aircraft
            existing_count = session.exec(select(func.count(Airplane.airplane_id))).first()
            print(f"Existing aircraft: {existing_count}")
            
            if existing_count > 0:
                response = input(f"Found {existing_count} existing aircraft. Clear and regenerate? (y/N): ")
                if response.lower() == 'y':
                    # Clear existing aircraft with progress tracking
                    existing_aircraft = session.exec(select(Airplane)).all()
                    
                    with tqdm(
                        existing_aircraft,
                        desc="🗑️  Clearing aircraft",
                        unit="aircraft",
                        colour='red',
                        bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
                    ) as pbar:
                        for aircraft in pbar:
                            session.delete(aircraft)
                    
                    session.commit()
                    print(f"Cleared {existing_count} existing aircraft")
                else:
                    print("Keeping existing aircraft")
                    return existing_count
            
            # Generate new aircraft fleets
            aircraft_list = self.generate_aircraft_fleet(airplane_types, airlines, fleet_size_multiplier)
            
            if not aircraft_list:
                print("❌ No aircraft generated")
                return 0
            
            # Insert in batches with progress tracking
            total_inserted = 0
            
            with tqdm(
                total=len(aircraft_list),
                desc="✈️  Inserting aircraft",
                unit="aircraft",
                colour='green',
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} ({percentage:3.0f}%) [{elapsed}<{remaining}]'
            ) as pbar:
                for i in range(0, len(aircraft_list), batch_size):
                    batch = aircraft_list[i:i + batch_size]
                    session.add_all(batch)
                    session.commit()
                    total_inserted += len(batch)
                    
                    # Update progress bar
                    pbar.update(len(batch))
                    pbar.set_postfix({
                        'Inserted': f"{total_inserted:,}",
                        'Batch': f"{len(batch)}"
                    })
            
            print(f"✅ Successfully populated {total_inserted:,} aircraft")
            
            # Show sample aircraft by category and airline
            self.show_aircraft_summary(session)
            
            return total_inserted
    
    def show_aircraft_summary(self, session: Session):
        """Show summary of aircraft by capacity categories and airline fleets"""
        
        print("\nAircraft Summary by Category:")
        
        # Wide-body (250+ seats)
        wide_body_count = session.exec(
            select(func.count(Airplane.airplane_id)).where(Airplane.capacity >= 250)
        ).first()
        
        # Narrow-body (120-249 seats)
        narrow_body_count = session.exec(
            select(func.count(Airplane.airplane_id)).where(
                Airplane.capacity >= 120, Airplane.capacity < 250
            )
        ).first()
        
        # Regional (50-119 seats)
        regional_count = session.exec(
            select(func.count(Airplane.airplane_id)).where(
                Airplane.capacity >= 50, Airplane.capacity < 120
            )
        ).first()
        
        # Small (<50 seats)
        small_count = session.exec(
            select(func.count(Airplane.airplane_id)).where(Airplane.capacity < 50)
        ).first()
        
        print(f"  Wide-body (250+ seats): {wide_body_count:,}")
        print(f"  Narrow-body (120-249 seats): {narrow_body_count:,}")
        print(f"  Regional (50-119 seats): {regional_count:,}")
        print(f"  Small (<50 seats): {small_count:,}")
        
        # Show top airlines by fleet size
        fleet_query = (
            select(Airline.name, func.count(Airplane.airplane_id).label('fleet_size'))
            .join(Airplane, Airline.airline_id == Airplane.airline_id)
            .group_by(Airline.airline_id, Airline.name)
            .order_by(func.count(Airplane.airplane_id).desc())
            .limit(10)
        )
        
        print(f"\nTop 10 Airlines by Fleet Size:")
        for airline_name, fleet_size in session.exec(fleet_query).all():
            print(f"  {airline_name}: {fleet_size} aircraft")
        
        # Show sample aircraft with airline information
        sample_query = (
            select(Airplane.airplane_id, Airplane.capacity, AirplaneType.name, Airline.name)
            .join(AirplaneType, Airplane.type_id == AirplaneType.type_id)
            .join(Airline, Airplane.airline_id == Airline.airline_id)
            .limit(10)
        )
        
        # Show fleet diversity by category
        from sqlalchemy import case
        diversity_query = (
            select(
                Airline.name,
                func.sum(case((Airplane.capacity >= 250, 1), else_=0)).label('wide_body'),
                func.sum(case(((Airplane.capacity >= 120) & (Airplane.capacity < 250), 1), else_=0)).label('narrow_body'),
                func.sum(case(((Airplane.capacity >= 50) & (Airplane.capacity < 120), 1), else_=0)).label('regional'),
                func.sum(case((Airplane.capacity < 50, 1), else_=0)).label('small')
            )
            .join(Airplane, Airline.airline_id == Airplane.airline_id)
            .group_by(Airline.airline_id, Airline.name)
            .having(func.count(Airplane.airplane_id) >= 5)  # Only airlines with 5+ aircraft
            .order_by(func.count(Airplane.airplane_id).desc())
            .limit(5)
        )
        
        print(f"\nFleet Composition (Top 5 Airlines with 5+ Aircraft):")
        print(f"{'Airline':<25} {'Wide':<5} {'Narrow':<7} {'Regional':<8} {'Small':<5}")
        print("-" * 50)
        for airline_name, wide, narrow, regional, small in session.exec(diversity_query).all():
            print(f"{airline_name[:24]:<25} {wide:<5} {narrow:<7} {regional:<8} {small:<5}")
        
        print(f"\nSample Aircraft:")
        for airplane_id, capacity, type_name, airline_name in session.exec(sample_query).all():
            print(f"  ID {airplane_id}: {type_name} ({capacity} seats) - {airline_name}")


def main():
    """Main function"""
    if not DEPENDENCIES_AVAILABLE:
        return 1
    
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return 1
    
    load_dotenv()
    
    print("Aircraft Population Script")
    print("=" * 30)
    
    # Initialize
    db_manager = DatabaseManager()
    populator = AircraftPopulator(db_manager)
    
    # Get user preferences
    print("\nThis script will generate realistic aircraft fleets for each airline.")
    print("Fleet composition is based on airline type (international, regional, low-cost, etc.)")
    
    fleet_multiplier = 1.0  # Default
    response = input(f"\nFleet size multiplier (default {fleet_multiplier}): ").strip()
    try:
        if response:
            fleet_multiplier = float(response)
    except ValueError:
        print("Invalid input, using default multiplier")
    
    print(f"\nWill generate fleets with {fleet_multiplier}x base size")
    print("Base fleet sizes vary by airline type:")
    print("  - Major US/International (American, Delta, United, Southwest): ~860 aircraft")
    print("  - Large International (Lufthansa, Emirates, British Airways): ~485 aircraft")
    print("  - Medium International (Air Canada, Qantas, JAL): ~305 aircraft")
    print("  - Low-cost carriers (Ryanair, JetBlue, Spirit): ~210 aircraft")
    print("  - Regional airlines (SkyWest, Regional Express): ~125 aircraft")
    print("  - Cargo airlines (FedEx, UPS): ~120 aircraft")
    print("  - Charter/private airlines: ~50 aircraft")
    print("  - Small/startup airlines: ~80 aircraft")
    print("  - Default medium airlines: ~105 aircraft")
    
    # Confirmation
    confirm = input("\nProceed with fleet generation? (y/N): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return 0
    
    try:
        created_count = populator.populate_aircraft(fleet_multiplier)
        
        if created_count > 0:
            print(f"\n🎉 Successfully created {created_count:,} aircraft!")
            print("\nYou can now run the flight population scripts:")
            print("  python scripts/test_flight_population.py")
            print("  python scripts/populate_flights_comprehensive.py")
        else:
            print("\n⚠ No aircraft were created.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())