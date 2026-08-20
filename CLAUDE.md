# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Operations

**NEVER stage (`git add`) or commit files unless explicitly asked by the user.** Only make code changes and let the user decide when to stage and commit.

## Project Overview

The **Avela Integration Cookbook** is a set of working integration examples for the Avela Education Platform, covering Customer API v2, webhooks, and CSV processing.

## Repository Structure

Recipes sit in one flat layer, so they are easy to browse:

```
integration-cookbook/
├── api/                                    # API integration recipes
│   ├── applicants-fetch-all-python/       # Fetch applicants with pagination
│   ├── forms-update-csv-python/           # Bulk update forms from CSV
│   └── [future recipes: {resource}-{action}-{language}]
├── data-processing/                        # File-based integrations (planned)
├── webhooks/                               # Event-driven integrations (planned)
├── integrations/                           # Third-party platforms (planned)
├── use-cases/                              # Complete solutions (planned)
└── quickstart/                             # Quick start examples
    ├── api/                               # Minimal API examples
    └── csv/                               # Minimal CSV examples
```

**Recipe Naming Convention:** `{resource}-{action}-{language}/`
- Example: `applicants-fetch-all-python/`
- Example: `forms-update-csv-nodejs/` (when available)

The flat layout means you can:
- List every recipe with `ls api/`
- See which languages are covered
- Add a recipe without burying it in folders

## Key Architecture Patterns

### OAuth2 Authentication Flow
All API examples use the **client credentials flow**:
1. POST to `https://{env}.auth.avela.org/oauth/token` with client_id and client_secret
2. Receive access token (valid 24 hours)
3. Include token in Authorization header: `Bearer {token}`
4. Environment-specific audience values required

### API Endpoints Structure
- **Auth:** `https://{env}.auth.avela.org/oauth/token`
- **REST v2:** `https://{env}.execute-api.apply.avela.org/api/rest/v2/`
- **GraphQL:** `https://{env}.api.apply.avela.org/v1/graphql`

Environments: `dev`, `qa`, `uat`, `prod` (prod URLs omit the `{env}.` prefix)

### Pagination Pattern
API responses use offset-based pagination:
- `limit` parameter (max: 1000 records per request)
- `offset` parameter for page position
- Continue fetching until `len(results) < limit`

### Credential Resolution
Recipes never read credentials themselves. They call `create_client()` or `resolve_credentials()` from `shared/python/avela_client.py`, which checks three sources in order and stops at the first with both an ID and a secret:

| Order | Source                | Names                                                                 |
| ----- | --------------------- | --------------------------------------------------------------------- |
| 1     | Arguments in code     | `AvelaClient(client_id=..., client_secret=...)`                       |
| 2     | Environment variables | `AVELA_CLIENT_ID`, `AVELA_CLIENT_SECRET`, `AVELA_ENVIRONMENT`         |
| 3     | OS keychain           | Service `avela-api`, keys `client_id`, `client_secret`, `environment` |

Environment variables come before the keychain so a server, container, or CI job can override what a developer stored on a laptop. `config.json` files hold non-secret settings only; credentials in one are ignored, with a note saying so.

**Profiles.** `--profile district-a` or `AVELA_PROFILE=district-a` picks a named client. The name goes into the env vars (`AVELA_DISTRICT_A_CLIENT_ID`) and the keychain service (`avela-api:district-a`). Settings may live in `config.district-a.json`, layered over `config.json`. A named profile reads only its own names. If nothing is stored for it, resolution fails with an error rather than quietly using the default credentials, so a mistyped profile cannot run against the wrong client.

**Storing credentials:**
```bash
python shared/python/setup_credentials.py                    # default credentials
python shared/python/setup_credentials.py --profile district-a  # a named client
python shared/python/setup_credentials.py --list             # stored profiles
python shared/python/setup_credentials.py --show             # never prints the secret
```

`pip install -r requirements.txt` installs `keyring`, so the keychain works with no extra step.

See `shared/python/README.md` for the full reference.

## Common Development Commands

### Python Recipes
```bash
# Navigate to recipe directory
cd api/applicants-fetch-all-python     # Or any other recipe

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Store credentials once, in the OS keychain
python ../../shared/python/setup_credentials.py

# Or, on a server or in CI, export them instead
export AVELA_CLIENT_ID='...'
export AVELA_CLIENT_SECRET='...'
export AVELA_ENVIRONMENT='prod'

# Run the recipe
python avela_api_client.py        # For applicants recipe
python form_update_client.py      # For forms recipe
```

### Available Recipes
- `api/applicants-fetch-all-python/` - Fetch and export applicant data with pagination
- `api/forms-update-csv-python/` - Bulk update form answers from a CSV file
- `api/forms-download-files-python/` - Batch download file attachments from forms
- `api/offers-update-status-python/` - Bulk accept or decline offers from a CSV file
- `api/register-forms-find-school-python/` - Map every register form to its school
- `api/form-school-tags-import-python/` - Bulk import form school tags from a CSV file

## Recipe Standards

New recipes follow these patterns:

### Recipe Structure
```
{resource}-{action}-{language}/
├── README.md                 # Comprehensive documentation
├── main_script.py            # Main implementation
├── requirements.txt          # Python dependencies
├── package.json              # Node.js dependencies (if applicable)
├── config.example.json       # Optional, non-secret settings only
└── sample_data.csv           # Example data (if applicable)
```

**Naming Examples:**
- `applicants-fetch-all-python/`
- `forms-update-csv-nodejs/`
- `webhooks-handler-python/`

### README Template Requirements
Each example README must include:
1. **Overview** - What the example demonstrates (2-3 sentences)
2. **Prerequisites** - Required tools, credentials, knowledge
3. **Installation** - Step-by-step setup including virtual environment
4. **Configuration** - Keychain setup and the environment variables the recipe reads
5. **Usage** - How to run the example
6. **What This Example Does** - Numbered step-by-step explanation
7. **Expected Output** - Console output and file examples
8. **Key Concepts** - Educational explanation of patterns used
9. **Common Issues** - Troubleshooting guide
10. **API Endpoints Used** - Document specific endpoints
11. **Security Best Practices** - Credential handling

### Code Style Guidelines

**Python:**
- Follow PEP 8 (90 character line length)
- Type hints for function parameters and returns
- Docstrings on every function
- Comments explain "why", not "what"
- Use `requests` library for HTTP calls
- Error handling with try/except and clear error messages

**General:**
- Minimal dependencies (prefer standard libraries)
- No hardcoded credentials, and no direct config file reads. Call `create_client()`
- Timestamps on exported files: `YYYYMMDD_HHMMSS`
- UTF-8 encoding for all file operations

## Security Requirements

**Never commit:**
- Credentials, in any file
- CSV files with real data
- API tokens or secrets
- Production database connection strings

`.gitignore` covers `config.json`, `config.*.json`, `*.config.json`, `.env`, and `.env.*`, while still allowing `*.example.json`.

**Always include:**
- `.gitignore` entries for sensitive files
- Clear documentation on credential sources
- Input validation in example code

**Never do:**
- Read a credential file to display or copy its contents
- Print, log, or export a client secret or access token
- Ask a user to paste a client secret into a chat or a command line

## Testing Examples

Before submitting or updating examples:
1. Create fresh virtual environment and install dependencies
2. Test credentials from environment variables and from the keychain
3. Verify all documented commands work
4. Test error cases (no credentials found, invalid credentials)
5. Ensure CSV exports have correct formatting
6. Check that README expected output matches actual output

## API Versions and Environments

**Current API Version:** v2 (all examples use Customer API v2)

**Environment Mapping:**
- `dev` - Development environment
- `qa` - QA environment
- `uat` - UAT environment
- `prod` - Production environment

**API Response Patterns:**
Most endpoints return data in this structure:
```json
{
  "applicants": [...],  // or "forms", "data", etc.
  "total": 150,
  "offset": 0,
  "limit": 1000
}
```

## Fetching the OpenAPI v2 Spec

The API v2 spec is generated on the fly, served from `/api/rest/v2/doc`, and requires authentication.

### Credentials

Do not hunt for credential files on disk. Never run something like `ls api/*/config.json`, and never open a config file to read the values out of it. Let the shared client find credentials wherever the user keeps them.

### Fetching the Spec

The shared client handles auth, so this is the shortest path and works with any credential source:

```bash
# From the repository root
PYTHONPATH=shared/python python - <<'PY'
from avela_client import create_client

client = create_client(environment='uat')  # or 'qa', 'dev', 'prod'
response = client.get('/doc')
response.raise_for_status()

with open('openapi-v2.json', 'w', encoding='utf-8') as spec:
    spec.write(response.text)

print(f'Wrote openapi-v2.json ({len(response.text)} bytes)')
PY
```

If you need the raw HTTP calls, take the credentials from the environment. This sends the request body through stdin, so the secret never shows up in the process list:

```bash
# Set environment (uat, qa, dev, or prod)
ENV=uat

# Requires AVELA_CLIENT_ID and AVELA_CLIENT_SECRET to be exported already
# 1. Get an access token
TOKEN=$(jq -n \
  --arg id "$AVELA_CLIENT_ID" \
  --arg secret "$AVELA_CLIENT_SECRET" \
  --arg aud "https://${ENV}.api.apply.avela.org/v1/graphql" \
  '{client_id: $id, client_secret: $secret, audience: $aud, grant_type: "client_credentials"}' \
  | curl -s -X POST "https://${ENV}.auth.avela.org/oauth/token" \
      -H "Content-Type: application/json" -d @- \
  | jq -r '.access_token')

# 2. Fetch the OpenAPI spec
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://${ENV}.execute-api.apply.avela.org/api/rest/v2/doc" > openapi-v2.json
```

**Notes:**
- The audience must include `/v1/graphql` suffix
- For prod, URLs omit the environment prefix (e.g., `https://auth.avela.org/oauth/token`)
- The spec is ~180KB and includes all v2 endpoints
- Interactive docs: `https://{env}.api-docs.avela.dev/v2/index.html`

## Contributing Recipes

When adding new recipes:
1. Use the flat structure: `api/{resource}-{action}-{language}/`
2. Use existing recipes as templates (see `applicants-fetch-all-python/`)
3. Include comprehensive README following the template
4. Test thoroughly before submitting
5. Update main README.md and api/README.md with new recipe
6. See CONTRIBUTING.md for full guidelines

**Multi-language Support:**
Each recipe concept should have multiple language implementations:
- `applicants-fetch-all-python/` (current)
- `applicants-fetch-all-nodejs/` (future)
- `applicants-fetch-all-ruby/` (future)

## Common Troubleshooting

**"No Avela API credentials found"**
- Nothing was stored yet. Run `python shared/python/setup_credentials.py`, or export `AVELA_CLIENT_ID` and `AVELA_CLIENT_SECRET`
- If the credentials are in the keychain, check that `pip install -r requirements.txt` ran in the active virtual environment, since that is what installs `keyring`
- With `--profile`, confirm the name matches what `setup_credentials.py --list` reports

**"Authentication failed"**
- Verify correct environment (usually `prod`)
- Every recipe prints a `Credentials: ...` line at startup naming where it got them, for example `Credentials: keychain (avela-api:district-a)`. Check that it is the source you meant
- Check for a trailing newline or space in an exported variable or a stored value

**"Module not found" errors**
- Virtual environment not activated
- Dependencies not installed with `pip install -r requirements.txt`

**Virtual environment issues on Windows**
- PowerShell may need: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Use `venv\Scripts\activate.bat` for Command Prompt
- Use `venv\Scripts\Activate.ps1` for PowerShell

## Reference Documentation

- Main API Docs: https://prod.api-docs.avela.dev/v2/index.html
- Rate Limits: shared/python/README.md#rate-limits
- Support: help@avela.org
