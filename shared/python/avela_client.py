#!/usr/bin/env python3
"""
Avela API client with rate limiting.

The client logs in with OAuth2, spaces out requests so you stay under the API
limit of 100 requests per 5 minutes, and retries failed requests. When the API
answers 429 (too many requests), it waits as long as the response asks for.

Usage:
    from avela_client import AvelaClient

    # Credentials are found for you (see resolve_credentials below)
    client = AvelaClient()

    # ...or passed in
    client = AvelaClient(
        client_id='your_client_id',
        client_secret='your_client_secret',
        environment='prod'  # or 'qa', 'uat', 'dev'
    )

    # Rate limiting is handled for you
    response = client.get('/forms', params={'limit': 100})
    data = response.json()

Author: Avela Education
License: MIT
"""

import os
import re
import sys
import time
from pathlib import Path
from typing import Any, NamedTuple

import backoff
import requests

# =============================================================================
# RATE LIMIT CONSTANTS
# =============================================================================

# Avela API rate limit: 100 requests per 5 minutes (300 seconds)
# Enforced at AWS WAF level per IP address
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 300  # seconds

# Safe interval between requests (with 10% buffer)
# 300 seconds / 100 requests = 3 seconds, plus buffer = 3.3 seconds
MIN_REQUEST_INTERVAL = (RATE_LIMIT_PERIOD / RATE_LIMIT_REQUESTS) * 1.1

# Retry configuration
MAX_RETRIES = 5
MAX_RETRY_TIME = 300  # 5 minutes max total retry time


# =============================================================================
# BACKOFF HANDLERS
# =============================================================================


def _on_backoff(details: dict) -> None:
    """Log when a retry is about to happen."""
    wait = details['wait']
    tries = details['tries']
    print(f'  Retry {tries}: waiting {wait:.1f}s before next attempt...')


def _on_giveup(details: dict) -> None:
    """Log when all retries are exhausted."""
    tries = details['tries']
    print(f'  Failed after {tries} attempts')


def _is_rate_limited(response: requests.Response) -> bool:
    """Check if response indicates rate limiting."""
    return response.status_code == 429


def _is_server_error(exception: Exception) -> bool:
    """Check if we should retry this exception."""
    if isinstance(exception, requests.exceptions.RequestException):
        if hasattr(exception, 'response') and exception.response is not None:
            # Don't retry client errors (4xx) except 429
            status = exception.response.status_code
            if 400 <= status < 500 and status != 429:
                return False
        return True
    return False


# =============================================================================
# CREDENTIAL RESOLUTION
# =============================================================================

# Environment variables checked for credentials
ENV_CLIENT_ID = 'AVELA_CLIENT_ID'
ENV_CLIENT_SECRET = 'AVELA_CLIENT_SECRET'
ENV_ENVIRONMENT = 'AVELA_ENVIRONMENT'

# Picks which set of credentials to use when you work with several clients
ENV_PROFILE = 'AVELA_PROFILE'

# The OS keychain service name credentials are stored under
KEYRING_SERVICE = 'avela-api'

# Keychain key holding the list of profile names, so they can be listed later
KEYRING_PROFILE_INDEX = 'profiles'

VALID_ENVIRONMENTS = ('prod', 'staging', 'uat', 'qa', 'dev', 'dev2')

# Deliberately not prod. An unset environment should land somewhere safe.
DEFAULT_ENVIRONMENT = 'uat'


class Credentials(NamedTuple):
    """API credentials, plus a note on where they came from."""

    client_id: str
    client_secret: str
    environment: str
    source: str
    profile: str | None = None


def normalize_profile(profile: str | None) -> str | None:
    """
    Clean up a profile name, or return None for the default profile.

    Profile names end up in environment variable names and keychain entries,
    so they are cut down to lowercase letters, digits, and dashes.

    Raises:
        ValueError: If nothing usable is left after cleaning
    """
    if not profile:
        return None
    cleaned = re.sub(r'[^A-Za-z0-9]+', '-', profile).strip('-').lower()
    if not cleaned:
        raise ValueError(
            f"'{profile}' is not a usable profile name. Use letters or digits."
        )
    return cleaned


def _env_var(name: str, profile: str | None) -> str:
    """
    Build the environment variable name for a profile.

    With the profile 'district-a', AVELA_CLIENT_ID becomes
    AVELA_DISTRICT_A_CLIENT_ID, so two clients' credentials can sit in one
    shell without clashing.
    """
    if not profile:
        return name
    suffix = profile.replace('-', '_').upper()
    return name.replace('AVELA_', f'AVELA_{suffix}_', 1)


def keyring_service_name(profile: str | None) -> str:
    """
    Build the keychain service name for a profile.

    Each named profile gets its own entry ('avela-api:district-a'), so profiles
    show up separately in Keychain Access and Credential Manager and you can
    delete one without touching the others.
    """
    profile = normalize_profile(profile)
    return f'{KEYRING_SERVICE}:{profile}' if profile else KEYRING_SERVICE


def config_file_name(profile: str | None) -> str:
    """Build the settings file name for a profile."""
    profile = normalize_profile(profile)
    return f'config.{profile}.json' if profile else 'config.json'


def setup_script_path() -> str:
    """Path to setup_credentials.py, written relative to the current directory."""
    import os.path

    script = Path(__file__).resolve().parent / 'setup_credentials.py'
    repo_root = script.parent.parent.parent

    # A relative path only reads well from inside the repo. From anywhere
    # else, print the absolute path.
    try:
        Path.cwd().relative_to(repo_root)
    except ValueError:
        return str(script)

    try:
        return os.path.relpath(script, Path.cwd())
    except ValueError:
        return str(script)


def credential_help() -> str:
    """The message shown when no source held both an id and a secret."""
    return f"""
No Avela API credentials found. Pick one of these:

  1. OS keychain. Works out of the box on a laptop:
         python {setup_script_path()}
     It asks for the environment too, so you do not silently get prod.

  2. Environment variables. Best on servers, CI, and containers:
         export {ENV_CLIENT_ID}=...
         export {ENV_CLIENT_SECRET}=...
         export {ENV_ENVIRONMENT}=prod

Several clients? Give each one a profile name, then pick one with
--profile NAME or {ENV_PROFILE}=NAME. See shared/python/README.md.

Your Avela account team has your credentials. Email help@avela.org.
"""


def environment_urls(environment: str) -> tuple[str, str, str]:
    """
    Return (auth_url, base_url, audience) for an environment.

    Staging uses a different login host from the other environments.

    Raises:
        ValueError: If the environment is not one we know
    """
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"'{environment}' is not a known environment. "
            f'Valid environments: {", ".join(VALID_ENVIRONMENTS)}'
        )

    if environment == 'prod':
        return (
            'https://auth.avela.org/oauth/token',
            'https://prod.execute-api.apply.avela.org/api/rest/v2',
            'https://api.apply.avela.org/v1/graphql',
        )
    if environment == 'staging':
        return (
            'https://avela-staging.us.auth0.com/oauth/token',
            'https://staging.execute-api.apply.avela.org/api/rest/v2',
            'https://staging.api.apply.avela.org/v1/graphql',
        )
    return (
        f'https://{environment}.auth.avela.org/oauth/token',
        f'https://{environment}.execute-api.apply.avela.org/api/rest/v2',
        f'https://{environment}.api.apply.avela.org/v1/graphql',
    )


def _read_config_file(config_path: str) -> dict:
    """Read a settings file, returning an empty dict if it is not there."""
    import json

    path = Path(config_path)
    if not path.exists():
        return {}

    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f'{config_path} is not valid JSON: {exc}') from exc
    except OSError as exc:
        raise ValueError(f'Could not read {config_path}: {exc}') from exc

    if not isinstance(data, dict):
        raise ValueError(
            f'{config_path} must hold a JSON object, not a {type(data).__name__}.'
        )
    return data


def unsafe_keyring_backend(backend) -> str | None:
    """
    Return the module name of an unencrypted keyring backend, or None.

    keyring can wrap several stores, so chains are checked all the way down.
    Anything from keyrings.alt stores secrets in plain text.
    """
    members = getattr(backend, 'backends', None)
    if members:
        for member in members:
            found = unsafe_keyring_backend(member)
            if found:
                return found
        return None

    module = backend.__class__.__module__
    if 'keyrings.alt' in module or 'fail' in module.lower():
        return module
    return None


def _credentials_from_keyring(
    service_name: str = KEYRING_SERVICE,
) -> tuple[str | None, str | None, str | None]:
    """
    Read credentials from the OS keychain.

    Backends are chosen by the keyring library: macOS Keychain, Windows
    Credential Manager, or Secret Service on Linux. A locked or missing
    backend is treated as "not found" rather than an error.

    Returns:
        (client_id, client_secret, environment), any of which may be None
    """
    try:
        import keyring
    except ImportError:
        return None, None, None

    unsafe = unsafe_keyring_backend(keyring.get_keyring())
    if unsafe:
        print(
            f'  Warning: keyring includes the {unsafe} backend, which '
            'stores secrets unencrypted.',
            file=sys.stderr,
        )

    try:
        return (
            keyring.get_password(service_name, 'client_id'),
            keyring.get_password(service_name, 'client_secret'),
            keyring.get_password(service_name, 'environment'),
        )
    except Exception as exc:
        print(f'  Note: keychain unavailable ({exc}); trying other sources...')
        return None, None, None


class _ProfileIndexUnavailable(Exception):
    """The keychain could not be read, which is not the same as it being empty."""


def list_profiles() -> list[str]:
    """
    List profile names stored in the OS keychain.

    Keychain backends cannot be listed directly, so profile names are recorded
    in a small index entry as they are stored.
    """
    try:
        import keyring
    except ImportError:
        return []

    try:
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_PROFILE_INDEX)
    except Exception as exc:
        # A locked keychain is not the same as an empty one. Say so.
        print(f'  Note: keychain unavailable ({exc}), so profiles cannot be listed.')
        raise _ProfileIndexUnavailable from exc

    return [name for name in (raw or '').split(',') if name]


def stored_profiles() -> list[str]:
    """Profile names for display. Empty if the keychain is unreadable."""
    try:
        return list_profiles()
    except _ProfileIndexUnavailable:
        return []


def remember_profile(profile: str | None) -> None:
    """Add a profile name to the keychain index that list_profiles() reads."""
    profile = normalize_profile(profile)
    if not profile:
        return

    try:
        import keyring
    except ImportError:
        return

    try:
        known = list_profiles()
    except _ProfileIndexUnavailable:
        # Writing now would replace the whole index with just this one name
        return

    if profile in known:
        return

    try:
        keyring.set_password(
            KEYRING_SERVICE, KEYRING_PROFILE_INDEX, ','.join([*known, profile])
        )
    except Exception:
        # The index is a convenience, so failing to update it must not stop setup
        pass


def forget_profile(profile: str | None) -> None:
    """Remove a profile name from the keychain index."""
    profile = normalize_profile(profile)
    if not profile:
        return

    try:
        import keyring
    except ImportError:
        return

    try:
        remaining = [name for name in list_profiles() if name != profile]
    except _ProfileIndexUnavailable:
        return

    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_PROFILE_INDEX, ','.join(remaining))
    except Exception:
        pass


def load_settings(profile: str | None = None) -> dict:
    """
    Read a recipe's non-secret settings from its config files.

    config.json is read first, then config.{profile}.json layered over it, so a
    profile file can set just what differs and inherit the rest.

    Credentials never come from these files. If one still holds them, they are
    ignored, and a note says so.

    Args:
        profile: Named credential set, so the right profile file is read

    Returns:
        Settings dict, empty when there is no config file
    """
    profile = normalize_profile(profile or os.environ.get(ENV_PROFILE))

    settings: dict = {}
    seen = set()
    for candidate in ('config.json', config_file_name(profile)):
        if candidate in seen:
            continue
        seen.add(candidate)
        loaded = _read_config_file(candidate)
        ignored = [
            k for k in ('client_id', 'client_secret', 'environment') if k in loaded
        ]
        if ignored:
            print(
                f'  Note: {", ".join(ignored)} in {candidate} is no longer '
                'used. Store credentials and the environment with '
                'setup_credentials.py, then remove them from the file.',
                file=sys.stderr,
            )
        settings.update(loaded)

    for key in ('client_id', 'client_secret', 'environment'):
        settings.pop(key, None)
    return settings


def _missing_credentials_error(profile: str | None) -> ValueError:
    """Build the error raised when no source held both an id and a secret."""
    if not profile:
        return ValueError(credential_help())
    return ValueError(
        f"No credentials stored for profile '{profile}'.\n\n"
        f'Nothing was found in {_env_var(ENV_CLIENT_ID, profile)} or the '
        f'keychain entry {keyring_service_name(profile)}.\n\n'
        f'  See what is stored:  python {setup_script_path()} --list\n'
        f'  Store this profile:  python {setup_script_path()} '
        f'--profile {profile}\n\n'
        'The default credentials are deliberately not used here, so a mistyped '
        'profile cannot run against the wrong client.'
    )


def _resolve_environment(
    explicit: str | None,
    profile: str | None,
    from_source: str | None,
) -> str:
    """
    Work out which environment to talk to.

    Order: the caller's argument, then an exported AVELA_ENVIRONMENT, then the
    environment stored with the credential. When nothing names one,
    DEFAULT_ENVIRONMENT is used and a note is printed. The default is uat, not
    prod, so forgetting costs an empty result rather than a write to a real
    district.

    Raises:
        ValueError: If the environment named is not one we know
    """
    # A named profile only reads its own variable. The unprefixed one belongs
    # to the default credentials.
    exported = os.environ.get(_env_var(ENV_ENVIRONMENT, profile))
    if not profile:
        exported = exported or os.environ.get(ENV_ENVIRONMENT)

    environment = explicit or exported or from_source

    if not environment:
        print(
            f'  Note: no environment set, using {DEFAULT_ENVIRONMENT}. '
            f'Set {_env_var(ENV_ENVIRONMENT, profile)} to choose.',
            file=sys.stderr,
        )
        environment = DEFAULT_ENVIRONMENT

    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"'{environment}' is not a known environment. "
            f'Valid environments: {", ".join(VALID_ENVIRONMENTS)}'
        )

    return environment


def resolve_credentials(
    client_id: str | None = None,
    client_secret: str | None = None,
    environment: str | None = None,
    profile: str | None = None,
) -> Credentials:
    """
    Find API credentials, checking three sources in order.

    The order is:
        1. Arguments passed to this function
        2. Environment variables
        3. The OS keychain, through the `keyring` package

    Environment variables come before the keychain, so a server, container,
    or CI job can override whatever a developer stored on a laptop.

    A profile with nothing stored is an error. It never quietly uses the
    default credentials. An unset environment uses uat, announced on screen,
    never prod.

    Profiles keep several clients apart. Pass profile='district-a' (or set
    AVELA_PROFILE=district-a) and every source uses that name:
    AVELA_DISTRICT_A_CLIENT_ID and keychain service 'avela-api:district-a'.

    Args:
        client_id: OAuth2 client ID, if you already have it
        client_secret: OAuth2 client secret, if you already have it
        environment: Which environment to use ('prod', 'uat', 'qa', 'dev')
        profile: Named credential set to use; defaults to $AVELA_PROFILE

    Returns:
        Credentials with the values and the name of the source they came from

    Raises:
        ValueError: If no source had both an ID and a secret, or half of a
            pair was given, or the environment named is not a real one
    """
    if (client_id is not None or client_secret is not None) and not (
        client_id and client_secret
    ):
        raise ValueError(
            'client_id and client_secret were passed, but at least one is '
            'missing or empty. Pass both with values, or neither to look them '
            'up. Falling back would run as a different client than the one '
            'you named.'
        )

    # A profile passed in code wins over the one exported in the shell
    profile = normalize_profile(profile or os.environ.get(ENV_PROFILE))

    if client_id and client_secret:
        return Credentials(
            client_id,
            client_secret,
            _resolve_environment(environment, profile, None),
            'arguments',
            profile,
        )

    env_id = os.environ.get(_env_var(ENV_CLIENT_ID, profile))
    env_secret = os.environ.get(_env_var(ENV_CLIENT_SECRET, profile))
    if bool(env_id) != bool(env_secret):
        set_name = ENV_CLIENT_ID if env_id else ENV_CLIENT_SECRET
        unset_name = ENV_CLIENT_SECRET if env_id else ENV_CLIENT_ID
        raise ValueError(
            f'{_env_var(set_name, profile)} is set but '
            f'{_env_var(unset_name, profile)} is not. Set both, or unset both. '
            'Continuing would run as whatever client the next source holds.'
        )
    if env_id and env_secret:
        return Credentials(
            env_id,
            env_secret,
            _resolve_environment(environment, profile, None),
            f'environment ({profile})' if profile else 'environment',
            profile,
        )

    ring_id, ring_secret, ring_env = _credentials_from_keyring(
        keyring_service_name(profile)
    )
    if ring_id and ring_secret:
        return Credentials(
            ring_id,
            ring_secret,
            _resolve_environment(environment, profile, ring_env),
            f'keychain ({keyring_service_name(profile)})',
            profile,
        )

    raise _missing_credentials_error(profile)


# =============================================================================
# AVELA CLIENT
# =============================================================================


class AvelaClient:
    """
    HTTP client for the Avela API, with rate limiting and retries built in.

    It logs in with OAuth2, spaces out requests to stay under the rate limit,
    waits and retries when the API answers 429, and retries timeouts and
    server errors. When a response carries a Retry-After header, it waits that
    long.

    Example:
        client = AvelaClient(
            client_id='your_id',
            client_secret='your_secret',
            environment='prod'
        )

        # Fetch paginated data
        forms = []
        offset = 0
        while True:
            response = client.get('/forms', params={'limit': 1000, 'offset': offset})
            data = response.json()
            forms.extend(data.get('forms', []))
            if len(data.get('forms', [])) < 1000:
                break
            offset += 1000

    Attributes:
        environment: Which environment to use (prod, qa, uat, dev)
        base_url: Base URL for API requests
        access_token: Current OAuth2 access token
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        environment: str | None = None,
        requests_per_period: int = RATE_LIMIT_REQUESTS,
        period_seconds: float = RATE_LIMIT_PERIOD,
        profile: str | None = None,
    ):
        """
        Set up the Avela API client.

        Leave out client_id and client_secret to have them found for you in
        environment variables or the OS keychain. See
        resolve_credentials().

        Args:
            client_id: OAuth2 client ID (from Avela)
            client_secret: OAuth2 client secret (from Avela)
            environment: Which environment ('prod', 'staging', 'uat', 'qa', 'dev')
            requests_per_period: Requests allowed per period (default: 100)
            period_seconds: Length of the rate limit period (default: 300)
            profile: Named credential set, for working with several clients
        """
        credentials = resolve_credentials(
            client_id, client_secret, environment, profile=profile
        )
        self.client_id = credentials.client_id
        self.client_secret = credentials.client_secret
        self.credential_source = credentials.source
        self.profile = credentials.profile
        environment = credentials.environment
        self.environment = environment

        # Build the URLs for this environment
        self.auth_url, self.base_url, self.audience = environment_urls(environment)

        # Rate limiting state
        self._min_interval = (period_seconds / requests_per_period) * 1.1  # 10% buffer
        self._last_request_time = 0.0

        # Authentication state
        self.access_token: str | None = None
        self._token_expires_at = 0.0

    def authenticate(self) -> str:
        """
        Log in to the Avela API and get an access token.

        Uses the OAuth2 client credentials flow. Tokens last 24 hours.

        Returns:
            Access token string

        Raises:
            requests.RequestException: If the login fails
        """
        print(f'Authenticating with Avela API ({self.environment})...')

        response = requests.post(
            self.auth_url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'audience': self.audience,
            },
            timeout=30,
        )
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data['access_token']

        # Track token expiration (default 24 hours, refresh 1 hour early)
        expires_in = token_data.get('expires_in', 86400)
        self._token_expires_at = time.time() + expires_in - 3600

        print(f'Authentication successful! Token expires in {expires_in // 3600} hours.')
        return self.access_token

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        if not self.access_token or time.time() >= self._token_expires_at:
            self.authenticate()

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limits."""
        elapsed = time.time() - self._last_request_time
        wait_time = self._min_interval - elapsed

        if wait_time > 0:
            time.sleep(wait_time)

    def _handle_rate_limit_response(self, response: requests.Response) -> None:
        """Handle a 429 response by waiting the appropriate time."""
        try:
            retry_after = int(response.headers.get('Retry-After', 10))
        except ValueError:
            # The header can also be a date or malformed. Wait a safe default.
            retry_after = 10
        # A proxy can send a negative or huge value. Keep the wait sane.
        retry_after = min(max(retry_after, 1), 300)
        print(
            f'  Rate limited (429). Waiting {retry_after}s (from Retry-After header)...'
        )
        time.sleep(retry_after)

    @backoff.on_exception(
        backoff.expo,
        requests.exceptions.RequestException,
        max_tries=MAX_RETRIES,
        max_time=MAX_RETRY_TIME,
        giveup=lambda e: not _is_server_error(e),
        on_backoff=_on_backoff,
        on_giveup=_on_giveup,
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Make an HTTP request with rate limiting and retry logic.

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint (e.g., '/forms')
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails after all retries
        """
        self._ensure_authenticated()
        self._wait_for_rate_limit()

        # Build full URL
        url = f'{self.base_url}{endpoint}' if endpoint.startswith('/') else endpoint

        # Set default headers
        headers = kwargs.pop('headers', {})
        headers.setdefault('Authorization', f'Bearer {self.access_token}')
        headers.setdefault('Content-Type', 'application/json')

        # Set default timeout
        kwargs.setdefault('timeout', 60)

        # Make the request
        self._last_request_time = time.time()
        response = requests.request(method, url, headers=headers, **kwargs)

        # Handle rate limiting
        if response.status_code == 429:
            self._handle_rate_limit_response(response)
            raise requests.exceptions.RequestException(
                'Rate limited (429)',
                response=response,
            )

        # Raise for server errors (will be retried by backoff)
        if response.status_code >= 500:
            response.raise_for_status()

        return response

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Make a GET request to the API.

        Args:
            endpoint: API endpoint (e.g., '/forms', '/applicants')
            **kwargs: Additional arguments (params, headers, etc.)

        Returns:
            Response object

        Example:
            response = client.get('/forms', params={'limit': 100})
            forms = response.json().get('forms', [])
        """
        return self._request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Make a POST request to the API.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments (json, data, headers, etc.)

        Returns:
            Response object

        Example:
            response = client.post('/forms/search', json={'status': 'submitted'})
        """
        return self._request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make a PUT request to the API."""
        return self._request('PUT', endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make a PATCH request to the API."""
        return self._request('PATCH', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make a DELETE request to the API."""
        return self._request('DELETE', endpoint, **kwargs)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_client(
    environment: str | None = None,
    profile: str | None = None,
) -> AvelaClient:
    """
    Create an AvelaClient using whichever credentials the user has set up.

    Recipes should call this. It checks environment variables, then the OS
    keychain. See resolve_credentials().

    Args:
        environment: Use this environment instead ('prod', 'uat', 'qa', 'dev')
        profile: Named credential set, for working with several clients

    Returns:
        A ready to use AvelaClient

    Example:
        client = create_client()                     # default credentials
        client = create_client(profile='district-a')    # a specific client
        response = client.get('/forms')
    """
    return AvelaClient(environment=environment, profile=profile)


# =============================================================================
# STANDALONE USAGE
# =============================================================================


if __name__ == '__main__':
    # Runs a short test when you run this file directly
    print('Avela API Client (test mode)')
    print('=' * 40)

    try:
        client = create_client()
        print(f'Credentials loaded from: {client.credential_source}')
        client.authenticate()

        # One small request, to prove the credentials work
        print('\nFetching forms (limit=5)...')
        response = client.get('/forms', params={'limit': 5})

        if response.status_code == 200:
            data = response.json()
            forms = data.get('forms', [])
            print(f'Retrieved {len(forms)} form(s)')
            for form in forms[:3]:
                print(f'  - {form.get("id", "unknown")[:8]}...')
        else:
            print(f'Error: {response.status_code}')
            print(response.text)

    except ValueError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
