#!/usr/bin/env python3
"""
Passenger Data Management Tools - Main Entry Point

This script provides a unified interface to all passenger data management tools.
"""

import sys
import subprocess
import argparse


def run_population(args):
    """Run passenger population script"""
    cmd = ["python", "scripts/populate_passengers.py"]
    if args.total_records:
        cmd.extend(["--total-records", str(args.total_records)])
    if args.batch_size:
        cmd.extend(["--batch-size", str(args.batch_size)])
    
    return subprocess.run(cmd).returncode


def run_test(args):
    """Run test population script"""
    return subprocess.run(["python", "scripts/test_passenger_generation.py"]).returncode


def run_monitor(args):
    """Run monitoring script"""
    cmd = ["python", "scripts/monitor_population.py"]
    if args.target:
        cmd.extend(["--target", str(args.target)])
    if args.interval:
        cmd.extend(["--interval", str(args.interval)])
    if args.stats_only:
        cmd.append("--stats-only")
    
    return subprocess.run(cmd).returncode


def run_validate(args):
    """Run validation script"""
    return subprocess.run(["python", "scripts/validate_passenger_data.py"]).returncode


def show_help():
    """Show help information"""
    print("""
🚀 Passenger Data Management Tools
==================================

Available Commands:

1. populate    - Generate passenger records (default: 10M records)
2. test        - Test generation with small dataset (1K records)  
3. monitor     - Monitor population progress in real-time
4. validate    - Validate data quality and show distributions
5. help        - Show this help message

Examples:
---------
# Full population with default settings
python scripts/passenger_tools.py populate

# Custom population
python scripts/passenger_tools.py populate --total-records 5000000 --batch-size 5000

# Test with small dataset
python scripts/passenger_tools.py test

# Monitor progress
python scripts/passenger_tools.py monitor

# Get current stats only
python scripts/passenger_tools.py monitor --stats-only

# Validate data after population
python scripts/passenger_tools.py validate

For detailed help on any command:
python scripts/passenger_tools.py <command> --help
""")


def main():
    parser = argparse.ArgumentParser(
        description='Passenger Data Management Tools',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Population command
    pop_parser = subparsers.add_parser('populate', help='Generate passenger records')
    pop_parser.add_argument('--total-records', type=int, help='Total records to generate')
    pop_parser.add_argument('--batch-size', type=int, help='Batch size for inserts')
    
    # Test command
    subparsers.add_parser('test', help='Test generation with small dataset')
    
    # Monitor command
    mon_parser = subparsers.add_parser('monitor', help='Monitor population progress')
    mon_parser.add_argument('--target', type=int, help='Target number of records')
    mon_parser.add_argument('--interval', type=int, help='Check interval in seconds')
    mon_parser.add_argument('--stats-only', action='store_true', help='Show stats only')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate data quality')
    
    # Help command
    subparsers.add_parser('help', help='Show detailed help')
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        show_help()
        return 0
    
    # Route to appropriate function
    if args.command == 'populate':
        return run_population(args)
    elif args.command == 'test':
        return run_test(args)
    elif args.command == 'monitor':
        return run_monitor(args)
    elif args.command == 'validate':
        return run_validate(args)
    else:
        print(f"Unknown command: {args.command}")
        show_help()
        return 1


if __name__ == "__main__":
    exit(main())