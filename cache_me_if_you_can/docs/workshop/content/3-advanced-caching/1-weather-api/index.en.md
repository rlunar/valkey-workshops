# 3.1 Weather API Caching

## Overview

Learn to use Valkey to cache external API responses, reducing both latency and costs.

## Objectives

- Cache external API responses effectively
- Reduce API call costs
- Improve response times for repeated queries
- Handle multiple cities and countries

## Use Case

Weather data from external APIs is perfect for caching because:
- Weather doesn't change frequently
- API calls have rate limits and costs
- Users often query the same locations

## Hands-on Demo

### Getting Weather from Multiple Cities

[Demo content showing weather API caching across different countries]

## Performance Metrics

[Comparison of cached vs uncached API calls]

## Key Takeaways

- External API caching significantly reduces costs
- TTL should match data freshness requirements
- Cache hit rates improve with popular queries
