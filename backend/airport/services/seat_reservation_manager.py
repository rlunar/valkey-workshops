"""
Seat reservation manager using Valkey bitmaps and distributed locking.

This module implements the seat reservation system for Use Case 2, demonstrating:
- Bitmap-based seat availability tracking using SETBIT/GETBIT operations
- Distributed locking for atomic seat reservations with 60-second TTL
- Concurrent user simulation and race condition prevention
- Bulk operations for seat availability queries and statistics
"""

import asyncio
import logging
import time
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from ..cache.manager import CacheManager
from ..cache.utils import key_manager
from ..services.lock_manager import DistributedLockManager
from ..models.seat import SeatModel, SeatReservationModel, FlightSeatMapModel
from ..models.enums import SeatStatus, SeatClass
from ..models.simulation import ConcurrentBookingSimulationModel, UserSimulationModel

logger = logging.getLogger(__name__)


@dataclass
class AircraftLayout:
    """Aircraft seating layout configuration."""
    aircraft_type: str
    total_seats: int
    rows: int
    seats_per_row: int
    seat_classes: Dict[str, SeatClass]  # seat_code -> class mapping
    
    @classmethod
    def get_boeing_737_layout(cls) -> 'AircraftLayout':
        """Standard Boeing 737-800 layout (189 seats)."""
        seat_classes = {}
        
        # First class: rows 1-3 (A, B, C, D, E, F) = 18 seats
        for row in range(1, 4):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.FIRST
        
        # Business class: rows 4-6 (A, B, C, D, E, F) = 18 seats  
        for row in range(4, 7):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.BUSINESS
        
        # Premium economy: rows 7-10 (A, B, C, D, E, F) = 24 seats
        for row in range(7, 11):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.PREMIUM_ECONOMY
        
        # Economy: rows 11-32 (A, B, C, D, E, F) = 132 seats
        for row in range(11, 33):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.ECONOMY
        
        return cls(
            aircraft_type="Boeing 737-800",
            total_seats=189,
            rows=32,
            seats_per_row=6,
            seat_classes=seat_classes
        )
    
    @classmethod
    def get_airbus_a320_layout(cls) -> 'AircraftLayout':
        """Standard Airbus A320 layout (180 seats)."""
        seat_classes = {}
        
        # Business class: rows 1-4 (A, B, C, D, E, F) = 24 seats
        for row in range(1, 5):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.BUSINESS
        
        # Premium economy: rows 5-8 (A, B, C, D, E, F) = 24 seats
        for row in range(5, 9):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.PREMIUM_ECONOMY
        
        # Economy: rows 9-30 (A, B, C, D, E, F) = 132 seats
        for row in range(9, 31):
            for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                seat_classes[f"{row}{seat_letter}"] = SeatClass.ECONOMY
        
        return cls(
            aircraft_type="Airbus A320",
            total_seats=180,
            rows=30,
            seats_per_row=6,
            seat_classes=seat_classes
        )


class SeatReservationManager:
    """
    Seat reservation manager using Valkey bitmaps and distributed locking.
    
    Features:
    - Bitmap-based seat availability tracking (SETBIT/GETBIT operations)
    - Distributed locking for atomic seat reservations (60-second TTL)
    - Configurable aircraft layouts (Boeing 737, Airbus A320)
    - Bulk operations for seat availability queries and statistics
    - Automatic reservation expiration and cleanup
    """
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize seat reservation manager.
        
        Args:
            cache_manager: CacheManager instance for bitmap operations
        """
        self.cache = cache_manager
        self.lock_manager = DistributedLockManager(cache_manager)
        
        # Reservation configuration
        self.reservation_ttl = 60  # 1 minute reservation timeout
        self.lock_timeout = 60     # 1 minute lock timeout
        self.cleanup_interval = 30 # 30 seconds between cleanup runs
        
        # Aircraft layouts
        self.aircraft_layouts = {
            "boeing_737": AircraftLayout.get_boeing_737_layout(),
            "airbus_a320": AircraftLayout.get_airbus_a320_layout()
        }
        
        logger.info("SeatReservationManager initialized")
    
    async def create_flight_seating(
        self, 
        flight_id: str, 
        aircraft_type: str = "boeing_737",
        blocked_seats: Optional[List[int]] = None
    ) -> FlightSeatMapModel:
        """
        Initialize flight seating with configurable aircraft layout.
        
        Args:
            flight_id: Flight identifier
            aircraft_type: Aircraft layout type ("boeing_737" or "airbus_a320")
            blocked_seats: List of seat numbers to mark as blocked
            
        Returns:
            FlightSeatMapModel: Complete seat map information
        """
        if aircraft_type not in self.aircraft_layouts:
            raise ValueError(f"Unknown aircraft type: {aircraft_type}")
        
        layout = self.aircraft_layouts[aircraft_type]
        blocked_seats = blocked_seats or []
        
        # Initialize bitmap for seat availability (0 = available, 1 = occupied/reserved)
        bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
        
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Clear existing bitmap
            self.cache.client.client.delete(bitmap_key)
            
            # Set blocked seats in bitmap
            for seat_num in blocked_seats:
                if 1 <= seat_num <= layout.total_seats:
                    self.cache.client.client.setbit(bitmap_key, seat_num - 1, 1)  # 0-based indexing
            
            # Create detailed seat information
            seats = []
            seat_number = 1
            
            for row in range(1, layout.rows + 1):
                for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                    if seat_number <= layout.total_seats:
                        seat_code = f"{row}{seat_letter}"
                        seat_class = layout.seat_classes.get(seat_code, SeatClass.ECONOMY)
                        
                        status = SeatStatus.BLOCKED if seat_number in blocked_seats else SeatStatus.AVAILABLE
                        
                        seat = SeatModel(
                            seat_number=seat_number,
                            seat_code=seat_code,
                            seat_class=seat_class,
                            status=status
                        )
                        seats.append(seat)
                        seat_number += 1
            
            # Calculate seat statistics
            available_seats = layout.total_seats - len(blocked_seats)
            reserved_seats = 0
            booked_seats = 0
            
            # Create seat map model
            seat_map = FlightSeatMapModel(
                flight_id=flight_id,
                aircraft_type=layout.aircraft_type,
                total_seats=layout.total_seats,
                available_seats=available_seats,
                reserved_seats=reserved_seats,
                booked_seats=booked_seats,
                seat_bitmap=self._get_bitmap_as_base64(bitmap_key),
                seats=seats
            )
            
            # Store seat map metadata in cache
            metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
            await self.cache.set(metadata_key, seat_map.model_dump(), ttl=3600)  # 1 hour TTL
            
            logger.info(f"Created flight seating for {flight_id}: {layout.aircraft_type} "
                       f"({layout.total_seats} seats, {len(blocked_seats)} blocked)")
            
            return seat_map
            
        except Exception as e:
            logger.error(f"Error creating flight seating for {flight_id}: {e}")
            raise
    
    async def get_seat_availability(self, flight_id: str, seat_number: int) -> bool:
        """
        Check if a specific seat is available using GETBIT operation.
        
        Args:
            flight_id: Flight identifier
            seat_number: Seat number (1-based)
            
        Returns:
            bool: True if seat is available, False if occupied/reserved
        """
        bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
        
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Get bit value (0 = available, 1 = occupied/reserved)
            bit_value = self.cache.client.client.getbit(bitmap_key, seat_number - 1)  # 0-based indexing
            return bit_value == 0
            
        except Exception as e:
            logger.error(f"Error checking seat availability for {flight_id}, seat {seat_number}: {e}")
            return False
    
    async def get_bulk_seat_availability(
        self, 
        flight_id: str, 
        seat_numbers: List[int]
    ) -> Dict[int, bool]:
        """
        Check availability for multiple seats efficiently.
        
        Args:
            flight_id: Flight identifier
            seat_numbers: List of seat numbers to check
            
        Returns:
            Dict[int, bool]: Mapping of seat number to availability
        """
        bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
        availability = {}
        
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Use pipeline for efficient bulk operations
            pipe = self.cache.client.client.pipeline()
            
            for seat_num in seat_numbers:
                pipe.getbit(bitmap_key, seat_num - 1)  # 0-based indexing
            
            results = pipe.execute()
            
            for seat_num, bit_value in zip(seat_numbers, results):
                availability[seat_num] = (bit_value == 0)
            
            return availability
            
        except Exception as e:
            logger.error(f"Error checking bulk seat availability for {flight_id}: {e}")
            return {seat_num: False for seat_num in seat_numbers}
    
    async def get_seat_statistics(self, flight_id: str) -> Dict[str, int]:
        """
        Get seat availability statistics using bitmap operations.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            Dict[str, int]: Statistics including total, available, occupied seats
        """
        bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
        metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
        
        try:
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Get total seats from metadata
            metadata = await self.cache.get(metadata_key)
            if not metadata:
                logger.warning(f"No seat metadata found for flight {flight_id}")
                return {"error": "Flight not found"}
            
            total_seats = metadata.get("total_seats", 0)
            
            # Count occupied seats using BITCOUNT
            occupied_count = self.cache.client.client.bitcount(bitmap_key)
            available_count = total_seats - occupied_count
            
            # Get reservation counts from separate tracking
            reservations_key = key_manager.key_builder.build_key("seat_reservations", flight_id)
            reservations_data = await self.cache.get(reservations_key) or {}
            
            active_reservations = 0
            confirmed_bookings = 0
            
            current_time = datetime.now()
            for reservation_data in reservations_data.values():
                if isinstance(reservation_data, dict):
                    expires_at = datetime.fromisoformat(reservation_data.get("expires_at", ""))
                    if current_time < expires_at:
                        if reservation_data.get("is_confirmed", False):
                            confirmed_bookings += 1
                        else:
                            active_reservations += 1
            
            return {
                "total_seats": total_seats,
                "available_seats": available_count,
                "occupied_seats": occupied_count,
                "active_reservations": active_reservations,
                "confirmed_bookings": confirmed_bookings,
                "utilization_percentage": round((occupied_count / total_seats) * 100, 2) if total_seats > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting seat statistics for {flight_id}: {e}")
            return {"error": str(e)}
    
    async def get_available_seats_by_class(
        self, 
        flight_id: str, 
        seat_class: Optional[SeatClass] = None
    ) -> List[SeatModel]:
        """
        Get available seats filtered by class.
        
        Args:
            flight_id: Flight identifier
            seat_class: Optional seat class filter
            
        Returns:
            List[SeatModel]: Available seats matching criteria
        """
        metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
        
        try:
            metadata = await self.cache.get(metadata_key)
            if not metadata:
                return []
            
            all_seats = [SeatModel(**seat_data) for seat_data in metadata.get("seats", [])]
            available_seats = []
            
            # Get current availability for all seats
            seat_numbers = [seat.seat_number for seat in all_seats]
            availability = await self.get_bulk_seat_availability(flight_id, seat_numbers)
            
            for seat in all_seats:
                if availability.get(seat.seat_number, False):  # Available
                    if seat_class is None or seat.seat_class == seat_class:
                        available_seats.append(seat)
            
            return available_seats
            
        except Exception as e:
            logger.error(f"Error getting available seats by class for {flight_id}: {e}")
            return []
    
    def _get_bitmap_as_base64(self, bitmap_key: str) -> str:
        """
        Get bitmap data as base64 encoded string.
        
        Args:
            bitmap_key: Valkey key for the bitmap
            
        Returns:
            str: Base64 encoded bitmap data
        """
        try:
            bitmap_data = self.cache.client.client.get(bitmap_key)
            if bitmap_data:
                return base64.b64encode(bitmap_data).decode('utf-8')
            return ""
        except Exception as e:
            logger.warning(f"Error getting bitmap data: {e}")
            return ""
    
    async def get_seat_map(self, flight_id: str) -> Optional[FlightSeatMapModel]:
        """
        Get complete seat map with current availability status.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            FlightSeatMapModel: Complete seat map or None if not found
        """
        metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
        
        try:
            metadata = await self.cache.get(metadata_key)
            if not metadata:
                return None
            
            # Update seat map with current statistics
            stats = await self.get_seat_statistics(flight_id)
            
            metadata.update({
                "available_seats": stats.get("available_seats", 0),
                "reserved_seats": stats.get("active_reservations", 0),
                "booked_seats": stats.get("confirmed_bookings", 0),
                "last_updated": datetime.now()
            })
            
            return FlightSeatMapModel(**metadata)
            
        except Exception as e:
            logger.error(f"Error getting seat map for {flight_id}: {e}")
            return None
    
    async def reserve_seat(
        self, 
        flight_id: str, 
        seat_number: int, 
        user_id: str,
        timeout_seconds: float = 5.0
    ) -> Optional[SeatReservationModel]:
        """
        Reserve a seat with distributed locking (60-second TTL).
        
        Uses atomic SET NX EX operations for distributed locking to prevent
        race conditions during seat reservation process.
        
        Args:
            flight_id: Flight identifier
            seat_number: Seat number to reserve (1-based)
            user_id: User making the reservation
            timeout_seconds: Maximum time to wait for lock acquisition
            
        Returns:
            SeatReservationModel: Reservation details if successful, None if failed
        """
        # Check if seat is available first
        if not await self.get_seat_availability(flight_id, seat_number):
            logger.info(f"Seat {seat_number} on flight {flight_id} is not available")
            return None
        
        # Create lock key for this specific seat
        seat_lock_key = f"seat_lock:{flight_id}:{seat_number}"
        
        try:
            # Acquire distributed lock for seat reservation
            async with self.lock_manager.lock_context(
                seat_lock_key, 
                ttl_seconds=self.lock_timeout,
                timeout_seconds=timeout_seconds
            ) as lock:
                
                if not lock:
                    logger.info(f"Failed to acquire lock for seat {seat_number} on flight {flight_id}")
                    return None
                
                # Double-check availability while holding lock
                if not await self.get_seat_availability(flight_id, seat_number):
                    logger.info(f"Seat {seat_number} became unavailable while acquiring lock")
                    return None
                
                # Mark seat as reserved in bitmap
                bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
                
                if not self.cache.client:
                    await self.cache.initialize()
                
                await self.cache.client.ensure_connection()
                
                # Set bit to 1 (occupied/reserved)
                self.cache.client.client.setbit(bitmap_key, seat_number - 1, 1)
                
                # Create reservation record
                reservation_id = str(uuid.uuid4())
                reserved_at = datetime.now()
                expires_at = reserved_at + timedelta(seconds=self.reservation_ttl)
                
                reservation = SeatReservationModel(
                    flight_id=flight_id,
                    seat_number=seat_number,
                    user_id=user_id,
                    reservation_id=reservation_id,
                    reserved_at=reserved_at,
                    expires_at=expires_at,
                    lock_key=lock.lock_key,
                    is_confirmed=False
                )
                
                # Store reservation in cache with TTL
                reservations_key = key_manager.key_builder.build_key("seat_reservations", flight_id)
                reservations_data = await self.cache.get(reservations_key) or {}
                
                reservations_data[f"{seat_number}:{user_id}"] = reservation.model_dump()
                
                await self.cache.set(
                    reservations_key, 
                    reservations_data, 
                    ttl=self.reservation_ttl + 60  # Extra buffer for cleanup
                )
                
                # Set individual reservation key with TTL for automatic expiration
                reservation_key = key_manager.key_builder.build_key(
                    "reservation", f"{flight_id}:{seat_number}:{user_id}"
                )
                await self.cache.set(
                    reservation_key, 
                    reservation.model_dump(), 
                    ttl=self.reservation_ttl
                )
                
                logger.info(f"Reserved seat {seat_number} on flight {flight_id} for user {user_id} "
                           f"(expires at {expires_at})")
                
                return reservation
                
        except Exception as e:
            logger.error(f"Error reserving seat {seat_number} on flight {flight_id}: {e}")
            return None
    
    async def confirm_reservation(
        self, 
        flight_id: str, 
        seat_number: int, 
        user_id: str,
        booking_id: Optional[int] = None
    ) -> bool:
        """
        Confirm a seat reservation and convert it to a booking.
        
        Args:
            flight_id: Flight identifier
            seat_number: Seat number to confirm
            user_id: User confirming the reservation
            booking_id: Optional booking ID for tracking
            
        Returns:
            bool: True if confirmation successful, False otherwise
        """
        reservation_key = key_manager.key_builder.build_key(
            "reservation", f"{flight_id}:{seat_number}:{user_id}"
        )
        
        try:
            # Get reservation details
            reservation_data = await self.cache.get(reservation_key)
            if not reservation_data:
                logger.warning(f"No reservation found for seat {seat_number} on flight {flight_id} by user {user_id}")
                return False
            
            reservation = SeatReservationModel(**reservation_data)
            
            # Check if reservation has expired
            if datetime.now() > reservation.expires_at:
                logger.warning(f"Reservation expired for seat {seat_number} on flight {flight_id}")
                await self._release_expired_reservation(flight_id, seat_number, user_id)
                return False
            
            # Update reservation to confirmed status
            reservation.is_confirmed = True
            
            # Update in reservations collection
            reservations_key = key_manager.key_builder.build_key("seat_reservations", flight_id)
            reservations_data = await self.cache.get(reservations_key) or {}
            
            reservation_entry_key = f"{seat_number}:{user_id}"
            if reservation_entry_key in reservations_data:
                reservations_data[reservation_entry_key] = reservation.model_dump()
                
                # Store with longer TTL for confirmed bookings
                await self.cache.set(reservations_key, reservations_data, ttl=86400)  # 24 hours
            
            # Update individual reservation key
            await self.cache.set(reservation_key, reservation.model_dump(), ttl=86400)  # 24 hours
            
            # Update seat metadata if booking_id provided
            if booking_id:
                metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
                metadata = await self.cache.get(metadata_key)
                
                if metadata and "seats" in metadata:
                    for seat_data in metadata["seats"]:
                        if seat_data.get("seat_number") == seat_number:
                            seat_data["status"] = SeatStatus.BOOKED.value
                            seat_data["booking_id"] = booking_id
                            break
                    
                    await self.cache.set(metadata_key, metadata, ttl=3600)
            
            logger.info(f"Confirmed reservation for seat {seat_number} on flight {flight_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error confirming reservation for seat {seat_number} on flight {flight_id}: {e}")
            return False
    
    async def release_reservation(
        self, 
        flight_id: str, 
        seat_number: int, 
        user_id: str
    ) -> bool:
        """
        Manually release a seat reservation.
        
        Args:
            flight_id: Flight identifier
            seat_number: Seat number to release
            user_id: User releasing the reservation
            
        Returns:
            bool: True if release successful, False otherwise
        """
        return await self._release_expired_reservation(flight_id, seat_number, user_id)
    
    async def _release_expired_reservation(
        self, 
        flight_id: str, 
        seat_number: int, 
        user_id: str
    ) -> bool:
        """
        Internal method to release expired or cancelled reservations.
        
        Args:
            flight_id: Flight identifier
            seat_number: Seat number to release
            user_id: User who made the reservation
            
        Returns:
            bool: True if release successful, False otherwise
        """
        try:
            # Mark seat as available in bitmap
            bitmap_key = key_manager.key_builder.build_key("seat_bitmap", flight_id)
            
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Set bit to 0 (available)
            self.cache.client.client.setbit(bitmap_key, seat_number - 1, 0)
            
            # Remove from reservations collection
            reservations_key = key_manager.key_builder.build_key("seat_reservations", flight_id)
            reservations_data = await self.cache.get(reservations_key) or {}
            
            reservation_entry_key = f"{seat_number}:{user_id}"
            if reservation_entry_key in reservations_data:
                del reservations_data[reservation_entry_key]
                await self.cache.set(reservations_key, reservations_data, ttl=3600)
            
            # Remove individual reservation key
            reservation_key = key_manager.key_builder.build_key(
                "reservation", f"{flight_id}:{seat_number}:{user_id}"
            )
            await self.cache.delete(reservation_key)
            
            # Update seat metadata
            metadata_key = key_manager.key_builder.build_key("seat_metadata", flight_id)
            metadata = await self.cache.get(metadata_key)
            
            if metadata and "seats" in metadata:
                for seat_data in metadata["seats"]:
                    if seat_data.get("seat_number") == seat_number:
                        seat_data["status"] = SeatStatus.AVAILABLE.value
                        seat_data["reserved_by"] = None
                        seat_data["reserved_at"] = None
                        seat_data["booking_id"] = None
                        break
                
                await self.cache.set(metadata_key, metadata, ttl=3600)
            
            logger.info(f"Released reservation for seat {seat_number} on flight {flight_id} by user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing reservation for seat {seat_number} on flight {flight_id}: {e}")
            return False
    
    async def release_expired_reservations(self, flight_id: str) -> List[int]:
        """
        Clean up expired reservations for a flight.
        
        Args:
            flight_id: Flight identifier
            
        Returns:
            List[int]: List of seat numbers that were released
        """
        reservations_key = key_manager.key_builder.build_key("seat_reservations", flight_id)
        released_seats = []
        
        try:
            reservations_data = await self.cache.get(reservations_key) or {}
            current_time = datetime.now()
            
            expired_keys = []
            
            for reservation_key, reservation_data in reservations_data.items():
                if isinstance(reservation_data, dict):
                    expires_at_str = reservation_data.get("expires_at")
                    is_confirmed = reservation_data.get("is_confirmed", False)
                    
                    if expires_at_str and not is_confirmed:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        
                        if current_time > expires_at:
                            # Reservation has expired
                            seat_number = reservation_data.get("seat_number")
                            user_id = reservation_data.get("user_id")
                            
                            if seat_number and user_id:
                                if await self._release_expired_reservation(flight_id, seat_number, user_id):
                                    released_seats.append(seat_number)
                                    expired_keys.append(reservation_key)
            
            # Update reservations data
            for key in expired_keys:
                if key in reservations_data:
                    del reservations_data[key]
            
            if expired_keys:
                await self.cache.set(reservations_key, reservations_data, ttl=3600)
                logger.info(f"Released {len(released_seats)} expired reservations for flight {flight_id}")
            
            return released_seats
            
        except Exception as e:
            logger.error(f"Error releasing expired reservations for flight {flight_id}: {e}")
            return []
    
    async def get_user_reservations(self, user_id: str) -> List[SeatReservationModel]:
        """
        Get all active reservations for a user across all flights.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[SeatReservationModel]: List of active reservations
        """
        # This would require scanning all flight reservations
        # For demo purposes, we'll implement a simple version
        # In production, you'd want to maintain a user-to-reservations index
        
        user_reservations = []
        
        try:
            # Get all reservation keys (this is a simplified approach)
            # In production, maintain separate user reservation tracking
            pattern = key_manager.key_builder.build_key("reservation", f"*:*:{user_id}")
            
            if not self.cache.client:
                await self.cache.initialize()
            
            await self.cache.client.ensure_connection()
            
            # Scan for user's reservation keys
            reservation_keys = []
            cursor = 0
            
            while True:
                cursor, keys = self.cache.client.client.scan(cursor, match=pattern, count=100)
                reservation_keys.extend(keys)
                if cursor == 0:
                    break
            
            # Get reservation data for each key
            if reservation_keys:
                pipe = self.cache.client.client.pipeline()
                for key in reservation_keys:
                    pipe.get(key)
                
                results = pipe.execute()
                
                for key, data in zip(reservation_keys, results):
                    if data:
                        try:
                            reservation_data = self.cache._deserialize_value(data)
                            if isinstance(reservation_data, dict):
                                reservation = SeatReservationModel(**reservation_data)
                                
                                # Check if reservation is still valid
                                if datetime.now() <= reservation.expires_at or reservation.is_confirmed:
                                    user_reservations.append(reservation)
                        except Exception as e:
                            logger.warning(f"Error parsing reservation data from key {key}: {e}")
            
            return user_reservations
            
        except Exception as e:
            logger.error(f"Error getting user reservations for {user_id}: {e}")
            return []
    
    async def detect_lock_contention(
        self, 
        flight_id: str, 
        seat_numbers: List[int],
        num_concurrent_users: int = 5
    ) -> Dict[str, Any]:
        """
        Detect and measure lock contention for specific seats.
        
        Args:
            flight_id: Flight identifier
            seat_numbers: List of seat numbers to test
            num_concurrent_users: Number of concurrent users to simulate
            
        Returns:
            Dict[str, Any]: Lock contention metrics and results
        """
        contention_results = {
            "flight_id": flight_id,
            "tested_seats": seat_numbers,
            "concurrent_users": num_concurrent_users,
            "contention_events": 0,
            "successful_acquisitions": 0,
            "failed_acquisitions": 0,
            "average_wait_time_ms": 0.0,
            "seat_results": {}
        }
        
        async def attempt_seat_lock(seat_number: int, user_id: str) -> Dict[str, Any]:
            """Attempt to acquire lock for a specific seat."""
            start_time = time.time()
            seat_lock_key = f"seat_lock:{flight_id}:{seat_number}"
            
            lock = await self.lock_manager.acquire_lock(
                seat_lock_key,
                ttl_seconds=5,  # Short TTL for testing
                timeout_seconds=2.0
            )
            
            wait_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "user_id": user_id,
                "seat_number": seat_number,
                "lock_acquired": lock is not None,
                "wait_time_ms": wait_time_ms,
                "lock_key": lock.lock_key if lock else None
            }
            
            # Release lock immediately for testing
            if lock:
                await self.lock_manager.release_lock(lock)
            
            return result
        
        try:
            for seat_number in seat_numbers:
                seat_results = []
                
                # Create concurrent lock attempts for this seat
                tasks = []
                for i in range(num_concurrent_users):
                    user_id = f"test_user_{i}"
                    task = attempt_seat_lock(seat_number, user_id)
                    tasks.append(task)
                
                # Execute concurrent attempts
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful = 0
                failed = 0
                total_wait_time = 0.0
                contention_events = 0
                
                for result in results:
                    if isinstance(result, dict):
                        seat_results.append(result)
                        
                        if result["lock_acquired"]:
                            successful += 1
                        else:
                            failed += 1
                            contention_events += 1
                        
                        total_wait_time += result["wait_time_ms"]
                
                contention_results["seat_results"][seat_number] = {
                    "successful_acquisitions": successful,
                    "failed_acquisitions": failed,
                    "contention_events": contention_events,
                    "average_wait_time_ms": total_wait_time / len(results) if results else 0.0,
                    "attempts": seat_results
                }
                
                # Update overall metrics
                contention_results["successful_acquisitions"] += successful
                contention_results["failed_acquisitions"] += failed
                contention_results["contention_events"] += contention_events
            
            # Calculate overall averages
            total_attempts = contention_results["successful_acquisitions"] + contention_results["failed_acquisitions"]
            if total_attempts > 0:
                total_wait_time = sum(
                    seat_data["average_wait_time_ms"] * len(seat_data["attempts"])
                    for seat_data in contention_results["seat_results"].values()
                )
                contention_results["average_wait_time_ms"] = total_wait_time / total_attempts
            
            logger.info(f"Lock contention test completed for flight {flight_id}: "
                       f"{contention_results['contention_events']} contention events detected")
            
            return contention_results
            
        except Exception as e:
            logger.error(f"Error detecting lock contention for flight {flight_id}: {e}")
            contention_results["error"] = str(e)
            return contention_results