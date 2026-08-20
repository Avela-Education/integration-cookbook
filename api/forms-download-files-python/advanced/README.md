# Download Form Files - Advanced Version

A larger version of the [basic download script](../README.md), built for downloading files in bulk.

## Quick Start

```bash
cd api/forms-download-files-python/advanced
pip install -r requirements.txt
python ../../../shared/python/setup_credentials.py   # Store credentials in the OS keychain
python download_form_files.py students.csv
```

## When to Use This Version

Use this advanced version when you need:

- **CSV input with student info** - Organize files by student name instead of form ID
- **Resume support** - Continue interrupted downloads without re-downloading
- **Retry logic for API calls** - Automatic retry with exponential backoff (via shared `avela_client` module)
- **Logging to file** - Keep a record of what was downloaded
- **Question filtering** - Download only specific file types (e.g., immunization records)

For learning the API or simple one-time downloads, use the [basic version](../README.md) instead.

## What's Different

| Feature         | Basic Version  | Advanced Version                            |
| --------------- | -------------- | ------------------------------------------- |
| Input format    | Text file only | Text file OR CSV                            |
| Folder naming   | `form_<uuid>/` | `Last, First (RefID) - FormID/` (with CSV)  |
| Resume support  | None           | Skips folders that already contain files    |
| Retry logic     | None           | Exponential backoff via `avela_client`      |
| Logging         | Console only   | Console + log file                          |
| Question filter | None           | Filter by question key                      |
| Batch size      | 100            | 60 (avoids URL expiry)                      |
| Rate limiting   | None           | Proactive (100 req/5min) via `avela_client` |

This version uses the shared [`avela_client`](../../../shared/python/) module which provides OAuth2 authentication, automatic rate limiting, and retry with exponential backoff.

## Setup

```bash
cd api/forms-download-files-python/advanced

# Create virtual environment (if not already done in parent)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (same as basic version)
pip install -r requirements.txt
```

## Configuration

### Credentials

This version takes credentials from the same places as every other recipe. On a laptop, store them once in your computer's keychain:

```bash
python ../../../shared/python/setup_credentials.py
```

The helper asks for your client id, client secret, and environment, hides the secret as you type it, and stores it encrypted.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### Settings

`output_dir` and `question_key_filter` are settings, not secrets, so they stay in `config.json` no matter where your credentials live. The script ignores a `config.json` that has no client id and secret, so a settings only file prints no plaintext warning.

```json
{
  "environment": "prod",
  "output_dir": "downloaded_files",
  "question_key_filter": []
}
```

- `question_key_filter` - Array of question keys to download. These are the slug-style `key` fields from your form schema (e.g., `["immunization-record", "physical-record"]`). Empty array downloads all files.

### Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../../shared/python/setup_credentials.py --profile district-a
python download_form_files.py students.csv --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every credential source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. It also picks the settings file: `config.{profile}.json` is layered over `config.json`, so a profile can override `output_dir` or `question_key_filter` and inherit the rest. See [shared/python/README.md](../../../shared/python/README.md) for the full explanation.

## Usage

### With Text File (same as basic)

```bash
python download_form_files.py form_ids.txt
```

Folders will be named: `form_<uuid>/`

### With CSV File (for descriptive folder names)

```bash
python download_form_files.py students.csv
```

Expected CSV columns:
- `App ID` (required) - The form UUID
- `Student Reference ID` (optional)
- `First Name` (optional)
- `Last Name` (optional)

Folders will be named: `Smith, John (12345) - <uuid>/`

### Resume an Interrupted Download

Run the same command again. The script skips folders that already contain files.

### Select a Credential Profile

Add `--profile <name>` to any of the commands above to run against a specific client's credentials.

## Uploading to Google Drive

For bulk uploads to Google Drive, use [rclone](https://rclone.org/) instead of the web interface.

### Install rclone

**macOS:**
```bash
brew install rclone
```

**Windows:**
```powershell
choco install rclone   # or: scoop install rclone
```

### Configure Google Drive

```bash
rclone config
# Follow prompts: n > gdrive > Google Drive > (blank) > (blank) > 1 > y > n > y > q
```

### Upload Files

```bash
# Upload (skips existing)
rclone copy downloaded_files gdrive:/MyFolder --progress --transfers=20

# Verify upload
rclone check downloaded_files gdrive:/MyFolder --progress
```
