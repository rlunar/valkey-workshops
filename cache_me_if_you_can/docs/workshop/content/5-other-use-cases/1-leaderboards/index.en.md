# 5.1 Leaderboards for Top Airports

## Overview

Demonstrate the substantial difference between running analytical queries in an OLTP RDBMS versus using a purpose-built data structure (Valkey Sorted Set).

## The Challenge

Leaderboards require:
- Real-time ranking
- Frequent updates
- Fast retrieval of top N items
- Score-based sorting

## OLTP RDBMS Approach

### Query Example
```sql
SELECT airport_name, flight_count 
FROM airports 
ORDER BY flight_count DESC 
LIMIT 10;
```

### Challenges
- Full table scan or index scan
- Expensive sorting operation
- High compute requirements
- Latency increases with data size

## Valkey Sorted Set Approach

### Commands
```
ZADD airport:leaderboard 1523 "JFK"
ZADD airport:leaderboard 1456 "LAX"
ZREVRANGE airport:leaderboard 0 9 WITHSCORES
```

### Benefits
- O(log N) insertion
- O(log N + M) range queries
- Minimal compute
- Consistent low latency

## Hands-on Demo

[Demo comparing RDBMS vs Valkey Sorted Set performance]

## Performance Comparison

| Metric | RDBMS | Valkey Sorted Set |
|--------|-------|-------------------|
| Latency | 100ms+ | <1ms |
| CPU Usage | High | Minimal |
| Scalability | Limited | Excellent |

## Key Takeaways

- Purpose-built data structures outperform general-purpose databases
- Sorted Sets are ideal for leaderboards and rankings
- Dramatic reduction in compute and latency
- Real-time updates without performance penalty
