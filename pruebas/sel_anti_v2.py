#!/usr/bin/env python3
"""
sel_anti_captcha.py

Automates the X.com login flow with Arkose FunCaptcha solving via AntiCaptcha,
then submits the password to complete login. Professional, scalable structure.
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
from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless
from webdriver_manager.chrome import ChromeDriverManager

# ——— Logging configuration ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ——— Credentials & API keys ———
USERNAME       = "antonioreverteandujar@gmx.com"
PASSWORD       = "xJHuc@EhMFNBgJd3"
ANTICAPTCHA_KEY = "c20ef01b3a86bda0cf99cddef67a1477"
WEBSITE_URL     = "https://x.com"
FUN_CAPTCHA_KEY = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"

def solve_funcaptcha():
    """
    Uses AntiCaptcha to solve Arkose FunCaptcha and returns the session token.
    """
    solver = funcaptchaProxyless()
    solver.set_verbose(1)
    solver.set_key(ANTICAPTCHA_KEY)
    solver.set_website_url(WEBSITE_URL)
    solver.set_website_key(FUN_CAPTCHA_KEY)

    token = solver.solve_and_return_solution()
    if token == 0:
        logging.error("AntiCaptcha error: %s", solver.error_code)
        return None
    logging.info("AntiCaptcha returned token: %s", token)
    return token

def main():
    # Prepare directories
    os.makedirs("captures", exist_ok=True)

    # Chrome stealth options
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
        # Step 1: Navigate to login flow
        logging.info("Navigating to X.com login flow…")
        driver.get(f"{WEBSITE_URL}/i/flow/login")
        time.sleep(2)
        driver.save_screenshot("captures/1_login_page.png")

        # Step 2: Enter username
        logging.info("Entering username…")
        username_input = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="text"], input[type="text"]'))
        )
        username_input.clear()
        username_input.send_keys(USERNAME)
        driver.save_screenshot("captures/2_username_entered.png")

        # Step 3: Click "Next" or send Enter
        try:
            next_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//*[contains(text(),'Next') or contains(text(),'Siguiente')]"
                ))
            )
            next_btn.click()
            logging.info("Clicked 'Next' button.")
        except Exception:
            logging.info("'Next' not found; submitting via Enter.")
            username_input.send_keys("\n")

        time.sleep(3)
        driver.save_screenshot("captures/3_after_next.png")

        # Step 4: Switch into Arkose outer iframe
        logging.info("Switching to arkoseFrame…")
        outer_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "arkoseFrame"))
        )
        driver.switch_to.frame(outer_iframe)
        driver.save_screenshot("captures/4_inside_arkoseFrame.png")

        # Step 5: Switch into enforcement-frame
        logging.info("Switching to enforcement-frame…")
        enforcement_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[data-e2e="enforcement-frame"]'))
        )
        driver.switch_to.frame(enforcement_iframe)
        driver.save_screenshot("captures/5_inside_enforcement_frame.png")

        # Step 6: Switch into game-core-frame
        logging.info("Switching to game-core-frame…")
        game_iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "game-core-frame"))
        )
        driver.switch_to.frame(game_iframe)
        driver.save_screenshot("captures/6_inside_game_core_frame.png")

        # Step 7: Solve FunCaptcha via AntiCaptcha
        logging.info("Solving FunCaptcha via AntiCaptcha…")
        token = solve_funcaptcha()
        if not token:
            raise RuntimeError("Failed to obtain FunCaptcha token")

        # Step 8: Inject the token into the hidden input
        logging.info("Injecting token into FunCaptcha-Token field…")
        driver.execute_script(
            "document.getElementById('FunCaptcha-Token').value = arguments[0];",
            token
        )
        # Optional: dispatch change event
        driver.execute_script(
            "document.getElementById('FunCaptcha-Token').dispatchEvent(new Event('change'));"
        )
        driver.save_screenshot("captures/7_token_injected.png")

        # Step 9: Return to top-level context
        driver.switch_to.default_content()
        time.sleep(2)

        # Step 10: Wait for password field to appear
        logging.info("Waiting for password field…")
        password_input = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="password"], input[type="password"]'))
        )
        password_input.clear()
        password_input.send_keys(PASSWORD)
        driver.save_screenshot("captures/8_password_entered.png")

        # Step 11: Click "Iniciar sesión"
        logging.info("Clicking 'Iniciar sesión' button…")
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//span[contains(text(),'Iniciar sesión')]/ancestor::div[@role='button']"
            ))
        )
        login_btn.click()
        driver.save_screenshot("captures/9_after_login_click.png")

        logging.info("Login sequence complete.")

    except Exception as e:
        logging.error("An unexpected error occurred: %s", e, exc_info=True)
        driver.save_screenshot("captures/error.png")

    finally:
        input("Press Enter to close the browser…")
        driver.quit()

if __name__ == "__main__":
    main()
