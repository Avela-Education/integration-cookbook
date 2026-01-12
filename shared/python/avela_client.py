#!/usr/bin/env python3
"""
Avela API Client with Rate Limiting

A production-ready HTTP client for the Avela API that handles:
- OAuth2 authentication (client credentials flow)
- Rate limiting (100 requests per 5 minutes)
- Automatic retry with exponential backoff
- Proper 429 (Too Many Requests) handling

Rate Limit Details:
    - Limit: 100 requests per 5 minutes (enforced by AWS WAF)
    - This client proactively spaces requests to stay under the limit
    - If rate limited, respects Retry-After header with exponential backoff

Usage:
    from avela_client import AvelaClient

    client = AvelaClient(
        client_id='your_client_id',
        client_secret='your_client_secret',
        environment='prod'  # or 'qa', 'uat', 'dev'
    )

    # Make API requests - rate limiting handled automatically
    response = client.get('/forms', params={'limit': 100})
    data = response.json()

Author: Avela Education
License: MIT
"""

import time
from typing import Any

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
# AVELA CLIENT
# =============================================================================


class AvelaClient:
    """
    HTTP client for the Avela API with built-in rate limiting and retry logic.

    Features:
        - OAuth2 client credentials authentication
        - Proactive rate limiting (spaces requests to stay under limit)
        - Reactive rate limiting (handles 429 responses with backoff)
        - Automatic retry for transient failures (5xx, timeouts)
        - Respects Retry-After header from server

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
        environment: Target environment (prod, qa, uat, dev)
        base_url: Base URL for API requests
        access_token: Current OAuth2 access token
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        environment: str = 'prod',
        requests_per_period: int = RATE_LIMIT_REQUESTS,
        period_seconds: float = RATE_LIMIT_PERIOD,
    ):
        """
        Initialize the Avela API client.

        Args:
            client_id: OAuth2 client ID (provided by Avela)
            client_secret: OAuth2 client secret (provided by Avela)
            environment: Target environment ('prod', 'staging', 'uat', 'qa', 'dev')
            requests_per_period: Max requests allowed per period (default: 100)
            period_seconds: Rate limit period in seconds (default: 300)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment

        # Build URLs based on environment
        if environment == 'prod':
            self.auth_url = 'https://auth.avela.org/oauth/token'
            self.base_url = 'https://prod.execute-api.apply.avela.org/api/rest/v2'
            self.audience = 'https://api.apply.avela.org/v1/graphql'
        elif environment == 'staging':
            # Staging uses a direct Auth0 URL (exception to the normal pattern)
            self.auth_url = 'https://avela-staging.us.auth0.com/oauth/token'
            self.base_url = 'https://staging.execute-api.apply.avela.org/api/rest/v2'
            self.audience = 'https://staging.api.apply.avela.org/v1/graphql'
        else:
            self.auth_url = f'https://{environment}.auth.avela.org/oauth/token'
            self.base_url = (
                f'https://{environment}.execute-api.apply.avela.org/api/rest/v2'
            )
            self.audience = f'https://{environment}.api.apply.avela.org/v1/graphql'

        # Rate limiting state
        self._min_interval = (period_seconds / requests_per_period) * 1.1  # 10% buffer
        self._last_request_time = 0.0

        # Authentication state
        self.access_token: str | None = None
        self._token_expires_at = 0.0

    def authenticate(self) -> str:
        """
        Authenticate with the Avela API and get an access token.

        Uses OAuth2 client credentials flow. Tokens are valid for 24 hours.

        Returns:
            Access token string

        Raises:
            requests.RequestException: If authentication fails
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
        retry_after = int(response.headers.get('Retry-After', 10))
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


def create_client_from_config(config_path: str = 'config.json') -> AvelaClient:
    """
    Create an AvelaClient from a config.json file.

    Args:
        config_path: Path to config.json file

    Returns:
        Configured AvelaClient instance

    Example:
        client = create_client_from_config('config.json')
        response = client.get('/forms')
    """
    import json
    from pathlib import Path

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file '{config_path}' not found. Create it from config.example.json"
        )

    with open(config_file, encoding='utf-8') as f:
        config = json.load(f)

    required = ['client_id', 'client_secret', 'environment']
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f'Missing required config fields: {", ".join(missing)}')

    return AvelaClient(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        environment=config['environment'],
    )


# =============================================================================
# STANDALONE USAGE
# =============================================================================


if __name__ == '__main__':
    # Example usage when run directly
    import sys

    print('Avela API Client - Test Mode')
    print('=' * 40)

    try:
        client = create_client_from_config()
        client.authenticate()

        # Test API call
        print('\nFetching forms (limit=5)...')
        response = client.get('/forms', params={'limit': 5})

        if response.status_code == 200:
            data = response.json()
            forms = data.get('forms', [])
            print(f'Success! Retrieved {len(forms)} form(s)')
            for form in forms[:3]:
                print(f'  - {form.get("id", "unknown")[:8]}...')
        else:
            print(f'Error: {response.status_code}')
            print(response.text)

    except FileNotFoundError as e:
        print(f'Error: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
