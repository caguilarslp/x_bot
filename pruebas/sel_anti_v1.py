#!/usr/bin/env python3
"""
sel_click_authenticate.py

This script automates the X.com login flow and clicks the "Autentificar"
button inside nested Arkose iframes. All comments are in English and
the structure is professional and scalable.
"""

import os
import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ——— Logging configuration ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ——— Credentials ———
USERNAME = "antonioreverteandujar@gmx.com"

def main():
    # Prepare screenshots directory
    os.makedirs("captures", exist_ok=True)

    # Chrome options for stealth
    chrome_opts = Options()
    chrome_opts.add_argument("--start-maximized")
    chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
    chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_opts.add_experimental_option("useAutomationExtension", False)

    # Initialize WebDriver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )

    # Hide the webdriver navigator flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
    )

    try:
        # Step 1: Navigate to X.com login flow
        logging.info("Navigating to X.com login flow...")
        driver.get("https://x.com/i/flow/login")
        time.sleep(3)
        driver.save_screenshot("captures/1_login_page.png")

        # Step 2: Enter username
        logging.info("Waiting for username field...")
        username_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="text"], input[type="text"]'))
        )
        username_field.clear()
        username_field.send_keys(USERNAME)
        driver.save_screenshot("captures/2_username_entered.png")

        # Step 3: Click "Next" or press Enter
        try:
            next_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[contains(text(),'Next') or contains(text(),'Siguiente')]"
                ))
            )
            next_btn.click()
            logging.info("Clicked 'Next' button.")
        except:
            logging.info("'Next' button not found; sending Enter key.")
            username_field.send_keys("\n")

        # Allow time for Arkose iframe to load
        time.sleep(3)
        driver.save_screenshot("captures/3_after_next.png")

        # Step 4: Switch into first iframe (arkoseFrame)
        logging.info("Locating outer Arkose iframe (arkoseFrame)...")
        outer_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "arkoseFrame"))
        )
        driver.switch_to.frame(outer_iframe)
        driver.save_screenshot("captures/4_inside_arkoseFrame.png")

        # Step 5: Switch into second iframe (enforcement-frame)
        logging.info("Locating enforcement-frame iframe...")
        enforcement_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[data-e2e="enforcement-frame"]'))
        )
        driver.switch_to.frame(enforcement_iframe)
        driver.save_screenshot("captures/5_inside_enforcement_frame.png")

        # Step 6: Switch into third iframe (game-core-frame)
        logging.info("Locating game-core-frame iframe...")
        game_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "game-core-frame"))
        )
        driver.switch_to.frame(game_iframe)
        driver.save_screenshot("captures/6_inside_game_core_frame.png")

        # Step 7: Locate and click the "Autentificar" button
        logging.info("Searching for 'Autentificar' button...")
        auth_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-theme='home.verifyButton']"))
        )
        auth_button.click()
        logging.info("Clicked 'Autentificar' button.")
        driver.save_screenshot("captures/7_after_click_authenticate.png")

        # Optionally switch back to the top-level context
        driver.switch_to.default_content()

        logging.info("Script completed successfully.")

    except Exception as ex:
        logging.error(f"An unexpected error occurred: {ex}", exc_info=True)
        driver.save_screenshot("captures/error.png")

    finally:
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()






# ok captura los tres niveles de iframe
#########################################################################################

# #!/usr/bin/env python3
# """
# iframe_extractor.py

# A Selenium-based script that:
#   1. Navigates to X.com login flow
#   2. Enters username and clicks Next
#   3. Waits for the Arkose login iframe to load
#   4. Recursively extracts the HTML, src, id, and name of every iframe
#      (including nested ones)
#   5. Saves each iframe’s HTML to disk under frames/{frame_path}.html
# """

# import os
# import time
# import logging

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from webdriver_manager.chrome import ChromeDriverManager

# # ——— Logging configuration ———
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # ——— Credentials ———
# USERNAME = "antonioreverteandujar@gmx.com"

# def save_iframes(driver, frame_prefix="frame", parent_path=""):
#     """
#     Recursively find all <iframe> elements in the current browsing context,
#     extract their HTML, and save to {frames_dir}/{parent_path}{frame_prefix}_{idx}.html.
#     Then switch into each iframe and recurse.
#     """
#     frames = driver.find_elements(By.TAG_NAME, "iframe")
#     for idx, frame in enumerate(frames):
#         # Build unique identifier for this iframe
#         frame_path = f"{parent_path}{frame_prefix}_{idx}"
#         src = frame.get_attribute("src") or ""
#         fid = frame.get_attribute("id") or ""
#         fname = frame.get_attribute("name") or ""

#         logging.info(
#             "Found iframe %s: src=%s, id=%s, name=%s",
#             frame_path, src, fid, fname
#         )

#         # Switch into iframe context
#         driver.switch_to.frame(frame)

#         # Extract outer HTML of document
#         html = driver.execute_script("return document.documentElement.outerHTML;")

#         # Ensure output directory exists
#         os.makedirs("frames", exist_ok=True)
#         out_file = os.path.join("frames", f"{frame_path}.html")

#         # Write HTML to file
#         with open(out_file, "w", encoding="utf-8") as f:
#             f.write(html)
#         logging.info("Saved iframe HTML to %s", out_file)

#         # Recurse into nested iframes
#         save_iframes(driver, frame_prefix, parent_path=frame_path + "_")

#         # Return to parent frame
#         driver.switch_to.parent_frame()

# def main():
#     # Chrome stealth options
#     chrome_opts = Options()
#     chrome_opts.add_argument("--start-maximized")
#     chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
#     chrome_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
#     chrome_opts.add_experimental_option("useAutomationExtension", False)

#     # Initialize WebDriver
#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=chrome_opts
#     )

#     # Hide the webdriver flag
#     driver.execute_cdp_cmd(
#         "Page.addScriptToEvaluateOnNewDocument",
#         {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
#     )

#     try:
#         # Step 1: Navigate to the login flow
#         logging.info("Opening X.com login flow...")
#         driver.get("https://x.com/i/flow/login")

#         # Step 2: Wait for and enter username
#         username_input = WebDriverWait(driver, 15).until(
#             EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="text"], input[type="text"]'))
#         )
#         username_input.clear()
#         username_input.send_keys(USERNAME)
#         driver.save_screenshot("captures/username_entered.png")

#         # Step 3: Click Next (or press Enter if missing)
#         try:
#             next_btn = WebDriverWait(driver, 5).until(
#                 EC.element_to_be_clickable((By.XPATH,
#                     "//*[contains(text(),'Next') or contains(text(),'Siguiente')]"
#                 ))
#             )
#             next_btn.click()
#             logging.info("Clicked Next.")
#         except:
#             logging.warning("Next button not found; sending Enter key.")
#             username_input.send_keys("\n")

#         # Allow time for Arkose iframe to load
#         time.sleep(3)

#         # Step 4: Extract all iframes recursively
#         logging.info("Beginning recursive iframe extraction...")
#         save_iframes(driver)

#         logging.info("Iframe extraction complete.")

#     except Exception as e:
#         logging.error("An error occurred: %s", e, exc_info=True)

#     finally:
#         driver.quit()

# if __name__ == "__main__":
#     main()
