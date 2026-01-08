# Fetch All Applicants - Python

Fetch applicants with automatic pagination and export to CSV.

## Prerequisites

- **Python 3.10 or higher**
- **API Credentials** from Avela (client_id and client_secret)

**macOS users:** If you haven't used Python before, you may need to install Xcode Command Line Tools first:
```bash
xcode-select --install
```
A dialog will appear - click "Install" and wait for it to complete.

## Installation

```bash
cd api/applicants-fetch-all-python

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

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
- `environment` - Target environment: `prod`, `qa`, `uat`, or `dev`

## Usage

```bash
python avela_api_client.py
```

## Expected Output

```
How would you like to fetch applicants?
[1] Fetch all applicants
[2] Filter by specific reference IDs

Enter your choice (1 or 2): 1

Authenticating with Avela API (prod)...
✓ Authentication successful!

Fetching applicants from prod environment...
✓ Total applicants retrieved: 150

✓ Exported 150 applicants to: avela_applicants_20251110_143022.csv
```

**Output file:** `avela_applicants_YYYYMMDD_HHMMSS.csv` with all applicant fields.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## API Endpoints Used

### Authentication
- **Endpoint (prod):** `https://auth.avela.org/oauth/token`
- **Endpoint (non-prod):** `https://{env}.auth.avela.org/oauth/token`
- **Method:** POST

### List Applicants
- **Endpoint:** `https://{env}.execute-api.apply.avela.org/api/rest/v2/applicants`
- **Method:** GET
- **Purpose:** Retrieve applicant data
- **Pagination:** Automatic (max 1000 per request)

## Related Examples

- [Update Forms from CSV](../forms-update-csv-python/)
- [Download Form Files](../forms-download-files-python/)

## API Reference

- [Applicants Endpoint Documentation](https://docs.avela.org/api/v2/applicants)
- [Authentication Guide](https://docs.avela.org/authentication)
- [Rate Limits](https://docs.avela.org/rate-limits)

## Security Best Practices

- Never commit `config.json` to version control
- Use environment variables in production
- Rotate credentials regularly

---

**Complexity Level:** Beginner | **Language:** Python 3.10+ | **API Version:** v2
