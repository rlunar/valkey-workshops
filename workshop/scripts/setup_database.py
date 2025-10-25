#!/usr/bin/env python3
"""
Database setup script for Flughafen DB
Creates tables and optionally loads sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import DatabaseManager
    from models import *  # Import all models
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def setup_database():
    """Create database tables"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    load_dotenv()
    
    try:
        db_manager = DatabaseManager()
        print("Connected to database successfully!")
        
        # Create all tables
        print("Creating database tables...")
        db_manager.create_tables()
        print("✓ Database tables created successfully!")
        
        # Verify that both airport and airport_geo tables were created
        print("Verifying normalized airport schema...")
        _verify_normalized_schema(db_manager)
        
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Ensure your database server is running")
        print("3. Verify database credentials and permissions")
        return False

def _verify_normalized_schema(db_manager):
    """Verify that the normalized airport schema was created correctly"""
    from sqlmodel import text, Session
    
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    
    with Session(db_manager.engine) as session:
        try:
            # Check table existence - database agnostic approach
            if db_type in ["mysql", "mariadb"]:
                airport_exists = session.exec(text("SHOW TABLES LIKE 'airport'")).first()
                airport_geo_exists = session.exec(text("SHOW TABLES LIKE 'airport_geo'")).first()
            else:  # PostgreSQL
                airport_exists = session.exec(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE tablename = 'airport'
                """)).first()
                airport_geo_exists = session.exec(text("""
                    SELECT tablename FROM pg_tables 
                    WHERE tablename = 'airport_geo'
                """)).first()
            
            if airport_exists:
                print("✓ Airport table created")
            else:
                print("✗ Airport table not found")
                
            if airport_geo_exists:
                print("✓ AirportGeo table created")
            else:
                print("✗ AirportGeo table not found")
                
            # Verify foreign key constraint exists
            if db_type in ["mysql", "mariadb"]:
                fk_query = text("""
                    SELECT CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_NAME = 'airport_geo' 
                    AND REFERENCED_TABLE_NAME = 'airport'
                    AND REFERENCED_COLUMN_NAME = 'airport_id'
                """)
            else:  # PostgreSQL
                fk_query = text("""
                    SELECT tc.constraint_name, ccu.table_name, ccu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = 'airport_geo'
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.table_name = 'airport'
                    AND ccu.column_name = 'airport_id'
                """)
            
            result = session.exec(fk_query).first()
            if result:
                print("✓ Foreign key constraint between AirportGeo and Airport verified")
            else:
                print("⚠ Foreign key constraint not found (may be database-specific)")
                
        except Exception as e:
            print(f"⚠ Could not verify schema: {e}")
            print("  (This may be normal for some database configurations)")

def check_database_config():
    """Check database configuration"""
    if not os.path.exists('.env'):
        print("⚠ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    load_dotenv()
    
    db_type = os.getenv("DB_TYPE", "mysql")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME", "flughafendb")
    user = os.getenv("DB_USER")
    
    print(f"Database Configuration:")
    print(f"  Type: {db_type}")
    print(f"  Host: {host}")
    print(f"  Port: {port or 'default'}")
    print(f"  Database: {name}")
    print(f"  User: {user}")
    
    if not user or user == "username":
        print("⚠ Please update your database credentials in .env")
        return False
    
    return True

if __name__ == "__main__":
    print("Flughafen DB Setup")
    print("=" * 20)
    
    if not check_database_config():
        sys.exit(1)
    
    if setup_database():
        print("\n✓ Database setup completed successfully!")
        print("You can now run: uv run python scripts/database_example.py")
    else:
        sys.exit(1)