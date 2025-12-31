#!/usr/bin/env python3
"""
Watersmart.com session manager with automatic cookie handling.

This module provides a session manager that:
1. Authenticates using Playwright (headless)
2. Extracts and manages session cookies
3. Provides requests.Session for API calls
4. Automatically re-authenticates on 401 errors
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests
from playwright.sync_api import sync_playwright


logger = logging.getLogger(__name__)


class WatersmartSessionManager:
    """
    Manages authenticated sessions for paloalto.watersmart.com.

    Handles SAML/SSO authentication via Playwright and provides
    a requests.Session with valid cookies for API access.

    Example:
        >>> manager = WatersmartSessionManager('username', 'password')
        >>> session = manager.get_session()
        >>> response = session.get('https://paloalto.watersmart.com/index.php/rest/v1/Chart/RealTimeChart')
        >>> data = response.json()
    """

    def __init__(self, username: str, password: str, headless: bool = True):
        """
        Initialize session manager.

        Args:
            username: CPAU username
            password: CPAU password
            headless: Run Playwright in headless mode (default: True)
        """
        self.username = username
        self.password = password
        self.headless = headless

        self._cookies: Optional[list] = None
        self._authenticated_at: Optional[datetime] = None

        logger.debug(f"Initialized WatersmartSessionManager for user {username}")

    def authenticate(self) -> None:
        """
        Authenticate with watersmart.com using Playwright.

        Performs SAML/SSO login flow and extracts session cookies.

        Raises:
            Exception: If authentication fails
        """
        logger.info("Authenticating with watersmart.com...")
        start_time = datetime.now()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()

                # Step 1: Login to CPAU portal
                logger.debug("Navigating to CPAU portal...")
                page.goto('https://mycpau.cityofpaloalto.org/Portal')
                page.fill('#txtLogin', self.username)
                page.fill('#txtpwd', self.password)
                page.press('#txtpwd', 'Enter')
                page.wait_for_load_state('networkidle')

                # Step 2: Navigate to watersmart (triggers SAML flow)
                logger.debug("Completing SAML authentication...")
                page.goto('https://paloalto.watersmart.com/index.php/trackUsage')
                page.wait_for_load_state('networkidle')

                # Verify authentication succeeded
                if 'login' in page.url.lower() or 'signin' in page.url.lower():
                    raise Exception("Authentication failed - redirected to login page")

                # Extract cookies
                self._cookies = context.cookies()
                self._authenticated_at = datetime.now()

                browser.close()

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Authentication successful in {elapsed:.1f}s")
        logger.debug(f"Extracted {len(self._cookies)} cookies")

    def is_authenticated(self) -> bool:
        """
        Check if we have valid authentication cookies.

        Returns:
            bool: True if authenticated, False otherwise
        """
        return self._cookies is not None

    def get_session(self, force_refresh: bool = False) -> requests.Session:
        """
        Get a requests.Session with authenticated cookies.

        Args:
            force_refresh: Force re-authentication even if already authenticated

        Returns:
            requests.Session: Session with valid cookies

        Raises:
            Exception: If authentication fails
        """
        # Authenticate if needed
        if force_refresh or not self.is_authenticated():
            self.authenticate()

        # Create session with cookies
        session = requests.Session()

        for cookie in self._cookies:
            session.cookies.set(
                name=cookie['name'],
                value=cookie['value'],
                domain=cookie['domain'],
                path=cookie.get('path', '/')
            )

        # Wrap session to handle 401 errors
        return _AutoRefreshSession(session, self)

    def get_authentication_age(self) -> Optional[timedelta]:
        """
        Get time since last authentication.

        Returns:
            timedelta: Time since authentication, or None if not authenticated
        """
        if self._authenticated_at is None:
            return None

        return datetime.now() - self._authenticated_at


class _AutoRefreshSession:
    """
    Wrapper around requests.Session that automatically re-authenticates on 401.

    This is an internal class - users should use WatersmartSessionManager.get_session().
    """

    def __init__(self, session: requests.Session, manager: WatersmartSessionManager):
        """
        Initialize auto-refresh session wrapper.

        Args:
            session: Underlying requests.Session
            manager: WatersmartSessionManager for re-authentication
        """
        self._session = session
        self._manager = manager

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with automatic re-authentication on 401.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for requests

        Returns:
            requests.Response: Response object

        Raises:
            requests.exceptions.RequestException: On request failure (after retry)
        """
        # Make request
        response = self._session.request(method, url, **kwargs)

        # Check if authentication expired
        if response.status_code == 401:
            logger.warning("Received 401 - re-authenticating...")

            # Re-authenticate
            self._manager.authenticate()

            # Get new session with fresh cookies
            new_session = requests.Session()
            for cookie in self._manager._cookies:
                new_session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie['domain'],
                    path=cookie.get('path', '/')
                )

            # Update underlying session
            self._session = new_session

            # Retry request
            logger.debug(f"Retrying {method} {url}")
            response = self._session.request(method, url, **kwargs)

            if response.status_code == 401:
                logger.error("Still getting 401 after re-authentication")

        return response

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request with auto-refresh."""
        return self.request('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request with auto-refresh."""
        return self.request('POST', url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT request with auto-refresh."""
        return self.request('PUT', url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE request with auto-refresh."""
        return self.request('DELETE', url, **kwargs)

    def head(self, url: str, **kwargs) -> requests.Response:
        """HEAD request with auto-refresh."""
        return self.request('HEAD', url, **kwargs)

    def options(self, url: str, **kwargs) -> requests.Response:
        """OPTIONS request with auto-refresh."""
        return self.request('OPTIONS', url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        """PATCH request with auto-refresh."""
        return self.request('PATCH', url, **kwargs)

    # Expose underlying session attributes
    @property
    def cookies(self):
        """Access to session cookies."""
        return self._session.cookies

    @property
    def headers(self):
        """Access to session headers."""
        return self._session.headers


# Example usage
if __name__ == '__main__':
    import json
    from pathlib import Path

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load credentials
    secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        creds = json.load(f)

    # Create session manager
    manager = WatersmartSessionManager(
        username=creds['userid'],
        password=creds['password'],
        headless=True
    )

    # Get session (authenticates automatically)
    session = manager.get_session()

    # Make API calls
    print("\nTesting API calls...")
    print("=" * 70)

    apis = [
        'https://paloalto.watersmart.com/index.php/rest/v1/Chart/RealTimeChart',
        'https://paloalto.watersmart.com/index.php/rest/v1/Chart/annualChart?module=portal&commentary=full',
    ]

    for api_url in apis:
        print(f"\n{api_url}")
        response = session.get(api_url)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print(f"  ✓ Success - data retrieved")
        else:
            print(f"  ✗ Failed")

    # Check authentication age
    age = manager.get_authentication_age()
    if age:
        print(f"\nAuthenticated {age.total_seconds():.1f} seconds ago")

    print("\n" + "=" * 70)
    print("Session manager test complete!")
