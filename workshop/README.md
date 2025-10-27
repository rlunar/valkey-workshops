# OPN402: Cache me if you can, Valkey edition

A hands-on workshop exploring practical caching strategies with Valkey through real-world use cases.

## Workshop Information

**Session ID:** OPN402  
**Level:** 400 – Expert  
**Type:** Workshop  
**Duration:** 120 minutes  
**Format:** Hands-on, Interactive  

### Schedule
- **OPN402-R:** Wed, December 3, 12:30 PM - 2:30 PM PST | MGM Level 1, Grand 117
- **OPN402-R1:** Thu, December 4, 3:30 PM - 5:30 PM PST | MGM Level 3, Premier 313

### Topics
- Databases, Open Source
- Resilience, DevOps

### Target Audience
- Developer / Engineer
- DevOps Engineer  
- Solution / Systems Architect

### Speakers
- Roberto Luna-Rojas
- Nigel Brown
- Ran Shidlansik

## Workshop Overview

This hands-on workshop explores practical caching with Valkey through three key use cases:

1. **Database Query Optimization** - Cache expensive database operations and external API calls
2. **Session Management** - Build scalable session storage solutions
3. **Real-time Leaderboards** - Implement dynamic leaderboards with JSON configurations

Beyond implementation, the workshop emphasizes critical caching challenges including:
- Cache invalidation strategies
- Stampede prevention techniques
- Memory management best practices
- Data consistency patterns

## What You'll Learn

- Practical caching patterns for real-world applications
- Common caching pitfalls and how to avoid them
- Proven strategies for cache warming and TTL optimization
- Production monitoring and observability techniques
- Architectural patterns for scalable caching solutions

## Project Structure

```
├── data/           # Sample datasets (airlines, airports, routes, etc.)
├── docs/           # Workshop documentation and guides
├── models/         # Database models and schemas
├── scripts/        # Setup and demo scripts
├── tests/          # Test cases and examples
├── utils/          # Utility functions and helpers
└── main.py         # Main application entry point
```

## Prerequisites

- Python 3.8+
- Basic understanding of databases and caching concepts
- Familiarity with Redis/Valkey concepts (helpful but not required)

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd cache-workshop
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # or if using uv
   uv sync
   ```

3. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run Workshop Setup**
   ```bash
   python scripts/setup_workshop.sh
   ```

5. **Start the Application**
   ```bash
   python main.py
   ```

## Workshop Modules

### Module 1: Database Query Caching
Learn to cache expensive database operations using the FlughafenDB dataset with airlines, airports, and flight routes.

**Caching Patterns Covered:**
1. **Cache Aside (Lazy Loading)** - Load data into cache only when requested
2. **Write-through Cache** - Write to cache and database simultaneously
3. **Write Behind** - Write to cache immediately, database asynchronously

**Advanced Caching Patterns:**
- **Nested Doll Caching** - Hierarchical caching strategies for complex data structures
- **Proper TTL Management** - Dynamic TTL strategies based on data access patterns
- **Memory Saturation** - Handling cache memory limits and optimization techniques
- **Eviction Policies** - LRU, LFU, and custom eviction strategies for optimal performance
- **Cache Hit Ratio** - Monitoring and optimizing cache effectiveness metrics

### Module 2: Anything that can be queried can be cached
Explore caching strategies for various data sources beyond databases.

**Topics Covered:**
- **API Caching** - Cache external API responses and reduce latency
- **Object Store Caching** - Cache images and static assets for faster delivery

### Module 3: Real-time Leaderboards
Build dynamic leaderboards with efficient data structures and update patterns.

### Module 4: Session Management
Implement scalable session storage patterns for web applications.

## Key Learning Outcomes

By the end of this workshop, you'll have:
- Working code examples for common caching scenarios
- Understanding of caching trade-offs and when to apply different strategies
- Practical experience with cache invalidation and consistency patterns
- Production-ready monitoring and observability techniques
- Clear architectural patterns you can immediately apply to your applications

## Documentation

- [Workshop Setup Guide](docs/README.md)
- [Flight Database Schema](docs/FlughafenDB.md)
- [Query Examples](docs/query_demo.md)
- [Flight Rules and Logic](docs/flight_rules.md)

## Support

For questions during the workshop, reach out to any of the speakers or check the documentation in the `docs/` directory.

---

*This workshop is part of the AWS re:Invent 2024 conference.*