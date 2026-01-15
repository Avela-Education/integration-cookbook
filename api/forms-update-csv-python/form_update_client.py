#!/usr/bin/env python3
"""
Avela Form Service API Integration Script

This script demonstrates how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Look up form templates to get question UUIDs from question keys
3. Read form updates from a CSV file
4. Update form answers via the Form Service API

Author: Avela Education
License: MIT
"""

import argparse
import csv
import json
import sys
from pathlib import Path

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
        environment: Target environment (prod, qa, uat, dev)

    Returns:
        Access token string (JWT format)

    Raises:
        requests.RequestException: If authentication fails
    """
    # Build the authentication URL based on environment
    if environment == 'prod':
        auth_url = 'https://auth.avela.org/oauth/token'
        audience = 'https://api.apply.avela.org/v1/graphql'
    else:
        auth_url = f'https://{environment}.auth.avela.org/oauth/token'
        audience = f'https://{environment}.api.apply.avela.org/v1/graphql'

    print(f'Authenticating with Avela API ({environment})...')

    # Prepare the authentication request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    # The data payload for OAuth2 client credentials flow
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': audience,
    }

    try:
        # Make the POST request to get the token
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
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
# CUSTOMER API - FORM OPERATIONS
# =============================================================================


def get_customer_api_base_url(environment: str) -> str:
    """
    Get the Customer API base URL for the given environment.

    Args:
        environment: Target environment (prod, qa, uat, dev)

    Returns:
        Base URL for the Customer API
    """
    return f'https://{environment}.execute-api.apply.avela.org/api/rest/v2/'


def update_form_questions(
    access_token: str, environment: str, form_id: str, questions: list[dict]
) -> bool:
    """
    Update multiple questions/answers in a form using the Customer API.

    This uses the POST /forms/{id}/questions endpoint which allows updating
    answers by question key without needing to fetch the form template.

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev)
        form_id: UUID of the form instance
        questions: List of question dictionaries with keys:
            - key: Question key (e.g., "internal1")
            - type: Question type (e.g., "FreeText", "Email", etc.)
            - answer: Answer object matching the question type

    Returns:
        True if successful, False otherwise
    """
    base_url = get_customer_api_base_url(environment)
    questions_url = f'{base_url}forms/{form_id}/questions'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    payload = {'questions': questions}

    try:
        response = requests.post(questions_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        return True

    except requests.exceptions.RequestException as e:
        print('  ✗ Failed to update questions!')
        print(f'    Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'    Response: {e.response.text}')
        return False


def build_answer_object(question_type: str, answer_value: str) -> dict:
    """
    Build the answer object based on question type.

    Different question types require different answer structures.

    Args:
        question_type: The type of question (FreeText, Email, PhoneNumber, etc.)
        answer_value: The answer value as a string

    Returns:
        Answer object formatted for the Customer API
    """
    # Map question types to their answer structure
    answer_type_map = {
        'FreeText': 'free_text',
        'Email': 'email',
        'PhoneNumber': 'phone_number',
        'Number': 'number',
        'Date': 'date',
        'SingleSelect': 'single_select',
        'MultiSelect': 'multi_select',
        'Address': 'address',
    }

    answer_key = answer_type_map.get(question_type, 'free_text')

    # For most types, the answer is simply {type: {value: answer_value}}
    if question_type in ['FreeText', 'Email', 'PhoneNumber', 'Date', 'SingleSelect']:
        return {answer_key: {'value': answer_value}}

    # For Number, convert to numeric type
    if question_type == 'Number':
        try:
            return {answer_key: {'value': float(answer_value)}}
        except ValueError:
            return {answer_key: {'value': answer_value}}

    # For MultiSelect, answer is just {'options': [...]} (not nested under multi_select)
    # Options can match by id, label, or value - only include fields that have real values
    if question_type == 'MultiSelect':
        if not answer_value:
            return {'options': []}
        # Split comma-separated values and create option objects
        # Use 'value' field to match (same as SingleSelect) - API matches by id, label, or value
        option_objects = [{'value': val.strip()} for val in answer_value.split(',')]
        return {'options': option_objects}

    # Default fallback to free_text
    return {'free_text': {'value': answer_value}}


# =============================================================================
# CSV PROCESSING
# =============================================================================


def read_csv_updates(csv_path: str) -> list[dict]:
    """
    Read form update data from a CSV file.

    Expected CSV format:
    form_id,question_key,question_type,answer_value
    uuid-1,key1,FreeText,value1
    uuid-2,key2,Email,value2

    Note: question_type column is optional and defaults to FreeText

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of dictionaries with form_id, question_key, question_type, and answer_value

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

            # Validate required columns
            required_columns = {'form_id', 'question_key', 'answer_value'}
            if not required_columns.issubset(reader.fieldnames or []):
                missing = required_columns - set(reader.fieldnames or [])
                raise ValueError(f'CSV missing required columns: {missing}')

            # Check if question_type column exists
            has_type_column = 'question_type' in (reader.fieldnames or [])

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                # Skip empty rows
                if not any(row.values()):
                    continue

                # Validate row data
                if not row.get('form_id'):
                    print(f'Warning: Row {row_num} missing form_id, skipping')
                    continue

                if not row.get('question_key'):
                    print(f'Warning: Row {row_num} missing question_key, skipping')
                    continue

                # Get question type or default to FreeText
                question_type = (
                    row.get('question_type', 'FreeText').strip()
                    if has_type_column
                    else 'FreeText'
                )
                if not question_type:
                    question_type = 'FreeText'

                updates.append(
                    {
                        'form_id': row['form_id'].strip(),
                        'question_key': row['question_key'].strip(),
                        'question_type': question_type,
                        'answer_value': row['answer_value'],
                    }
                )

        print(f'✓ Read {len(updates)} updates from CSV file')
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
    Process all form updates from a CSV file.

    This is the main processing function that:
    1. Reads the CSV file
    2. Groups updates by form_id
    3. Builds question objects with answer structures
    4. Updates all questions for each form in a single API call

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev)
        csv_path: Path to the CSV file
        dry_run: If True, print what would be sent without making API calls

    Returns:
        Tuple of (successful_updates, failed_updates)
    """
    # Read updates from CSV
    updates = read_csv_updates(csv_path)

    if not updates:
        print('No updates to process.')
        return (0, 0)

    # Group updates by form_id to batch updates
    updates_by_form = {}
    for update in updates:
        form_id = update['form_id']
        if form_id not in updates_by_form:
            updates_by_form[form_id] = []
        updates_by_form[form_id].append(update)

    print(f'\nProcessing updates for {len(updates_by_form)} form(s)...\n')

    successful = 0
    failed = 0

    # Process each form's updates
    for form_id, form_updates in updates_by_form.items():
        print(f'Form: {form_id}')
        print(f'  {len(form_updates)} update(s) to process')

        # Build questions array for API request
        questions = []
        for update in form_updates:
            question_key = update['question_key']
            question_type = update['question_type']
            answer_value = update['answer_value']

            # Build the answer object based on question type
            answer_obj = build_answer_object(question_type, answer_value)

            questions.append(
                {'key': question_key, 'type': question_type, 'answer': answer_obj}
            )

            print(f'  • {question_key} ({question_type}) = "{answer_value}"')
            if dry_run:
                print(f'    → {answer_obj}')

        if dry_run:
            print(f'  [DRY RUN] Would submit {len(questions)} question(s) to API')
            successful += len(form_updates)
        else:
            # Update all questions in a single API call
            print(f'  Submitting {len(questions)} question(s) to API...', end=' ')
            success = update_form_questions(access_token, environment, form_id, questions)

            if success:
                print('✓')
                successful += len(form_updates)
            else:
                failed += len(form_updates)

        print()  # Blank line between forms

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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Update form answers in bulk from a CSV file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be sent without making API calls',
    )
    parser.add_argument(
        '--csv',
        default='sample_updates.csv',
        help='Path to CSV file (default: sample_updates.csv)',
    )
    args = parser.parse_args()

    print('=' * 80)
    print('AVELA FORM SERVICE API - UPDATE ANSWERS FROM CSV')
    if args.dry_run:
        print('[DRY RUN MODE - No changes will be made]')
    print('=' * 80)
    print()

    # Step 1: Load configuration from config.json
    config = load_config('config.json')

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    # Step 2: Authenticate and get access token (skip in dry-run mode)
    if args.dry_run:
        print(f'[DRY RUN] Skipping authentication (environment: {environment})')
        access_token = 'dry-run-token'
    else:
        access_token = get_access_token(client_id, client_secret, environment)
    print()

    # Step 3: Process updates from CSV
    successful, failed = process_csv_updates(
        access_token, environment, args.csv, dry_run=args.dry_run
    )

    # Step 4: Report results
    print('=' * 80)
    print('RESULTS')
    print('=' * 80)
    print(f'✓ Successful updates: {successful}')
    print(f'✗ Failed updates: {failed}')
    print(f'Total: {successful + failed}')
    print('=' * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    """
    Entry point when script is run directly.

    Usage:
        python form_update_client.py                    # Run with sample_updates.csv
        python form_update_client.py --dry-run          # Test without making API calls
        python form_update_client.py --csv myfile.csv   # Use a different CSV file
        python form_update_client.py --dry-run --csv /path/to/test.csv

    Make sure you have:
    1. Created a 'config.json' file with your credentials
    2. Created a CSV file with your updates (or use sample_updates.csv)
    """
    main()
