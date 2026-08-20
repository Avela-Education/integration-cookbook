# Offer Status Update - Python

## Overview

This recipe updates offer statuses (accept or decline) in bulk using the Avela Customer API v2. It reads offer IDs and actions from a CSV file, signs in with OAuth2, and calls the single offer status endpoint.

## Prerequisites

- Python 3.10 or higher
- Avela M2M (machine-to-machine) API credentials (client ID and secret)
- Network access to Avela API endpoints
- Basic understanding of REST APIs and CSV files

## Installation

1. Navigate to this recipe directory:
   ```bash
   cd api/offers-update-status-python
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

You need three values from Avela:

| Value         | Description                                       |
| ------------- | ------------------------------------------------- |
| Client ID     | Your OAuth2 client ID (provided by Avela)         |
| Client secret | Your OAuth2 client secret (provided by Avela)     |
| Environment   | Target environment: `dev`, `qa`, `uat`, or `prod` |

On a laptop, store them once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for the three values, hides the secret as you type it, and stores it encrypted. Add `--show`, `--list`, or `--delete` to see or remove what is stored.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=dev
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python offer_status_client.py --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

## Usage

```bash
# Run with default sample_offers.csv
python offer_status_client.py

# Use a specific CSV file
python offer_status_client.py --csv /path/to/offers.csv

# Dry run - see what would happen without making changes
python offer_status_client.py --dry-run

# Use a named profile
python offer_status_client.py --profile district-a
```

## What This Example Does

1. **Finds your credentials** in the first place that has them (environment variables, then the OS keychain)
2. **Authenticates** with Avela's OAuth2 endpoint using client credentials flow
3. **Reads the CSV file** and validates each row has a valid offer_id and action
4. **Groups offers by action** (accept vs decline) for efficient API calls
5. **Calls the API** with `PUT /forms/offers/status` for each group
6. **Reports results** showing successful and failed updates

## Expected Output

```
================================================================================
AVELA OFFER STATUS UPDATE - ACCEPT/DECLINE FROM CSV
================================================================================

Authenticating with Avela API (dev)...
Authentication successful! Token expires in 86400 seconds.

Read 2 updates from CSV file

Processing 2 offer update(s)...
  - 1 to accept
  - 1 to decline

Accepting 1 offer(s)...
  - 38ef384c-739d-4cf6-a319-c84d4ac62f8b
  Successfully accepted 1 offer(s)

Declining 1 offer(s)...
  - 833c3c9d-ba46-4539-9b69-9281b98c2f61
  Successfully declined 1 offer(s)

================================================================================
RESULTS
================================================================================
Successful updates: 2
Failed updates: 0
Total: 2
================================================================================
```

## CSV Format

| Column     | Description           |
| ---------- | --------------------- |
| `offer_id` | UUID of the offer     |
| `action`   | `accept` or `decline` |

Example:
```csv
offer_id,action
38ef384c-739d-4cf6-a319-c84d4ac62f8b,accept
833c3c9d-ba46-4539-9b69-9281b98c2f61,decline
```

## Offer Statuses

| Status       | Description                                             |
| ------------ | ------------------------------------------------------- |
| **Offered**  | Starting state, the offer has gone to the family        |
| **Accepted** | Family accepted the offer                               |
| **Declined** | Family declined the offer                               |
| **Revoked**  | Admin revoked the offer (not available via this script) |

This script can change offers to `Accepted` or `Declined`. The API allows moving between these states (Accepted to Declined, for example), though your organization's policies may not.

> [!NOTE]
> For large batches (1000+ offers), consider splitting your CSV into smaller files to avoid timeout issues.

## Finding Offer IDs

You can find offer IDs in the Avela Admin UI under Forms → Offers tab, or via database query:

```sql
SELECT offer.id, offer.status, school.name
FROM offer
JOIN school ON school.id = offer.school_id
WHERE offer.status = 'Offered'
  AND offer.deleted_at IS NULL;
```

## Key Concepts

### OAuth2 Client Credentials Flow

This recipe uses the OAuth2 "client credentials" grant type for machine-to-machine authentication:

1. Send `client_id` and `client_secret` to the token endpoint
2. Receive an access token (valid for 24 hours)
3. Include the token in API requests: `Authorization: Bearer {token}`

The login request also carries an audience value for the target environment. The shared client builds it, so you never type it.

### Unified Status Endpoint

Instead of separate accept and decline endpoints, Customer API v2 has one endpoint with a `status` field. New statuses can be added later without new endpoints, and your code stays shorter.

### Batch Processing

The script groups offers by action (accept/decline) and sends them in batches to the API. This is more efficient than individual calls but means all offers in a batch succeed or fail together.

## Common Issues

**"No credentials found"**
- Nothing the script checked had both an id and a secret. The error message lists both options
- Quickest fix on a laptop: `python ../../shared/python/setup_credentials.py`
- On a server or in CI: export `AVELA_CLIENT_ID`, `AVELA_CLIENT_SECRET`, and `AVELA_ENVIRONMENT`

**"Authentication failed"**
- Verify the client id and secret are correct in whichever source you set up
- Check where they came from. The script reports it as `client.credential_source`
- Ensure the environment matches where your credentials were issued
- Check for extra spaces in the values

**Profile has nothing stored**
- Run `python ../../shared/python/setup_credentials.py --list` to see stored profiles
- Store the missing one with `--profile <name>`
- Profile names become lowercase, and anything that is not a letter or a number turns into `-`, so `District A` becomes `district-a`

**"Invalid action" warning**
- CSV action column must be exactly `accept` or `decline` (case-insensitive)

**"Missing offer_id" warning**
- Each CSV row must have a non-empty offer_id column

**Timeout errors with large batches**
- Split your CSV into files with fewer than 1000 offers each

## API Endpoint

### PUT /forms/offers/status

Updates the status of one or more offers.

**Request:**
```json
{
  "offers": [
    { "offer_id": "38ef384c-739d-4cf6-a319-c84d4ac62f8b" },
    { "offer_id": "833c3c9d-ba46-4539-9b69-9281b98c2f61" }
  ],
  "status": "Accepted"
}
```

| Field    | Type   | Description                     |
| -------- | ------ | ------------------------------- |
| `offers` | array  | List of objects with `offer_id` |
| `status` | string | `"Accepted"` or `"Declined"`    |

**Response (success):**
```json
{
  "data": {
    "success": true
  }
}
```

**Response (failure):**
```json
{
  "data": {
    "success": false
  }
}
```

## Security Best Practices

1. **Never put credentials in a file** - The keychain and environment variables keep the secret off disk entirely
2. **Use environment-appropriate credentials** - Don't use prod credentials for testing
3. **Rotate secrets regularly** - Request new credentials if you suspect exposure
4. **Validate input data** - Review CSV contents before running against production
5. **Use dry-run first** - Always test with `--dry-run` before making real changes
6. **Limit access** - Only share credentials with authorized team members
