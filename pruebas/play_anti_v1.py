#!/usr/bin/env python3
"""
sel_click_authenticate.py

This script automates the X.com login flow and clicks the "Autentificar"
button inside nested Arkose iframes using Playwright.
"""

import os
import time
import random
import logging
from playwright.sync_api import sync_playwright

# ——— Logging configuration ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ——— Credentials ———
USERNAME = "antonioreverteandujar@gmx.com"

def human_like_typing(page, element, text, min_delay=0.1, max_delay=0.3):
    """
    Simulate human-like typing with variable delays and occasional pauses
    """
    for char in text:
        element.type(char)
        # Random delay between keystrokes
        time.sleep(random.uniform(min_delay, max_delay))
        
        # Occasionally add a longer pause
        if random.random() < 0.1:  # 10% chance of a longer pause
            time.sleep(random.uniform(0.5, 1.2))

def main():
    # Prepare screenshots directory
    os.makedirs("captures", exist_ok=True)

    with sync_playwright() as p:
        # Launch browser with stealth options
        browser = p.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Create a new browser context with additional stealth settings
        context = browser.new_context(
            viewport=None,  # Use full browser window
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Disable webdriver detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            # Create a new page
            page = context.new_page()

            # Step 1: Navigate to X.com login flow
            logging.info("Navigating to X.com login flow...")
            page.goto("https://x.com/i/flow/login")
            
            # Wait for username input to be visible
            logging.info("Waiting for username field...")
            username_field = page.locator('input[name="text"], input[type="text"]')
            username_field.wait_for(state="visible", timeout=15000)
            
            # Enter username with human-like typing
            logging.info(f"Entering username: {USERNAME}")
            # Clear the field first
            username_field.fill("")
            # Simulate human-like typing
            human_like_typing(page, username_field, USERNAME)
            
            page.screenshot(path="captures/2_username_entered.png")

            # Wait and click Next button with more robust selection
            logging.info("Attempting to click 'Next' button...")
            next_buttons = page.locator(
                'div[role="button"] span:has-text("Next"), div[role="button"] span:has-text("Siguiente")'
            )
            
            # Try multiple methods to click
            clicked = False
            try:
                # Try clicking the first visible next button
                for btn in next_buttons.all():
                    try:
                        # Add a small random delay before clicking
                        time.sleep(random.uniform(0.5, 1.5))
                        btn.click(timeout=5000)
                        clicked = True
                        break
                    except:
                        continue
                
                # If no button clicked, try pressing Enter
                if not clicked:
                    username_field.press("Enter")
                    logging.info("Pressed Enter instead of clicking button.")
            except Exception as click_error:
                logging.error(f"Error clicking Next button: {click_error}")
                username_field.press("Enter")
            
            # Allow time for Arkose iframe to load with some randomness
            page.wait_for_timeout(random.randint(4000, 6000))
            page.screenshot(path="captures/3_after_next.png")

            # Step 4: Switch into first iframe (arkoseFrame)
            logging.info("Locating outer Arkose iframe (arkoseFrame)...")
            outer_iframe = page.frame_locator("#arkoseFrame")
            page.screenshot(path="captures/4_inside_arkoseFrame.png")

            # Step 5: Switch into second iframe (enforcement-frame)
            logging.info("Locating enforcement-frame iframe...")
            enforcement_iframe = outer_iframe.frame_locator('iframe[data-e2e="enforcement-frame"]')
            page.screenshot(path="captures/5_inside_enforcement_frame.png")

            # Step 6: Switch into third iframe (game-core-frame)
            logging.info("Locating game-core-frame iframe...")
            game_iframe = enforcement_iframe.frame_locator("#game-core-frame")
            page.screenshot(path="captures/6_inside_game_core_frame.png")

            # Step 7: Locate and click the "Autentificar" button
            logging.info("Searching for 'Autentificar' button...")
            auth_button = game_iframe.locator("button[data-theme='home.verifyButton']")
            auth_button.wait_for(state="visible", timeout=15000)
            
            # Add a small random delay before clicking
            time.sleep(random.uniform(0.5, 1.5))
            auth_button.click()
            logging.info("Clicked 'Autentificar' button.")
            page.screenshot(path="captures/7_after_click_authenticate.png")

            logging.info("Script completed successfully.")

            # Keep the browser open until user input
            input("Press Enter to close the browser...")

        except Exception as ex:
            logging.error(f"An unexpected error occurred: {ex}", exc_info=True)
            page.screenshot(path="captures/error.png")

        finally:
            # Close browser
            browser.close()

if __name__ == "__main__":
    main()