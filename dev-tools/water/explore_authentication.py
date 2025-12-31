#!/usr/bin/env python3
"""
Explore authentication flow from CPAU portal to watersmart.com.

This script traces how authentication works when navigating from the main
CPAU portal to the watersmart.com water usage portal.

Goals:
1. Login to CPAU portal
2. Navigate to water usage section
3. Capture SAML/SSO token exchange
4. Document session establishment with watersmart.com
5. Test if we can make direct API calls to watersmart.com
"""

import json
import re
import sys
from datetime import datetime

# Add src directory to path to import cpau
sys.path.insert(0, '../../src')

from cpau import CpauApiSession


def login_to_cpau(userid, password):
    """
    Login to the main CPAU portal using the cpau library.

    Returns the authenticated CpauApiSession object.
    """
    print("=" * 70)
    print("STEP 1: Logging into CPAU Portal")
    print("=" * 70)

    print("\n1.1 Creating CPAU session and authenticating...")
    try:
        cpau_session = CpauApiSession(userid=userid, password=password)
        print(f"   ✓ Authenticated: {cpau_session.is_authenticated}")

        # Get the underlying requests.Session for direct HTTP calls
        session = cpau_session.session
        print(f"   ✓ Got underlying requests session")

        return cpau_session, session
    except Exception as e:
        print(f"   ✗ Login failed: {e}")
        return None, None


def explore_water_navigation(session):
    """
    Explore how to navigate from CPAU portal to water usage pages.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Exploring Water Usage Navigation")
    print("=" * 70)

    # Try to find links to water usage on the main portal
    print("\n2.1 Checking main portal for water usage links...")

    # Common water-related URLs to try
    water_urls = [
        'https://mycpau.cityofpaloalto.org/Portal/WaterUsages.aspx',
        'https://mycpau.cityofpaloalto.org/Portal/Water.aspx',
        'https://mycpau.cityofpaloalto.org/Portal/WaterUsage.aspx',
        'https://paloalto.watersmart.com',
        'https://paloalto.watersmart.com/index.php/welcome',
        'https://paloalto.watersmart.com/index.php/trackUsage',
    ]

    results = {}

    for url in water_urls:
        print(f"\n   Trying: {url}")
        try:
            # Don't follow redirects initially - we want to see them
            response = session.get(url, allow_redirects=False)

            print(f"      Status: {response.status_code}")

            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location', 'Not specified')
                print(f"      Redirect to: {location}")

                # Follow the redirect chain
                redirect_chain = [url]
                current_response = response

                for i in range(10):  # Max 10 redirects
                    if current_response.status_code not in [301, 302, 303, 307, 308]:
                        break

                    location = current_response.headers.get('Location')
                    if not location:
                        break

                    # Handle relative URLs
                    if location.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(redirect_chain[-1])
                        location = f"{parsed.scheme}://{parsed.netloc}{location}"

                    redirect_chain.append(location)
                    print(f"      Redirect {i+1}: {location}")

                    try:
                        current_response = session.get(location, allow_redirects=False)
                        print(f"         Status: {current_response.status_code}")
                    except Exception as e:
                        print(f"         Error: {e}")
                        break

                results[url] = {
                    'initial_status': response.status_code,
                    'redirect_chain': redirect_chain,
                    'final_status': current_response.status_code if 'current_response' in locals() else None
                }

            elif response.status_code == 200:
                print(f"      ✓ Direct access successful")
                print(f"      Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                print(f"      Content length: {len(response.content)} bytes")

                results[url] = {
                    'status': 200,
                    'accessible': True,
                    'content_type': response.headers.get('Content-Type'),
                    'content_length': len(response.content)
                }
            else:
                print(f"      ✗ Unexpected status")
                results[url] = {
                    'status': response.status_code,
                    'accessible': False
                }

        except Exception as e:
            print(f"      ✗ Error: {e}")
            results[url] = {
                'error': str(e)
            }

    return results


def analyze_watersmart_session(session):
    """
    Analyze the session state for watersmart.com.
    """
    print("\n" + "=" * 70)
    print("STEP 3: Analyzing Watersmart.com Session")
    print("=" * 70)

    print("\n3.1 Current session cookies:")
    for cookie in session.cookies:
        domain = cookie.domain
        name = cookie.name
        # Don't print full cookie values for security
        value_preview = cookie.value[:20] + "..." if len(cookie.value) > 20 else cookie.value
        print(f"   {domain}: {name} = {value_preview}")

    print("\n3.2 Testing direct access to watersmart.com pages:")

    test_urls = [
        ('Track Usage Page', 'https://paloalto.watersmart.com/index.php/trackUsage'),
        ('Download Page', 'https://paloalto.watersmart.com/index.php/accountPreferences/download'),
        ('Main Page', 'https://paloalto.watersmart.com'),
    ]

    for name, url in test_urls:
        print(f"\n   Testing {name}:")
        print(f"   URL: {url}")

        try:
            response = session.get(url, allow_redirects=True)
            print(f"      Final status: {response.status_code}")
            print(f"      Final URL: {response.url}")
            print(f"      Content-Type: {response.headers.get('Content-Type', 'unknown')}")

            # Check if we got redirected to login
            if 'login' in response.url.lower() or 'signin' in response.url.lower():
                print(f"      ⚠ Redirected to login page - not authenticated")
            elif response.status_code == 200:
                print(f"      ✓ Successfully accessed")

                # Look for indicators of successful authentication
                if 'logout' in response.text.lower():
                    print(f"      ✓ Found logout link - likely authenticated")

                # Save a sample of the page for inspection
                filename = f"/tmp/watersmart_{name.replace(' ', '_').lower()}.html"
                with open(filename, 'w') as f:
                    f.write(response.text)
                print(f"      Saved page content to: {filename}")

        except Exception as e:
            print(f"      ✗ Error: {e}")


def search_for_saml_tokens(session):
    """
    Look for SAML tokens or SSO-related data in responses.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Searching for SAML/SSO Tokens")
    print("=" * 70)

    print("\n4.1 Checking CPAU portal pages for SAML references...")

    # Try the main portal page
    try:
        response = session.get('https://mycpau.cityofpaloalto.org/Portal')

        # Look for SAML-related patterns
        saml_patterns = [
            r'SAMLRequest',
            r'SAMLResponse',
            r'RelayState',
            r'watersmart',
            r'sso',
            r'SingleSignOn',
        ]

        for pattern in saml_patterns:
            matches = re.findall(pattern, response.text, re.IGNORECASE)
            if matches:
                print(f"   Found '{pattern}': {len(matches)} occurrences")

    except Exception as e:
        print(f"   ✗ Error: {e}")


def main():
    # Load credentials
    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    print("\n" + "=" * 70)
    print("CPAU Portal to Watersmart.com Authentication Flow Explorer")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Login to CPAU
    cpau_session, session = login_to_cpau(creds['userid'], creds['password'])
    if not cpau_session or not session:
        print("\n✗ Failed to login to CPAU portal. Exiting.")
        return 1

    # Step 2: Explore navigation to water pages
    nav_results = explore_water_navigation(session)

    # Step 3: Analyze watersmart session
    analyze_watersmart_session(session)

    # Step 4: Look for SAML tokens
    search_for_saml_tokens(session)

    # Clean up
    cpau_session.close()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nNavigation Results:")
    for url, result in nav_results.items():
        print(f"\n{url}:")
        if 'redirect_chain' in result:
            print(f"  Redirects: {len(result['redirect_chain']) - 1}")
            for i, redirect_url in enumerate(result['redirect_chain']):
                print(f"    {i}: {redirect_url}")
        elif 'accessible' in result:
            print(f"  Directly accessible: {result['accessible']}")
        elif 'error' in result:
            print(f"  Error: {result['error']}")

    print("\n" + "=" * 70)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    print("\nNext steps:")
    print("1. Review saved HTML files in /tmp/")
    print("2. Check browser developer tools when navigating manually")
    print("3. Look for API calls in the watersmart.com pages")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
