# 4.4 Eviction Policies: LRU vs LFU

## Overview

Understand different eviction policies and when to use each one.

## Least Recently Used (LRU)

### How it Works
Evicts the least recently accessed items first.

### Best For
- Time-sensitive data
- Trending content
- Session data

### Configuration
```
maxmemory-policy allkeys-lru
```

## Least Frequently Used (LFU)

### How it Works
Evicts the least frequently accessed items first.

### Best For
- Stable access patterns
- Reference data
- Long-term popular content

### Configuration
```
maxmemory-policy allkeys-lfu
```

## Other Policies

- **volatile-lru**: LRU among keys with TTL
- **volatile-lfu**: LFU among keys with TTL
- **allkeys-random**: Random eviction
- **volatile-ttl**: Evict keys with shortest TTL
- **noeviction**: Return errors when memory limit reached

## Hands-on Demo

[Demo comparing LRU vs LFU behavior]

## Key Takeaways

- Choose eviction policy based on access patterns
- LRU for recency, LFU for frequency
- Monitor eviction metrics in production
