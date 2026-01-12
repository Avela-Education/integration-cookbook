#!/usr/bin/env python3
"""
Avela API Integration Script - Download Form Files

This script demonstrates how to:
1. Authenticate with the Avela API using OAuth2 client credentials
2. Retrieve file upload questions and pre-signed download URLs for forms
3. Download all file attachments to a local directory

Uses the shared avela_client module for authentication, rate limiting, and retry logic.

Author: Avela Education
License: MIT
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

from avela_client import AvelaClient, create_client_from_config

# =============================================================================
# CONSTANTS
# =============================================================================

BATCH_SIZE = 60


# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logging(log_file: str = None) -> str:
    """
    Configure logging to output to both console and file.

    Args:
        log_file: Optional log file path. If None, creates timestamped file.

    Returns:
        Path to the log file
    """
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'download_{timestamp}.log'

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Console handler (simpler format)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return log_file


# =============================================================================
# UTILITIES
# =============================================================================


def chunk_list(items: list, size: int = 100) -> list[list]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to split
        size: Maximum size of each chunk (default: 100)

    Returns:
        List of lists, each containing up to 'size' items
    """
    return [items[i : i + size] for i in range(0, len(items), size)]


def sanitize_folder_name(name: str) -> str:
    """
    Sanitize a folder name to remove problematic characters.

    Args:
        name: Original folder name

    Returns:
        Sanitized name safe for filesystem use
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Limit length
    if len(name) > 200:
        name = name[:200]

    return name.strip()


def get_folder_name(form_id: str, student_info: dict = None) -> str:
    """
    Generate folder name from form ID and optional student info.

    Args:
        form_id: The form UUID
        student_info: Optional dict with first_name, last_name, ref_id

    Returns:
        Folder name: "Last, First (RefID) - FormID" or "form_<uuid>" if no student info
    """
    if not student_info:
        return f'form_{form_id}'

    first_name = student_info.get('first_name', '')
    last_name = student_info.get('last_name', '')
    ref_id = student_info.get('ref_id', '')

    if not first_name and not last_name:
        return f'form_{form_id}'

    if ref_id:
        folder_name = f'{last_name}, {first_name} ({ref_id}) - {form_id}'
    else:
        folder_name = f'{last_name}, {first_name} - {form_id}'

    return sanitize_folder_name(folder_name)


def count_existing_files(folder_path: Path) -> int:
    """
    Count all files in a folder (recursively).

    Args:
        folder_path: Path to the folder

    Returns:
        Number of files found
    """
    if not folder_path.exists():
        return 0

    count = 0
    for item in folder_path.rglob('*'):
        if item.is_file():
            count += 1
    return count


def detect_input_format(file_path: str) -> str:
    """
    Detect if input file is a CSV with student info or a plain text file.

    Args:
        file_path: Path to the input file

    Returns:
        'csv' if file has CSV headers with 'App ID', otherwise 'text'
    """
    with open(file_path, encoding='utf-8') as f:
        first_line = f.readline().strip()
        # Check if first line looks like a CSV header with 'App ID'
        if ',' in first_line and 'App ID' in first_line:
            return 'csv'
    return 'text'


def load_input_file(file_path: str) -> tuple[list[str], dict | None]:
    """
    Load form IDs from either a text file or CSV file (auto-detected).

    For text files: One form ID per line
    For CSV files: Expects columns including 'App ID', optionally
                   'Student Reference ID', 'First Name', 'Last Name'

    Args:
        file_path: Path to the input file

    Returns:
        Tuple of (form_ids list, student_map dict or None)
        student_map maps form_id -> {first_name, last_name, ref_id}

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)

    if not path.exists():
        logging.error(f"Input file '{file_path}' not found!")
        sys.exit(1)

    input_format = detect_input_format(file_path)

    if input_format == 'csv':
        return _load_csv_file(file_path)
    else:
        return _load_text_file(file_path)


def _load_text_file(file_path: str) -> tuple[list[str], None]:
    """
    Load form IDs from a plain text file (one ID per line).

    Args:
        file_path: Path to the text file

    Returns:
        Tuple of (form_ids list, None)
    """
    with open(file_path, encoding='utf-8') as f:
        # Read lines, strip whitespace, skip empty lines and comments
        form_ids = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith('#')
        ]

    if not form_ids:
        logging.error(f"No form IDs found in '{file_path}'")
        sys.exit(1)

    logging.info(f'Loaded {len(form_ids)} form IDs from text file')
    return form_ids, None


def _load_csv_file(file_path: str) -> tuple[list[str], dict]:
    """
    Load form IDs and student info from a CSV file.

    Expected columns:
    - 'App ID' (required): The form UUID
    - 'Student Reference ID' (optional): Student ref ID
    - 'First Name' (optional): Student first name
    - 'Last Name' (optional): Student last name

    Args:
        file_path: Path to the CSV file

    Returns:
        Tuple of (form_ids list, student_map dict)
    """
    form_ids = []
    student_map = {}

    with open(file_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            form_id = row.get('App ID', '').strip()
            if not form_id:
                continue

            form_ids.append(form_id)

            # Build student info dict
            student_info = {
                'first_name': row.get('First Name', '').strip(),
                'last_name': row.get('Last Name', '').strip(),
                'ref_id': row.get('Student Reference ID', '').strip(),
            }

            student_map[form_id] = student_info

    if not form_ids:
        logging.error(f"No form IDs found in CSV '{file_path}'")
        sys.exit(1)

    logging.info(f'Loaded {len(form_ids)} form IDs from CSV file')
    return form_ids, student_map


# =============================================================================
# FORM FILES API
# =============================================================================


def get_form_files(
    client: AvelaClient,
    form_ids: list[str],
) -> list[dict]:
    """
    Retrieve file upload questions and download URLs for specified forms.

    This function calls the GET /rest/v2/forms/files endpoint which returns
    file upload questions from forms along with pre-signed download URLs
    for each uploaded document. Rate limiting and retry logic are handled
    by the AvelaClient.

    Args:
        client: Authenticated AvelaClient instance
        form_ids: List of form IDs to get files for (max 100)

    Returns:
        List of form response objects containing file information

    Raises:
        requests.RequestException: If API request fails after all retries
    """
    # form_id parameter is comma-delimited
    params = {'form_id': ','.join(form_ids)}

    logging.info(f'Fetching file information for {len(form_ids)} form(s)...')

    response = client.get('/forms/files', params=params)

    # This endpoint returns 207 Multi-Status for batch responses
    if response.status_code not in [200, 207]:
        response.raise_for_status()

    data = response.json()

    # The response contains a 'responses' array with per-form results
    responses = data.get('responses', [])

    logging.info(f'Received responses for {len(responses)} form(s)')

    return responses


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
    student_map: dict | None = None,
    question_key_filter: list[str] | None = None,
) -> tuple[dict, str]:
    """
    Download all files from form responses.

    Files are organized by form folder and question key in the output directory.
    If student_map is provided, uses "Last, First (RefID) - FormID" folder naming.
    If question_key_filter is provided, only downloads files from matching questions.

    Args:
        form_responses: List of form response objects from the API
        output_dir: Base directory for downloads (default: timestamped folder)
        student_map: Optional dict mapping form_id -> {first_name, last_name, ref_id}
        question_key_filter: Optional list of question keys to download (e.g.,
            ['immunization-record', 'physical-record']). If empty/None, downloads all.

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
        'skipped_existing': 0,
    }

    logging.info(f'Downloading files to: {base_path.absolute()}')

    for form_response in form_responses:
        # Check if this form had an error
        # Note: status may be string '200' or int 200 depending on API serialization
        status = form_response.get('status')
        if str(status) != '200':
            logging.warning(f'Form response error (status {status}), skipping')
            continue

        form_data = form_response.get('form', {})
        form_id = form_data.get('id', 'unknown')
        questions = form_data.get('questions', [])

        # Generate folder name based on available student info
        student_info = student_map.get(form_id) if student_map else None
        folder_name = get_folder_name(form_id, student_info)
        form_folder = base_path / folder_name

        # Resume logic: skip if folder already exists with files
        existing_files = count_existing_files(form_folder)
        if existing_files > 0:
            logging.info(f'Skipping {folder_name} ({existing_files} files exist)')
            stats['skipped_existing'] += 1
            stats['total_forms'] += 1
            continue

        stats['total_forms'] += 1

        for question in questions:
            # Only process FileUpload type questions
            if question.get('type') != 'FileUpload':
                continue

            question_id = question.get('id', 'unknown')
            question_key = question.get('key') or question_id

            # Filter by question key if filter is specified
            if question_key_filter and question_key not in question_key_filter:
                continue

            answer = question.get('answer', {})
            files = answer.get('files', [])

            if not files:
                continue

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
                    logging.warning(
                        f'{folder_name}: {filename} - No download URL (status: {file_status})'
                    )
                    stats['skipped'] += 1
                    continue

                # Organize files: output_dir/folder_name/question_key/filename
                file_path = form_folder / question_key / filename

                # Handle duplicate filenames by appending a number
                if file_path.exists():
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while file_path.exists():
                        new_filename = f'{name}_{counter}{ext}'
                        file_path = form_folder / question_key / new_filename
                        counter += 1

                if download_file(download_url, file_path):
                    stats['downloaded'] += 1
                else:
                    logging.error(
                        f'Failed to download: {folder_name}/{question_key}/{filename}'
                    )
                    stats['failed'] += 1

    return stats, output_dir


def print_summary(stats: dict, output_dir: str) -> None:
    """
    Print a summary of the download operation.

    Args:
        stats: Dictionary with download statistics
        output_dir: Directory where files were saved
    """
    logging.info('')
    logging.info('=' * 60)
    logging.info('DOWNLOAD SUMMARY')
    logging.info('=' * 60)
    logging.info(f'Forms processed:    {stats["total_forms"]}')
    logging.info(
        f'Forms skipped:      {stats.get("skipped_existing", 0)} (already downloaded)'
    )
    logging.info(f'Total files:        {stats["total_files"]}')
    logging.info(f'Downloaded:         {stats["downloaded"]}')
    logging.info(f'Failed:             {stats["failed"]}')
    logging.info(f'Skipped (no URL):   {stats["skipped"]}')
    logging.info('')
    logging.info(f'Files saved to: {output_dir}')
    logging.info('=' * 60)


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def get_input_file() -> str:
    """
    Get the input file path from command line args or prompt.

    The input file can be either:
    - A text file with one form ID per line
    - A CSV file with 'App ID' column (and optionally student info)

    Returns:
        Path to the input file
    """
    # Check command line arguments
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Prompt the user
    print('Enter path to input file (text file with form IDs or CSV):')
    file_path = input('> ').strip()

    if not file_path:
        print('Error: No file path provided')
        sys.exit(1)

    return file_path


def main():
    """
    Main execution function.

    This orchestrates the entire workflow:
    1. Set up logging
    2. Load configuration
    3. Load form IDs from file (text or CSV)
    4. Authenticate with the API
    5. Process in batches (fetch metadata + download immediately)
    6. Display summary

    Usage:
        python download_form_files.py <input_file>
        python download_form_files.py  # prompts for file path

    Input file formats:
        - Text file: One form ID per line
        - CSV file: Must have 'App ID' column, optionally
          'First Name', 'Last Name', 'Student Reference ID'
    """
    # Step 1: Set up logging
    log_file = setup_logging()

    logging.info('=' * 60)
    logging.info('AVELA API INTEGRATION - FORM FILES DOWNLOAD')
    logging.info('=' * 60)
    logging.info(f'Log file: {log_file}')

    # Step 2: Create API client (handles auth, rate limiting, retries)
    try:
        client = create_client_from_config('config.json')
    except FileNotFoundError:
        print("Error: Configuration file 'config.json' not found!")
        print("Please create it based on 'config.example.json'")
        sys.exit(1)
    except ValueError as e:
        print(f'Error: {e}')
        sys.exit(1)

    # Load optional settings from config
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)
    output_dir = config.get('output_dir')
    question_key_filter = config.get('question_key_filter', [])

    # Step 3: Get input file and load form IDs
    input_file = get_input_file()
    form_ids, student_map = load_input_file(input_file)

    input_type = 'CSV' if student_map else 'text'
    logging.info(f'Input file: {input_file} ({input_type} format)')
    logging.info(f'Environment: {client.environment}')
    logging.info(f'Form IDs: {len(form_ids)}')
    if question_key_filter:
        logging.info(f'Question filter: {question_key_filter}')

    # Step 4: Authenticate
    client.authenticate()

    # Step 5: Process in batches - fetch and download immediately
    # Using smaller batch size (60) to avoid URL expiration issues
    chunks = chunk_list(form_ids, BATCH_SIZE)
    total_batches = len(chunks)

    # Accumulate stats across all batches
    total_stats = {
        'total_forms': 0,
        'total_files': 0,
        'downloaded': 0,
        'failed': 0,
        'skipped': 0,
        'skipped_existing': 0,
    }

    logging.info(f'Processing {len(form_ids)} forms in {total_batches} batch(es)...')

    for i, chunk in enumerate(chunks, 1):
        logging.info('')
        logging.info(f'--- Batch {i}/{total_batches} ({len(chunk)} forms) ---')

        # Fetch file metadata for this batch
        responses = get_form_files(client, chunk)

        # Download immediately (before pre-signed URLs expire)
        batch_stats, _ = download_all_files(
            responses,
            output_dir=output_dir,
            student_map=student_map,
            question_key_filter=question_key_filter if question_key_filter else None,
        )

        # Accumulate stats
        for key in total_stats:
            total_stats[key] += batch_stats.get(key, 0)

        logging.info(
            f'Batch {i} complete: {batch_stats["downloaded"]} downloaded, '
            f'{batch_stats.get("skipped_existing", 0)} skipped'
        )

    # Step 6: Print final summary
    print_summary(total_stats, output_dir or 'form_files_<timestamp>')

    logging.info('')
    logging.info('Integration completed successfully!')


if __name__ == '__main__':
    """
    Entry point when script is run directly.

    Usage:
        python download_form_files.py form_ids.txt    # Text file with form IDs
        python download_form_files.py students.csv    # CSV with App ID column
        python download_form_files.py                 # Prompts for file path

    Make sure you have:
    1. Created 'config.json' with your credentials
    2. Created an input file:
       - Text file: One form ID (UUID) per line
       - CSV file: Must have 'App ID' column, optionally
         'First Name', 'Last Name', 'Student Reference ID'
    """
    main()
