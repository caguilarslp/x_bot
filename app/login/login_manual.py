import os
import json
import time
import random
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Función para cargar las cuentas desde el archivo JSON
def load_accounts():
    accounts_file = Path('login_accounts.json')
    if not accounts_file.exists():
        logging.info("No se encontró el archivo login_accounts.json. Creando uno de ejemplo...")
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
        
        logging.info(f"Se ha creado el archivo {accounts_file} con cuentas de ejemplo.")
        logging.info("Por favor, edita este archivo con tus cuentas reales antes de continuar.")
        return example_accounts["accounts"]
    
    try:
        with open(accounts_file, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
            return accounts_data.get("accounts", [])
    except json.JSONDecodeError:
        logging.error("Error: El archivo login_accounts.json no tiene un formato JSON válido.")
        return []
    except Exception as e:
        logging.error(f"Error al cargar el archivo de cuentas: {e}")
        return []

# Función para seleccionar una cuenta de la lista
def select_account(accounts):
    if not accounts:
        logging.error("No hay cuentas disponibles en el archivo login_accounts.json")
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
        logging.error(f"Error al escribir texto: {e}")
        # Intentar una alternativa si el método normal falla
        try:
            await page.fill(selector, text)
        except Exception:
            logging.error("No se pudo escribir el texto.")

# Función para esperar a un selector con posibilidad de continuar si no aparece
async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
    try:
        await page.wait_for_selector(selector, state='visible', timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        if message:
            logging.info(message)
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
            logging.debug(f"Primer intento de clic fallido: {e}")
            
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
            logging.debug(f"Clic por JavaScript fallido: {e}")
            
        # Si todo falla, intentamos con opciones más agresivas
        try:
            await page.click(selector, force=True, timeout=timeout)
            return True
        except Exception as e:
            logging.debug(f"Clic forzado fallido: {e}")
            return False
            
    except Exception as e:
        logging.error(f"Error al intentar hacer clic en {selector}: {e}")
        return False

# Función para detectar y manejar el captcha
async def handle_captcha(page):
    logging.info("Verificando presencia de captcha...")
    
    # Verificar si el iframe de Arkose está presente
    has_arkose_frame = await wait_for_selector_or_continue(page, "#arkoseFrame", timeout=3000)
    
    if has_arkose_frame:
        logging.info("=== CAPTCHA DETECTADO ===")
        logging.info("Se encontró el iframe de Arkose Labs.")
        
        # Tomar captura del captcha para depuración
        screenshot_dir = Path('screenshots')
        screenshot_dir.mkdir(exist_ok=True)
        captcha_screenshot = screenshot_dir / f'captcha_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        await page.screenshot(path=str(captcha_screenshot))
        logging.info(f"Captura del captcha guardada en: {captcha_screenshot}")
        
        # Pedir al usuario que resuelva el captcha manualmente
        print("\n=== CAPTCHA DETECTADO ===")
        print("Por favor, resuelve el captcha manualmente.")
        print("Nota: Es posible que necesites hacer clic en el botón 'Autentificar'/'Authenticate' primero.")
        print("El script esperará hasta que indiques que has completado el captcha.")
        captcha_resolved = input("Presiona Enter cuando hayas resuelto el captcha y estés listo para continuar...")
        logging.info("Usuario indicó que el captcha fue resuelto manualmente.")
        
        # Esperar a que el captcha desaparezca o el campo de contraseña aparezca
        for _ in range(20):  # Intentar hasta 20 segundos
            # Verificar si el iframe de Arkose ya no está presente
            arkose_present = await wait_for_selector_or_continue(page, "#arkoseFrame", timeout=1000)
            if not arkose_present:
                logging.info("Iframe de Arkose ya no está presente, captcha completado con éxito.")
                break
            
            # Verificar si el campo de contraseña está visible (señal de éxito)
            password_visible = await wait_for_selector_or_continue(page, 'input[name="password"]', timeout=1000)
            if password_visible:
                logging.info("Campo de contraseña detectado, captcha completado con éxito.")
                break
            
            await asyncio.sleep(1)
        
        return True
    else:
        logging.info("No se detectó captcha, continuando con el flujo normal de login.")
        return False

# Función para verificar y guardar la sesión con información del perfil
# Función para verificar y guardar la sesión con información del perfil
async def save_session(context, page, screenshot_dir, sessions_dir, username):
    # Guardar el estado de la sesión
    logging.info('Guardando estado de la sesión...')
    session_state = await context.storage_state()
    
    # Obtener información del perfil si estamos logueados
    profile_info = {}
    try:
        is_logged_in = await wait_for_selector_or_continue(page, 'a[data-testid="AppTabBar_Home_Link"]', timeout=3000)
        if is_logged_in:
            # Intentar obtener el nombre de usuario desde la UI
            try:
                username_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"] span span')
                if username_element:
                    profile_info['displayName'] = await username_element.inner_text()
                
                handle_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"][class*="r-1wvb978"] span')
                if handle_element:
                    profile_info['handle'] = await handle_element.inner_text()
                
                # También guardar el nombre de usuario proporcionado para iniciar sesión
                profile_info['loginUsername'] = username
            except Exception as e:
                logging.error(f"Error al obtener información del perfil: {e}")
    except Exception as e:
        logging.error(f"Error al verificar login: {e}")
    
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
                logging.info(f'Sesión antigua eliminada: {old_file}')
    except Exception as e:
        logging.warning(f'Error al eliminar sesiones antiguas: {e}')
    
    # Guardar la nueva sesión
    with open(session_file_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    logging.info(f'Sesión guardada en: {session_file_path}')
    
    # Tomar captura de pantalla del estado actual
    timestamp_str = current_time.strftime('%H%M%S')
    await page.screenshot(path=str(screenshot_dir / f'session_saved_{user_identifier}_{date_str}_{timestamp_str}.png'))
    
    return session_file_path

# Función principal
async def manual_login():
    # Cargar cuentas desde el archivo JSON
    accounts = load_accounts()
    
    # Seleccionar una cuenta
    username, password = select_account(accounts)
    
    if not username or not password:
        logging.info("No se seleccionó ninguna cuenta. Saliendo...")
        return
    
    logging.info(f"Iniciando sesión con la cuenta: {username}")
    
    # Crear directorios necesarios
    screenshot_dir = Path('screenshots')
    screenshot_dir.mkdir(exist_ok=True)
    
    sessions_dir = Path('sessions')
    sessions_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Lanzar el navegador con UI visible
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Crear contexto con configuración para evitar detección
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            bypass_csp=True,
            ignore_https_errors=True
        )
        
        # Agregar script para ocultar detección de automatización
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined 
            });
        """)
        
        # Crear una nueva página
        page = await context.new_page()
        
        try:
            # Ir directamente a la página de inicio de sesión para evitar redirecciones extras
            logging.info('Navegando a la página de inicio de sesión...')
            await page.goto('https://x.com/i/flow/login', wait_until='domcontentloaded')
            await human_delay(1000, 2000)
            
            # Tomar captura de pantalla de la página inicial
            await page.screenshot(path=str(screenshot_dir / '1_initial_page.png'))
            
            # Verificar si ya estamos en una sesión iniciada
            is_logged_in = await wait_for_selector_or_continue(
                page, 
                'a[data-testid="AppTabBar_Home_Link"]', 
                timeout=3000, 
                message="No se detectó sesión iniciada, intentando iniciar sesión."
            )
            
            if is_logged_in:
                logging.info("¡Ya hay una sesión iniciada! Guardando estado actual...")
                await save_session(context, page, screenshot_dir, sessions_dir, username)
            else:
                # Esperar al campo de nombre de usuario
                logging.info("Esperando al campo de nombre de usuario...")
                username_input_found = False
                username_selectors = [
                    'input[name="text"]',
                    'input[autocomplete="username"]',
                    'input[class*="r-30o5oe"]'
                ]
                
                for selector in username_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=5000):
                        logging.info(f'Campo de usuario encontrado: {selector}')
                        await human_delay()
                        await type_human_like(page, selector, username)
                        await human_delay(1000, 2000)
                        username_input_found = True
                        break
                
                if not username_input_found:
                    logging.error("No se encontró el campo de usuario. Por favor, introdúcelo manualmente.")
                    manual_action = input("Presiona Enter cuando hayas introducido el nombre de usuario manualmente...")
                
                # Hacer clic en el botón Next/Siguiente
                logging.info("Haciendo clic en el botón Next/Siguiente...")
                next_button_found = False
                
                next_selectors = [
                    'button:has-text("Next")',
                    'button:has-text("Siguiente")',
                    'button[type="button"]:has(span:has-text("Next"))',
                    'button[type="button"]:has(span:has-text("Siguiente"))',
                    'div[role="button"]:has-text("Next")',
                    'div[role="button"]:has-text("Siguiente")',
                    'button[role="button"]:has(span:has-text("Next"))',
                    'button[role="button"]:has(span:has-text("Siguiente"))'
                ]
                
                for selector in next_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=3000):
                        logging.info(f'Botón Next/Siguiente encontrado: {selector}')
                        if await click_safely(page, selector):
                            next_button_found = True
                            await human_delay(1000, 2000)
                            break
                
                if not next_button_found:
                    logging.warning("No se encontró el botón Next/Siguiente. Intentando presionar Enter en el campo de usuario...")
                    try:
                        for selector in username_selectors:
                            if await wait_for_selector_or_continue(page, selector, timeout=1000):
                                await page.press(selector, "Enter")
                                next_button_found = True
                                await human_delay(1000, 2000)
                                break
                    except Exception as e:
                        logging.error(f"Error al presionar Enter: {e}")
                
                if not next_button_found:
                    logging.error("No se pudo avanzar después de introducir el usuario. Por favor, avanza manualmente.")
                    manual_action = input("Presiona Enter cuando hayas avanzado manualmente...")
                
                # Tomar captura de pantalla después de introducir el usuario
                await page.screenshot(path=str(screenshot_dir / '2_after_username.png'))
                
                # Manejar captcha si está presente
                await handle_captcha(page)
                
                # Tomar captura de pantalla después del captcha
                await page.screenshot(path=str(screenshot_dir / '3_after_captcha.png'))
                
                # Esperar al campo de contraseña
                logging.info("Esperando al campo de contraseña...")
                password_input_found = False
                password_selectors = [
                    'input[name="password"]',
                    'input[type="password"]',
                    'input[autocomplete="current-password"]'
                ]
                
                for selector in password_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=8000):
                        logging.info(f'Campo de contraseña encontrado: {selector}')
                        await human_delay()
                        await type_human_like(page, selector, password)
                        await human_delay(1000, 2000)
                        password_input_found = True
                        break
                
                if not password_input_found:
                    logging.error("No se encontró el campo de contraseña. Por favor, introdúcelo manualmente.")
                    manual_action = input("Presiona Enter cuando hayas introducido la contraseña manualmente...")
                
                # Hacer clic en el botón Log in/Iniciar sesión
                logging.info("Haciendo clic en el botón Log in/Iniciar sesión...")
                login_button_found = False
                login_selectors = [
                    'button:has-text("Log in")',
                    'button:has-text("Iniciar sesión")',
                    'div[role="button"]:has-text("Log in")',
                    'div[role="button"]:has-text("Iniciar sesión")',
                    'button[type="button"]:has(span:has-text("Log in"))',
                    'button[type="button"]:has(span:has-text("Iniciar sesión"))'
                ]
                
                for selector in login_selectors:
                    if await wait_for_selector_or_continue(page, selector, timeout=3000):
                        logging.info(f'Botón Log in/Iniciar sesión encontrado: {selector}')
                        if await click_safely(page, selector):
                            login_button_found = True
                            await human_delay(2000, 4000)
                            break
                
                if not login_button_found:
                    logging.warning("No se encontró el botón Log in/Iniciar sesión. Intentando presionar Enter en el campo de contraseña...")
                    try:
                        for selector in password_selectors:
                            if await wait_for_selector_or_continue(page, selector, timeout=1000):
                                await page.press(selector, "Enter")
                                login_button_found = True
                                await human_delay(2000, 4000)
                                break
                    except Exception as e:
                        logging.error(f"Error al presionar Enter: {e}")
                
                if not login_button_found:
                    logging.error("No se pudo iniciar sesión. Por favor, inicia sesión manualmente.")
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
                    # Verificar si el login fue exitoso antes de guardar
                    try:
                        await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
                        logging.info('Sesión verificada correctamente. Guardando...')
                    except PlaywrightTimeoutError:
                        logging.warning('Advertencia: No se puede verificar que el login sea exitoso.')
                        verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
                        if verify_anyway.lower() != 's':
                            logging.info('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
                            continue
                    
                    # Guardar la sesión
                    session_path = await save_session(context, page, screenshot_dir, sessions_dir, username)
                    logging.info(f'Sesión guardada exitosamente en: {session_path}')
                    
                    continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
                    if continue_browsing.lower() != 's':
                        break
                
                elif action.lower() == 'esperar':
                    wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
                    logging.info(f'Esperando {wait_time} segundos...')
                    await asyncio.sleep(wait_time)
                
                elif action.lower() == 'salir':
                    save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
                    if save_before_exit.lower() == 's':
                        await save_session(context, page, screenshot_dir, sessions_dir, username)
                    break
                
                else:
                    print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
            logging.info('Cerrando navegador...')
            
        except Exception as error:
            logging.error(f'Ocurrió un error: {error}')
            await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
            logging.info('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
            # Intentar guardar la sesión incluso si hay un error
            try:
                save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
                if save_anyway.lower() == 's':
                    await save_session(context, page, screenshot_dir, sessions_dir, username)
            except Exception as save_error:
                logging.error(f'Error al guardar la sesión: {save_error}')
        
        finally:
            await browser.close()

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(manual_login())

#################################################################################
##### ANTES DETECCIÓN CAPTCHA PARA RESOLVER MANUAL
#################################################################################

# import os
# import json
# import time
# import random
# import asyncio
# from datetime import datetime
# from pathlib import Path
# from playwright.async_api import async_playwright, TimeoutError

# # Función para cargar las cuentas desde el archivo JSON
# def load_accounts():
#     accounts_file = Path('login_accounts.json')
#     if not accounts_file.exists():
#         print("No se encontró el archivo login_accounts.json. Creando uno de ejemplo...")
#         example_accounts = {
#             "accounts": [
#                 {
#                     "username": "antonioreverteandujar@gmx.com",
#                     "password": "xJHuc@EhMFNBgJd3",
#                     "description": "Cuenta principal para automatización"
#                 },
#                 {
#                     "username": "ejemplo@email.com",
#                     "password": "contraseña_ejemplo",
#                     "description": "Cuenta de ejemplo"
#                 }
#             ]
#         }
#         with open(accounts_file, 'w', encoding='utf-8') as f:
#             json.dump(example_accounts, f, indent=2)
        
#         print(f"Se ha creado el archivo {accounts_file} con cuentas de ejemplo.")
#         print("Por favor, edita este archivo con tus cuentas reales antes de continuar.")
#         return example_accounts["accounts"]
    
#     try:
#         with open(accounts_file, 'r', encoding='utf-8') as f:
#             accounts_data = json.load(f)
#             return accounts_data.get("accounts", [])
#     except json.JSONDecodeError:
#         print("Error: El archivo login_accounts.json no tiene un formato JSON válido.")
#         return []
#     except Exception as e:
#         print(f"Error al cargar el archivo de cuentas: {e}")
#         return []

# # Función para seleccionar una cuenta de la lista
# def select_account(accounts):
#     if not accounts:
#         print("No hay cuentas disponibles en el archivo login_accounts.json")
#         return None, None
    
#     print("\n=== Cuentas Disponibles ===")
#     for i, account in enumerate(accounts):
#         username = account.get("username", "Sin nombre de usuario")
#         description = account.get("description", "")
#         print(f"{i+1}. {username} - {description}")
    
#     while True:
#         try:
#             selection = input("\nSelecciona el número de la cuenta que quieres usar (o 'q' para salir): ")
#             if selection.lower() == 'q':
#                 return None, None
            
#             index = int(selection) - 1
#             if 0 <= index < len(accounts):
#                 selected_account = accounts[index]
#                 return selected_account.get("username"), selected_account.get("password")
#             else:
#                 print(f"Error: Por favor, selecciona un número entre 1 y {len(accounts)}")
#         except ValueError:
#             print("Error: Por favor, introduce un número válido")

# # Función para agregar retraso de aspecto humano (tiempo variable)
# async def human_delay(min_ms=500, max_ms=2000):
#     delay = random.uniform(min_ms, max_ms) / 1000
#     await asyncio.sleep(delay)

# # Función para simular movimiento de ratón realista
# async def move_mouse_realistic(page, target_selector):
#     # Obtener la posición del elemento
#     try:
#         element = await page.query_selector(target_selector)
#         if not element:
#             return False
        
#         box = await element.bounding_box()
#         if not box:
#             return False
        
#         # Calcular posición objetivo (ligeramente aleatorizada dentro del elemento)
#         target_x = box["x"] + box["width"] * (0.3 + random.random() * 0.4)
#         target_y = box["y"] + box["height"] * (0.3 + random.random() * 0.4)
        
#         # Obtener posición actual del ratón o utilizar una posición de inicio predeterminada
#         current_x = 500 + random.random() * 200
#         current_y = 300 + random.random() * 100
        
#         # Número de pasos para el movimiento (más pasos = movimiento más suave)
#         steps = 10 + int(random.random() * 15)
        
#         # Puntos de control de curva Bezier para una curva natural
#         cp1x = current_x + (target_x - current_x) * (0.2 + random.random() * 0.3)
#         cp1y = current_y + (target_y - current_y) * (0.3 + random.random() * 0.4)
#         cp2x = current_x + (target_x - current_x) * (0.7 + random.random() * 0.2)
#         cp2y = current_y + (target_y - current_y) * (0.7 + random.random() * 0.2)
        
#         # Realizar el movimiento en pasos
#         for i in range(steps + 1):
#             t = i / steps
            
#             # Fórmula de curva Bezier para bezier cúbico
#             t_squared = t * t
#             t_cubed = t_squared * t
#             t_complement = 1 - t
#             t_complement_squared = t_complement * t_complement
#             t_complement_cubed = t_complement_squared * t_complement
            
#             x = t_complement_cubed * current_x + \
#                 3 * t_complement_squared * t * cp1x + \
#                 3 * t_complement * t_squared * cp2x + \
#                 t_cubed * target_x
                    
#             y = t_complement_cubed * current_y + \
#                 3 * t_complement_squared * t * cp1y + \
#                 3 * t_complement * t_squared * cp2y + \
#                 t_cubed * target_y
            
#             await page.mouse.move(x, y)
            
#             # Añadir pequeño retraso aleatorio entre movimientos
#             await asyncio.sleep(0.01 + random.random() * 0.03)
        
#         return True
#     except Exception as e:
#         print(f"Error en el movimiento del ratón: {e}")
#         return False

# # Función para escribir texto con velocidad variable como un humano
# async def type_human_like(page, selector, text):
#     try:
#         await page.focus(selector)
        
#         # Borrar cualquier texto existente primero
#         await page.fill(selector, '')
#         await human_delay(200, 600)
        
#         # Escribir cada carácter con retraso variable
#         for char in text:
#             await page.type(selector, char, delay=50 + random.randint(50, 150))
            
#             # Ocasionalmente hacer una pausa como lo haría un humano
#             if random.random() < 0.2:
#                 await human_delay(200, 1000)
#     except Exception as e:
#         print(f"Error al escribir texto: {e}")
#         # Intentar una alternativa si el método normal falla
#         try:
#             await page.fill(selector, text)
#         except Exception:
#             print("No se pudo escribir el texto.")

# # Función para esperar a un selector con posibilidad de continuar si no aparece
# async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
#     try:
#         await page.wait_for_selector(selector, state='visible', timeout=timeout)
#         return True
#     except TimeoutError:
#         if message:
#             print(message)
#         return False

# # Función para hacer clic con manejo de interceptores
# async def click_safely(page, selector, timeout=30000, force=False):
#     try:
#         # Primero intentamos el método estándar
#         try:
#             element = await page.wait_for_selector(selector, timeout=5000)
#             if element:
#                 if force:
#                     await element.click(force=True)
#                 else:
#                     await element.click()
#                 return True
#         except Exception as e:
#             print(f"Primer intento de clic fallido: {e}")
            
#         # Si falla, intentamos con JavaScript
#         try:
#             await page.evaluate(f'''() => {{
#                 const elements = document.querySelectorAll('{selector}');
#                 if (elements.length > 0) {{
#                     elements[0].click();
#                     return true;
#                 }}
#                 return false;
#             }}''')
#             await human_delay(500, 1000)  # Esperar para que el clic surta efecto
#             return True
#         except Exception as e:
#             print(f"Clic por JavaScript fallido: {e}")
            
#         # Si todo falla, intentamos con opciones más agresivas
#         try:
#             await page.click(selector, force=True, timeout=timeout)
#             return True
#         except Exception as e:
#             print(f"Clic forzado fallido: {e}")
#             return False
            
#     except Exception as e:
#         print(f"Error al intentar hacer clic en {selector}: {e}")
#         return False

# # Función para verificar y guardar la sesión con información del perfil
# async def save_session(context, page, screenshot_dir, sessions_dir, username):
#     # Guardar el estado de la sesión
#     print('Guardando estado de la sesión...')
#     session_state = await context.storage_state()
    
#     # Obtener información del perfil si estamos logueados
#     profile_info = {}
#     try:
#         is_logged_in = await wait_for_selector_or_continue(page, 'a[data-testid="AppTabBar_Home_Link"]', timeout=3000)
#         if is_logged_in:
#             # Intentar obtener el nombre de usuario desde la UI
#             try:
#                 username_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"] span span')
#                 if username_element:
#                     profile_info['displayName'] = await username_element.inner_text()
                
#                 handle_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"][class*="r-1wvb978"] span')
#                 if handle_element:
#                     profile_info['handle'] = await handle_element.inner_text()
                
#                 # También guardar el nombre de usuario proporcionado para iniciar sesión
#                 profile_info['loginUsername'] = username
#             except Exception as e:
#                 print(f"Error al obtener información del perfil: {e}")
#     except Exception as e:
#         print(f"Error al verificar login: {e}")
    
#     # Añadir timestamp y metadatos al estado de la sesión
#     current_time = datetime.now()
#     session_data = {
#         'timestamp': current_time.isoformat(),
#         'userAgent': await page.evaluate('navigator.userAgent'),
#         'platform': await page.evaluate('navigator.platform'),
#         'sessionState': session_state,
#         'profileInfo': profile_info
#     }
    
#     # Crear directorio de sesiones si no existe
#     sessions_dir.mkdir(exist_ok=True)
    
#     # Usar solo el nombre de usuario en el nombre del archivo
#     user_identifier = username
    
#     # Nombre simplificado del archivo (solo nombre de usuario)
#     session_file_path = sessions_dir / f'x_session_{user_identifier}.json'
    
#     # Si el archivo ya existe, hacer una copia de seguridad
#     if session_file_path.exists():
#         backup_timestamp = current_time.strftime('%Y%m%d_%H%M%S')
#         backup_path = sessions_dir / f'x_session_{user_identifier}_{backup_timestamp}.json'
#         import shutil
#         shutil.copy2(session_file_path, backup_path)
#         print(f'Se creó copia de seguridad de la sesión anterior: {backup_path}')
    
#     with open(session_file_path, 'w', encoding='utf-8') as f:
#         json.dump(session_data, f, indent=2)
#     print(f'Sesión guardada en: {session_file_path}')
    
#     # Tomar captura de pantalla del estado actual con timestamp para diferenciarlo
#     timestamp_str = current_time.strftime('%Y%m%d_%H%M%S')
#     await page.screenshot(path=str(screenshot_dir / f'session_saved_{user_identifier}_{timestamp_str}.png'))
    
#     return session_file_path

# # Función principal
# async def manual_login():
#     # Cargar cuentas desde el archivo JSON
#     accounts = load_accounts()
    
#     # Seleccionar una cuenta
#     username, password = select_account(accounts)
    
#     if not username or not password:
#         print("No se seleccionó ninguna cuenta. Saliendo...")
#         return
    
#     print(f"Iniciando sesión con la cuenta: {username}")
    
#     # Crear directorios necesarios
#     screenshot_dir = Path('screenshots')
#     screenshot_dir.mkdir(exist_ok=True)
    
#     sessions_dir = Path('sessions')
#     sessions_dir.mkdir(exist_ok=True)
    
#     async with async_playwright() as p:
#         # Lanzar el navegador con UI visible
#         browser = await p.chromium.launch(
#             headless=False,
#             slow_mo=50,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--no-sandbox',
#                 '--disable-web-security',
#                 '--disable-features=IsolateOrigins,site-per-process'
#             ]
#         )
        
#         # Crear contexto con configuración para evitar detección
#         context = await browser.new_context(
#             viewport={'width': 1280, 'height': 800},
#             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
#             locale='en-US',
#             timezone_id='America/New_York',
#             bypass_csp=True,
#             ignore_https_errors=True
#         )
        
#         # Crear una nueva página
#         page = await context.new_page()
        
#         try:
#             print('Navegando a X.com...')
#             await page.goto('https://x.com', wait_until='networkidle')
#             await human_delay()
            
#             # Tomar captura de pantalla de la página inicial
#             await page.screenshot(path=str(screenshot_dir / '1_initial_page.png'))
            
#             # Verificar si ya estamos en una sesión iniciada
#             is_logged_in = await wait_for_selector_or_continue(
#                 page, 
#                 'a[data-testid="AppTabBar_Home_Link"]', 
#                 timeout=3000, 
#                 message="No se detectó sesión iniciada, intentando iniciar sesión."
#             )
            
#             if is_logged_in:
#                 print("¡Ya hay una sesión iniciada! Guardando estado actual...")
#                 await save_session(context, page, screenshot_dir, sessions_dir, username)
#             else:
#                 # Intentar encontrar y hacer clic en el botón de login/sign in
#                 sign_in_found = False
                
#                 # Probar diferentes selectores para el botón de login/sign in
#                 sign_in_selectors = [
#                     'a[data-testid="loginButton"]',
#                     'a[href="/login"]',
#                     'a:has-text("Sign in")',
#                     'a:has-text("Iniciar sesión")'
#                 ]
                
#                 for selector in sign_in_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón de login ({selector})...')
#                         if await click_safely(page, selector):
#                             sign_in_found = True
#                             await human_delay(1000, 2000)
#                             break
                
#                 if not sign_in_found:
#                     print("No se pudo encontrar o hacer clic en el botón de login. Continuando de todos modos...")
                
#                 # Tomar captura de pantalla del estado actual
#                 await page.screenshot(path=str(screenshot_dir / '2_login_state.png'))
                
#                 # Comprobar si estamos en la pantalla de introducir usuario
#                 username_input_found = False
#                 username_selectors = [
#                     'input[autocomplete="username"]',
#                     'input[name="text"]',
#                     'input[class*="r-30o5oe"]'
#                 ]
                
#                 for selector in username_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Campo de usuario encontrado: {selector}')
#                         await move_mouse_realistic(page, selector)
#                         await human_delay()
#                         await type_human_like(page, selector, username)
#                         await human_delay(1000, 2000)
#                         username_input_found = True
#                         break
                
#                 if not username_input_found:
#                     print("No se encontró el campo de usuario. Por favor, introdúcelo manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas introducido el nombre de usuario manualmente...")
                
#                 # Soporte mejorado para el botón Next/Siguiente
#                 next_button_found = False
                
#                 # Lista ampliada de selectores para "Next" / "Siguiente"
#                 next_selectors = [
#                     'button:has-text("Next")',
#                     'button:has-text("Siguiente")',
#                     'button[type="button"]:has(span:has-text("Next"))',
#                     'button[type="button"]:has(span:has-text("Siguiente"))',
#                     'div[role="button"]:has-text("Next")',
#                     'div[role="button"]:has-text("Siguiente")',
#                     'button[role="button"]:has(span:has-text("Next"))',
#                     'button[role="button"]:has(span:has-text("Siguiente"))'
#                 ]
                
#                 for selector in next_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón Next/Siguiente: {selector}')
#                         if await click_safely(page, selector):
#                             next_button_found = True
#                             await human_delay(1000, 2000)
#                             break
                
#                 if not next_button_found:
#                     print("No se encontró el botón Next/Siguiente. Por favor, avanza manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas avanzado a la pantalla de contraseña...")
                
#                 # Tomar captura de pantalla después de introducir el usuario
#                 await page.screenshot(path=str(screenshot_dir / '3_after_username.png'))
                
#                 # Comprobar si estamos en la pantalla de contraseña
#                 password_input_found = False
#                 password_selectors = [
#                     'input[name="password"]',
#                     'input[type="password"]',
#                     'input[autocomplete="current-password"]'
#                 ]
                
#                 for selector in password_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Campo de contraseña encontrado: {selector}')
#                         await move_mouse_realistic(page, selector)
#                         await human_delay()
#                         await type_human_like(page, selector, password)
#                         await human_delay(1000, 2000)
#                         password_input_found = True
#                         break
                
#                 if not password_input_found:
#                     print("No se encontró el campo de contraseña. Por favor, introdúcelo manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas introducido la contraseña manualmente...")
                
#                 # Intentar hacer clic en el botón Log in
#                 login_button_found = False
#                 login_selectors = [
#                     'button:has-text("Log in")',
#                     'button:has-text("Iniciar sesión")',
#                     'div[role="button"]:has-text("Log in")',
#                     'div[role="button"]:has-text("Iniciar sesión")',
#                     'button[type="button"]:has(span:has-text("Log in"))',
#                     'button[type="button"]:has(span:has-text("Iniciar sesión"))'
#                 ]
                
#                 for selector in login_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón Log in: {selector}')
#                         if await click_safely(page, selector):
#                             login_button_found = True
#                             await human_delay(2000, 4000)
#                             break
                
#                 if not login_button_found:
#                     print("No se encontró el botón Log in. Por favor, inicia sesión manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas iniciado sesión manualmente...")
                
#                 # Tomar captura de pantalla después de iniciar sesión
#                 await page.screenshot(path=str(screenshot_dir / '4_after_password.png'))
            
#             # Mensaje para el usuario
#             print('\n============= ATENCIÓN =============')
#             print('El navegador permanecerá abierto para que puedas:')
#             print('- Resolver cualquier captcha que aparezca')
#             print('- Navegar manualmente si lo necesitas')
#             print('- Completar cualquier paso adicional necesario')
#             print('El script esperará hasta que indiques que quieres guardar la sesión.')
#             print('=====================================\n')
            
#             # Esperar a que el usuario indique que quiere guardar la sesión
#             while True:
#                 action = input('\n¿Qué deseas hacer? (guardar/esperar/salir): ')
                
#                 if action.lower() == 'guardar':
#                     # Verificar si el login fue exitoso antes de guardar
#                     try:
#                         await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
#                         print('Sesión verificada correctamente. Guardando...')
#                     except TimeoutError:
#                         print('Advertencia: No se puede verificar que el login sea exitoso.')
#                         verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
#                         if verify_anyway.lower() != 's':
#                             print('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
#                             continue
                    
#                     # Guardar la sesión
#                     session_path = await save_session(context, page, screenshot_dir, sessions_dir, username)
#                     print(f'Sesión guardada exitosamente en: {session_path}')
                    
#                     continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
#                     if continue_browsing.lower() != 's':
#                         break
                
#                 elif action.lower() == 'esperar':
#                     wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
#                     print(f'Esperando {wait_time} segundos...')
#                     await asyncio.sleep(wait_time)
                
#                 elif action.lower() == 'salir':
#                     save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
#                     if save_before_exit.lower() == 's':
#                         await save_session(context, page, screenshot_dir, sessions_dir, username)
#                     break
                
#                 else:
#                     print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
#             print('Cerrando navegador...')
            
#         except Exception as error:
#             print('Ocurrió un error:', error)
#             await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
#             print('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
#             # Intentar guardar la sesión incluso si hay un error
#             try:
#                 save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
#                 if save_anyway.lower() == 's':
#                     await save_session(context, page, screenshot_dir, sessions_dir, username)
#             except Exception as save_error:
#                 print(f'Error al guardar la sesión: {save_error}')
        
#         finally:
#             await browser.close()

# # Ejecutar la función principal
# if __name__ == "__main__":
#     asyncio.run(manual_login())

# import os
# import json
# import time
# import random
# import asyncio
# from datetime import datetime
# from pathlib import Path
# from playwright.async_api import async_playwright, TimeoutError

# # Función para agregar retraso de aspecto humano (tiempo variable)
# async def human_delay(min_ms=500, max_ms=2000):
#     delay = random.uniform(min_ms, max_ms) / 1000
#     await asyncio.sleep(delay)

# # Función para simular movimiento de ratón realista
# async def move_mouse_realistic(page, target_selector):
#     # Obtener la posición del elemento
#     try:
#         element = await page.query_selector(target_selector)
#         if not element:
#             return False
        
#         box = await element.bounding_box()
#         if not box:
#             return False
        
#         # Calcular posición objetivo (ligeramente aleatorizada dentro del elemento)
#         target_x = box["x"] + box["width"] * (0.3 + random.random() * 0.4)
#         target_y = box["y"] + box["height"] * (0.3 + random.random() * 0.4)
        
#         # Obtener posición actual del ratón o utilizar una posición de inicio predeterminada
#         current_x = 500 + random.random() * 200
#         current_y = 300 + random.random() * 100
        
#         # Número de pasos para el movimiento (más pasos = movimiento más suave)
#         steps = 10 + int(random.random() * 15)
        
#         # Puntos de control de curva Bezier para una curva natural
#         cp1x = current_x + (target_x - current_x) * (0.2 + random.random() * 0.3)
#         cp1y = current_y + (target_y - current_y) * (0.3 + random.random() * 0.4)
#         cp2x = current_x + (target_x - current_x) * (0.7 + random.random() * 0.2)
#         cp2y = current_y + (target_y - current_y) * (0.7 + random.random() * 0.2)
        
#         # Realizar el movimiento en pasos
#         for i in range(steps + 1):
#             t = i / steps
            
#             # Fórmula de curva Bezier para bezier cúbico
#             t_squared = t * t
#             t_cubed = t_squared * t
#             t_complement = 1 - t
#             t_complement_squared = t_complement * t_complement
#             t_complement_cubed = t_complement_squared * t_complement
            
#             x = t_complement_cubed * current_x + \
#                 3 * t_complement_squared * t * cp1x + \
#                 3 * t_complement * t_squared * cp2x + \
#                 t_cubed * target_x
                    
#             y = t_complement_cubed * current_y + \
#                 3 * t_complement_squared * t * cp1y + \
#                 3 * t_complement * t_squared * cp2y + \
#                 t_cubed * target_y
            
#             await page.mouse.move(x, y)
            
#             # Añadir pequeño retraso aleatorio entre movimientos
#             await asyncio.sleep(0.01 + random.random() * 0.03)
        
#         return True
#     except Exception as e:
#         print(f"Error en el movimiento del ratón: {e}")
#         return False

# # Función para escribir texto con velocidad variable como un humano
# async def type_human_like(page, selector, text):
#     try:
#         await page.focus(selector)
        
#         # Borrar cualquier texto existente primero
#         await page.fill(selector, '')
#         await human_delay(200, 600)
        
#         # Escribir cada carácter con retraso variable
#         for char in text:
#             await page.type(selector, char, delay=50 + random.randint(50, 150))
            
#             # Ocasionalmente hacer una pausa como lo haría un humano
#             if random.random() < 0.2:
#                 await human_delay(200, 1000)
#     except Exception as e:
#         print(f"Error al escribir texto: {e}")
#         # Intentar una alternativa si el método normal falla
#         try:
#             await page.fill(selector, text)
#         except Exception:
#             print("No se pudo escribir el texto.")

# # Función para esperar a un selector con posibilidad de continuar si no aparece
# async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
#     try:
#         await page.wait_for_selector(selector, state='visible', timeout=timeout)
#         return True
#     except TimeoutError:
#         if message:
#             print(message)
#         return False

# # Mejorado: Función para hacer clic con manejo de interceptores
# async def click_safely(page, selector, timeout=30000, force=False):
#     try:
#         # Primero intentamos el método estándar
#         try:
#             element = await page.wait_for_selector(selector, timeout=5000)
#             if element:
#                 if force:
#                     await element.click(force=True)
#                 else:
#                     await element.click()
#                 return True
#         except Exception as e:
#             print(f"Primer intento de clic fallido: {e}")
            
#         # Si falla, intentamos con JavaScript
#         try:
#             await page.evaluate(f'''() => {{
#                 const elements = document.querySelectorAll('{selector}');
#                 if (elements.length > 0) {{
#                     elements[0].click();
#                     return true;
#                 }}
#                 return false;
#             }}''')
#             await human_delay(500, 1000)  # Esperar para que el clic surta efecto
#             return True
#         except Exception as e:
#             print(f"Clic por JavaScript fallido: {e}")
            
#         # Si todo falla, intentamos con opciones más agresivas
#         try:
#             await page.click(selector, force=True, timeout=timeout)
#             return True
#         except Exception as e:
#             print(f"Clic forzado fallido: {e}")
#             return False
            
#     except Exception as e:
#         print(f"Error al intentar hacer clic en {selector}: {e}")
#         return False

# # Función para verificar y guardar la sesión con información del perfil
# async def save_session(context, page, screenshot_dir, sessions_dir, username):
#     # Guardar el estado de la sesión
#     print('Guardando estado de la sesión...')
#     session_state = await context.storage_state()
    
#     # Obtener información del perfil si estamos logueados
#     profile_info = {}
#     try:
#         is_logged_in = await wait_for_selector_or_continue(page, 'a[data-testid="AppTabBar_Home_Link"]', timeout=3000)
#         if is_logged_in:
#             # Intentar obtener el nombre de usuario desde la UI
#             try:
#                 username_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"] span span')
#                 if username_element:
#                     profile_info['displayName'] = await username_element.inner_text()
                
#                 handle_element = await page.query_selector('header button[data-testid="SideNav_AccountSwitcher_Button"] div[dir="ltr"][class*="r-1wvb978"] span')
#                 if handle_element:
#                     profile_info['handle'] = await handle_element.inner_text()
                
#                 # También guardar el nombre de usuario proporcionado para iniciar sesión
#                 profile_info['loginUsername'] = username
#             except Exception as e:
#                 print(f"Error al obtener información del perfil: {e}")
#     except Exception as e:
#         print(f"Error al verificar login: {e}")
    
#     # Añadir timestamp y metadatos al estado de la sesión
#     session_data = {
#         'timestamp': datetime.now().isoformat(),
#         'userAgent': await page.evaluate('navigator.userAgent'),
#         'platform': await page.evaluate('navigator.platform'),
#         'sessionState': session_state,
#         'profileInfo': profile_info
#     }
    
#     # Crear directorio de sesiones si no existe
#     sessions_dir.mkdir(exist_ok=True)
    
#     # Usar el nombre de usuario en el nombre del archivo si está disponible
#     user_identifier = profile_info.get('handle', '').replace('@', '') or username or 'unknown'
#     timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
#     session_file_path = sessions_dir / f'x_session_{user_identifier}_{timestamp_str}.json'
    
#     with open(session_file_path, 'w', encoding='utf-8') as f:
#         json.dump(session_data, f, indent=2)
#     print(f'Sesión guardada en: {session_file_path}')
    
#     # Tomar captura de pantalla del estado actual
#     await page.screenshot(path=str(screenshot_dir / f'session_saved_{user_identifier}_{timestamp_str}.png'))
    
#     return session_file_path

# # Función principal
# async def manual_login():
#     # Obtener credenciales de variables de entorno o solicitar al usuario
#     username = os.environ.get('X_USERNAME')
#     password = os.environ.get('X_PASSWORD')
    
#     if not username:
#         username = input('Introduce tu nombre de usuario o email de X: ')
#     if not password:
#         password = input('Introduce tu contraseña de X: ')
    
#     # Crear directorios necesarios
#     screenshot_dir = Path('screenshots')
#     screenshot_dir.mkdir(exist_ok=True)
    
#     sessions_dir = Path('sessions')
#     sessions_dir.mkdir(exist_ok=True)
    
#     async with async_playwright() as p:
#         # Lanzar el navegador con UI visible
#         browser = await p.chromium.launch(
#             headless=False,
#             slow_mo=50,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--no-sandbox',
#                 '--disable-web-security',
#                 '--disable-features=IsolateOrigins,site-per-process'
#             ]
#         )
        
#         # Crear contexto con configuración para evitar detección
#         context = await browser.new_context(
#             viewport={'width': 1280, 'height': 800},
#             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
#             locale='en-US',
#             timezone_id='America/New_York',
#             bypass_csp=True,
#             ignore_https_errors=True
#         )
        
#         # Crear una nueva página
#         page = await context.new_page()
        
#         try:
#             print('Navegando a X.com...')
#             await page.goto('https://x.com', wait_until='networkidle')
#             await human_delay()
            
#             # Tomar captura de pantalla de la página inicial
#             await page.screenshot(path=str(screenshot_dir / '1_initial_page.png'))
            
#             # Verificar si ya estamos en una sesión iniciada
#             is_logged_in = await wait_for_selector_or_continue(
#                 page, 
#                 'a[data-testid="AppTabBar_Home_Link"]', 
#                 timeout=3000, 
#                 message="No se detectó sesión iniciada, intentando iniciar sesión."
#             )
            
#             if is_logged_in:
#                 print("¡Ya hay una sesión iniciada! Guardando estado actual...")
#                 await save_session(context, page, screenshot_dir, sessions_dir, username)
#             else:
#                 # Intentar encontrar y hacer clic en el botón de login/sign in
#                 sign_in_found = False
                
#                 # Probar diferentes selectores para el botón de login/sign in
#                 sign_in_selectors = [
#                     'a[data-testid="loginButton"]',
#                     'a[href="/login"]',
#                     'a:has-text("Sign in")',
#                     'a:has-text("Iniciar sesión")'
#                 ]
                
#                 for selector in sign_in_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón de login ({selector})...')
#                         if await click_safely(page, selector):
#                             sign_in_found = True
#                             await human_delay(1000, 2000)
#                             break
                
#                 if not sign_in_found:
#                     print("No se pudo encontrar o hacer clic en el botón de login. Continuando de todos modos...")
                
#                 # Tomar captura de pantalla del estado actual
#                 await page.screenshot(path=str(screenshot_dir / '2_login_state.png'))
                
#                 # Comprobar si estamos en la pantalla de introducir usuario
#                 username_input_found = False
#                 username_selectors = [
#                     'input[autocomplete="username"]',
#                     'input[name="text"]',
#                     'input[class*="r-30o5oe"]'
#                 ]
                
#                 for selector in username_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Campo de usuario encontrado: {selector}')
#                         await move_mouse_realistic(page, selector)
#                         await human_delay()
#                         await type_human_like(page, selector, username)
#                         await human_delay(1000, 2000)
#                         username_input_found = True
#                         break
                
#                 if not username_input_found:
#                     print("No se encontró el campo de usuario. Por favor, introdúcelo manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas introducido el nombre de usuario manualmente...")
                
#                 # NUEVO: Soporte mejorado para el botón Next/Siguiente
#                 next_button_found = False
                
#                 # Lista ampliada de selectores para "Next" / "Siguiente"
#                 next_selectors = [
#                     'button:has-text("Next")',
#                     'button:has-text("Siguiente")',
#                     'button[type="button"]:has(span:has-text("Next"))',
#                     'button[type="button"]:has(span:has-text("Siguiente"))',
#                     'div[role="button"]:has-text("Next")',
#                     'div[role="button"]:has-text("Siguiente")',
#                     'button[role="button"]:has(span:has-text("Next"))',
#                     'button[role="button"]:has(span:has-text("Siguiente"))'
#                 ]
                
#                 for selector in next_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón Next/Siguiente: {selector}')
#                         if await click_safely(page, selector):
#                             next_button_found = True
#                             await human_delay(1000, 2000)
#                             break
                
#                 if not next_button_found:
#                     print("No se encontró el botón Next/Siguiente. Por favor, avanza manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas avanzado a la pantalla de contraseña...")
                
#                 # Tomar captura de pantalla después de introducir el usuario
#                 await page.screenshot(path=str(screenshot_dir / '3_after_username.png'))
                
#                 # Comprobar si estamos en la pantalla de contraseña
#                 password_input_found = False
#                 password_selectors = [
#                     'input[name="password"]',
#                     'input[type="password"]',
#                     'input[autocomplete="current-password"]'
#                 ]
                
#                 for selector in password_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Campo de contraseña encontrado: {selector}')
#                         await move_mouse_realistic(page, selector)
#                         await human_delay()
#                         await type_human_like(page, selector, password)
#                         await human_delay(1000, 2000)
#                         password_input_found = True
#                         break
                
#                 if not password_input_found:
#                     print("No se encontró el campo de contraseña. Por favor, introdúcelo manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas introducido la contraseña manualmente...")
                
#                 # Intentar hacer clic en el botón Log in
#                 login_button_found = False
#                 login_selectors = [
#                     'button:has-text("Log in")',
#                     'button:has-text("Iniciar sesión")',
#                     'div[role="button"]:has-text("Log in")',
#                     'div[role="button"]:has-text("Iniciar sesión")',
#                     'button[type="button"]:has(span:has-text("Log in"))',
#                     'button[type="button"]:has(span:has-text("Iniciar sesión"))'
#                 ]
                
#                 for selector in login_selectors:
#                     if await wait_for_selector_or_continue(page, selector, timeout=3000):
#                         print(f'Haciendo clic en el botón Log in: {selector}')
#                         if await click_safely(page, selector):
#                             login_button_found = True
#                             await human_delay(2000, 4000)
#                             break
                
#                 if not login_button_found:
#                     print("No se encontró el botón Log in. Por favor, inicia sesión manualmente.")
#                     manual_action = input("Presiona Enter cuando hayas iniciado sesión manualmente...")
                
#                 # Tomar captura de pantalla después de iniciar sesión
#                 await page.screenshot(path=str(screenshot_dir / '4_after_password.png'))
            
#             # Mensaje para el usuario
#             print('\n============= ATENCIÓN =============')
#             print('El navegador permanecerá abierto para que puedas:')
#             print('- Resolver cualquier captcha que aparezca')
#             print('- Navegar manualmente si lo necesitas')
#             print('- Completar cualquier paso adicional necesario')
#             print('El script esperará hasta que indiques que quieres guardar la sesión.')
#             print('=====================================\n')
            
#             # Esperar a que el usuario indique que quiere guardar la sesión
#             while True:
#                 action = input('\n¿Qué deseas hacer? (guardar/esperar/salir): ')
                
#                 if action.lower() == 'guardar':
#                     # Verificar si el login fue exitoso antes de guardar
#                     try:
#                         await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
#                         print('Sesión verificada correctamente. Guardando...')
#                     except TimeoutError:
#                         print('Advertencia: No se puede verificar que el login sea exitoso.')
#                         verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
#                         if verify_anyway.lower() != 's':
#                             print('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
#                             continue
                    
#                     # Guardar la sesión
#                     session_path = await save_session(context, page, screenshot_dir, sessions_dir, username)
#                     print(f'Sesión guardada exitosamente en: {session_path}')
                    
#                     continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
#                     if continue_browsing.lower() != 's':
#                         break
                
#                 elif action.lower() == 'esperar':
#                     wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
#                     print(f'Esperando {wait_time} segundos...')
#                     await asyncio.sleep(wait_time)
                
#                 elif action.lower() == 'salir':
#                     save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
#                     if save_before_exit.lower() == 's':
#                         await save_session(context, page, screenshot_dir, sessions_dir, username)
#                     break
                
#                 else:
#                     print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
#             print('Cerrando navegador...')
            
#         except Exception as error:
#             print('Ocurrió un error:', error)
#             await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
#             print('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
#             # Intentar guardar la sesión incluso si hay un error
#             try:
#                 save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
#                 if save_anyway.lower() == 's':
#                     await save_session(context, page, screenshot_dir, sessions_dir, username)
#             except Exception as save_error:
#                 print(f'Error al guardar la sesión: {save_error}')
        
#         finally:
#             await browser.close()

# # Ejecutar la función principal
# if __name__ == "__main__":
#     asyncio.run(manual_login())


# import os
# import json
# import time
# import random
# import asyncio
# from datetime import datetime
# from pathlib import Path
# from playwright.async_api import async_playwright, TimeoutError

# # Función para agregar retraso de aspecto humano (tiempo variable)
# async def human_delay(min_ms=500, max_ms=2000):
#     delay = random.uniform(min_ms, max_ms) / 1000
#     await asyncio.sleep(delay)

# # Función para simular movimiento de ratón realista
# async def move_mouse_realistic(page, target_selector):
#     # Obtener la posición del elemento
#     try:
#         element = await page.query_selector(target_selector)
#         if not element:
#             return False
        
#         box = await element.bounding_box()
#         if not box:
#             return False
        
#         # Calcular posición objetivo (ligeramente aleatorizada dentro del elemento)
#         target_x = box["x"] + box["width"] * (0.3 + random.random() * 0.4)
#         target_y = box["y"] + box["height"] * (0.3 + random.random() * 0.4)
        
#         # Obtener posición actual del ratón o utilizar una posición de inicio predeterminada
#         current_x = 500 + random.random() * 200
#         current_y = 300 + random.random() * 100
        
#         # Número de pasos para el movimiento (más pasos = movimiento más suave)
#         steps = 10 + int(random.random() * 15)
        
#         # Puntos de control de curva Bezier para una curva natural
#         cp1x = current_x + (target_x - current_x) * (0.2 + random.random() * 0.3)
#         cp1y = current_y + (target_y - current_y) * (0.3 + random.random() * 0.4)
#         cp2x = current_x + (target_x - current_x) * (0.7 + random.random() * 0.2)
#         cp2y = current_y + (target_y - current_y) * (0.7 + random.random() * 0.2)
        
#         # Realizar el movimiento en pasos
#         for i in range(steps + 1):
#             t = i / steps
            
#             # Fórmula de curva Bezier para bezier cúbico
#             t_squared = t * t
#             t_cubed = t_squared * t
#             t_complement = 1 - t
#             t_complement_squared = t_complement * t_complement
#             t_complement_cubed = t_complement_squared * t_complement
            
#             x = t_complement_cubed * current_x + \
#                 3 * t_complement_squared * t * cp1x + \
#                 3 * t_complement * t_squared * cp2x + \
#                 t_cubed * target_x
                    
#             y = t_complement_cubed * current_y + \
#                 3 * t_complement_squared * t * cp1y + \
#                 3 * t_complement * t_squared * cp2y + \
#                 t_cubed * target_y
            
#             await page.mouse.move(x, y)
            
#             # Añadir pequeño retraso aleatorio entre movimientos
#             await asyncio.sleep(0.01 + random.random() * 0.03)
        
#         return True
#     except Exception as e:
#         print(f"Error en el movimiento del ratón: {e}")
#         return False

# # Función para escribir texto con velocidad variable como un humano
# async def type_human_like(page, selector, text):
#     try:
#         await page.focus(selector)
        
#         # Borrar cualquier texto existente primero
#         await page.fill(selector, '')
#         await human_delay(200, 600)
        
#         # Escribir cada carácter con retraso variable
#         for char in text:
#             await page.type(selector, char, delay=50 + random.randint(50, 150))
            
#             # Ocasionalmente hacer una pausa como lo haría un humano
#             if random.random() < 0.2:
#                 await human_delay(200, 1000)
#     except Exception as e:
#         print(f"Error al escribir texto: {e}")
#         # Intentar una alternativa si el método normal falla
#         try:
#             await page.fill(selector, text)
#         except Exception:
#             print("No se pudo escribir el texto.")

# # Función para esperar a un selector con posibilidad de continuar si no aparece
# async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
#     try:
#         await page.wait_for_selector(selector, state='visible', timeout=timeout)
#         return True
#     except TimeoutError:
#         if message:
#             print(message)
#         return False

# # Función para verificar y guardar la sesión en cualquier punto
# async def save_session(context, page, screenshot_dir, sessions_dir):
#     # Guardar el estado de la sesión
#     print('Guardando estado de la sesión...')
#     session_state = await context.storage_state()
    
#     # Añadir timestamp y metadatos al estado de la sesión
#     session_data = {
#         'timestamp': datetime.now().isoformat(),
#         'userAgent': await page.evaluate('navigator.userAgent'),
#         'platform': await page.evaluate('navigator.platform'),
#         'sessionState': session_state
#     }
    
#     # Crear directorio de sesiones si no existe
#     sessions_dir.mkdir(exist_ok=True)
    
#     # Guardar datos de sesión
#     timestamp_str = datetime.now().isoformat().replace(':', '-').replace('.', '-')
#     session_file_path = sessions_dir / f'x_session_{timestamp_str}.json'
#     with open(session_file_path, 'w', encoding='utf-8') as f:
#         json.dump(session_data, f, indent=2)
#     print(f'Sesión guardada en: {session_file_path}')
    
#     # Tomar captura de pantalla del estado actual
#     await page.screenshot(path=str(screenshot_dir / f'session_saved_{timestamp_str}.png'))
    
#     return session_file_path

# # Función principal
# async def manual_login():
#     # Obtener credenciales de variables de entorno o solicitar al usuario
#     username = os.environ.get('X_USERNAME')
#     password = os.environ.get('X_PASSWORD')
    
#     if not username:
#         username = input('Introduce tu nombre de usuario o email de X: ')
#     if not password:
#         password = input('Introduce tu contraseña de X: ')
    
#     # Crear directorios necesarios
#     screenshot_dir = Path('screenshots')
#     screenshot_dir.mkdir(exist_ok=True)
    
#     sessions_dir = Path('sessions')
#     sessions_dir.mkdir(exist_ok=True)
    
#     async with async_playwright() as p:
#         # Lanzar el navegador con UI visible
#         browser = await p.chromium.launch(
#             headless=False,
#             slow_mo=50,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--no-sandbox',
#                 '--disable-web-security',
#                 '--disable-features=IsolateOrigins,site-per-process'
#             ]
#         )
        
#         # Crear contexto con configuración para evitar detección
#         context = await browser.new_context(
#             viewport={'width': 1280, 'height': 800},
#             user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
#             locale='en-US',
#             timezone_id='America/New_York',
#             bypass_csp=True,
#             ignore_https_errors=True
#         )
        
#         # Crear una nueva página
#         page = await context.new_page()
        
#         try:
#             print('Navegando a X.com...')
#             await page.goto('https://x.com', wait_until='networkidle')
#             await human_delay()
            
#             # Tomar captura de pantalla de la página inicial
#             await page.screenshot(path=str(screenshot_dir / '1_initial_page.png'))
            
#             # Verificar si ya estamos en una sesión iniciada
#             is_logged_in = await wait_for_selector_or_continue(
#                 page, 
#                 'a[data-testid="AppTabBar_Home_Link"]', 
#                 timeout=3000, 
#                 message="No se detectó sesión iniciada, intentando iniciar sesión."
#             )
            
#             if is_logged_in:
#                 print("¡Ya hay una sesión iniciada! Guardando estado actual...")
#                 await save_session(context, page, screenshot_dir, sessions_dir)
#             else:
#                 # Intentar encontrar y hacer clic en el botón de login
#                 login_button_found = await wait_for_selector_or_continue(
#                     page, 
#                     'a[data-testid="loginButton"]', 
#                     timeout=5000, 
#                     message="No se encontró el botón de login, comprobando si ya estamos en la pantalla de login."
#                 )
                
#                 if login_button_found:
#                     print('Haciendo clic en el botón de login...')
#                     await move_mouse_realistic(page, 'a[data-testid="loginButton"]')
#                     await human_delay()
#                     await page.click('a[data-testid="loginButton"]')
#                     await human_delay()
                
#                 # Tomar captura de pantalla del estado actual
#                 await page.screenshot(path=str(screenshot_dir / '2_login_state.png'))
                
#                 # Comprobar si estamos en la pantalla de introducir usuario
#                 username_input_found = await wait_for_selector_or_continue(
#                     page, 
#                     'input[autocomplete="username"]', 
#                     timeout=5000, 
#                     message="No se encontró el campo de usuario, comprobando otras pantallas..."
#                 )
                
#                 if username_input_found:
#                     print('Introduciendo nombre de usuario...')
#                     await move_mouse_realistic(page, 'input[autocomplete="username"]')
#                     await human_delay()
#                     await type_human_like(page, 'input[autocomplete="username"]', username)
#                     await human_delay()
                    
#                     # Intentar hacer clic en el botón Next
#                     next_button_found = False
#                     for next_selector in ['div[role="button"]:text("Next")', 'div[role="button"]:text("Siguiente")', 'button:has-text("Next")']:
#                         if await wait_for_selector_or_continue(page, next_selector, timeout=3000):
#                             print(f'Haciendo clic en el botón Next ({next_selector})...')
#                             await move_mouse_realistic(page, next_selector)
#                             await human_delay()
#                             await page.click(next_selector)
#                             await human_delay(1000, 2000)
#                             next_button_found = True
#                             break
                    
#                     if not next_button_found:
#                         print("No se encontró el botón Next. Puedes continuar manualmente.")
                
#                 # Tomar captura de pantalla del estado actual
#                 await page.screenshot(path=str(screenshot_dir / '3_after_username.png'))
                
#                 # Comprobar si estamos en la pantalla de contraseña
#                 password_input_found = await wait_for_selector_or_continue(
#                     page, 
#                     'input[name="password"]', 
#                     timeout=5000, 
#                     message="No se encontró el campo de contraseña, comprobando otras pantallas..."
#                 )
                
#                 if password_input_found:
#                     print('Introduciendo contraseña...')
#                     await move_mouse_realistic(page, 'input[name="password"]')
#                     await human_delay()
#                     await type_human_like(page, 'input[name="password"]', password)
#                     await human_delay()
                    
#                     # Intentar hacer clic en el botón Log in
#                     login_button_found = False
#                     for login_selector in ['div[role="button"]:text("Log in")', 'div[role="button"]:text("Iniciar sesión")', 'button:has-text("Log in")']:
#                         if await wait_for_selector_or_continue(page, login_selector, timeout=3000):
#                             print(f'Haciendo clic en el botón Log in ({login_selector})...')
#                             await move_mouse_realistic(page, login_selector)
#                             await human_delay()
#                             await page.click(login_selector)
#                             await human_delay(1000, 2000)
#                             login_button_found = True
#                             break
                    
#                     if not login_button_found:
#                         print("No se encontró el botón Log in. Puedes continuar manualmente.")
                
#                 # Tomar captura de pantalla del estado actual
#                 await page.screenshot(path=str(screenshot_dir / '4_after_password.png'))
            
#             # Mensaje para el usuario
#             print('\n============= ATENCIÓN =============')
#             print('El navegador permanecerá abierto para que puedas:')
#             print('- Resolver cualquier captcha que aparezca')
#             print('- Navegar manualmente si lo necesitas')
#             print('- Completar cualquier paso adicional necesario')
#             print('El script esperará hasta que indiques que quieres guardar la sesión.')
#             print('=====================================\n')
            
#             # Esperar a que el usuario indique que quiere guardar la sesión
#             while True:
#                 action = input('\n¿Qué deseas hacer? (guardar/esperar/salir): ')
                
#                 if action.lower() == 'guardar':
#                     # Verificar si el login fue exitoso antes de guardar
#                     try:
#                         await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
#                         print('Sesión verificada correctamente. Guardando...')
#                     except TimeoutError:
#                         print('Advertencia: No se puede verificar que el login sea exitoso.')
#                         verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
#                         if verify_anyway.lower() != 's':
#                             print('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
#                             continue
                    
#                     # Guardar la sesión
#                     session_path = await save_session(context, page, screenshot_dir, sessions_dir)
#                     print(f'Sesión guardada exitosamente en: {session_path}')
                    
#                     continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
#                     if continue_browsing.lower() != 's':
#                         break
                
#                 elif action.lower() == 'esperar':
#                     wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
#                     print(f'Esperando {wait_time} segundos...')
#                     await asyncio.sleep(wait_time)
                
#                 elif action.lower() == 'salir':
#                     save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
#                     if save_before_exit.lower() == 's':
#                         await save_session(context, page, screenshot_dir, sessions_dir)
#                     break
                
#                 else:
#                     print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
#             print('Cerrando navegador...')
            
#         except Exception as error:
#             print('Ocurrió un error:', error)
#             await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
#             print('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
#             # Intentar guardar la sesión incluso si hay un error
#             try:
#                 save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
#                 if save_anyway.lower() == 's':
#                     await save_session(context, page, screenshot_dir, sessions_dir)
#             except Exception as save_error:
#                 print(f'Error al guardar la sesión: {save_error}')
        
#         finally:
#             await browser.close()

# # Ejecutar la función principal
# if __name__ == "__main__":
#     asyncio.run(manual_login())