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

