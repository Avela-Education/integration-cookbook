# Download Form Files - Python

Find the file upload questions on a set of forms and download every attached file.

## Overview

This example shows how to:
- Authenticate using OAuth2 client credentials
- Call the `GET /forms/files` endpoint to get file metadata and download URLs
- Automatically batch requests for any number of forms (100 per API call)
- Download files using pre-signed URLs
- Organize downloaded files by form ID and question

Use it to back up form attachments, move files somewhere else, or process uploaded documents.

## See It In Action

[![Watch the AI Agent Walkthrough](https://img.youtube.com/vi/qA-o_W8KdQQ/maxresdefault.jpg)](https://youtu.be/qA-o_W8KdQQ)

▶️ **[Watch the Video](https://youtu.be/qA-o_W8KdQQ)** - See how to use an AI agent to automate file downloads

## Prerequisites

- Python 3.10 or higher
- Avela API credentials (Client ID and Client Secret)
- Form IDs for the forms containing file uploads
- `pip` package manager (included with Python 3.4+)

## Setup Virtual Environment (Recommended)

A virtual environment keeps this recipe's dependencies separate from your other Python projects.

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

### 1. Store your credentials

You need your OAuth2 client id and client secret from Avela, plus the environment you are working in: `prod`, `qa`, `uat`, or `dev`.

On a laptop, store them once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for the three values, hides the secret as you type it, and stores it encrypted. Add `--show`, `--list`, or `--delete` to see or remove what is stored.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### 2. Set the output directory (optional)

`output_dir` is a setting, not a secret, so it stays in `config.json` no matter where your credentials live. Create the file with just that key and leave the credential fields out:

```json
{
  "output_dir": "downloaded_files"
}
```

The script ignores a `config.json` that has no client id and secret, so a settings only file prints no plaintext warning.

### 3. Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python download_form_files.py form_ids.txt --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every credential source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`.

Settings such as `output_dir` come from `config.json`, with `config.district-a.json` layered over it when you run with a profile. Credentials never come from these files. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

### 4. Create a form IDs file

One UUID per line:

```bash
cp form_ids.example.txt form_ids.txt
```

Example `form_ids.txt`:
```
# Lines starting with # are comments
123e4567-e89b-12d3-a456-426614174000
987fcdeb-51a2-3b4c-d5e6-f78901234567
```

## Usage

```bash
# Pass form IDs file as argument
python download_form_files.py form_ids.txt

# Or run without argument to be prompted
python download_form_files.py

# Use a named profile
python download_form_files.py form_ids.txt --profile district-a
```

## What This Example Does

1. **Finds Credentials** - Takes them from the first place that has them (environment variables, then the OS keychain)
2. **Loads Form IDs** - Reads form IDs from the specified text file
3. **Authenticates** - Obtains an OAuth2 access token (valid for 24 hours)
4. **Fetches File Metadata** - Automatically batches API calls (100 forms per request)
5. **Downloads Files** - Iterates through responses and downloads each file
6. **Organizes Output** - Saves files in `output_dir/form_<form_id>/question_key/filename`
7. **Displays Summary** - Shows download statistics

## Expected Output

### Console Output
```
============================================================
AVELA API INTEGRATION - FORM FILES DOWNLOAD
============================================================

Configuration loaded:
  Environment: prod
  Form IDs file: form_ids.txt
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
├── form_123e4567-e89b-12d3-a456-426614174000/
│   ├── proof_of_residency/
│   │   ├── utility_bill.pdf
│   │   └── lease_agreement.pdf
│   └── birth_certificate/
│       └── birth_cert_scan.jpg
└── form_987fcdeb-51a2-3b4c-d5e6-f78901234567/
    └── proof_of_residency/
        └── drivers_license.png
```

## Key Concepts

### The Get Form Files Endpoint

The `GET /rest/v2/forms/files` endpoint is a batch endpoint that:
- Accepts a comma-delimited list of form IDs
- Returns file upload questions from those forms
- Includes pre-signed download URLs for each uploaded file
- Returns a 207 Multi-Status response for batch results

```python
# Example API call
response = requests.get(
    f'{api_base}/forms/files',
    params={'form_id': 'uuid1,uuid2,uuid3'},
    headers={'Authorization': f'Bearer {token}'},
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

### "No credentials found"
**Problem:** Nothing the script checked had both a client id and a client secret. The error message lists both options.

**Solution:** set up any one of them.
```bash
# OS keychain (recommended on a laptop)
python ../../shared/python/setup_credentials.py

# Environment variables (recommended for servers, CI, and containers)
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

If you passed `--profile`, check that the profile actually has credentials stored: `python ../../shared/python/setup_credentials.py --list`.

### "Form IDs file not found"
**Problem:** The specified form IDs file doesn't exist

**Solution:**
```bash
cp form_ids.example.txt form_ids.txt
# Edit form_ids.txt with your form UUIDs (one per line)
```

### "No form IDs found"
**Problem:** The form IDs file is empty or contains only comments

**Solution:** Add form UUIDs to your form IDs file (one per line)

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
1. Verify the client id and secret in whichever source you set up
2. Check where they came from. The script reports it as `client.credential_source`
3. Confirm you're using the correct environment (usually `prod`)
4. Check for extra spaces or quotes in credentials

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
- **Endpoint (prod):** `https://auth.avela.org/oauth/token`
- **Endpoint (non-prod):** `https://{env}.auth.avela.org/oauth/token`
- **Method:** POST

### Get Form Files
- **Endpoint:** `https://{env}.execute-api.apply.avela.org/api/rest/v2/forms/files`
- **Method:** GET
- **Parameters:** `form_id` (comma-delimited list of form UUIDs)
- **Purpose:** Retrieve file metadata and pre-signed download URLs
- **Response:** 207 Multi-Status with per-form results

## Advanced Version

Need more features? The [advanced version](./advanced/) includes:

- **CSV input** - Use student names for folder organization
- **Resume support** - Continue interrupted downloads
- **Retry logic** - Handle network failures gracefully
- **Question filtering** - Download only specific file types

See [advanced/README.md](./advanced/README.md) for details.

## Related Examples

- [Fetch All Applicants (Python)](../applicants-fetch-all-python/) - Export applicant data
- [Update Forms from CSV (Python)](../forms-update-csv-python/) - Bulk update form data

## API Reference

- [Forms Files Endpoint Documentation](https://prod.api-docs.avela.dev/v2/index.html)
- [Rate Limits](../../shared/python/README.md#rate-limits)

## Security Best Practices

- Prefer the OS keychain on a laptop and environment variables in production; both keep the secret out of the repository
- Keep secrets out of files; credentials live in the keychain or environment variables
- Downloaded files may contain sensitive student data, so store them carefully and delete them when you are done

---

**Complexity Level:** Beginner | **Language:** Python 3.10+ | **API Version:** v2
