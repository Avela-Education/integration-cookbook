# Find School for Register Forms

## Overview

Demonstrates how to reliably identify which school a registration form belongs to, **even when the accepted offer has been revoked or deleted**. This is useful for BI/reporting teams that need to match every register form to a school.

## The Problem

Register forms are created when a family accepts an offer. The `previous_offer_id` field on the register form points to that offer. However, if the offer is later revoked or declined with no replacement, the offer may no longer appear in the API — leaving the register form with no obvious link to a school.

## The Solution

Instead of relying on `previous_offer_id`, follow the `previous_form_id` link:

```
Register Form
  └── previous_form_id → Apply Form
                            └── /school_choices → Schools (always present)
```

`previous_form_id` always points to the apply (enrollment) form, regardless of offer state. The school choices on the apply form are the authoritative source for which schools the applicant applied to.

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

```bash
cp config.example.json config.json
```

Edit `config.json` with your credentials:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "environment": "prod",
  "enrollment_period_id": "your_enrollment_period_id",
  "form_template_keys": ["register-for-arizona-schools", "register-for-texas-schools"]
}
```

| Field                 | Required | Description                                                   |
| --------------------- | -------- | ------------------------------------------------------------- |
| `client_id`           | Yes      | OAuth2 client ID                                              |
| `client_secret`       | Yes      | OAuth2 client secret                                          |
| `environment`         | Yes      | `prod`, `uat`, `qa`, or `dev`                                 |
| `enrollment_period_id`| Yes      | UUID of the enrollment period to scan                         |
| `form_template_keys`  | No       | List of template keys to filter by (recommended for speed)    |

## Usage

```bash
python find_school_for_register_forms.py
```

## What This Example Does

1. **Authenticates** with the Avela API using OAuth2 client credentials
2. **Fetches forms** for the enrollment period, filtered by `form_template_keys` if configured
3. **Fetches form detail** for each form to get `previous_form_id` — forms with this field set are register forms
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
Filtering by template keys: ['register-for-arizona-schools', 'register-for-texas-schools']
  Template: register-for-arizona-schools
    Fetching page 1 (offset: 0)... 500 forms
  Template: register-for-texas-schools
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
  NO_SCHOOL_CHOICES                                      3

  Total matched:   497
  Total unmatched: 41

Exported 538 rows to: register_form_schools_20260401_120000.csv
```

## CSV Output Columns

| Column                       | Description                                              |
| ---------------------------- | -------------------------------------------------------- |
| `register_form_id`           | UUID of the register form                                |
| `applicant_id`               | UUID of the applicant                                    |
| `applicant_reference_id`     | Human-readable applicant reference ID                    |
| `previous_form_id`           | UUID of the linked apply form                            |
| `previous_offer_id`          | UUID of the offer that created this form (may be stale)  |
| `matched_school_id`          | UUID of the matched school                               |
| `matched_school_reference_id`| Human-readable school reference ID                       |
| `match_method`               | How the school was determined (see below)                |
| `all_schools`                | All schools on the apply form (semicolon-separated)      |

## Match Methods

| Method                              | Meaning                                                        |
| ----------------------------------- | -------------------------------------------------------------- |
| `ACCEPTED_OFFER`                    | Apply form has a currently accepted offer at this school        |
| `PREVIOUS_OFFER (Revoked)`          | The offer that created the reg form was revoked but is on the apply form |
| `PREVIOUS_OFFER (Declined)`         | The offer that created the reg form was declined but is on the apply form |
| `SINGLE_SCHOOL`                     | Only one school on the apply form — unambiguous match          |
| `AMBIGUOUS`                         | Multiple schools, no accepted offer — review manually          |
| `NO_SCHOOL_CHOICES`                 | Apply form has no school choices                               |

## Key Concepts

### Why `previous_form_id` is more reliable than `previous_offer_id`

- `previous_form_id` links to the **apply form** — this is a structural link that doesn't change
- `previous_offer_id` links to a **specific offer** — if that offer is revoked or deleted, the link becomes stale
- The school choices on the apply form persist regardless of offer state

### Rate Limiting

This script uses the shared `AvelaClient` which automatically:
- Spaces requests to stay under 100 requests / 5 minutes
- Handles 429 responses with exponential backoff
- Caches apply form school choices to minimize API calls

## API Endpoints Used

| Endpoint                        | Purpose                                      |
| ------------------------------- | -------------------------------------------- |
| `GET /forms`                    | List register forms with pagination          |
| `GET /forms/{id}`               | Get form detail (previous_form_id)           |
| `GET /forms/{id}/school_choices`| Get schools and offers for the apply form    |

## Troubleshooting

**"No forms found"**
- Verify `enrollment_period_id` is correct
- If using `form_template_keys`, verify the keys match your organization's template names

**"Found 0 register forms"**
- The forms fetched may all be apply forms (no `previous_form_id`)
- Add register form template keys to `form_template_keys` in config to target only register forms

## Related Examples

- `applicants-fetch-all-python/` — Fetch applicants with pagination
- `form-school-tags-import-python/` — Import school tags via API
- `offers-update-status-python/` — Update offer statuses
