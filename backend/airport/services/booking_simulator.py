"""
Concurrent booking simulator for race condition demonstration.

This module implements multi-user seat booking simulations to demonstrate:
- Race condition detection and prevention
- Distributed locking effectiveness
- Performance metrics for lock contention and booking success rates
- Configurable concurrency levels and booking patterns
"""

import asyncio
import logging
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from ..services.seat_reservation_manager import SeatReservationManager
from ..models.simulation import ConcurrentBookingSimulationModel, UserSimulationModel
from ..models.seat import SeatReservationModel

logger = logging.getLogger(__name__)


@dataclass
class BookingScenario:
    """Configuration for a booking simulation scenario."""
    scenario_name: str
    concurrent_users: int
    target_seats: List[int]  # Seats that users will try to book
    booking_pattern: str     # "random", "focused", "sequential"
    user_think_time_ms: Tuple[int, int]  # Min, max think time between actions
    confirmation_rate: float  # Percentage of users who confirm reservations
    simulation_duration_seconds: int


class BookingSimulator:
    """
    Multi-user seat booking simulator for race condition demonstration.
    
    Features:
    - Configurable concurrency levels (1-100 concurrent users)
    - Multiple booking patterns (random, focused on popular seats, sequential)
    - Race condition detection and prevention showcase
    - Performance metrics for lock contention and booking success rates
    - Realistic user behavior simulation with think times
    """
    
    def __init__(self, seat_manager: SeatReservationManager):
        """
        Initialize booking simulator.
        
        Args:
            seat_manager: SeatReservationManager instance for booking operations
        """
        self.seat_manager = seat_manager
        self.active_simulations: Dict[str, ConcurrentBookingSimulationModel] = {}
        
        # Predefined scenarios for different demonstration purposes
        self.scenarios = {
            "high_contention": BookingScenario(
                scenario_name="High Contention - Popular Seats",
                concurrent_users=20,
                target_seats=[1, 2, 3, 4, 5],  # First 5 seats (high demand)
                booking_pattern="focused",
                user_think_time_ms=(100, 500),
                confirmation_rate=0.8,
                simulation_duration_seconds=30
            ),
            "moderate_contention": BookingScenario(
                scenario_name="Moderate Contention - Mixed Demand",
                concurrent_users=15,
                target_seats=list(range(1, 21)),  # First 20 seats
                booking_pattern="random",
                user_think_time_ms=(200, 1000),
                confirmation_rate=0.7,
                simulation_duration_seconds=45
            ),
            "low_contention": BookingScenario(
                scenario_name="Low Contention - Distributed Booking",
                concurrent_users=10,
                target_seats=list(range(1, 51)),  # First 50 seats
                booking_pattern="sequential",
                user_think_time_ms=(500, 1500),
                confirmation_rate=0.9,
                simulation_duration_seconds=60
            ),
            "race_condition_demo": BookingScenario(
                scenario_name="Race Condition Demo - Single Seat",
                concurrent_users=50,
                target_seats=[12],  # Everyone tries to book seat 12
                booking_pattern="focused",
                user_think_time_ms=(50, 200),
                confirmation_rate=1.0,
                simulation_duration_seconds=15
            )
        }
        
        logger.info("BookingSimulator initialized with predefined scenarios")
    
    async def run_simulation(
        self,
        flight_id: str,
        scenario_name: str = "moderate_contention",
        custom_scenario: Optional[BookingScenario] = None
    ) -> ConcurrentBookingSimulationModel:
        """
        Run a concurrent booking simulation.
        
        Args:
            flight_id: Flight identifier for seat bookings
            scenario_name: Name of predefined scenario to run
            custom_scenario: Optional custom scenario configuration
            
        Returns:
            ConcurrentBookingSimulationModel: Simulation results and metrics
        """
        scenario = custom_scenario or self.scenarios.get(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        simulation_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Initialize simulation model
        simulation = ConcurrentBookingSimulationModel(
            simulation_id=simulation_id,
            flight_id=flight_id,
            num_concurrent_users=scenario.concurrent_users,
            successful_reservations=0,
            failed_reservations=0,
            race_conditions_detected=0,
            average_response_time_ms=0.0,
            lock_contention_events=0,
            simulation_duration_ms=0
        )
        
        self.active_simulations[simulation_id] = simulation
        
        logger.info(f"Starting simulation '{scenario.scenario_name}' for flight {flight_id} "
                   f"with {scenario.concurrent_users} concurrent users")
        
        try:
            # Create user simulation tasks
            user_tasks = []
            for i in range(scenario.concurrent_users):
                user_id = f"sim_user_{simulation_id}_{i}"
                task = self._simulate_user_booking(
                    simulation_id=simulation_id,
                    flight_id=flight_id,
                    user_id=user_id,
                    scenario=scenario
                )
                user_tasks.append(task)
            
            # Run all user simulations concurrently
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Process results
            successful_reservations = 0
            failed_reservations = 0
            race_conditions = 0
            total_response_time = 0.0
            lock_contentions = 0
            valid_results = []
            
            for result in user_results:
                if isinstance(result, UserSimulationModel):
                    valid_results.append(result)
                    
                    if result.success:
                        successful_reservations += 1
                    else:
                        failed_reservations += 1
                        
                        # Detect race conditions (failed due to seat unavailability)
                        if result.error_message and "not available" in result.error_message.lower():
                            race_conditions += 1
                        
                        # Detect lock contention (failed to acquire lock)
                        if result.error_message and "lock" in result.error_message.lower():
                            lock_contentions += 1
                    
                    total_response_time += result.total_response_time_ms
                elif isinstance(result, Exception):
                    logger.warning(f"User simulation failed with exception: {result}")
                    failed_reservations += 1
            
            # Calculate final metrics
            simulation_duration_ms = int((time.time() - start_time) * 1000)
            avg_response_time = (
                total_response_time / len(valid_results) 
                if valid_results else 0.0
            )
            
            # Update simulation model
            simulation.successful_reservations = successful_reservations
            simulation.failed_reservations = failed_reservations
            simulation.race_conditions_detected = race_conditions
            simulation.average_response_time_ms = avg_response_time
            simulation.lock_contention_events = lock_contentions
            simulation.simulation_duration_ms = simulation_duration_ms
            simulation.completed_at = datetime.now()
            
            logger.info(f"Simulation completed: {successful_reservations} successful, "
                       f"{failed_reservations} failed, {race_conditions} race conditions, "
                       f"{lock_contentions} lock contentions")
            
            return simulation
            
        except Exception as e:
            logger.error(f"Error running simulation {simulation_id}: {e}")
            simulation.completed_at = datetime.now()
            simulation.simulation_duration_ms = int((time.time() - start_time) * 1000)
            raise
        
        finally:
            # Clean up active simulation tracking
            if simulation_id in self.active_simulations:
                del self.active_simulations[simulation_id]
    
    async def _simulate_user_booking(
        self,
        simulation_id: str,
        flight_id: str,
        user_id: str,
        scenario: BookingScenario
    ) -> UserSimulationModel:
        """
        Simulate a single user's booking behavior.
        
        Args:
            simulation_id: Simulation identifier
            flight_id: Flight identifier
            user_id: User identifier
            scenario: Booking scenario configuration
            
        Returns:
            UserSimulationModel: User simulation results
        """
        start_time = time.time()
        
        # Select target seat based on booking pattern
        target_seat = self._select_target_seat(scenario)
        
        user_sim = UserSimulationModel(
            user_id=user_id,
            target_seat=target_seat,
            attempt_start=datetime.now()
        )
        
        try:
            # Simulate user think time before booking
            think_time = random.uniform(
                scenario.user_think_time_ms[0] / 1000,
                scenario.user_think_time_ms[1] / 1000
            )
            await asyncio.sleep(think_time)
            
            # Attempt seat reservation
            lock_start_time = time.time()
            
            reservation = await self.seat_manager.reserve_seat(
                flight_id=flight_id,
                seat_number=target_seat,
                user_id=user_id,
                timeout_seconds=5.0
            )
            
            lock_wait_time_ms = int((time.time() - lock_start_time) * 1000)
            user_sim.lock_wait_time_ms = lock_wait_time_ms
            
            if reservation:
                user_sim.success = True
                
                # Simulate confirmation decision
                if random.random() < scenario.confirmation_rate:
                    # Simulate additional think time before confirmation
                    confirmation_think_time = random.uniform(0.1, 0.5)
                    await asyncio.sleep(confirmation_think_time)
                    
                    # Confirm the reservation
                    confirmed = await self.seat_manager.confirm_reservation(
                        flight_id=flight_id,
                        seat_number=target_seat,
                        user_id=user_id,
                        booking_id=random.randint(10000, 99999)
                    )
                    
                    if not confirmed:
                        user_sim.error_message = "Failed to confirm reservation"
                        user_sim.success = False
                else:
                    # User decides not to confirm - release reservation
                    await self.seat_manager.release_reservation(
                        flight_id=flight_id,
                        seat_number=target_seat,
                        user_id=user_id
                    )
                    user_sim.error_message = "User chose not to confirm"
                    user_sim.success = False
            else:
                user_sim.success = False
                user_sim.error_message = "Seat not available or lock acquisition failed"
            
        except Exception as e:
            user_sim.success = False
            user_sim.error_message = str(e)
            logger.warning(f"User simulation error for {user_id}: {e}")
        
        finally:
            user_sim.attempt_end = datetime.now()
            user_sim.total_response_time_ms = int((time.time() - start_time) * 1000)
        
        return user_sim
    
    def _select_target_seat(self, scenario: BookingScenario) -> int:
        """
        Select target seat based on booking pattern.
        
        Args:
            scenario: Booking scenario configuration
            
        Returns:
            int: Selected seat number
        """
        if scenario.booking_pattern == "focused":
            # Focus on first few seats (high contention)
            return random.choice(scenario.target_seats[:min(5, len(scenario.target_seats))])
        
        elif scenario.booking_pattern == "random":
            # Random selection from all target seats
            return random.choice(scenario.target_seats)
        
        elif scenario.booking_pattern == "sequential":
            # Sequential selection (lower contention)
            # Use user ID hash to distribute users across seats
            return scenario.target_seats[
                hash(str(time.time())) % len(scenario.target_seats)
            ]
        
        else:
            # Default to random
            return random.choice(scenario.target_seats)
    
    async def run_race_condition_demonstration(
        self,
        flight_id: str,
        target_seat: int,
        num_concurrent_users: int = 20
    ) -> Dict[str, Any]:
        """
        Demonstrate race conditions with multiple users targeting the same seat.
        
        Args:
            flight_id: Flight identifier
            target_seat: Seat number that all users will try to book
            num_concurrent_users: Number of concurrent users
            
        Returns:
            Dict[str, Any]: Race condition demonstration results
        """
        logger.info(f"Starting race condition demo: {num_concurrent_users} users targeting seat {target_seat}")
        
        start_time = time.time()
        
        # Create custom scenario for race condition demo
        race_scenario = BookingScenario(
            scenario_name="Race Condition Demonstration",
            concurrent_users=num_concurrent_users,
            target_seats=[target_seat],
            booking_pattern="focused",
            user_think_time_ms=(10, 50),  # Very short think times
            confirmation_rate=1.0,  # Everyone tries to confirm
            simulation_duration_seconds=10
        )
        
        # Run the simulation
        simulation_result = await self.run_simulation(
            flight_id=flight_id,
            custom_scenario=race_scenario
        )
        
        # Analyze race condition patterns
        analysis = {
            "demonstration_summary": {
                "target_seat": target_seat,
                "concurrent_attempts": num_concurrent_users,
                "successful_bookings": simulation_result.successful_reservations,
                "failed_attempts": simulation_result.failed_reservations,
                "race_conditions_detected": simulation_result.race_conditions_detected,
                "lock_contention_events": simulation_result.lock_contention_events,
                "success_rate": (
                    simulation_result.successful_reservations / num_concurrent_users
                    if num_concurrent_users > 0 else 0.0
                ),
                "average_response_time_ms": simulation_result.average_response_time_ms,
                "total_duration_ms": simulation_result.simulation_duration_ms
            },
            "race_condition_analysis": {
                "expected_winners": 1,  # Only one user should successfully book the seat
                "actual_winners": simulation_result.successful_reservations,
                "data_consistency": simulation_result.successful_reservations <= 1,
                "lock_effectiveness": (
                    simulation_result.lock_contention_events / 
                    (num_concurrent_users - 1) if num_concurrent_users > 1 else 0.0
                ),
                "race_prevention_success": simulation_result.race_conditions_detected == 0
            },
            "performance_metrics": {
                "lock_acquisition_efficiency": (
                    1.0 - (simulation_result.lock_contention_events / num_concurrent_users)
                    if num_concurrent_users > 0 else 0.0
                ),
                "system_throughput": (
                    num_concurrent_users / (simulation_result.simulation_duration_ms / 1000)
                    if simulation_result.simulation_duration_ms > 0 else 0.0
                ),
                "fairness_score": (
                    1.0 / num_concurrent_users if simulation_result.successful_reservations == 1
                    else 0.0
                )
            }
        }
        
        logger.info(f"Race condition demo completed: "
                   f"{analysis['demonstration_summary']['successful_bookings']} winner(s), "
                   f"data consistency: {analysis['race_condition_analysis']['data_consistency']}")
        
        return analysis
    
    async def run_performance_comparison(
        self,
        flight_id: str,
        with_locking: bool = True,
        without_locking: bool = True
    ) -> Dict[str, Any]:
        """
        Compare performance with and without distributed locking.
        
        Args:
            flight_id: Flight identifier
            with_locking: Run simulation with locking enabled
            without_locking: Run simulation with locking disabled (for comparison)
            
        Returns:
            Dict[str, Any]: Performance comparison results
        """
        comparison_results = {
            "flight_id": flight_id,
            "with_locking": None,
            "without_locking": None,
            "performance_comparison": {}
        }
        
        # Standard test scenario
        test_scenario = BookingScenario(
            scenario_name="Performance Comparison",
            concurrent_users=15,
            target_seats=list(range(1, 11)),  # First 10 seats
            booking_pattern="random",
            user_think_time_ms=(100, 300),
            confirmation_rate=0.8,
            simulation_duration_seconds=30
        )
        
        if with_locking:
            logger.info("Running simulation WITH distributed locking...")
            
            # Ensure flight seating is initialized
            await self.seat_manager.create_flight_seating(flight_id, "boeing_737")
            
            with_locking_result = await self.run_simulation(
                flight_id=flight_id,
                custom_scenario=test_scenario
            )
            comparison_results["with_locking"] = with_locking_result.model_dump()
        
        if without_locking:
            logger.info("Running simulation WITHOUT distributed locking...")
            
            # For demonstration purposes, we'll simulate what would happen
            # without proper locking by using very short lock timeouts
            # This is a simplified approach for educational purposes
            
            # Temporarily modify lock timeout for demonstration
            original_timeout = self.seat_manager.lock_timeout
            self.seat_manager.lock_timeout = 0.001  # 1ms timeout (effectively no locking)
            
            try:
                # Re-initialize flight seating
                await self.seat_manager.create_flight_seating(flight_id + "_no_lock", "boeing_737")
                
                without_locking_result = await self.run_simulation(
                    flight_id=flight_id + "_no_lock",
                    custom_scenario=test_scenario
                )
                comparison_results["without_locking"] = without_locking_result.model_dump()
                
            finally:
                # Restore original timeout
                self.seat_manager.lock_timeout = original_timeout
        
        # Calculate performance comparison metrics
        if comparison_results["with_locking"] and comparison_results["without_locking"]:
            with_lock = comparison_results["with_locking"]
            without_lock = comparison_results["without_locking"]
            
            comparison_results["performance_comparison"] = {
                "data_consistency": {
                    "with_locking_race_conditions": with_lock["race_conditions_detected"],
                    "without_locking_race_conditions": without_lock["race_conditions_detected"],
                    "consistency_improvement": (
                        without_lock["race_conditions_detected"] - with_lock["race_conditions_detected"]
                    )
                },
                "performance_impact": {
                    "with_locking_avg_response_ms": with_lock["average_response_time_ms"],
                    "without_locking_avg_response_ms": without_lock["average_response_time_ms"],
                    "response_time_overhead_ms": (
                        with_lock["average_response_time_ms"] - without_lock["average_response_time_ms"]
                    ),
                    "overhead_percentage": (
                        ((with_lock["average_response_time_ms"] - without_lock["average_response_time_ms"]) /
                         without_lock["average_response_time_ms"] * 100)
                        if without_lock["average_response_time_ms"] > 0 else 0.0
                    )
                },
                "success_rates": {
                    "with_locking_success_rate": (
                        with_lock["successful_reservations"] / 
                        (with_lock["successful_reservations"] + with_lock["failed_reservations"])
                        if (with_lock["successful_reservations"] + with_lock["failed_reservations"]) > 0 else 0.0
                    ),
                    "without_locking_success_rate": (
                        without_lock["successful_reservations"] / 
                        (without_lock["successful_reservations"] + without_lock["failed_reservations"])
                        if (without_lock["successful_reservations"] + without_lock["failed_reservations"]) > 0 else 0.0
                    )
                }
            }
        
        logger.info("Performance comparison completed")
        return comparison_results
    
    def get_available_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available simulation scenarios.
        
        Returns:
            Dict[str, Dict[str, Any]]: Scenario information
        """
        scenarios_info = {}
        
        for name, scenario in self.scenarios.items():
            scenarios_info[name] = {
                "scenario_name": scenario.scenario_name,
                "concurrent_users": scenario.concurrent_users,
                "target_seats_count": len(scenario.target_seats),
                "booking_pattern": scenario.booking_pattern,
                "user_think_time_range_ms": scenario.user_think_time_ms,
                "confirmation_rate": scenario.confirmation_rate,
                "duration_seconds": scenario.simulation_duration_seconds,
                "description": self._get_scenario_description(name)
            }
        
        return scenarios_info
    
    def _get_scenario_description(self, scenario_name: str) -> str:
        """Get description for a scenario."""
        descriptions = {
            "high_contention": "Demonstrates high lock contention with many users targeting popular seats",
            "moderate_contention": "Balanced simulation with moderate contention across multiple seats",
            "low_contention": "Low contention scenario with distributed booking patterns",
            "race_condition_demo": "Extreme race condition demonstration with all users targeting one seat"
        }
        return descriptions.get(scenario_name, "Custom simulation scenario")
    
    def get_active_simulations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about currently active simulations.
        
        Returns:
            Dict[str, Dict[str, Any]]: Active simulation information
        """
        active_info = {}
        
        for sim_id, simulation in self.active_simulations.items():
            active_info[sim_id] = {
                "simulation_id": sim_id,
                "flight_id": simulation.flight_id,
                "concurrent_users": simulation.num_concurrent_users,
                "started_at": simulation.started_at.isoformat(),
                "status": "running" if simulation.completed_at is None else "completed"
            }
        
        return active_info