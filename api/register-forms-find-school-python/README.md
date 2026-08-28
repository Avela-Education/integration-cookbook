# Find School for Register Forms

## Overview

Find which school a registration form belongs to, whatever has since happened to the offer that created it. Reporting teams use this to match every register form to a school.

## Why not just use `previous_offer_id`?

Register forms are created when a family accepts an offer, and the register form's `previous_offer_id` points to that offer. It is tempting to resolve the school by following it, but it is not a dependable path:

- **The offer's status changes.** An offer that was accepted can later be revoked or declined. It still appears in `/school_choices`, carrying its current status, so a query that joins only on accepted offers silently drops the register form.
- **A deleted offer disappears.** `/school_choices` omits deleted offers, so `previous_offer_id` can point at something the API will not return at all.
- **The pointer itself can be rewritten.** It is a live reference to current state, not a permanent record of how the register form came to exist.

`previous_form_id` has none of these properties.

## The Solution

Instead of relying on `previous_offer_id`, follow the `previous_form_id` link:

```
Register Form
  └── previous_form_id → Apply Form
                            └── /school_choices → Schools (always present)
```

`previous_form_id` always points to the apply (enrollment) form, whatever happened to the offer. The school choices on that form are the reliable record of where the applicant applied.

## Prerequisites

- Python 3.10+
- Avela API credentials (client_id and client_secret)
- The enrollment period ID for the forms you want to process

## Installation

```bash
cd api/register-forms-find-school-python

python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Configuration

This recipe needs two things: credentials, and the settings that tell it which forms to scan.

### 1. Store your credentials

On a laptop, store them once in your computer's keychain:

```bash
python ../../shared/python/setup_credentials.py
```

The helper asks for your client id, client secret, and environment, hides the secret as you type it, and stores it encrypted.

On a server, in a container, or in CI there is no keychain to unlock, so export the values instead:

```bash
export AVELA_CLIENT_ID=your_client_id
export AVELA_CLIENT_SECRET=your_client_secret
export AVELA_ENVIRONMENT=prod
```

The script checks environment variables first, then the keychain, so a scheduled job can override whatever you stored on your own machine.

### 2. Set the scan settings

`enrollment_period_id` and `form_template_keys` are settings, not secrets, so they live in `config.json` no matter where your credentials come from:

```bash
cp config.example.json config.json
```

Fill in the settings. The template holds no credentials, so the file stays safe to keep alongside your code:

```json
{
  "enrollment_period_id": "your_enrollment_period_id",
  "form_template_keys": ["your-register-form-template-key", "another-register-form-template-key"]
}
```

| Field                  | Required | Description                                                |
| ---------------------- | -------- | ---------------------------------------------------------- |
| `enrollment_period_id` | Yes      | UUID of the enrollment period to scan                      |
| `form_template_keys`   | No       | List of template keys to filter by (recommended for speed) |

The file holds settings only. The environment comes from your stored credentials or `AVELA_ENVIRONMENT`.

### 3. Working with several clients

Store one set of credentials per client under a name, then pick the name when you run:

```bash
python ../../shared/python/setup_credentials.py --profile district-a
python find_school_for_register_forms.py --profile district-a
```

`AVELA_PROFILE=district-a` does the same as the flag. The name changes every credential source: `AVELA_DISTRICT_A_CLIENT_ID` and keychain service `avela-api:district-a`. It also picks the settings file: `config.district-a.json` is layered over `config.json`, so a profile file can set just the enrollment period and inherit the rest. See [shared/python/README.md](../../shared/python/README.md) for the full explanation.

## Usage

```bash
# Use the default credentials
python find_school_for_register_forms.py

# Use a named profile
python find_school_for_register_forms.py --profile district-a
```

## What This Example Does

1. **Authenticates** with the Avela API using OAuth2 client credentials
2. **Fetches forms** for the enrollment period, filtered by `form_template_keys` if configured
3. **Fetches form detail** for each form to get `previous_form_id`. Forms with this field set are register forms
4. **Follows `previous_form_id`** to the linked apply form
5. **Fetches school choices** from the apply form (cached to avoid redundant calls)
6. **Matches the school** using this priority:
   - Accepted offer on the apply form
   - The specific offer referenced by `previous_offer_id` (even if revoked/declined)
   - Single school on the apply form (unambiguous)
7. **Exports a CSV** mapping each register form to its matched school

## Expected Output

```
======================================================================
FIND SCHOOL FOR REGISTER FORMS
======================================================================
Authenticating with Avela API (prod)...
Authentication successful! Token expires in 24 hours.

Fetching forms for enrollment period abc123...
Filtering by template keys: ['your-register-form-template-key', 'another-register-form-template-key']
  Template: your-register-form-template-key
    Fetching page 1 (offset: 0)... 500 forms
  Template: another-register-form-template-key
    Fetching page 1 (offset: 0)... 38 forms
Total forms fetched: 538

Fetching form details to identify register forms...
  Checking form 1/538...
  Checking form 100/538...
  ...

Found 538 register forms (forms with previous_form_id)

======================================================================
RESULTS SUMMARY
======================================================================
  ACCEPTED_OFFER                                       229
  PREVIOUS_OFFER (revoked/declined)                    220
  SINGLE_SCHOOL                                         48
  AMBIGUOUS (multiple schools, no accepted offer)       38
  NO_SCHOOL_CHOICES                                      3

  Total matched:   497
  Total unmatched: 41

Exported 538 rows to: register_form_schools_20260401_120000.csv
```

## CSV Output Columns

| Column                        | Description                                             |
| ----------------------------- | ------------------------------------------------------- |
| `register_form_id`            | UUID of the register form                               |
| `applicant_id`                | UUID of the applicant                                   |
| `applicant_reference_id`      | Human-readable applicant reference ID                   |
| `previous_form_id`            | UUID of the linked apply form                           |
| `previous_offer_id`           | UUID of the offer that created this form (may be stale) |
| `matched_school_id`           | UUID of the matched school                              |
| `matched_school_reference_id` | Human-readable school reference ID                      |
| `match_method`                | How the school was determined (see below)               |
| `all_schools`                 | All schools on the apply form (semicolon-separated)     |

## Match Methods

| Method                      | Meaning                                                                   |
| --------------------------- | ------------------------------------------------------------------------- |
| `ACCEPTED_OFFER`            | Apply form has a currently accepted offer at this school                  |
| `PREVIOUS_OFFER (Revoked)`  | The offer that created the reg form was revoked but is on the apply form  |
| `PREVIOUS_OFFER (Declined)` | The offer that created the reg form was declined but is on the apply form |
| `SINGLE_SCHOOL`             | Only one school on the apply form, so the match is unambiguous            |
| `AMBIGUOUS`                 | Multiple schools and no accepted offer, so review manually                |
| `NO_SCHOOL_CHOICES`         | Apply form has no school choices                                          |

`ACCEPTED_OFFER` is checked before `previous_offer_id`, so if the family accepted an
offer at a different school after this register form was created, the row reports the
school they accepted most recently rather than the one the register form was opened
for. Compare `previous_offer_id` against `matched_school_id` in the CSV when you need
to tell those apart.

## Key Concepts

### Why `previous_form_id` is more reliable than `previous_offer_id`

- `previous_form_id` links to the **apply form**, and that link never changes
- `previous_offer_id` links to a **specific offer**, whose status can change and which disappears from the API if it is deleted
- The school choices on the apply form stay put whatever happens to the offer

### Rate Limiting

This script uses the shared `AvelaClient` which automatically:
- Spaces requests to stay under 100 requests / 5 minutes
- Handles 429 responses with exponential backoff
- Caches apply form school choices to minimize API calls

## API Endpoints Used

| Endpoint                         | Purpose                                   |
| -------------------------------- | ----------------------------------------- |
| `GET /forms`                     | List register forms with pagination       |
| `GET /forms/{id}`                | Get form detail (previous_form_id)        |
| `GET /forms/{id}/school_choices` | Get schools and offers for the apply form |

## Troubleshooting

**"No credentials found"**
- Nothing the script checked had both an id and a secret. The error message lists both options
- Quickest fix on a laptop: `python ../../shared/python/setup_credentials.py`
- If you passed `--profile`, confirm that profile has credentials stored with `python ../../shared/python/setup_credentials.py --list`

**"No forms found"**
- Verify `enrollment_period_id` is correct
- If using `form_template_keys`, verify the keys match your organization's template names

**"Found 0 register forms"**
- The forms fetched may all be apply forms (no `previous_form_id`)
- Add register form template keys to `form_template_keys` in config to target only register forms

## Related Examples

- `applicants-fetch-all-python/`: Fetch applicants with pagination
- `form-school-tags-import-python/`: Import school tags via API
- `offers-update-status-python/`: Update offer statuses
