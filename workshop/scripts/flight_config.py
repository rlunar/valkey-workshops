#!/usr/bin/env python3
"""
Flight Population Configuration

Configuration settings for flight generation based on flight rules.
"""

from datetime import time
from typing import Dict, List, Tuple, Any

class FlightConfig:
    """Configuration for flight population based on docs/flight_rules.md"""
    
    # Airport tiers based on route count (from flight rules)
    AIRPORT_TIERS = {
        'tier_1_major_hub': {
            'min_routes': 500,
            'name': 'Major Hub Airport',
            'daily_flights_range': (6, 12),
            'peak_hours_weight': 0.7,
            'weekend_multiplier': 0.9,
            'seasonal_boost': 1.3,
            'description': 'ATL, ORD, PEK, LHR, CDG, FRA, LAX, DFW, JFK, AMS'
        },
        'tier_2_regional_hub': {
            'min_routes': 200,
            'name': 'Regional Hub Airport', 
            'daily_flights_range': (2, 6),
            'peak_hours_weight': 0.6,
            'weekend_multiplier': 0.85,
            'seasonal_boost': 1.2,
            'description': 'Major regional centers with significant connectivity'
        },
        'tier_3_secondary': {
            'min_routes': 50,
            'name': 'Secondary Airport',
            'daily_flights_range': (1, 3),
            'peak_hours_weight': 0.5,
            'weekend_multiplier': 0.8,
            'seasonal_boost': 1.15,
            'description': 'Important regional airports with moderate connectivity'
        },
        'tier_4_regional': {
            'min_routes': 10,
            'name': 'Regional Airport',
            'daily_flights_range': (0.4, 1.0),  # 3-7 flights per week
            'peak_hours_weight': 0.4,
            'weekend_multiplier': 0.6,
            'seasonal_boost': 1.1,
            'description': 'Smaller regional airports serving local markets'
        },
        'tier_5_local': {
            'min_routes': 0,
            'name': 'Local Airport',
            'daily_flights_range': (0.1, 0.4),  # 1-3 flights per week
            'peak_hours_weight': 0.3,
            'weekend_multiplier': 0.4,
            'seasonal_boost': 1.05,
            'description': 'Small airports with limited connectivity'
        }
    }
    
    # Time slots based on flight rules
    PEAK_HOURS = [6, 7, 8, 9, 12, 13, 17, 18, 19, 20]  # 6-9 AM, 12-2 PM, 5-8 PM
    OFF_PEAK_HOURS = [10, 11, 14, 15, 16, 21, 22]
    NIGHT_HOURS = [23, 0, 1, 2, 3, 4, 5]
    
    # Common departure times (realistic airline scheduling)
    DEPARTURE_TIMES = [
        time(6, 0), time(6, 30), time(7, 0), time(7, 30),
        time(8, 0), time(8, 30), time(9, 0), time(9, 30),
        time(10, 0), time(10, 30), time(11, 0), time(11, 30),
        time(12, 0), time(12, 30), time(13, 0), time(13, 30),
        time(14, 0), time(14, 30), time(15, 0), time(15, 30),
        time(16, 0), time(16, 30), time(17, 0), time(17, 30),
        time(18, 0), time(18, 30), time(19, 0), time(19, 30),
        time(20, 0), time(20, 30), time(21, 0), time(21, 30),
        time(22, 0), time(22, 30)
    ]
    
    # Seasonal multipliers (from flight rules)
    SEASONAL_MULTIPLIERS = {
        'winter': 0.85,   # Dec, Jan, Feb
        'spring': 1.0,    # Mar, Apr, May  
        'summer': 1.3,    # Jun, Jul, Aug
        'fall': 1.1       # Sep, Oct, Nov
    }
    
    # Day of week multipliers
    DAY_OF_WEEK_MULTIPLIERS = {
        0: 1.2,  # Monday - business travel
        1: 1.1,  # Tuesday
        2: 1.0,  # Wednesday
        3: 1.1,  # Thursday  
        4: 1.3,  # Friday - weekend travel starts
        5: 0.9,  # Saturday - leisure travel
        6: 1.0   # Sunday - return travel
    }
    
    # Aircraft selection by route characteristics
    AIRCRAFT_CATEGORIES = {
        'wide_body': {
            'capacity_range': (250, 500),
            'use_cases': ['long_haul', 'high_demand', 'international_hub'],
            'min_distance_km': 3000,
            'min_daily_passengers': 300
        },
        'narrow_body': {
            'capacity_range': (120, 250), 
            'use_cases': ['medium_haul', 'domestic_trunk', 'regional_hub'],
            'min_distance_km': 500,
            'min_daily_passengers': 150
        },
        'regional': {
            'capacity_range': (50, 120),
            'use_cases': ['short_haul', 'regional', 'low_demand'],
            'min_distance_km': 0,
            'min_daily_passengers': 0
        }
    }
    
    # Flight duration estimation (simplified)
    FLIGHT_DURATION_RULES = {
        'short_haul': {'max_km': 1500, 'avg_speed_kmh': 600, 'overhead_min': 30},
        'medium_haul': {'max_km': 4000, 'avg_speed_kmh': 700, 'overhead_min': 45},
        'long_haul': {'max_km': float('inf'), 'avg_speed_kmh': 800, 'overhead_min': 60}
    }
    
    # Airline-specific patterns (from route analysis)
    AIRLINE_PATTERNS = {
        'FR': {'type': 'low_cost', 'frequency_boost': 1.2, 'peak_preference': 0.3},
        'AA': {'type': 'legacy_hub', 'frequency_boost': 1.0, 'peak_preference': 0.7},
        'UA': {'type': 'legacy_hub', 'frequency_boost': 1.0, 'peak_preference': 0.7},
        'DL': {'type': 'legacy_hub', 'frequency_boost': 1.0, 'peak_preference': 0.7},
        'WN': {'type': 'low_cost', 'frequency_boost': 1.1, 'peak_preference': 0.4},
        'default': {'type': 'regional', 'frequency_boost': 1.0, 'peak_preference': 0.5}
    }
    
    @classmethod
    def get_airport_tier(cls, route_count: int) -> Dict[str, Any]:
        """Get airport tier configuration based on route count"""
        for tier_name, config in cls.AIRPORT_TIERS.items():
            if route_count >= config['min_routes']:
                return {
                    'tier_name': tier_name,
                    **config
                }
        
        # Default to lowest tier
        return {
            'tier_name': 'tier_5_local',
            **cls.AIRPORT_TIERS['tier_5_local']
        }
    
    @classmethod
    def get_seasonal_multiplier(cls, month: int) -> float:
        """Get seasonal multiplier for given month"""
        if month in [12, 1, 2]:
            return cls.SEASONAL_MULTIPLIERS['winter']
        elif month in [3, 4, 5]:
            return cls.SEASONAL_MULTIPLIERS['spring']
        elif month in [6, 7, 8]:
            return cls.SEASONAL_MULTIPLIERS['summer']
        else:
            return cls.SEASONAL_MULTIPLIERS['fall']
    
    @classmethod
    def get_airline_pattern(cls, airline_code: str) -> Dict[str, Any]:
        """Get airline-specific operational patterns"""
        return cls.AIRLINE_PATTERNS.get(airline_code, cls.AIRLINE_PATTERNS['default'])
    
    @classmethod
    def get_aircraft_category(cls, distance_km: float, daily_passengers: int) -> str:
        """Determine appropriate aircraft category"""
        for category, config in cls.AIRCRAFT_CATEGORIES.items():
            if (distance_km >= config['min_distance_km'] and 
                daily_passengers >= config['min_daily_passengers']):
                return category
        
        return 'regional'  # Default fallback
    
    @classmethod
    def estimate_flight_duration_minutes(cls, distance_km: float) -> int:
        """Estimate flight duration in minutes"""
        for category, rules in cls.FLIGHT_DURATION_RULES.items():
            if distance_km <= rules['max_km']:
                flight_time = (distance_km / rules['avg_speed_kmh']) * 60
                total_time = flight_time + rules['overhead_min']
                return max(30, int(total_time))  # Minimum 30 minutes
        
        # Fallback for very long distances
        return int((distance_km / 800) * 60) + 60
    
    @classmethod
    def print_configuration_summary(cls):
        """Print a summary of the flight configuration"""
        print("Flight Population Configuration Summary")
        print("=" * 45)
        
        print("\nAirport Tiers:")
        for tier_name, config in cls.AIRPORT_TIERS.items():
            print(f"  {config['name']}:")
            print(f"    Min routes: {config['min_routes']}")
            print(f"    Daily flights: {config['daily_flights_range'][0]}-{config['daily_flights_range'][1]}")
            print(f"    Seasonal boost: {config['seasonal_boost']}x")
        
        print(f"\nSeasonal Multipliers:")
        for season, mult in cls.SEASONAL_MULTIPLIERS.items():
            print(f"  {season.capitalize()}: {mult}x")
        
        print(f"\nAircraft Categories:")
        for category, config in cls.AIRCRAFT_CATEGORIES.items():
            print(f"  {category.replace('_', ' ').title()}:")
            print(f"    Capacity: {config['capacity_range'][0]}-{config['capacity_range'][1]} seats")
            print(f"    Min distance: {config['min_distance_km']} km")
        
        print(f"\nTime Slots:")
        print(f"  Peak hours: {cls.PEAK_HOURS}")
        print(f"  Off-peak hours: {cls.OFF_PEAK_HOURS}")
        print(f"  Night hours: {cls.NIGHT_HOURS}")


if __name__ == "__main__":
    # Print configuration when run directly
    FlightConfig.print_configuration_summary()