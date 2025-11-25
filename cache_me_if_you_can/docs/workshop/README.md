Title: Cache me if you can, Valkey edition

Session Abstract:

This hands-on workshop explores practical caching with Valkey through three key use cases: database query optimization, session management, and real-time leaderboards. Participants will learn to cache expensive database operations, external API calls, and JSON configurations while building scalable session storage and dynamic leaderboards.

Beyond implementation, the workshop emphasizes critical caching challenges including cache invalidation, stampede prevention, memory management, and data consistency. Attendees will experience common pitfalls firsthand and learn proven strategies for cache warming, TTL optimization, and production monitoring.

Participants leave with working code examples, architectural patterns, and clear understanding of caching trade-offs they can immediately apply to their applications.

Level: 400 – Expert
Type: Workshop
Duration: 120 minutes
Format: Hands-on, Interactive

Topics:
Databases, Open Source
Resilience, DevOps

Target Audience:
Developer / Engineer
DevOps Engineer
Solution / Systems Architect

Modules:
1. Why Caching is important? 
1.1 Explore the sample Airport App. Demonstrate caching benefits visually.
1.2 Understand the AirportDB (FlughafenDB) schema. Use mycli to run sample queries and validate latency as well as understand the query plan with the EXPLAIN command and diagrams.

2. Common Caching Patterns
2.1 Cache Aside or Lazy Loading. Explain in depth the pattern and use cases with demos of different queries from simple, medium and advanced to gauge performance vs cache. Summarize pros and cons.
2.2 Write Through. Explain in depth the pattern and use cases with demo where data needs to be synchonized between cache and RDBMS. Summarize pros and cons.
2.3 Write Behind. Explain in depth the pattern and use cases with demo where data can be updated afterwards in the RDBMS (usually proactive caching). Summarize pros and cons.

3. Anything that can be queried can be cached.
3.1 Weather API. Use Valkey to cache external API responses, to reduce latency and costs. Demonstrate getting the weather from multiple cities in different countries.
3.2 GenAI Semantic Caching. Explore the use case using prompts to convert NLP to SQL, and use Valkey Vector Similarity Search to reduce the number of times we call the model by implementing semantic caching so similar prompts can be bunbled in a single model request and reduce the latency and number of tokens used.

4. Advanced Caching Concepts
4.1 Performance testing. Explain multiple scenarios to understand the following concepts:
4.1.1 Concurrency
4.1.2 Read/write ratio
4.1.3 Variance in the sets of cacheable data
4.1.4 Time To Live (TTL)
4.2 Understand which use cases are candidates for caching.
4.3 Key Naming for proper key management in a flat keyspace.
4.4 Eviction policies LRU vs LFU
4.5 Stampede prevention techniques. In the Weather API demo, showcase the use of a distributed lock to reduce the number of times we are calling the external API and make use of exponential backoff to reduce the thundering herd of client requests. Explain the difference the TTL in the lock makes to be able to prevent (or not) stampedes.

5. Other Valkey use cases (Optional)
5.1 Leaderboards for top airports. Demonstrate the substancial difference of running analytical queries in an OLTP RDBMS vs a purpose built data structure (Valkey Sorted Set) to achieve the same result with far less compute and latency.
5.2 Session Store. Demonstrate a simple application that uses Valkey as the Session Store for Flask, add a Zip Code and fetch the weather or Add a Flight. Showcase how data is ephemeral when the user logs out.