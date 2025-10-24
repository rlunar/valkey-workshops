"""
Database package for the airport workshop system.

This package provides SQLAlchemy models and database configuration
for the Valkey caching workshop demonstrations.
"""

from .models import (
    Base,
    Airport,
    Airline, 
    Flight,
    Passenger,
    Booking,
    create_all_tables,
    drop_all_tables
)

from .config import (
    DatabaseConfig,
    get_database_config,
    initialize_database,
    get_db_session,
    get_db_session_context
)

__all__ = [
    # Models
    'Base',
    'Airport',
    'Airline',
    'Flight', 
    'Passenger',
    'Booking',
    'create_all_tables',
    'drop_all_tables',
    
    # Configuration
    'DatabaseConfig',
    'get_database_config', 
    'initialize_database',
    'get_db_session',
    'get_db_session_context',
]
