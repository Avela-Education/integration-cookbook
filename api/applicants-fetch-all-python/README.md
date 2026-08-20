# Fetch All Applicants - Python

Fetch applicants with automatic pagination and export to CSV.

## Prerequisites

- **Python 3.10 or higher**
- **API Credentials** from Avela (client_id and client_secret)

**macOS users:** If you haven't used Python before, install the Xcode Command Line Tools first:
```bash
xcode-select --install
```
A dialog appears. Click "Install" and wait for it to finish.

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

You need your OAuth2 client id and client secret from Avela, plus the environment you are working in: `prod`, `qa`, `uat`, or `dev`.

On a laptop, store them once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for the three values, hides the secret as you type it, and stores it encrypted. Nothing is written into the repository. Add `--show`, `--list`, or `--delete` to see or remove what is stored.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python avela_api_client.py --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

## Usage

```bash
# Use the default credentials
python avela_api_client.py

# Use a named profile
python avela_api_client.py --profile district-a
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

## API Endpoints Used

### Authentication
- **Endpoint (prod):** `https://auth.avela.org/oauth/token`
- **Endpoint (non-prod):** `https://{env}.auth.avela.org/oauth/token`
- **Method:** POST

### List Applicants
- **Customer API endpoint:** `GET /api/rest/v2/applicants`
- **Method:** GET
- **Purpose:** Retrieve applicant data
- **Pagination:** Automatic (max 1000 per request)

## Related Examples

- [Update Forms from CSV](../forms-update-csv-python/)
- [Download Form Files](../forms-download-files-python/)

## API Reference

- [Applicants Endpoint Documentation](https://prod.api-docs.avela.dev/v2/index.html)
- [Rate Limits](../../shared/python/README.md#rate-limits)

## Security Best Practices

- Prefer the OS keychain on a laptop and environment variables on a server; both keep the secret out of the repository
- Keep secrets out of files; credentials live in the keychain or environment variables
- Rotate credentials regularly, and request new ones if you suspect exposure
- Use credentials scoped to the environment you are working in, not production credentials for testing

---

**Complexity Level:** Beginner | **Language:** Python 3.10+ | **API Version:** v2
