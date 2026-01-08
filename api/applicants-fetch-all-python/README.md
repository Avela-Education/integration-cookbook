# Fetch All Applicants - Python

A comprehensive Python script demonstrating how to authenticate with the Avela API and retrieve all applicants with automatic pagination and CSV export.

## Overview

This example shows how to:
- Authenticate using OAuth2 client credentials
- Fetch applicants from the Avela Customer API v2
- Handle automatic pagination for large datasets
- Export data to CSV format
- Display formatted console output

Perfect for generating reports, data analysis, or migrating applicant data.

## Prerequisites

- Python 3.10 or higher
- Avela API credentials (Client ID and Client Secret)
- `pip` package manager (included with Python 3.4+)

## Setup Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid dependency conflicts with other Python projects.

### Create Virtual Environment

**On macOS/Linux:**
```bash
# Navigate to this directory
cd api/applicants-fetch-all-python

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

**On Windows:**
```bash
# Navigate to this directory
cd api/applicants-fetch-all-python

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) in your command prompt
```

### Verify Activation

When activated, you'll see `(venv)` at the start of your command prompt:
```
(venv) user@computer:~/integration-cookbook/api/applicants-fetch-all-python$
```

### Deactivate (When Done)

To exit the virtual environment when you're finished:
```bash
deactivate
```

**Note:** You need to activate the virtual environment each time you open a new terminal session.

## Installation

```bash
# Navigate to this directory (if not already there)
cd api/applicants-fetch-all-python

# (Recommended) Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration:
```bash
cp config.example.json config.json
```

2. Edit `config.json` with your credentials:
```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "environment": "prod"
}
```

**Configuration Options:**
- `client_id` - Your OAuth2 client ID (provided by Avela)
- `client_secret` - Your OAuth2 client secret (keep secure!)
- `environment` - Target environment: `prod`, `qa`, `uat`, `dev`, or `dev2`

## Usage

```bash
python avela_api_client.py
```

## What This Example Does

1. **Loads Configuration** - Reads credentials from `config.json`
2. **Prompts for Filter Options** - Asks if you want all applicants or specific ones
3. **Authenticates** - Obtains an OAuth2 access token (valid for 24 hours)
4. **Fetches Applicants** - Retrieves applicants with automatic pagination
5. **Displays Summary** - Shows a formatted table in the console
6. **Exports to CSV** - Creates a timestamped CSV file with all applicant data

## Expected Output

### Console Output
```
================================================================================
AVELA API INTEGRATION - APPLICANTS EXPORT
================================================================================

How would you like to fetch applicants?
[1] Fetch all applicants
[2] Filter by specific reference IDs

Enter your choice (1 or 2): 1

Authenticating with Avela API (prod)...
✓ Authentication successful! Token expires in 86400 seconds.

Fetching applicants from prod environment...
  Fetching page 1 (offset: 0)... Retrieved 150 applicants

✓ Total applicants retrieved: 150

========================================================
APPLICANTS SUMMARY (150 total)
========================================================
Reference ID    Name                           Email                               Birth Date   City, State
------------------------------------------------------------------------------------------------------------------------
450156          John A Doe                     john.doe@example.com                2012-02-12   Tulsa, OK
450157          Jane Smith                     jane.smith@example.com              2011-05-23   Boston, MA
...
========================================================

✓ Exported 150 applicants to: avela_applicants_20251110_143022.csv

✓ Integration completed successfully!
================================================================================
```

### CSV Export

The script generates a timestamped CSV file containing all applicant fields:

**Filename format:** `avela_applicants_YYYYMMDD_HHMMSS.csv`

**Columns included:**
- `reference_id` - External reference identifier
- `first_name`, `middle_name`, `last_name` - Full name
- `birth_date` - Date of birth (YYYY-MM-DD)
- `email_address` - Primary email
- `phone_number` - Contact phone (format: +12135551212)
- `street_address`, `street_address_line_2`, `city`, `state`, `zip_code` - Address
- `preferred_language` - Language preference
- `email_okay`, `sms_okay` - Communication preferences
- `active` - Active status
- `person_type` - Type of person record
- `created_at`, `updated_at`, `deleted_at` - Timestamps
- `id` - Unique internal identifier (UUID)

## Key Concepts

### OAuth2 Authentication
The script uses the **client credentials flow**:
1. Sends client ID and secret to auth endpoint
2. Receives access token (valid 24 hours)
3. Uses token for all API requests

```python
# Authentication happens automatically in the script
token = get_access_token(client_id, client_secret, environment)
```

### Automatic Pagination
Handles large datasets by fetching in batches:
- Maximum 1000 records per request
- Automatically fetches additional pages
- Continues until all records retrieved

```python
# Pagination is handled automatically
applicants = get_applicants(token, environment)  # Gets ALL applicants
```

### Error Handling
Robust error handling for common issues:
- Invalid credentials → Clear error message
- Network issues → Timeout and retry guidance
- API errors → Detailed error response
- Missing config → Helpful setup instructions

## Common Issues

### "Configuration file not found"
**Problem:** `config.json` doesn't exist

**Solution:**
```bash
cp config.example.json config.json
# Edit config.json with your credentials
```

### "Authentication failed"
**Problem:** Invalid credentials or wrong environment

**Solutions:**
1. Verify `client_id` and `client_secret` in `config.json`
2. Confirm you're using the correct environment (usually `prod`)
3. Check for extra spaces or quotes in credentials
4. Contact your Avela administrator to verify credentials are active

### "No applicants found"
**Problem:** Query returned zero results

**Possible causes:**
1. You're using a test environment with no data
2. The `reference_ids` filter doesn't match any records
3. Your credentials don't have access to applicant data

**Solution:**
- Remove `reference_ids` filter to fetch all applicants
- Verify the correct environment in config
- Check permissions with your administrator

### Module not found errors
**Problem:** Dependencies not installed

**Solution:**
```bash
# Make sure virtual environment is activated (if using)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Virtual environment not activating
**Problem:** `source venv/bin/activate` doesn't work

**Solutions:**

**On Windows (PowerShell):**
```powershell
# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate:
venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
# Make sure you're in the correct directory
cd api/applicants-fetch-all-python

# Try with full path
source ./venv/bin/activate
```

### Wrong Python version in virtual environment
**Problem:** Virtual environment using wrong Python version

**Solution:**
```bash
# Remove old virtual environment
rm -rf venv  # On Windows: rmdir /s venv

# Create with specific Python version
python3.10 -m venv venv  # Use Python 3.10 or higher

# Activate and reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
```

## Customization Examples

### Filter by Reference IDs

When you run the script, you'll be prompted to choose how to fetch applicants:

```
How would you like to fetch applicants?
[1] Fetch all applicants
[2] Filter by specific reference IDs

Enter your choice (1 or 2): 2

Enter reference IDs separated by commas.
Example: 450156,450157,450158

Reference IDs: 450156, 450157, 450158

✓ Will filter by 3 reference ID(s)
```

This allows you to fetch only specific applicants without editing code or config files.

### Change CSV Filename
Modify the `export_to_csv()` call in `main()`:
```python
export_to_csv(applicants, filename='my_custom_report.csv')
```

### Add Data Processing
Process applicants before export:
```python
# After fetching applicants, before export
for applicant in applicants:
    # Example: Format phone numbers
    phone = applicant.get('phone_number')
    if phone:
        applicant['formatted_phone'] = f"({phone[2:5]}) {phone[5:8]}-{phone[8:]}"
```

## API Endpoints Used

### Authentication
- **Endpoint:** `https://{env}.auth.avela.org/oauth/token`
- **Method:** POST
- **Purpose:** Obtain OAuth2 access token

### List Applicants
- **Endpoint:** `https://{env}.execute-api.apply.avela.org/api/rest/v2/applicants`
- **Method:** GET
- **Purpose:** Retrieve applicant data
- **Pagination:** Automatic (max 1000 per request)

## Related Examples

- [Update Forms from CSV (Python)](../forms-update-csv-python/) - Bulk update form data
- [Search and Filter Applicants](../) - _(coming soon)_ Advanced filtering
- [Batch Operations](../) - _(coming soon)_ Update multiple applicants

## API Reference

- [Applicants Endpoint Documentation](https://docs.avela.org/api/v2/applicants)
- [Authentication Guide](https://docs.avela.org/authentication)
- [Rate Limits](https://docs.avela.org/rate-limits)

## Security Best Practices

- ✅ Never commit `config.json` to version control
- ✅ Use environment variables in production systems
- ✅ Rotate credentials regularly
- ✅ Store credentials securely (use secrets management)
- ✅ Limit credential access to authorized personnel

## Support

- Report issues: [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- Ask questions: [GitHub Discussions](https://github.com/Avela-Education/integration-cookbook/discussions)
- Email: [api-support@avela.org](mailto:api-support@avela.org)

## Contributing

Found a way to improve this example? We welcome contributions! See our [Contributing Guide](../../CONTRIBUTING.md).

---

**Complexity Level:** 🟢 Beginner
**Language:** Python 3.10+
**API Version:** v2
