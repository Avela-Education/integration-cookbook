#!/usr/bin/env python3
"""
Find the School for Every Register Form

Work out which school each registration form belongs to, even when the offer
the family accepted was later revoked or deleted.

The approach:
    1. Fetch all register forms for an enrollment period
    2. Follow each form's previous_form_id to the linked apply form
    3. Call /forms/{id}/school_choices on the apply form to get the schools
    4. Export a CSV mapping every register form to its school

Why previous_form_id instead of previous_offer_id?
    previous_form_id always points to the apply form, whatever happened to the
    offer. previous_offer_id can go stale when an offer is revoked or deleted.
    The school choices on the apply form are the record of where the applicant
    actually applied.

Author: Avela Education
License: MIT
"""

import argparse
import csv
import sys
from datetime import datetime

try:
    from avela_client import create_client, load_settings
except ImportError as exc:
    print('Error: the shared Avela client could not be imported.')
    print(f'Details: {exc}')
    print("Install this recipe's dependencies and try again:")
    print('    pip install -r requirements.txt')
    sys.exit(1)


# =============================================================================
# FORM FETCHING
# =============================================================================


def fetch_all_forms(
    client,
    enrollment_period_id: str,
    form_template_keys: list[str] | None = None,
) -> list[dict]:
    """
    Fetch every form in an enrollment period, one page at a time.

    Naming form_template_keys asks the API for each template on its own, which
    is much faster than fetching every form and throwing most of them away.

    Args:
        client: Logged in AvelaClient
        enrollment_period_id: UUID of the enrollment period
        form_template_keys: Fetch only these template keys, if given

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
    Fetch one form in full, including previous_form_id and previous_offer_id.

    Args:
        client: Logged in AvelaClient
        form_id: UUID of the form

    Returns:
        Form detail dict, or None if there is no such form
    """
    response = client.get(f'/forms/{form_id}')

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json().get('form')


def fetch_school_choices(client, form_id: str) -> list[dict]:
    """
    Fetch a form's school choices, and the offers on them.

    This is the call that matters. It returns the schools on the apply form
    whether the offers were accepted, declined, or revoked.

    Args:
        client: Logged in AvelaClient
        form_id: UUID of the form, usually the apply form

    Returns:
        List of school choice dicts, each holding a school and its offers
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
    Work out the school for one register form.

    Steps:
        1. Read the register form's previous_form_id, which names the apply form
        2. Fetch school_choices from that apply form
        3. Pick the school. An accepted offer settles it. Without one, the row
           still lists every school on the apply form.

    Args:
        client: Logged in AvelaClient
        register_form: Form detail dict for the register form
        apply_form_cache: Dict of apply_form_id to school_choices, so a form
            shared by several register forms is only fetched once

    Returns:
        Dict holding the match:
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

    # Fetch the linked apply form's school choices, once per apply form
    if previous_form_id not in apply_form_cache:
        apply_form_cache[previous_form_id] = fetch_school_choices(
            client, previous_form_id
        )

    school_choices = apply_form_cache[previous_form_id]

    if not school_choices:
        result['match_method'] = 'NO_SCHOOL_CHOICES'
        return result

    # List every school on the form, so the row shows the whole picture
    all_schools = []
    for sc in school_choices:
        school = sc.get('school', {})
        all_schools.append(school.get('reference_id') or school.get('id', ''))

    result['all_schools'] = '; '.join(all_schools)

    # First try: the school with an accepted offer
    for sc in school_choices:
        for offer in sc.get('offers', []):
            if offer.get('status') == 'Accepted':
                school = sc.get('school', {})
                result['matched_school_id'] = school.get('id', '')
                result['matched_school_reference_id'] = school.get('reference_id', '')
                result['match_method'] = 'ACCEPTED_OFFER'
                return result

    # Second try: the school that held the offer named in previous_offer_id,
    # even if that offer has since been revoked or declined
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

    # Third try: only one school on the form, so that is the one
    if len(school_choices) == 1:
        school = school_choices[0].get('school', {})
        result['matched_school_id'] = school.get('id', '')
        result['matched_school_reference_id'] = school.get('reference_id', '')
        result['match_method'] = 'SINGLE_SCHOOL'
        return result

    # Several schools and no accepted offer, so a person has to decide
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
    Open a CSV file and write its header row.

    The caller writes one row at a time, so results survive a crash partway
    through a long run.

    Args:
        filename: Name for the file (defaults to a timestamped name)

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
    """Log in, follow every register form to its apply form, and write the CSV."""
    parser = argparse.ArgumentParser(
        description='Map every register form to the school on its linked apply form'
    )
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    print('=' * 70)
    print('FIND SCHOOL FOR REGISTER FORMS')
    print('=' * 70)

    # Read the settings. Credentials come from create_client() below.
    # The settings and the credentials always come from the same client
    try:
        config = load_settings(args.profile)
    except ValueError as e:
        print(e)
        sys.exit(1)

    enrollment_period_id = config.get('enrollment_period_id')
    if not enrollment_period_id:
        print("Error: this recipe needs an 'enrollment_period_id' setting.")
        print('Copy config.example.json to config.json and fill it in.')
        print('That file holds settings only, never credentials.')
        sys.exit(1)

    form_template_keys = config.get('form_template_keys')

    # Log in
    try:
        client = create_client(profile=args.profile)
    except ValueError as e:
        print(e)
        sys.exit(1)

    print(f'Credentials: {client.credential_source}')
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

    # Step 2: Fetch each form in full to read its previous_form_id. A form that
    # has one is a register form. Rows go to the CSV as they are found, so a
    # long run that stops early still leaves usable results.
    csv_file, csv_writer, filename = open_csv_writer()
    print(f'\nWriting results to: {filename}')
    print('Fetching form details to identify register forms...')
    apply_form_cache = {}  # One apply form can serve several register forms
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

            # A form without previous_form_id is not a register form
            if not detail.get('previous_form_id'):
                continue

            register_count += 1
            result = find_school_for_register_form(client, detail, apply_form_cache)
            csv_writer.writerow(result)
            csv_file.flush()

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
    print('Done.')
    print(f'Results saved to: {filename}')
    print(f'{"=" * 70}')


if __name__ == '__main__':
    main()
