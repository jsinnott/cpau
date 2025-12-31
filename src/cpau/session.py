"""
CPAU API Session Management

This module provides the CpauApiSession class which handles authentication
and session management for the CPAU portal.
"""

import json
import logging
import re
import requests
from typing import Optional

from .electric_meter import CpauElectricMeter
from .exceptions import (
    CpauAuthenticationError,
    CpauConnectionError,
    CpauApiError,
    CpauMeterNotFoundError
)

logger = logging.getLogger(__name__)


class CpauApiSession:
    """
    Represents an authenticated session with the CPAU web portal.

    This class handles login, session management, and provides access to
    meter objects for retrieving usage data.
    """

    def __init__(self, userid: str, password: str):
        """
        Initialize a CPAU API session.

        Args:
            userid: CPAU account username
            password: CPAU account password

        Raises:
            CpauAuthenticationError: If login fails
            CpauConnectionError: If unable to connect to CPAU portal
        """
        logger.debug(f"Initializing CPAU API session for user: {userid}")
        self._userid = userid
        self._password = password
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self._csrf_token = None
        self._authenticated = False

        # Login automatically on initialization
        logger.debug("Attempting automatic login")
        self.login()

    def login(self) -> bool:
        """
        Authenticate with the CPAU portal.

        This method is called automatically by __init__ but can be called
        again to re-authenticate if the session expires.

        Returns:
            True if login successful, False otherwise

        Raises:
            CpauAuthenticationError: If credentials are invalid
            CpauConnectionError: If unable to connect to CPAU portal
        """
        try:
            # First, get the homepage to establish session cookies and extract CSRF token
            logger.info("Authenticating with CPAU portal")
            logger.debug("Fetching homepage to establish session")
            homepage_response = self._session.get('https://mycpau.cityofpaloalto.org/Portal')

            if homepage_response.status_code != 200:
                logger.error(f"Failed to connect to CPAU portal (status {homepage_response.status_code})")
                raise CpauConnectionError(f"Failed to connect to CPAU portal (status {homepage_response.status_code})")

            # Extract CSRF token from the page
            csrf_token = None
            csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage_response.text)
            if csrf_match:
                csrf_token = csrf_match.group(1)
                logger.debug("Extracted CSRF token from homepage")

            # Prepare login payload
            payload = {
                'username': self._userid,
                'password': self._password,
                'rememberme': False,
                'calledFrom': 'LN',
                'ExternalLoginId': '',
                'LoginMode': '1'
            }

            headers = {
                'Content-Type': 'application/json; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'isajax': '1',
                'Referer': 'https://mycpau.cityofpaloalto.org/Portal/'
            }

            # Add CSRF token if found
            if csrf_token:
                headers['csrftoken'] = csrf_token

            # Submit login request
            logger.debug("Submitting login credentials")
            login_url = 'https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin'
            response = self._session.post(login_url, json=payload, headers=headers)

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if login was successful
                    if 'd' in data:
                        result = json.loads(data['d'])
                        # Result can be a dict or list
                        if isinstance(result, dict):
                            if result.get('STATUS') == '1' or 'UserID' in result:
                                self._authenticated = True
                                logger.info("Successfully authenticated")
                                return True
                        elif isinstance(result, list) and len(result) > 0:
                            if result[0].get('STATUS') == '1' or 'UserID' in result[0]:
                                self._authenticated = True
                                logger.info("Successfully authenticated")
                                return True
                except Exception as e:
                    logger.error(f"Login response error: {e}")
                    raise CpauAuthenticationError(f"Login response error: {e}")

            logger.error("Authentication failed: Invalid credentials")
            raise CpauAuthenticationError("Invalid credentials")

        except requests.RequestException as e:
            raise CpauConnectionError(f"Network error during login: {e}")

    def get_electric_meters(self) -> list[CpauElectricMeter]:
        """
        Retrieve all active electric meters associated with this account.

        Returns:
            List of CpauElectricMeter objects (typically just one)

        Raises:
            CpauApiError: If API request fails
        """
        if not self._authenticated:
            logger.error("Cannot retrieve meters: Not authenticated")
            raise CpauAuthenticationError("Not authenticated. Call login() first.")

        try:
            # Navigate to Usages page to get CSRF token
            logger.debug("Retrieving CSRF token from Usages page")
            self._csrf_token = self._get_csrf_token('Usages')

            # Get meter info
            logger.debug("Fetching electric meter information")
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                'csrftoken': self._csrf_token
            }

            meter_url = 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/BindMultiMeter'
            meter_response = self._session.post(meter_url, json={'MeterType': 'E'}, headers=headers)

            if meter_response.status_code != 200:
                logger.error(f"Failed to fetch meter information (status {meter_response.status_code})")
                raise CpauApiError(f"Failed to fetch meter information (status {meter_response.status_code})")

            meter_data = meter_response.json()
            meter_info = json.loads(meter_data['d'])

            # Get all active meters
            active_meters = []
            if 'MeterDetails' in meter_info:
                for meter in meter_info['MeterDetails']:
                    if meter['Status'] == 1:  # Active meter
                        active_meters.append(CpauElectricMeter(self, meter))

            logger.info(f"Found {len(active_meters)} active electric meter(s)")
            return active_meters

        except requests.RequestException as e:
            raise CpauApiError(f"Network error retrieving meters: {e}")

    def get_electric_meter(self, meter_number: Optional[str] = None) -> CpauElectricMeter:
        """
        Get a specific electric meter, or the default/only meter if meter_number is None.

        Args:
            meter_number: Optional meter number to retrieve. If None, returns the
                         first active meter found.

        Returns:
            CpauElectricMeter object

        Raises:
            CpauMeterNotFoundError: If specified meter not found
            CpauApiError: If API request fails
        """
        meters = self.get_electric_meters()

        if not meters:
            logger.error("No active electric meters found")
            raise CpauMeterNotFoundError("No active electric meters found")

        if meter_number is None:
            logger.debug(f"Returning default meter: {meters[0].meter_number}")
            return meters[0]

        logger.debug(f"Looking for meter: {meter_number}")
        for meter in meters:
            if meter.meter_number == meter_number:
                logger.debug(f"Found meter: {meter_number}")
                return meter

        logger.error(f"Meter {meter_number} not found")
        raise CpauMeterNotFoundError(f"Meter {meter_number} not found")

    @property
    def is_authenticated(self) -> bool:
        """Check if the session is currently authenticated."""
        return self._authenticated

    @property
    def session(self) -> requests.Session:
        """
        Get the underlying requests.Session object.

        This is exposed for use by meter objects but should not typically
        be used directly by library consumers.
        """
        return self._session

    def close(self) -> None:
        """
        Close the session and clean up resources.

        This should be called when done with the session, or use the
        session as a context manager.
        """
        if self._session:
            logger.debug("Closing CPAU API session")
            self._session.close()
            self._authenticated = False

    def __enter__(self) -> 'CpauApiSession':
        """Support for context manager (with statement)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up when exiting context manager."""
        self.close()

    # Private methods for internal use

    def _get_csrf_token(self, page_name: str) -> str:
        """
        Get CSRF token for a specific page.

        Args:
            page_name: Name of the page (e.g., 'Usages')

        Returns:
            CSRF token string

        Raises:
            CpauApiError: If CSRF token not found
        """
        try:
            page_url = f'https://mycpau.cityofpaloalto.org/Portal/{page_name}.aspx'
            page_response = self._session.get(page_url)

            if page_response.status_code != 200:
                raise CpauApiError(f"Failed to load {page_name} page (status {page_response.status_code})")

            # Extract CSRF token from the page
            csrf_match = re.search(r'name="ctl00\$hdnCSRFToken".*?value="([^"]+)"', page_response.text)
            if csrf_match:
                return csrf_match.group(1)

            raise CpauApiError(f"CSRF token not found in {page_name} page")

        except requests.RequestException as e:
            raise CpauApiError(f"Network error retrieving CSRF token: {e}")

    def _make_api_request(self, endpoint: str, payload: dict) -> dict:
        """
        Make an authenticated API request with CSRF token handling.

        Args:
            endpoint: API endpoint name (e.g., 'LoadUsage')
            payload: Request payload dictionary

        Returns:
            Parsed response data

        Raises:
            CpauApiError: If request fails
        """
        if not self._authenticated:
            logger.error("Cannot make API request: Not authenticated")
            raise CpauAuthenticationError("Not authenticated")

        # Ensure we have a CSRF token
        if not self._csrf_token:
            logger.debug("CSRF token not cached, retrieving")
            self._csrf_token = self._get_csrf_token('Usages')

        try:
            logger.debug(f"Making API request to endpoint: {endpoint}")
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx',
                'csrftoken': self._csrf_token
            }

            url = f'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/{endpoint}'
            response = self._session.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"API request to {endpoint} failed (status {response.status_code})")
                raise CpauApiError(f"API request failed (status {response.status_code})")

            response_data = response.json()
            parsed_data = json.loads(response_data['d'])

            logger.debug(f"API request to {endpoint} successful")
            return parsed_data

        except requests.RequestException as e:
            raise CpauApiError(f"Network error during API request: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            raise CpauApiError(f"Failed to parse API response: {e}")
