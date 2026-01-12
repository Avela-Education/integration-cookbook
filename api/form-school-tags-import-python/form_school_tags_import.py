#!/usr/bin/env python3
"""
Form-School Tags CSV Import

Bulk import or delete form-school tag assignments from a CSV file using the
Avela Customer API v2. Tags are specified by name (not UUID) and automatically
resolved via the API.

Usage:
    python form_school_tags_import.py tags.csv                    # Add tags
    python form_school_tags_import.py tags.csv --dry-run          # Validate only
    python form_school_tags_import.py tags.csv --delete           # Remove tags
    python form_school_tags_import.py tags.csv --limit 10         # Test with 10 rows
    python form_school_tags_import.py tags.csv --start-row 100    # Resume from row 100

CSV Format:
    Form ID,School ID,Tag Name
    e4c2f10d-...,a1b2c3d4-...,Eligible For Lottery

Required API Permissions:
    - form:read (to fetch enrollment period from first form)
    - tag:read (to fetch available tags for name-to-UUID lookup)
    - tag:create (to add tags to form-school combinations)
    - tag:delete (only if using --delete mode)

All forms in the CSV must belong to the same enrollment period.
"""

import argparse
import csv
import re
import sys

from avela_client import AvelaClient, create_client_from_config

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE
)


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

            # Check for Tag Name column
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


def get_form(client: AvelaClient, form_id: str) -> dict:
    """
    Fetch a single form to get its enrollment period.

    Args:
        client: Authenticated AvelaClient instance
        form_id: UUID of the form to fetch

    Returns:
        Form data dict containing enrollment_period.id
    """
    response = client.get(f'/forms/{form_id}')

    if response.status_code == 404:
        print(f'Error: Form not found: {form_id}', file=sys.stderr)
        sys.exit(1)

    response.raise_for_status()
    return response.json().get('form', {})


def fetch_tags(client: AvelaClient, enrollment_period_id: str) -> dict[str, str]:
    """
    Fetch all tags for an enrollment period and build a name-to-ID lookup.

    Args:
        client: Authenticated AvelaClient instance
        enrollment_period_id: UUID of the enrollment period

    Returns:
        Dictionary mapping lowercase tag names to tag UUIDs
    """
    response = client.get('/tags', params={'enrollment_period_id': enrollment_period_id})
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


def resolve_tag_name(
    tag_name: str, tag_cache: dict[str, str]
) -> tuple[str | None, str | None]:
    """
    Look up a tag name in the cache and return its UUID.

    Args:
        tag_name: The tag name from the CSV (case-insensitive)
        tag_cache: Dictionary mapping lowercase names to UUIDs

    Returns:
        Tuple of (tag_id, error_message) - one will be None
    """
    tag_id = tag_cache.get(tag_name.lower())

    if tag_id:
        return tag_id, None

    # Tag not found - build helpful error message
    available = ', '.join(sorted(tag_cache.keys())[:5])
    if len(tag_cache) > 5:
        available += f', ... ({len(tag_cache)} total)'

    return None, f"Tag '{tag_name}' not found. Available: {available}"


def add_tag(
    client: AvelaClient, form_id: str, school_id: str, tag_id: str
) -> tuple[bool, int, str]:
    """
    Add a tag to a form-school choice via the Customer API.

    Returns:
        Tuple of (success: bool, affected_rows: int, error_message: str)
    """
    try:
        response = client.post(
            f'/tags/forms/{form_id}/schools/{school_id}',
            json={'tag_id': tag_id},
        )

        if response.status_code == 401:
            return False, 0, 'Unauthorized (401)'

        if response.status_code == 404:
            return False, 0, 'Form, school, or tag not found (404)'

        response.raise_for_status()
        data = response.json()
        affected_rows = data.get('affected_rows', 0)
        return True, affected_rows, ''

    except Exception as e:
        return False, 0, str(e)


def delete_tag(
    client: AvelaClient, form_id: str, school_id: str, tag_id: str
) -> tuple[bool, int, str]:
    """
    Remove a tag from a form-school choice via the Customer API.

    Returns:
        Tuple of (success: bool, affected_rows: int, error_message: str)
    """
    try:
        response = client.delete(
            f'/tags/forms/{form_id}/schools/{school_id}',
            json={'tag_id': tag_id},
        )

        if response.status_code == 401:
            return False, 0, 'Unauthorized (401)'

        if response.status_code == 404:
            return False, 0, 'Form, school, or tag not found (404)'

        response.raise_for_status()
        data = response.json()
        affected_rows = data.get('affected_rows', 0)
        return True, affected_rows, ''

    except Exception as e:
        return False, 0, str(e)


# =============================================================================
# MAIN PROCESSING
# =============================================================================


def process_tags(
    records: list[tuple[str, str, str, int]],
    client: AvelaClient,
    tag_cache: dict[str, str],
    dry_run: bool = False,
    delete_mode: bool = False,
) -> tuple[int, int, int, list[tuple[int, str]]]:
    """
    Process tag assignments from CSV records.

    Args:
        records: List of (form_id, school_id, tag_name, csv_line) tuples
        client: Authenticated AvelaClient instance
        tag_cache: Dictionary mapping lowercase tag names to UUIDs
        dry_run: If True, validate only without making API calls
        delete_mode: If True, remove tags instead of adding them

    Returns:
        Tuple of (affected, skipped, error_count, errors_list)
    """
    affected = 0
    skipped = 0
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
            affected += 1
            continue

        # Make API call to add or remove the tag
        success, affected_rows, error_msg = api_fn(client, form_id, school_id, tag_id)

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
        help='Remove tags instead of adding them',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate CSV and resolve tags without modifying data',
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

    # Display mode information
    if args.delete:
        print(
            'DELETE MODE - Will remove tags from form-school combinations',
            file=sys.stderr,
        )
    if args.dry_run:
        print('DRY RUN MODE - Will validate but not modify data', file=sys.stderr)

    # Create client from config (handles authentication automatically)
    try:
        client = create_client_from_config(args.config)
    except FileNotFoundError:
        print(f'Error: Configuration file not found: {args.config}', file=sys.stderr)
        print('Please copy config.example.json to config.json and add your credentials.')
        sys.exit(1)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    # Read CSV to get form IDs and tag names
    print(f'\nReading CSV: {args.csv_file}', file=sys.stderr)
    records = read_csv(args.csv_file, args.start_row, args.limit)

    if not records:
        print('No records to process.', file=sys.stderr)
        sys.exit(0)

    print(f'Found {len(records):,} rows to process', file=sys.stderr)

    if args.start_row > 0:
        print(f'  (skipped first {args.start_row} data rows)', file=sys.stderr)

    # Get enrollment period from the first form
    first_form_id = records[0][0]
    print(
        f'\nFetching enrollment period from form: {first_form_id[:8]}...', file=sys.stderr
    )
    form_data = get_form(client, first_form_id)
    enrollment_period_id = form_data.get('enrollment_period', {}).get('id')

    if not enrollment_period_id:
        print('Error: Could not determine enrollment period from form', file=sys.stderr)
        sys.exit(1)

    print(f'Enrollment period: {enrollment_period_id[:8]}...', file=sys.stderr)

    # Fetch all tags for this enrollment period
    print('Fetching available tags...', file=sys.stderr)
    tag_cache = fetch_tags(client, enrollment_period_id)
    print(f'Found {len(tag_cache)} tags', file=sys.stderr)

    # Process tags
    action = 'Deleting' if args.delete else 'Processing'
    print(f'\n{action}...', file=sys.stderr)
    affected, skipped, error_count, errors = process_tags(
        records, client, tag_cache, args.dry_run, args.delete
    )

    # Print results
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
        for csv_line, msg in errors[:20]:
            print(f'  Line {csv_line}: {msg}', file=sys.stderr)
        if len(errors) > 20:
            print(f'  ... and {len(errors) - 20} more errors', file=sys.stderr)

    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
