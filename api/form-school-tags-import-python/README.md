# Form-School Tags CSV Import

Import form-school tag assignments from a CSV file via the Avela Customer API.

## Prerequisites

- Python 3.10+
- Client ID and Client Secret from Avela

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
# Import all tags from CSV
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
```

## Output

```
Authenticating with Avela API (prod)...
✓ Authentication successful

Reading CSV: tags.csv
✓ Found 1,500 rows to process

Fetching enrollment period from form: e4c2f10d...
✓ Enrollment period: 26f92532...
Fetching available tags...
✓ Found 15 tags

Processing...
  500/1500 (33%)...
  1000/1500 (67%)...
  1500/1500 (100%)

Results:
  Inserted: 1,200
  Already existed: 280
  Errors: 20

Errors:
  Line 45: Form, school, or tag not found (404)
  Line 89: Tag 'Unknown Tag' not found. Available: eligible for lottery, ...
```

**Note:** Row numbers refer to CSV line numbers (line 1 = header, line 2 = first data row).

## How It Works

1. **Authentication** - Gets an access token using your API credentials
2. **Read CSV** - Loads form IDs, school IDs, and tag names from your CSV
3. **Fetch Enrollment Period** - Gets the enrollment period from the first form
4. **Fetch Tags** - Loads all available tags for that enrollment period into a cache
5. **Process Rows** - For each row, resolves the tag name to its UUID and calls the API

Tag name matching is case-insensitive ("Eligible For Lottery" matches "eligible for lottery").

## Troubleshooting

| Error | Cause | Solution |
| ----- | ----- | -------- |
| `Unauthorized (401)` | Invalid credentials or expired token | Check client_id and client_secret in config.json |
| `Form not found` | First form ID in CSV doesn't exist | Verify the form UUID is correct |
| `Tag 'xyz' not found` | Tag name doesn't match any available tag | Check spelling, the error shows available tags |
| `Form, school, or tag not found (404)` | Resource doesn't exist in the system | Verify the form and school UUIDs are correct |
| `Configuration file not found` | Missing config.json | Copy config.example.json to config.json |

## API Endpoints

This script uses the following API endpoints:

**GET /forms/{form_id}** - Fetch form to get enrollment period
**GET /tags** - Fetch all tags for the enrollment period

**POST /tags/forms/{form_id}/schools/{school_id}** - Add tag to form-school
```
Authorization: Bearer <token>
Content-Type: application/json

{"tag_id": "uuid-string"}
```

**Responses:**
- `201` with `{"affected_rows": 1}` - tag added
- `201` with `{"affected_rows": 0}` - tag already exists (silently skipped)
- `404` - form, school, or tag not found

**DELETE /tags/forms/{form_id}/schools/{school_id}** - Remove tag from form-school (used with `--delete` flag)
```
Authorization: Bearer <token>
Content-Type: application/json

{"tag_id": "uuid-string"}
```

**Responses:**
- `200` with `{"affected_rows": 1}` - tag removed
- `200` with `{"affected_rows": 0}` - tag was not present
- `404` - form, school, or tag not found
