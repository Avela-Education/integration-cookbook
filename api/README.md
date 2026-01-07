# API Integration Recipes

Production-ready code examples for integrating with the Avela API.

## Overview

Each recipe is a self-contained example showing how to accomplish a specific integration task. All recipes include complete working code, configuration templates, and comprehensive documentation.

## Available Recipes

### [Fetch All Applicants (Python)](applicants-fetch-all-python/)
Retrieve applicant data from Avela with automatic pagination and export to CSV.

**What you'll learn:**
- OAuth2 authentication with client credentials
- Handling paginated API responses
- Exporting data to CSV format
- Error handling and retry logic

**Complexity:** Beginner | **Language:** Python 3.8+

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

## Coming Soon

- **Applicants Fetch All (Node.js)** - Node.js version of applicant retrieval
- **Forms Update CSV (Node.js)** - Node.js version of CSV form updates
- **Webhook Event Handler** - Process real-time application events
- **Applicant Search & Filter** - Advanced querying patterns

## Getting Started

### Prerequisites

1. **API Credentials**
   - Client ID and Client Secret from your Avela administrator
   - [Request access](https://avela.org/api-access) if you don't have credentials

2. **Development Environment**
   - Python 3.8+ or Node.js 16+ (depending on example)
   - Basic knowledge of REST APIs and OAuth2

### Quick Start

1. **Choose your language**: Navigate to an example in your preferred language
2. **Install dependencies**: Follow the example's README
3. **Configure credentials**: Copy `config.example.json` to `config.json` and add your credentials
4. **Run the example**: Execute the main script

## API Versions

- **REST API v2** - Current version (all examples use v2)

## Common Patterns

### Authentication Flow
```python
# 1. Get access token using client credentials
token = get_access_token(client_id, client_secret, environment)

# 2. Use token for API requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get(api_url, headers=headers)
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

- [API Reference Documentation](https://docs.avela.org/api/v2)
- [Authentication Guide](https://docs.avela.org/authentication)
- [Rate Limits](https://docs.avela.org/rate-limits)
- [API Changelog](https://docs.avela.org/changelog)

## Support

- Report issues: [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- Ask questions: [GitHub Discussions](https://github.com/Avela-Education/integration-cookbook/discussions)
- Email support: [api-support@avela.org](mailto:api-support@avela.org)

## Contributing

Have an API integration pattern to share? See our [Contributing Guide](../CONTRIBUTING.md) for guidelines on submitting new examples.
