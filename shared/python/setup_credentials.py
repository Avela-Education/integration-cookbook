#!/usr/bin/env python3
"""
Store Avela API credentials in the OS keychain.

Run this once on each computer. Your operating system encrypts the credentials,
every recipe finds them on its own, and nothing goes into a file.

Where they are stored:
    macOS    login Keychain (open Keychain Access to see it)
    Windows  Credential Manager (Control Panel > Credential Manager)
    Linux    Secret Service (GNOME Keyring or KWallet)

Usage:
    python setup_credentials.py                      # store default credentials
    python setup_credentials.py --profile district-a    # store a named client
    python setup_credentials.py --list               # list stored profiles
    python setup_credentials.py --show               # check what is stored
    python setup_credentials.py --delete             # remove stored credentials

Recipes then pick a client with --profile district-a or AVELA_PROFILE=district-a.

Author: Avela Education
License: MIT
"""

import argparse
import sys
from getpass import getpass

from avela_client import (
    DEFAULT_ENVIRONMENT,
    ENV_PROFILE,
    VALID_ENVIRONMENTS,
    forget_profile,
    keyring_service_name,
    normalize_profile,
    remember_profile,
    stored_profiles,
)

NO_KEYCHAIN_HINT = """
This machine has no keychain to unlock. That is normal on a server, in a
container, over SSH, or in CI. Use environment variables there instead:

    export AVELA_CLIENT_ID=...
    export AVELA_CLIENT_SECRET=...
    export AVELA_ENVIRONMENT=prod
"""

INSTALL_HINT = """
The 'keyring' package is missing, so the recipe requirements were never
installed. From the recipe directory, with your virtual environment active:

    pip install -r requirements.txt

Then run this script again.
"""


def _require_keyring():
    """Import keyring, or quit and say how to install the requirements."""
    try:
        import keyring
    except ImportError:
        print(INSTALL_HINT)
        sys.exit(1)
    return keyring


def _unsafe_backend(backend) -> str | None:
    """Return the module name of an unencrypted backend, looking inside chains."""
    # keyring can wrap several stores, so check each one. keyrings.alt stores
    # secrets in plain text.
    members = getattr(backend, 'backends', None)
    if members:
        for member in members:
            found = _unsafe_backend(member)
            if found:
                return found
        return None

    module = backend.__class__.__module__
    if 'keyrings.alt' in module or 'fail' in module.lower():
        return module
    return None


def _warn_if_backend_is_not_encrypted(keyring) -> None:
    """
    Stop when the chosen backend does not encrypt what it stores.

    Some keyring setups store secrets in a plain file instead of the encrypted
    keychain. Stop rather than write the secret to disk unencrypted.
    """
    backend = _unsafe_backend(keyring.get_keyring())
    if backend:
        print(f'Refusing to store: keyring chose the {backend} backend, which')
        print('does not encrypt what it stores. Your secret would go to a plain')
        print('file instead of the encrypted keychain.')
        print(NO_KEYCHAIN_HINT)
        sys.exit(1)


def _delete_not_found_error():
    """The exception keyring raises when there was nothing to delete."""
    from keyring.errors import PasswordDeleteError

    return PasswordDeleteError


def _label(profile: str | None) -> str:
    """Name this set of credentials, for messages on screen."""
    return f"profile '{profile}'" if profile else 'default credentials'


def store_credentials(profile: str | None) -> None:
    """Ask for credentials and save them in the OS keychain."""
    keyring = _require_keyring()
    service_name = keyring_service_name(profile)

    _warn_if_backend_is_not_encrypted(keyring)

    print(f'Storing {_label(profile)} in the OS keychain ({service_name}).')
    print('Your Avela account team has these. Email help@avela.org.\n')

    if not sys.stdin.isatty():
        print('This needs an interactive terminal to ask for your credentials.')
        print(NO_KEYCHAIN_HINT)
        sys.exit(1)

    client_id = input('Client ID: ').strip()
    # getpass hides the secret, so it stays out of your screen and shell history
    client_secret = getpass('Client secret (hidden): ').strip()
    environment = (
        input(f'Environment {VALID_ENVIRONMENTS} [{DEFAULT_ENVIRONMENT}]: ').strip()
        or DEFAULT_ENVIRONMENT
    )

    if not client_id or not client_secret:
        print('\nBoth values are required. Nothing was stored.')
        sys.exit(1)

    # Checked here so a typo fails now, not on every later run
    if environment not in VALID_ENVIRONMENTS:
        print(f"\n'{environment}' is not a known environment. Nothing was stored.")
        print(f'Valid environments: {", ".join(VALID_ENVIRONMENTS)}')
        sys.exit(1)

    written = []
    try:
        for key, value in (
            ('client_id', client_id),
            ('client_secret', client_secret),
            ('environment', environment),
        ):
            keyring.set_password(service_name, key, value)
            written.append(key)
    except Exception as exc:
        # Remove a half-written entry, or later runs see nothing stored
        survivors = []
        for key in written:
            try:
                keyring.delete_password(service_name, key)
            except Exception:
                survivors.append(key)
        print(f'\nCould not write to the keychain: {exc}')
        if survivors:
            print(
                'COULD NOT REMOVE '
                + ', '.join(survivors)
                + f'. Check {service_name} in your keychain before you treat '
                'this credential as absent.'
            )
        else:
            print('Nothing was left behind.')
        print(NO_KEYCHAIN_HINT)
        sys.exit(1)

    remember_profile(profile)

    print('\nStored. Recipes will find these credentials on their own now.')
    if profile:
        print(f'Pick them with --profile {profile} or {ENV_PROFILE}={profile}.')
    print('You can delete any config.json file holding the same secret.')


def show_credentials(profile: str | None) -> None:
    """Say whether credentials are stored, without printing the secret."""
    keyring = _require_keyring()
    service_name = keyring_service_name(profile)

    try:
        client_id = keyring.get_password(service_name, 'client_id')
        client_secret = keyring.get_password(service_name, 'client_secret')
        environment = keyring.get_password(service_name, 'environment')
    except Exception as exc:
        print(f'Could not read the keychain: {exc}')
        print(NO_KEYCHAIN_HINT)
        sys.exit(1)

    print(f'Keychain service: {service_name} ({_label(profile)})')
    print(f'  Stored in:     {keyring.get_keyring().__class__.__name__}')
    print(f'  Client ID:     {client_id or "(not set)"}')
    print(f'  Client secret: {"(set)" if client_secret else "(not set)"}')
    print(f'  Environment:   {environment or "(not set)"}')


def show_profiles() -> None:
    """List every profile stored on this computer."""
    _require_keyring()
    profiles = stored_profiles()

    print('Stored profiles:')
    print('  (default)')
    for name in profiles:
        print(f'  {name}')
    if not profiles:
        print('\nNo named profiles yet. Add one with --profile NAME.')


def delete_credentials(profile: str | None) -> None:
    """Delete stored credentials from the OS keychain."""
    keyring = _require_keyring()
    service_name = keyring_service_name(profile)

    failed = []
    for key in ('client_id', 'client_secret', 'environment'):
        try:
            keyring.delete_password(service_name, key)
            print(f'Deleted {key}.')
        except _delete_not_found_error():
            # Nothing was stored under that key, which is the result we wanted
            print(f'No stored {key}.')
        except Exception as exc:
            # Anything else means the secret may still be there. Say so, because
            # someone deleting a leaked credential needs to know it survived.
            print(f'COULD NOT DELETE {key}: {exc}')
            failed.append(key)

    if failed:
        print(
            '\nWarning: '
            + ', '.join(failed)
            + ' may still be in the keychain. Check with Keychain Access, or '
            'run --show, before you treat this credential as removed.'
        )
        sys.exit(1)

    forget_profile(profile)


def main() -> None:
    """Parse the command line and run the requested action."""
    parser = argparse.ArgumentParser(
        description='Store Avela API credentials in the OS keychain.'
    )
    parser.add_argument(
        '--profile',
        default=None,
        help='Name for this set of credentials, when you have several clients',
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--show', action='store_true', help='Show what is stored, minus the secret'
    )
    group.add_argument('--list', action='store_true', help='List stored profiles')
    group.add_argument('--delete', action='store_true', help='Delete stored credentials')
    args = parser.parse_args()

    if args.list:
        show_profiles()
        return

    try:
        profile = normalize_profile(args.profile)
    except ValueError as e:
        print(e)
        sys.exit(1)

    if args.show:
        show_credentials(profile)
    elif args.delete:
        delete_credentials(profile)
    else:
        store_credentials(profile)


if __name__ == '__main__':
    main()
