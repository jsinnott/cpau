#!/usr/bin/env python3
"""
Find where the CSRF token comes from
"""

import json
import asyncio
from playwright.async_api import async_playwright


async def find_token_source():
    """Find where the CSRF token is stored/generated"""

    with open('../../secrets.json', 'r') as f:
        creds = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Login
        await page.goto('https://mycpau.cityofpaloalto.org/Portal')
        await page.wait_for_load_state('networkidle')

        await page.fill('#txtLogin', creds['userid'])
        await page.fill('#txtpwd', creds['password'])
        await page.press('#txtpwd', 'Enter')

        await asyncio.sleep(2)
        await page.wait_for_load_state('networkidle')

        # Navigate to Usages page
        await page.goto('https://mycpau.cityofpaloalto.org/Portal/Usages.aspx')
        await asyncio.sleep(2)

        # Check cookies
        cookies = await context.cookies()
        print("\n=== COOKIES ===")
        for cookie in cookies:
            if 'csrf' in cookie['name'].lower() or 'token' in cookie['name'].lower():
                print(f"{cookie['name']}: {cookie['value'][:60]}...")

        # Check localStorage
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        print("\n=== LOCAL STORAGE ===")
        print(local_storage)

        # Check sessionStorage
        session_storage = await page.evaluate("() => JSON.stringify(sessionStorage)")
        print("\n=== SESSION STORAGE ===")
        print(session_storage)

        # Check for global variables
        print("\n=== GLOBAL VARIABLES (window object) ===")
        csrf_vars = await page.evaluate("""() => {
            const results = {};
            for (let key in window) {
                if (key.toLowerCase().includes('csrf') || key.toLowerCase().includes('token')) {
                    try {
                        const val = window[key];
                        if (typeof val === 'string' && val.length > 10) {
                            results[key] = val;
                        }
                    } catch(e) {}
                }
            }
            return results;
        }""")
        print(json.dumps(csrf_vars, indent=2))

        # Check all inputs/hidden fields
        print("\n=== HIDDEN FIELDS ===")
        hidden_fields = await page.evaluate("""() => {
            const fields = {};
            document.querySelectorAll('input[type="hidden"]').forEach(input => {
                if (input.name || input.id) {
                    fields[input.name || input.id] = input.value;
                }
            });
            return fields;
        }""")
        for name, value in hidden_fields.items():
            if value and len(value) > 10:
                print(f"{name}: {value[:60]}...")

        await browser.close()


if __name__ == '__main__':
    asyncio.run(find_token_source())
