#!/usr/bin/env python3
"""
X.com Login Automation Script - Versión Mejorada

Características:
- Manejo de iframes anidados para FunCaptcha de Arkose Labs incluyendo desafíos multi-etapa
- Integración con 2Captcha con sondeo robusto y manejo de errores
- Verificación de tokens mediante múltiples métodos de inyección del lado del cliente
- Detección y manejo del botón "Volver a intentarlo" cuando el captcha falla
- Estructura escalable y comentarios profesionales
"""
import os
import sys
import time
import random
import logging
import json
import requests
from playwright.sync_api import sync_playwright, Locator, Page, TimeoutError as PlaywrightTimeoutError

# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- Credenciales ---
USERNAME = os.getenv("X_USERNAME", "antonioreverteandujar@gmx.com")
PASSWORD = os.getenv("X_PASSWORD", "xJHuc@EhMFNBgJd3")

# --- Credenciales para Solucionador de Captcha ---
ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY", "c20ef01b3a86bda0cf99cddef67a1477")
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "c6ac633f41e049c794aa8dc1455c7756")

# --- Constantes ---
MAX_CAPTCHA_RETRIES = 5  # Número máximo de intentos para resolver captchas
CAPTCHA_RETRY_DELAY = 2  # Segundos de espera entre intentos de captcha
SITE_URL = "https://x.com"
SITE_KEY = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"

class CaptchaSolver:
    @staticmethod
    def solve_with_2captcha(site_url: str, site_key: str, api_key: str) -> dict | None:
        """
        Usa la API de 2Captcha para resolver FunCaptcha (Arkose Labs).
        Devuelve el JSON completo del resultado en caso de éxito, o None en caso de fallo.
        """
        logging.info("Iniciando desafío 2Captcha...")
        payload = {
            "clientKey": api_key,
            "task": {
                "type": "FunCaptchaTaskProxyless",
                "websiteURL": site_url,
                "websitePublicKey": site_key,
                "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
                "userAgent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                ),
            }
        }
        try:
            create_resp = requests.post(
                "https://api.2captcha.com/createTask",
                json=payload,
                timeout=30
            )
            create_data = create_resp.json()
            if create_data.get("errorId", 1) != 0:
                logging.error(f"Error createTask 2Captcha: {create_data}")
                return None
            task_id = create_data.get("taskId")

            # Sondeo para obtener la solución hasta ~200 segundos
            for _ in range(40):
                time.sleep(5)
                result_resp = requests.post(
                    "https://api.2captcha.com/getTaskResult",
                    json={"clientKey": api_key, "taskId": task_id},
                    timeout=30
                )
                result_data = result_resp.json()
                if result_data.get("status") == "ready":
                    logging.info("2Captcha resuelto con éxito.")
                    logging.debug(json.dumps(result_data, indent=2))
                    return result_data
                logging.debug(f"Estado 2Captcha: {result_data.get('status')}")
            logging.warning("Tiempo de espera agotado para la solución de 2Captcha.")
        except Exception as e:
            logging.error(f"Excepción 2Captcha: {e}")
        return None


def verify_captcha_token(page: Page, token: str) -> bool:
    """
    Inyecta y ejecuta la verificación del lado del cliente para el token de Arkose Labs.
    Intenta múltiples métodos de inyección y devuelve True en caso de éxito.
    """
    script = f"""
    ;(function() {{
        console.log('Verificando token de Arkose...');
        try {{ if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{ window.ArkoseEnforcement.setup('{token}'); return true; }} }} catch(e) {{}}
        try {{ if (window.fc && window.fc.processToken) {{ window.fc.processToken('{token}'); return true; }} }} catch(e) {{}}
        try {{ const evt = new CustomEvent('arkose_token_received', {{ detail: {{ token: '{token}' }} }}); window.dispatchEvent(evt); return true; }} catch(e) {{}}
        return false;
    }})();
    """
    try:
        result = page.evaluate(script)
        logging.info(f"Resultado de verificación del token: {result}")
        return bool(result)
    except Exception as e:
        logging.error(f"Error de inyección del token: {e}")
        return False


def check_retry_button(page: Page) -> bool:
    """
    Verifica si el botón "Volver a intentarlo" está presente y lo hace clic si es así.
    Retorna True si se hizo clic en el botón, False en caso contrario.
    """
    logging.info("Verificando si hay botón 'Volver a intentarlo'...")
    retry_selectors = [
        "button:has-text('Volver a intentarlo')",
        "button:has-text('Try again')",
        "button:has-text('Retry')"
    ]
    
    # Comprobar en el contexto principal
    for selector in retry_selectors:
        try:
            retry_btn = page.locator(selector).first
            if retry_btn.count() > 0:
                logging.info(f"Botón '{selector}' encontrado en contexto principal, haciendo clic...")
                retry_btn.click(timeout=5000)
                page.wait_for_timeout(random.uniform(2000, 4000))
                return True
        except Exception:
            pass
    
    # Comprobar en los iframes anidados
    try:
        outer = page.frame_locator("#arkoseFrame")
        enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
        game = enforcement.frame_locator("#game-core-frame")
        
        for selector in retry_selectors:
            try:
                retry_btn = game.locator(selector).first
                if retry_btn.count() > 0:
                    logging.info(f"Botón '{selector}' encontrado en iframe de juego, haciendo clic...")
                    retry_btn.click(timeout=5000)
                    page.wait_for_timeout(random.uniform(2000, 4000))
                    return True
            except Exception:
                pass
    except Exception as e:
        logging.debug(f"Error al verificar botón de reintento en iframes: {e}")
    
    logging.info("No se encontró botón 'Volver a intentarlo'")
    return False


def is_captcha_completed(page: Page) -> bool:
    """
    Verifica si el captcha ha sido completado (ya no se muestra el iframe de Arkose).
    También verifica si aparece el campo de contraseña, lo que indicaría éxito.
    """
    # Verificar si el iframe de Arkose ya no está presente
    arkose_frame_count = page.locator("#arkoseFrame").count()
    
    # Verificar si el campo de contraseña está visible (indicador de éxito)
    try:
        password_visible = page.locator('input[name="password"]').is_visible(timeout=1000)
    except PlaywrightTimeoutError:
        password_visible = False
    
    if password_visible:
        logging.info("Campo de contraseña detectado, captcha completado con éxito.")
        return True
    
    if arkose_frame_count == 0:
        logging.info("Iframe de Arkose ya no está presente, captcha completado.")
        return True
    
    logging.debug("Captcha aún no completado.")
    return False


def solve_captcha(page: Page) -> bool:
    """
    Maneja el FunCaptcha de Arkose Labs, incluyendo reintento cuando falla.
    Continúa resolviendo hasta que todos los desafíos estén completados.
    """
    logging.info("Manejando captcha de Arkose Labs...")
    
    retry_count = 0
    
    # Bucle principal para manejar múltiples intentos de captcha
    while retry_count < MAX_CAPTCHA_RETRIES:
        if is_captcha_completed(page):
            logging.info("Captcha completado exitosamente.")
            return True
        
        # Verificar si necesitamos hacer clic en "Volver a intentarlo"
        if check_retry_button(page):
            logging.info("Se hizo clic en 'Volver a intentarlo', reintentando captcha...")
            retry_count += 1
            continue
        
        # Esperar para que los iframes carguen completamente
        page.wait_for_timeout(random.uniform(2000, 4000))
        
        # Preparar los selectores de iframe
        outer = page.frame_locator("#arkoseFrame")
        enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
        game = enforcement.frame_locator("#game-core-frame")
        
        # Solicitar solución de captcha a 2Captcha
        result = CaptchaSolver.solve_with_2captcha(SITE_URL, SITE_KEY, TWOCAPTCHA_KEY)
        if not result or not result.get("solution", {}).get("token"):
            logging.error("No se pudo obtener token de captcha.")
            retry_count += 1
            time.sleep(CAPTCHA_RETRY_DELAY)
            continue
        
        token = result["solution"]["token"]
        logging.info(f"Token extraído: {token[:20]}...")
        
        # Verificar el token en la página
        if not verify_captcha_token(page, token):
            logging.error("Verificación de token falló.")
            retry_count += 1
            time.sleep(CAPTCHA_RETRY_DELAY)
            continue
        
        # Intentar hacer clic en 'Enviar'
        clicked = False
        
        # Intento 1: Botón en contexto principal
        try:
            btn = page.locator("button:has-text('Enviar'), button:has-text('Submit')").first
            if btn.count() > 0:
                btn.click(timeout=5000)
                clicked = True
                logging.info("Clic en 'Enviar' en contexto principal.")
            else:
                logging.debug("Botón 'Enviar' no encontrado en contexto principal")
        except Exception as e:
            logging.debug(f"Error al hacer clic en contexto principal: {e}")
        
        # Intento 2: Botón dentro del iframe de juego
        if not clicked:
            try:
                btn_iframe = game.locator("button:has-text('Enviar'), button:has-text('Submit')").first
                if btn_iframe.count() > 0:
                    btn_iframe.click(timeout=5000)
                    clicked = True
                    logging.info("Clic en 'Enviar' dentro del iframe anidado.")
                else:
                    logging.debug("Botón 'Enviar' no encontrado en iframe de juego")
            except Exception as e:
                logging.debug(f"Error al hacer clic en iframe anidado: {e}")
        
        # Si no pudimos hacer clic en ningún botón, incrementar el contador de reintentos
        if not clicked:
            logging.error("No se pudo hacer clic en el botón de envío del captcha.")
            retry_count += 1
            time.sleep(CAPTCHA_RETRY_DELAY)
            continue
        
        # Esperar brevemente después del clic para ver si el captcha fue aceptado
        page.wait_for_timeout(random.uniform(3000, 5000))
        
        # Verificar si hemos completado todos los desafíos
        if is_captcha_completed(page):
            logging.info("Captcha completado exitosamente después del envío.")
            return True
        
        # Verificar si necesitamos hacer clic en "Volver a intentarlo"
        if check_retry_button(page):
            logging.info("Captcha rechazado. Haciendo clic en 'Volver a intentarlo'...")
            retry_count += 1
            continue
        
        # Si llegamos aquí, puede que necesitemos resolver otra etapa del captcha
        logging.info("Continuando con el siguiente paso del captcha...")
    
    logging.error(f"No se pudo resolver el captcha después de {MAX_CAPTCHA_RETRIES} intentos.")
    return False


def human_like_typing(element: Locator, text: str, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
    """
    Simula escritura realista variando los retrasos entre pulsaciones de teclas.
    """
    for ch in text:
        element.type(ch)
        time.sleep(random.uniform(min_delay, max_delay))
        
        # Ocasionalmente añadir una pausa más larga (como un humano pensando)
        if random.random() < 0.1:  # 10% de probabilidad
            time.sleep(random.uniform(0.5, 1.0))


def main():
    os.makedirs("captures", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = context.new_page()

        try:
            logging.info("Navegando a la página de inicio de sesión...")
            page.goto("https://x.com/i/flow/login", timeout=30000)

            logging.info("Esperando al campo de nombre de usuario...")
            username = page.locator('input[name="text"]')
            username.wait_for(state="visible", timeout=15000)
            username.fill("")
            human_like_typing(username, USERNAME)
            page.screenshot(path="captures/username.png")

            logging.info("Enviando nombre de usuario...")
            next_btns = page.locator(
                "div[role='button'] span:has-text('Next'), "
                "div[role='button'] span:has-text('Siguiente')"
            )
            if next_btns.count() > 0:
                next_btns.first.click()
            else:
                username.press("Enter")
            page.wait_for_timeout(random.uniform(3000, 5000))
            page.screenshot(path="captures/after_username.png")

            # Verificar si necesitamos autenticarnos con captcha
            if page.locator("#arkoseFrame").count() > 0:
                logging.info("Iframe de Arkose detectado, preparando para resolver captcha...")
                
                # Intentar hacer clic en 'Autentificar' si es necesario
                try:
                    outer_auth = page.frame_locator("#arkoseFrame")
                    enforce_auth = outer_auth.frame_locator("iframe[data-e2e='enforcement-frame']")
                    game_auth = enforce_auth.frame_locator("#game-core-frame")
                    auth_btn = game_auth.locator("button[data-theme='home.verifyButton']")
                    
                    if auth_btn.count() > 0:
                        logging.info("Haciendo clic en botón 'Autentificar'...")
                        auth_btn.first.click()
                        page.wait_for_timeout(random.uniform(2000, 4000))
                    else:
                        logging.info("No se encontró botón 'Autentificar', posiblemente ya estamos en el desafío")
                except Exception as e:
                    logging.warning(f"Error al hacer clic en 'Autentificar': {e}")
                
                page.screenshot(path="captures/before_captcha.png")
                
                # Resolver captcha con manejo de reintentos
                if not solve_captcha(page):
                    logging.error("El manejo del captcha falló, abortando inicio de sesión.")
                    page.screenshot(path="captures/captcha_failed.png")
                    sys.exit(1)
                
                page.screenshot(path="captures/after_captcha.png")
            else:
                logging.info("No se detectó iframe de Arkose, continuando con el flujo normal")

            logging.info("Esperando al campo de contraseña...")
            pwd = page.locator('input[name="password"]')
            pwd.wait_for(state="visible", timeout=15000)
            pwd.fill("")
            human_like_typing(pwd, PASSWORD)
            page.screenshot(path="captures/password.png")

            logging.info("Enviando contraseña...")
            login_btns = page.locator(
                "div[role='button'] span:has-text('Log in'), "
                "div[role='button'] span:has-text('Iniciar sesión')"
            )
            if login_btns.count() > 0:
                login_btns.first.click()
            else:
                pwd.press("Enter")
            page.wait_for_timeout(random.uniform(5000, 7000))
            page.screenshot(path="captures/final.png")

            logging.info("Inicio de sesión completado con éxito.")
            input("Presiona Enter para cerrar...")

        except Exception as e:
            logging.error(f"Error inesperado: {e}", exc_info=True)
            page.screenshot(path="captures/error.png")
        finally:
            browser.close()

if __name__ == '__main__':
    main()


# #!/usr/bin/env python3
# """
# X.com Login Automation Script - Enhanced Version

# Features:
# - Nested iframe handling for Arkose Labs FunCaptcha including multi-step challenges
# - 2Captcha integration with robust polling and error handling
# - Token verification via multiple client-side injection methods
# - Professional, English-language comments and scalable structure
# """
# import os
# import sys
# import time
# import random
# import logging
# import json
# import requests
# from playwright.sync_api import sync_playwright, Locator, Page

# # --- Logging configuration ---
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # --- Credentials ---
# USERNAME = os.getenv("X_USERNAME", "antonioreverteandujar@gmx.com")
# PASSWORD = os.getenv("X_PASSWORD", "xJHuc@EhMFNBgJd3")

# # --- Captcha Solver Credentials ---
# ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY", "c20ef01b3a86bda0cf99cddef67a1477")
# TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "c6ac633f41e049c794aa8dc1455c7756")

# class CaptchaSolver:
#     @staticmethod
#     def solve_with_2captcha(site_url: str, site_key: str, api_key: str) -> dict | None:
#         """
#         Use 2Captcha API to solve FunCaptcha (Arkose Labs).
#         Returns the full result JSON on success, or None on failure.
#         """
#         logging.info("Starting 2Captcha challenge...")
#         payload = {
#             "clientKey": api_key,
#             "task": {
#                 "type": "FunCaptchaTaskProxyless",
#                 "websiteURL": site_url,
#                 "websitePublicKey": site_key,
#                 "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
#                 "userAgent": (
#                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                     "AppleWebKit/537.36 (KHTML, like Gecko) "
#                     "Chrome/115.0.0.0 Safari/537.36"
#                 ),
#             }
#         }
#         try:
#             create_resp = requests.post(
#                 "https://api.2captcha.com/createTask",
#                 json=payload,
#                 timeout=30
#             )
#             create_data = create_resp.json()
#             if create_data.get("errorId", 1) != 0:
#                 logging.error(f"2Captcha createTask error: {create_data}")
#                 return None
#             task_id = create_data.get("taskId")

#             # Poll for solution up to ~200 seconds
#             for _ in range(40):
#                 time.sleep(5)
#                 result_resp = requests.post(
#                     "https://api.2captcha.com/getTaskResult",
#                     json={"clientKey": api_key, "taskId": task_id},
#                     timeout=30
#                 )
#                 result_data = result_resp.json()
#                 if result_data.get("status") == "ready":
#                     logging.info("2Captcha solved successfully.")
#                     logging.debug(json.dumps(result_data, indent=2))
#                     return result_data
#                 logging.debug(f"2Captcha status: {result_data.get('status')}")
#             logging.warning("2Captcha solution timed out.")
#         except Exception as e:
#             logging.error(f"2Captcha exception: {e}")
#         return None


# def verify_captcha_token(page: Page, token: str) -> bool:
#     """
#     Inject and execute client-side verification for Arkose Labs token.
#     Tries multiple injection methods and returns True on success.
#     """
#     script = f"""
#     ;(function() {{
#         console.log('Verifying Arkose token...');
#         try {{ if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{ window.ArkoseEnforcement.setup('{token}'); return true; }} }} catch(e) {{}}
#         try {{ if (window.fc && window.fc.processToken) {{ window.fc.processToken('{token}'); return true; }} }} catch(e) {{}}
#         try {{ const evt = new CustomEvent('arkose_token_received', {{ detail: {{ token: '{token}' }} }}); window.dispatchEvent(evt); return true; }} catch(e) {{}}
#         return false;
#     }})();
#     """
#     try:
#         result = page.evaluate(script)
#         logging.info(f"Token verification result: {result}")
#         return bool(result)
#     except Exception as e:
#         logging.error(f"Token injection error: {e}")
#         return False


# def solve_captcha(page: Page) -> bool:
#     """
#     Handle Arkose Labs FunCaptcha until the widget iframe is gone.
#     Each iteration solves one stage by obtaining a token and clicking 'Enviar'.
#     """
#     logging.info("Handling Arkose Labs captcha...")
#     site_url = "https://x.com"
#     site_key = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"

#     # Initial wait for iframe to load
#     page.wait_for_timeout(random.uniform(2000, 4000))

#     # Loop while the captcha iframe is present
#     while page.locator("#arkoseFrame").count() > 0:
#         outer = page.frame_locator("#arkoseFrame")
#         enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
#         game = enforcement.frame_locator("#game-core-frame")

#         # Solve one stage
#         result = CaptchaSolver.solve_with_2captcha(site_url, site_key, TWOCAPTCHA_KEY)
#         if not result or not result.get("solution", {}).get("token"):
#             logging.error("Failed to obtain captcha token.")
#             return False
#         token = result["solution"]["token"]
#         logging.info(f"Extracted token: {token[:20]}...")

#         # Verify the token in the page
#         if not verify_captcha_token(page, token):
#             logging.error("Token verification failed.")
#             return False

#         # Attempt to click 'Enviar'
#         clicked = False
#         try:
#             btn = page.locator("button:has-text('Enviar')").first
#             btn.wait_for(state="visible", timeout=10000)
#             btn.click()
#             clicked = True
#             logging.info("Clicked 'Enviar' in main context.")
#         except Exception:
#             pass
#         if not clicked:
#             try:
#                 btn_iframe = game.locator("button:has-text('Enviar')").first
#                 btn_iframe.wait_for(state="visible", timeout=10000)
#                 btn_iframe.click()
#                 clicked = True
#                 logging.info("Clicked 'Enviar' inside nested iframe.")
#             except Exception as e:
#                 logging.error(f"Nested iframe click failed: {e}")
#         if not clicked:
#             logging.error("Could not click submit button for captcha.")
#             return False

#         # Small delay before next check
#         page.wait_for_timeout(random.uniform(2000, 4000))

#     logging.info("Captcha widget removed, proceeding.")
#     return True


# def human_like_typing(element: Locator, text: str, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
#     """
#     Simulates realistic typing by varying inter-keystroke delays.
#     """
#     for ch in text:
#         element.type(ch)
#         time.sleep(random.uniform(min_delay, max_delay))


# def main():
#     os.makedirs("captures", exist_ok=True)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--start-maximized',
#                 '--disable-blink-features=AutomationControlled'
#             ]
#         )
#         context = browser.new_context(
#             viewport=None,
#             user_agent=(
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/91.0.4472.124 Safari/537.36"
#             )
#         )
#         context.add_init_script(
#             "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
#         )
#         page = context.new_page()

#         try:
#             logging.info("Navigating to login page...")
#             page.goto("https://x.com/i/flow/login", timeout=30000)

#             logging.info("Waiting for username field...")
#             username = page.locator('input[name="text"]')
#             username.wait_for(state="visible", timeout=15000)
#             username.fill("")
#             human_like_typing(username, USERNAME)
#             page.screenshot(path="captures/username.png")

#             logging.info("Submitting username...")
#             next_btns = page.locator(
#                 "div[role='button'] span:has-text('Next'), "
#                 "div[role='button'] span:has-text('Siguiente')"
#             )
#             if next_btns.count() > 0:
#                 next_btns.first.click()
#             else:
#                 username.press("Enter")
#             page.wait_for_timeout(random.uniform(3000, 5000))

#             logging.info("Clicking 'Autentificar' button...")
#             outer_auth = page.frame_locator("#arkoseFrame")
#             enforce_auth = outer_auth.frame_locator("iframe[data-e2e='enforcement-frame']")
#             game_auth = enforce_auth.frame_locator("#game-core-frame")
#             game_auth.locator("button[data-theme='home.verifyButton']").first.click()
#             page.wait_for_timeout(random.uniform(2000, 4000))

#             if not solve_captcha(page):
#                 logging.error("Captcha handling failed, aborting login.")
#                 sys.exit(1)

#             logging.info("Waiting for password field...")
#             pwd = page.locator('input[name="password"]')
#             pwd.wait_for(state="visible", timeout=15000)
#             pwd.fill("")
#             human_like_typing(pwd, PASSWORD)
#             page.screenshot(path="captures/password.png")

#             logging.info("Submitting password...")
#             login_btns = page.locator(
#                 "div[role='button'] span:has-text('Log in'), "
#                 "div[role='button'] span:has-text('Iniciar sesión')"
#             )
#             if login_btns.count() > 0:
#                 login_btns.first.click()
#             else:
#                 pwd.press("Enter")
#             page.wait_for_timeout(random.uniform(5000, 7000))
#             page.screenshot(path="captures/final.png")

#             logging.info("Login completed successfully.")
#             input("Press Enter to close...")

#         except Exception as e:
#             logging.error(f"Unexpected error: {e}", exc_info=True)
#             page.screenshot(path="captures/error.png")
#         finally:
#             browser.close()

# if __name__ == '__main__':
#     main()



# #!/usr/bin/env python3
# """
# X.com Login Automation Script - Enhanced Version

# Features:
# - Nested iframe handling for Arkose Labs FunCaptcha including multi-step challenges
# - 2Captcha integration with robust polling and error handling
# - Token verification via multiple client-side injection methods
# - Professional, English-language comments and scalable structure
# """
# import os
# import sys
# import time
# import random
# import logging
# import json
# import requests
# import re
# from playwright.sync_api import sync_playwright, Locator, Page

# # --- Logging configuration ---
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # --- Credentials ---
# USERNAME = os.getenv("X_USERNAME", "antonioreverteandujar@gmx.com")
# PASSWORD = os.getenv("X_PASSWORD", "xJHuc@EhMFNBgJd3")

# # --- Captcha Solver Credentials ---
# ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY", "c20ef01b3a86bda0cf99cddef67a1477")
# TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "c6ac633f41e049c794aa8dc1455c7756")

# class CaptchaSolver:
#     @staticmethod
#     def solve_with_2captcha(site_url: str, site_key: str, api_key: str) -> dict | None:
#         """
#         Use 2Captcha API to solve FunCaptcha (Arkose Labs).
#         Returns the full result JSON on success, or None on failure.
#         """
#         logging.info("Starting 2Captcha challenge...")
#         payload = {
#             "clientKey": api_key,
#             "task": {
#                 "type": "FunCaptchaTaskProxyless",
#                 "websiteURL": site_url,
#                 "websitePublicKey": site_key,
#                 "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
#                 "userAgent": (
#                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                     "AppleWebKit/537.36 (KHTML, like Gecko) "
#                     "Chrome/115.0.0.0 Safari/537.36"
#                 ),
#             }
#         }
#         try:
#             create_resp = requests.post(
#                 "https://api.2captcha.com/createTask",
#                 json=payload,
#                 timeout=30
#             )
#             create_data = create_resp.json()
#             if create_data.get("errorId", 1) != 0:
#                 logging.error(f"2Captcha createTask error: {create_data}")
#                 return None
#             task_id = create_data.get("taskId")

#             # Poll for solution up to ~200 seconds
#             for _ in range(40):
#                 time.sleep(5)
#                 result_resp = requests.post(
#                     "https://api.2captcha.com/getTaskResult",
#                     json={"clientKey": api_key, "taskId": task_id},
#                     timeout=30
#                 )
#                 result_data = result_resp.json()
#                 if result_data.get("status") == "ready":
#                     logging.info("2Captcha solved successfully.")
#                     logging.debug(json.dumps(result_data, indent=2))
#                     return result_data
#                 logging.debug(f"2Captcha status: {result_data.get('status')}")
#             logging.warning("2Captcha solution timed out.")
#         except Exception as e:
#             logging.error(f"2Captcha exception: {e}")
#         return None


# def verify_captcha_token(page: Page, token: str) -> bool:
#     """
#     Inject and execute client-side verification for Arkose Labs token.
#     Tries multiple injection methods and returns True on success.
#     """
#     script = f"""
#     ;(function() {{
#         console.log('Verifying Arkose token...');
#         try {{ if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{ window.ArkoseEnforcement.setup('{token}'); return true; }} }} catch(e) {{}}
#         try {{ if (window.fc && window.fc.processToken) {{ window.fc.processToken('{token}'); return true; }} }} catch(e) {{}}
#         try {{ const evt = new CustomEvent('arkose_token_received', {{ detail: {{ token: '{token}' }} }}); window.dispatchEvent(evt); return true; }} catch(e) {{}}
#         return false;
#     }})();
#     """
#     try:
#         result = page.evaluate(script)
#         logging.info(f"Token verification result: {result}")
#         return bool(result)
#     except Exception as e:
#         logging.error(f"Token injection error: {e}")
#         return False


# def solve_captcha(page: Page) -> bool:
#     """
#     Handle nested Arkose Labs FunCaptcha, including multi-step (e.g., 1 de 3).
#     Continues solving until all stages are completed.
#     """
#     logging.info("Handling Arkose Labs captcha...")
#     site_url = "https://x.com"
#     site_key = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"

#     # Allow iframes to load
#     page.wait_for_timeout(random.uniform(2000, 4000))
#     outer = page.frame_locator("#arkoseFrame")
#     enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
#     game = enforcement.frame_locator("#game-core-frame")

#     # Loop through all captcha stages
#     while True:
#         # Solve via 2Captcha
#         result = CaptchaSolver.solve_with_2captcha(site_url, site_key, TWOCAPTCHA_KEY)
#         if not result or not result.get("solution", {}).get("token"):
#             logging.warning("No captcha solution obtained.")
#             return False
#         token = result["solution"]["token"]
#         logging.info(f"Extracted token: {token[:20]}...)")

#         # Verify token client-side
#         if not verify_captcha_token(page, token):
#             logging.warning("Client-side token verification failed.")
#             return False

#         # Attempt to click 'Enviar'
#         clicked = False
#         try:
#             btn = page.locator("button:has-text('Enviar')").first
#             btn.wait_for(state="visible", timeout=10000)
#             btn.click()
#             clicked = True
#             logging.info("Clicked 'Enviar' in main context.")
#         except Exception as e:
#             logging.warning(f"Main click failed: {e}")
#         if not clicked:
#             try:
#                 btn_iframe = game.locator("button:has-text('Enviar')").first
#                 btn_iframe.wait_for(state="visible", timeout=10000)
#                 btn_iframe.click()
#                 clicked = True
#                 logging.info("Clicked 'Enviar' inside nested iframe.")
#             except Exception as e:
#                 logging.error(f"Iframe click failed: {e}")
#         if not clicked:
#             logging.error("Captcha submit failed in all contexts.")
#             return False

#         # Allow for stage transition
#         page.wait_for_timeout(random.uniform(2000, 4000))

#         # Check for multi-stage indicator
#         try:
#             text = game.locator("h2").first.inner_text(timeout=5000)
#             match = re.search(r"\((\d+)\s+de\s+(\d+)\)", text)
#             if match:
#                 current, total = int(match.group(1)), int(match.group(2))
#                 logging.info(f"Captcha stage {current} of {total}.")
#                 if current < total:
#                     continue  # Solve next stage
#         except Exception:
#             pass

#         # All stages complete
#         return True


# def human_like_typing(element: Locator, text: str, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
#     """
#     Simulates realistic typing by varying inter-keystroke delays.
#     """
#     for ch in text:
#         element.type(ch)
#         time.sleep(random.uniform(min_delay, max_delay))


# def main():
#     os.makedirs("captures", exist_ok=True)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--start-maximized',
#                 '--disable-blink-features=AutomationControlled'
#             ]
#         )
#         context = browser.new_context(
#             viewport=None,
#             user_agent=(
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/91.0.4472.124 Safari/537.36"
#             )
#         )
#         context.add_init_script(
#             "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
#         )
#         page = context.new_page()

#         try:
#             # Navigate to login flow
#             logging.info("Navigating to login page...")
#             page.goto("https://x.com/i/flow/login", timeout=30000)

#             # Username entry
#             logging.info("Waiting for username field...")
#             username = page.locator('input[name=\"text\"]')
#             username.wait_for(state="visible", timeout=15000)
#             username.fill("")
#             human_like_typing(username, USERNAME)
#             page.screenshot(path="captures/username.png")

#             # Click Next / Siguiente
#             logging.info("Submitting username...")
#             next_btns = page.locator(
#                 "div[role='button'] span:has-text('Next'), "
#                 "div[role='button'] span:has-text('Siguiente')"
#             )
#             if next_btns.count() > 0:
#                 next_btns.first.click()
#             else:
#                 username.press("Enter")
#             page.wait_for_timeout(random.uniform(3000, 5000))

#             # Click 'Autentificar'
#             logging.info("Clicking 'Autentificar' button...")
#             outer_auth = page.frame_locator("#arkoseFrame")
#             enforce_auth = outer_auth.frame_locator("iframe[data-e2e='enforcement-frame']")
#             game_auth = enforce_auth.frame_locator("#game-core-frame")
#             game_auth.locator("button[data-theme='home.verifyButton']").first.click()
#             page.wait_for_timeout(random.uniform(2000, 4000))

#             # Solve captcha (multi-stage)
#             if not solve_captcha(page):
#                 logging.error("Captcha handling failed, aborting login.")
#                 sys.exit(1)

#             # Password entry
#             logging.info("Waiting for password field...")
#             pwd = page.locator('input[name=\"password\"]')
#             pwd.wait_for(state="visible", timeout=15000)
#             pwd.fill("")
#             human_like_typing(pwd, PASSWORD)
#             page.screenshot(path="captures/password.png")

#             # Click Log In / Iniciar sesión
#             logging.info("Submitting password...")
#             login_btns = page.locator(
#                 "div[role='button'] span:has-text('Log in'), "
#                 "div[role='button'] span:has-text('Iniciar sesión')"
#             )
#             if login_btns.count() > 0:
#                 login_btns.first.click()
#             else:
#                 pwd.press("Enter")
#             page.wait_for_timeout(random.uniform(5000, 7000))
#             page.screenshot(path="captures/final.png")

#             logging.info("Login completed successfully.")

#             # Pause before closing
#             input("Press Enter to close...")

#         except Exception as e:
#             logging.error(f"Unexpected error: {e}", exc_info=True)
#             page.screenshot(path="captures/error.png")
#         finally:
#             browser.close()

# if __name__ == '__main__':
#     main()



##############################################################
## OK 1 CAPTCHA
##############################################################


# #!/usr/bin/env python3
# """
# X.com Login Automation Script - Enhanced Version

# Features:
# - Nested iframe handling for Arkose Labs FunCaptcha
# - 2Captcha integration with robust polling and error handling
# - Token verification via multiple client-side injection methods
# - Professional, English-language comments and scalable structure
# """
# import os
# import sys
# import time
# import random
# import logging
# import json
# import requests
# from playwright.sync_api import sync_playwright, Locator, Page

# # --- Logging configuration ---
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# # --- Credentials ---
# USERNAME = os.getenv("X_USERNAME", "antonioreverteandujar@gmx.com")
# PASSWORD = os.getenv("X_PASSWORD", "xJHuc@EhMFNBgJd3")

# # --- Captcha Solver Credentials ---
# ANTICAPTCHA_KEY = os.getenv("ANTICAPTCHA_KEY", "c20ef01b3a86bda0cf99cddef67a1477")
# TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "c6ac633f41e049c794aa8dc1455c7756")

# class CaptchaSolver:
#     @staticmethod
#     def solve_with_2captcha(site_url: str, site_key: str, api_key: str) -> dict | None:
#         """
#         Use 2Captcha API to solve FunCaptcha (Arkose Labs).
#         Returns the full result JSON on success, or None on failure.
#         """
#         logging.info("Starting 2Captcha challenge...")
#         payload = {
#             "clientKey": api_key,
#             "task": {
#                 "type": "FunCaptchaTaskProxyless",
#                 "websiteURL": site_url,
#                 "websitePublicKey": site_key,
#                 "funcaptchaApiJSSubdomain": "client-api.arkoselabs.com",
#                 "userAgent": (
#                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                     "AppleWebKit/537.36 (KHTML, like Gecko) "
#                     "Chrome/115.0.0.0 Safari/537.36"
#                 ),
#             }
#         }
#         try:
#             create_resp = requests.post(
#                 "https://api.2captcha.com/createTask",
#                 json=payload,
#                 timeout=30
#             )
#             create_data = create_resp.json()
#             if create_data.get("errorId", 1) != 0:
#                 logging.error(f"2Captcha createTask error: {create_data}")
#                 return None
#             task_id = create_data.get("taskId")

#             # Poll for solution up to ~200 seconds
#             for _ in range(40):
#                 time.sleep(5)
#                 result_resp = requests.post(
#                     "https://api.2captcha.com/getTaskResult",
#                     json={"clientKey": api_key, "taskId": task_id},
#                     timeout=30
#                 )
#                 result_data = result_resp.json()
#                 if result_data.get("status") == "ready":
#                     logging.info("2Captcha solved successfully.")
#                     logging.debug(json.dumps(result_data, indent=2))
#                     return result_data
#                 logging.debug(f"2Captcha status: {result_data.get('status')}")
#             logging.warning("2Captcha solution timed out.")
#         except Exception as e:
#             logging.error(f"2Captcha exception: {e}")
#         return None


# def verify_captcha_token(page: Page, token: str) -> bool:
#     """
#     Inject and execute client-side verification for Arkose Labs token.
#     Tries multiple injection methods and returns True on success.
#     """
#     script = f"""
#     ;(function() {{
#         console.log('Verifying Arkose token...');
#         try {{ if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{ window.ArkoseEnforcement.setup('{token}'); return true; }} }} catch(e) {{}}
#         try {{ if (window.fc && window.fc.processToken) {{ window.fc.processToken('{token}'); return true; }} }} catch(e) {{}}
#         try {{ const evt = new CustomEvent('arkose_token_received', {{ detail: {{ token: '{token}' }} }}); window.dispatchEvent(evt); return true; }} catch(e) {{}}
#         return false;
#     }})();
#     """
#     try:
#         result = page.evaluate(script)
#         logging.info(f"Token verification result: {result}")
#         return bool(result)
#     except Exception as e:
#         logging.error(f"Token injection error: {e}")
#         return False


# def solve_captcha(page: Page) -> bool:
#     """
#     Navigate nested iframes, request a token via 2Captcha, verify it,
#     and click the "Enviar" button in main context or fallback inside iframe.
#     """
#     logging.info("Handling Arkose Labs captcha...")
#     site_url = "https://x.com"
#     site_key = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"

#     page.wait_for_timeout(random.uniform(2000, 4000))  # let iframes load
#     outer = page.frame_locator("#arkoseFrame")
#     enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
#     game = enforcement.frame_locator("#game-core-frame")

#     result = CaptchaSolver.solve_with_2captcha(site_url, site_key, TWOCAPTCHA_KEY)
#     if not result:
#         logging.warning("No captcha solution obtained.")
#         return False

#     token = result['solution']['token']
#     logging.info(f"Extracted token: {token[:20]}...")

#     if not verify_captcha_token(page, token):
#         logging.warning("Client-side token verification failed.")
#         return False

#     # Main context click
#     try:
#         btn = page.locator("button:has-text('Enviar')").first
#         btn.wait_for(state="visible", timeout=10000)
#         btn.click()
#         logging.info("Clicked 'Enviar' in main context.")
#         page.wait_for_timeout(random.uniform(2000, 4000))
#         return True
#     except Exception as e:
#         logging.warning(f"Main click failed: {e}")

#     # Fallback inside iframe
#     try:
#         btn_iframe = game.locator("button:has-text('Enviar')").first
#         btn_iframe.wait_for(state="visible", timeout=10000)
#         btn_iframe.click()
#         logging.info("Clicked 'Enviar' inside nested iframe.")
#         page.wait_for_timeout(random.uniform(2000, 4000))
#         return True
#     except Exception as e:
#         logging.error(f"Iframe click failed: {e}")

#     logging.error("Captcha submit failed in all contexts.")
#     return False


# def human_like_typing(element: Locator, text: str, min_delay: float = 0.1, max_delay: float = 0.3) -> None:
#     """
#     Simulates realistic typing by varying inter-keystroke delays.
#     """
#     for ch in text:
#         element.type(ch)
#         time.sleep(random.uniform(min_delay, max_delay))


# def main():
#     os.makedirs("captures", exist_ok=True)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--start-maximized',
#                 '--disable-blink-features=AutomationControlled'
#             ]
#         )
#         context = browser.new_context(
#             viewport=None,
#             user_agent=(
#                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                 "AppleWebKit/537.36 (KHTML, like Gecko) "
#                 "Chrome/91.0.4472.124 Safari/537.36"
#             )
#         )
#         context.add_init_script(
#             "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
#         )
#         page = context.new_page()

#         try:
#             # Navigate to login flow
#             logging.info("Navigating to login page...")
#             page.goto("https://x.com/i/flow/login", timeout=30000)

#             # Username entry
#             logging.info("Waiting for username field...")
#             username = page.locator('input[name="text"]')
#             username.wait_for(state="visible", timeout=15000)
#             username.fill("")
#             human_like_typing(username, USERNAME)
#             page.screenshot(path="captures/username.png")

#             # Click Next / Siguiente
#             logging.info("Submitting username...")
#             next_btns = page.locator(
#                 "div[role='button'] span:has-text('Next'), "
#                 "div[role='button'] span:has-text('Siguiente')"
#             )
#             if next_btns.count() > 0:
#                 next_btns.first.click()
#             else:
#                 username.press("Enter")
#             page.wait_for_timeout(random.uniform(3000, 5000))

#             # Click 'Autentificar'
#             logging.info("Clicking 'Autentificar' button...")
#             outer_auth = page.frame_locator("#arkoseFrame")
#             enforce_auth = outer_auth.frame_locator("iframe[data-e2e='enforcement-frame']")
#             game_auth = enforce_auth.frame_locator("#game-core-frame")
#             game_auth.locator("button[data-theme='home.verifyButton']").first.click()
#             page.wait_for_timeout(random.uniform(2000, 4000))

#             # Solve captcha
#             if not solve_captcha(page):
#                 logging.error("Captcha handling failed, aborting login.")
#                 sys.exit(1)

#             # Password entry
#             logging.info("Waiting for password field...")
#             pwd = page.locator('input[name="password"]')
#             pwd.wait_for(state="visible", timeout=15000)
#             pwd.fill("")
#             human_like_typing(pwd, PASSWORD)
#             page.screenshot(path="captures/password.png")

#             # Click Log In / Iniciar sesión
#             logging.info("Submitting password...")
#             login_btns = page.locator(
#                 "div[role='button'] span:has-text('Log in'), "
#                 "div[role='button'] span:has-text('Iniciar sesión')"
#             )
#             if login_btns.count() > 0:
#                 login_btns.first.click()
#             else:
#                 pwd.press("Enter")
#             page.wait_for_timeout(random.uniform(5000, 7000))
#             page.screenshot(path="captures/final.png")

#             logging.info("Login completed successfully.")

#             # Pause before closing
#             input("Press Enter to close...")

#         except Exception as e:
#             logging.error(f"Unexpected error: {e}", exc_info=True)
#             page.screenshot(path="captures/error.png")
#         finally:
#             browser.close()

# if __name__ == '__main__':
#     main()




# #!/usr/bin/env python3
# """
# X.com Login Automation Script

# This script automates the X.com login flow with:
# - Multiple captcha solving strategies
# - Robust captcha token verification
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

# def verify_captcha_token(page, solution_token):
#     """
#     Comprehensive captcha token verification
#     """
#     try:
#         # Extensive token verification methods
#         verification_script = f"""
#         // Function to simulate Arkose Labs token verification
#         function verifyCaptchaToken() {{
#             console.log('Starting captcha token verification');
            
#             // Method 1: Direct Arkose verification
#             if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{
#                 try {{
#                     console.log('Attempting Arkose Enforcement verification');
#                     window.ArkoseEnforcement.setup('{solution_token}');
#                     return true;
#                 }} catch (error) {{
#                     console.error('Arkose Enforcement verification failed:', error);
#                 }}
#             }}

#             // Method 2: Manual token processing
#             if (window.fc) {{
#                 try {{
#                     console.log('Attempting manual FC token processing');
#                     window.fc.processToken('{solution_token}');
#                     return true;
#                 }} catch (error) {{
#                     console.error('Manual FC token processing failed:', error);
#                 }}
#             }}

#             // Method 3: Trigger Arkose callback directly
#             try {{
#                 console.log('Attempting direct Arkose callback');
#                 const arkoseEvent = new CustomEvent('arkose_token_received', {{
#                     detail: {{ token: '{solution_token}' }}
#                 }});
#                 window.dispatchEvent(arkoseEvent);
#                 return true;
#             }} catch (error) {{
#                 console.error('Direct Arkose callback failed:', error);
#             }}

#             console.log('All captcha verification methods failed');
#             return false;
#         }}

#         // Execute verification and return result
#         verifyCaptchaToken();
#         """
        
#         # Execute verification script
#         result = page.evaluate(verification_script)
        
#         logging.info(f"Captcha token verification result: {result}")
#         return result
    
#     except Exception as e:
#         logging.error(f"Captcha token verification error: {e}")
#         return False

# def solve_captcha(page):
#     """
#     Solve Arkose Labs Captcha with multiple providers
#     """
#     captcha_solvers = [
#         CaptchaSolver.solve_twocaptcha,  # Try 2Captcha first
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
                    
#                     # Extract token
#                     token = captcha_solution['solution']['token']
                    
#                     # Verify token
#                     verification_result = verify_captcha_token(page, token)
                    
#                     if verification_result:
#                         # Try to find and click Submit/Enviar button using page-level locator
#                         submit_buttons = page.locator('button.sc-nkuzb1-0.yuVdl, button:has-text("Submit"), button:has-text("Enviar")')
                        
#                         # Wait for the submit button to be visible
#                         try:
#                             submit_buttons.first().wait_for(state="visible", timeout=10000)
                            
#                             # Click the submit button
#                             submit_buttons.first().click()
#                             logging.info("Clicked Submit/Enviar button")
                            
#                             # Additional wait to allow processing
#                             page.wait_for_timeout(random.randint(2000, 4000))
#                             return True
#                         except Exception as btn_error:
#                             logging.warning(f"Could not find or click Submit button: {btn_error}")
                            
#                             # Fallback: try to click within the game iframe
#                             try:
#                                 game_submit = game_iframe.locator('button.sc-nkuzb1-0.yuVdl, button:has-text("Submit"), button:has-text("Enviar")')
#                                 game_submit.first().click()
#                                 logging.info("Clicked Submit button in game iframe")
#                                 page.wait_for_timeout(random.randint(2000, 4000))
#                                 return True
#                             except Exception as iframe_btn_error:
#                                 logging.warning(f"Could not click Submit button in game iframe: {iframe_btn_error}")
#                                 continue
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