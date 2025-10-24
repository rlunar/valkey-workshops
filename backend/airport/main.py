"""
Main entry point for the OPN402 workshop application.
"""

from airport.utils.config import get_config


def main() -> int:
    """Main entry point for the OPN402 workshop."""
    print("🚀 OPN402: Cache me if you can, Valkey edition")
    print("=" * 50)

    try:
        # Load and validate configuration
        config = get_config()
        print("✓ Configuration loaded successfully")

        # TODO: Initialize workshop application
        print("📚 Workshop application starting...")
        print("   Use Case 1: Database Query Optimization")
        print("   Use Case 2: Seat Reservation with Bitmaps & Locks")
        print("   Use Case 3: Real-time Leaderboards")
        print("\n🔧 Implementation in progress...")

    except Exception as e:
        print(f"❌ Failed to start workshop: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
