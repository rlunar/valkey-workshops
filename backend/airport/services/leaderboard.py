"""
Real-time leaderboard system using Valkey sorted sets for passenger booking rankings.

This module implements a comprehensive leaderboard system that tracks passenger
booking statistics and provides real-time rankings with atomic operations,
pagination support, and memory optimization features.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import valkey
from valkey.exceptions import ConnectionError, ResponseError

from ..cache.client import ValkeyClient
from ..models.passenger import PassengerModel

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    """Individual leaderboard entry with passenger information and score."""
    passenger_id: str
    passenger_name: str
    booking_count: int
    rank: int
    last_updated: datetime


@dataclass
class LeaderboardStats:
    """Leaderboard statistics and performance metrics."""
    total_passengers: int
    total_bookings: int
    top_score: int
    average_score: float
    memory_usage_bytes: int
    last_updated: datetime
    cache_hits: int = 0
    cache_misses: int = 0


class LeaderboardSystem:
    """
    Real-time leaderboard system using Valkey sorted sets.
    
    Features:
    - Atomic score updates using ZADD operations
    - Range queries with pagination support using ZREVRANGE
    - Individual rank lookup with ZREVRANK operations
    - Memory optimization for large-scale data
    - Leaderboard reset and archival functionality
    - Performance monitoring and statistics
    """
    
    def __init__(self, valkey_client: ValkeyClient, leaderboard_name: str = "passenger_bookings"):
        """
        Initialize leaderboard system.
        
        Args:
            valkey_client: ValkeyClient instance for cache operations
            leaderboard_name: Name of the leaderboard (used as key prefix)
        """
        self.valkey = valkey_client
        self.leaderboard_name = leaderboard_name
        self.leaderboard_key = f"leaderboard:{leaderboard_name}"
        self.passenger_details_key = f"leaderboard:{leaderboard_name}:passengers"
        self.stats_key = f"leaderboard:{leaderboard_name}:stats"
        self.archive_key_prefix = f"leaderboard:{leaderboard_name}:archive"
        
        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_stats_update = 0.0
        self._stats_cache_ttl = 60  # Cache stats for 1 minute
        
        logger.info(f"Initialized leaderboard system: {leaderboard_name}")
    
    async def update_passenger_score(self, passenger_id: str, booking_count: int, 
                                   passenger_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update passenger booking count with atomic operations.
        
        Uses ZADD for atomic score updates to maintain consistency
        in high-concurrency scenarios.
        
        Args:
            passenger_id: Unique passenger identifier
            booking_count: New total booking count for the passenger
            passenger_info: Optional passenger details (name, etc.)
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Use pipeline for atomic operations
            pipe = client.pipeline()
            
            # Update score in sorted set
            pipe.zadd(self.leaderboard_key, {passenger_id: booking_count})
            
            # Store passenger details if provided
            if passenger_info:
                passenger_key = f"{self.passenger_details_key}:{passenger_id}"
                passenger_data = {
                    "passenger_id": passenger_id,
                    "name": passenger_info.get("name", "Unknown"),
                    "firstname": passenger_info.get("firstname", ""),
                    "lastname": passenger_info.get("lastname", ""),
                    "last_updated": datetime.now().isoformat()
                }
                pipe.hset(passenger_key, mapping=passenger_data)
                pipe.expire(passenger_key, 86400)  # Expire passenger details after 24 hours
            
            # Execute pipeline atomically
            results = pipe.execute()
            
            # Update statistics
            await self._update_stats_async()
            
            logger.debug(f"Updated passenger {passenger_id} score to {booking_count}")
            return True
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to update passenger score: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating passenger score: {e}")
            return False
    
    async def increment_passenger_score(self, passenger_id: str, increment: int = 1,
                                      passenger_info: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Increment passenger booking count atomically.
        
        Args:
            passenger_id: Unique passenger identifier
            increment: Amount to increment (default: 1)
            passenger_info: Optional passenger details
            
        Returns:
            Optional[int]: New score after increment, None if failed
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Use ZINCRBY for atomic increment
            new_score = client.zincrby(self.leaderboard_key, increment, passenger_id)
            
            # Store passenger details if provided
            if passenger_info:
                passenger_key = f"{self.passenger_details_key}:{passenger_id}"
                passenger_data = {
                    "passenger_id": passenger_id,
                    "name": passenger_info.get("name", "Unknown"),
                    "firstname": passenger_info.get("firstname", ""),
                    "lastname": passenger_info.get("lastname", ""),
                    "last_updated": datetime.now().isoformat()
                }
                client.hset(passenger_key, mapping=passenger_data)
                client.expire(passenger_key, 86400)
            
            # Update statistics
            await self._update_stats_async()
            
            logger.debug(f"Incremented passenger {passenger_id} score by {increment} to {new_score}")
            return int(new_score)
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to increment passenger score: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error incrementing passenger score: {e}")
            return None
    
    async def get_top_passengers(self, limit: int = 10, offset: int = 0) -> List[LeaderboardEntry]:
        """
        Get top passengers with pagination support using ZREVRANGE.
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip (for pagination)
            
        Returns:
            List[LeaderboardEntry]: Top passengers with their rankings
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Calculate range for pagination
            start = offset
            end = offset + limit - 1
            
            # Get top passengers with scores using ZREVRANGE
            results = client.zrevrange(
                self.leaderboard_key, 
                start, 
                end, 
                withscores=True
            )
            
            if not results:
                self._cache_misses += 1
                return []
            
            self._cache_hits += 1
            
            # Convert results to LeaderboardEntry objects
            entries = []
            for i, (passenger_id, score) in enumerate(results):
                # Get passenger details
                passenger_info = await self._get_passenger_info(passenger_id.decode())
                
                entry = LeaderboardEntry(
                    passenger_id=passenger_id.decode(),
                    passenger_name=passenger_info.get("name", "Unknown"),
                    booking_count=int(score),
                    rank=start + i + 1,  # Calculate actual rank
                    last_updated=datetime.now()
                )
                entries.append(entry)
            
            logger.debug(f"Retrieved {len(entries)} top passengers (offset: {offset}, limit: {limit})")
            return entries
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to get top passengers: {e}")
            self._cache_misses += 1
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting top passengers: {e}")
            self._cache_misses += 1
            return []
    
    async def get_passenger_rank(self, passenger_id: str) -> Optional[int]:
        """
        Get individual passenger rank using ZREVRANK.
        
        Args:
            passenger_id: Unique passenger identifier
            
        Returns:
            Optional[int]: Passenger rank (1-based), None if not found
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get rank using ZREVRANK (0-based, so add 1)
            rank = client.zrevrank(self.leaderboard_key, passenger_id)
            
            if rank is None:
                self._cache_misses += 1
                return None
            
            self._cache_hits += 1
            actual_rank = rank + 1  # Convert to 1-based ranking
            
            logger.debug(f"Passenger {passenger_id} rank: {actual_rank}")
            return actual_rank
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to get passenger rank: {e}")
            self._cache_misses += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting passenger rank: {e}")
            self._cache_misses += 1
            return None
    
    async def get_passenger_score(self, passenger_id: str) -> Optional[int]:
        """
        Get passenger's current booking count.
        
        Args:
            passenger_id: Unique passenger identifier
            
        Returns:
            Optional[int]: Current booking count, None if not found
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            score = client.zscore(self.leaderboard_key, passenger_id)
            
            if score is None:
                self._cache_misses += 1
                return None
            
            self._cache_hits += 1
            return int(score)
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to get passenger score: {e}")
            self._cache_misses += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting passenger score: {e}")
            self._cache_misses += 1
            return None
    
    async def get_passengers_in_range(self, start_rank: int, end_rank: int) -> List[LeaderboardEntry]:
        """
        Get passengers within a specific rank range.
        
        Args:
            start_rank: Starting rank (1-based)
            end_rank: Ending rank (1-based, inclusive)
            
        Returns:
            List[LeaderboardEntry]: Passengers in the specified range
        """
        # Convert to 0-based indexing for Valkey
        offset = start_rank - 1
        limit = end_rank - start_rank + 1
        
        return await self.get_top_passengers(limit=limit, offset=offset)
    
    async def _get_passenger_info(self, passenger_id: str) -> Dict[str, Any]:
        """
        Get passenger information from cache.
        
        Args:
            passenger_id: Unique passenger identifier
            
        Returns:
            Dict[str, Any]: Passenger information
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            passenger_key = f"{self.passenger_details_key}:{passenger_id}"
            info = client.hgetall(passenger_key)
            
            if not info:
                return {"name": f"Passenger {passenger_id}"}
            
            # Decode bytes to strings
            decoded_info = {k.decode(): v.decode() for k, v in info.items()}
            
            # Format name
            firstname = decoded_info.get("firstname", "")
            lastname = decoded_info.get("lastname", "")
            if firstname and lastname:
                decoded_info["name"] = f"{firstname} {lastname}"
            elif firstname:
                decoded_info["name"] = firstname
            elif lastname:
                decoded_info["name"] = lastname
            else:
                decoded_info["name"] = f"Passenger {passenger_id}"
            
            return decoded_info
            
        except Exception as e:
            logger.warning(f"Failed to get passenger info for {passenger_id}: {e}")
            return {"name": f"Passenger {passenger_id}"}
    
    async def _update_stats_async(self) -> None:
        """Update leaderboard statistics asynchronously."""
        current_time = time.time()
        
        # Throttle stats updates to avoid excessive computation
        if current_time - self._last_stats_update < self._stats_cache_ttl:
            return
        
        try:
            stats = await self.get_leaderboard_stats()
            if stats:
                self._last_stats_update = current_time
        except Exception as e:
            logger.warning(f"Failed to update stats: {e}")
    
    async def get_leaderboard_stats(self) -> Optional[LeaderboardStats]:
        """
        Get comprehensive leaderboard statistics and performance metrics.
        
        Returns:
            Optional[LeaderboardStats]: Statistics object, None if failed
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get basic leaderboard info
            total_passengers = client.zcard(self.leaderboard_key)
            
            if total_passengers == 0:
                return LeaderboardStats(
                    total_passengers=0,
                    total_bookings=0,
                    top_score=0,
                    average_score=0.0,
                    memory_usage_bytes=0,
                    last_updated=datetime.now(),
                    cache_hits=self._cache_hits,
                    cache_misses=self._cache_misses
                )
            
            # Get score statistics
            top_entry = client.zrevrange(self.leaderboard_key, 0, 0, withscores=True)
            top_score = int(top_entry[0][1]) if top_entry else 0
            
            # Calculate total bookings and average
            all_scores = client.zrange(self.leaderboard_key, 0, -1, withscores=True)
            total_bookings = sum(int(score) for _, score in all_scores)
            average_score = total_bookings / total_passengers if total_passengers > 0 else 0.0
            
            # Estimate memory usage (approximate)
            memory_usage = await self._estimate_memory_usage()
            
            stats = LeaderboardStats(
                total_passengers=total_passengers,
                total_bookings=total_bookings,
                top_score=top_score,
                average_score=average_score,
                memory_usage_bytes=memory_usage,
                last_updated=datetime.now(),
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses
            )
            
            # Cache stats for performance
            stats_data = {
                "total_passengers": stats.total_passengers,
                "total_bookings": stats.total_bookings,
                "top_score": stats.top_score,
                "average_score": stats.average_score,
                "memory_usage_bytes": stats.memory_usage_bytes,
                "last_updated": stats.last_updated.isoformat(),
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses
            }
            client.setex(self.stats_key, self._stats_cache_ttl, json.dumps(stats_data))
            
            logger.debug(f"Generated leaderboard stats: {stats}")
            return stats
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to get leaderboard stats: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting leaderboard stats: {e}")
            return None
    
    async def reset_leaderboard(self, archive: bool = True) -> bool:
        """
        Reset leaderboard with optional archival.
        
        Args:
            archive: Whether to archive current leaderboard before reset
            
        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            if archive:
                # Archive current leaderboard
                archive_success = await self._archive_leaderboard()
                if not archive_success:
                    logger.warning("Failed to archive leaderboard, proceeding with reset anyway")
            
            # Use pipeline for atomic reset
            pipe = client.pipeline()
            
            # Delete leaderboard and related keys
            pipe.delete(self.leaderboard_key)
            pipe.delete(self.stats_key)
            
            # Delete all passenger detail keys
            passenger_keys = client.keys(f"{self.passenger_details_key}:*")
            if passenger_keys:
                pipe.delete(*passenger_keys)
            
            # Execute pipeline
            results = pipe.execute()
            
            # Reset performance counters
            self._cache_hits = 0
            self._cache_misses = 0
            self._last_stats_update = 0.0
            
            logger.info(f"Reset leaderboard '{self.leaderboard_name}' (archived: {archive})")
            return True
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to reset leaderboard: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error resetting leaderboard: {e}")
            return False
    
    async def _archive_leaderboard(self) -> bool:
        """
        Archive current leaderboard data.
        
        Returns:
            bool: True if archival was successful, False otherwise
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Generate archive key with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_key = f"{self.archive_key_prefix}:{timestamp}"
            
            # Check if leaderboard exists
            if not client.exists(self.leaderboard_key):
                logger.info("No leaderboard data to archive")
                return True
            
            # Copy leaderboard to archive
            # Note: COPY command might not be available in all Valkey versions
            # Using ZUNIONSTORE as alternative
            result = client.zunionstore(archive_key, [self.leaderboard_key])
            
            if result > 0:
                # Set expiration for archive (30 days)
                client.expire(archive_key, 30 * 24 * 3600)
                
                # Store archive metadata
                archive_meta_key = f"{archive_key}:meta"
                archive_metadata = {
                    "archived_at": datetime.now().isoformat(),
                    "original_key": self.leaderboard_key,
                    "total_entries": result,
                    "leaderboard_name": self.leaderboard_name
                }
                client.setex(archive_meta_key, 30 * 24 * 3600, json.dumps(archive_metadata))
                
                logger.info(f"Archived leaderboard to {archive_key} with {result} entries")
                return True
            else:
                logger.warning("No entries found to archive")
                return True
                
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to archive leaderboard: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error archiving leaderboard: {e}")
            return False
    
    async def get_archived_leaderboards(self) -> List[Dict[str, Any]]:
        """
        Get list of archived leaderboards.
        
        Returns:
            List[Dict[str, Any]]: List of archived leaderboard metadata
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Find all archive keys
            archive_pattern = f"{self.archive_key_prefix}:*:meta"
            archive_keys = client.keys(archive_pattern)
            
            archives = []
            for key in archive_keys:
                try:
                    metadata_json = client.get(key)
                    if metadata_json:
                        metadata = json.loads(metadata_json.decode())
                        archives.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to parse archive metadata for {key}: {e}")
            
            # Sort by archived_at timestamp (newest first)
            archives.sort(key=lambda x: x.get("archived_at", ""), reverse=True)
            
            return archives
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to get archived leaderboards: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting archived leaderboards: {e}")
            return []
    
    async def _estimate_memory_usage(self) -> int:
        """
        Estimate memory usage of leaderboard data.
        
        Returns:
            int: Estimated memory usage in bytes
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get memory usage of main leaderboard key
            try:
                # MEMORY USAGE command (available in newer versions)
                main_memory = client.memory_usage(self.leaderboard_key) or 0
            except (ResponseError, AttributeError):
                # Fallback: estimate based on entry count
                entry_count = client.zcard(self.leaderboard_key)
                # Rough estimate: 50 bytes per entry (key + score + overhead)
                main_memory = entry_count * 50
            
            # Estimate passenger details memory
            passenger_keys = client.keys(f"{self.passenger_details_key}:*")
            passenger_memory = len(passenger_keys) * 200  # Rough estimate: 200 bytes per passenger record
            
            total_memory = main_memory + passenger_memory
            
            logger.debug(f"Estimated memory usage: {total_memory} bytes")
            return total_memory
            
        except Exception as e:
            logger.warning(f"Failed to estimate memory usage: {e}")
            return 0
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """
        Perform memory optimization operations.
        
        Returns:
            Dict[str, Any]: Optimization results and statistics
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            initial_memory = await self._estimate_memory_usage()
            
            # Clean up expired passenger details
            passenger_keys = client.keys(f"{self.passenger_details_key}:*")
            expired_keys = []
            
            for key in passenger_keys:
                ttl = client.ttl(key)
                if ttl == -1:  # No expiration set
                    client.expire(key, 86400)  # Set 24-hour expiration
                elif ttl == -2:  # Key doesn't exist (race condition)
                    expired_keys.append(key)
            
            # Remove passengers with zero scores (if any)
            zero_score_passengers = client.zrangebyscore(self.leaderboard_key, 0, 0)
            removed_passengers = 0
            
            if zero_score_passengers:
                # Only remove if they haven't been active recently
                for passenger_id in zero_score_passengers:
                    passenger_key = f"{self.passenger_details_key}:{passenger_id.decode()}"
                    last_updated_str = client.hget(passenger_key, "last_updated")
                    
                    if last_updated_str:
                        try:
                            last_updated = datetime.fromisoformat(last_updated_str.decode())
                            if datetime.now() - last_updated > timedelta(days=7):
                                client.zrem(self.leaderboard_key, passenger_id)
                                client.delete(passenger_key)
                                removed_passengers += 1
                        except Exception:
                            pass  # Skip if date parsing fails
            
            final_memory = await self._estimate_memory_usage()
            memory_saved = initial_memory - final_memory
            
            optimization_results = {
                "initial_memory_bytes": initial_memory,
                "final_memory_bytes": final_memory,
                "memory_saved_bytes": memory_saved,
                "expired_keys_cleaned": len(expired_keys),
                "inactive_passengers_removed": removed_passengers,
                "optimization_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Memory optimization completed: saved {memory_saved} bytes")
            return optimization_results
            
        except (ConnectionError, ResponseError) as e:
            logger.error(f"Failed to optimize memory: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during memory optimization: {e}")
            return {"error": str(e)}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Dict[str, Any]: Performance metrics and statistics
        """
        stats = await self.get_leaderboard_stats()
        
        hit_ratio = 0.0
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            hit_ratio = self._cache_hits / total_requests
        
        metrics = {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "leaderboard_stats": stats.__dict__ if stats else None,
            "last_updated": datetime.now().isoformat()
        }
        
        return metrics
    
    async def simulate_high_frequency_updates(self, num_passengers: int = 100, 
                                            updates_per_passenger: int = 10) -> Dict[str, Any]:
        """
        Simulate high-frequency leaderboard updates for performance testing.
        
        Args:
            num_passengers: Number of passengers to simulate
            updates_per_passenger: Number of updates per passenger
            
        Returns:
            Dict[str, Any]: Simulation results and performance metrics
        """
        start_time = time.time()
        successful_updates = 0
        failed_updates = 0
        
        logger.info(f"Starting leaderboard simulation: {num_passengers} passengers, "
                   f"{updates_per_passenger} updates each")
        
        try:
            # Generate passenger data
            passengers = []
            for i in range(num_passengers):
                passenger_info = {
                    "name": f"Test Passenger {i+1}",
                    "firstname": f"Test{i+1}",
                    "lastname": f"Passenger{i+1}"
                }
                passengers.append((f"test_passenger_{i+1}", passenger_info))
            
            # Perform updates
            for passenger_id, passenger_info in passengers:
                for update_num in range(updates_per_passenger):
                    try:
                        # Simulate booking increment
                        result = await self.increment_passenger_score(
                            passenger_id, 
                            increment=1, 
                            passenger_info=passenger_info
                        )
                        
                        if result is not None:
                            successful_updates += 1
                        else:
                            failed_updates += 1
                            
                    except Exception as e:
                        logger.warning(f"Update failed for {passenger_id}: {e}")
                        failed_updates += 1
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Get final statistics
            final_stats = await self.get_leaderboard_stats()
            
            simulation_results = {
                "simulation_duration_seconds": duration,
                "total_updates_attempted": num_passengers * updates_per_passenger,
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "updates_per_second": successful_updates / duration if duration > 0 else 0,
                "final_leaderboard_size": final_stats.total_passengers if final_stats else 0,
                "final_total_bookings": final_stats.total_bookings if final_stats else 0,
                "simulation_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Simulation completed: {successful_updates} successful updates "
                       f"in {duration:.2f} seconds ({simulation_results['updates_per_second']:.2f} ops/sec)")
            
            return simulation_results
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return {
                "error": str(e),
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "simulation_timestamp": datetime.now().isoformat()
            }


# Convenience functions for common leaderboard operations

async def create_leaderboard_system(valkey_client: ValkeyClient, 
                                  leaderboard_name: str = "passenger_bookings") -> LeaderboardSystem:
    """
    Create and initialize a leaderboard system.
    
    Args:
        valkey_client: ValkeyClient instance
        leaderboard_name: Name for the leaderboard
        
    Returns:
        LeaderboardSystem: Initialized leaderboard system
    """
    system = LeaderboardSystem(valkey_client, leaderboard_name)
    logger.info(f"Created leaderboard system: {leaderboard_name}")
    return system


async def batch_update_leaderboard(leaderboard: LeaderboardSystem, 
                                 updates: List[Tuple[str, int, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Perform batch updates to leaderboard for better performance.
    
    Args:
        leaderboard: LeaderboardSystem instance
        updates: List of (passenger_id, score, passenger_info) tuples
        
    Returns:
        Dict[str, Any]: Batch update results
    """
    start_time = time.time()
    successful = 0
    failed = 0
    
    try:
        await leaderboard.valkey.ensure_connection()
        client = leaderboard.valkey.client
        
        # Use pipeline for batch operations
        pipe = client.pipeline()
        
        # Prepare batch updates
        score_updates = {}
        passenger_details = {}
        
        for passenger_id, score, passenger_info in updates:
            score_updates[passenger_id] = score
            if passenger_info:
                passenger_key = f"{leaderboard.passenger_details_key}:{passenger_id}"
                passenger_data = {
                    "passenger_id": passenger_id,
                    "name": passenger_info.get("name", "Unknown"),
                    "firstname": passenger_info.get("firstname", ""),
                    "lastname": passenger_info.get("lastname", ""),
                    "last_updated": datetime.now().isoformat()
                }
                passenger_details[passenger_key] = passenger_data
        
        # Add operations to pipeline
        if score_updates:
            pipe.zadd(leaderboard.leaderboard_key, score_updates)
        
        for passenger_key, passenger_data in passenger_details.items():
            pipe.hset(passenger_key, mapping=passenger_data)
            pipe.expire(passenger_key, 86400)
        
        # Execute batch
        results = pipe.execute()
        successful = len(updates)
        
        # Update statistics
        await leaderboard._update_stats_async()
        
    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        failed = len(updates)
    
    end_time = time.time()
    duration = end_time - start_time
    
    return {
        "total_updates": len(updates),
        "successful_updates": successful,
        "failed_updates": failed,
        "duration_seconds": duration,
        "updates_per_second": successful / duration if duration > 0 else 0,
        "timestamp": datetime.now().isoformat()
    }


class LeaderboardManager:
    """
    High-level manager for multiple leaderboards with advanced features.
    
    Provides centralized management of multiple leaderboards with
    cross-leaderboard operations and advanced analytics.
    """
    
    def __init__(self, valkey_client: ValkeyClient):
        """
        Initialize leaderboard manager.
        
        Args:
            valkey_client: ValkeyClient instance for cache operations
        """
        self.valkey = valkey_client
        self.leaderboards: Dict[str, LeaderboardSystem] = {}
        self.manager_key = "leaderboard_manager:registry"
        
        logger.info("Initialized leaderboard manager")
    
    async def create_leaderboard(self, name: str) -> LeaderboardSystem:
        """
        Create a new leaderboard.
        
        Args:
            name: Leaderboard name
            
        Returns:
            LeaderboardSystem: New leaderboard instance
        """
        if name in self.leaderboards:
            logger.warning(f"Leaderboard '{name}' already exists")
            return self.leaderboards[name]
        
        leaderboard = LeaderboardSystem(self.valkey, name)
        self.leaderboards[name] = leaderboard
        
        # Register in manager registry
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            registry_data = {
                "name": name,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            client.hset(f"{self.manager_key}:{name}", mapping=registry_data)
            
        except Exception as e:
            logger.warning(f"Failed to register leaderboard in manager: {e}")
        
        logger.info(f"Created leaderboard: {name}")
        return leaderboard
    
    async def get_leaderboard(self, name: str) -> Optional[LeaderboardSystem]:
        """
        Get existing leaderboard by name.
        
        Args:
            name: Leaderboard name
            
        Returns:
            Optional[LeaderboardSystem]: Leaderboard instance or None
        """
        if name in self.leaderboards:
            return self.leaderboards[name]
        
        # Try to load from registry
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            registry_entry = client.hgetall(f"{self.manager_key}:{name}")
            if registry_entry:
                leaderboard = LeaderboardSystem(self.valkey, name)
                self.leaderboards[name] = leaderboard
                return leaderboard
                
        except Exception as e:
            logger.warning(f"Failed to load leaderboard from registry: {e}")
        
        return None
    
    async def list_leaderboards(self) -> List[Dict[str, Any]]:
        """
        List all registered leaderboards.
        
        Returns:
            List[Dict[str, Any]]: List of leaderboard information
        """
        leaderboards = []
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get all registry keys
            registry_keys = client.keys(f"{self.manager_key}:*")
            
            for key in registry_keys:
                try:
                    registry_data = client.hgetall(key)
                    if registry_data:
                        # Decode bytes to strings
                        decoded_data = {k.decode(): v.decode() for k, v in registry_data.items()}
                        
                        # Add current statistics if leaderboard is loaded
                        name = decoded_data.get("name")
                        if name and name in self.leaderboards:
                            stats = await self.leaderboards[name].get_leaderboard_stats()
                            if stats:
                                decoded_data.update({
                                    "total_passengers": stats.total_passengers,
                                    "total_bookings": stats.total_bookings,
                                    "memory_usage_bytes": stats.memory_usage_bytes
                                })
                        
                        leaderboards.append(decoded_data)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse registry entry {key}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to list leaderboards: {e}")
        
        return leaderboards
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """
        Get statistics across all managed leaderboards.
        
        Returns:
            Dict[str, Any]: Global statistics
        """
        total_leaderboards = len(self.leaderboards)
        total_passengers = 0
        total_bookings = 0
        total_memory = 0
        
        leaderboard_details = []
        
        for name, leaderboard in self.leaderboards.items():
            try:
                stats = await leaderboard.get_leaderboard_stats()
                if stats:
                    total_passengers += stats.total_passengers
                    total_bookings += stats.total_bookings
                    total_memory += stats.memory_usage_bytes
                    
                    leaderboard_details.append({
                        "name": name,
                        "passengers": stats.total_passengers,
                        "bookings": stats.total_bookings,
                        "memory_bytes": stats.memory_usage_bytes
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to get stats for leaderboard {name}: {e}")
        
        return {
            "total_leaderboards": total_leaderboards,
            "total_passengers": total_passengers,
            "total_bookings": total_bookings,
            "total_memory_bytes": total_memory,
            "leaderboard_details": leaderboard_details,
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup_inactive_leaderboards(self, inactive_days: int = 30) -> Dict[str, Any]:
        """
        Clean up leaderboards that haven't been used recently.
        
        Args:
            inactive_days: Number of days to consider a leaderboard inactive
            
        Returns:
            Dict[str, Any]: Cleanup results
        """
        cutoff_date = datetime.now() - timedelta(days=inactive_days)
        cleaned_up = []
        errors = []
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Check all registered leaderboards
            registry_keys = client.keys(f"{self.manager_key}:*")
            
            for key in registry_keys:
                try:
                    registry_data = client.hgetall(key)
                    if not registry_data:
                        continue
                    
                    decoded_data = {k.decode(): v.decode() for k, v in registry_data.items()}
                    name = decoded_data.get("name")
                    created_at_str = decoded_data.get("created_at")
                    
                    if not name or not created_at_str:
                        continue
                    
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        if created_at < cutoff_date:
                            # Check if leaderboard has any recent activity
                            leaderboard_key = f"leaderboard:{name}"
                            if not client.exists(leaderboard_key):
                                # Remove from registry
                                client.delete(key)
                                if name in self.leaderboards:
                                    del self.leaderboards[name]
                                cleaned_up.append(name)
                                
                    except ValueError as e:
                        logger.warning(f"Invalid date format in registry for {name}: {e}")
                        
                except Exception as e:
                    logger.warning(f"Error processing registry entry {key}: {e}")
                    errors.append(str(e))
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive leaderboards: {e}")
            errors.append(str(e))
        
        return {
            "cleaned_up_leaderboards": cleaned_up,
            "cleanup_count": len(cleaned_up),
            "errors": errors,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.now().isoformat()
        }

@dataclass
class AirportTrafficEntry:
    """Airport traffic leaderboard entry with passenger flow statistics."""
    airport_code: str
    airport_name: str
    total_passengers: int
    inbound_passengers: int
    outbound_passengers: int
    rank: int
    last_updated: datetime


@dataclass
class PassengerMilesEntry:
    """Passenger miles leaderboard entry with flight distance statistics."""
    passenger_id: str
    passenger_name: str
    total_miles: int
    total_flights: int
    average_miles_per_flight: float
    rank: int
    last_updated: datetime


@dataclass
class PerformanceComparison:
    """Performance comparison between Valkey and RDBMS operations."""
    operation_type: str
    valkey_time_ms: float
    estimated_rdbms_time_ms: float
    performance_improvement: float
    data_points: int
    timestamp: datetime


class AirportTrafficLeaderboard:
    """
    Airport traffic leaderboard tracking passenger flow in/out of airports.
    
    Demonstrates high-performance aggregation using Valkey sorted sets
    compared to SQL SUM operations on RDBMS.
    """
    
    def __init__(self, valkey_client: ValkeyClient, leaderboard_name: str = "airport_traffic"):
        """
        Initialize airport traffic leaderboard.
        
        Args:
            valkey_client: ValkeyClient instance for cache operations
            leaderboard_name: Name of the leaderboard
        """
        self.valkey = valkey_client
        self.leaderboard_name = leaderboard_name
        self.total_traffic_key = f"leaderboard:{leaderboard_name}:total"
        self.inbound_traffic_key = f"leaderboard:{leaderboard_name}:inbound"
        self.outbound_traffic_key = f"leaderboard:{leaderboard_name}:outbound"
        self.airport_details_key = f"leaderboard:{leaderboard_name}:airports"
        self.performance_key = f"leaderboard:{leaderboard_name}:performance"
        
        logger.info(f"Initialized airport traffic leaderboard: {leaderboard_name}")
    
    async def update_airport_traffic(self, airport_code: str, inbound_count: int, 
                                   outbound_count: int, airport_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update airport traffic counts with atomic operations.
        
        This demonstrates the performance advantage of Valkey sorted sets
        over SQL SUM operations for real-time aggregations.
        
        Args:
            airport_code: Airport identifier (e.g., 'LAX', 'JFK')
            inbound_count: Number of inbound passengers
            outbound_count: Number of outbound passengers
            airport_info: Optional airport details (name, location, etc.)
            
        Returns:
            bool: True if update was successful
        """
        start_time = time.time()
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            total_passengers = inbound_count + outbound_count
            
            # Use pipeline for atomic operations
            pipe = client.pipeline()
            
            # Update all traffic metrics atomically
            pipe.zadd(self.total_traffic_key, {airport_code: total_passengers})
            pipe.zadd(self.inbound_traffic_key, {airport_code: inbound_count})
            pipe.zadd(self.outbound_traffic_key, {airport_code: outbound_count})
            
            # Store airport details if provided
            if airport_info:
                airport_key = f"{self.airport_details_key}:{airport_code}"
                airport_data = {
                    "airport_code": airport_code,
                    "name": airport_info.get("name", f"Airport {airport_code}"),
                    "city": airport_info.get("city", "Unknown"),
                    "country": airport_info.get("country", "Unknown"),
                    "last_updated": datetime.now().isoformat()
                }
                pipe.hset(airport_key, mapping=airport_data)
                pipe.expire(airport_key, 86400)  # 24 hour expiration
            
            # Execute pipeline
            results = pipe.execute()
            
            end_time = time.time()
            valkey_time_ms = (end_time - start_time) * 1000
            
            # Store performance metrics
            await self._record_performance_metric(
                "airport_traffic_update", 
                valkey_time_ms, 
                total_passengers
            )
            
            logger.debug(f"Updated airport {airport_code} traffic: {total_passengers} total passengers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update airport traffic: {e}")
            return False
    
    async def increment_airport_traffic(self, airport_code: str, inbound_increment: int = 0, 
                                      outbound_increment: int = 0, 
                                      airport_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, int]]:
        """
        Increment airport traffic counts atomically.
        
        Args:
            airport_code: Airport identifier
            inbound_increment: Inbound passenger increment
            outbound_increment: Outbound passenger increment
            airport_info: Optional airport details
            
        Returns:
            Optional[Dict[str, int]]: New traffic counts or None if failed
        """
        start_time = time.time()
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            total_increment = inbound_increment + outbound_increment
            
            # Use atomic increments
            new_total = client.zincrby(self.total_traffic_key, total_increment, airport_code)
            new_inbound = client.zincrby(self.inbound_traffic_key, inbound_increment, airport_code)
            new_outbound = client.zincrby(self.outbound_traffic_key, outbound_increment, airport_code)
            
            # Store airport details if provided
            if airport_info:
                airport_key = f"{self.airport_details_key}:{airport_code}"
                airport_data = {
                    "airport_code": airport_code,
                    "name": airport_info.get("name", f"Airport {airport_code}"),
                    "city": airport_info.get("city", "Unknown"),
                    "country": airport_info.get("country", "Unknown"),
                    "last_updated": datetime.now().isoformat()
                }
                client.hset(airport_key, mapping=airport_data)
                client.expire(airport_key, 86400)
            
            end_time = time.time()
            valkey_time_ms = (end_time - start_time) * 1000
            
            # Record performance
            await self._record_performance_metric(
                "airport_traffic_increment", 
                valkey_time_ms, 
                total_increment
            )
            
            result = {
                "total": int(new_total),
                "inbound": int(new_inbound),
                "outbound": int(new_outbound)
            }
            
            logger.debug(f"Incremented airport {airport_code} traffic: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to increment airport traffic: {e}")
            return None
    
    async def get_top_airports_by_traffic(self, limit: int = 10, offset: int = 0) -> List[AirportTrafficEntry]:
        """
        Get top airports by total passenger traffic.
        
        Demonstrates fast range queries using ZREVRANGE vs SQL ORDER BY + LIMIT.
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List[AirportTrafficEntry]: Top airports by traffic
        """
        start_time = time.time()
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get top airports with total traffic
            start = offset
            end = offset + limit - 1
            
            results = client.zrevrange(
                self.total_traffic_key, 
                start, 
                end, 
                withscores=True
            )
            
            if not results:
                return []
            
            entries = []
            for i, (airport_code, total_passengers) in enumerate(results):
                airport_code = airport_code.decode()
                
                # Get inbound/outbound breakdown
                inbound = client.zscore(self.inbound_traffic_key, airport_code) or 0
                outbound = client.zscore(self.outbound_traffic_key, airport_code) or 0
                
                # Get airport details
                airport_info = await self._get_airport_info(airport_code)
                
                entry = AirportTrafficEntry(
                    airport_code=airport_code,
                    airport_name=airport_info.get("name", f"Airport {airport_code}"),
                    total_passengers=int(total_passengers),
                    inbound_passengers=int(inbound),
                    outbound_passengers=int(outbound),
                    rank=start + i + 1,
                    last_updated=datetime.now()
                )
                entries.append(entry)
            
            end_time = time.time()
            valkey_time_ms = (end_time - start_time) * 1000
            
            # Record performance comparison
            await self._record_performance_metric(
                "top_airports_query", 
                valkey_time_ms, 
                len(entries)
            )
            
            logger.debug(f"Retrieved {len(entries)} top airports by traffic")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get top airports: {e}")
            return []
    
    async def get_airport_rank(self, airport_code: str) -> Optional[int]:
        """
        Get airport rank by total traffic.
        
        Args:
            airport_code: Airport identifier
            
        Returns:
            Optional[int]: Airport rank (1-based) or None if not found
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            rank = client.zrevrank(self.total_traffic_key, airport_code)
            return rank + 1 if rank is not None else None
            
        except Exception as e:
            logger.error(f"Failed to get airport rank: {e}")
            return None
    
    async def _get_airport_info(self, airport_code: str) -> Dict[str, Any]:
        """Get airport information from cache."""
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            airport_key = f"{self.airport_details_key}:{airport_code}"
            info = client.hgetall(airport_key)
            
            if not info:
                return {"name": f"Airport {airport_code}"}
            
            return {k.decode(): v.decode() for k, v in info.items()}
            
        except Exception as e:
            logger.warning(f"Failed to get airport info for {airport_code}: {e}")
            return {"name": f"Airport {airport_code}"}
    
    async def _record_performance_metric(self, operation_type: str, valkey_time_ms: float, data_points: int):
        """Record performance metrics for comparison with RDBMS."""
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Estimate equivalent RDBMS time (based on typical SQL aggregation performance)
            # This is a rough estimate for demonstration purposes
            estimated_rdbms_time_ms = self._estimate_rdbms_time(operation_type, data_points)
            
            performance_data = {
                "operation_type": operation_type,
                "valkey_time_ms": valkey_time_ms,
                "estimated_rdbms_time_ms": estimated_rdbms_time_ms,
                "performance_improvement": estimated_rdbms_time_ms / valkey_time_ms if valkey_time_ms > 0 else 0,
                "data_points": data_points,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in a list for performance tracking
            performance_key = f"{self.performance_key}:{operation_type}"
            client.lpush(performance_key, json.dumps(performance_data))
            client.ltrim(performance_key, 0, 99)  # Keep last 100 measurements
            client.expire(performance_key, 3600)  # 1 hour expiration
            
        except Exception as e:
            logger.warning(f"Failed to record performance metric: {e}")
    
    def _estimate_rdbms_time(self, operation_type: str, data_points: int) -> float:
        """
        Estimate equivalent RDBMS operation time.
        
        This provides rough estimates for demonstration purposes.
        Real-world performance would depend on database size, indexing, etc.
        """
        base_times = {
            "airport_traffic_update": 5.0,  # INSERT/UPDATE with aggregation
            "airport_traffic_increment": 8.0,  # UPDATE with SUM calculation
            "top_airports_query": 15.0,  # SELECT with ORDER BY and GROUP BY
        }
        
        base_time = base_times.get(operation_type, 10.0)
        
        # Scale with data points (logarithmic for queries, linear for updates)
        if "query" in operation_type:
            scaling_factor = 1 + (data_points / 100) * 0.5  # Logarithmic scaling
        else:
            scaling_factor = 1 + (data_points / 1000) * 2.0  # Linear scaling
        
        return base_time * scaling_factor


class PassengerMilesLeaderboard:
    """
    Passenger miles leaderboard tracking total flight distances.
    
    Demonstrates real-time distance aggregation using Valkey sorted sets
    vs SQL SUM operations on flight distances.
    """
    
    def __init__(self, valkey_client: ValkeyClient, leaderboard_name: str = "passenger_miles"):
        """
        Initialize passenger miles leaderboard.
        
        Args:
            valkey_client: ValkeyClient instance for cache operations
            leaderboard_name: Name of the leaderboard
        """
        self.valkey = valkey_client
        self.leaderboard_name = leaderboard_name
        self.total_miles_key = f"leaderboard:{leaderboard_name}:miles"
        self.flight_count_key = f"leaderboard:{leaderboard_name}:flights"
        self.passenger_details_key = f"leaderboard:{leaderboard_name}:passengers"
        self.performance_key = f"leaderboard:{leaderboard_name}:performance"
        
        logger.info(f"Initialized passenger miles leaderboard: {leaderboard_name}")
    
    async def add_flight_miles(self, passenger_id: str, miles: int, 
                             passenger_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, int]]:
        """
        Add flight miles to passenger's total with atomic operations.
        
        Demonstrates the performance advantage of Valkey increments
        over SQL SUM aggregations for real-time mile tracking.
        
        Args:
            passenger_id: Unique passenger identifier
            miles: Flight distance in miles
            passenger_info: Optional passenger details
            
        Returns:
            Optional[Dict[str, int]]: Updated totals or None if failed
        """
        start_time = time.time()
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Atomic increments for miles and flight count
            new_total_miles = client.zincrby(self.total_miles_key, miles, passenger_id)
            new_flight_count = client.zincrby(self.flight_count_key, 1, passenger_id)
            
            # Store passenger details if provided
            if passenger_info:
                passenger_key = f"{self.passenger_details_key}:{passenger_id}"
                passenger_data = {
                    "passenger_id": passenger_id,
                    "name": passenger_info.get("name", f"Passenger {passenger_id}"),
                    "firstname": passenger_info.get("firstname", ""),
                    "lastname": passenger_info.get("lastname", ""),
                    "last_updated": datetime.now().isoformat()
                }
                client.hset(passenger_key, mapping=passenger_data)
                client.expire(passenger_key, 86400)
            
            end_time = time.time()
            valkey_time_ms = (end_time - start_time) * 1000
            
            # Record performance
            await self._record_performance_metric(
                "add_flight_miles", 
                valkey_time_ms, 
                miles
            )
            
            result = {
                "total_miles": int(new_total_miles),
                "total_flights": int(new_flight_count)
            }
            
            logger.debug(f"Added {miles} miles to passenger {passenger_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add flight miles: {e}")
            return None
    
    async def get_top_passengers_by_miles(self, limit: int = 10, offset: int = 0) -> List[PassengerMilesEntry]:
        """
        Get top passengers by total miles flown.
        
        Demonstrates fast sorted set queries vs SQL aggregation with ORDER BY.
        
        Args:
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List[PassengerMilesEntry]: Top passengers by miles
        """
        start_time = time.time()
        
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Get top passengers by miles
            start = offset
            end = offset + limit - 1
            
            results = client.zrevrange(
                self.total_miles_key, 
                start, 
                end, 
                withscores=True
            )
            
            if not results:
                return []
            
            entries = []
            for i, (passenger_id, total_miles) in enumerate(results):
                passenger_id = passenger_id.decode()
                
                # Get flight count
                flight_count = client.zscore(self.flight_count_key, passenger_id) or 0
                
                # Calculate average miles per flight
                avg_miles = total_miles / flight_count if flight_count > 0 else 0
                
                # Get passenger details
                passenger_info = await self._get_passenger_info(passenger_id)
                
                entry = PassengerMilesEntry(
                    passenger_id=passenger_id,
                    passenger_name=passenger_info.get("name", f"Passenger {passenger_id}"),
                    total_miles=int(total_miles),
                    total_flights=int(flight_count),
                    average_miles_per_flight=round(avg_miles, 2),
                    rank=start + i + 1,
                    last_updated=datetime.now()
                )
                entries.append(entry)
            
            end_time = time.time()
            valkey_time_ms = (end_time - start_time) * 1000
            
            # Record performance
            await self._record_performance_metric(
                "top_passengers_by_miles_query", 
                valkey_time_ms, 
                len(entries)
            )
            
            logger.debug(f"Retrieved {len(entries)} top passengers by miles")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get top passengers by miles: {e}")
            return []
    
    async def get_passenger_miles_rank(self, passenger_id: str) -> Optional[int]:
        """
        Get passenger rank by total miles.
        
        Args:
            passenger_id: Unique passenger identifier
            
        Returns:
            Optional[int]: Passenger rank (1-based) or None if not found
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            rank = client.zrevrank(self.total_miles_key, passenger_id)
            return rank + 1 if rank is not None else None
            
        except Exception as e:
            logger.error(f"Failed to get passenger miles rank: {e}")
            return None
    
    async def get_passenger_miles_stats(self, passenger_id: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive miles statistics for a passenger.
        
        Args:
            passenger_id: Unique passenger identifier
            
        Returns:
            Optional[Dict[str, Any]]: Miles statistics or None if not found
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            total_miles = client.zscore(self.total_miles_key, passenger_id)
            flight_count = client.zscore(self.flight_count_key, passenger_id)
            
            if total_miles is None:
                return None
            
            total_miles = int(total_miles)
            flight_count = int(flight_count or 0)
            avg_miles = total_miles / flight_count if flight_count > 0 else 0
            rank = await self.get_passenger_miles_rank(passenger_id)
            
            passenger_info = await self._get_passenger_info(passenger_id)
            
            return {
                "passenger_id": passenger_id,
                "passenger_name": passenger_info.get("name", f"Passenger {passenger_id}"),
                "total_miles": total_miles,
                "total_flights": flight_count,
                "average_miles_per_flight": round(avg_miles, 2),
                "rank": rank,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get passenger miles stats: {e}")
            return None
    
    async def _get_passenger_info(self, passenger_id: str) -> Dict[str, Any]:
        """Get passenger information from cache."""
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            passenger_key = f"{self.passenger_details_key}:{passenger_id}"
            info = client.hgetall(passenger_key)
            
            if not info:
                return {"name": f"Passenger {passenger_id}"}
            
            decoded_info = {k.decode(): v.decode() for k, v in info.items()}
            
            # Format name
            firstname = decoded_info.get("firstname", "")
            lastname = decoded_info.get("lastname", "")
            if firstname and lastname:
                decoded_info["name"] = f"{firstname} {lastname}"
            elif firstname:
                decoded_info["name"] = firstname
            elif lastname:
                decoded_info["name"] = lastname
            else:
                decoded_info["name"] = f"Passenger {passenger_id}"
            
            return decoded_info
            
        except Exception as e:
            logger.warning(f"Failed to get passenger info for {passenger_id}: {e}")
            return {"name": f"Passenger {passenger_id}"}
    
    async def _record_performance_metric(self, operation_type: str, valkey_time_ms: float, data_points: int):
        """Record performance metrics for comparison with RDBMS."""
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Estimate equivalent RDBMS time
            estimated_rdbms_time_ms = self._estimate_rdbms_time(operation_type, data_points)
            
            performance_data = {
                "operation_type": operation_type,
                "valkey_time_ms": valkey_time_ms,
                "estimated_rdbms_time_ms": estimated_rdbms_time_ms,
                "performance_improvement": estimated_rdbms_time_ms / valkey_time_ms if valkey_time_ms > 0 else 0,
                "data_points": data_points,
                "timestamp": datetime.now().isoformat()
            }
            
            performance_key = f"{self.performance_key}:{operation_type}"
            client.lpush(performance_key, json.dumps(performance_data))
            client.ltrim(performance_key, 0, 99)
            client.expire(performance_key, 3600)
            
        except Exception as e:
            logger.warning(f"Failed to record performance metric: {e}")
    
    def _estimate_rdbms_time(self, operation_type: str, data_points: int) -> float:
        """Estimate equivalent RDBMS operation time."""
        base_times = {
            "add_flight_miles": 12.0,  # UPDATE with SUM calculation
            "top_passengers_by_miles_query": 25.0,  # Complex JOIN with GROUP BY and ORDER BY
        }
        
        base_time = base_times.get(operation_type, 15.0)
        
        # Scale with data complexity
        if "query" in operation_type:
            scaling_factor = 1 + (data_points / 50) * 0.8
        else:
            scaling_factor = 1 + (data_points / 1000) * 1.5
        
        return base_time * scaling_factor


class MultiLeaderboardManager:
    """
    Enhanced leaderboard manager supporting multiple leaderboard types.
    
    Manages passenger bookings, airport traffic, and passenger miles leaderboards
    with comprehensive performance monitoring and comparison features.
    """
    
    def __init__(self, valkey_client: ValkeyClient):
        """
        Initialize multi-leaderboard manager.
        
        Args:
            valkey_client: ValkeyClient instance for cache operations
        """
        self.valkey = valkey_client
        self.passenger_bookings = LeaderboardSystem(valkey_client, "passenger_bookings")
        self.airport_traffic = AirportTrafficLeaderboard(valkey_client, "airport_traffic")
        self.passenger_miles = PassengerMilesLeaderboard(valkey_client, "passenger_miles")
        
        logger.info("Initialized multi-leaderboard manager")
    
    async def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report across all leaderboards.
        
        Returns:
            Dict[str, Any]: Performance comparison report
        """
        try:
            await self.valkey.ensure_connection()
            client = self.valkey.client
            
            # Collect performance data from all leaderboards
            performance_keys = client.keys("leaderboard:*:performance:*")
            
            all_metrics = []
            operation_summaries = {}
            
            for key in performance_keys:
                try:
                    metrics_list = client.lrange(key, 0, -1)
                    for metric_json in metrics_list:
                        metric = json.loads(metric_json.decode())
                        all_metrics.append(metric)
                        
                        op_type = metric["operation_type"]
                        if op_type not in operation_summaries:
                            operation_summaries[op_type] = {
                                "count": 0,
                                "total_valkey_time": 0,
                                "total_estimated_rdbms_time": 0,
                                "avg_improvement": 0
                            }
                        
                        summary = operation_summaries[op_type]
                        summary["count"] += 1
                        summary["total_valkey_time"] += metric["valkey_time_ms"]
                        summary["total_estimated_rdbms_time"] += metric["estimated_rdbms_time_ms"]
                        
                except Exception as e:
                    logger.warning(f"Failed to parse performance metric from {key}: {e}")
            
            # Calculate averages and improvements
            for op_type, summary in operation_summaries.items():
                if summary["count"] > 0:
                    avg_valkey = summary["total_valkey_time"] / summary["count"]
                    avg_rdbms = summary["total_estimated_rdbms_time"] / summary["count"]
                    summary["avg_valkey_time_ms"] = round(avg_valkey, 2)
                    summary["avg_estimated_rdbms_time_ms"] = round(avg_rdbms, 2)
                    summary["avg_improvement"] = round(avg_rdbms / avg_valkey, 2) if avg_valkey > 0 else 0
            
            # Get current leaderboard stats
            booking_stats = await self.passenger_bookings.get_leaderboard_stats()
            
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "total_operations_measured": len(all_metrics),
                "operation_summaries": operation_summaries,
                "leaderboard_stats": {
                    "passenger_bookings": {
                        "total_passengers": booking_stats.total_passengers if booking_stats else 0,
                        "total_bookings": booking_stats.total_bookings if booking_stats else 0
                    }
                },
                "overall_performance": {
                    "avg_valkey_time_ms": round(
                        sum(m["valkey_time_ms"] for m in all_metrics) / len(all_metrics), 2
                    ) if all_metrics else 0,
                    "avg_estimated_rdbms_time_ms": round(
                        sum(m["estimated_rdbms_time_ms"] for m in all_metrics) / len(all_metrics), 2
                    ) if all_metrics else 0,
                    "overall_improvement_factor": round(
                        sum(m["performance_improvement"] for m in all_metrics) / len(all_metrics), 2
                    ) if all_metrics else 0
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def simulate_mixed_workload(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Simulate mixed workload across all leaderboard types.
        
        Args:
            duration_seconds: Duration of simulation
            
        Returns:
            Dict[str, Any]: Simulation results and performance metrics
        """
        start_time = time.time()
        operations_performed = {
            "passenger_bookings": 0,
            "airport_traffic": 0,
            "passenger_miles": 0
        }
        
        logger.info(f"Starting mixed workload simulation for {duration_seconds} seconds")
        
        try:
            # Simulate concurrent operations
            while time.time() - start_time < duration_seconds:
                # Passenger booking update
                passenger_id = f"sim_passenger_{operations_performed['passenger_bookings'] % 100}"
                await self.passenger_bookings.increment_passenger_score(
                    passenger_id, 
                    1, 
                    {"name": f"Sim Passenger {operations_performed['passenger_bookings'] % 100}"}
                )
                operations_performed["passenger_bookings"] += 1
                
                # Airport traffic update
                airport_code = f"SIM{operations_performed['airport_traffic'] % 10:02d}"
                await self.airport_traffic.increment_airport_traffic(
                    airport_code, 
                    inbound_increment=1, 
                    outbound_increment=1,
                    airport_info={"name": f"Simulation Airport {airport_code}"}
                )
                operations_performed["airport_traffic"] += 1
                
                # Passenger miles update
                miles_passenger_id = f"miles_passenger_{operations_performed['passenger_miles'] % 50}"
                await self.passenger_miles.add_flight_miles(
                    miles_passenger_id, 
                    500 + (operations_performed['passenger_miles'] % 1000),
                    {"name": f"Miles Passenger {operations_performed['passenger_miles'] % 50}"}
                )
                operations_performed["passenger_miles"] += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            actual_duration = end_time - start_time
            
            # Get final performance report
            performance_report = await self.get_comprehensive_performance_report()
            
            simulation_results = {
                "simulation_duration_seconds": actual_duration,
                "operations_performed": operations_performed,
                "total_operations": sum(operations_performed.values()),
                "operations_per_second": sum(operations_performed.values()) / actual_duration,
                "performance_report": performance_report,
                "simulation_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Mixed workload simulation completed: {simulation_results['total_operations']} "
                       f"operations in {actual_duration:.2f} seconds "
                       f"({simulation_results['operations_per_second']:.2f} ops/sec)")
            
            return simulation_results
            
        except Exception as e:
            logger.error(f"Mixed workload simulation failed: {e}")
            return {
                "error": str(e),
                "operations_performed": operations_performed,
                "simulation_timestamp": datetime.now().isoformat()
            }