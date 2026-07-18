# Cache Me If You Can: GenAI Weather

This module accepts natural-language weather questions, resolves relative dates in the requested city's time zone, fetches structured data through the shared `openweathermap_api` client, and returns a concise prose answer.

## Cache architecture

```text
Natural-language question
        |
        v
Static alias lookup, then OpenWeatherMap Direct Geocoding
        |
        v
Geocoding metadata cache
        |
        v
IANA time-zone lookup + intent normalization
        |
        v
Exact interpreted-answer cache
        |
        | miss
        v
Valkey Search KNN + 0.90 gate + MMR
        |
        | miss
        v
openweathermap_api.OpenWeatherMapClient
        |
        v
OpenWeatherMap Valkey JSON response cache
        |
        | miss
        v
OpenWeatherMap One Call API 4.0
        |
        v
Prose interpretation
        |
        v
Interpreted answer + prompt embedding cache
```

The system uses three independent namespaces:

1. **Geocoding metadata cache:** stores city search results under `openweathermap:geocoding:v1:cache:v1:response:*` and defaults to a 24-hour TTL. It prevents repeated geocoding calls during prompt normalization.
2. **OpenWeatherMap response cache:** stores raw upstream weather JSON under `openweathermap:onecall:v4:cache:v1:response:*` and defaults to a 10-minute TTL.
3. **Interpreted answer cache:** stores prose answers, exact prompt pointers, and FLOAT32 prompt embeddings under `genai-weather:v3:*` and defaults to a 15-minute TTL.

The raw weather and interpreted-answer namespaces remain the two weather/answer cache layers. Geocoding metadata is kept separate from both. API keys are never included in cache keys or returned responses.

An exact interpreted-answer hit avoids embedding generation, weather lookup, and interpretation. A semantic hit performs embedding search but avoids the weather lookup and interpretation. Location resolution occurs first so cache compatibility can include the resolved city and its local time window. Static aliases preserve stable IDs for the workshop's original cities; other locations use cached worldwide geocoding. On a full miss, the weather client still checks its independent raw response cache before calling the upstream API.

Semantic answers are reused only when city, explicit time window, units, and timeline granularity match. Candidates below `0.90` cosine similarity are rejected. Qualified candidates are reranked with relevance-heavy Maximal Marginal Relevance (MMR), using `lambda=0.85` by default. The highest-similarity candidate remains first for the single answer. The implementation follows the [Valkey bundle demo MMR algorithm](https://github.com/valkey-io/valkey-bundle-demo/blob/main/app.py#L163).

## Supported questions

City resolution supports locations worldwide. The parser first checks known workshop aliases such as `Cuzco`, then uses OpenWeatherMap Direct Geocoding for other names. It recognizes forms including:

- `What is the weather today in Tokyo?`
- `Give me the forecast for São Paulo tomorrow`
- `Weather at Paris next week`
- `Berlin weather today`

OpenWeatherMap's first relevance-ranked result is used when a name is ambiguous. Include the state or province and country—for example, `Springfield, Illinois, US`—to select a specific place.

Supported periods are:

- `yesterday`
- `today`, or no period, which defaults to today
- `now`
- `this afternoon`
- `tomorrow`
- `next week`, defined as the next Monday through Sunday
- `next N days`, where `N` is from 1 through 14 and includes today

At `2026-07-18 07:59 UTC-05:00`, for example, `today` normalizes to `2026-07-18`, `now` to `2026-07-18T07:59:00-05:00`, and `this afternoon` to the local noon-through-18:00 interval. Runtime values are calculated dynamically with the resolved city's IANA time zone.

## Configuration

From the repository root, start the Valkey bundle and install dependencies:

```bash
./quickstart.sh
```

Set `OPENWEATHERMAP_API_KEY` in `cache_me_if_you_can/.env`. Relevant optional settings are in `.env.example`:

```dotenv
# Worldwide city geocoding metadata cache
OPENWEATHERMAP_GEOCODING_BASE_URL=https://api.openweathermap.org/geo/1.0/direct
OPENWEATHERMAP_GEOCODING_CACHE_ENABLED=true
OPENWEATHERMAP_GEOCODING_CACHE_HOST=localhost
OPENWEATHERMAP_GEOCODING_CACHE_PORT=16379
OPENWEATHERMAP_GEOCODING_CACHE_DB=0
OPENWEATHERMAP_GEOCODING_CACHE_TTL_SECONDS=86400

# Raw OpenWeatherMap JSON response cache
OPENWEATHERMAP_CACHE_ENABLED=true
OPENWEATHERMAP_CACHE_HOST=localhost
OPENWEATHERMAP_CACHE_PORT=16379
OPENWEATHERMAP_CACHE_TTL_SECONDS=600

# Interpreted prose and semantic prompt cache
GENAI_WEATHER_CACHE_ENABLED=true
GENAI_WEATHER_CACHE_HOST=localhost
GENAI_WEATHER_CACHE_PORT=16379
GENAI_WEATHER_CACHE_TTL_SECONDS=900
GENAI_WEATHER_SIMILARITY_THRESHOLD=0.90
GENAI_WEATHER_MMR_LAMBDA=0.85
GENAI_WEATHER_MMR_TOP_N=5
```

All caches may use the same Valkey bundle because their key namespaces do not overlap.

## Run

From `cache_me_if_you_can`:

```bash
uv run python -m cache_me_if_you_can_genai
```

The API listens on `http://127.0.0.1:5001`. The GenAI process imports `openweathermap_api.OpenWeatherMapClient` directly, so the separate proxy process on port `5000` does not need to be running.

## Ask a question

`POST /weather` accepts JSON and returns a compact JSON envelope. Only the interpreted prose, request latency, interpreted-cache metadata, and service metrics are included; the raw OpenWeatherMap response is never exposed by this endpoint.

```bash
curl -i -X POST "http://127.0.0.1:5001/weather" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the weather today in Lima?","units":"metric"}'
```

Example body for Saturday, July 18, 2026:

```json
{
  "bot-reply": "The weather in Lima, Peru 🇵🇪 today, Saturday July 18th, 2026, is cloudy ⛅ at 17.44 degrees Celsius.",
  "latency_ms": 245.317,
  "cache": {
    "hit": false,
    "type": "miss",
    "similarity": null,
    "matched_prompt": null
  },
  "metrics": {
    "requests": 1,
    "cache_hits": 0,
    "hit_rate": 0.0,
    "weather_api_calls": 1,
    "interpretation_calls": 1
  }
}
```

The `metrics` object also includes the remaining service counters. The same cache and latency values remain available in response headers:

```text
Content-Type: application/json
X-GenAI-Cache-Hit: false
X-GenAI-Cache-Type: miss
X-Total-Time-Ms: 245.317
Server-Timing: total;dur=245.317
```

Ask a differently worded equivalent question to exercise semantic caching:

```bash
curl -i -X POST "http://127.0.0.1:5001/weather" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Give me the weather forecast for Lima","units":"metric"}'
```

A qualified semantic hit also includes:

```text
X-GenAI-Cache-Type: semantic
X-Semantic-Similarity: 0.93
X-Semantic-Matched-Prompt: What is the weather today in Lima?
```

Mexico City period examples:

```bash
for period in yesterday today tomorrow "next week" "next 3 days" "next 10 days"; do
  curl -sS -X POST "http://127.0.0.1:5001/weather" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\":\"What is the weather in Mexico City ${period}?\"}"
  printf '\n'
done
```

## Inspect cache namespaces

Worldwide geocoding metadata:

```bash
valkey-cli -p 16379 --scan \
  --pattern 'openweathermap:geocoding:v1:cache:v1:response:*'
```

Raw OpenWeatherMap JSON responses:

```bash
valkey-cli -p 16379 --scan \
  --pattern 'openweathermap:onecall:v4:cache:v1:response:*'
```

Interpreted answers and prompt vectors:

```bash
valkey-cli -p 16379 --scan --pattern 'genai-weather:v3:*'
valkey-cli -p 16379 FT.INFO genai_weather_interpreted_prompts_v3
```

Operational endpoints remain JSON:

```text
GET    /health
GET    /metrics
DELETE /cache
```

`DELETE /cache` clears only interpreted-answer keys and is disabled unless `GENAI_WEATHER_CACHE_ALLOW_CLEAR=true`. The raw OpenWeatherMap namespace has its own safety gate and clear endpoint in `openweathermap_api`.
