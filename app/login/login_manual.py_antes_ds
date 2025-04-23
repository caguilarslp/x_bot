import os
import json
import time
import random
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("x_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Función para cargar las cuentas desde el archivo JSON
def load_accounts():
    accounts_file = Path('login_accounts.json')
    if not accounts_file.exists():
        logger.info("No se encontró el archivo login_accounts.json. Creando uno de ejemplo...")
        example_accounts = {
            "accounts": [
                {
                    "username": "antonioreverteandujar@gmx.com",
                    "password": "xJHuc@EhMFNBgJd3",
                    "description": "Cuenta principal para automatización"
                },
                {
                    "username": "martin.rodriguez87@outlook.com",
                    "password": "P@ssw0rd2025!Secure",
                    "description": "Cuenta de testeo para engagement"
                },
                {
                    "username": "social_media_test_42@protonmail.com",
                    "password": "Kj8$bQ9pLm2!zXcV",
                    "description": "Cuenta para pruebas de API"
                },
                {
                    "username": "laura.tech.tester@gmail.com",
                    "password": "T3ch#T3ster2025!",
                    "description": "Cuenta para analítica"
                }
            ]
        }
        with open(accounts_file, 'w', encoding='utf-8') as f:
            json.dump(example_accounts, f, indent=2)
        
        logger.info(f"Se ha creado el archivo {accounts_file} con cuentas de ejemplo.")
        logger.info("Por favor, edita este archivo con tus cuentas reales antes de continuar.")
        return example_accounts["accounts"]
    
    try:
        with open(accounts_file, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
            return accounts_data.get("accounts", [])
    except json.JSONDecodeError:
        logger.error("Error: El archivo login_accounts.json no tiene un formato JSON válido.")
        return []
    except Exception as e:
        logger.error(f"Error al cargar el archivo de cuentas: {e}")
        return []

# Función para seleccionar una cuenta de la lista
def select_account(accounts):
    if not accounts:
        logger.error("No hay cuentas disponibles en el archivo login_accounts.json")
        return None, None
    
    print("\n=== Cuentas Disponibles ===")
    for i, account in enumerate(accounts):
        username = account.get("username", "Sin nombre de usuario")
        description = account.get("description", "")
        print(f"{i+1}. {username} - {description}")
    
    while True:
        try:
            selection = input("\nSelecciona el número de la cuenta que quieres usar (o 'q' para salir): ")
            if selection.lower() == 'q':
                return None, None
            
            index = int(selection) - 1
            if 0 <= index < len(accounts):
                selected_account = accounts[index]
                return selected_account.get("username"), selected_account.get("password")
            else:
                print(f"Error: Por favor, selecciona un número entre 1 y {len(accounts)}")
        except ValueError:
            print("Error: Por favor, introduce un número válido")

# Función para agregar retraso de aspecto humano (tiempo variable)
async def human_delay(min_ms=500, max_ms=2000):
    delay = random.uniform(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)

# Función para simular escritura humana con velocidad variable
async def type_human_like(page, selector, text):
    try:
        await page.focus(selector)
        
        # Borrar cualquier texto existente primero
        await page.fill(selector, '')
        await human_delay(200, 600)
        
        # Escribir cada carácter con retraso variable
        for char in text:
            await page.type(selector, char, delay=50 + random.randint(50, 150))
            
            # Ocasionalmente hacer una pausa como lo haría un humano
            if random.random() < 0.2:
                await human_delay(200, 1000)
    except Exception as e:
        logger.error(f"Error al escribir texto: {e}")
        # Intentar una alternativa si el método normal falla
        try:
            await page.fill(selector, text)
        except Exception:
            logger.error("No se pudo escribir el texto.")

# Función para esperar a un selector con posibilidad de continuar si no aparece
async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
    try:
        await page.wait_for_selector(selector, state='visible', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        if message:
            logger.info(message)
        return False

# Función para hacer clic con manejo de interceptores
async def click_safely(page, selector, timeout=30000, force=False):
    try:
        # Primero intentamos el método estándar
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            if element:
                if force:
                    await element.click(force=True)
                else:
                    await element.click()
                return True
        except Exception as e:
            logger.debug(f"Primer intento de clic fallido: {e}")
            
        # Si falla, intentamos con JavaScript
        try:
            await page.evaluate(f'''() => {{
                const elements = document.querySelectorAll('{selector}');
                if (elements.length > 0) {{
                    elements[0].click();
                    return true;
                }}
                return false;
            }}''')
            await human_delay(500, 1000)  # Esperar para que el clic surta efecto
            return True
        except Exception as e:
            logger.debug(f"Clic por JavaScript fallido: {e}")
            
        # Si todo falla, intentamos con opciones más agresivas
        try:
            await page.click(selector, force=True, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Clic forzado fallido: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error al intentar hacer clic en {selector}: {e}")
        return False

# Función para analizar la página con BeautifulSoup y encontrar elementos específicos
async def analyze_page_with_bs4(page, element_type="unknown"):
    """
    Analiza la estructura de la página con BeautifulSoup para encontrar 
    elementos específicos según el tipo solicitado.
    
    Args:
        page: Página de Playwright
        element_type: Tipo de elemento a buscar (login, username, password, button)
    
    Returns:
        dict: Información encontrada relevante al elemento solicitado
    """
    # Obtener el HTML completo de la página
    html_content = await page.content()
    
    # Analizar con BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    results = {"found": False, "selectors": []}
    
    if element_type == "username_field":
        # Buscar campos de entrada que puedan ser de usuario
        for input_tag in soup.find_all('input'):
            # Buscar atributos comunes para campos de usuario
            input_type = input_tag.get('type', '')
            input_name = input_tag.get('name', '')
            input_id = input_tag.get('id', '')
            input_placeholder = input_tag.get('placeholder', '')
            input_autocomplete = input_tag.get('autocomplete', '')
            input_class = ' '.join(input_tag.get('class', []))
            
            # Verificar si parece un campo de usuario
            is_username_field = (
                (input_type in ['text', 'email', 'tel']) or
                (input_name in ['text', 'username', 'email', 'user', 'screen_name']) or
                (input_id and ('user' in input_id.lower() or 'email' in input_id.lower())) or
                (input_placeholder and ('user' in input_placeholder.lower() or 'email' in input_placeholder.lower() or 'phone' in input_placeholder.lower())) or
                (input_autocomplete in ['username', 'email']) or
                (input_class and ('username' in input_class.lower() or 'user' in input_class.lower()))
            )
            
            if is_username_field:
                # Encontrar el selector CSS más preciso
                selector = f"input"
                if input_id:
                    selector = f"input#{input_id}"
                elif input_name:
                    selector = f"input[name='{input_name}']"
                else:
                    # Construir un selector basado en la combinación de atributos
                    attributes = []
                    if input_type:
                        attributes.append(f"type='{input_type}'")
                    if input_autocomplete:
                        attributes.append(f"autocomplete='{input_autocomplete}'")
                    if input_placeholder:
                        attributes.append(f"placeholder='{input_placeholder}'")
                    
                    if attributes:
                        selector = f"input[{']['.join(attributes)}]"
                
                results["selectors"].append(selector)
                results["found"] = True
    
    elif element_type == "password_field":
        # Buscar campos de contraseña
        for input_tag in soup.find_all('input', attrs={'type': 'password'}):
            input_id = input_tag.get('id', '')
            input_name = input_tag.get('name', '')
            
            # Crear selector
            if input_id:
                selector = f"input#{input_id}"
            elif input_name:
                selector = f"input[name='{input_name}']"
            else:
                selector = "input[type='password']"
            
            results["selectors"].append(selector)
            results["found"] = True
    
    
    elif element_type == "login_button":
        # Buscar botones de inicio de sesión
        login_text_variations = ['log in', 'login', 'sign in', 'signin', 'iniciar sesión', 'ingresar', 'acceder']
        
        # Buscar botones por texto
        for button in soup.find_all(['button', 'div', 'a']):
            button_text = button.get_text(strip=True).lower()
            button_role = button.get('role', '')
            button_type = button.get('type', '')
            button_class = ' '.join(button.get('class', []))
            button_id = button.get('id', '')
            button_testid = button.get('data-testid', '')
            
            is_login_button = (
                any(text in button_text for text in login_text_variations) or
                (button_id and any(text in button_id.lower() for text in login_text_variations)) or
                (button_type == 'submit' and any(text in button_class.lower() for text in login_text_variations)) or
                (button_testid and 'login' in button_testid.lower())
            )
            
            if is_login_button:
                # Encontrar el selector para este botón
                selector = None
                if button_testid:
                    selector = f"[data-testid='{button_testid}']"
                elif button_id:
                    selector = f"#{button_id}"
                elif button.name == 'button':
                    selector = f"button:has-text('{button_text}')"
                elif button_role == 'button':
                    selector = f"[role='button']:has-text('{button_text}')"
                
                if selector:
                    results["selectors"].append(selector)
                    results["found"] = True
    
    
    elif element_type == "next_button":
        # Buscar botones de "siguiente" o "next"
        next_text_variations = ['next', 'siguiente', 'continuar', 'continue']
        
        # Buscar botones por texto
        for button in soup.find_all(['button', 'div', 'a']):
            button_text = button.get_text(strip=True).lower()
            button_role = button.get('role', '')
            button_type = button.get('type', '')
            button_id = button.get('id', '')
            
            is_next_button = (
                any(text in button_text for text in next_text_variations) or
                (button_id and any(text in button_id.lower() for text in next_text_variations))
            )
            
            if is_next_button:
                # Encontrar el selector para este botón
                selector = None
                if button_id:
                    selector = f"#{button_id}"
                elif button.name == 'button':
                    if button_role == 'button':
                        # Selector más específico para los botones de X.com
                        selector = f"button[role='button'][type='button']:has-text('{button_text}')"
                    else:
                        selector = f"button:has-text('{button_text}')"
                elif button_role == 'button':
                    selector = f"[role='button']:has-text('{button_text}')"
                
                if selector:
                    results["selectors"].append(selector)
                    results["found"] = True
        
        # Añadir selectores específicos para el botón Next de X.com basado en el ejemplo proporcionado
        specific_next_selectors = [
            "button[role='button'][type='button'] div:has-text('Next')",
            "button[role='button'] span:has-text('Next')",
            "button[role='button'] span span:has-text('Next')"
        ]
        
        for selector in specific_next_selectors:
            results["selectors"].append(selector)
            results["found"] = True
    
    elif element_type == "is_logged_in":
        # Verificar si parece que estamos logueados
        # Buscar elementos que aparecen post-login
        nav_elements = [
            soup.find('a', attrs={'data-testid': 'AppTabBar_Home_Link'}),
            soup.find('a', attrs={'data-testid': 'AppTabBar_Profile_Link'}),
            soup.find('a', attrs={'aria-label': 'Profile'}),
            soup.find('div', attrs={'aria-label': 'Home timeline'})
        ]
        
        # Si encontramos algún elemento de navegación post-login
        results["found"] = any(elem is not None for elem in nav_elements)
        
        # Además, intentar encontrar el nombre de usuario
        profile_info = {}
        account_switcher = soup.find(attrs={'data-testid': 'SideNav_AccountSwitcher_Button'})
        if account_switcher:
            display_name_el = account_switcher.select_one('div[dir="ltr"] span span')
            if display_name_el and display_name_el.text:
                profile_info['display_name'] = display_name_el.text.strip()
                
            handle_el = account_switcher.select_one('div[dir="ltr"][class*="r-1wvb978"] span')
            if handle_el and handle_el.text:
                profile_info['handle'] = handle_el.text.strip()
                
        results["profile_info"] = profile_info
    
    return results

# Función para detectar y manejar el captcha
async def handle_captcha(page):
    logger.info("Verificando presencia de captcha...")
    
    # Verificar si el iframe de Arkose está presente
    has_arkose_frame = await wait_for_selector_or_continue(page, "#arkoseFrame", timeout=3000)
    
    if has_arkose_frame:
        logger.info("=== CAPTCHA DETECTADO ===")
        logger.info("Se encontró el iframe de Arkose Labs.")
        
        # Intenta identificar otros elementos de captcha usando BeautifulSoup
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        captcha_elements = []
        
        # Buscar iframes que podrían contener captcha
        for iframe in soup.find_all('iframe'):
            iframe_id = iframe.get('id', '')
            iframe_src = iframe.get('src', '')
            iframe_title = iframe.get('title', '')
            
            if (
                'arkose' in iframe_id.lower() or 
                'captcha' in iframe_id.lower() or
                'arkose' in iframe_src.lower() or
                'captcha' in iframe_src.lower() or
                'captcha' in iframe_title.lower() or
                'challenge' in iframe_title.lower()
            ):
                captcha_elements.append({
                    'type': 'iframe',
                    'id': iframe_id,
                    'src': iframe_src,
                    'title': iframe_title
                })
        
        if captcha_elements:
            logger.info(f"Elementos de captcha adicionales detectados: {len(captcha_elements)}")
        
        # Tomar captura del captcha para depuración
        screenshot_dir = Path('screenshots')
        screenshot_dir.mkdir(exist_ok=True)
        captcha_screenshot = screenshot_dir / f'captcha_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        await page.screenshot(path=str(captcha_screenshot))
        logger.info(f"Captura del captcha guardada en: {captcha_screenshot}")
        
        # Pedir al usuario que resuelva el captcha manualmente
        print("\n=== CAPTCHA DETECTADO ===")
        print("Por favor, resuelve el captcha manualmente.")
        print("Nota: Es posible que necesites hacer clic en el botón 'Autentificar'/'Authenticate' primero.")
        print("El script esperará hasta que indiques que has completado el captcha.")
        captcha_resolved = input("Presiona Enter cuando hayas resuelto el captcha y estés listo para continuar...")
        logger.info("Usuario indicó que el captcha fue resuelto manualmente.")
        
        # Esperar a que el captcha desaparezca o el campo de contraseña aparezca
        for _ in range(20):  # Intentar hasta 20 segundos
            # Verificar si el iframe de Arkose ya no está presente
            arkose_present = await wait_for_selector_or_continue(page, "#arkoseFrame", timeout=1000)
            if not arkose_present:
                logger.info("Iframe de Arkose ya no está presente, captcha completado con éxito.")
                break
            
            # Verificar si el campo de contraseña está visible (señal de éxito)
            password_visible = await wait_for_selector_or_continue(page, 'input[name="password"]', timeout=1000)
            if password_visible:
                logger.info("Campo de contraseña detectado, captcha completado con éxito.")
                break
            
            await asyncio.sleep(1)
        
        return True
    else:
        logger.info("No se detectó captcha, continuando con el flujo normal de login.")
        return False

# Función para verificar y guardar la sesión con información del perfil
async def save_session(context, page, screenshot_dir, sessions_dir, username):
    # Guardar el estado de la sesión
    logger.info('Guardando estado de la sesión...')
    session_state = await context.storage_state()
    
    # Obtener información del perfil usando BeautifulSoup
    profile_info = {}
    try:
        # Analizar la página con BS4 para verificar si estamos logueados
        page_analysis = await analyze_page_with_bs4(page, "is_logged_in")
        
        if page_analysis["found"]:
            # Si hay información de perfil, guardarla
            if page_analysis.get("profile_info"):
                profile_info = page_analysis["profile_info"]
                
            # También guardar el nombre de usuario proporcionado para iniciar sesión
            profile_info['loginUsername'] = username
    except Exception as e:
        logger.error(f"Error al obtener información del perfil: {e}")
    
    # Añadir timestamp y metadatos al estado de la sesión
    current_time = datetime.now()
    session_data = {
        'timestamp': current_time.isoformat(),
        'userAgent': await page.evaluate('navigator.userAgent'),
        'platform': await page.evaluate('navigator.platform'),
        'sessionState': session_state,
        'profileInfo': profile_info
    }
    
    # Crear directorio de sesiones si no existe
    sessions_dir.mkdir(exist_ok=True)
    
    # Usar el nombre de usuario y la fecha en el nombre del archivo
    user_identifier = username
    date_str = current_time.strftime('%Y%m%d')
    
    # Nombre de archivo con usuario y fecha: x_session_username_YYYYMMDD.json
    session_file_path = sessions_dir / f'x_session_{user_identifier}_{date_str}.json'
    
    # Eliminar sesiones antiguas del mismo usuario
    try:
        for old_file in sessions_dir.glob(f'x_session_{user_identifier}_*.json'):
            if old_file != session_file_path:  # No eliminar el archivo que vamos a crear
                old_file.unlink()  # Eliminar archivo antiguo
                logger.info(f'Sesión antigua eliminada: {old_file}')
    except Exception as e:
        logger.warning(f'Error al eliminar sesiones antiguas: {e}')
    
    # Guardar la nueva sesión
    with open(session_file_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    logger.info(f'Sesión guardada en: {session_file_path}')
    
    # Tomar captura de pantalla del estado actual
    timestamp_str = current_time.strftime('%H%M%S')
    await page.screenshot(path=str(screenshot_dir / f'session_saved_{user_identifier}_{date_str}_{timestamp_str}.png'))
    
    return session_file_path

# Función para configurar el proxy en Playwright basado en variables de entorno
def get_proxy_config():
    """
    Obtiene la configuración de proxy desde las variables de entorno.
    
    Returns:
        dict: Configuración de proxy para Playwright, o None si no hay proxy configurado
    """
    if os.environ.get("USE_PROXY") == "true" and os.environ.get("PROXY_SERVER"):
        proxy_config = {
            "server": os.environ.get("PROXY_SERVER")
        }
        
        # Añadir credenciales si están disponibles
        if os.environ.get("PROXY_USERNAME") and os.environ.get("PROXY_PASSWORD"):
            proxy_config["username"] = os.environ.get("PROXY_USERNAME")
            proxy_config["password"] = os.environ.get("PROXY_PASSWORD")
        
        # Añadir tipo de proxy si está disponible
        proxy_type = os.environ.get("PROXY_TYPE")
        if proxy_type and proxy_type.startswith("socks"):
            proxy_config["type"] = proxy_type
        
        logger.info(f"Usando proxy: {proxy_config['server']}")
        return proxy_config
    else:
        logger.info("No se configuró proxy o está desactivado.")
        return None

# Función principal
async def manual_login():
    # Cargar cuentas desde el archivo JSON
    accounts = load_accounts()
    
    # Seleccionar una cuenta
    username, password = select_account(accounts)
    
    if not username or not password:
        logger.info("No se seleccionó ninguna cuenta. Saliendo...")
        return
    
    logger.info(f"Iniciando sesión con la cuenta: {username}")
    
    # Crear directorios necesarios
    screenshot_dir = Path('screenshots')
    screenshot_dir.mkdir(exist_ok=True)
    
    sessions_dir = Path('sessions')
    sessions_dir.mkdir(exist_ok=True)
    
    # Obtener configuración de proxy
    proxy_config = get_proxy_config()
    
    async with async_playwright() as p:
        # Lanzar el navegador con UI visible
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=browser_args
        )
        
        # Parámetros para el contexto
        context_params = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'bypass_csp': True,
            'ignore_https_errors': True
        }
        
        # Añadir proxy si está configurado
        if proxy_config:
            context_params['proxy'] = proxy_config
        
        # Crear contexto con configuración para evitar detección
        context = await browser.new_context(**context_params)
        
        # Agregar script para ocultar detección de automatización
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined 
            });
            
            // Ocultar más características de automatización
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
            
            // Sobrescribir propiedades de plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    0: {
                        type: 'application/x-google-chrome-pdf',
                        suffixes: 'pdf',
                        description: 'Portable Document Format'
                    },
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format',
                    length: 1
                }))
            });
        """)
        
        # Crear una nueva página
        page = await context.new_page()
        
        try:
            # Ir directamente a la página de inicio de sesión para evitar redirecciones extras
            logger.info('Navegando a la página de inicio de sesión...')
            await page.goto('https://x.com/i/flow/login', wait_until='domcontentloaded')
            await human_delay(1000, 2000)
            
            # Tomar captura de pantalla de la página inicial
            await page.screenshot(path=str(screenshot_dir / '1_initial_page.png'))
            
            # Verificar si ya estamos en una sesión iniciada usando BeautifulSoup
            page_analysis = await analyze_page_with_bs4(page, "is_logged_in")
            is_logged_in = page_analysis["found"]
            
            if is_logged_in:
                logger.info("¡Ya hay una sesión iniciada! Guardando estado actual...")
                await save_session(context, page, screenshot_dir, sessions_dir, username)
            else:
                # Usar BeautifulSoup para encontrar el campo de usuario
                logger.info("Buscando campo de usuario con análisis de página...")
                username_analysis = await analyze_page_with_bs4(page, "username_field")
                
                # Intentar con los selectores tradicionales si BS4 no encuentra nada
                username_selectors = [
                    'input[name="text"]',
                    'input[autocomplete="username"]',
                    'input[class*="r-30o5oe"]'
                ]
                
                # Añadir selectores encontrados por BS4
                if username_analysis["found"]:
                    username_selectors = username_analysis["selectors"] + username_selectors
                
                # Probar cada selector para el campo de usuario
                username_input_found = False
                for selector in username_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=5000):
                        logger.info(f'Campo de usuario encontrado: {selector}')
                        await human_delay()
                        await type_human_like(page, selector, username)
                        await human_delay(1000, 2000)
                        username_input_found = True
                        break
                
                if not username_input_found:
                    logger.error("No se encontró el campo de usuario. Por favor, introdúcelo manualmente.")
                    manual_action = input("Presiona Enter cuando hayas introducido el nombre de usuario manualmente...")
                
                # Buscar botón "Next" usando BS4
                logger.info("Buscando botón Next/Siguiente con análisis de página...")
                next_button_analysis = await analyze_page_with_bs4(page, "next_button")
                
                # Lista de selectores tradicionales
                next_selectors = [
                    'button:has-text("Next")',
                    'button:has-text("Siguiente")',
                    'button[type="button"]:has(span:has-text("Next"))',
                    'button[type="button"]:has(span:has-text("Siguiente"))',
                    'div[role="button"]:has-text("Next")',
                    'div[role="button"]:has-text("Siguiente")'
                ]
                
                # Añadir selectores encontrados por BS4
                if next_button_analysis["found"]:
                    next_selectors = next_button_analysis["selectors"] + next_selectors
                
                # Hacer clic en el botón Next/Siguiente
                logger.info("Haciendo clic en el botón Next/Siguiente...")
                next_button_found = False
                
                # Añadir selectores específicos basados en el HTML proporcionado
                specific_next_selectors = [
                    "button[role='button'][type='button'] span span:has-text('Next')",
                    "button[role='button'][type='button'] div:has-text('Next')"
                ]
                
                # Intentar primero con los selectores específicos
                for selector in specific_next_selectors + next_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=3000):
                        logger.info(f'Botón Next/Siguiente encontrado: {selector}')
                        if await click_safely(page, selector):
                            next_button_found = True
                            await human_delay(1000, 2000)
                            break
                
                # Si no funciona, intentar con JavaScript para buscar el botón por su texto
                if not next_button_found:
                    logger.info("Intentando encontrar el botón 'Next' con JavaScript...")
                    try:
                        # Script que busca botones que contengan el texto "Next"
                        found = await page.evaluate('''() => {
                            const buttonTexts = ['Next', 'Siguiente'];
                            // Buscar botones con el texto exacto
                            for (const text of buttonTexts) {
                                const buttons = Array.from(document.querySelectorAll('button')).filter(
                                    button => button.innerText.trim() === text
                                );
                                if (buttons.length > 0) {
                                    buttons[0].click();
                                    return true;
                                }
                            }
                            
                            // Buscar botones que contengan el texto
                            for (const text of buttonTexts) {
                                const buttons = Array.from(document.querySelectorAll('button')).filter(
                                    button => button.innerText.includes(text)
                                );
                                if (buttons.length > 0) {
                                    buttons[0].click();
                                    return true;
                                }
                            }
                            
                            // Buscar elementos con role="button" que contengan el texto
                            for (const text of buttonTexts) {
                                const buttons = Array.from(document.querySelectorAll('[role="button"]')).filter(
                                    el => el.innerText.includes(text)
                                );
                                if (buttons.length > 0) {
                                    buttons[0].click();
                                    return true;
                                }
                            }
                            
                            return false;
                        }''')
                        
                        if found:
                            logger.info("Botón 'Next' encontrado y clicado con JavaScript")
                            next_button_found = True
                            await human_delay(1000, 2000)
                    except Exception as e:
                        logger.error(f"Error al intentar clic con JavaScript: {e}")
                
                if not next_button_found:
                    logger.warning("No se encontró el botón Next/Siguiente. Intentando presionar Enter en el campo de usuario...")
                    try:
                        for selector in username_selectors:
                            if await wait_for_selector_or_continue(page, selector, timeout=1000):
                                await page.press(selector, "Enter")
                                next_button_found = True
                                await human_delay(1000, 2000)
                                break
                    except Exception as e:
                        logger.error(f"Error al presionar Enter: {e}")
                
                if not next_button_found:
                    logger.error("No se pudo avanzar después de introducir el usuario. Por favor, avanza manualmente.")
                    manual_action = input("Presiona Enter cuando hayas avanzado manualmente...")
                
                # Tomar captura de pantalla después de introducir el usuario
                await page.screenshot(path=str(screenshot_dir / '2_after_username.png'))
                
                # Manejar captcha si está presente
                await handle_captcha(page)
                
                # Tomar captura de pantalla después del captcha
                await page.screenshot(path=str(screenshot_dir / '3_after_captcha.png'))
                
                # Usar BeautifulSoup para encontrar el campo de contraseña
                logger.info("Buscando campo de contraseña con análisis de página...")
                password_analysis = await analyze_page_with_bs4(page, "password_field")
                
                # Lista de selectores tradicionales para contraseña
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]'
                ]
                
                # Añadir selectores encontrados por BS4
                if password_analysis["found"]:
                    password_selectors = password_analysis["selectors"] + password_selectors
                
                # Intentar escribir la contraseña
                password_input_found = False
                for selector in password_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=8000):
                        logger.info(f'Campo de contraseña encontrado: {selector}')
                        await human_delay()
                        await type_human_like(page, selector, password)
                        await human_delay(1000, 2000)
                        password_input_found = True
                        break
                
                if not password_input_found:
                    logger.error("No se encontró el campo de contraseña. Por favor, introdúcelo manualmente.")
                    manual_action = input("Presiona Enter cuando hayas introducido la contraseña manualmente...")
                
                # Buscar botón de login usando BS4
                logger.info("Buscando botón Log in/Iniciar sesión con análisis de página...")
                login_button_analysis = await analyze_page_with_bs4(page, "login_button")
                
                # Lista de selectores tradicionales
                login_selectors = [
                    "[data-testid='LoginForm_Login_Button']",
                    'button:has-text("Log in")',
                    'button:has-text("Iniciar sesión")',
                    'div[role="button"]:has-text("Log in")',
                    'div[role="button"]:has-text("Iniciar sesión")',
                    'button[type="button"]:has(span:has-text("Log in"))',
                    'button[type="button"]:has(span:has-text("Iniciar sesión"))'
                ]
                
                # Añadir selectores encontrados por BS4
                if login_button_analysis["found"]:
                    login_selectors = login_button_analysis["selectors"] + login_selectors
                
                # Hacer clic en el botón Log in/Iniciar sesión
                logger.info("Haciendo clic en el botón Log in/Iniciar sesión...")
                login_button_found = False
                
                for selector in login_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=3000):
                        logger.info(f'Botón Log in/Iniciar sesión encontrado: {selector}')
                        if await click_safely(page, selector):
                            login_button_found = True
                            await human_delay(2000, 4000)
                            break
                
                if not login_button_found:
                    logger.warning("No se encontró el botón Log in/Iniciar sesión. Intentando presionar Enter en el campo de contraseña...")
                    try:
                        for selector in password_selectors:
                            if await wait_for_selector_or_continue(page, selector, timeout=1000):
                                await page.press(selector, "Enter")
                                login_button_found = True
                                await human_delay(2000, 4000)
                                break
                    except Exception as e:
                        logger.error(f"Error al presionar Enter: {e}")
                
                if not login_button_found:
                    logger.error("No se pudo iniciar sesión. Por favor, inicia sesión manualmente.")
                    manual_action = input("Presiona Enter cuando hayas iniciado sesión manualmente...")
                
                # Tomar captura de pantalla después de iniciar sesión
                await page.screenshot(path=str(screenshot_dir / '4_after_login.png'))
            
            # Mensaje para el usuario
            print('\n============= ATENCIÓN =============')
            print('El navegador permanecerá abierto para que puedas:')
            print('- Resolver cualquier captcha adicional que aparezca')
            print('- Navegar manualmente si lo necesitas')
            print('- Completar cualquier paso adicional necesario')
            print('El script esperará hasta que indiques que quieres guardar la sesión.')
            print('=====================================\n')
            
            # Esperar a que el usuario indique que quiere guardar la sesión
            while True:
                action = input('\n¿Qué deseas hacer? (guardar/esperar/salir): ')
                
                if action.lower() == 'guardar':
                    # Verificar si el login fue exitoso antes de guardar usando BS4
                    page_analysis = await analyze_page_with_bs4(page, "is_logged_in")
                    is_logged_in = page_analysis["found"]
                    
                    if is_logged_in:
                        logger.info('Sesión verificada correctamente. Guardando...')
                    else:
                        logger.warning('Advertencia: No se puede verificar que el login sea exitoso.')
                        verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
                        if verify_anyway.lower() != 's':
                            logger.info('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
                            continue
                    
                    # Guardar la sesión
                    session_path = await save_session(context, page, screenshot_dir, sessions_dir, username)
                    logger.info(f'Sesión guardada exitosamente en: {session_path}')
                    
                    continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
                    if continue_browsing.lower() != 's':
                        break
                
                elif action.lower() == 'esperar':
                    wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
                    logger.info(f'Esperando {wait_time} segundos...')
                    await asyncio.sleep(wait_time)
                
                elif action.lower() == 'salir':
                    save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
                    if save_before_exit.lower() == 's':
                        await save_session(context, page, screenshot_dir, sessions_dir, username)
                    break
                
                else:
                    print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
            logger.info('Cerrando navegador...')
            
        except Exception as error:
            logger.error(f'Ocurrió un error: {error}')
            await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
            logger.info('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
            # Intentar guardar la sesión incluso si hay un error
            try:
                save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
                if save_anyway.lower() == 's':
                    await save_session(context, page, screenshot_dir, sessions_dir, username)
            except Exception as save_error:
                logger.error(f'Error al guardar la sesión: {save_error}')
        
        finally:
            await browser.close()

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(manual_login())

