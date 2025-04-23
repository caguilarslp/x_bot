#!/usr/bin/env python3
"""
X.com Login Automation Script - Versión con Inyección Directa de Token

Características:
- Llamadas directas a la API de 2Captcha siguiendo la documentación oficial
- Inyección del token en los elementos específicos de la página (FunCaptcha-Token y verification-token)
- Forzado del idioma inglés para mejorar la resolución de captchas
- Manejo mejorado de captchas visuales de coordenadas
"""
import os
import sys
import time
import random
import logging
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

# --- Credenciales para Solucionadores de Captcha ---
TWOCAPTCHA_KEY = os.getenv("TWOCAPTCHA_KEY", "c6ac633f41e049c794aa8dc1455c7756")

# --- Constantes ---
MAX_CAPTCHA_RETRIES = 10  # Número máximo de intentos para resolver captchas
SITE_URL = "https://x.com"  # URL base
SITE_KEY = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"  # Clave pública de Arkose Labs
SURL = "https://client-api.arkoselabs.com"  # URL de servicio para Arkose Labs
POLLING_INTERVAL = 5  # Intervalo de sondeo en segundos
MAX_POLLING_TIMEOUT = 180  # Tiempo máximo de espera para la solución

class DirectCaptchaSolver:
    """
    Clase para manejar la resolución de captchas directamente con la API de 2Captcha
    """
    @staticmethod
    def solve_funcaptcha(api_key, public_key, page_url, surl=None, lang="en", previous_id=None):
        """
        Resuelve FunCaptcha usando la API directa de 2Captcha
        """
        # Si tenemos un ID anterior, reportar como incorrecto
        if previous_id:
            try:
                report_url = f"https://2captcha.com/res.php?key={api_key}&action=reportbad&id={previous_id}"
                requests.get(report_url)
                logging.info(f"Captcha incorrecto reportado: {previous_id}")
            except Exception as e:
                logging.error(f"Error al reportar captcha incorrecto: {e}")
        
        # Construir la URL de la solicitud
        request_url = "https://2captcha.com/in.php"
        
        # Parámetros para la solicitud
        params = {
            'key': api_key,
            'method': 'funcaptcha',
            'publickey': public_key,
            'pageurl': page_url,
            'json': 1,  # Solicitar respuesta en formato JSON
            'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'data[lang]': lang  # Especificar idioma para los trabajadores
        }
        
        # Añadir surl si está disponible
        if surl:
            params['surl'] = surl
        
        try:
            # Enviar solicitud para crear la tarea
            logging.info("Enviando solicitud a 2Captcha...")
            response = requests.post(request_url, params=params)
            
            # Verificar si la respuesta es válida
            if not response.ok:
                logging.error(f"Error en la respuesta HTTP: {response.status_code}")
                return None
            
            # Analizar la respuesta JSON
            json_response = response.json()
            
            if json_response.get('status') != 1:
                logging.error(f"Error en la solicitud a 2Captcha: {json_response.get('request')}")
                return None
            
            # Obtener el ID de la tarea
            task_id = json_response.get('request')
            logging.info(f"Tarea creada con ID: {task_id}")
            
            # Sondear para obtener el resultado
            start_time = time.time()
            while time.time() - start_time < MAX_POLLING_TIMEOUT:
                # Esperar antes de solicitar el resultado
                time.sleep(POLLING_INTERVAL)
                
                # Solicitar el resultado
                get_url = "https://2captcha.com/res.php"
                get_params = {
                    'key': api_key,
                    'action': 'get',
                    'id': task_id,
                    'json': 1
                }
                
                get_response = requests.get(get_url, params=get_params)
                
                if not get_response.ok:
                    logging.error(f"Error al obtener resultado: {get_response.status_code}")
                    continue
                
                get_json = get_response.json()
                
                # Verificar si la tarea está lista
                if get_json.get('status') == 1:
                    token = get_json.get('request')
                    logging.info(f"Captcha resuelto. Token recibido.")
                    return {
                        'success': True,
                        'captchaId': task_id,
                        'token': token
                    }
                
                # Si la tarea aún no está lista, continuar sondeando
                if get_json.get('request') == 'CAPCHA_NOT_READY':
                    logging.debug("Captcha aún no está listo...")
                    continue
                
                # Si hay algún otro error, salir del bucle
                logging.error(f"Error al obtener resultado: {get_json.get('request')}")
                return None
            
            # Si llegamos aquí, se agotó el tiempo de espera
            logging.error("Tiempo de espera agotado para obtener resultado del captcha")
            return None
            
        except Exception as e:
            logging.error(f"Error al resolver captcha: {e}")
            return None
    
    @staticmethod
    def report_good(api_key, captcha_id):
        """
        Reporta un captcha como resuelto correctamente
        """
        try:
            report_url = f"https://2captcha.com/res.php?key={api_key}&action=reportgood&id={captcha_id}"
            requests.get(report_url)
            logging.info(f"Captcha correcto reportado: {captcha_id}")
            return True
        except Exception as e:
            logging.error(f"Error al reportar captcha correcto: {e}")
            return False


def inject_captcha_token(page: Page, token: str) -> bool:
    """
    Inyecta el token del captcha en los elementos específicos de la página
    """
    script = f"""
    (function() {{
        console.log('Inyectando token de captcha en elementos de la página...');
        let injected = false;
        
        // Método 1: Inyectar en los elementos específicos
        try {{
            // Inyectar en elemento FunCaptcha-Token
            const fcTokenElement = document.querySelector('#FunCaptcha-Token');
            if (fcTokenElement) {{
                fcTokenElement.value = '{token}';
                console.log('Token inyectado en #FunCaptcha-Token');
                injected = true;
            }}
            
            // Inyectar en elemento verification-token
            const verificationTokenElement = document.querySelector('#verification-token');
            if (verificationTokenElement) {{
                verificationTokenElement.value = '{token}';
                console.log('Token inyectado en #verification-token');
                injected = true;
            }}
        }} catch(e) {{
            console.error('Error al inyectar en elementos específicos:', e);
        }}
        
        // Método 2: Inyección a través de Arkose
        if (!injected) {{
            try {{ 
                if (window.ArkoseEnforcement && window.ArkoseEnforcement.setup) {{ 
                    window.ArkoseEnforcement.setup('{token}'); 
                    console.log('Token inyectado vía ArkoseEnforcement.setup');
                    injected = true;
                }} 
            }} catch(e) {{
                console.error('Error en ArkoseEnforcement.setup:', e);
            }}
        }}
        
        // Método 3: Procesamiento manual de token
        if (!injected) {{
            try {{ 
                if (window.fc && window.fc.processToken) {{ 
                    window.fc.processToken('{token}'); 
                    console.log('Token inyectado vía fc.processToken');
                    injected = true;
                }} 
            }} catch(e) {{
                console.error('Error en fc.processToken:', e);
            }}
        }}
        
        // Método 4: Evento personalizado
        if (!injected) {{
            try {{ 
                const evt = new CustomEvent('arkose_token_received', {{ 
                    detail: {{ token: '{token}' }} 
                }}); 
                window.dispatchEvent(evt); 
                console.log('Token inyectado vía evento personalizado');
                injected = true;
            }} catch(e) {{
                console.error('Error en evento personalizado:', e);
            }}
        }}
        
        return injected;
    }})();
    """
    try:
        result = page.evaluate(script)
        logging.info(f"Resultado de inyección del token: {result}")
        return bool(result)
    except Exception as e:
        logging.error(f"Error de inyección del token: {e}")
        return False


def detect_captcha_text(page: Page) -> str:
    """
    Detecta el texto del captcha para proporcionar información de depuración
    """
    outer = page.frame_locator("#arkoseFrame")
    enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
    game = enforcement.frame_locator("#game-core-frame")
    
    try:
        # Intentar obtener el texto descriptivo del desafío
        challenge_text = game.locator("p.sc-1io4bok-0, .text").inner_text()
        logging.info(f"Texto del desafío detectado: {challenge_text}")
        
        # Tomar screenshot del captcha para ayudar en la depuración
        try:
            page.screenshot(path="captures/current_captcha.png")
        except Exception:
            pass
            
        return challenge_text
    except Exception as e:
        logging.debug(f"Error al detectar texto del captcha: {e}")
    
    return ""


def check_retry_button(page: Page) -> bool:
    """
    Verifica si el botón "Try again" está presente y lo hace clic si es así.
    Retorna True si se hizo clic en el botón, False en caso contrario.
    """
    logging.info("Verificando si hay botón 'Try again'...")
    retry_selectors = [
        "button:has-text('Try again')",  # Texto explícito
        "button.sc-nkuzb1-0.dJlpAa.button",  # Selector de clase completo
        "button.dJlpAa"  # Selector de clase parcial
    ]
    
    # Tomar screenshot para depuración
    try:
        page.screenshot(path="captures/before_retry_check.png")
    except Exception:
        pass
    
    # Comprobar en el contexto principal
    for selector in retry_selectors:
        try:
            retry_btn = page.locator(selector).first
            if retry_btn.count() > 0 and retry_btn.is_visible(timeout=3000):
                logging.info(f"Botón '{selector}' encontrado en contexto principal, haciendo clic...")
                retry_btn.click(timeout=5000)
                page.wait_for_timeout(random.uniform(2000, 4000))
                return True
        except Exception as e:
            logging.debug(f"Error al verificar/hacer clic en botón '{selector}': {e}")
    
    # Comprobar en los iframes anidados
    try:
        outer = page.frame_locator("#arkoseFrame")
        enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
        game = enforcement.frame_locator("#game-core-frame")
        
        for selector in retry_selectors:
            try:
                retry_btn = game.locator(selector).first
                if retry_btn.count() > 0 and retry_btn.is_visible(timeout=3000):
                    logging.info(f"Botón '{selector}' encontrado en iframe de juego, haciendo clic...")
                    retry_btn.click(timeout=5000)
                    page.wait_for_timeout(random.uniform(2000, 4000))
                    return True
            except Exception as e:
                logging.debug(f"Error al verificar/hacer clic en botón '{selector}' en iframe: {e}")
    except Exception as e:
        logging.debug(f"Error al acceder a iframes: {e}")
    
    logging.info("No se encontró botón 'Try again'")
    return False


def is_captcha_completed(page: Page) -> bool:
    """
    Verifica múltiples indicadores para determinar si el captcha ha sido completado exitosamente.
    """
    # 1. Verificar si el campo de contraseña está visible (éxito definitivo)
    try:
        if page.locator('input[name="password"]').is_visible(timeout=2000):
            logging.info("Campo de contraseña detectado, captcha completado con éxito.")
            return True
    except Exception:
        pass
    
    # 2. Verificar si el iframe de Arkose ya no está presente
    try:
        if page.locator("#arkoseFrame").count() == 0:
            logging.info("Iframe de Arkose ya no está presente, captcha completado.")
            return True
    except Exception:
        pass
    
    # 3. Verificar si estamos en la pantalla de contraseña verificando elementos únicos
    try:
        if page.locator('div:has-text("Enter your password")').count() > 0:
            logging.info("Texto 'Enter your password' detectado, captcha completado.")
            return True
    except Exception:
        pass
    
    logging.debug("Captcha aún no completado.")
    return False


def solve_captcha(page: Page) -> bool:
    """
    Maneja el FunCaptcha de Arkose Labs utilizando llamadas directas a la API de 2Captcha.
    Incluye inyección directa del token en los elementos específicos de la página.
    """
    logging.info("Manejando captcha de Arkose Labs...")
    
    retry_count = 0
    last_captcha_id = None
    
    # Bucle principal para manejar múltiples intentos de captcha
    while retry_count < MAX_CAPTCHA_RETRIES:
        # Verificar primero si el captcha ya está completado
        if is_captcha_completed(page):
            logging.info("Captcha completado exitosamente.")
            return True
        
        # Verificar si necesitamos hacer clic en "Try again"
        if check_retry_button(page):
            logging.info("Se hizo clic en 'Try again', reintentando captcha...")
            retry_count += 1
            continue
        
        # Esperar para que los iframes carguen completamente
        page.wait_for_timeout(random.uniform(2000, 4000))
        
        # Intentar detectar texto del captcha para depuración
        captcha_text = detect_captcha_text(page)
        
        # Preparar los selectores de iframe
        outer = page.frame_locator("#arkoseFrame")
        enforcement = outer.frame_locator("iframe[data-e2e='enforcement-frame']")
        game = enforcement.frame_locator("#game-core-frame")
        
        # Resolver captcha con llamada directa a la API de 2Captcha
        try:
            logging.info("Enviando solicitud a 2Captcha para resolver FunCaptcha...")
            result = DirectCaptchaSolver.solve_funcaptcha(
                api_key=TWOCAPTCHA_KEY,
                public_key=SITE_KEY,
                page_url=SITE_URL,
                surl=SURL,
                lang="en",
                previous_id=last_captcha_id
            )
            
            if not result:
                logging.error("No se pudo obtener solución de 2Captcha.")
                retry_count += 1
                page.wait_for_timeout(random.uniform(3000, 5000))
                continue
                
            # Extraer token y ID para posible reporte
            token = result.get("token")
            last_captcha_id = result.get("captchaId")
            
            if not token:
                logging.error("No se encontró token en la respuesta de 2Captcha.")
                retry_count += 1
                page.wait_for_timeout(random.uniform(3000, 5000))
                continue
                
            logging.info(f"Token recibido: {token[:50]}...")
            
            # Inyectar el token en los elementos específicos de la página
            if not inject_captcha_token(page, token):
                logging.error("Inyección de token falló.")
                retry_count += 1
                page.wait_for_timeout(random.uniform(3000, 5000))
                continue
            
            # Intentar hacer clic en 'Submit'
            clicked = False
            submit_selectors = [
                "button:has-text('Submit')",  # Texto explícito
                "button.sc-nkuzb1-0.yuVdl",  # Selector de clase completo
                "button.yuVdl"  # Selector de clase parcial
            ]
            
            # Intento 1: Botones en contexto principal
            for selector in submit_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible(timeout=3000):
                        btn.click(timeout=5000)
                        clicked = True
                        logging.info(f"Clic en '{selector}' en contexto principal.")
                        break
                    else:
                        logging.debug(f"Botón '{selector}' no encontrado o no visible en contexto principal")
                except Exception as e:
                    logging.debug(f"Error al hacer clic en '{selector}' en contexto principal: {e}")
            
            # Intento 2: Botones dentro del iframe de juego
            if not clicked:
                for selector in submit_selectors:
                    try:
                        btn_iframe = game.locator(selector).first
                        if btn_iframe.count() > 0 and btn_iframe.is_visible(timeout=3000):
                            btn_iframe.click(timeout=5000)
                            clicked = True
                            logging.info(f"Clic en '{selector}' dentro del iframe anidado.")
                            break
                        else:
                            logging.debug(f"Botón '{selector}' no encontrado o no visible en iframe de juego")
                    except Exception as e:
                        logging.debug(f"Error al hacer clic en '{selector}' en iframe anidado: {e}")
            
            # Si no pudimos hacer clic en ningún botón, incrementar el contador de fallos
            if not clicked:
                logging.error("No se pudo hacer clic en el botón de envío del captcha.")
                retry_count += 1
                page.wait_for_timeout(random.uniform(3000, 5000))
                continue
            
            # Esperar a que se procese la solución
            page.wait_for_timeout(random.uniform(4000, 6000))
            
            # Verificar si hemos completado todos los desafíos
            if is_captcha_completed(page):
                logging.info("Captcha completado exitosamente después del envío.")
                # Reportar captcha correcto
                DirectCaptchaSolver.report_good(TWOCAPTCHA_KEY, last_captcha_id)
                return True
            
            # Verificar si necesitamos hacer clic en "Try again"
            if check_retry_button(page):
                logging.info("Captcha rechazado. Haciendo clic en 'Try again'...")
                retry_count += 1
                continue
            
            # Si llegamos aquí, puede que necesitemos resolver otra etapa del captcha
            logging.info("Continuando con el siguiente paso del captcha...")
            page.wait_for_timeout(random.uniform(3000, 5000))
            
        except Exception as e:
            logging.error(f"Error durante la resolución del captcha: {e}")
            retry_count += 1
            page.wait_for_timeout(random.uniform(3000, 5000))
    
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
            ),
            locale="en-US"  # Forzar idioma inglés en el navegador
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = context.new_page()

        try:
            logging.info("Navegando a la página de inicio de sesión en inglés...")
            # Forzar idioma inglés en la URL
            page.goto("https://x.com/i/flow/login?lang=en", timeout=30000)
            page.screenshot(path="captures/1_login_page.png")

            logging.info("Esperando al campo de nombre de usuario...")
            username = page.locator('input[name="text"]')
            username.wait_for(state="visible", timeout=15000)
            username.fill("")
            human_like_typing(username, USERNAME)
            page.screenshot(path="captures/2_username.png")

            logging.info("Enviando nombre de usuario...")
            next_btns = page.locator(
                "div[role='button'] span:has-text('Next')"
            )
            if next_btns.count() > 0:
                next_btns.first.click()
            else:
                username.press("Enter")
            page.wait_for_timeout(random.uniform(3000, 5000))
            page.screenshot(path="captures/3_after_username.png")

            # Verificar si necesitamos autenticarnos con captcha
            if page.locator("#arkoseFrame").count() > 0:
                logging.info("Iframe de Arkose detectado, preparando para resolver captcha...")
                page.screenshot(path="captures/4_arkose_detected.png")
                
                # Intentar hacer clic en 'Verify' o un botón similar si es necesario
                try:
                    outer_auth = page.frame_locator("#arkoseFrame")
                    enforce_auth = outer_auth.frame_locator("iframe[data-e2e='enforcement-frame']")
                    game_auth = enforce_auth.frame_locator("#game-core-frame")
                    
                    # Buscar y hacer clic en varios posibles botones de autenticación
                    auth_buttons = [
                        "button[data-theme='home.verifyButton']",
                        "button:has-text('Verify')",
                        "button.sc-nkuzb1-0.yuVdl"
                    ]
                    
                    clicked = False
                    for selector in auth_buttons:
                        try:
                            auth_btn = game_auth.locator(selector).first
                            if auth_btn.count() > 0 and auth_btn.is_visible(timeout=3000):
                                logging.info(f"Haciendo clic en botón '{selector}'...")
                                auth_btn.click(timeout=5000)
                                clicked = True
                                page.wait_for_timeout(random.uniform(2000, 4000))
                                break
                        except Exception as e:
                            logging.debug(f"Error al hacer clic en '{selector}': {e}")
                    
                    if not clicked:
                        logging.info("No se encontró botón de autenticación, posiblemente ya estamos en el desafío")
                except Exception as e:
                    logging.warning(f"Error al interactuar con el iframe de Arkose: {e}")
                
                page.screenshot(path="captures/5_before_captcha.png")
                
                # Resolver captcha con manejo de reintentos
                if not solve_captcha(page):
                    logging.error("El manejo del captcha falló, abortando inicio de sesión.")
                    page.screenshot(path="captures/captcha_failed.png")
                    sys.exit(1)
                
                page.screenshot(path="captures/6_after_captcha.png")
            else:
                logging.info("No se detectó iframe de Arkose, continuando con el flujo normal")

            logging.info("Esperando al campo de contraseña...")
            pwd = page.locator('input[name="password"]')
            pwd.wait_for(state="visible", timeout=15000)
            pwd.fill("")
            human_like_typing(pwd, PASSWORD)
            page.screenshot(path="captures/7_password.png")

            logging.info("Enviando contraseña...")
            login_btns = page.locator(
                "div[role='button'] span:has-text('Log in')"
            )
            if login_btns.count() > 0:
                login_btns.first.click()
            else:
                pwd.press("Enter")
            page.wait_for_timeout(random.uniform(5000, 7000))
            page.screenshot(path="captures/8_final.png")

            logging.info("Inicio de sesión completado con éxito.")
            input("Presiona Enter para cerrar...")

        except Exception as e:
            logging.error(f"Error inesperado: {e}", exc_info=True)
            page.screenshot(path="captures/error.png")
        finally:
            browser.close()

if __name__ == '__main__':
    main()