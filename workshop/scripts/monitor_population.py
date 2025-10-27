#!/usr/bin/env python3
"""
Monitor passenger population progress and provide performance estimates
"""

import time
import sys
import os
from sqlmodel import Session, select, func

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from models.passenger import Passenger, PassengerDetails


def monitor_progress(target_records: int = 10_000_000, check_interval: int = 30):
    """Monitor the population progress and provide estimates"""
    
    db_manager = DatabaseManager()
    start_time = time.time()
    last_count = 0
    last_check_time = start_time
    
    print(f"Monitoring passenger population progress...")
    print(f"Target: {target_records:,} records")
    print(f"Check interval: {check_interval} seconds")
    print("-" * 60)
    
    try:
        while True:
            with Session(db_manager.engine) as session:
                # Get current count
                current_count = session.exec(
                    select(func.count(Passenger.passenger_id))
                ).first()
                
                current_time = time.time()
                elapsed_total = current_time - start_time
                elapsed_interval = current_time - last_check_time
                
                # Calculate rates
                if elapsed_total > 0:
                    overall_rate = current_count / elapsed_total
                else:
                    overall_rate = 0
                
                if elapsed_interval > 0 and last_count > 0:
                    recent_rate = (current_count - last_count) / elapsed_interval
                else:
                    recent_rate = 0
                
                # Calculate estimates
                remaining = target_records - current_count
                if overall_rate > 0:
                    eta_overall = remaining / overall_rate
                else:
                    eta_overall = float('inf')
                
                if recent_rate > 0:
                    eta_recent = remaining / recent_rate
                else:
                    eta_recent = float('inf')
                
                # Progress percentage
                progress = (current_count / target_records) * 100
                
                # Format time estimates
                def format_time(seconds):
                    if seconds == float('inf'):
                        return "Unknown"
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    return f"{hours}h {minutes}m"
                
                # Display progress
                print(f"\nTime: {time.strftime('%H:%M:%S')}")
                print(f"Records: {current_count:,} / {target_records:,} ({progress:.2f}%)")
                print(f"Elapsed: {format_time(elapsed_total)}")
                print(f"Rate (overall): {overall_rate:.1f} records/sec")
                print(f"Rate (recent): {recent_rate:.1f} records/sec")
                print(f"ETA (overall): {format_time(eta_overall)}")
                print(f"ETA (recent): {format_time(eta_recent)}")
                
                # Progress bar
                bar_length = 40
                filled_length = int(bar_length * progress / 100)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                print(f"Progress: [{bar}] {progress:.1f}%")
                
                # Check if completed
                if current_count >= target_records:
                    print(f"\n🎉 Population completed!")
                    print(f"Total time: {format_time(elapsed_total)}")
                    print(f"Average rate: {overall_rate:.1f} records/sec")
                    break
                
                # Update for next iteration
                last_count = current_count
                last_check_time = current_time
                
                # Wait for next check
                time.sleep(check_interval)
                
    except KeyboardInterrupt:
        print(f"\nMonitoring stopped by user")
        print(f"Final count: {current_count:,} records")
    except Exception as e:
        print(f"Error during monitoring: {e}")


def get_current_stats():
    """Get current database statistics"""
    db_manager = DatabaseManager()
    
    try:
        with Session(db_manager.engine) as session:
            passenger_count = session.exec(
                select(func.count(Passenger.passenger_id))
            ).first()
            
            details_count = session.exec(
                select(func.count(PassengerDetails.passenger_id))
            ).first()
            
            print(f"Current Database Statistics:")
            print(f"Passengers: {passenger_count:,}")
            print(f"Passenger Details: {details_count:,}")
            
            if passenger_count != details_count:
                print(f"⚠️  Mismatch detected! {abs(passenger_count - details_count)} records difference")
            else:
                print("✅ Passenger and details counts match")
                
    except Exception as e:
        print(f"Error getting statistics: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor passenger population progress')
    parser.add_argument('--target', type=int, default=10_000_000,
                       help='Target number of records (default: 10,000,000)')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Show current statistics only, do not monitor')
    
    args = parser.parse_args()
    
    if args.stats_only:
        get_current_stats()
    else:
        monitor_progress(args.target, args.interval)


if __name__ == "__main__":
    main()