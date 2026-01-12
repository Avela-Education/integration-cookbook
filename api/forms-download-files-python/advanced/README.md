# Download Form Files - Advanced Version

This is an enhanced version of the [basic download script](../README.md) with additional features for production use cases involving large numbers of files.

## Quick Start

```bash
cd api/forms-download-files-python/advanced
pip install -r ../requirements.txt
cp config.example.json config.json   # Edit with your credentials
python download_form_files.py students.csv
```

## When to Use This Version

Use this advanced version when you need:

- **CSV input with student info** - Organize files by student name instead of form ID
- **Resume support** - Continue interrupted downloads without re-downloading
- **Retry logic for API calls** - Handle transient failures when fetching file metadata
- **Logging to file** - Keep a record of what was downloaded
- **Question filtering** - Download only specific file types (e.g., immunization records)

For learning the API or simple one-time downloads, use the [basic version](../README.md) instead.

## What's Different

| Feature | Basic Version | Advanced Version |
|---------|---------------|------------------|
| Input format | Text file only | Text file OR CSV |
| Folder naming | `form_<uuid>/` | `Last, First (RefID) - FormID/` (with CSV) |
| Resume support | None | Skips folders that already contain files |
| Retry logic | None | 3 retries with backoff (API calls) |
| Logging | Console only | Console + log file |
| Question filter | None | Filter by question key |
| Batch size | 100 | 60 (avoids URL expiry) |

## Setup

```bash
cd api/forms-download-files-python/advanced

# Create virtual environment (if not already done in parent)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (same as basic version)
pip install -r ../requirements.txt

# Configure
cp config.example.json config.json
# Edit config.json with your credentials
```

## Configuration

```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "environment": "prod",
  "output_dir": "downloaded_files",
  "question_key_filter": []
}
```

**Additional Options:**
- `question_key_filter` - Array of question keys to download. These are the slug-style `key` fields from your form schema (e.g., `["immunization-record", "physical-record"]`). Empty array downloads all files.

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

Simply run the same command again. The script skips folders that already contain files.

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
