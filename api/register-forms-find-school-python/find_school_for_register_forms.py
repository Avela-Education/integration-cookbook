#!/usr/bin/env python3
"""
Find the School for Every Register Form

Demonstrates the reliable way to identify which school a registration form
belongs to, even when the accepted offer has been revoked or deleted.

The approach:
    1. Fetch all register forms for an enrollment period
    2. Follow each form's previous_form_id to the linked apply form
    3. Call /forms/{id}/school_choices on the apply form to get the schools
    4. Export a CSV mapping every register form to its school

Why previous_form_id instead of previous_offer_id?
    previous_form_id always points to the apply form, regardless of offer
    state. previous_offer_id can become stale if an offer is revoked or
    deleted. The school choices on the apply form are the authoritative
    source for which schools the applicant applied to.

Author: Avela Education
License: MIT
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent / 'shared' / 'python')
)

from avela_client import create_client_from_config

# =============================================================================
# FORM FETCHING
# =============================================================================


def fetch_all_forms(
    client,
    enrollment_period_id: str,
    form_template_keys: list[str] | None = None,
) -> list[dict]:
    """
    Fetch forms for an enrollment period, handling pagination.

    If form_template_keys are provided, fetches each template separately
    (much faster than fetching all forms and filtering later).

    Args:
        client: Authenticated AvelaClient
        enrollment_period_id: UUID of the enrollment period
        form_template_keys: Optional list of template keys to filter by

    Returns:
        List of form dicts
    """
    if not form_template_keys:
        form_template_keys = [None]

    all_forms = []
    for template_key in form_template_keys:
        if template_key:
            print(f'  Template: {template_key}')

        offset = 0
        limit = 1000
        page = 1

        while True:
            print(f'    Fetching page {page} (offset: {offset})...', end=' ')

            params = {
                'enrollment_period_id': enrollment_period_id,
                'limit': limit,
                'offset': offset,
            }
            if template_key:
                params['form_template_key'] = template_key

            response = client.get('/forms', params=params)
            response.raise_for_status()
            data = response.json()

            forms = data.get('forms', [])
            print(f'{len(forms)} forms')

            all_forms.extend(forms)

            if len(forms) < limit:
                break

            offset += limit
            page += 1

    return all_forms


def fetch_form_detail(client, form_id: str) -> dict | None:
    """
    Fetch a single form's detail (includes previous_form_id, previous_offer_id).

    Args:
        client: Authenticated AvelaClient
        form_id: UUID of the form

    Returns:
        Form detail dict, or None if not found
    """
    response = client.get(f'/forms/{form_id}')

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json().get('form')


def fetch_school_choices(client, form_id: str) -> list[dict]:
    """
    Fetch school choices (with offers) for a form.

    This is the key call: it returns the schools on the apply form
    regardless of whether offers are accepted, declined, or revoked.

    Args:
        client: Authenticated AvelaClient
        form_id: UUID of the form (typically the apply/enrollment form)

    Returns:
        List of school choice dicts, each containing school info and offers
    """
    response = client.get(f'/forms/{form_id}/school_choices')

    if response.status_code == 404:
        return []

    response.raise_for_status()
    return response.json().get('school_choices', [])


# =============================================================================
# SCHOOL MATCHING LOGIC
# =============================================================================


def find_school_for_register_form(
    client,
    register_form: dict,
    apply_form_cache: dict,
) -> dict:
    """
    Determine the school for a single register form.

    Strategy:
        1. Get the register form's previous_form_id (link to apply form)
        2. Fetch school_choices from the apply form
        3. Identify the school — if there's an accepted offer, that's the
           match. Otherwise, return all schools on the apply form.

    Args:
        client: Authenticated AvelaClient
        register_form: Form detail dict for the register form
        apply_form_cache: Dict of apply_form_id -> school_choices (for reuse)

    Returns:
        Dict with matching info:
            register_form_id, applicant_id, applicant_reference_id,
            previous_form_id, previous_offer_id,
            matched_school_id, matched_school_reference_id,
            match_method, all_schools
    """
    form_id = register_form['id']
    applicant = register_form.get('applicant', {})
    previous_form_id = register_form.get('previous_form_id')
    previous_offer_id = register_form.get('previous_offer_id')

    result = {
        'register_form_id': form_id,
        'applicant_id': applicant.get('id', ''),
        'applicant_reference_id': applicant.get('reference_id', ''),
        'previous_form_id': previous_form_id or '',
        'previous_offer_id': previous_offer_id or '',
        'matched_school_id': '',
        'matched_school_reference_id': '',
        'match_method': '',
        'all_schools': '',
    }

    if not previous_form_id:
        result['match_method'] = 'NO_PREVIOUS_FORM'
        return result

    # Fetch school choices from the linked apply form (with caching)
    if previous_form_id not in apply_form_cache:
        apply_form_cache[previous_form_id] = fetch_school_choices(
            client, previous_form_id
        )

    school_choices = apply_form_cache[previous_form_id]

    if not school_choices:
        result['match_method'] = 'NO_SCHOOL_CHOICES'
        return result

    # Collect all schools for reference
    all_schools = []
    for sc in school_choices:
        school = sc.get('school', {})
        all_schools.append(school.get('reference_id') or school.get('id', ''))

    result['all_schools'] = '; '.join(all_schools)

    # Strategy 1: Find school with an accepted offer
    for sc in school_choices:
        for offer in sc.get('offers', []):
            if offer.get('status') == 'Accepted':
                school = sc.get('school', {})
                result['matched_school_id'] = school.get('id', '')
                result['matched_school_reference_id'] = school.get('reference_id', '')
                result['match_method'] = 'ACCEPTED_OFFER'
                return result

    # Strategy 2: If previous_offer_id is set, find the school that had that offer
    # (even if the offer is now revoked/declined)
    if previous_offer_id:
        for sc in school_choices:
            for offer in sc.get('offers', []):
                if offer.get('id') == previous_offer_id:
                    school = sc.get('school', {})
                    result['matched_school_id'] = school.get('id', '')
                    result['matched_school_reference_id'] = school.get('reference_id', '')
                    result['match_method'] = (
                        f'PREVIOUS_OFFER ({offer.get("status", "unknown")})'
                    )
                    return result

    # Strategy 3: Only one school on the form — it's the match
    if len(school_choices) == 1:
        school = school_choices[0].get('school', {})
        result['matched_school_id'] = school.get('id', '')
        result['matched_school_reference_id'] = school.get('reference_id', '')
        result['match_method'] = 'SINGLE_SCHOOL'
        return result

    # Multiple schools, no accepted offer, can't determine automatically
    result['match_method'] = 'AMBIGUOUS (multiple schools, no accepted offer)'
    return result


# =============================================================================
# EXPORT
# =============================================================================


CSV_FIELDNAMES = [
    'register_form_id',
    'applicant_id',
    'applicant_reference_id',
    'previous_form_id',
    'previous_offer_id',
    'matched_school_id',
    'matched_school_reference_id',
    'match_method',
    'all_schools',
]


def open_csv_writer(filename: str | None = None):
    """
    Open a CSV file for incremental writing.

    Args:
        filename: Output filename (defaults to timestamped name)

    Returns:
        Tuple of (file handle, csv.DictWriter, filename)
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'register_form_schools_{timestamp}.csv'

    f = open(filename, 'w', newline='', encoding='utf-8')  # noqa: SIM115
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    return f, writer, filename


# =============================================================================
# MAIN
# =============================================================================


def main():
    """
    Main execution:
    1. Load config and authenticate
    2. Fetch all register forms for the enrollment period
    3. Fetch form details (to get previous_form_id)
    4. Follow previous_form_id to the apply form's school_choices
    5. Export a CSV mapping each register form to its school
    """
    print('=' * 70)
    print('FIND SCHOOL FOR REGISTER FORMS')
    print('=' * 70)

    # Load config
    config_path = Path('config.json')
    if not config_path.exists():
        print(
            'Error: config.json not found. Copy config.example.json and fill in credentials.'
        )
        sys.exit(1)

    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    enrollment_period_id = config.get('enrollment_period_id')
    if not enrollment_period_id:
        print("Error: 'enrollment_period_id' is required in config.json")
        sys.exit(1)

    form_template_keys = config.get('form_template_keys')

    # Authenticate
    client = create_client_from_config('config.json')
    client.authenticate()

    # Step 1: Fetch forms for the enrollment period
    print(f'\nFetching forms for enrollment period {enrollment_period_id}...')
    if form_template_keys:
        print(f'Filtering by template keys: {form_template_keys}')
    all_forms = fetch_all_forms(client, enrollment_period_id, form_template_keys)
    print(f'Total forms fetched: {len(all_forms)}')

    if not all_forms:
        print('No forms found. Check enrollment_period_id.')
        sys.exit(0)

    # Step 2: Fetch detail for each form to get previous_form_id.
    # Forms with previous_form_id set are register forms.
    # Write results to CSV incrementally so partial results survive crashes.
    csv_file, csv_writer, filename = open_csv_writer()
    print(f'\nWriting results to: {filename}')
    print('Fetching form details to identify register forms...')
    apply_form_cache = {}  # Reuse school_choices across register forms
    register_count = 0
    methods = {}

    try:
        for i, form in enumerate(all_forms, 1):
            if i % 25 == 0 or i == 1:
                now = datetime.now().strftime('%H:%M:%S')
                print(f'  [{now}] Checking form {i}/{len(all_forms)}...')

            detail = fetch_form_detail(client, form['id'])
            if not detail:
                continue

            # Only process forms that have previous_form_id (register forms)
            if not detail.get('previous_form_id'):
                continue

            register_count += 1
            result = find_school_for_register_form(client, detail, apply_form_cache)
            csv_writer.writerow(result)
            csv_file.flush()

            # Track match methods for summary
            method = result['match_method']
            if method.startswith('PREVIOUS_OFFER'):
                method = 'PREVIOUS_OFFER (revoked/declined)'
            methods[method] = methods.get(method, 0) + 1
    finally:
        csv_file.close()

    print(f'\nFound {register_count} register forms (forms with previous_form_id)')

    # Step 3: Print summary
    print(f'\n{"=" * 70}')
    print('RESULTS SUMMARY')
    print(f'{"=" * 70}')

    for method, count in sorted(methods.items(), key=lambda x: -x[1]):
        print(f'  {method:<50} {count:>5}')

    matched_methods = {
        'ACCEPTED_OFFER',
        'PREVIOUS_OFFER (revoked/declined)',
        'SINGLE_SCHOOL',
    }
    matched = sum(count for method, count in methods.items() if method in matched_methods)
    print(f'\n  Total matched:   {matched}')
    print(f'  Total unmatched: {register_count - matched}')

    print(f'\n{"=" * 70}')
    print('Done!')
    print(f'Results saved to: {filename}')
    print(f'{"=" * 70}')


if __name__ == '__main__':
    main()
