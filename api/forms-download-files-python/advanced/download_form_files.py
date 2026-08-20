#!/usr/bin/env python3
"""
Download every file attached to a list of Avela forms, with a log and resume.

The script:
1. Logs in with OAuth2 client credentials
2. Asks the API for the file upload questions on each form, and the download
   links that go with them
3. Saves every file under a folder named for the student, when the input file
   carries names

It writes a log file, and it skips any form folder that already holds files, when output_dir is set in config.json (the default folder is timestamped per run, so a rerun starts fresh), so
you can stop it and start it again. Logging in, staying under the rate limit,
and retrying come from the shared avela_client module.

Author: Avela Education
License: MIT
"""

import argparse
import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

try:
    from avela_client import AvelaClient, create_client, load_settings
except ImportError as exc:
    print('Error: the shared Avela client could not be imported.')
    print(f'Details: {exc}')
    print("Install this recipe's dependencies and try again:")
    print('    pip install -r requirements.txt')
    sys.exit(1)


# =============================================================================
# CONSTANTS
# =============================================================================

BATCH_SIZE = 60


# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logging(log_file: str = None) -> str:
    """
    Send log messages to the screen and to a file.

    Args:
        log_file: Where to write the log (default: a timestamped file)

    Returns:
        Path to the log file
    """
    if log_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'download_{timestamp}.log'

    # The file gets a timestamp on every line
    formatter = logging.Formatter(
        '%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # The screen gets the message on its own
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(message)s'))

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
    Split a list into smaller lists.

    Args:
        items: List to split
        size: Largest size of each piece (default: 100)

    Returns:
        List of lists, each holding up to 'size' items
    """
    return [items[i : i + size] for i in range(0, len(items), size)]


def sanitize_folder_name(name: str) -> str:
    """
    Replace the characters an operating system will not accept in a folder name.

    Args:
        name: Original folder name

    Returns:
        A name you can safely create on disk
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Keep the name short enough for every filesystem
    if len(name) > 200:
        name = name[:200]

    return name.strip()


def get_folder_name(form_id: str, student_info: dict = None) -> str:
    """
    Build the folder name for one form.

    Args:
        form_id: The form UUID
        student_info: Dict with first_name, last_name, and ref_id, if you have it

    Returns:
        Folder name: "Last, First (RefID) - FormID", or "form_<uuid>" with no
        student information
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
    Count the files in a folder, including the ones in subfolders.

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
    Work out whether the input file is a CSV or a plain list of form IDs.

    Args:
        file_path: Path to the input file

    Returns:
        'csv' if the first line is a CSV header holding 'App ID', else 'text'
    """
    with open(file_path, encoding='utf-8') as f:
        first_line = f.readline().strip()
        if ',' in first_line and 'App ID' in first_line:
            return 'csv'
    return 'text'


def load_input_file(file_path: str) -> tuple[list[str], dict | None]:
    """
    Read form IDs from a text file or a CSV file, whichever you point it at.

    A text file holds one form ID per line. A CSV file needs an 'App ID'
    column, and may also carry 'Student Reference ID', 'First Name', and
    'Last Name'. Those names go into the folder names.

    Args:
        file_path: Path to the input file

    Returns:
        Tuple of (form_ids list, student_map dict or None). student_map maps
        form_id to {first_name, last_name, ref_id}.

    Raises:
        FileNotFoundError: If the file is missing
    """
    path = Path(file_path)

    if not path.exists():
        logging.error(f"Input file '{file_path}' not found.")
        sys.exit(1)

    input_format = detect_input_format(file_path)

    if input_format == 'csv':
        return _load_csv_file(file_path)
    else:
        return _load_text_file(file_path)


def _load_text_file(file_path: str) -> tuple[list[str], None]:
    """
    Read form IDs from a text file, one per line.

    Blank lines and lines starting with # are skipped.

    Args:
        file_path: Path to the text file

    Returns:
        Tuple of (form_ids list, None)
    """
    with open(file_path, encoding='utf-8') as f:
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
    Read form IDs and student names from a CSV file.

    Columns:
    - 'App ID' (required): The form UUID
    - 'Student Reference ID' (optional)
    - 'First Name' (optional)
    - 'Last Name' (optional)

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
    Ask the API which files are attached to a batch of forms.

    Calls GET /rest/v2/forms/files. For each form it returns the file upload
    questions and a download link for every uploaded document. Those links are
    pre-signed, so they work without the access token and they expire. The
    AvelaClient keeps the calls under the rate limit and retries them.

    Args:
        client: Logged in AvelaClient
        form_ids: The forms to ask about (up to 100 at a time)

    Returns:
        List of per-form response objects holding the file information

    Raises:
        requests.RequestException: If the request still fails after the retries
    """
    # The form_id parameter takes a comma separated list
    params = {'form_id': ','.join(form_ids)}

    logging.info(f'Fetching file information for {len(form_ids)} form(s)...')

    response = client.get('/forms/files', params=params)

    # A batch answer comes back as 207 Multi-Status, which is not an error
    if response.status_code not in [200, 207]:
        response.raise_for_status()

    data = response.json()

    # One entry per form, in a 'responses' array
    responses = data.get('responses', [])

    logging.info(f'Received responses for {len(responses)} form(s)')

    return responses


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
    student_map: dict | None = None,
    question_key_filter: list[str] | None = None,
) -> tuple[dict, str]:
    """
    Download every file named in the API responses.

    Each file lands in output_dir/<form folder>/<question_key>/<filename>. Pass
    student_map to name the form folders "Last, First (RefID) - FormID". Pass
    question_key_filter to download only certain questions.

    Args:
        form_responses: Per-form response objects from the API
        output_dir: Folder to download into (default: a timestamped folder)
        student_map: Dict mapping form_id to {first_name, last_name, ref_id}
        question_key_filter: Question keys to download, for example
            ['immunization-record', 'physical-record']. Empty or None gets all.

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
        'skipped_existing': 0,
    }

    logging.info(f'Downloading files to: {base_path.absolute()}')

    for form_response in form_responses:
        # Skip forms the API could not return. The status arrives as either the
        # string '200' or the number 200, so compare it as text.
        status = form_response.get('status')
        if str(status) != '200':
            logging.warning(f'Form response error (status {status}), skipping')
            continue

        form_data = form_response.get('form', {})
        form_id = form_data.get('id', 'unknown')
        questions = form_data.get('questions', [])

        student_info = student_map.get(form_id) if student_map else None
        folder_name = get_folder_name(form_id, student_info)
        form_folder = base_path / folder_name

        # A folder with files in it was downloaded on an earlier run, so skip it
        existing_files = count_existing_files(form_folder)
        if existing_files > 0:
            logging.info(f'Skipping {folder_name} ({existing_files} files exist)')
            stats['skipped_existing'] += 1
            stats['total_forms'] += 1
            continue

        stats['total_forms'] += 1

        for question in questions:
            # Only FileUpload questions can hold files
            if question.get('type') != 'FileUpload':
                continue

            question_id = question.get('id', 'unknown')
            question_key = question.get('key') or question_id

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

                # Some filenames arrive with folders in front, so keep the end
                if '/' in filename:
                    filename = filename.split('/')[-1]

                filename = sanitize_filename(filename)

                # No link means the file is not ready to download
                if not download_url:
                    logging.warning(
                        f'{folder_name}: {filename} - No download URL (status: {file_status})'
                    )
                    stats['skipped'] += 1
                    continue

                file_path = form_folder / question_key / filename

                # Two files with the same name: add _1, _2, and so on
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
    Print the download totals.

    Args:
        stats: Dictionary of download counts
        output_dir: Folder the files were saved in
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


def get_input_file(file_path: str | None = None) -> str:
    """
    Take the input file from the command line, or ask for it.

    The input file is either a text file with one form ID per line, or a CSV
    file with an 'App ID' column and, if you have them, student names.

    Args:
        file_path: Path given on the command line, if any

    Returns:
        Path to the input file
    """
    if file_path:
        return file_path

    print('Enter path to input file (text file with form IDs or CSV):')
    file_path = input('> ').strip()

    if not file_path:
        print('Error: No file path entered.')
        sys.exit(1)

    return file_path


def main():
    """
    Log in, read the form IDs, then download every file on those forms.

    Files are fetched and saved one batch at a time, so no download link sits
    unused long enough to expire.

    Usage:
        python download_form_files.py <input_file>
        python download_form_files.py  # asks for the file path

    Input file formats:
        - Text file: One form ID per line
        - CSV file: Must have 'App ID' column, optionally
          'First Name', 'Last Name', 'Student Reference ID'
    """
    parser = argparse.ArgumentParser(
        description='Download every file attached to a list of Avela forms'
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default=None,
        help='Text file with one form ID per line, or CSV with an App ID column',
    )
    parser.add_argument(
        '--profile', default=None, help='Named credential set to use (see README)'
    )
    args = parser.parse_args()

    # Step 1: Start the log
    log_file = setup_logging()

    logging.info('=' * 60)
    logging.info('AVELA API INTEGRATION - FORM FILES DOWNLOAD')
    logging.info('=' * 60)
    logging.info(f'Log file: {log_file}')

    # Step 2: Build the API client. It logs in, stays under the rate limit,
    # and retries a failed request.
    try:
        client = create_client(profile=args.profile)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # These settings are optional
    # The settings and the credentials always come from the same client
    try:
        config = load_settings(args.profile)
    except ValueError as e:
        print(e)
        sys.exit(1)
    # Settle the folder once, here. download_all_files runs per batch and would
    # otherwise invent a new timestamped folder for each one, scattering a large
    # download across several directories and breaking the resume check.
    output_dir = config.get('output_dir') or f'form_files_{datetime.now():%Y%m%d_%H%M%S}'
    question_key_filter = config.get('question_key_filter', [])

    # Step 3: Read the form IDs
    input_file = get_input_file(args.input_file)
    form_ids, student_map = load_input_file(input_file)

    input_type = 'CSV' if student_map else 'text'
    logging.info(f'Input file: {input_file} ({input_type} format)')
    logging.info(f'Credentials: {client.credential_source}')
    logging.info(f'Environment: {client.environment}')
    logging.info(f'Form IDs: {len(form_ids)}')
    if question_key_filter:
        logging.info(f'Question filter: {question_key_filter}')

    # Step 4: Log in
    client.authenticate()

    # Step 5: Work in batches of 60, downloading each batch before asking for
    # the next one, so no download link expires before it is used
    chunks = chunk_list(form_ids, BATCH_SIZE)
    total_batches = len(chunks)

    # Running totals across every batch
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

        responses = get_form_files(client, chunk)

        batch_stats, _ = download_all_files(
            responses,
            output_dir=output_dir,
            student_map=student_map,
            question_key_filter=question_key_filter if question_key_filter else None,
        )

        for key in total_stats:
            total_stats[key] += batch_stats.get(key, 0)

        logging.info(
            f'Batch {i} complete: {batch_stats["downloaded"]} downloaded, '
            f'{batch_stats.get("skipped_existing", 0)} skipped'
        )

    # Step 6: Print the totals
    print_summary(total_stats, output_dir or 'form_files_<timestamp>')

    logging.info('')
    logging.info('Done.')


if __name__ == '__main__':
    """
    Run the recipe.

    Usage:
        python download_form_files.py form_ids.txt    # Text file with form IDs
        python download_form_files.py students.csv    # CSV with App ID column
        python download_form_files.py --profile district-a students.csv
        python download_form_files.py                 # Asks for the file path

    Before you run it:
    1. Store your credentials (the README covers the keychain and environment variables)
    2. Write an input file:
       - Text file: One form ID (UUID) per line
       - CSV file: Must have 'App ID' column, optionally
         'First Name', 'Last Name', 'Student Reference ID'
    """
    main()
