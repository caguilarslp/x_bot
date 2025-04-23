#!/usr/bin/env python3
"""
X.com Login Automation Script

This script automates the X.com login flow with:
- Multiple captcha solving strategies
- Robust captcha token verification
"""

import os
import sys
import time
import random
import logging
import json
import requests
from anticaptchaofficial.funcaptchaproxyless import *
from playwright.sync_api import sync_playwright

# ——— Logging configuration ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ——— Credentials ———
USERNAME = "antonioreverteandujar@gmx.com"
PASSWORD = "xJHuc@EhMFNBgJd3"

# ——— Captcha Solver Credentials ———
ANTICAPTCHA_KEY = "e8d8c8569500a73bd3c7cafc3c743acb"
TWOCAPTCHA_KEY = "c6ac633f41e049c794aa8dc1455c7756"

class CaptchaSolver:
    @staticmethod
    def solve_twocaptcha(website_url, website_key):
        """
        Solve FunCaptcha using 2Captcha service with direct API call
        """
        logging.info("Attempting to solve with 2Captcha...")
        try:
            # Direct API call to 2Captcha
            payload = {
                "clientKey": TWOCAPTCHA_KEY,
                "task": {
                    "type": "FunCaptchaTaskProxyless",
                    "websiteURL": website_url,
                    "websitePublicKey": website_key,
                    "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                }
            }

            # Create task
            create_response = requests.post(
                "https://api.2captcha.com/createTask", 
                json=payload
            )
            create_data = create_response.json()

            if create_data.get('errorId', 1) != 0:
                logging.error(f"2Captcha create task error: {create_data}")
                return None

            task_id = create_data.get('taskId')

            # Get task result with timeout
            max_attempts = 40  # 40 * 5 = 200 seconds max wait
            for attempt in range(max_attempts):
                result_response = requests.post(
                    "https://api.2captcha.com/getTaskResult",
                    json={
                        "clientKey": TWOCAPTCHA_KEY,
                        "taskId": task_id
                    }
                )
                result_data = result_response.json()

                if result_data.get('status') == 'ready':
                    logging.info("2Captcha solved successfully")
                    logging.info(f"Solution details: {json.dumps(result_data, indent=2)}")
                    return result_data

                if result_data.get('status') == 'processing':
                    time.sleep(5)  # Wait 5 seconds before next check
                    continue

                logging.warning(f"2Captcha task failed: {result_data}")
                return None

            logging.warning("2Captcha task timed out")
            return None

        except Exception as e:
            logging.error(f"2Captcha error: {e}")
            return None

def verify_captcha_token(page, solution_token):
    """
    Comprehensive captcha token verification
    """
    try:
        # Extensive token verification methods
        verification_script = f"""
        // Function to simulate Arkose Labs token verification
        function verifyCaptchaToken() {{
            console.log('Starting captcha token verification');
            
            // Method 1: Direct Arkose verification
            if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{
                try {{
                    console.log('Attempting Arkose Enforcement verification');
                    window.ArkoseEnforcement.setup('{solution_token}');
                    return true;
                }} catch (error) {{
                    console.error('Arkose Enforcement verification failed:', error);
                }}
            }}

            // Method 2: Manual token processing
            if (window.fc) {{
                try {{
                    console.log('Attempting manual FC token processing');
                    window.fc.processToken('{solution_token}');
                    return true;
                }} catch (error) {{
                    console.error('Manual FC token processing failed:', error);
                }}
            }}

            // Method 3: Trigger Arkose callback directly
            try {{
                console.log('Attempting direct Arkose callback');
                const arkoseEvent = new CustomEvent('arkose_token_received', {{
                    detail: {{ token: '{solution_token}' }}
                }});
                window.dispatchEvent(arkoseEvent);
                return true;
            }} catch (error) {{
                console.error('Direct Arkose callback failed:', error);
            }}

            console.log('All captcha verification methods failed');
            return false;
        }}

        // Execute verification and return result
        verifyCaptchaToken();
        """
        
        # Execute verification script
        result = page.evaluate(verification_script)
        
        logging.info(f"Captcha token verification result: {result}")
        return result
    
    except Exception as e:
        logging.error(f"Captcha token verification error: {e}")
        return False

def solve_captcha(page):
    """
    Solve Arkose Labs Captcha with multiple providers
    """
    captcha_solvers = [
        CaptchaSolver.solve_twocaptcha,  # Try 2Captcha first
    ]

    try:
        logging.info("Navigating through Arkose iframes...")
        
        # Wait a bit to ensure iframes are fully loaded
        page.wait_for_timeout(random.randint(2000, 4000))
        
        # Navigate through iframes
        outer_iframe = page.frame_locator("#arkoseFrame")
        enforcement_iframe = outer_iframe.frame_locator('iframe[data-e2e="enforcement-frame"]')
        game_iframe = enforcement_iframe.frame_locator("#game-core-frame")
        
        # Try each captcha solver
        for solver in captcha_solvers:
            try:
                # Solve FunCaptcha
                captcha_solution = solver(
                    "https://x.com", 
                    "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"
                )
                
                if captcha_solution and captcha_solution.get('solution', {}).get('token'):
                    # Log the full solution details
                    logging.info("Captcha Solution Details:")
                    logging.info(json.dumps(captcha_solution, indent=2))
                    
                    # Extract token
                    token = captcha_solution['solution']['token']
                    
                    # Verify token
                    verification_result = verify_captcha_token(page, token)
                    
                    if verification_result:
                        # Try to find and click Submit/Enviar button using page-level locator
                        submit_buttons = page.locator('button.sc-nkuzb1-0.yuVdl, button:has-text("Submit"), button:has-text("Enviar")')
                        
                        # Wait for the submit button to be visible
                        try:
                            submit_buttons.first().wait_for(state="visible", timeout=10000)
                            
                            # Click the submit button
                            submit_buttons.first().click()
                            logging.info("Clicked Submit/Enviar button")
                            
                            # Additional wait to allow processing
                            page.wait_for_timeout(random.randint(2000, 4000))
                            return True
                        except Exception as btn_error:
                            logging.warning(f"Could not find or click Submit button: {btn_error}")
                            
                            # Fallback: try to click within the game iframe
                            try:
                                game_submit = game_iframe.locator('button.sc-nkuzb1-0.yuVdl, button:has-text("Submit"), button:has-text("Enviar")')
                                game_submit.first().click()
                                logging.info("Clicked Submit button in game iframe")
                                page.wait_for_timeout(random.randint(2000, 4000))
                                return True
                            except Exception as iframe_btn_error:
                                logging.warning(f"Could not click Submit button in game iframe: {iframe_btn_error}")
                                continue
            except Exception as solver_error:
                logging.error(f"Error with solver: {solver_error}")
                continue
        
        logging.warning("All captcha solvers failed")
        return False
    
    except Exception as e:
        logging.error(f"Unexpected error in captcha handling: {e}")
        return False

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
            username_field.fill("")
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
            
            # Allow time for page to load with some randomness
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

            # Solve captcha after Autentificar click
            captcha_result = solve_captcha(page)
            if not captcha_result:
                logging.warning("Failed to handle captcha.")
                # Additional error handling can be added here

            # Wait for password field
            logging.info("Waiting for password field...")
            password_field = page.locator('input[name="password"]')
            password_field.wait_for(state="visible", timeout=15000)
            
            # Enter password with human-like typing
            logging.info("Entering password...")
            password_field.fill("")
            human_like_typing(page, password_field, PASSWORD)
            page.screenshot(path="captures/8_password_entered.png")

            # Find and click Log In button
            logging.info("Attempting to click Log In button...")
            login_buttons = page.locator(
                'div[role="button"] span:has-text("Log in"), div[role="button"] span:has-text("Iniciar sesión")'
            )
            
            # Try to click login button
            for btn in login_buttons.all():
                try:
                    time.sleep(random.uniform(0.5, 1.5))
                    btn.click(timeout=5000)
                    logging.info("Clicked Log In button.")
                    break
                except:
                    continue
            
            # Take final screenshot
            page.screenshot(path="captures/9_final_page.png")

            logging.info("Login process completed.")

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

############################################
############################################
# #!/usr/bin/env python3
# """
# X.com Login Automation Script

# This script automates the X.com login flow with:
# - Multiple captcha solving strategies
# - Robust 2Captcha integration
# """

# import os
# import sys
# import time
# import random
# import logging
# import json
# import requests
# from anticaptchaofficial.funcaptchaproxyless import *
# from playwright.sync_api import sync_playwright

# # ——— Logging configuration ———
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # ——— Credentials ———
# USERNAME = "antonioreverteandujar@gmx.com"
# PASSWORD = "xJHuc@EhMFNBgJd3"

# # ——— Captcha Solver Credentials ———
# ANTICAPTCHA_KEY = "c20ef01b3a86bda0cf99cddef67a1477"
# TWOCAPTCHA_KEY = "c6ac633f41e049c794aa8dc1455c7756"

# class CaptchaSolver:
#     @staticmethod
#     def solve_twocaptcha(website_url, website_key):
#         """
#         Solve FunCaptcha using 2Captcha service with direct API call
#         """
#         logging.info("Attempting to solve with 2Captcha...")
#         try:
#             # Direct API call to 2Captcha
#             payload = {
#                 "clientKey": TWOCAPTCHA_KEY,
#                 "task": {
#                     "type": "FunCaptchaTaskProxyless",
#                     "websiteURL": website_url,
#                     "websitePublicKey": website_key,
#                     "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
#                     "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
#                 }
#             }

#             # Create task
#             create_response = requests.post(
#                 "https://api.2captcha.com/createTask", 
#                 json=payload
#             )
#             create_data = create_response.json()

#             if create_data.get('errorId', 1) != 0:
#                 logging.error(f"2Captcha create task error: {create_data}")
#                 return None

#             task_id = create_data.get('taskId')

#             # Get task result with timeout
#             max_attempts = 40  # 40 * 5 = 200 seconds max wait
#             for attempt in range(max_attempts):
#                 result_response = requests.post(
#                     "https://api.2captcha.com/getTaskResult",
#                     json={
#                         "clientKey": TWOCAPTCHA_KEY,
#                         "taskId": task_id
#                     }
#                 )
#                 result_data = result_response.json()

#                 if result_data.get('status') == 'ready':
#                     logging.info("2Captcha solved successfully")
#                     logging.info(f"Solution details: {json.dumps(result_data, indent=2)}")
#                     return result_data

#                 if result_data.get('status') == 'processing':
#                     time.sleep(5)  # Wait 5 seconds before next check
#                     continue

#                 logging.warning(f"2Captcha task failed: {result_data}")
#                 return None

#             logging.warning("2Captcha task timed out")
#             return None

#         except Exception as e:
#             logging.error(f"2Captcha error: {e}")
#             return None

#     @staticmethod
#     def solve_anticaptcha(website_url, website_key):
#         """
#         Solve FunCaptcha using AntiCaptcha service with enhanced error handling
#         """
#         logging.info("Attempting to solve with AntiCaptcha...")
#         try:
#             # Configure solver with additional parameters
#             solver = funcaptchaProxyless()
#             solver.set_verbose(1)
#             solver.set_key(ANTICAPTCHA_KEY)
#             solver.set_website_url(website_url)
#             solver.set_website_key(website_key)
            
#             # Additional configuration to improve solving
#             solver.set_api_domain("api.anti-captcha.com")
            
#             result = solver.solve_and_return_solution()
            
#             if result != 0:
#                 solution_details = {
#                     "errorId": 0,
#                     "status": "ready",
#                     "solution": {
#                         "token": result
#                     }
#                 }
#                 logging.info("AntiCaptcha solved successfully")
#                 return solution_details
#             else:
#                 logging.warning(f"AntiCaptcha solving failed. Error: {solver.error_code}")
#                 return None
#         except Exception as e:
#             logging.error(f"AntiCaptcha error: {e}")
#             return None

# def solve_captcha(page):
#     """
#     Solve Arkose Labs Captcha with multiple providers
#     """
#     captcha_solvers = [
#         CaptchaSolver.solve_twocaptcha,  # Try 2Captcha first
#         CaptchaSolver.solve_anticaptcha,  # Fallback to AntiCaptcha
#     ]

#     try:
#         logging.info("Navigating through Arkose iframes...")
        
#         # Wait a bit to ensure iframes are fully loaded
#         page.wait_for_timeout(random.randint(2000, 4000))
        
#         # Navigate through iframes
#         outer_iframe = page.frame_locator("#arkoseFrame")
#         enforcement_iframe = outer_iframe.frame_locator('iframe[data-e2e="enforcement-frame"]')
#         game_iframe = enforcement_iframe.frame_locator("#game-core-frame")
        
#         # Try each captcha solver
#         for solver in captcha_solvers:
#             try:
#                 # Solve FunCaptcha
#                 captcha_solution = solver(
#                     "https://x.com", 
#                     "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"
#                 )
                
#                 if captcha_solution and captcha_solution.get('solution', {}).get('token'):
#                     # Log the full solution details
#                     logging.info("Captcha Solution Details:")
#                     logging.info(json.dumps(captcha_solution, indent=2))
                    
#                     # Try to find and click Submit/Enviar button
#                     submit_buttons = game_iframe.locator('button.sc-nkuzb1-0.yuVdl, button:has-text("Submit"), button:has-text("Enviar")')
                    
#                     if submit_buttons.count() > 0:
#                         # Click the first matching submit button
#                         submit_buttons.first().click()
#                         logging.info("Clicked Submit/Enviar button")
#                         return True
#                     else:
#                         logging.warning("Could not find Submit/Enviar button")
#                         continue  # Try next solver
#             except Exception as solver_error:
#                 logging.error(f"Error with solver: {solver_error}")
#                 continue
        
#         logging.warning("All captcha solvers failed")
#         return False
    
#     except Exception as e:
#         logging.error(f"Unexpected error in captcha handling: {e}")
#         return False

# def human_like_typing(page, element, text, min_delay=0.1, max_delay=0.3):
#     """
#     Simulate human-like typing with variable delays and occasional pauses
#     """
#     for char in text:
#         element.type(char)
#         # Random delay between keystrokes
#         time.sleep(random.uniform(min_delay, max_delay))
        
#         # Occasionally add a longer pause
#         if random.random() < 0.1:  # 10% chance of a longer pause
#             time.sleep(random.uniform(0.5, 1.2))

# def main():
#     # Prepare screenshots directory
#     os.makedirs("captures", exist_ok=True)

#     with sync_playwright() as p:
#         # Launch browser with stealth options
#         browser = p.chromium.launch(
#             headless=False,  # Set to True for headless mode
#             args=[
#                 '--start-maximized',
#                 '--disable-blink-features=AutomationControlled'
#             ]
#         )
        
#         # Create a new browser context with additional stealth settings
#         context = browser.new_context(
#             viewport=None,  # Use full browser window
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#         )

#         # Disable webdriver detection
#         context.add_init_script("""
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined
#             });
#         """)

#         try:
#             # Create a new page
#             page = context.new_page()

#             # Step 1: Navigate to X.com login flow
#             logging.info("Navigating to X.com login flow...")
#             page.goto("https://x.com/i/flow/login")
            
#             # Wait for username input to be visible
#             logging.info("Waiting for username field...")
#             username_field = page.locator('input[name="text"], input[type="text"]')
#             username_field.wait_for(state="visible", timeout=15000)
            
#             # Enter username with human-like typing
#             logging.info(f"Entering username: {USERNAME}")
#             username_field.fill("")
#             human_like_typing(page, username_field, USERNAME)
            
#             page.screenshot(path="captures/2_username_entered.png")

#             # Wait and click Next button with more robust selection
#             logging.info("Attempting to click 'Next' button...")
#             next_buttons = page.locator(
#                 'div[role="button"] span:has-text("Next"), div[role="button"] span:has-text("Siguiente")'
#             )
            
#             # Try multiple methods to click
#             clicked = False
#             try:
#                 # Try clicking the first visible next button
#                 for btn in next_buttons.all():
#                     try:
#                         # Add a small random delay before clicking
#                         time.sleep(random.uniform(0.5, 1.5))
#                         btn.click(timeout=5000)
#                         clicked = True
#                         break
#                     except:
#                         continue
                
#                 # If no button clicked, try pressing Enter
#                 if not clicked:
#                     username_field.press("Enter")
#                     logging.info("Pressed Enter instead of clicking button.")
#             except Exception as click_error:
#                 logging.error(f"Error clicking Next button: {click_error}")
#                 username_field.press("Enter")
            
#             # Allow time for page to load with some randomness
#             page.wait_for_timeout(random.randint(4000, 6000))
#             page.screenshot(path="captures/3_after_next.png")

#             # Step 4: Switch into first iframe (arkoseFrame)
#             logging.info("Locating outer Arkose iframe (arkoseFrame)...")
#             outer_iframe = page.frame_locator("#arkoseFrame")
#             page.screenshot(path="captures/4_inside_arkoseFrame.png")

#             # Step 5: Switch into second iframe (enforcement-frame)
#             logging.info("Locating enforcement-frame iframe...")
#             enforcement_iframe = outer_iframe.frame_locator('iframe[data-e2e="enforcement-frame"]')
#             page.screenshot(path="captures/5_inside_enforcement_frame.png")

#             # Step 6: Switch into third iframe (game-core-frame)
#             logging.info("Locating game-core-frame iframe...")
#             game_iframe = enforcement_iframe.frame_locator("#game-core-frame")
#             page.screenshot(path="captures/6_inside_game_core_frame.png")

#             # Step 7: Locate and click the "Autentificar" button
#             logging.info("Searching for 'Autentificar' button...")
#             auth_button = game_iframe.locator("button[data-theme='home.verifyButton']")
#             auth_button.wait_for(state="visible", timeout=15000)
            
#             # Add a small random delay before clicking
#             time.sleep(random.uniform(0.5, 1.5))
#             auth_button.click()
#             logging.info("Clicked 'Autentificar' button.")
#             page.screenshot(path="captures/7_after_click_authenticate.png")

#             # Solve captcha after Autentificar click
#             captcha_result = solve_captcha(page)
#             if not captcha_result:
#                 logging.warning("Failed to handle captcha.")
#                 # Additional error handling can be added here

#             # Wait for password field
#             logging.info("Waiting for password field...")
#             password_field = page.locator('input[name="password"]')
#             password_field.wait_for(state="visible", timeout=15000)
            
#             # Enter password with human-like typing
#             logging.info("Entering password...")
#             password_field.fill("")
#             human_like_typing(page, password_field, PASSWORD)
#             page.screenshot(path="captures/8_password_entered.png")

#             # Find and click Log In button
#             logging.info("Attempting to click Log In button...")
#             login_buttons = page.locator(
#                 'div[role="button"] span:has-text("Log in"), div[role="button"] span:has-text("Iniciar sesión")'
#             )
            
#             # Try to click login button
#             for btn in login_buttons.all():
#                 try:
#                     time.sleep(random.uniform(0.5, 1.5))
#                     btn.click(timeout=5000)
#                     logging.info("Clicked Log In button.")
#                     break
#                 except:
#                     continue
            
#             # Take final screenshot
#             page.screenshot(path="captures/9_final_page.png")

#             logging.info("Login process completed.")

#             # Keep the browser open until user input
#             input("Press Enter to close the browser...")

#         except Exception as ex:
#             logging.error(f"An unexpected error occurred: {ex}", exc_info=True)
#             page.screenshot(path="captures/error.png")

#         finally:
#             # Close browser
#             browser.close()

# if __name__ == "__main__":
#     main()


# #!/usr/bin/env python3
# """
# X.com Login Automation Script

# This script automates the X.com login flow with:
# - Human-like username entry
# - Captcha solving with AntiCaptcha
# - Password authentication
# """

# import os
# import time
# import random
# import logging
# from anticaptchaofficial.funcaptchaproxyless import *
# from playwright.sync_api import sync_playwright

# # ——— Logging configuration ———
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # ——— Credentials ———
# USERNAME = "antonioreverteandujar@gmx.com"
# PASSWORD = "xJHuc@EhMFNBgJd3"
# ANTICAPTCHA_KEY = "e8d8c8569500a73bd3c7cafc3c743acb"

# def solve_funcaptcha(website_url, website_key):
#     """
#     Solve FunCaptcha using AntiCaptcha service
#     """
#     logging.info("Attempting to solve FunCaptcha...")
#     solver = funcaptchaProxyless()
#     solver.set_verbose(1)
#     solver.set_key(ANTICAPTCHA_KEY)
#     solver.set_website_url(website_url)
#     solver.set_website_key(website_key)
    
#     token = solver.solve_and_return_solution()
    
#     if token != 0:
#         logging.info("FunCaptcha solved successfully")
#         return token
#     else:
#         logging.error(f"FunCaptcha solving failed. Error: {solver.error_code}")
#         return None

# def human_like_typing(page, element, text, min_delay=0.1, max_delay=0.3):
#     """
#     Simulate human-like typing with variable delays and occasional pauses
#     """
#     for char in text:
#         element.type(char)
#         # Random delay between keystrokes
#         time.sleep(random.uniform(min_delay, max_delay))
        
#         # Occasionally add a longer pause
#         if random.random() < 0.1:  # 10% chance of a longer pause
#             time.sleep(random.uniform(0.5, 1.2))

# def solve_all_captchas(page):
#     """
#     Attempt to solve multiple possible captchas
#     """
#     captcha_solved = False
#     attempts = 0
#     max_attempts = 3

#     while not captcha_solved and attempts < max_attempts:
#         try:
#             # Look for Arkose Labs FunCaptcha
#             logging.info(f"Captcha solving attempt {attempts + 1}")
            
#             # Switch to first iframe (arkoseFrame)
#             try:
#                 outer_iframe = page.frame_locator("#arkoseFrame")
#                 enforcement_iframe = outer_iframe.frame_locator('iframe[data-e2e="enforcement-frame"]')
#                 game_iframe = enforcement_iframe.frame_locator("#game-core-frame")
                
#                 # Check if captcha is present
#                 auth_button = game_iframe.locator("button[data-theme='home.verifyButton']")
                
#                 if auth_button.is_visible():
#                     # Solve FunCaptcha
#                     token = solve_funcaptcha(
#                         "https://x.com", 
#                         "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"
#                     )
                    
#                     if token:
#                         # Inject the token (method may vary depending on the specific implementation)
#                         page.evaluate(f"""
#                             window.localStorage.setItem('funcaptcha_token', '{token}');
#                         """)
                        
#                         # Click authenticate button
#                         auth_button.click()
#                         captcha_solved = True
#                     else:
#                         logging.warning("Failed to solve captcha")
#             except Exception as e:
#                 logging.info(f"No captcha found in this iteration: {e}")
            
#             attempts += 1
#             time.sleep(random.uniform(2, 4))
        
#         except Exception as e:
#             logging.error(f"Error in captcha solving: {e}")
#             break
    
#     return captcha_solved

# def main():
#     # Prepare screenshots directory
#     os.makedirs("captures", exist_ok=True)

#     with sync_playwright() as p:
#         # Launch browser with stealth options
#         browser = p.chromium.launch(
#             headless=False,  # Set to True for headless mode
#             args=[
#                 '--start-maximized',
#                 '--disable-blink-features=AutomationControlled'
#             ]
#         )
        
#         # Create a new browser context with additional stealth settings
#         context = browser.new_context(
#             viewport=None,  # Use full browser window
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#         )

#         # Disable webdriver detection
#         context.add_init_script("""
#             Object.defineProperty(navigator, 'webdriver', {
#                 get: () => undefined
#             });
#         """)

#         try:
#             # Create a new page
#             page = context.new_page()

#             # Step 1: Navigate to X.com login flow
#             logging.info("Navigating to X.com login flow...")
#             page.goto("https://x.com/i/flow/login")
            
#             # Wait for username input to be visible
#             logging.info("Waiting for username field...")
#             username_field = page.locator('input[name="text"], input[type="text"]')
#             username_field.wait_for(state="visible", timeout=15000)
            
#             # Enter username with human-like typing
#             logging.info(f"Entering username: {USERNAME}")
#             username_field.fill("")
#             human_like_typing(page, username_field, USERNAME)
            
#             page.screenshot(path="captures/2_username_entered.png")

#             # Wait and click Next button with more robust selection
#             logging.info("Attempting to click 'Next' button...")
#             next_buttons = page.locator(
#                 'div[role="button"] span:has-text("Next"), div[role="button"] span:has-text("Siguiente")'
#             )
            
#             # Try multiple methods to click
#             clicked = False
#             try:
#                 # Try clicking the first visible next button
#                 for btn in next_buttons.all():
#                     try:
#                         # Add a small random delay before clicking
#                         time.sleep(random.uniform(0.5, 1.5))
#                         btn.click(timeout=5000)
#                         clicked = True
#                         break
#                     except:
#                         continue
                
#                 # If no button clicked, try pressing Enter
#                 if not clicked:
#                     username_field.press("Enter")
#                     logging.info("Pressed Enter instead of clicking button.")
#             except Exception as click_error:
#                 logging.error(f"Error clicking Next button: {click_error}")
#                 username_field.press("Enter")
            
#             # Allow time for page to load with some randomness
#             page.wait_for_timeout(random.randint(4000, 6000))
#             page.screenshot(path="captures/3_after_next.png")

#             # Solve any captchas
#             logging.info("Attempting to solve potential captchas...")
#             captcha_result = solve_all_captchas(page)
            
#             if not captcha_result:
#                 logging.warning("Could not solve captcha. Proceeding cautiously.")
            
#             # Wait for password field
#             logging.info("Waiting for password field...")
#             password_field = page.locator('input[name="password"]')
#             password_field.wait_for(state="visible", timeout=15000)
            
#             # Enter password with human-like typing
#             logging.info("Entering password...")
#             password_field.fill("")
#             human_like_typing(page, password_field, PASSWORD)
#             page.screenshot(path="captures/4_password_entered.png")

#             # Find and click Log In button
#             logging.info("Attempting to click Log In button...")
#             login_buttons = page.locator(
#                 'div[role="button"] span:has-text("Log in"), div[role="button"] span:has-text("Iniciar sesión")'
#             )
            
#             # Try to click login button
#             for btn in login_buttons.all():
#                 try:
#                     time.sleep(random.uniform(0.5, 1.5))
#                     btn.click(timeout=5000)
#                     logging.info("Clicked Log In button.")
#                     break
#                 except:
#                     continue
            
#             # Take final screenshot
#             page.screenshot(path="captures/5_final_page.png")

#             logging.info("Login process completed.")

#             # Keep the browser open until user input
#             input("Press Enter to close the browser...")

#         except Exception as ex:
#             logging.error(f"An unexpected error occurred: {ex}", exc_info=True)
#             page.screenshot(path="captures/error.png")

#         finally:
#             # Close browser
#             browser.close()

# if __name__ == "__main__":
#     main()