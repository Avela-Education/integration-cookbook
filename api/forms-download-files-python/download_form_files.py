#!/usr/bin/env python3
"""
Download every file attached to a list of Avela forms.

The script:
1. Logs in with OAuth2 client credentials
2. Asks the API for the file upload questions on each form, and the download
   links that go with them
3. Saves every file under a folder for its form and its question

Author: Avela Education
License: MIT
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

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
# UTILITIES
# =============================================================================


def chunk_list(items: list, size: int = 100) -> list[list]:
    """
    Split a list into smaller lists.

    Args:
        items: List to split
        size: Largest size of each piece (default: 100)

    Returns:
        List of lists, each holding up to 'size' items
    """
    return [items[i : i + size] for i in range(0, len(items), size)]


# =============================================================================
# CONFIGURATION LOADING
# =============================================================================


def load_config(profile: str | None = None, required: bool = True) -> dict:
    """
    Find credentials, and read any other settings from the config file.

    Credentials come from environment variables or the OS keychain. See
    resolve_credentials() in the shared avela_client module.
    Other settings, such as output_dir, pass through untouched.

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


def load_form_ids(file_path: str) -> list[str]:
    """
    Read form IDs from a text file, one per line.

    Blank lines and lines starting with # are skipped.

    Args:
        file_path: Path to the form IDs file

    Returns:
        List of form ID strings

    Raises:
        FileNotFoundError: If the file is missing
    """
    path = Path(file_path)

    if not path.exists():
        print(f"Error: Form IDs file '{file_path}' not found.")
        sys.exit(1)

    with open(path, encoding='utf-8') as f:
        form_ids = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith('#')
        ]

    if not form_ids:
        print(f"Error: No form IDs found in '{file_path}'")
        sys.exit(1)

    return form_ids


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
# FORM FILES API
# =============================================================================


def get_form_files(
    access_token: str,
    environment: str,
    form_ids: list[str],
) -> list[dict]:
    """
    Ask the API which files are attached to a batch of forms.

    Calls GET /rest/v2/forms/files. For each form it returns the file upload
    questions and a download link for every uploaded document. Those links are
    pre-signed, so they work without the access token and they expire.

    Args:
        access_token: Bearer token from authentication
        environment: Which environment to use (prod, qa, uat, dev)
        form_ids: The forms to ask about (up to 100 at a time)

    Returns:
        List of per-form response objects holding the file information

    Raises:
        requests.RequestException: If the request fails
    """
    _, api_base_url, _ = environment_urls(environment)
    files_url = urljoin(api_base_url + '/', 'forms/files')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # The form_id parameter takes a comma separated list
    params = {'form_id': ','.join(form_ids)}

    print(f'\nFetching file information for {len(form_ids)} form(s)...')

    try:
        response = requests.get(files_url, headers=headers, params=params, timeout=60)

        # A batch answer comes back as 207 Multi-Status, which is not an error
        if response.status_code not in [200, 207]:
            response.raise_for_status()

        data = response.json()

        # One entry per form, in a 'responses' array
        responses = data.get('responses', [])

        print(f'Received responses for {len(responses)} form(s)')

        return responses

    except requests.exceptions.RequestException as e:
        print('Error: Failed to fetch the form files.')
        print(f'Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}')
        sys.exit(1)


# =============================================================================
# FILE DOWNLOAD
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """
    Replace the characters an operating system will not accept in a filename.

    Args:
        filename: Original filename

    Returns:
        A filename you can safely write to disk
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[: 200 - len(ext)] + ext

    return filename


def download_file(url: str, output_path: Path) -> bool:
    """
    Download one file from a pre-signed URL.

    Args:
        url: Pre-signed download URL
        output_path: Where to save the file

    Returns:
        True if the download worked, False if it did not
    """
    try:
        # Read the file a piece at a time, so a large one fits in memory
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return True

    except requests.exceptions.RequestException as e:
        print(f'    Error downloading: {e}')
        return False
    except OSError as e:
        print(f'    Error writing file: {e}')
        return False


def download_all_files(
    form_responses: list[dict],
    output_dir: str | None = None,
) -> tuple[dict, str]:
    """
    Download every file named in the API responses.

    Each file lands in output_dir/form_<form_id>/<question_key>/<filename>.

    Args:
        form_responses: Per-form response objects from the API
        output_dir: Folder to download into (default: a timestamped folder)

    Returns:
        Tuple of (stats dict, output directory path)
    """
    if output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = f'form_files_{timestamp}'

    base_path = Path(output_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    stats = {
        'total_forms': 0,
        'total_files': 0,
        'downloaded': 0,
        'failed': 0,
        'skipped': 0,
    }

    print(f'\nDownloading files to: {base_path.absolute()}')
    print('-' * 60)

    for form_response in form_responses:
        # Skip forms the API could not return. The status arrives as either the
        # string '200' or the number 200, so compare it as text.
        status = form_response.get('status')
        if str(status) != '200':
            print(f'\nForm response error (status {status}), skipping')
            continue

        form_data = form_response.get('form', {})
        form_id = form_data.get('id', 'unknown')
        questions = form_data.get('questions', [])

        stats['total_forms'] += 1
        print(f'\nForm: {form_id}')

        for question in questions:
            # Only FileUpload questions can hold files
            if question.get('type') != 'FileUpload':
                continue

            question_id = question.get('id', 'unknown')
            question_key = question.get('key') or question_id

            answer = question.get('answer', {})
            files = answer.get('files', [])

            if not files:
                continue

            print(f'  Question: {question_key} ({len(files)} file(s))')

            for file_info in files:
                stats['total_files'] += 1

                file_id = file_info.get('id', 'unknown')
                filename = file_info.get('filename', f'file_{file_id}')
                download_url = file_info.get('download_url')
                file_status = file_info.get('status')

                # Some filenames arrive with folders in front, so keep the end
                if '/' in filename:
                    filename = filename.split('/')[-1]

                filename = sanitize_filename(filename)

                # No link means the file is not ready to download
                if not download_url:
                    print(f'    - {filename}: No download URL (status: {file_status})')
                    stats['skipped'] += 1
                    continue

                file_path = base_path / f'form_{form_id}' / question_key / filename

                # Two files with the same name: add _1, _2, and so on
                if file_path.exists():
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while file_path.exists():
                        new_filename = f'{name}_{counter}{ext}'
                        file_path = (
                            base_path / f'form_{form_id}' / question_key / new_filename
                        )
                        counter += 1

                print(f'    - {filename}...', end=' ', flush=True)

                if download_file(download_url, file_path):
                    print('OK')
                    stats['downloaded'] += 1
                else:
                    print('FAILED')
                    stats['failed'] += 1

    return stats, output_dir


def print_summary(stats: dict, output_dir: str) -> None:
    """
    Print the download totals.

    Args:
        stats: Dictionary of download counts
        output_dir: Folder the files were saved in
    """
    print('\n' + '=' * 60)
    print('DOWNLOAD SUMMARY')
    print('=' * 60)
    print(f'Forms processed:  {stats["total_forms"]}')
    print(f'Total files:      {stats["total_files"]}')
    print(f'Downloaded:       {stats["downloaded"]}')
    print(f'Failed:           {stats["failed"]}')
    print(f'Skipped:          {stats["skipped"]}')
    print(f'\nFiles saved to: {output_dir}')
    print('=' * 60)


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def get_form_ids_file(file_path: str | None = None) -> str:
    """
    Take the form IDs file from the command line, or ask for it.

    Args:
        file_path: Path given on the command line, if any

    Returns:
        Path to the form IDs file
    """
    if file_path:
        return file_path

    print('Enter path to form IDs file (one ID per line):')
    file_path = input('> ').strip()

    if not file_path:
        print('Error: No file path entered.')
        sys.exit(1)

    return file_path


def main():
    """
    Log in, read the form IDs, then download every file on those forms.

    Usage:
        python download_form_files.py <form_ids_file>
        python download_form_files.py  # asks for the file path
    """
    parser = argparse.ArgumentParser(
        description='Download every file attached to a list of Avela forms'
    )
    parser.add_argument(
        'form_ids_file',
        nargs='?',
        default=None,
        help='File with one form ID per line (prompts if omitted)',
    )
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    print('=' * 60)
    print('AVELA API INTEGRATION - FORM FILES DOWNLOAD')
    print('=' * 60)

    # Step 1: Find credentials and any extra settings
    config = load_config(profile=args.profile)

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    # An output_dir setting is optional
    output_dir = config.get('output_dir')

    # Step 2: Read the form IDs
    form_ids_file = get_form_ids_file(args.form_ids_file)
    form_ids = load_form_ids(form_ids_file)

    print('\nConfiguration loaded:')
    print(f'  Credentials: {config["credential_source"]}')
    print(f'  Environment: {environment}')
    print(f'  Form IDs file: {form_ids_file}')
    print(f'  Form IDs: {len(form_ids)} form(s)')

    # Step 3: Log in
    access_token = get_access_token(client_id, client_secret, environment)

    # Step 4: Ask about the files, 100 forms at a time, which is the API limit
    form_responses = []
    chunks = chunk_list(form_ids, 100)

    if len(chunks) > 1:
        print(f'\nProcessing {len(form_ids)} forms in {len(chunks)} batches...')

    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            print(f'\n--- Batch {i}/{len(chunks)} ({len(chunk)} forms) ---')
        responses = get_form_files(access_token, environment, chunk)
        form_responses.extend(responses)

    # Step 5: Download the files
    stats, output_path = download_all_files(form_responses, output_dir)

    # Step 6: Print the totals
    print_summary(stats, output_path)

    print('\nDone.')


if __name__ == '__main__':
    """
    Run the recipe.

    Usage:
        python download_form_files.py form_ids.txt
        python download_form_files.py --profile district-a form_ids.txt
        python download_form_files.py  # asks for the file path

    Before you run it:
    1. Store your credentials (the README covers the keychain and environment variables)
    2. Write a form IDs file with one UUID per line
    """
    main()
