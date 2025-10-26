#!/usr/bin/env python3
"""
Reset database with new schema (drops existing tables)
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlmodel import SQLModel, text
    from models.database import DatabaseManager
    from dotenv import load_dotenv
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Dependencies not available: {e}")
    print("Install with: uv sync")
    DEPENDENCIES_AVAILABLE = False

def reset_database(verbose: bool = False, auto_confirm: bool = False):
    """Drop all tables and recreate with new schema"""
    if not DEPENDENCIES_AVAILABLE:
        print("Please install dependencies first: uv sync")
        return False
    
    if not os.path.exists('.env'):
        print("✗ .env file not found")
        print("Copy .env.example to .env and configure your database settings")
        return False
    
    load_dotenv()
    
    try:
        if verbose:
            print("Database Schema Reset")
            print("=" * 21)
            print("⚠️  WARNING: This will DROP ALL EXISTING TABLES!")
        
        if not auto_confirm:
            response = input("Reset database (DROP ALL TABLES)? (y/N): ").strip().lower()
            if response != 'y':
                if verbose:
                    print("Operation cancelled")
                return False
        
        db_manager = DatabaseManager()
        if verbose:
            print("✓ Connected to database successfully!")
        
        # Drop all tables (disable foreign key checks first)
        if verbose:
            print("Dropping existing tables...")
        
        # Disable foreign key checks to allow dropping tables with constraints
        with db_manager.engine.connect() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            connection.commit()
        
        SQLModel.metadata.drop_all(db_manager.engine)
        
        # Re-enable foreign key checks
        with db_manager.engine.connect() as connection:
            connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            connection.commit()
            
        if verbose:
            print("✓ Dropped all existing tables")
        
        # Create new tables with updated schema
        if verbose:
            print("Creating tables with new schema...")
        SQLModel.metadata.create_all(db_manager.engine)
        if verbose:
            print("✓ Created all tables with new schema")
        
        print("✅ Database reset completed successfully!")
        if verbose:
            print("You can now run: uv run python scripts/download_airports.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Reset Database Schema')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose output (default: minimal output)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-confirm reset without prompting')
    args = parser.parse_args()
    
    success = reset_database(verbose=args.verbose, auto_confirm=args.yes)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()