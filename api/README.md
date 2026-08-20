# API Integration Recipes

Production-ready code examples for integrating with the Avela API.

## Overview

Each recipe is a standalone example of one integration task. Every recipe ships with working code, configuration templates, and full documentation.

## Available Recipes

### [Fetch All Applicants (Python)](applicants-fetch-all-python/)
Retrieve applicant data from Avela with automatic pagination and export to CSV.

**What you'll learn:**
- OAuth2 authentication with client credentials
- Handling paginated API responses
- Exporting data to CSV format
- Error handling and retry logic

**Complexity:** Beginner | **Language:** Python 3.10+

---

### [Update Forms from CSV (Python)](forms-update-csv-python/)
Bulk update form answers by reading changes from a CSV file.

**What you'll learn:**
- Reading and validating CSV data
- Updating form questions via Customer API
- Batching API requests for efficiency
- Handling different question types

**Complexity:** Intermediate | **Language:** Python 3.10+

---

### [Download Form Files (Python)](forms-download-files-python/)
Batch download file attachments from forms using pre-signed URLs.

**What you'll learn:**
- Using the batch forms/files endpoint
- Working with pre-signed download URLs
- Streaming file downloads efficiently
- Organizing downloaded files by form and question

**Complexity:** Beginner | **Language:** Python 3.10+

---

### [Find School for Register Forms (Python)](register-forms-find-school-python/)
Reliably identify which school a registration form belongs to, even when the accepted offer has been revoked or deleted.

**What you'll learn:**
- Following `previous_form_id` to traverse form relationships
- Fetching school choices from the apply form
- Matching schools when offer state is unreliable
- Caching API responses to minimize calls

**Complexity:** Intermediate | **Language:** Python 3.10+

---

### [Update Offer Statuses (Python)](offers-update-status-python/)
Accept or decline offers in bulk from a CSV file.

**What you'll learn:**
- Using the unified offer status endpoint
- Grouping rows by action to batch API calls
- Dry run before writing to production
- Reading and validating CSV input

**Complexity:** Beginner | **Language:** Python 3.10+

---

### [Import Form-School Tags (Python)](form-school-tags-import-python/)
Assign tags to form and school pairs in bulk from a CSV file.

**What you'll learn:**
- Resolving tag names to UUIDs through the API
- Batch endpoints with 207 Multi-Status responses
- Handling partial success across a batch
- Resuming a partial import with `--start-row`

**Complexity:** Intermediate | **Language:** Python 3.10+

---

## Recipe Index

| Recipe                                                                  | Task                                               | Complexity   |
| ----------------------------------------------------------------------- | -------------------------------------------------- | ------------ |
| [applicants-fetch-all-python](applicants-fetch-all-python/)             | Fetch applicants with pagination and export to CSV | Beginner     |
| [forms-update-csv-python](forms-update-csv-python/)                     | Bulk update form answers from a CSV                | Intermediate |
| [forms-download-files-python](forms-download-files-python/)             | Batch download form file attachments               | Beginner     |
| [register-forms-find-school-python](register-forms-find-school-python/) | Match register forms to schools reliably           | Intermediate |
| [offers-update-status-python](offers-update-status-python/)             | Accept or decline offers in bulk                   | Beginner     |
| [form-school-tags-import-python](form-school-tags-import-python/)       | Import form-school tag assignments from a CSV      | Intermediate |

## Coming Soon

- **Applicants Fetch All (Node.js)**, applicant retrieval in Node.js
- **Forms Update CSV (Node.js)**, CSV form updates in Node.js
- **Webhook Event Handler**, process real-time application events
- **Applicant Search & Filter**, advanced querying patterns

## Getting Started

### Prerequisites

1. **API Credentials**
   - Client ID and Client Secret from your Avela administrator
   - Existing customers: email [help@avela.org](mailto:help@avela.org)
   - New to Avela? [Contact us](https://avela.org/contact)

2. **Development Environment**
   - Python 3.10+ or Node.js 16+ (depending on example)
   - Basic knowledge of REST APIs and OAuth2

### Quick Start

1. **Choose your language**: Open an example in the language you want
2. **Install dependencies**: Follow the example's README
3. **Store credentials**: See [Credentials](#credentials) below
4. **Run the example**: Run the main script

## Credentials

Every recipe gets its credentials the same way, through the shared resolver in [shared/python/avela_client.py](../shared/python/avela_client.py). It checks these places in order and stops at the first that has both an id and a secret:

| Order | Source                | Names                                                                 |
| ----- | --------------------- | --------------------------------------------------------------------- |
| 1     | Arguments in code     | `AvelaClient(client_id=..., client_secret=...)`                       |
| 2     | Environment variables | `AVELA_CLIENT_ID`, `AVELA_CLIENT_SECRET`, `AVELA_ENVIRONMENT`         |
| 3     | OS keychain           | Service `avela-api`, keys `client_id`, `client_secret`, `environment` |

Environment variables come before the keychain on purpose, so a server, container, or CI job can override whatever a developer stored locally. `config.json` files hold non-secret settings only; credentials in one are ignored.

### OS keychain (recommended on a laptop)

```bash
# from the repository root
python shared/python/setup_credentials.py

# from inside a recipe directory
python ../../shared/python/setup_credentials.py
```

The helper asks for your client id, client secret, and environment, then stores them encrypted in your operating system keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service). The prompt hides the secret as you type, so it never reaches your shell history.

### Environment variables (recommended for servers, CI, and containers)

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

AWS Secrets Manager, SSM, and `op run` all fill these same variables.

### config.json (legacy)

Credentials in a `config.json` are no longer used. A run that finds some prints a note telling you to move them to the keychain. It stores the secret in plaintext and now prints a warning. Recipes still read `config.json` for settings that are not secret (`output_dir`, `enrollment_period_id`, and similar). A file with no id and secret in it is skipped when credentials are looked up.

### Working with several clients

Store one set of credentials per client and pick one at run time:

```bash
python shared/python/setup_credentials.py --profile district-a
python api/applicants-fetch-all-python/avela_api_client.py --profile district-a
```

`AVELA_PROFILE=district-a` does the same without the flag. The profile renames every source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. [shared/python/README.md](../shared/python/README.md) has the full explanation.

`pip install -r requirements.txt` installs `keyring`, so the keychain works with no extra step.

## API Versions

- **Customer API v2** is the current version. All examples use it.

## Common Patterns

### Authentication Flow
```python
from avela_client import create_client

# Credentials come from the sources listed above, so no arguments are needed
client = create_client()

# Or select a named client
client = create_client(profile='district-a')

# The client authenticates and attaches the bearer token to every request
response = client.get('/applicants', params={'limit': 1000})
```

### Pagination
```python
# Handle large datasets with automatic pagination
offset = 0
limit = 1000
all_records = []

while True:
    response = api.get(endpoint, params={'offset': offset, 'limit': limit})
    records = response.json()['data']
    all_records.extend(records)

    if len(records) < limit:
        break
    offset += limit
```

### Error Handling
```python
try:
    response = requests.get(api_url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # Token expired, refresh and retry
        token = refresh_token()
    elif e.response.status_code == 429:
        # Rate limited, implement backoff
        time.sleep(60)
```

## Resources

- [API Reference Documentation](https://prod.api-docs.avela.dev/v2/index.html)
- [Rate Limits](../shared/python/README.md#rate-limits)

## Support

- Report issues: [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- Email support: [help@avela.org](mailto:help@avela.org)

## Contributing

Have an API integration pattern to share? Our [Contributing Guide](../CONTRIBUTING.md) covers how to submit a new example.
