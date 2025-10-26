#!/usr/bin/env python3
"""
City Flight Analysis Script

Analyze city population data and generate flight planning recommendations
based on population, demand scores, and airport accessibility.
"""

import os
import sys
from typing import List, Dict, Any
from sqlmodel import Session, select, func
from decimal import Decimal

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.city import City, CityAirportRelation
from models.airport import Airport
from models.airport_geo import AirportGeo
from models.country import Country


class CityFlightAnalyzer:
    """Analyze city data for flight planning and route optimization"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_top_cities_by_population(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top cities by population with flight planning data"""
        with Session(self.db_manager.engine) as session:
            query = (
                select(
                    City.name,
                    City.country_code,
                    City.population,
                    City.flight_demand_score,
                    City.recommended_daily_flights,
                    Country.name.label('country_name')
                )
                .join(Country, City.country_id == Country.country_id, isouter=True)
                .where(City.population.is_not(None))
                .order_by(City.population.desc())
                .limit(limit)
            )
            
            results = session.exec(query).all()
            
            return [
                {
                    'city_name': result.name,
                    'country_code': result.country_code,
                    'country_name': result.country_name or 'Unknown',
                    'population': result.population,
                    'flight_demand_score': float(result.flight_demand_score) if result.flight_demand_score else 0,
                    'recommended_daily_flights': result.recommended_daily_flights or 0,
                }
                for result in results
            ]
    
    def get_cities_with_airports(self, min_population: int = 100000) -> List[Dict[str, Any]]:
        """Get cities with nearby airports and their accessibility metrics"""
        with Session(self.db_manager.engine) as session:
            query = (
                select(
                    City.name.label('city_name'),
                    City.population,
                    City.flight_demand_score,
                    City.recommended_daily_flights,
                    Airport.name.label('airport_name'),
                    Airport.iata,
                    Airport.icao,
                    CityAirportRelation.distance_km,
                    CityAirportRelation.is_primary_airport,
                    CityAirportRelation.accessibility_score,
                    CityAirportRelation.estimated_passenger_share,
                    Country.name.label('country_name')
                )
                .join(CityAirportRelation, City.city_id == CityAirportRelation.city_id)
                .join(Airport, CityAirportRelation.airport_id == Airport.airport_id)
                .join(Country, City.country_id == Country.country_id, isouter=True)
                .where(City.population >= min_population)
                .order_by(City.population.desc(), CityAirportRelation.distance_km.asc())
            )
            
            results = session.exec(query).all()
            
            return [
                {
                    'city_name': result.city_name,
                    'country_name': result.country_name or 'Unknown',
                    'population': result.population,
                    'flight_demand_score': float(result.flight_demand_score) if result.flight_demand_score else 0,
                    'recommended_daily_flights': result.recommended_daily_flights or 0,
                    'airport_name': result.airport_name,
                    'airport_iata': result.iata,
                    'airport_icao': result.icao,
                    'distance_km': float(result.distance_km) if result.distance_km else 0,
                    'is_primary_airport': result.is_primary_airport,
                    'accessibility_score': float(result.accessibility_score) if result.accessibility_score else 0,
                    'estimated_passenger_share': float(result.estimated_passenger_share) if result.estimated_passenger_share else 0,
                }
                for result in results
            ]
    
    def get_underserved_cities(self, min_population: int = 500000, max_airports: int = 1) -> List[Dict[str, Any]]:
        """Identify potentially underserved cities that might need more flight connections"""
        with Session(self.db_manager.engine) as session:
            # Subquery to count airports per city
            airport_count_subquery = (
                select(
                    CityAirportRelation.city_id,
                    func.count(CityAirportRelation.airport_id).label('airport_count')
                )
                .group_by(CityAirportRelation.city_id)
                .subquery()
            )
            
            query = (
                select(
                    City.name.label('city_name'),
                    City.population,
                    City.flight_demand_score,
                    City.recommended_daily_flights,
                    Country.name.label('country_name'),
                    func.coalesce(airport_count_subquery.c.airport_count, 0).label('airport_count')
                )
                .join(Country, City.country_id == Country.country_id, isouter=True)
                .join(airport_count_subquery, City.city_id == airport_count_subquery.c.city_id, isouter=True)
                .where(
                    City.population >= min_population,
                    func.coalesce(airport_count_subquery.c.airport_count, 0) <= max_airports
                )
                .order_by(City.population.desc())
            )
            
            results = session.exec(query).all()
            
            return [
                {
                    'city_name': result.city_name,
                    'country_name': result.country_name or 'Unknown',
                    'population': result.population,
                    'flight_demand_score': float(result.flight_demand_score) if result.flight_demand_score else 0,
                    'recommended_daily_flights': result.recommended_daily_flights or 0,
                    'airport_count': result.airport_count,
                    'underserved_score': (result.population / 100000) * (float(result.flight_demand_score) if result.flight_demand_score else 1) / max(1, result.airport_count)
                }
                for result in results
            ]
    
    def get_country_flight_summary(self) -> List[Dict[str, Any]]:
        """Get flight planning summary by country"""
        with Session(self.db_manager.engine) as session:
            query = (
                select(
                    Country.name.label('country_name'),
                    Country.iso_code,
                    func.count(City.city_id).label('city_count'),
                    func.sum(City.population).label('total_population'),
                    func.avg(City.flight_demand_score).label('avg_demand_score'),
                    func.sum(City.recommended_daily_flights).label('total_recommended_flights')
                )
                .join(City, Country.country_id == City.country_id)
                .where(City.population.is_not(None))
                .group_by(Country.country_id, Country.name, Country.iso_code)
                .order_by(func.sum(City.population).desc())
            )
            
            results = session.exec(query).all()
            
            return [
                {
                    'country_name': result.country_name,
                    'country_code': result.iso_code,
                    'city_count': result.city_count,
                    'total_population': result.total_population or 0,
                    'avg_demand_score': round(float(result.avg_demand_score), 2) if result.avg_demand_score else 0,
                    'total_recommended_flights': result.total_recommended_flights or 0,
                }
                for result in results
            ]
    
    def generate_route_recommendations(self, min_population: int = 1000000) -> List[Dict[str, Any]]:
        """Generate potential route recommendations between major cities"""
        with Session(self.db_manager.engine) as session:
            # Get major cities with primary airports
            major_cities_query = (
                select(
                    City.city_id,
                    City.name.label('city_name'),
                    City.latitude,
                    City.longitude,
                    City.population,
                    City.flight_demand_score,
                    Airport.airport_id,
                    Airport.name.label('airport_name'),
                    Airport.iata,
                    Country.name.label('country_name')
                )
                .join(CityAirportRelation, City.city_id == CityAirportRelation.city_id)
                .join(Airport, CityAirportRelation.airport_id == Airport.airport_id)
                .join(Country, City.country_id == Country.country_id, isouter=True)
                .where(
                    City.population >= min_population,
                    CityAirportRelation.is_primary_airport == True
                )
                .order_by(City.population.desc())
            )
            
            major_cities = session.exec(major_cities_query).all()
            
            recommendations = []
            
            # Generate route recommendations between top cities
            for i, origin in enumerate(major_cities[:20]):  # Top 20 cities
                for destination in major_cities[i+1:]:
                    if origin.country_name != destination.country_name:  # International routes
                        # Calculate route priority based on combined populations and demand
                        combined_population = origin.population + destination.population
                        combined_demand = (float(origin.flight_demand_score) + float(destination.flight_demand_score)) / 2
                        
                        # Calculate distance if coordinates are available
                        distance = None
                        if all([origin.latitude, origin.longitude, destination.latitude, destination.longitude]):
                            distance = self.calculate_distance(
                                float(origin.latitude), float(origin.longitude),
                                float(destination.latitude), float(destination.longitude)
                            )
                        
                        # Estimate weekly flights based on population and distance
                        weekly_flights = min(21, max(1, int(combined_population / 2000000)))
                        if distance and distance > 10000:  # Long-haul routes
                            weekly_flights = max(1, weekly_flights // 2)
                        
                        recommendations.append({
                            'origin_city': origin.city_name,
                            'origin_country': origin.country_name,
                            'origin_airport': origin.airport_name,
                            'origin_iata': origin.iata,
                            'destination_city': destination.city_name,
                            'destination_country': destination.country_name,
                            'destination_airport': destination.airport_name,
                            'destination_iata': destination.iata,
                            'combined_population': combined_population,
                            'route_priority_score': combined_demand * (combined_population / 1000000),
                            'estimated_weekly_flights': weekly_flights,
                            'distance_km': round(distance, 0) if distance else None,
                        })
            
            # Sort by priority score
            recommendations.sort(key=lambda x: x['route_priority_score'], reverse=True)
            
            return recommendations[:50]  # Top 50 route recommendations
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r


def print_table(data: List[Dict[str, Any]], title: str, max_rows: int = 20):
    """Print data in a formatted table"""
    if not data:
        print(f"\n{title}: No data available\n")
        return
    
    print(f"\n{title}")
    print("=" * len(title))
    
    # Show only first max_rows
    display_data = data[:max_rows]
    
    # Print headers
    headers = list(display_data[0].keys())
    header_line = " | ".join(f"{header:>15}" for header in headers)
    print(header_line)
    print("-" * len(header_line))
    
    # Print data rows
    for row in display_data:
        values = []
        for key, value in row.items():
            if isinstance(value, float):
                values.append(f"{value:>15.2f}")
            elif isinstance(value, int):
                values.append(f"{value:>15,}")
            else:
                values.append(f"{str(value):>15}")
        print(" | ".join(values))
    
    if len(data) > max_rows:
        print(f"\n... and {len(data) - max_rows} more rows")
    
    print()


def main():
    """Main function to run city flight analysis"""
    print("City Flight Analysis for Route Planning")
    print("=" * 40)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    analyzer = CityFlightAnalyzer(db_manager)
    
    try:
        # Top cities by population
        print("Analyzing city data for flight planning...")
        top_cities = analyzer.get_top_cities_by_population(30)
        print_table(top_cities, "Top 30 Cities by Population", 15)
        
        # Cities with airports
        cities_with_airports = analyzer.get_cities_with_airports(500000)
        print_table(cities_with_airports, "Major Cities with Airport Access", 15)
        
        # Underserved cities
        underserved = analyzer.get_underserved_cities(500000, 1)
        print_table(underserved, "Potentially Underserved Cities (>500k population, ≤1 airport)", 10)
        
        # Country summary
        country_summary = analyzer.get_country_flight_summary()
        print_table(country_summary, "Flight Planning Summary by Country", 15)
        
        # Route recommendations
        print("Generating route recommendations...")
        route_recommendations = analyzer.generate_route_recommendations(1000000)
        print_table(route_recommendations, "Top International Route Recommendations", 15)
        
        print("\nAnalysis completed successfully!")
        print("\nKey Insights:")
        print("- Flight demand scores are calculated using logarithmic population scaling")
        print("- Recommended daily flights consider city type and population tiers")
        print("- Route priorities combine population size and demand scores")
        print("- Underserved cities may need additional airport infrastructure")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())