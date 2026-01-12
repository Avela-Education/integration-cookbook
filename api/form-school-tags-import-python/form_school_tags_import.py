#!/usr/bin/env python3
"""
Form-School Tags CSV Import

Import or delete form-school tag assignments from a CSV via the Avela Customer API.

Usage:
    python form_school_tags_import.py tags.csv [--dry-run] [--start-row N] [--limit N]
    python form_school_tags_import.py tags.csv --delete [--dry-run]

CSV Format:
    Form ID,School ID,Tag Name
    (or App ID as alias for Form ID)

The script automatically looks up tag UUIDs from the API using the tag names
provided in the CSV. Tag name matching is case-insensitive.

Use --delete to remove tags instead of adding them (useful for resetting tests).
"""

import argparse
import csv
import json
import re
import sys

import requests

# UUID validation pattern (8-4-4-4-12 hex characters)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE
)


# =============================================================================
# CONFIGURATION
# =============================================================================


def load_config(config_path: str = 'config.json') -> dict:
    """
    Load and validate configuration from JSON file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary with client_id, client_secret, environment
    """
    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f'Error: Configuration file not found: {config_path}')
        print('Please copy config.example.json to config.json and add your credentials.')
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON in configuration file: {e}')
        sys.exit(1)

    required_fields = ['client_id', 'client_secret', 'environment']
    missing = [f for f in required_fields if not config.get(f)]
    if missing:
        print(f'Error: Missing required configuration fields: {", ".join(missing)}')
        sys.exit(1)

    return config


# =============================================================================
# AUTHENTICATION
# =============================================================================


def get_access_token(client_id: str, client_secret: str, environment: str) -> str:
    """
    Get bearer token via OAuth2 client credentials flow.

    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        environment: Target environment (prod, staging, uat, qa, dev, dev2)

    Returns:
        Access token string
    """
    if environment == 'prod':
        token_url = 'https://auth.avela.org/oauth/token'
        audience = 'https://api.apply.avela.org/v1/graphql'
    elif environment == 'staging':
        # Staging uses a direct Auth0 URL (exception to the normal pattern)
        token_url = 'https://avela-staging.us.auth0.com/oauth/token'
        audience = 'https://staging.api.apply.avela.org/v1/graphql'
    else:
        token_url = f'https://{environment}.auth.avela.org/oauth/token'
        audience = f'https://{environment}.api.apply.avela.org/v1/graphql'

    print(f'Authenticating with Avela API ({environment})...', file=sys.stderr)

    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': audience,
    }

    try:
        response = requests.post(
            token_url,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            print('Error: No access token in response', file=sys.stderr)
            sys.exit(1)

        print('✓ Authentication successful', file=sys.stderr)
        return access_token

    except requests.exceptions.RequestException as e:
        print(f'Error: Authentication failed: {e}', file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}', file=sys.stderr)
        sys.exit(1)


# =============================================================================
# VALIDATION
# =============================================================================


def validate_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    return bool(UUID_PATTERN.match(value))


# =============================================================================
# CSV PROCESSING
# =============================================================================


def read_csv(
    filepath: str, start_row: int = 0, limit: int | None = None
) -> list[tuple[str, str, str, int]]:
    """
    Parse CSV file and return tag assignments.

    Expected CSV columns:
    - Form ID (or App ID as alias)
    - School ID
    - Tag Name (the display name of the tag, case-insensitive)

    Args:
        filepath: Path to CSV file
        start_row: Number of data rows to skip (default: 0)
        limit: Maximum number of rows to process (default: None = all)

    Returns:
        List of (form_id, school_id, tag_name, csv_line_number) tuples
    """
    records = []

    try:
        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Normalize headers to uppercase for case-insensitive matching
            if reader.fieldnames:
                reader.fieldnames = [field.upper().strip() for field in reader.fieldnames]

            # Validate required columns (Form ID or App ID alias)
            headers = set(reader.fieldnames or [])
            has_form_id = 'FORM ID' in headers or 'APP ID' in headers
            if not has_form_id:
                print(
                    'Error: CSV must have "Form ID" or "App ID" column', file=sys.stderr
                )
                sys.exit(1)
            if 'SCHOOL ID' not in headers:
                print('Error: CSV must have "School ID" column', file=sys.stderr)
                sys.exit(1)

            # Check for Tag Name column (prefer "Tag Name", fall back to "Tag ID" for compatibility)
            if 'TAG NAME' not in headers and 'TAG ID' not in headers:
                print(
                    'Error: CSV must have "Tag Name" or "Tag ID" column', file=sys.stderr
                )
                sys.exit(1)
            tag_col = 'TAG NAME' if 'TAG NAME' in headers else 'TAG ID'

            # Determine form ID column name
            form_id_col = 'FORM ID' if 'FORM ID' in headers else 'APP ID'

            for row_idx, row in enumerate(reader):
                csv_line = row_idx + 2  # +2 for 1-indexed and header row

                # Skip rows if start_row specified
                if row_idx < start_row:
                    continue

                # Stop if limit reached
                if limit is not None and len(records) >= limit:
                    break

                form_id = row.get(form_id_col, '').strip()
                school_id = row.get('SCHOOL ID', '').strip()
                tag_name = row.get(tag_col, '').strip()

                records.append((form_id, school_id, tag_name, csv_line))

    except FileNotFoundError:
        print(f'Error: CSV file not found: {filepath}', file=sys.stderr)
        sys.exit(1)

    return records


# =============================================================================
# API OPERATIONS
# =============================================================================


def get_api_base_url(environment: str) -> str:
    """Get API base URL for environment."""
    # All environments (including prod and staging) follow the same pattern
    return f'https://{environment}.execute-api.apply.avela.org/api/rest/v2'


def get_form(access_token: str, environment: str, form_id: str) -> dict:
    """
    Fetch a single form to get its enrollment period.

    This is used to determine which enrollment period the tags belong to,
    so we can fetch the correct set of available tag names.

    Args:
        access_token: Bearer token for API authentication
        environment: Target environment (prod, uat, qa, dev)
        form_id: UUID of the form to fetch

    Returns:
        Form data dict containing enrollment_period.id

    Raises:
        SystemExit: If form is not found or API call fails
    """
    base_url = get_api_base_url(environment)
    url = f'{base_url}/forms/{form_id}'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 404:
            print(f'Error: Form not found: {form_id}', file=sys.stderr)
            sys.exit(1)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f'Error: Failed to fetch form: {e}', file=sys.stderr)
        sys.exit(1)


def fetch_tags(
    access_token: str, environment: str, enrollment_period_id: str
) -> dict[str, str]:
    """
    Fetch all tags for an enrollment period and build a name-to-ID lookup.

    This lookup dictionary is used to resolve tag names from the CSV
    to their corresponding UUIDs for API calls. The lookup is case-insensitive.

    Args:
        access_token: Bearer token for API authentication
        environment: Target environment (prod, uat, qa, dev)
        enrollment_period_id: UUID of the enrollment period to fetch tags for

    Returns:
        Dictionary mapping lowercase tag names to tag UUIDs
        Example: {"eligible for lottery": "abc-123-...", ...}

    Raises:
        SystemExit: If API call fails
    """
    base_url = get_api_base_url(environment)
    url = f'{base_url}/tags'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    params = {'enrollment_period_id': enrollment_period_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Build case-insensitive lookup: {lowercase_name: id}
        tag_cache: dict[str, str] = {}
        for tag in data.get('tags', []):
            name = tag.get('name', '').lower()
            tag_id = tag.get('id', '')
            if name and tag_id:
                tag_cache[name] = tag_id

        return tag_cache

    except requests.exceptions.RequestException as e:
        print(f'Error: Failed to fetch tags: {e}', file=sys.stderr)
        sys.exit(1)


def resolve_tag_name(
    tag_name: str, tag_cache: dict[str, str]
) -> tuple[str | None, str | None]:
    """
    Look up a tag name in the cache and return its UUID.

    Matching is case-insensitive. If the tag is not found, returns a helpful
    error message listing available tag names.

    Args:
        tag_name: The tag name from the CSV (case-insensitive)
        tag_cache: Dictionary mapping lowercase names to UUIDs

    Returns:
        Tuple of (tag_id, error_message) - one will be None
        - Success: (tag_id, None)
        - Failure: (None, "Tag 'xyz' not found. Available: ...")
    """
    # Look up using lowercase for case-insensitive matching
    tag_id = tag_cache.get(tag_name.lower())

    if tag_id:
        return tag_id, None

    # Tag not found - build helpful error message
    available = ', '.join(sorted(tag_cache.keys())[:5])  # Show first 5
    if len(tag_cache) > 5:
        available += f', ... ({len(tag_cache)} total)'

    return None, f"Tag '{tag_name}' not found. Available: {available}"


def add_tag(
    access_token: str, environment: str, form_id: str, school_id: str, tag_id: str
) -> tuple[bool, int, str]:
    """
    Add a tag to a form-school choice via the Customer API.

    Args:
        access_token: Bearer token
        environment: Target environment
        form_id: Form UUID
        school_id: School UUID
        tag_id: Tag UUID

    Returns:
        Tuple of (success: bool, affected_rows: int, error_message: str)
    """
    base_url = get_api_base_url(environment)
    url = f'{base_url}/tags/forms/{form_id}/schools/{school_id}'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(
            url, json={'tag_id': tag_id}, headers=headers, timeout=30
        )

        if response.status_code == 401:
            return False, 0, 'Unauthorized (401)'

        if response.status_code == 404:
            return False, 0, 'Form, school, or tag not found (404)'

        response.raise_for_status()
        data = response.json()
        affected_rows = data.get('affected_rows', 0)
        return True, affected_rows, ''

    except requests.exceptions.Timeout:
        return False, 0, 'Request timeout'
    except requests.exceptions.RequestException as e:
        return False, 0, str(e)


def delete_tag(
    access_token: str, environment: str, form_id: str, school_id: str, tag_id: str
) -> tuple[bool, int, str]:
    """
    Remove a tag from a form-school choice via the Customer API.

    Args:
        access_token: Bearer token
        environment: Target environment
        form_id: Form UUID
        school_id: School UUID
        tag_id: Tag UUID

    Returns:
        Tuple of (success: bool, affected_rows: int, error_message: str)
    """
    base_url = get_api_base_url(environment)
    url = f'{base_url}/tags/forms/{form_id}/schools/{school_id}'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.delete(
            url, json={'tag_id': tag_id}, headers=headers, timeout=30
        )

        if response.status_code == 401:
            return False, 0, 'Unauthorized (401)'

        if response.status_code == 404:
            return False, 0, 'Form, school, or tag not found (404)'

        response.raise_for_status()
        data = response.json()
        affected_rows = data.get('affected_rows', 0)
        return True, affected_rows, ''

    except requests.exceptions.Timeout:
        return False, 0, 'Request timeout'
    except requests.exceptions.RequestException as e:
        return False, 0, str(e)


# =============================================================================
# MAIN PROCESSING
# =============================================================================


def process_tags(
    records: list[tuple[str, str, str, int]],
    access_token: str,
    environment: str,
    tag_cache: dict[str, str],
    dry_run: bool = False,
    delete_mode: bool = False,
) -> tuple[int, int, int, list[tuple[int, str]]]:
    """
    Process tag assignments from CSV records.

    For each record, validates the form and school UUIDs, resolves the tag name
    to its UUID using the tag cache, then calls the API to add or remove the tag.

    Args:
        records: List of (form_id, school_id, tag_name, csv_line) tuples
        access_token: Bearer token for API authentication
        environment: Target environment (prod, uat, qa, dev)
        tag_cache: Dictionary mapping lowercase tag names to UUIDs
        dry_run: If True, validate only without making API calls
        delete_mode: If True, remove tags instead of adding them

    Returns:
        Tuple of (affected, not_found, error_count, errors_list)
        - In add mode: (inserted, already_existed, errors, error_list)
        - In delete mode: (deleted, not_found, errors, error_list)
    """
    affected = 0  # inserted (add mode) or deleted (delete mode)
    skipped = 0  # already_existed (add mode) or not_found (delete mode)
    errors: list[tuple[int, str]] = []
    total = len(records)

    # Choose the appropriate API function
    api_fn = delete_tag if delete_mode else add_tag

    for idx, (form_id, school_id, tag_name, csv_line) in enumerate(records):
        # Progress update every 100 rows or at end
        if (idx + 1) % 100 == 0 or idx + 1 == total:
            pct = int((idx + 1) / total * 100)
            print(f'  {idx + 1}/{total} ({pct}%)...', file=sys.stderr)

        # Validate Form ID and School ID are valid UUIDs
        if not validate_uuid(form_id):
            errors.append((csv_line, f'Invalid UUID in Form ID: {form_id}'))
            continue
        if not validate_uuid(school_id):
            errors.append((csv_line, f'Invalid UUID in School ID: {school_id}'))
            continue

        # Resolve tag name to UUID using the cache
        tag_id, tag_error = resolve_tag_name(tag_name, tag_cache)
        if tag_error:
            errors.append((csv_line, tag_error))
            continue

        if dry_run:
            # In dry-run mode, count as "would be affected"
            affected += 1
            continue

        # Make API call to add or remove the tag
        success, affected_rows, error_msg = api_fn(
            access_token, environment, form_id, school_id, tag_id
        )

        if not success:
            if 'Unauthorized' in error_msg:
                print(f'\nError: {error_msg}', file=sys.stderr)
                print('Stopping due to authentication failure.', file=sys.stderr)
                sys.exit(1)
            errors.append((csv_line, error_msg))
        elif affected_rows > 0:
            affected += 1
        else:
            skipped += 1

    return affected, skipped, len(errors), errors


def main():
    parser = argparse.ArgumentParser(
        description='Import or delete form-school tag assignments from CSV via Avela Customer API'
    )
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Remove tags instead of adding them (useful for resetting tests)',
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='Validate CSV without making API calls'
    )
    parser.add_argument(
        '--start-row', type=int, default=0, help='Skip first N data rows (default: 0)'
    )
    parser.add_argument('--limit', type=int, default=None, help='Process only N rows')
    parser.add_argument(
        '--config',
        default='config.json',
        help='Path to config file (default: config.json)',
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Display mode information
    if args.delete:
        print(
            'DELETE MODE - Will remove tags from form-school combinations',
            file=sys.stderr,
        )
    if args.dry_run:
        print('DRY RUN MODE - Will validate but not modify data', file=sys.stderr)

    # Authenticate with the API
    # Note: We always authenticate because we need to fetch form/tag data even in dry-run
    access_token = get_access_token(
        config['client_id'], config['client_secret'], config['environment']
    )

    # Read CSV to get form IDs and tag names
    print(f'\nReading CSV: {args.csv_file}', file=sys.stderr)
    records = read_csv(args.csv_file, args.start_row, args.limit)

    if not records:
        print('No records to process.', file=sys.stderr)
        sys.exit(0)

    print(f'✓ Found {len(records):,} rows to process', file=sys.stderr)

    if args.start_row > 0:
        print(f'  (skipped first {args.start_row} data rows)', file=sys.stderr)

    # Get enrollment period from the first form
    # This determines which set of tags are available for lookup
    first_form_id = records[0][0]  # form_id is first element of tuple
    print(
        f'\nFetching enrollment period from form: {first_form_id[:8]}...', file=sys.stderr
    )
    form_data = get_form(access_token, config['environment'], first_form_id)
    enrollment_period_id = form_data.get('enrollment_period', {}).get('id')

    if not enrollment_period_id:
        print('Error: Could not determine enrollment period from form', file=sys.stderr)
        sys.exit(1)

    print(f'✓ Enrollment period: {enrollment_period_id[:8]}...', file=sys.stderr)

    # Fetch all tags for this enrollment period and build lookup cache
    # This cache maps tag names (lowercase) to their UUIDs
    print('Fetching available tags...', file=sys.stderr)
    tag_cache = fetch_tags(access_token, config['environment'], enrollment_period_id)
    print(f'✓ Found {len(tag_cache)} tags', file=sys.stderr)

    # Process tags using the cached lookup
    action = 'Deleting' if args.delete else 'Processing'
    print(f'\n{action}...', file=sys.stderr)
    affected, skipped, error_count, errors = process_tags(
        records, access_token, config['environment'], tag_cache, args.dry_run, args.delete
    )

    # Print results with labels appropriate to the mode
    print('\nResults:', file=sys.stderr)
    if args.dry_run:
        action_label = 'Would delete' if args.delete else 'Would insert'
        print(f'  {action_label}: {affected:,}', file=sys.stderr)
        print(f'  Validation errors: {error_count:,}', file=sys.stderr)
    elif args.delete:
        print(f'  Deleted: {affected:,}', file=sys.stderr)
        print(f'  Not found (already removed): {skipped:,}', file=sys.stderr)
        print(f'  Errors: {error_count:,}', file=sys.stderr)
    else:
        print(f'  Inserted: {affected:,}', file=sys.stderr)
        print(f'  Already existed: {skipped:,}', file=sys.stderr)
        print(f'  Errors: {error_count:,}', file=sys.stderr)

    # Print errors
    if errors:
        print('\nErrors:', file=sys.stderr)
        for csv_line, msg in errors[:20]:  # Limit to first 20
            print(f'  Line {csv_line}: {msg}', file=sys.stderr)
        if len(errors) > 20:
            print(f'  ... and {len(errors) - 20} more errors', file=sys.stderr)

    # Exit with error code if there were failures
    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
