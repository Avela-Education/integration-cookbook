# Offer Status Update - Python

## Overview

This recipe demonstrates how to bulk update offer statuses (accept or decline) using the Avela Customer API v2. It reads offer IDs and actions from a CSV file, authenticates via OAuth2, and calls the unified offer status endpoint.

## Prerequisites

- Python 3.8 or higher
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

1. Copy the configuration template:
   ```bash
   cp config.example.json config.json
   ```

2. Edit `config.json` with your credentials:
   ```json
   {
     "client_id": "your_client_id",
     "client_secret": "your_client_secret",
     "environment": "dev"
   }
   ```

   | Field           | Description                                       |
   |-----------------|---------------------------------------------------|
   | `client_id`     | Your OAuth2 client ID (provided by Avela)         |
   | `client_secret` | Your OAuth2 client secret (provided by Avela)     |
   | `environment`   | Target environment: `dev`, `qa`, `uat`, or `prod` |

## Usage

```bash
# Run with default sample_offers.csv
python offer_status_client.py

# Use a specific CSV file
python offer_status_client.py --csv /path/to/offers.csv

# Dry run - see what would happen without making changes
python offer_status_client.py --dry-run
```

## What This Example Does

1. **Loads configuration** from `config.json` (client credentials and environment)
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
|------------|-----------------------|
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
|--------------|---------------------------------------------------------|
| **Offered**  | Initial state - offer has been made to the family       |
| **Accepted** | Family accepted the offer                               |
| **Declined** | Family declined the offer                               |
| **Revoked**  | Admin revoked the offer (not available via this script) |

This script can change offers to `Accepted` or `Declined`. The API allows transitioning between these states (e.g., Accepted → Declined), though organizational policies may restrict certain transitions.

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

The audience parameter must match the target environment's GraphQL endpoint.

### Unified Status Endpoint

Instead of separate accept/decline endpoints, Customer API v2 provides a single endpoint that accepts a `status` field. This makes the API more extensible (new statuses can be added without new endpoints) and simplifies client code.

### Batch Processing

The script groups offers by action (accept/decline) and sends them in batches to the API. This is more efficient than individual calls but means all offers in a batch succeed or fail together.

## Common Issues

**"Configuration file not found"**
- Run `cp config.example.json config.json` and edit with your credentials

**"Authentication failed"**
- Verify `client_id` and `client_secret` are correct
- Ensure `environment` matches where your credentials were provisioned
- Check for extra whitespace in config values

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
|----------|--------|---------------------------------|
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

1. **Never commit credentials** - `config.json` is gitignored for a reason
2. **Use environment-appropriate credentials** - Don't use prod credentials for testing
3. **Rotate secrets regularly** - Request new credentials if you suspect exposure
4. **Validate input data** - Review CSV contents before running against production
5. **Use dry-run first** - Always test with `--dry-run` before making real changes
6. **Limit access** - Only share credentials with authorized team members
