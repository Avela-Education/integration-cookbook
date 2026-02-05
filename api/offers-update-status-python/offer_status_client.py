#!/usr/bin/env python3
"""
Avela Offer Status Update Script

This script demonstrates how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Read offer updates from a CSV file
3. Update offer statuses (accept/decline) via the Customer API v2

Author: Avela Education
License: MIT
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import requests

VALID_ENVIRONMENTS = {'dev', 'qa', 'uat', 'prod'}

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_config(config_path: str = 'config.json') -> dict:
    """
    Load configuration from a JSON file.

    The config file should contain:
    - client_id: Your OAuth2 client ID (provided by Avela)
    - client_secret: Your OAuth2 client secret (provided by Avela)
    - environment: Which Avela environment to connect to (prod, qa, uat, dev)

    Args:
        config_path: Path to the configuration JSON file

    Returns:
        Dictionary containing configuration values

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Error: Configuration file '{config_path}' not found!")
        print("Please create it based on 'config.example.json'")
        sys.exit(1)

    with open(config_file, encoding='utf-8') as f:
        config = json.load(f)

    required_fields = ['client_id', 'client_secret', 'environment']
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        print(f'Error: Missing required fields in config: {", ".join(missing_fields)}')
        sys.exit(1)

    environment = config['environment']
    if environment not in VALID_ENVIRONMENTS:
        print(f'Error: Invalid environment "{environment}"')
        print(f'Valid environments: {", ".join(sorted(VALID_ENVIRONMENTS))}')
        sys.exit(1)

    return config


# =============================================================================
# AUTHENTICATION
# =============================================================================


def get_access_token(client_id: str, client_secret: str, environment: str) -> str:
    """
    Authenticate with Avela API and get an access token.

    This function uses the OAuth2 "client credentials" flow:
    1. Send client_id and client_secret to the authentication endpoint
    2. Receive an access token that's valid for 24 hours
    3. Use this token in subsequent API requests

    Args:
        client_id: Your OAuth2 client ID
        client_secret: Your OAuth2 client secret
        environment: Target environment (prod, qa, uat, dev)

    Returns:
        Access token string (JWT format)

    Raises:
        requests.RequestException: If authentication fails
    """
    if environment == 'prod':
        auth_url = 'https://auth.avela.org/oauth/token'
        audience = 'https://api.apply.avela.org/v1/graphql'
    else:
        auth_url = f'https://{environment}.auth.avela.org/oauth/token'
        audience = f'https://{environment}.api.apply.avela.org/v1/graphql'

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
            print('Error: No access token in response!')
            print(f'Response: {token_data}')
            sys.exit(1)

        expires_in = token_data.get('expires_in', 86400)
        print(f'Authentication successful! Token expires in {expires_in} seconds.')

        return access_token

    except requests.exceptions.RequestException as e:
        print('Error: Authentication failed!')
        print(f'Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}')
        sys.exit(1)


# =============================================================================
# CUSTOMER API - OFFER OPERATIONS
# =============================================================================


def get_customer_api_base_url(environment: str) -> str:
    """
    Get the Customer API v2 base URL for the given environment.

    Args:
        environment: Target environment (prod, qa, uat, dev)

    Returns:
        Base URL for the Customer API v2
    """
    if environment == 'prod':
        return 'https://execute-api.apply.avela.org/api/rest/v2/'
    return f'https://{environment}.execute-api.apply.avela.org/api/rest/v2/'


def update_offer_status(
    access_token: str, environment: str, offer_ids: list[str], status: str
) -> bool:
    """
    Update status for multiple offers.

    Uses the PUT /forms/offers/status endpoint.

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev)
        offer_ids: List of offer UUIDs to update
        status: "Accepted" or "Declined"

    Returns:
        True if successful, False otherwise
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
        print(f'  Failed to update offers to {status}!')
        print(f'  Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'  Response: {e.response.text}')
        return False


# =============================================================================
# CSV PROCESSING
# =============================================================================


def read_csv_updates(csv_path: str) -> list[dict]:
    """
    Read offer update data from a CSV file.

    Expected CSV format:
    offer_id,action
    uuid-1,accept
    uuid-2,decline

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of dictionaries with offer_id and action

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    csv_file = Path(csv_path)

    if not csv_file.exists():
        print(f"Error: CSV file '{csv_path}' not found!")
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
        print('Error: Failed to parse CSV file!')
        print(f'Details: {e}')
        sys.exit(1)
    except ValueError as e:
        print('Error: Invalid CSV format!')
        print(f'Details: {e}')
        sys.exit(1)


def process_csv_updates(
    access_token: str, environment: str, csv_path: str, dry_run: bool = False
) -> tuple[int, int]:
    """
    Process all offer updates from a CSV file.

    This function:
    1. Reads the CSV file
    2. Groups updates by action (accept/decline)
    3. Calls the appropriate API endpoint for each group

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev)
        csv_path: Path to the CSV file
        dry_run: If True, print what would be sent without making API calls

    Returns:
        Tuple of (successful_updates, failed_updates)
    """
    updates = read_csv_updates(csv_path)

    if not updates:
        print('No updates to process.')
        return (0, 0)

    # Group by action
    accept_ids = [u['offer_id'] for u in updates if u['action'] == 'accept']
    decline_ids = [u['offer_id'] for u in updates if u['action'] == 'decline']

    print(f'\nProcessing {len(updates)} offer update(s)...')
    print(f'  - {len(accept_ids)} to accept')
    print(f'  - {len(decline_ids)} to decline')
    print()

    successful = 0
    failed = 0

    # Process accepts
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

    # Process declines
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
    """
    Main execution function.

    This orchestrates the entire workflow:
    1. Load configuration
    2. Authenticate with the API
    3. Process CSV updates
    4. Report results
    """
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
    args = parser.parse_args()

    print('=' * 80)
    print('AVELA OFFER STATUS UPDATE - ACCEPT/DECLINE FROM CSV')
    if args.dry_run:
        print('[DRY RUN MODE - No changes will be made]')
    print('=' * 80)
    print()

    # Step 1: Load configuration
    config = load_config('config.json')

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    # Step 2: Authenticate
    if args.dry_run:
        print(f'[DRY RUN] Skipping authentication (environment: {environment})')
        access_token = 'dry-run-token'
    else:
        access_token = get_access_token(client_id, client_secret, environment)
    print()

    # Step 3: Process updates
    successful, failed = process_csv_updates(
        access_token, environment, args.csv, dry_run=args.dry_run
    )

    # Step 4: Report results
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
    Entry point when script is run directly.

    Usage:
        python offer_status_client.py                    # Run with sample_offers.csv
        python offer_status_client.py --dry-run          # Test without making API calls
        python offer_status_client.py --csv myfile.csv   # Use a different CSV file

    Make sure you have:
    1. Created a 'config.json' file with your credentials
    2. Created a CSV file with your updates (or use sample_offers.csv)
    """
    main()
