# Avela API Client - Python Utilities

Shared Python utilities for Avela API integrations with built-in rate limiting and retry logic.

## Rate Limits

The Avela API enforces rate limits at the AWS WAF level:

| Setting | Value |
|---------|-------|
| **Limit** | 100 requests per 5 minutes |
| **Scope** | Per IP address |
| **Response** | HTTP 429 (Too Many Requests) |

## Installation

### For Recipe Authors

Add to your recipe's `requirements.txt`:

```
requests>=2.31.0
-e ../../shared/python
```

Then install:

```bash
pip install -r requirements.txt
```

### Standalone Installation

```bash
cd shared/python
pip install -e .
```

## Quick Start

```python
from avela_client import AvelaClient

# Initialize client
client = AvelaClient(
    client_id='your_client_id',
    client_secret='your_client_secret',
    environment='prod'  # or 'qa', 'uat', 'dev'
)

# Make API calls - rate limiting handled automatically
response = client.get('/forms', params={'limit': 100})
data = response.json()
```

Or load credentials from config.json:

```python
from avela_client import create_client_from_config

client = create_client_from_config('config.json')
response = client.get('/applicants')
```

## Features

### Proactive Rate Limiting

The client automatically spaces requests to stay under the rate limit:

```
100 requests / 300 seconds = 1 request every 3 seconds (+ 10% buffer)
```

### Automatic Retry with Exponential Backoff

Uses the `backoff` library to handle transient failures:

- **429 (Rate Limited)**: Waits for `Retry-After` header duration, then retries
- **5xx (Server Error)**: Exponential backoff (2s, 4s, 8s, 16s, 32s)
- **Timeouts**: Automatic retry with backoff
- **Max retries**: 5 attempts or 5 minutes total

### Token Management

- Automatically authenticates on first request
- Refreshes token 1 hour before expiration
- No manual token handling required

## Usage Examples

### Paginated Fetching

```python
from avela_client import create_client_from_config

client = create_client_from_config()

# Fetch all forms with pagination
forms = []
offset = 0
limit = 1000

while True:
    response = client.get('/forms', params={'limit': limit, 'offset': offset})
    response.raise_for_status()

    data = response.json()
    batch = data.get('forms', [])
    forms.extend(batch)

    print(f'Fetched {len(forms)} forms...')

    if len(batch) < limit:
        break
    offset += limit

print(f'Total: {len(forms)} forms')
```

### Batch Operations

```python
from avela_client import create_client_from_config

client = create_client_from_config()

form_ids = ['uuid1', 'uuid2', 'uuid3', ...]

# Process in batches of 100 (API limit)
for i in range(0, len(form_ids), 100):
    batch = form_ids[i:i+100]

    response = client.get('/forms/files', params={
        'form_id': ','.join(batch)
    })

    # Process response...
    # Rate limiting is handled automatically
```

### Error Handling

```python
from avela_client import create_client_from_config
import requests

client = create_client_from_config()

try:
    response = client.get('/forms/invalid-endpoint')
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print('Endpoint not found')
    elif e.response.status_code == 403:
        print('Access denied - check permissions')
    else:
        print(f'HTTP error: {e}')
except requests.exceptions.RequestException as e:
    print(f'Request failed after retries: {e}')
```

## Configuration

### config.json Format

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "environment": "prod"
}
```

### Environments

| Environment | Auth URL | API URL |
|-------------|----------|---------|
| `prod` | `https://auth.avela.org` | `https://prod.execute-api.apply.avela.org` |
| `uat` | `https://uat.auth.avela.org` | `https://uat.execute-api.apply.avela.org` |
| `qa` | `https://qa.auth.avela.org` | `https://qa.execute-api.apply.avela.org` |
| `dev` | `https://dev.auth.avela.org` | `https://dev.execute-api.apply.avela.org` |

## Using in a Recipe

1. Add to your recipe's `requirements.txt`:
   ```
   -e ../../shared/python
   ```

2. Import in your script:
   ```python
   from avela_client import AvelaClient, create_client_from_config
   ```

3. Create `config.json` in your recipe directory (from `config.example.json`)

## How Rate Limiting Works

```
Request Flow:

  Your Code          AvelaClient              Avela API
      │                   │                       │
      │── client.get() ──>│                       │
      │                   │── wait if needed ──>  │
      │                   │── HTTP request ────────>│
      │                   │<─── 200 OK ────────────│
      │<── response ──────│                       │
      │                   │                       │
      │── client.get() ──>│                       │
      │                   │── wait 3.3s ───────>  │  (proactive)
      │                   │── HTTP request ────────>│
      │                   │<─── 429 Rate Limited ──│
      │                   │── wait Retry-After ──>│  (reactive)
      │                   │── HTTP request ────────>│
      │                   │<─── 200 OK ────────────│
      │<── response ──────│                       │
```

## Dependencies

Defined in `pyproject.toml`:

- `requests>=2.28.0` - HTTP library
- `backoff>=2.2.0` - Exponential backoff and retry
