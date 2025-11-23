#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Multi-threaded Performance Test Demo

This script demonstrates how to run performance tests against a MySQL database
with Valkey caching, simulating multiple concurrent users and capturing detailed
metrics in JSON format.

Usage:
    python samples/multi_threaded_performance_test.py --users 4 --queries 10 --read_rate 80
    python samples/multi_threaded_performance_test.py --users 10 --queries 100 --read_rate 90 --ssl true
"""

import json
import random
import threading
import sys
import os
import time
import string
import argparse
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import get_db_engine, get_cache_client

# Load environment variables
load_dotenv()


class PerformanceTest:
    """Manages multi-threaded performance testing with metrics collection"""
    
    def __init__(self, args):
        self.args = args
        self.read_count = 0
        self.write_count = 0
        self.cache_hit = 0
        self.cache_miss = 0
        self.thread_metrics = {}
        self.lock = threading.Lock()
        
        # Database configuration from environment variables
        self.db_params = {
            "host": os.getenv('DB_HOST', "localhost"),
            "database": os.getenv('DB_NAME', "flughafendb_large"),
            "user": os.getenv('DB_USER', "root"),
            "password": os.getenv('DB_PASSWORD', ""),
            "port": int(os.getenv('DB_PORT', 3306)),
            "valkey_host": os.getenv('CACHE_HOST', 'localhost'),
            "valkey_port": int(os.getenv('CACHE_PORT', 6379)),
        }
        
        # SQL queries
        self.READ_QUERY = text("""
            SELECT p.firstname, p.lastname, COUNT(*) as booking_count
            FROM flughafendb.passenger p
            JOIN flughafendb.booking b ON p.passenger_id = b.passenger_id
            WHERE p.passenger_id = :passenger
            GROUP BY p.firstname, p.lastname
        """)
        
        self.WRITE_QUERY = text("""
            INSERT INTO flughafendb.booking (flight_id, passenger_id, price, seat)
            VALUES(:flight, :passenger, 1000.00, '1A')
        """)
        
        self._setup_connections()
    
    def _setup_connections(self):
        """Initialize database and cache connections"""
        try:
            # Database engines using core module
            self.engine_rw = get_db_engine(
                host=self.db_params['host'],
                port=str(self.db_params['port']),
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                pool_size=self.args.users,
                max_overflow=50
            )
            self.engine_ro = get_db_engine(
                host=self.db_params['host'],
                port=str(self.db_params['port']),
                user=self.db_params['user'],
                password=self.db_params['password'],
                database=self.db_params['database'],
                pool_size=self.args.users,
                max_overflow=50
            )
            
            # Test connections
            self.engine_rw.connect()
            self.engine_ro.connect()
            print("✓ Connected to MySQL database")
            
            # Valkey connections using core module
            cache_write = get_cache_client(
                host=self.db_params['valkey_host'],
                port=self.db_params['valkey_port']
            )
            cache_read = get_cache_client(
                host=self.db_params['valkey_host'],
                port=self.db_params['valkey_port']
            )
            
            # Get underlying clients for direct access (needed for performance testing)
            self.valkey_write = cache_write.client
            self.valkey_read = cache_read.client
            
            # Test Valkey connection
            self.valkey_write.ping()
            print("✓ Connected to Valkey cache")
            
        except Exception as e:
            print(f"✗ Connection error: {e}")
            sys.exit(1)
    
    def _should_read(self):
        """Determine if operation should be read or write based on read_rate"""
        return random.triangular(0, 1, self.args.read_rate) < self.args.read_rate
    
    def _execute_read(self, engine, query):
        """Execute a read query"""
        with engine.connect() as conn:
            result = conn.execute(query).fetchall()
        return result
    
    def _execute_write(self, engine, query):
        """Execute a write query"""
        with engine.connect() as conn:
            result = conn.execute(query)
        return result
    
    def _record_metric(self, timestamp, query_time_ns, operation_type):
        """Thread-safe metric recording (stores nanoseconds internally)"""
        with self.lock:
            if timestamp not in self.thread_metrics:
                self.thread_metrics[timestamp] = {
                    "count": 0,
                    "total_time_ns": 0,
                    "min_time_ns": float('inf'),
                    "max_time_ns": 0,
                    "reads": 0,
                    "writes": 0,
                    "cache_hits": 0,
                    "cache_misses": 0
                }
            
            metrics = self.thread_metrics[timestamp]
            metrics["count"] += 1
            metrics["total_time_ns"] += query_time_ns
            metrics["min_time_ns"] = min(metrics["min_time_ns"], query_time_ns)
            metrics["max_time_ns"] = max(metrics["max_time_ns"], query_time_ns)
            
            if operation_type == "read":
                metrics["reads"] += 1
            elif operation_type == "write":
                metrics["writes"] += 1
            elif operation_type == "cache_hit":
                metrics["cache_hits"] += 1
            elif operation_type == "cache_miss":
                metrics["cache_misses"] += 1
    
    def worker_thread(self):
        """Worker function executed by each thread"""
        for _ in range(self.args.queries):
            passenger_id = random.randrange(4, 35000)
            flight_id = random.randrange(4, 35000)
            cache_key = f"bookings:{passenger_id}"
            
            start_time_ns = time.time_ns()
            
            if self._should_read():
                # Read operation with cache-aside pattern
                cached_data = self.valkey_read.get(cache_key)
                
                if cached_data:
                    # Cache hit
                    with self.lock:
                        self.read_count += 1
                        self.cache_hit += 1
                    end_time_ns = time.time_ns()
                    query_time_ns = end_time_ns - start_time_ns
                    self._record_metric(str(int(start_time_ns // 1_000_000_000)), query_time_ns, "cache_hit")
                else:
                    # Cache miss - fetch from database
                    read_query = self.READ_QUERY.bindparams(passenger=passenger_id)
                    data = self._execute_read(self.engine_ro, read_query)
                    end_time_ns = time.time_ns()
                    
                    # Update cache
                    self.valkey_write.set(cache_key, str(data))
                    
                    query_time_ns = end_time_ns - start_time_ns
                    with self.lock:
                        self.read_count += 1
                        self.cache_miss += 1
                    self._record_metric(str(int(start_time_ns // 1_000_000_000)), query_time_ns, "cache_miss")
            else:
                # Write operation
                write_query = self.WRITE_QUERY.bindparams(flight=flight_id, passenger=passenger_id)
                self._execute_write(self.engine_rw, write_query)
                
                # Update cache after write
                read_query = self.READ_QUERY.bindparams(passenger=passenger_id)
                data = self._execute_read(self.engine_ro, read_query)
                self.valkey_write.set(cache_key, str(data))
                
                end_time_ns = time.time_ns()
                query_time_ns = end_time_ns - start_time_ns
                
                with self.lock:
                    self.write_count += 1
                self._record_metric(str(int(start_time_ns // 1_000_000_000)), query_time_ns, "write")
    
    def run(self):
        """Execute the performance test"""
        print(f"\n{'='*60}")
        print(f"Starting Performance Test")
        print(f"{'='*60}")
        print(f"Users (threads): {self.args.users}")
        print(f"Queries per user: {self.args.queries}")
        print(f"Read rate: {int(self.args.read_rate * 100)}%")
        print(f"SSL enabled: {self.args.ssl}")
        print(f"{'='*60}\n")
        
        # Create and start threads
        threads = []
        test_start = time.time()
        
        for i in range(self.args.users):
            thread = threading.Thread(target=self.worker_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        test_end = time.time()
        total_duration = test_end - test_start
        
        # Display results
        self._display_results(total_duration)
        
        # Save results to JSON
        log_file = self._save_results(total_duration)
        
        return log_file
    
    def _display_results(self, duration):
        """Display test results"""
        total_queries = self.read_count + self.write_count
        
        print(f"\n{'='*60}")
        print(f"Performance Test Results")
        print(f"{'='*60}")
        print(f"Total duration: {duration:.2f} seconds")
        print(f"Total queries: {total_queries}")
        print(f"Queries per second: {total_queries / duration:.2f}")
        print(f"\nOperation Breakdown:")
        print(f"  Reads: {self.read_count} ({self.read_count/total_queries*100:.1f}%)")
        print(f"  Writes: {self.write_count} ({self.write_count/total_queries*100:.1f}%)")
        print(f"\nCache Performance:")
        print(f"  Cache hits: {self.cache_hit}")
        print(f"  Cache misses: {self.cache_miss}")
        if self.read_count > 0:
            print(f"  Hit rate: {self.cache_hit/self.read_count*100:.1f}%")
        print(f"{'='*60}\n")
    
    def _save_results(self, duration):
        """Save results to JSON log file"""
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Generate log filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"logs/perf_test_{timestamp}_{self.args.log_tag}.json"
        
        # Calculate aggregate metrics (convert nanoseconds to microseconds for presentation)
        aggregate_metrics = {
            "avg_time_ns": 0,
            "min_time_ns": float('inf'),
            "max_time_ns": 0
        }
        
        for ts_metrics in self.thread_metrics.values():
            if ts_metrics["count"] > 0:
                avg_ns = ts_metrics["total_time_ns"] / ts_metrics["count"]
                aggregate_metrics["avg_time_ns"] += avg_ns
                aggregate_metrics["min_time_ns"] = min(aggregate_metrics["min_time_ns"], ts_metrics["min_time_ns"])
                aggregate_metrics["max_time_ns"] = max(aggregate_metrics["max_time_ns"], ts_metrics["max_time_ns"])
        
        if self.thread_metrics:
            aggregate_metrics["avg_time_ns"] /= len(self.thread_metrics)
        
        # Convert time series metrics to microseconds for presentation
        time_series_metrics_us = {}
        for ts, metrics in self.thread_metrics.items():
            time_series_metrics_us[ts] = {
                "count": metrics["count"],
                "total_time_us": round(metrics["total_time_ns"] / 1000, 2),
                "avg_time_us": round(metrics["total_time_ns"] / metrics["count"] / 1000, 2) if metrics["count"] > 0 else 0,
                "min_time_us": round(metrics["min_time_ns"] / 1000, 2),
                "max_time_us": round(metrics["max_time_ns"] / 1000, 2),
                "reads": metrics["reads"],
                "writes": metrics["writes"],
                "cache_hits": metrics["cache_hits"],
                "cache_misses": metrics["cache_misses"]
            }
        
        # Prepare output data
        output_data = {
            "test_config": {
                "users": self.args.users,
                "queries_per_user": self.args.queries,
                "read_rate": int(self.args.read_rate * 100),
                "ssl_enabled": self.args.ssl,
                "log_tag": self.args.log_tag
            },
            "summary": {
                "total_duration_seconds": round(duration, 2),
                "total_queries": self.read_count + self.write_count,
                "queries_per_second": round((self.read_count + self.write_count) / duration, 2),
                "reads": self.read_count,
                "writes": self.write_count,
                "cache_hits": self.cache_hit,
                "cache_misses": self.cache_miss,
                "cache_hit_rate_percent": round(self.cache_hit / self.read_count * 100, 2) if self.read_count > 0 else 0
            },
            "aggregate_metrics": {
                "avg_query_time_us": round(aggregate_metrics["avg_time_ns"] / 1000, 2),
                "min_query_time_us": round(aggregate_metrics["min_time_ns"] / 1000, 2),
                "max_query_time_us": round(aggregate_metrics["max_time_ns"] / 1000, 2)
            },
            "time_series_metrics": time_series_metrics_us
        }
        
        # Write to file
        with open(log_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✓ Results saved to: {log_file}\n")
        return log_file


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Multi-threaded performance test for MySQL + Valkey cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with 4 users, 10 queries each, 80% reads
  python samples/multi_threaded_performance_test.py
  
  # High concurrency test
  python samples/multi_threaded_performance_test.py --users 20 --queries 100
  
  # Write-heavy workload with SSL
  python samples/multi_threaded_performance_test.py --users 10 --queries 50 --read_rate 30 --ssl true
        """
    )
    
    parser.add_argument('--users', type=int, default=4,
                       help='Number of concurrent users (threads) to simulate (default: 4)')
    parser.add_argument('--queries', type=int, default=10,
                       help='Number of queries per user (default: 10)')
    parser.add_argument('--read_rate', type=int, default=80,
                       help='Percentage of read operations (0-100, default: 80)')
    parser.add_argument('--ssl', type=lambda x: str(x).lower() == 'true', default=False,
                       help='Enable SSL/TLS for Valkey connection (default: false)')
    parser.add_argument('--log_tag', type=str, default=None,
                       help='Custom tag for log file (default: random 8-char string)')
    
    args = parser.parse_args()
    
    # Validate and adjust parameters
    args.read_rate = max(0, min(100, args.read_rate)) / 100
    
    if not args.log_tag:
        args.log_tag = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    # Run the test
    try:
        test = PerformanceTest(args)
        test.run()
    except KeyboardInterrupt:
        print("\n\n✗ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
