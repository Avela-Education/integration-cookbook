# Download Form Files - Python

A comprehensive Python script demonstrating how to retrieve file upload questions from forms and download all associated file attachments using pre-signed URLs.

## Overview

This example shows how to:
- Authenticate using OAuth2 client credentials
- Call the `GET /forms/files` endpoint to get file metadata and download URLs
- Batch retrieve files across multiple forms (up to 100 per request)
- Download files using pre-signed URLs
- Organize downloaded files by form ID and question

Perfect for backing up form attachments, migrating files, or processing uploaded documents.

## Prerequisites

- Python 3.10 or higher
- Avela API credentials (Client ID and Client Secret)
- Form IDs for the forms containing file uploads
- `pip` package manager (included with Python 3.4+)

## Setup Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid dependency conflicts with other Python projects.

### Create Virtual Environment

**On macOS/Linux:**
```bash
# Navigate to this directory
cd api/forms-download-files-python

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

**On Windows:**
```bash
# Navigate to this directory
cd api/forms-download-files-python

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# You should see (venv) in your command prompt
```

### Verify Activation

When activated, you'll see `(venv)` at the start of your command prompt:
```
(venv) user@computer:~/integration-cookbook/api/forms-download-files-python$
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
cd api/forms-download-files-python

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

2. Edit `config.json` with your credentials and form IDs:
```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "environment": "prod",
  "form_ids": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987fcdeb-51a2-3b4c-d5e6-f78901234567"
  ],
  "output_dir": "downloaded_files"
}
```

**Configuration Options:**
- `client_id` - Your OAuth2 client ID (provided by Avela)
- `client_secret` - Your OAuth2 client secret (keep secure!)
- `environment` - Target environment: `prod`, `qa`, `uat`, or `dev`
- `form_ids` - Array of form UUIDs to download files from (max 100)
- `output_dir` - (Optional) Custom output directory name

## Usage

```bash
python download_form_files.py
```

## What This Example Does

1. **Loads Configuration** - Reads credentials and form IDs from `config.json`
2. **Authenticates** - Obtains an OAuth2 access token (valid for 24 hours)
3. **Fetches File Metadata** - Calls the batch endpoint to get all file information
4. **Downloads Files** - Iterates through responses and downloads each file
5. **Organizes Output** - Saves files in `output_dir/form_id/question_key/filename`
6. **Displays Summary** - Shows download statistics

## Expected Output

### Console Output
```
============================================================
AVELA API INTEGRATION - FORM FILES DOWNLOAD
============================================================

Configuration loaded:
  Environment: prod
  Form IDs: 2 form(s)

Authenticating with Avela API (prod)...
Authentication successful! Token expires in 86400 seconds.

Fetching file information for 2 form(s)...
Received responses for 2 form(s)

Downloading files to: /path/to/form_files_20251107_143022
------------------------------------------------------------

Form: 123e4567-e89b-12d3-a456-426614174000
  Question: proof_of_residency (2 file(s))
    - utility_bill.pdf... OK
    - lease_agreement.pdf... OK
  Question: birth_certificate (1 file(s))
    - birth_cert_scan.jpg... OK

Form: 987fcdeb-51a2-3b4c-d5e6-f78901234567
  Question: proof_of_residency (1 file(s))
    - drivers_license.png... OK

============================================================
DOWNLOAD SUMMARY
============================================================
Forms processed:  2
Total files:      4
Downloaded:       4
Failed:           0
Skipped:          0

Files saved to: form_files_20251107_143022
============================================================

Integration completed successfully!
```

### Output Directory Structure

Files are organized by form ID and question key:

```
form_files_20251107_143022/
├── 123e4567-e89b-12d3-a456-426614174000/
│   ├── proof_of_residency/
│   │   ├── utility_bill.pdf
│   │   └── lease_agreement.pdf
│   └── birth_certificate/
│       └── birth_cert_scan.jpg
└── 987fcdeb-51a2-3b4c-d5e6-f78901234567/
    └── proof_of_residency/
        └── drivers_license.png
```

## Key Concepts

### The Get Form Files Endpoint

The `GET /rest/v2/forms/files` endpoint is a batch endpoint that:
- Accepts a comma-delimited list of form IDs (up to 100)
- Returns file upload questions from those forms
- Includes pre-signed download URLs for each uploaded file
- Returns a 207 Multi-Status response for batch results

```python
# Example API call
response = requests.get(
    f'{api_base}/forms/files',
    params={'form_id': 'uuid1,uuid2,uuid3'},
    headers={'Authorization': f'Bearer {token}'}
)
```

### Pre-signed URLs

Download URLs are pre-signed S3 URLs that:
- Provide temporary access to files without authentication
- Expire after a limited time (typically 1 hour)
- Should be downloaded promptly after retrieval

### Response Structure

The API returns responses for each form:

```json
{
  "responses": [
    {
      "status": "200",
      "form": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "questions": [
          {
            "id": "question-uuid",
            "key": "proof_of_residency",
            "type": "FileUpload",
            "answer": {
              "id": "answer-uuid",
              "files": [
                {
                  "id": "file-uuid",
                  "filename": "document.pdf",
                  "status": 1,
                  "download_url": "https://s3.amazonaws.com/...",
                  "error": null
                }
              ]
            }
          }
        ]
      }
    }
  ]
}
```

## Common Issues

### "Configuration file not found"
**Problem:** `config.json` doesn't exist

**Solution:**
```bash
cp config.example.json config.json
# Edit config.json with your credentials and form IDs
```

### "form_ids must be a non-empty list"
**Problem:** The `form_ids` field is missing or empty

**Solution:** Add form IDs to your config.json:
```json
{
  "form_ids": ["your-form-uuid-here"]
}
```

### "Maximum 100 form IDs allowed"
**Problem:** Too many form IDs in one request

**Solution:** Split your form IDs into batches of 100 or fewer:
```python
# Run the script multiple times with different form ID batches
```

### "No download URL"
**Problem:** Some files show "No download URL (status: X)"

**Possible causes:**
1. File is still being processed (status != 1)
2. File was deleted or expired
3. File upload failed

**Solution:** Check the file status in the Avela admin interface

### "Authentication failed"
**Problem:** Invalid credentials or wrong environment

**Solutions:**
1. Verify `client_id` and `client_secret` in `config.json`
2. Confirm you're using the correct environment (usually `prod`)
3. Check for extra spaces or quotes in credentials

### Module not found errors
**Problem:** Dependencies not installed

**Solution:**
```bash
# Make sure virtual environment is activated (if using)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Customization Examples

### Download to Custom Directory

Set the `output_dir` in config.json:
```json
{
  "output_dir": "/path/to/my/downloads"
}
```

### Process Only Specific Question Types

Modify the download loop to filter by question key:
```python
# Only download files from specific questions
allowed_questions = ['birth_certificate', 'proof_of_residency']

for question in questions:
    if question.get('key') not in allowed_questions:
        continue
    # ... download files
```

### Add Progress Reporting

For large downloads, track progress:
```python
import time
start_time = time.time()
# ... after downloads complete
elapsed = time.time() - start_time
print(f'Downloaded {stats["downloaded"]} files in {elapsed:.1f} seconds')
```

## API Endpoints Used

### Authentication
- **Endpoint:** `https://{env}.auth.avela.org/oauth/token`
- **Method:** POST
- **Purpose:** Obtain OAuth2 access token

### Get Form Files
- **Endpoint:** `https://{env}.execute-api.apply.avela.org/api/rest/v2/forms/files`
- **Method:** GET
- **Parameters:** `form_id` (comma-delimited, max 100)
- **Purpose:** Retrieve file metadata and pre-signed download URLs
- **Response:** 207 Multi-Status with per-form results

## Related Examples

- [Fetch All Applicants (Python)](../applicants-fetch-all-python/) - Export applicant data
- [Update Forms from CSV (Python)](../forms-update-csv-python/) - Bulk update form data

## API Reference

- [Forms Files Endpoint Documentation](https://docs.avela.org/api/v2/forms/files)
- [Authentication Guide](https://docs.avela.org/authentication)
- [Rate Limits](https://docs.avela.org/rate-limits)

## Security Best Practices

- Never commit `config.json` to version control
- Use environment variables in production systems
- Rotate credentials regularly
- Store credentials securely (use secrets management)
- Be careful with downloaded files - they may contain sensitive data
- Delete downloaded files securely when no longer needed

## Support

- Report issues: [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- Ask questions: [GitHub Discussions](https://github.com/Avela-Education/integration-cookbook/discussions)
- Email: [api-support@avela.org](mailto:api-support@avela.org)

## Contributing

Found a way to improve this example? We welcome contributions! See our [Contributing Guide](../../CONTRIBUTING.md).

---

**Complexity Level:** Beginner
**Language:** Python 3.10+
**API Version:** v2
