#!/usr/bin/env python3
"""
Avela API Integration Script

This script demonstrates how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Retrieve a list of applicants from your Avela organization
3. Export the data to both console and CSV format

Author: Avela Education
License: MIT
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

# We use the 'requests' library for making HTTP calls
# Install it with: pip install requests
import requests

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_config(config_path: str = 'config.json') -> dict:
    """
    Load configuration from a JSON file.

    The config file should contain:
    - client_id: Your OAuth2 client ID (provided by Avela)
    - client_secret: Your OAuth2 client secret (provided by Avela)
    - environment: Which Avela environment to connect to (prod, qa, uat, dev, dev2)

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

    # Validate required fields
    required_fields = ['client_id', 'client_secret', 'environment']
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        print(f'Error: Missing required fields in config: {", ".join(missing_fields)}')
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
        environment: Target environment (prod, qa, uat, dev, dev2)

    Returns:
        Access token string (JWT format)

    Raises:
        requests.RequestException: If authentication fails
    """
    # Build the authentication URL based on environment
    # For production, the URL is: https://auth.avela.org/oauth/token
    # For other environments: https://{env}.auth.avela.org/oauth/token
    if environment == 'prod':
        auth_url = 'https://auth.avela.org/oauth/token'
        audience = 'https://api.apply.avela.org/v1/graphql'
    else:
        auth_url = f'https://{environment}.auth.avela.org/oauth/token'
        audience = f'https://{environment}.api.apply.avela.org/v1/graphql'

    print(f'Authenticating with Avela API ({environment})...')

    # Prepare the authentication request
    # Note: OAuth2 typically uses 'application/x-www-form-urlencoded' for token requests
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    # The data payload for OAuth2 client credentials flow
    data = {
        'grant_type': 'client_credentials',  # Type of OAuth2 flow
        'client_id': client_id,  # Your client identifier
        'client_secret': client_secret,  # Your client secret (keep secure!)
        'audience': audience,  # The API you want to access
    }

    try:
        # Make the POST request to get the token
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)

        # Raise an exception if the request failed (4xx or 5xx status codes)
        response.raise_for_status()

        # Parse the JSON response
        token_data = response.json()

        # Extract the access token from the response
        access_token = token_data.get('access_token')
        if not access_token:
            print('Error: No access token in response!')
            print(f'Response: {token_data}')
            sys.exit(1)

        expires_in = token_data.get('expires_in', 86400)  # Default 24 hours

        print(f'✓ Authentication successful! Token expires in {expires_in} seconds.')

        return access_token

    except requests.exceptions.RequestException as e:
        print('Error: Authentication failed!')
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
    Retrieve applicants from the Avela API.

    This function:
    1. Makes GET requests to the /api/applicants endpoint
    2. Automatically handles pagination to retrieve all records
    3. Returns a list of all applicants

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev, dev2)
        limit: Number of records to fetch per page (max: 1000)
        reference_ids: Optional list of reference IDs to filter by

    Returns:
        List of applicant dictionaries

    Raises:
        requests.RequestException: If API request fails
    """
    # Build the API base URL based on environment
    # The V2 API is mounted at /api/rest/v2 path
    api_base_url = f'https://{environment}.execute-api.apply.avela.org/api/rest/v2/'

    applicants_url = urljoin(api_base_url, 'applicants')

    # Prepare headers with the access token
    # The API expects the token in the 'Authorization' header with 'Bearer' prefix
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # Prepare query parameters
    params = {
        'limit': min(limit, 1000)  # API maximum is 1000 records per request
    }

    # If filtering by specific reference IDs, add them to params
    if reference_ids:
        params['reference_id'] = reference_ids

    print(f'\nFetching applicants from {environment} environment...')

    all_applicants = []
    offset = 0
    page = 1

    # Pagination loop: keep fetching until we get fewer records than requested
    while True:
        params['offset'] = offset

        print(f'  Fetching page {page} (offset: {offset})...', end=' ')

        try:
            # Make the GET request to fetch applicants
            response = requests.get(
                applicants_url, headers=headers, params=params, timeout=30
            )

            # Check if request was successful
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()

            # Extract the applicants array from the response
            applicants = data.get('applicants', [])

            print(f'Retrieved {len(applicants)} applicants')

            # Add these applicants to our collection
            all_applicants.extend(applicants)

            # If we got no records or fewer than the limit, we've reached the end
            if not applicants or len(applicants) < params['limit']:
                break

            # Move to the next page
            offset += params['limit']
            page += 1

        except requests.exceptions.RequestException as e:
            print('\nError: Failed to fetch applicants!')
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
    Print a formatted summary of applicants to the console.

    This displays a table with key information about each applicant.

    Args:
        applicants: List of applicant dictionaries
    """
    if not applicants:
        print('\nNo applicants found.')
        return

    print('\n' + '=' * 120)
    print(f'APPLICANTS SUMMARY ({len(applicants)} total)')
    print('=' * 120)

    # Print header
    header = f'{"Reference ID":<15} {"Name":<30} {"Email":<35} {"Birth Date":<12} {"City, State":<20}'
    print(header)
    print('-' * 120)

    # Print each applicant
    for applicant in applicants:
        reference_id = applicant.get('reference_id') or 'N/A'
        first_name = applicant.get('first_name') or ''
        middle_name = applicant.get('middle_name') or ''
        last_name = applicant.get('last_name') or ''

        # Build full name
        name_parts = [first_name, middle_name, last_name]
        full_name = ' '.join(part for part in name_parts if part) or 'N/A'

        email = applicant.get('email_address') or 'N/A'
        birth_date = applicant.get('birth_date') or 'N/A'
        city = applicant.get('city') or ''
        state = applicant.get('state') or ''
        location = f'{city}, {state}' if city or state else 'N/A'

        # Truncate long values to fit in columns
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
    Export applicants data to a CSV file.

    This creates a CSV file with all applicant fields that can be opened in
    Excel, Google Sheets, or any spreadsheet application.

    Args:
        applicants: List of applicant dictionaries
        filename: Output filename (defaults to timestamped filename)
    """
    if not applicants:
        print('No applicants to export.')
        return

    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'avela_applicants_{timestamp}.csv'

    # Determine all possible fields from the applicants data
    # This ensures we capture all fields even if some applicants have extra data
    all_fields = set()
    for applicant in applicants:
        all_fields.update(applicant.keys())

    # Define the preferred column order (common fields first)
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

    # Put preferred fields first, then any remaining fields alphabetically
    fieldnames = [f for f in preferred_order if f in all_fields]
    remaining_fields = sorted(all_fields - set(fieldnames))
    fieldnames.extend(remaining_fields)

    # Write to CSV file
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header row
            writer.writeheader()

            # Write all applicant rows
            writer.writerows(applicants)

        print(f'✓ Exported {len(applicants)} applicants to: {filename}')

    except OSError as e:
        print('Error: Failed to write CSV file!')
        print(f'Details: {e}')
        sys.exit(1)


# =============================================================================
# USER INPUT HELPERS
# =============================================================================


def prompt_for_reference_ids() -> list[str] | None:
    """
    Prompt the user to choose whether to fetch all applicants or filter by reference IDs.

    Returns:
        None if fetching all applicants, or a list of reference IDs to filter by
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
                print('Error: No reference IDs provided. Please try again.\n')
                continue

            # Split by comma and strip whitespace from each ID
            reference_ids = [rid.strip() for rid in ids_input.split(',') if rid.strip()]

            if not reference_ids:
                print('Error: No valid reference IDs provided. Please try again.\n')
                continue

            print(f'\n✓ Will filter by {len(reference_ids)} reference ID(s)')
            return reference_ids

        print('Error: Invalid choice. Please enter 1 or 2.\n')


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """
    Main execution function.

    This orchestrates the entire workflow:
    1. Load configuration
    2. Prompt user for filtering options
    3. Authenticate with the API
    4. Fetch applicants data
    5. Display and export the results
    """
    print('=' * 80)
    print('AVELA API INTEGRATION - APPLICANTS EXPORT')
    print('=' * 80)

    # Step 1: Load configuration from config.json
    config = load_config('config.json')

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    # Step 2: Ask user how they want to filter applicants
    reference_ids = prompt_for_reference_ids()

    # Step 3: Authenticate and get access token
    access_token = get_access_token(client_id, client_secret, environment)

    # Step 4: Fetch applicants from the API
    applicants = get_applicants(
        access_token=access_token, environment=environment, reference_ids=reference_ids
    )

    # Step 5: Display results to console
    print_applicants_summary(applicants)

    # Step 6: Export to CSV file
    export_to_csv(applicants)

    print('\n✓ Integration completed successfully!')
    print('=' * 80)


if __name__ == '__main__':
    """
    Entry point when script is run directly.

    Usage:
        python avela_api_client.py

    Make sure you have created a 'config.json' file with your credentials first!
    """
    main()
