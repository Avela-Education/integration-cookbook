#!/usr/bin/env python3
"""
Avela API Integration Script - Download Form Files

This script demonstrates how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Retrieve file upload questions and pre-signed download URLs for forms
3. Download all file attachments to a local directory

Author: Avela Education
License: MIT
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

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


def load_form_ids(file_path: str) -> list[str]:
    """
    Load form IDs from a text file (one ID per line).

    Args:
        file_path: Path to the form IDs file

    Returns:
        List of form ID strings

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        print(f"Error: Form IDs file '{file_path}' not found!")
        sys.exit(1)

    with open(path, encoding='utf-8') as f:
        # Read lines, strip whitespace, skip empty lines and comments
        form_ids = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith('#')
        ]

    if not form_ids:
        print(f"Error: No form IDs found in '{file_path}'")
        sys.exit(1)

    if len(form_ids) > 100:
        print(f'Error: Maximum 100 form IDs allowed per request (found {len(form_ids)})')
        sys.exit(1)

    return form_ids


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
# FORM FILES API
# =============================================================================


def get_form_files(
    access_token: str,
    environment: str,
    form_ids: list[str],
) -> list[dict]:
    """
    Retrieve file upload questions and download URLs for specified forms.

    This function calls the GET /rest/v2/forms/files endpoint which returns
    file upload questions from forms along with pre-signed download URLs
    for each uploaded document.

    Args:
        access_token: Bearer token from authentication
        environment: Target environment (prod, qa, uat, dev)
        form_ids: List of form IDs to get files for (max 100)

    Returns:
        List of form response objects containing file information

    Raises:
        requests.RequestException: If API request fails
    """
    # Build the API URL based on environment
    if environment == 'prod':
        api_base_url = 'https://prod.execute-api.apply.avela.org/api/rest/v2/'
    else:
        api_base_url = f'https://{environment}.execute-api.apply.avela.org/api/rest/v2/'

    files_url = urljoin(api_base_url, 'forms/files')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # form_id parameter is comma-delimited
    params = {'form_id': ','.join(form_ids)}

    print(f'\nFetching file information for {len(form_ids)} form(s)...')

    try:
        response = requests.get(files_url, headers=headers, params=params, timeout=60)

        # This endpoint returns 207 Multi-Status for batch responses
        if response.status_code not in [200, 207]:
            response.raise_for_status()

        data = response.json()

        # The response contains a 'responses' array with per-form results
        responses = data.get('responses', [])

        print(f'Received responses for {len(responses)} form(s)')

        return responses

    except requests.exceptions.RequestException as e:
        print('Error: Failed to fetch form files!')
        print(f'Details: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'Response: {e.response.text}')
        sys.exit(1)


# =============================================================================
# FILE DOWNLOAD
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially problematic characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove or replace characters that might cause issues
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
    Download a file from a pre-signed URL.

    Args:
        url: Pre-signed download URL
        output_path: Local path to save the file

    Returns:
        True if download succeeded, False otherwise
    """
    try:
        # Stream the download to handle large files efficiently
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file in chunks
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
    Download all files from form responses.

    Files are organized by form ID and question key in the output directory.

    Args:
        form_responses: List of form response objects from the API
        output_dir: Base directory for downloads (default: timestamped folder)

    Returns:
        Tuple of (stats dict, output directory path)
    """
    # Create output directory with timestamp
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
        # Check if this form had an error
        # Note: status may be string '200' or int 200 depending on API serialization
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
            # Only process FileUpload type questions
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

                # Extract just the filename from the path if it contains directories
                if '/' in filename:
                    filename = filename.split('/')[-1]

                filename = sanitize_filename(filename)

                # Skip files without download URLs
                if not download_url:
                    print(f'    - {filename}: No download URL (status: {file_status})')
                    stats['skipped'] += 1
                    continue

                # Organize files: output_dir/form_<form_id>/question_key/filename
                file_path = base_path / f'form_{form_id}' / question_key / filename

                # Handle duplicate filenames by appending a number
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
    Print a summary of the download operation.

    Args:
        stats: Dictionary with download statistics
        output_dir: Directory where files were saved
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


def get_form_ids_file() -> str:
    """
    Get the form IDs file path from command line args or prompt.

    Returns:
        Path to the form IDs file
    """
    # Check command line arguments
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Prompt the user
    print('Enter path to form IDs file (one ID per line):')
    file_path = input('> ').strip()

    if not file_path:
        print('Error: No file path provided')
        sys.exit(1)

    return file_path


def main():
    """
    Main execution function.

    This orchestrates the entire workflow:
    1. Load configuration
    2. Load form IDs from file
    3. Authenticate with the API
    4. Fetch form file metadata
    5. Download all files
    6. Display summary

    Usage:
        python download_form_files.py <form_ids_file>
        python download_form_files.py  # prompts for file path
    """
    print('=' * 60)
    print('AVELA API INTEGRATION - FORM FILES DOWNLOAD')
    print('=' * 60)

    # Step 1: Load configuration
    config = load_config('config.json')

    client_id = config['client_id']
    client_secret = config['client_secret']
    environment = config['environment']

    # Optional: custom output directory
    output_dir = config.get('output_dir')

    # Step 2: Get form IDs file and load form IDs
    form_ids_file = get_form_ids_file()
    form_ids = load_form_ids(form_ids_file)

    print('\nConfiguration loaded:')
    print(f'  Environment: {environment}')
    print(f'  Form IDs file: {form_ids_file}')
    print(f'  Form IDs: {len(form_ids)} form(s)')

    # Step 3: Authenticate
    access_token = get_access_token(client_id, client_secret, environment)

    # Step 4: Get form file metadata
    form_responses = get_form_files(access_token, environment, form_ids)

    # Step 5: Download all files
    stats, output_path = download_all_files(form_responses, output_dir)

    # Step 6: Print summary
    print_summary(stats, output_path)

    print('\nIntegration completed successfully!')


if __name__ == '__main__':
    """
    Entry point when script is run directly.

    Usage:
        python download_form_files.py form_ids.txt
        python download_form_files.py  # prompts for file path

    Make sure you have:
    1. Created 'config.json' with your credentials
    2. Created a form IDs file with one UUID per line
    """
    main()
