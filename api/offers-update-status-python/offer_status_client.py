#!/usr/bin/env python3
"""
Accept or decline offers in bulk from a CSV file.

The script:
1. Logs in with OAuth2 client credentials
2. Reads one offer ID and one action per row from a CSV file
3. Sends the accepts and the declines to the Customer API v2

Author: Avela Education
License: MIT
"""

import argparse
import csv
import sys
from pathlib import Path

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
        environment: Which environment to use (prod, qa, uat, dev)

    Returns:
        Access token string (JWT format)

    Raises:
        requests.RequestException: If the login fails
    """
    # environment_urls knows that staging authenticates against a different
    # host, which is easy to get wrong when building these by hand
    auth_url, _, audience = environment_urls(environment)

    print(f'Authenticating with Avela API ({environment})...')

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': audience,
    }

    try:
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        response.raise_for_status()

        token_data = response.json()

        access_token = token_data.get('access_token')
        if not access_token:
            print('Error: No access token in the response.')
            # Name the fields only. The body could hold another token.
            print(f'Response fields: {", ".join(sorted(token_data))}')
            sys.exit(1)

        expires_in = token_data.get('expires_in', 86400)
        print(f'Authentication successful. Token expires in {expires_in} seconds.')

        return access_token

    except requests.exceptions.RequestException as e:
        print('Error: Authentication failed.')
        print(f'Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}')
        sys.exit(1)


# =============================================================================
# CUSTOMER API - OFFER OPERATIONS
# =============================================================================


def get_customer_api_base_url(environment: str) -> str:
    """
    Build the Customer API v2 base URL for an environment.

    Args:
        environment: Which environment to use (prod, qa, uat, dev)

    Returns:
        Base URL for the Customer API v2
    """
    _, base_url, _ = environment_urls(environment)
    return base_url + '/'


def update_offer_status(
    access_token: str, environment: str, offer_ids: list[str], status: str
) -> bool:
    """
    Set the same status on a batch of offers.

    Uses the PUT /forms/offers/status endpoint.

    Args:
        access_token: Bearer token from authentication
        environment: Which environment to use (prod, qa, uat, dev)
        offer_ids: List of offer UUIDs to update
        status: "Accepted" or "Declined"

    Returns:
        True if the update worked, False if it did not
    """
    base_url = get_customer_api_base_url(environment)
    url = f'{base_url}forms/offers/status'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {
        'offers': [{'offer_id': offer_id} for offer_id in offer_ids],
        'status': status,
    }

    try:
        response = requests.put(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result.get('data', {}).get('success', False)

    except requests.exceptions.RequestException as e:
        print(f'  Failed to update the offers to {status}.')
        print(f'  Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'  Response: {e.response.text}')
        return False


# =============================================================================
# CSV PROCESSING
# =============================================================================


def read_csv_updates(csv_path: str) -> list[dict]:
    """
    Read the offer updates out of a CSV file.

    The file looks like this:
    offer_id,action
    uuid-1,accept
    uuid-2,decline

    Rows with no offer ID, or an action other than accept or decline, are
    skipped with a warning.

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of dictionaries with offer_id and action

    Raises:
        FileNotFoundError: If the CSV file is missing
        ValueError: If the CSV is missing a required column
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        print(f"Error: CSV file '{csv_path}' not found.")
        sys.exit(1)

    updates = []

    try:
        with open(csv_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            required_columns = {'offer_id', 'action'}
            if not required_columns.issubset(reader.fieldnames or []):
                missing = required_columns - set(reader.fieldnames or [])
                raise ValueError(f'CSV missing required columns: {missing}')

            for row_num, row in enumerate(reader, start=2):
                if not any(row.values()):
                    continue

                if not row.get('offer_id'):
                    print(f'Warning: Row {row_num} missing offer_id, skipping')
                    continue

                action = row.get('action', '').strip().lower()
                if action not in ['accept', 'decline']:
                    print(
                        f'Warning: Row {row_num} has invalid action "{action}", skipping'
                    )
                    continue

                updates.append(
                    {
                        'offer_id': row['offer_id'].strip(),
                        'action': action,
                    }
                )

        print(f'Read {len(updates)} updates from CSV file')
        return updates

    except csv.Error as e:
        print('Error: Could not read the CSV file.')
        print(f'Details: {e}')
        sys.exit(1)
    except ValueError as e:
        print('Error: The CSV file is missing something.')
        print(f'Details: {e}')
        sys.exit(1)


def process_csv_updates(
    access_token: str, environment: str, csv_path: str, dry_run: bool = False
) -> tuple[int, int]:
    """
    Apply every offer update in a CSV file.

    Reads the file, splits the rows into accepts and declines, and sends each
    group in one request.

    Args:
        access_token: Bearer token from authentication
        environment: Which environment to use (prod, qa, uat, dev)
        csv_path: Path to the CSV file
        dry_run: If True, print what would be sent and call nothing

    Returns:
        Tuple of (successful_updates, failed_updates)
    """
    updates = read_csv_updates(csv_path)

    if not updates:
        print('No updates to process.')
        return (0, 0)

    # One request per action, so split the rows first
    accept_ids = [u['offer_id'] for u in updates if u['action'] == 'accept']
    decline_ids = [u['offer_id'] for u in updates if u['action'] == 'decline']

    print(f'\nProcessing {len(updates)} offer update(s)...')
    print(f'  - {len(accept_ids)} to accept')
    print(f'  - {len(decline_ids)} to decline')
    print()

    successful = 0
    failed = 0

    if accept_ids:
        print(f'Accepting {len(accept_ids)} offer(s)...')
        for offer_id in accept_ids:
            print(f'  - {offer_id}')

        if dry_run:
            print(f'  [DRY RUN] Would accept {len(accept_ids)} offer(s)')
            successful += len(accept_ids)
        else:
            if update_offer_status(access_token, environment, accept_ids, 'Accepted'):
                print(f'  Successfully accepted {len(accept_ids)} offer(s)')
                successful += len(accept_ids)
            else:
                failed += len(accept_ids)
        print()

    if decline_ids:
        print(f'Declining {len(decline_ids)} offer(s)...')
        for offer_id in decline_ids:
            print(f'  - {offer_id}')

        if dry_run:
            print(f'  [DRY RUN] Would decline {len(decline_ids)} offer(s)')
            successful += len(decline_ids)
        else:
            if update_offer_status(access_token, environment, decline_ids, 'Declined'):
                print(f'  Successfully declined {len(decline_ids)} offer(s)')
                successful += len(decline_ids)
            else:
                failed += len(decline_ids)
        print()

    return (successful, failed)


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Log in, apply every offer update in the CSV file, then report results."""
    parser = argparse.ArgumentParser(
        description='Update offer statuses (accept/decline) in bulk from a CSV file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be sent without making API calls',
    )
    parser.add_argument(
        '--csv',
        default='sample_offers.csv',
        help='Path to CSV file (default: sample_offers.csv)',
    )
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    print('=' * 80)
    print('AVELA OFFER STATUS UPDATE - ACCEPT/DECLINE FROM CSV')
    if args.dry_run:
        print('[DRY RUN MODE - No changes will be made]')
    print('=' * 80)
    print()

    # Step 1: Find credentials and any extra settings
    config = load_config(profile=args.profile, required=not args.dry_run)

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    print(f'Credentials: {config["credential_source"]}')

    # Step 2: Log in, unless this is a dry run
    if args.dry_run:
        print(f'[DRY RUN] Skipping authentication (environment: {environment})')
        access_token = 'dry-run-token'
    else:
        access_token = get_access_token(client_id, client_secret, environment)
    print()

    # Step 3: Apply the updates
    successful, failed = process_csv_updates(
        access_token, environment, args.csv, dry_run=args.dry_run
    )

    # Step 4: Report what happened
    print('=' * 80)
    print('RESULTS')
    print('=' * 80)
    print(f'Successful updates: {successful}')
    print(f'Failed updates: {failed}')
    print(f'Total: {successful + failed}')
    print('=' * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    """
    Run the recipe.

    Usage:
        python offer_status_client.py                    # Run with sample_offers.csv
        python offer_status_client.py --dry-run          # Test without making API calls
        python offer_status_client.py --csv myfile.csv   # Use a different CSV file
        python offer_status_client.py --profile district-a  # Use a named credential set

    Before you run it:
    1. Store your credentials (the README covers the keychain and environment variables)
    2. Write a CSV file of updates, or use sample_offers.csv
    """
    main()
