#!/usr/bin/env python3
"""
Script to launch a Playwright browser, open a blank page, and allow manual navigation.
When the user types 'capture', the script records all network request and response headers,
and cookies for the current page, saving them to a JSON file.
Type 'exit' to close the browser and end the script.
"""

import json
import os
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        # Launch browser in headed mode for manual interaction
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Store all network responses
        responses = []
        page.on("response", lambda response: responses.append(response))

        print("Browser launched. Navigate to the desired page(s).")
        print("Type 'capture' and press Enter to record headers and cookies.")
        print("Type 'exit' and press Enter to close the browser and exit.")

        while True:
            command = input(">> ").strip().lower()
            if command == "capture":
                current_url = page.url
                parsed = urlparse(current_url)
                domain = parsed.netloc.replace(":", "_")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{domain}_{timestamp}.json"

                # Extract cookies
                cookies = context.cookies()

                # Extract request and response headers for each response from the same domain
                data = []
                for response in responses:
                    if urlparse(response.url).netloc == parsed.netloc:
                        data.append({
                            "url": response.url,
                            "request_headers": response.request.headers,
                            "response_headers": response.headers
                        })

                output = {
                    "url": current_url,
                    "cookies": cookies,
                    "network": data
                }

                # Ensure output directory exists
                os.makedirs("captures", exist_ok=True)
                path = os.path.join("captures", filename)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2)
                print(f"Capture saved to {path}")

            elif command == "exit":
                print("Closing browser and exiting script.")
                break
            else:
                print("Unknown command. Please type 'capture' or 'exit'.")

        browser.close()

if __name__ == "__main__":
    main()
