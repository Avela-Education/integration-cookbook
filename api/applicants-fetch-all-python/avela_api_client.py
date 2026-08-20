#!/usr/bin/env python3
"""
Fetch applicants from the Avela API and export them to CSV.

The script:
1. Logs in with OAuth2 client credentials
2. Fetches every applicant in your organization, one page at a time
3. Prints a summary table and writes a timestamped CSV file

Author: Avela Education
License: MIT
"""

import argparse
import csv
import sys
from datetime import datetime
from urllib.parse import urljoin

# We use the 'requests' library for making HTTP calls
# Install it with: pip install requests
import requests

try:
    from avela_client import (
        DEFAULT_ENVIRONMENT,
        environment_urls,
        load_settings,
        resolve_credentials,
    )
except ImportError as exc:
    print('Error: the shared Avela client could not be imported.')
    print(f'Details: {exc}')
    print("Install this recipe's dependencies and try again:")
    print('    pip install -r requirements.txt')
    sys.exit(1)

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_config(profile: str | None = None, required: bool = True) -> dict:
    """
    Find credentials, and read any other settings from the config file.

    Credentials come from environment variables or the OS keychain. See
    resolve_credentials() in the shared avela_client module.

    Args:
        profile: Named credential set to use, when you have several clients

    Returns:
        Settings dictionary, with the credentials added
    """
    # The settings and the credentials always come from the same client
    try:
        config = load_settings(profile)
    except ValueError as e:
        # Show the plain message instead of a Python error
        print(e)
        sys.exit(1)

    try:
        credentials = resolve_credentials(profile=profile)
    except ValueError as e:
        if not required:
            # A dry run calls no API, so it can go on without credentials
            config['client_id'] = ''
            config['client_secret'] = ''
            config['environment'] = DEFAULT_ENVIRONMENT
            config['credential_source'] = 'none (dry run)'
            return config
        print(e)
        sys.exit(1)

    config['client_id'] = credentials.client_id
    config['client_secret'] = credentials.client_secret
    config['environment'] = credentials.environment
    config['credential_source'] = credentials.source
    return config


# =============================================================================
# AUTHENTICATION
# =============================================================================


def get_access_token(client_id: str, client_secret: str, environment: str) -> str:
    """
    Log in to the Avela API and get an access token.

    This is the OAuth2 client credentials flow. You send the client ID and
    secret to the login endpoint, get back a token that lasts 24 hours, and
    send that token with every later request.

    Args:
        client_id: Your OAuth2 client ID
        client_secret: Your OAuth2 client secret
        environment: Which environment to use (prod, qa, uat, dev, dev2)

    Returns:
        Access token string (JWT format)

    Raises:
        requests.RequestException: If the login fails
    """
    # environment_urls knows that staging authenticates against a different
    # host, which is easy to get wrong when building these by hand
    auth_url, _, audience = environment_urls(environment)

    print(f'Authenticating with Avela API ({environment})...')

    # OAuth2 token requests are form encoded, not JSON
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': audience,  # The API you are asking for access to
    }

    try:
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)

        # Stop here on a 4xx or 5xx response
        response.raise_for_status()

        token_data = response.json()

        access_token = token_data.get('access_token')
        if not access_token:
            print('Error: No access token in the response.')
            # Name the fields only. The body could hold another token.
            print(f'Response fields: {", ".join(sorted(token_data))}')
            sys.exit(1)

        expires_in = token_data.get('expires_in', 86400)  # Default 24 hours

        print(f'✓ Authentication successful. Token expires in {expires_in} seconds.')

        return access_token

    except requests.exceptions.RequestException as e:
        print('Error: Authentication failed.')
        print(f'Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}')
        sys.exit(1)


# =============================================================================
# APPLICANTS API
# =============================================================================


def get_applicants(
    access_token: str,
    environment: str,
    limit: int = 1000,
    reference_ids: list[str] | None = None,
) -> list[dict]:
    """
    Fetch applicants from the Avela API.

    Reads one page at a time from the /api/rest/v2/applicants endpoint until a
    page comes back short, then returns every record as one list.

    Args:
        access_token: Bearer token from authentication
        environment: Which environment to use (prod, qa, uat, dev, dev2)
        limit: How many records to fetch per page (max: 1000)
        reference_ids: Fetch only these reference IDs, if given

    Returns:
        List of applicant dictionaries

    Raises:
        requests.RequestException: If the request fails
    """
    # The v2 API lives under /api/rest/v2
    _, api_base_url, _ = environment_urls(environment)
    api_base_url += '/'

    applicants_url = urljoin(api_base_url, 'applicants')

    # The token goes in the Authorization header, after the word Bearer
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    params = {
        'limit': min(limit, 1000)  # API maximum is 1000 records per request
    }

    if reference_ids:
        params['reference_id'] = reference_ids

    print(f'\nFetching applicants from {environment} environment...')

    all_applicants = []
    offset = 0
    page = 1

    # Keep fetching until a page comes back short, which means the last one
    while True:
        params['offset'] = offset

        print(f'  Fetching page {page} (offset: {offset})...', end=' ')

        try:
            response = requests.get(
                applicants_url, headers=headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            applicants = data.get('applicants', [])

            print(f'Retrieved {len(applicants)} applicants')

            all_applicants.extend(applicants)

            if not applicants or len(applicants) < params['limit']:
                break

            offset += params['limit']
            page += 1

        except requests.exceptions.RequestException as e:
            print('\nError: Failed to fetch applicants.')
            print(f'Details: {e}')
            if hasattr(e, 'response') and e.response is not None:
                print(f'Response: {e.response.text}')
            sys.exit(1)

    print(f'\n✓ Total applicants retrieved: {len(all_applicants)}')

    return all_applicants


# =============================================================================
# DATA EXPORT
# =============================================================================


def print_applicants_summary(applicants: list[dict]) -> None:
    """
    Print a table of applicants to the screen.

    Args:
        applicants: List of applicant dictionaries
    """
    if not applicants:
        print('\nNo applicants found.')
        return

    print('\n' + '=' * 120)
    print(f'APPLICANTS SUMMARY ({len(applicants)} total)')
    print('=' * 120)

    header = f'{"Reference ID":<15} {"Name":<30} {"Email":<35} {"Birth Date":<12} {"City, State":<20}'
    print(header)
    print('-' * 120)

    for applicant in applicants:
        reference_id = applicant.get('reference_id') or 'N/A'
        first_name = applicant.get('first_name') or ''
        middle_name = applicant.get('middle_name') or ''
        last_name = applicant.get('last_name') or ''

        name_parts = [first_name, middle_name, last_name]
        full_name = ' '.join(part for part in name_parts if part) or 'N/A'

        email = applicant.get('email_address') or 'N/A'
        birth_date = applicant.get('birth_date') or 'N/A'
        city = applicant.get('city') or ''
        state = applicant.get('state') or ''
        location = f'{city}, {state}' if city or state else 'N/A'

        # Cut long values down so the columns line up
        full_name = (full_name[:27] + '...') if len(full_name) > 30 else full_name
        email = (email[:32] + '...') if email != 'N/A' and len(email) > 35 else email
        location = (
            (location[:17] + '...')
            if location != 'N/A' and len(location) > 20
            else location
        )

        row = f'{reference_id:<15} {full_name:<30} {email:<35} {birth_date:<12} {location:<20}'
        print(row)

    print('=' * 120 + '\n')


def export_to_csv(applicants: list[dict], filename: str | None = None) -> None:
    """
    Write the applicants to a CSV file.

    The file holds every field the API returned and opens in Excel or Google
    Sheets.

    Args:
        applicants: List of applicant dictionaries
        filename: Name for the file (defaults to a timestamped name)
    """
    if not applicants:
        print('No applicants to export.')
        return

    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'avela_applicants_{timestamp}.csv'

    # Collect every field name, since some applicants carry extra fields
    all_fields = set()
    for applicant in applicants:
        all_fields.update(applicant.keys())

    # The common columns, in the order they should appear
    preferred_order = [
        'reference_id',
        'first_name',
        'middle_name',
        'last_name',
        'birth_date',
        'email_address',
        'phone_number',
        'street_address',
        'street_address_line_2',
        'city',
        'state',
        'zip_code',
        'preferred_language',
        'email_okay',
        'sms_okay',
        'active',
        'person_type',
        'created_at',
        'updated_at',
        'deleted_at',
        'id',
    ]

    # Those columns first, then anything left over in alphabetical order
    fieldnames = [f for f in preferred_order if f in all_fields]
    remaining_fields = sorted(all_fields - set(fieldnames))
    fieldnames.extend(remaining_fields)

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(applicants)

        print(f'✓ Exported {len(applicants)} applicants to: {filename}')

    except OSError as e:
        print('Error: Failed to write the CSV file.')
        print(f'Details: {e}')
        sys.exit(1)


# =============================================================================
# USER INPUT HELPERS
# =============================================================================


def prompt_for_reference_ids() -> list[str] | None:
    """
    Ask whether to fetch every applicant or only certain reference IDs.

    Returns:
        None to fetch everything, or the list of reference IDs to fetch
    """
    print('\nHow would you like to fetch applicants?')
    print('[1] Fetch all applicants')
    print('[2] Filter by specific reference IDs')
    print()

    while True:
        choice = input('Enter your choice (1 or 2): ').strip()

        if choice == '1':
            return None

        if choice == '2':
            print()
            print('Enter reference IDs separated by commas.')
            print('Example: 450156,450157,450158')
            print()
            ids_input = input('Reference IDs: ').strip()

            if not ids_input:
                print('Error: No reference IDs entered. Try again.\n')
                continue

            # Split on commas and trim the spaces around each ID
            reference_ids = [rid.strip() for rid in ids_input.split(',') if rid.strip()]

            if not reference_ids:
                print('Error: No usable reference IDs entered. Try again.\n')
                continue

            print(f'\n✓ Will filter by {len(reference_ids)} reference ID(s)')
            return reference_ids

        print('Error: Enter 1 or 2.\n')


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Log in, fetch the applicants, print them, and write the CSV file."""
    parser = argparse.ArgumentParser(
        description='Fetch applicants from the Avela API and export them to CSV'
    )
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    print('=' * 80)
    print('AVELA API INTEGRATION - APPLICANTS EXPORT')
    print('=' * 80)

    # Step 1: Find credentials and any extra settings
    config = load_config(profile=args.profile)

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    print(f'Credentials: {config["credential_source"]}')

    # Step 2: Ask which applicants to fetch
    reference_ids = prompt_for_reference_ids()

    # Step 3: Log in
    access_token = get_access_token(client_id, client_secret, environment)

    # Step 4: Fetch the applicants
    applicants = get_applicants(
        access_token=access_token, environment=environment, reference_ids=reference_ids
    )

    # Step 5: Print the results
    print_applicants_summary(applicants)

    # Step 6: Write the CSV file
    export_to_csv(applicants)

    print('\n✓ Done.')
    print('=' * 80)


if __name__ == '__main__':
    """
    Run the recipe.

    Usage:
        python avela_api_client.py
        python avela_api_client.py --profile district-a

    Store your credentials first. The README covers the keychain and
    environment variables.
    """
    main()
