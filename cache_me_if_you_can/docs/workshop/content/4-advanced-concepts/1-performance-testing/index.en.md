# 4.1 Performance Testing

## Overview

Learn to conduct comprehensive performance testing to understand caching behavior under various scenarios.

## Testing Scenarios

### 4.1.1 Concurrency

Understanding how caching performs under concurrent load:
- Multiple simultaneous requests
- Connection pooling
- Thread safety considerations

[Demo content]

Let's see the options available in the script:

```bash
uv run samples/demo_multi_threaded_performance.py --help
```

Expected Output:

```bash
 Usage: demo_multi_threaded_performance.py [OPTIONS]

 Run multi-threaded performance test for MySQL + Valkey cache.

 Examples:
 # Basic test with defaults   python samples/demo_multi_threaded_performance.py      # High concurrency test   python samples/demo_multi_threaded_performance.py --threads 20
 --queries 50000      # Write-heavy workload   python samples/demo_multi_threaded_performance.py --threads 10 --queries 10000 --read-ratio 30      # Interactive mode with verbose
 output   python samples/demo_multi_threaded_performance.py --interactive --verbose --flush      # Random passenger mode (all passengers)   python
 samples/demo_multi_threaded_performance.py --threads 8 --queries 20000 --random

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --threads             -t      INTEGER  Number of concurrent threads to simulate [default: 4]                                                                                     │
│ --queries             -q      INTEGER  Number of queries per thread [default: 10000]                                                                                             │
│ --read-ratio          -r      INTEGER  Percentage of read operations (0-100) [default: 80]                                                                                       │
│ --ttl                         INTEGER  Cache TTL in milliseconds [default: 300000]                                                                                               │
│ --random                               Use random passenger IDs (all passengers). If not set, uses limited pool                                                                  │
│ --interactive         -i               Run in interactive mode with prompts                                                                                                      │
│ --verbose             -v               Show SQL query and cache key format with sample                                                                                           │
│ --flush               -f               Flush Valkey cache before running test                                                                                                    │
│ --install-completion                   Install completion for the current shell.                                                                                                 │
│ --show-completion                      Show completion for the current shell, to copy it or customize the installation.                                                          │
│ --help                                 Show this message and exit.                                                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

Run the multi-threaded performance benchmark tool using 4 threads each doing a total of 10,000 requests with 80% of them being reads and setting a Time To Live (TTL) in the cace of 5 minutes (300 seconds => 300,000 milliseconds) interactive with verbose output and cache flush:

```bash
uv run samples/demo_multi_threaded_performance.py -t 4 -q 10000 -r 80 --ttl 300000 -i -v -f
```

After running the performance script dive deep into the metrics with graphical visualization.

First see the options from the plot script:

```bash
uv run samples/plot_time_series.py --help
```

Expected Output:

```bash
 Usage: plot_time_series.py [OPTIONS] COMMAND [ARGS]...

 Plot and explain performance test time-series data

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                                                          │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                                                   │
│ --help                        Show this message and exit.                                                                                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ explain     Explain a time-series data point from a performance test log file.                                                                                                   │
│ plot-only   Show only time-series graphs without detailed explanations.                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```




### 4.1.2 Read/Write Ratio

Analyzing performance based on workload characteristics:
- Read-heavy workloads (90/10)
- Write-heavy workloads (10/90)
- Balanced workloads (50/50)

[Demo content]

Run the scrit again without flushing the cache and doing 99% reads:

```bash
uv run samples/demo_multi_threaded_performance.py -t 4 -q 10000 -r 99 --ttl 300000 -i -v
```

### 4.1.3 Variance in Cacheable Data Sets

Testing with different data access patterns:
- Hot data (frequently accessed)
- Cold data (rarely accessed)
- Working set size vs cache size

[Demo content]

Run the script again with a lower read ratio and a higher universe of possible passengers; flush the cache to have a clean slate:

```bash
uv run samples/demo_multi_threaded_performance.py -t 4 -q 10000 -r 60 --ttl 300000 --random -i -v -f
```

### 4.1.4 Time To Live (TTL)

Understanding TTL impact on performance and consistency:
- Short TTL (seconds)
- Medium TTL (minutes)
- Long TTL (hours/days)
- TTL vs data freshness trade-offs

[Demo content]

Run the script again with a short lived TTL a higher universe of possible passengers; flush the cache to have a clean slate:

```bash
uv run samples/demo_multi_threaded_performance.py -t 4 -q 10000 -r 90 --ttl 100 --random -i -v -f
```


## Key Takeaways

- Performance testing reveals optimal caching strategies
- Different workloads require different approaches
- TTL tuning is critical for balancing freshness and performance
