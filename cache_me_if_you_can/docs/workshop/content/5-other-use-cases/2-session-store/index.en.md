# 5.2 Session Store

## Overview

Demonstrate a simple application that uses Valkey as the Session Store for Flask, showcasing ephemeral data management.

## Why Valkey for Sessions?

- Fast read/write operations
- Automatic expiration with TTL
- Distributed session sharing
- Horizontal scalability

## Use Case

A Flask application where users can:
- Add a Zip Code and fetch weather
- Add a Flight to their session
- View session data
- Logout (data is ephemeral)

## Implementation

### Flask Session Configuration
```python
from flask import Flask, session
from flask_session import Session

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis_client
```

## Hands-on Demo

### User Flow
1. User logs in
2. Add zip code to session
3. Fetch weather for that location
4. Add flight information
5. View all session data
6. Logout - data disappears

### Key Features
- Session data stored in Valkey
- Automatic TTL management
- Data persists across requests
- Ephemeral - gone on logout

## Session Data Structure

```json
{
  "user_id": "12345",
  "zip_code": "10001",
  "weather": {...},
  "flights": [...]
}
```

## Key Takeaways

- Valkey is excellent for session management
- TTL ensures automatic cleanup
- Ephemeral data is handled efficiently
- Scales horizontally for distributed applications
