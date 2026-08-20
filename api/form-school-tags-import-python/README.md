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
```

## Configuration

On a laptop, store your credentials once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for your client id, client secret, and environment, hides the secret as you type it, and stores it encrypted. Add `--show`, `--list`, or `--delete` to see or remove what is stored.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python form_school_tags_import.py tags.csv --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

**Environment values:**

The script builds the Customer API and login URLs from the environment name
stored with your credentials, so you never type a hostname.

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

**Important:** All forms in the CSV must belong to the same enrollment period. The script reads the available tags from the first form's enrollment period and uses them for every row. If your CSV mixes enrollment periods, the tag lookup can fail or match the wrong tag.

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

# Use a named credential profile
python form_school_tags_import.py tags.csv --profile district-a
```

### Batch vs Sequential Mode

By default, the script uses **batch mode**, sending up to 100 operations per API request. That is much faster for large imports:

| Rows   | Sequential (~3.3s/row) | Batch (100/request) |
| ------ | ---------------------- | ------------------- |
| 100    | ~5.5 min               | ~1 request (~1s)    |
| 1,000  | ~55 min                | ~10 requests (~10s) |
| 6,000+ | ~5.9 hours             | ~60 requests (~1m)  |

Use `--sequential` for the older one at a time behavior, which helps when you are debugging or when the batch endpoint is unavailable.

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

| Error                                           | Cause                                             | Solution                                                                                                                 |
| ----------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `Unauthorized (401)`                            | Invalid credentials or expired token              | Check the client id and secret in whichever source you set up; `client.credential_source` reports which one was used     |
| `You are not authorized to perform this action` | Missing API permissions                           | Ensure credentials have `tag:read`, `tag:create` permissions                                                             |
| `Form not found`                                | Form doesn't exist or credentials can't access it | Verify form UUID and that credentials have access to this organization                                                   |
| `Tag 'xyz' not found`                           | Tag name doesn't match any available tag          | Check spelling, the error shows available tags                                                                           |
| `Form, school, or tag not found (404)`          | Resource doesn't exist in the system              | Verify the form and school UUIDs are correct                                                                             |
| `No credentials found`                          | Nothing checked had both an id and a secret       | Store them with `python ../../shared/python/setup_credentials.py`, or export `AVELA_CLIENT_ID` and `AVELA_CLIENT_SECRET` |
| `No credentials found` with `--profile`         | Nothing stored for that profile name              | List what exists with `python ../../shared/python/setup_credentials.py --list`, then store the missing profile           |

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
