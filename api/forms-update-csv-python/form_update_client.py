#!/usr/bin/env python3
"""
Update form answers in bulk from a CSV file.

The script:
1. Logs in with OAuth2 client credentials
2. Reads form IDs, question keys, and answers from a CSV file
3. Sends each form's answers to the Customer API in one request

Answers go in by question key, so you never have to look up question UUIDs.

Author: Avela Education
License: MIT
"""

import argparse
import csv
import sys
from pathlib import Path

# We use the 'requests' library for making HTTP calls
# Install it with: pip install requests
import requests

try:
    from avela_client import environment_urls, load_settings, resolve_credentials
except ImportError:
    print('Error: the shared Avela client is not installed in this environment.')
    print("Install this recipe's dependencies and try again:")
    print('    pip install -r requirements.txt')
    sys.exit(1)

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_config(profile: str | None = None) -> dict:
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

    # OAuth2 token requests are form encoded, not JSON
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
            print(f'Response: {token_data}')
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
# CUSTOMER API - FORM OPERATIONS
# =============================================================================


def get_customer_api_base_url(environment: str) -> str:
    """
    Build the Customer API base URL for an environment.

    Args:
        environment: Which environment to use (prod, qa, uat, dev)

    Returns:
        Base URL for the Customer API
    """
    _, base_url, _ = environment_urls(environment)
    return base_url + '/'


def update_form_questions(
    access_token: str, environment: str, form_id: str, questions: list[dict]
) -> bool:
    """
    Update several answers on one form, in a single request.

    Uses POST /forms/{id}/questions, which takes question keys. That saves you
    from fetching the form template to look up question UUIDs.

    Args:
        access_token: Bearer token from authentication
        environment: Which environment to use (prod, qa, uat, dev)
        form_id: UUID of the form
        questions: List of question dictionaries, each holding:
            - key: Question key (for example "internal1")
            - type: Question type (for example "FreeText" or "Email")
            - answer: Answer object matching the question type

    Returns:
        True if the update worked, False if it did not
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
        print('  ✗ Failed to update the questions.')
        print(f'    Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'    Response: {e.response.text}')
        return False


def build_answer_object(question_type: str, answer_value: str) -> dict:
    """
    Build the answer object for one question.

    Each question type wants its answer shaped differently, so this turns the
    plain text from the CSV into the shape that type expects.

    Args:
        question_type: Question type (FreeText, Email, PhoneNumber, and so on)
        answer_value: The answer, as text from the CSV

    Returns:
        Answer object formatted for the Customer API
    """
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

    # Most types take {type: {value: answer_value}}
    if question_type in ['FreeText', 'Email', 'PhoneNumber', 'Date', 'SingleSelect']:
        return {answer_key: {'value': answer_value}}

    # Number wants a real number, not text
    if question_type == 'Number':
        try:
            return {answer_key: {'value': float(answer_value)}}
        except ValueError:
            return {answer_key: {'value': answer_value}}

    # Grades answers are {grade: {value: "..."}}
    if question_type == 'Grades':
        return {'grade': {'value': answer_value}}

    # MultiSelect answers are {'options': [...]}, not nested under multi_select.
    # The API matches an option by id, label, or value, so 'value' is enough here,
    # the same way it is for SingleSelect.
    if question_type == 'MultiSelect':
        if not answer_value:
            return {'options': []}
        option_objects = [{'value': val.strip()} for val in answer_value.split(',')]
        return {'options': option_objects}

    # Address answers arrive as street1|street2|city|state|zip
    if question_type == 'Address':
        parts = answer_value.split('|')
        address_obj = {}
        if len(parts) >= 1 and parts[0].strip():
            address_obj['street_address'] = parts[0].strip()
        if len(parts) >= 2 and parts[1].strip():
            address_obj['street_address_line_2'] = parts[1].strip()
        if len(parts) >= 3 and parts[2].strip():
            address_obj['city'] = parts[2].strip()
        if len(parts) >= 4 and parts[3].strip():
            address_obj['state'] = parts[3].strip()
        if len(parts) >= 5 and parts[4].strip():
            address_obj['zip_code'] = parts[4].strip()
        return {answer_key: address_obj}

    # Anything else is treated as free text
    return {'free_text': {'value': answer_value}}


# =============================================================================
# CSV PROCESSING
# =============================================================================


def read_csv_updates(csv_path: str) -> list[dict]:
    """
    Read the updates out of a CSV file.

    The file looks like this:
    form_id,question_key,question_type,answer_value
    uuid-1,key1,FreeText,value1
    uuid-2,key2,Email,value2

    The question_type column is optional. Leave it out and every answer is
    treated as FreeText.

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of dictionaries with form_id, question_key, question_type, and answer_value

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

            required_columns = {'form_id', 'question_key', 'answer_value'}
            if not required_columns.issubset(reader.fieldnames or []):
                missing = required_columns - set(reader.fieldnames or [])
                raise ValueError(f'CSV missing required columns: {missing}')

            has_type_column = 'question_type' in (reader.fieldnames or [])

            for row_num, row in enumerate(reader, start=2):  # Row 2 is the first data row
                if not any(row.values()):
                    continue

                if not row.get('form_id'):
                    print(f'Warning: Row {row_num} missing form_id, skipping')
                    continue

                if not row.get('question_key'):
                    print(f'Warning: Row {row_num} missing question_key, skipping')
                    continue

                # Use the question type from the file, or FreeText if there is none
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
    Apply every update in a CSV file.

    Reads the file, groups the rows by form, builds each answer, and sends one
    request per form.

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

    # One request per form, so group the rows by form_id first
    updates_by_form = {}
    for update in updates:
        form_id = update['form_id']
        if form_id not in updates_by_form:
            updates_by_form[form_id] = []
        updates_by_form[form_id].append(update)

    print(f'\nProcessing updates for {len(updates_by_form)} form(s)...\n')

    successful = 0
    failed = 0

    for form_id, form_updates in updates_by_form.items():
        print(f'Form: {form_id}')
        print(f'  {len(form_updates)} update(s) to process')

        questions = []
        for update in form_updates:
            question_key = update['question_key']
            question_type = update['question_type']
            answer_value = update['answer_value']

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
    """Log in, apply every update in the CSV file, then report what happened."""
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
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    print('=' * 80)
    print('AVELA FORM SERVICE API - UPDATE ANSWERS FROM CSV')
    if args.dry_run:
        print('[DRY RUN MODE - No changes will be made]')
    print('=' * 80)
    print()

    # Step 1: Find credentials and any extra settings
    config = load_config(profile=args.profile)

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
    print(f'✓ Successful updates: {successful}')
    print(f'✗ Failed updates: {failed}')
    print(f'Total: {successful + failed}')
    print('=' * 80)

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    """
    Run the recipe.

    Usage:
        python form_update_client.py                    # Run with sample_updates.csv
        python form_update_client.py --dry-run          # Test without making API calls
        python form_update_client.py --csv myfile.csv   # Use a different CSV file
        python form_update_client.py --profile district-a  # Use a named credential set
        python form_update_client.py --dry-run --csv /path/to/test.csv

    Before you run it:
    1. Store your credentials (the README covers the keychain and environment variables)
    2. Write a CSV file of updates, or use sample_updates.csv
    """
    main()
