# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Avela Integration Cookbook** - a collection of production-ready integration examples and patterns for the Avela Education Platform. It serves as a reference library for developers building integrations using Avela's REST API, webhooks, and CSV processing.

## Repository Structure

The repository uses a **flat recipe structure** for easy browsing:

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

This flat structure makes it easy to:
- Browse all recipes with a simple `ls api/`
- See which language implementations are available
- Add new recipes without deep nesting

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

### Configuration Management
All examples use a consistent configuration pattern:
1. `config.example.json` - Template with placeholder values (committed)
2. `config.json` - Actual credentials (gitignored, user creates)
3. Required fields: `client_id`, `client_secret`, `environment`

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

# Create configuration
cp config.example.json config.json
# Edit config.json with your credentials

# Run the recipe
python avela_api_client.py        # For applicants recipe
python form_update_client.py      # For forms recipe
```

### Available Recipes
- `api/applicants-fetch-all-python/` - Fetch and export applicants with pagination
- `api/forms-update-csv-python/` - Bulk update form answers from CSV

## Recipe Standards

When creating new recipes, follow these patterns:

### Recipe Structure
```
{resource}-{action}-{language}/
├── README.md                 # Comprehensive documentation
├── main_script.py            # Main implementation
├── requirements.txt          # Python dependencies
├── package.json              # Node.js dependencies (if applicable)
├── config.example.json       # Configuration template
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
4. **Configuration** - How to set up config.json
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
- Comprehensive docstrings for all functions
- Educational comments explaining "why", not "what"
- Use `requests` library for HTTP calls
- Error handling with try/except and clear error messages

**General:**
- Minimal dependencies (prefer standard libraries)
- No hardcoded credentials (use config.json)
- Timestamps on exported files: `YYYYMMDD_HHMMSS`
- UTF-8 encoding for all file operations

## Security Requirements

**Never commit:**
- `config.json` files (actual credentials)
- CSV files with real data
- API tokens or secrets
- Production database connection strings

**Always include:**
- `.gitignore` entries for sensitive files
- `config.example.json` with placeholder values
- Clear documentation on credential sources
- Input validation in example code

## Testing Examples

Before submitting or updating examples:
1. Create fresh virtual environment and install dependencies
2. Test with `config.example.json` → `config.json` workflow
3. Verify all documented commands work
4. Test error cases (missing config, invalid credentials)
5. Ensure CSV exports have correct formatting
6. Check that README expected output matches actual output

## API Versions and Environments

**Current API Version:** v2 (all examples use REST API v2)

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

**"Configuration file not found"**
- User needs to copy `config.example.json` to `config.json`

**"Authentication failed"**
- Verify correct environment (usually `prod`)
- Check client_id and client_secret are correct
- Ensure no extra spaces in config.json

**"Module not found" errors**
- Virtual environment not activated
- Dependencies not installed with `pip install -r requirements.txt`

**Virtual environment issues on Windows**
- PowerShell may need: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Use `venv\Scripts\activate.bat` for Command Prompt
- Use `venv\Scripts\Activate.ps1` for PowerShell

## Reference Documentation

- Main API Docs: https://docs.avela.org/api/v2
- Authentication Guide: https://docs.avela.org/authentication
- Rate Limits: https://docs.avela.org/rate-limits
- Support: api-support@avela.org
