#!/usr/bin/env python3
"""
Flight Population Configuration

Configuration settings for flight generation based on flight rules.
"""

from datetime import time
from typing import Dict, List, Tuple, Any

class FlightConfig:
    """Configuration for flight population based on docs/flight_rules.md"""
    
    # Airport tiers based on route count (REDUCED for 100M bookings target)
    AIRPORT_TIERS = {
        'tier_1_major_hub': {
            'min_routes': 500,
            'name': 'Major Hub Airport',
            'short_haul_daily': (2, 4),     # REDUCED: 0-1,500km (was 8-15)
            'medium_haul_daily': (1, 2),    # REDUCED: 1,500-4,000km (was 4-8)
            'long_haul_daily': (0.3, 0.8),  # REDUCED: 4,000+km (was 1-3)
            'peak_hours_weight': 0.7,
            'weekend_multiplier': 0.9,
            'seasonal_boost': 1.3,
            'description': 'ATL, ORD, PEK, LHR, CDG, FRA, LAX, DFW, JFK, AMS'
        },
        'tier_2_regional_hub': {
            'min_routes': 200,
            'name': 'Regional Hub Airport', 
            'short_haul_daily': (1, 2),     # REDUCED: 0-1,500km (was 4-8)
            'medium_haul_daily': (0.5, 1),  # REDUCED: 1,500-4,000km (was 2-4)
            'long_haul_weekly': (0.2, 0.5), # REDUCED: 4,000+km (was 0.4-1.0)
            'peak_hours_weight': 0.6,
            'weekend_multiplier': 0.85,
            'seasonal_boost': 1.2,
            'description': 'Major regional centers with significant connectivity'
        },
        'tier_3_secondary': {
            'min_routes': 50,
            'name': 'Secondary Airport',
            'short_haul_daily': (0.5, 1),   # REDUCED: 0-1,500km (was 2-4)
            'medium_haul_daily': (0.2, 0.5), # REDUCED: 1,500-4,000km (was 1-2)
            'long_haul_weekly': (0.1, 0.3), # REDUCED: 4,000+km (was 0.4-0.7)
            'peak_hours_weight': 0.5,
            'weekend_multiplier': 0.8,
            'seasonal_boost': 1.15,
            'description': 'Important regional airports with moderate connectivity'
        },
        'tier_4_regional': {
            'min_routes': 10,
            'name': 'Regional Airport',
            'short_haul_weekly': (1, 3),    # REDUCED: 0-1,500km (weekly)
            'medium_haul_weekly': (0.5, 1), # REDUCED: 1,500-4,000km (weekly)
            'peak_hours_weight': 0.4,
            'weekend_multiplier': 0.6,
            'seasonal_boost': 1.1,
            'description': 'Smaller regional airports serving local markets'
        },
        'tier_5_local': {
            'min_routes': 0,
            'name': 'Local Airport',
            'short_haul_weekly': (0.2, 1),  # REDUCED: 0-1,500km only (1-7 weekly)
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
    
    # Aircraft selection by distance (from flight rules)
    AIRCRAFT_DISTANCE_RULES = {
        'regional_turboprop': {
            'distance_range': (0, 800),
            'capacity_range': (30, 80),
            'aircraft_types': ['ATR series', 'Dash 8', 'Saab 340'],
            'description': 'Regional jets and turboprops for short runways'
        },
        'regional_jet': {
            'distance_range': (0, 800), 
            'capacity_range': (50, 120),
            'aircraft_types': ['CRJ series', 'ERJ series'],
            'description': 'Regional jets for short-haul routes'
        },
        'narrow_body': {
            'distance_range': (800, 2500),
            'capacity_range': (120, 200),
            'aircraft_types': ['A320 family', 'B737 series'],
            'description': 'Narrow-body aircraft for medium-haul'
        },
        'large_narrow_body': {
            'distance_range': (2500, 5500),
            'capacity_range': (150, 250),
            'aircraft_types': ['A321', 'B737 MAX', 'B757'],
            'description': 'Large narrow-body or small wide-body'
        },
        'wide_body': {
            'distance_range': (5500, 8000),
            'capacity_range': (250, 400),
            'aircraft_types': ['A330', 'A340', 'A350', 'B777', 'B787'],
            'description': 'Wide-body aircraft for long-haul'
        },
        'ultra_long_range': {
            'distance_range': (8000, 20000),
            'capacity_range': (280, 500),
            'aircraft_types': ['A350-900ULR', 'B777-200LR', 'B747'],
            'description': 'Ultra-long-range wide-body aircraft'
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
    def get_aircraft_category_by_distance(cls, distance_km: float) -> Dict[str, Any]:
        """Determine appropriate aircraft category based on distance rules"""
        for category, config in cls.AIRCRAFT_DISTANCE_RULES.items():
            min_dist, max_dist = config['distance_range']
            if min_dist <= distance_km <= max_dist:
                return {
                    'category': category,
                    **config
                }
        
        # Fallback for very long distances
        return {
            'category': 'ultra_long_range',
            **cls.AIRCRAFT_DISTANCE_RULES['ultra_long_range']
        }
    
    @classmethod
    def get_aircraft_category(cls, distance_km: float, daily_passengers: int) -> str:
        """Determine appropriate aircraft category (legacy method)"""
        category_info = cls.get_aircraft_category_by_distance(distance_km)
        return category_info['category']
    
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
            
            # Print distance-specific frequencies
            if 'short_haul_daily' in config:
                short_range = config['short_haul_daily']
                print(f"    Short-haul daily: {short_range[0]}-{short_range[1]}")
            if 'medium_haul_daily' in config:
                medium_range = config['medium_haul_daily']
                print(f"    Medium-haul daily: {medium_range[0]}-{medium_range[1]}")
            if 'long_haul_daily' in config:
                long_range = config['long_haul_daily']
                print(f"    Long-haul daily: {long_range[0]}-{long_range[1]}")
            if 'short_haul_weekly' in config:
                short_weekly = config['short_haul_weekly']
                print(f"    Short-haul weekly: {short_weekly[0]}-{short_weekly[1]}")
            if 'medium_haul_weekly' in config:
                medium_weekly = config['medium_haul_weekly']
                print(f"    Medium-haul weekly: {medium_weekly[0]}-{medium_weekly[1]}")
            if 'long_haul_weekly' in config:
                long_weekly = config['long_haul_weekly']
                print(f"    Long-haul weekly: {long_weekly[0]}-{long_weekly[1]}")
            
            print(f"    Seasonal boost: {config['seasonal_boost']}x")
        
        print(f"\nSeasonal Multipliers:")
        for season, mult in cls.SEASONAL_MULTIPLIERS.items():
            print(f"  {season.capitalize()}: {mult}x")
        
        print(f"\nAircraft Distance Rules:")
        for category, config in cls.AIRCRAFT_DISTANCE_RULES.items():
            print(f"  {category.replace('_', ' ').title()}:")
            dist_range = config['distance_range']
            cap_range = config['capacity_range']
            print(f"    Distance: {dist_range[0]}-{dist_range[1]} km")
            print(f"    Capacity: {cap_range[0]}-{cap_range[1]} seats")
        
        print(f"\nTime Slots:")
        print(f"  Peak hours: {cls.PEAK_HOURS}")
        print(f"  Off-peak hours: {cls.OFF_PEAK_HOURS}")
        print(f"  Night hours: {cls.NIGHT_HOURS}")


if __name__ == "__main__":
    # Print configuration when run directly
    FlightConfig.print_configuration_summary()