# Form-School Tags CSV Import

Import form-school tag assignments from a CSV file via the Avela Customer API.

## Prerequisites

- Python 3.10+
- Avela API credentials (Client ID and Client Secret)
- API credentials must have these permissions:
  - `form:read` - to fetch enrollment period from first form
  - `tag:read` - to fetch available tags for name lookup
  - `tag:create` - to add tags to form-school combinations
  - `tag:delete` - only needed if using `--delete` mode

## Installation

```bash
cd api/form-school-tags-import-python

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp config.example.json config.json
```

## Configuration

Edit `config.json` with your credentials:

```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "environment": "prod"
}
```

**Environment values:**

| Environment | API Base URL                                            | Token URL                                    |
| ----------- | ------------------------------------------------------- | -------------------------------------------- |
| `prod`      | `https://prod.execute-api.apply.avela.org/api/rest/v2`  | `https://auth.avela.org/oauth/token`         |
| `staging`   | `https://staging.execute-api.apply.avela.org/api/rest/v2` | `https://avela-staging.us.auth0.com/oauth/token` |
| `uat`       | `https://uat.execute-api.apply.avela.org/api/rest/v2`   | `https://uat.auth.avela.org/oauth/token`     |
| `qa`        | `https://qa.execute-api.apply.avela.org/api/rest/v2`    | `https://qa.auth.avela.org/oauth/token`      |
| `dev`       | `https://dev.execute-api.apply.avela.org/api/rest/v2`   | `https://dev.auth.avela.org/oauth/token`     |
| `dev2`      | `https://dev2.execute-api.apply.avela.org/api/rest/v2`  | `https://dev2.auth.avela.org/oauth/token`    |

## CSV Format

```csv
Form ID,School ID,Tag Name
e4c2f10d-b94a-49eb-b6b2-a129b0840f90,a1b2c3d4-e5f6-7890-abcd-ef1234567890,Eligible For Lottery
f5d3e20e-c05b-50fc-c7c3-b230c1951f01,b2c3d4e5-f6a7-8901-bcde-f12345678901,Ineligible for Lottery
```

**Column headers:**
- `Form ID` or `App ID` (UUID of the form)
- `School ID` (UUID of the school)
- `Tag Name` (display name of the tag, case-insensitive)

The script automatically looks up tag UUIDs from the API using the tag names in your CSV.

**Important:** All forms in the CSV must belong to the same enrollment period. The script fetches available tags from the first form's enrollment period and uses that for all rows. If your CSV contains forms from different enrollment periods, tag resolution may fail or produce unexpected results.

## Usage

```bash
# Import all tags from CSV (uses batch API by default)
python form_school_tags_import.py tags.csv

# Validate CSV and resolve tag names without modifying data
# (still authenticates and fetches form/tags from API)
python form_school_tags_import.py tags.csv --dry-run

# Test with first 10 rows
python form_school_tags_import.py tags.csv --limit 10

# Skip first 100 data rows (e.g., resume after fixing rows 1-100)
python form_school_tags_import.py tags.csv --start-row 100

# Remove tags instead of adding them (useful for resetting tests)
python form_school_tags_import.py tags.csv --delete

# Use single-item API calls instead of batch (slower, for debugging)
python form_school_tags_import.py tags.csv --sequential

# Custom batch size (default: 100, max: 100)
python form_school_tags_import.py tags.csv --batch-size 50
```

### Batch vs Sequential Mode

By default, the script uses **batch mode**, sending up to 100 operations per API request. This is dramatically faster for large imports:

| Rows   | Sequential (~3.3s/row) | Batch (100/request) |
| ------ | ---------------------- | ------------------- |
| 100    | ~5.5 min               | ~1 request (~1s)    |
| 1,000  | ~55 min                | ~10 requests (~10s) |
| 6,000+ | ~5.9 hours             | ~60 requests (~1m)  |

Use `--sequential` to fall back to the legacy one-at-a-time behavior (useful for debugging or if the batch endpoint is unavailable).

## Output

### Batch Mode (default)

```
BATCH MODE - Up to 100 operations per request

Reading CSV: tags.csv
Found 1,500 rows to process

Fetching enrollment period from form: e4c2f10d...
Enrollment period: 26f92532...
Fetching available tags...
Found 15 tags

Processing...
  Validated: 1,480 operations in 15 batch(es)
  Validation errors: 20 (will be skipped)
  Batch 1/15 (100/1,480 operations)...
  Batch 2/15 (200/1,480 operations)...
  ...
  Batch 15/15 (1,480/1,480 operations)...

Results:
  Inserted: 1,200
  Already existed: 280
  Errors: 20

Errors:
  Line 89: Tag 'Unknown Tag' not found. Available: eligible for lottery, ...
```

### Sequential Mode

```
SEQUENTIAL MODE - Using single-item API calls

Processing...
  500/1500 (33%)...
  1000/1500 (67%)...
  1500/1500 (100%)

Results:
  Inserted: 1,200
  Already existed: 280
  Errors: 20
```

**Note:** Row numbers refer to CSV line numbers (line 1 = header, line 2 = first data row).

## How It Works

1. **Authentication** - Gets an access token using your API credentials
2. **Read CSV** - Loads form IDs, school IDs, and tag names from your CSV
3. **Fetch Enrollment Period** - Gets the enrollment period from the first form
4. **Fetch Tags** - Loads all available tags for that enrollment period into a cache
5. **Validate & Batch** - Validates all rows (UUIDs, tag names), then groups into batches of up to 100
6. **Send Batches** - Sends each batch to the API; handles partial success per tag group

Tag name matching is case-insensitive ("Eligible For Lottery" matches "eligible for lottery").

## Troubleshooting

| Error | Cause | Solution |
| ----- | ----- | -------- |
| `Unauthorized (401)` | Invalid credentials or expired token | Check client_id and client_secret in config.json |
| `You are not authorized to perform this action` | Missing API permissions | Ensure credentials have `tag:read`, `tag:create` permissions |
| `Form not found` | Form doesn't exist or credentials can't access it | Verify form UUID and that credentials have access to this organization |
| `Tag 'xyz' not found` | Tag name doesn't match any available tag | Check spelling, the error shows available tags |
| `Form, school, or tag not found (404)` | Resource doesn't exist in the system | Verify the form and school UUIDs are correct |
| `Configuration file not found` | Missing config.json | Copy config.example.json to config.json |

## API Endpoints

This script uses the following API endpoints:

### Setup Endpoints

**GET /forms/{form_id}** - Fetch form to get enrollment period
**GET /tags** - Fetch all tags for the enrollment period

### Batch Endpoints (default)

**POST /tags/schools/batch** - Add tags in bulk (up to 100 per request)
```json
{
  "operations": [
    {"form_id": "uuid-1", "school_id": "uuid-a", "tag_id": "uuid-x"},
    {"form_id": "uuid-2", "school_id": "uuid-b", "tag_id": "uuid-x"}
  ]
}
```

**DELETE /tags/schools/batch** - Remove tags in bulk (used with `--delete` flag)

**Responses (207 Multi-Status):**
Results are grouped by `tag_id`:
```json
{
  "responses": [
    {"status": "201", "tag_id": "uuid-x", "affected_rows": 2, "requested": 2, "fully_applied": true},
    {"status": "404", "tag_id": "uuid-y", "error": "Tag not found", "requested": 1}
  ]
}
```

- `fully_applied: true` - all operations for this tag succeeded
- `fully_applied: false` - some operations skipped (duplicates or invalid pairs)
- One tag group failing does not affect others in the same batch

### Sequential Endpoints (with `--sequential` flag)

**POST /tags/forms/{form_id}/schools/{school_id}** - Add a single tag
```json
{"tag_id": "uuid-string"}
```

**DELETE /tags/forms/{form_id}/schools/{school_id}** - Remove a single tag (with `--delete`)
```json
{"tag_id": "uuid-string"}
```
