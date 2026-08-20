# Avela API Client (Python Utilities)

Shared Python code for Avela API integrations, with rate limiting and retries built in.

## Rate Limits

The Avela API limits requests at the AWS WAF level:

| Setting      | Value                        |
| ------------ | ---------------------------- |
| **Limit**    | 100 requests per 5 minutes   |
| **Scope**    | Per IP address               |
| **Response** | HTTP 429 (Too Many Requests) |

## Installation

### For Recipe Authors

Add to your recipe's `requirements.txt`:

```
requests>=2.31.0
-e ../../shared/python
keyring>=24.0.0
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

Store your credentials once. [Credentials](#credentials) covers the other options:

```bash
python setup_credentials.py
```

Every script then finds them on its own:

```python
from avela_client import create_client

client = create_client()

# Make API calls - rate limiting handled automatically
response = client.get('/forms', params={'limit': 100})
data = response.json()
```

Pass credentials directly when you already have them:

```python
from avela_client import AvelaClient

client = AvelaClient(
    client_id='your_client_id',
    client_secret='your_client_secret',
    environment='prod',  # or 'qa', 'uat', 'dev'
)
```

## Features

### Proactive Rate Limiting

The client spaces out your requests to stay under the limit:

```
100 requests / 300 seconds = 1 request every 3 seconds (+ 10% buffer)
```

### Automatic Retry with Exponential Backoff

The `backoff` library retries failures that clear on their own:

- **429 (Rate Limited)**: waits the time given in the `Retry-After` header, then retries
- **5xx (Server Error)**: waits 2s, 4s, 8s, 16s, 32s between tries
- **Timeouts**: retries with the same waits
- **Max retries**: 5 attempts, or 5 minutes total

### Token Management

- Authenticates on the first request
- Refreshes the token 1 hour before it expires
- You never handle a token yourself

## Usage Examples

### Paginated Fetching

```python
from avela_client import create_client

client = create_client()

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
from avela_client import create_client

client = create_client()

form_ids = ['uuid1', 'uuid2', 'uuid3', ...]

# Process in batches of 100 (API limit)
for i in range(0, len(form_ids), 100):
    batch = form_ids[i : i + 100]

    response = client.get('/forms/files', params={'form_id': ','.join(batch)})

    # Process response...
    # Rate limiting is handled automatically
```

### Error Handling

```python
from avela_client import create_client
import requests

client = create_client()

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

## Credentials

`create_client()` looks in three places and stops at the first one that has both
an ID and a secret:

| Order | Source                | Where it fits                               |
| ----- | --------------------- | ------------------------------------------- |
| 1     | Arguments in code     | `AvelaClient(client_id=..., client_secret=...)` |
| 2     | Environment variables | Servers, CI, containers, scheduled jobs     |
| 3     | OS keychain           | A person running recipes on a laptop        |

Environment variables come before the keychain on purpose, so a server or CI
job can override whatever a developer stored locally. Every recipe prints a
`Credentials:` line naming the source it used.

### OS keychain (recommended on a laptop)

```bash
python setup_credentials.py
```

Your operating system encrypts the credentials, and no file on disk holds the
secret. The prompt hides the secret as you type it (using `getpass`), so it
never reaches your shell history or terminal scrollback.

Where the values end up:

| Platform | Store              | Where to see them                  |
| -------- | ------------------ | ---------------------------------- |
| macOS    | login Keychain     | Keychain Access                    |
| Windows  | Credential Manager | Control Panel > Credential Manager |
| Linux    | Secret Service     | GNOME Keyring or KWallet           |

Useful variants:

```bash
python setup_credentials.py --show     # what is stored, never prints the secret
python setup_credentials.py --list     # profiles stored on this machine
python setup_credentials.py --delete   # remove
```

The keychain needs an unlocked desktop session. Use environment variables for
cron jobs, CI, containers, and headless servers.

### Environment variables (recommended for servers and CI)

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

Secret managers fill the same variables, keeping the secret out of your shell
history and off disk:

```bash
# AWS Secrets Manager
export AVELA_CLIENT_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id avela/api --query SecretString --output text)

# 1Password
op run --env-file=op.env -- python avela_api_client.py
```

### What about config.json?

`config.json` files hold a recipe's non-secret settings, such as an output
folder or an enrollment period id. Credentials in one are ignored, and a note
says so. If yours still holds a `client_secret`, store it with
`setup_credentials.py`, delete it from the file, and rotate the secret, since a
plaintext copy has been sitting on disk.

## When It Refuses To Run

The client fails rather than guessing, because every guess would mean using
credentials you did not ask for.

| Situation                            | What happens                  |
| ------------------------------------ | ----------------------------- |
| Profile named, nothing stored for it | Error naming the profile      |
| Client ID set without its secret     | Error, set both or unset both |
| No environment set anywhere          | Uses `uat` and prints a note  |
| Environment is not a real one        | Error listing the valid names |

## Working With Several Clients

Give each client a profile name. A profile renames every source above, so
credentials for different clients never collide.

Store one profile per client:

```bash
python setup_credentials.py --profile district-a
python setup_credentials.py --profile district-b
```

Then pick one per run:

```bash
python avela_api_client.py --profile district-a
python avela_api_client.py --profile district-b
```

...or in code:

```python
from avela_client import create_client

district_a = create_client(profile='district-a')
district_b = create_client(profile='district-b')

# Both clients are usable at the same time in one process
district_a.get('/forms')
district_b.get('/forms')
```

...or set one for a whole shell session:

```bash
export AVELA_PROFILE=district-a
```

The `--profile` flag always beats `AVELA_PROFILE`.

### What a profile changes

Using `district-a` as the example:

| Source               | Default               | Profile `district-a`             |
| -------------------- | --------------------- | -------------------------------- |
| Client ID variable   | `AVELA_CLIENT_ID`     | `AVELA_DISTRICT_A_CLIENT_ID`     |
| Secret variable      | `AVELA_CLIENT_SECRET` | `AVELA_DISTRICT_A_CLIENT_SECRET` |
| Environment variable | `AVELA_ENVIRONMENT`   | `AVELA_DISTRICT_A_ENVIRONMENT`   |
| Keychain service     | `avela-api`           | `avela-api:district-a`           |
| Settings file        | `config.json`         | `config.district-a.json`         |

Each profile is a separate keychain entry. It appears as its own item in Keychain
Access or Credential Manager, and you can delete it on its own.

Profile names are lowercased, and any run of characters that are not letters or
numbers becomes a dash. `District A` becomes `district-a`, and its variable
prefix is `AVELA_DISTRICT_A_`.

A profile reads only its own names, so no profile can pick up the default
credentials by accident.

### Which client am I actually talking to?

Check what the client picked before you run anything destructive. None of these
values contain the secret:

```python
client = create_client(profile='district-a')
print(client.profile)  # district-a
print(client.credential_source)  # keychain (avela-api:district-a)
print(client.environment)  # prod
```

## Configuration

### Environments

`prod`, `staging`, `uat`, `qa`, `dev`, `dev2`. You pick the environment name;
the client builds the Customer API and login URLs for it, so you never type a
hostname.

## Using in a Recipe

1. Add to your recipe's `requirements.txt`:
   ```
   -e ../../shared/python
   ```

2. Import in your script:
   ```python
   from avela_client import AvelaClient, create_client
   ```

3. Store your credentials once with `python ../../shared/python/setup_credentials.py`,
   or export `AVELA_CLIENT_ID` and `AVELA_CLIENT_SECRET`. See [Credentials](#credentials).

4. Accept a `--profile` flag in your script and pass it to
   `create_client(profile=...)` so the recipe works for several clients.

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

- `requests>=2.28.0` for HTTP calls
- `backoff>=2.2.0` for retries with growing waits
- `keyring>=24.0.0` for OS keychain storage

Installing this package installs all of them, so the keychain works with no
extra step.
