#!/usr/bin/env python3
"""
Test direct API calls with proper session
"""

import json
import re
import requests


def main():
    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })

    # Get homepage for CSRF token
    homepage = session.get('https://mycpau.cityofpaloalto.org/Portal')
    csrf_match = re.search(r'name="__RequestVerificationToken".*?value="([^"]+)"', homepage.text)
    csrf_token = csrf_match.group(1) if csrf_match else None

    # Login
    login_payload = {
        'username': creds['userid'],
        'password': creds['password'],
        'rememberme': False,
        'calledFrom': 'LN',
        'ExternalLoginId': '',
        'LoginMode': '1'
    }

    login_headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'isajax': '1',
        'Referer': 'https://mycpau.cityofpaloalto.org/Portal/'
    }
    if csrf_token:
        login_headers['csrftoken'] = csrf_token

    login_response = session.post(
        'https://mycpau.cityofpaloalto.org/Portal/Default.aspx/validateLogin',
        json=login_payload,
        headers=login_headers
    )
    print(f"Login status: {login_response.status_code}")

    if login_response.status_code != 200:
        print("Login failed")
        return

    # Load Usages page
    print("Loading Usages page...")
    usages_page = session.get('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
    print(f"Usages page status: {usages_page.status_code}")

    # Try LoadUsage with empty payload
    api_headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx'
    }

    print("\nTrying LoadUsage with empty payload...")
    response = session.post(
        'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
        json={},
        headers=api_headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:1000]}")

    # Try with MeterNumber from login response
    login_data = json.loads(login_response.json()['d'])[0]
    print(f"\nUser ID: {login_data.get('UserID')}")
    print(f"Meter Types: {login_data.get('MeterType')}")

    print("\nTrying LoadUsage with MeterNumber and MeterType...")
    response2 = session.post(
        'https://mycpau.cityofpaloalto.org/Portal/Usages.aspx/LoadUsage',
        json={
            'MeterType': 'E',
            'Duration': 'M'
        },
        headers=api_headers
    )
    print(f"Status: {response2.status_code}")
    print(f"Response: {response2.text[:1000]}")


if __name__ == '__main__':
    main()
