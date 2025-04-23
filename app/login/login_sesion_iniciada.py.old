import os
import json
import time
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

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

# Función para mostrar un banner de inicio
def show_banner():
    print("\n" + "="*60)
    print("   INICIADOR DE SESIÓN X.COM CON SESIONES GUARDADAS")
    print("="*60)
    print(" Este script permite cargar sesiones previamente guardadas")
    print(" para conectarse a X.com sin necesidad de iniciar sesión")
    print(" ni resolver captchas nuevamente.")
    print("-"*60 + "\n")

# Función para cargar las cuentas desde el archivo JSON
def load_accounts():
    accounts_file = Path('login_accounts.json')
    if not accounts_file.exists():
        logger.warning("No se encontró el archivo login_accounts.json.")
        return []
    
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

# Función para seleccionar una cuenta de la lista (similar al script original)
def select_account(accounts):
    if not accounts:
        logger.warning("No hay cuentas disponibles en el archivo login_accounts.json")
        return None
    
    print("\n=== Cuentas Disponibles ===")
    for i, account in enumerate(accounts):
        username = account.get("username", "Sin nombre de usuario")
        description = account.get("description", "")
        print(f"{i+1}. {username} - {description}")
    
    while True:
        try:
            selection = input("\nSelecciona el número de la cuenta que quieres usar (o 'q' para salir): ")
            if selection.lower() == 'q':
                return None
            
            index = int(selection) - 1
            if 0 <= index < len(accounts):
                selected_account = accounts[index]
                return selected_account.get("username")
            else:
                print(f"Error: Por favor, selecciona un número entre 1 y {len(accounts)}")
        except ValueError:
            print("Error: Por favor, introduce un número válido")

# Función para buscar la sesión más reciente de un usuario específico
def find_user_session(username):
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        raise Exception('Directorio de sesiones no encontrado.')
    
    # Patrón de búsqueda para las sesiones del usuario
    # Formato esperado: x_session_{username}_{date}.json
    session_pattern = f'x_session_{username}_*.json'
    
    # Buscar archivos que coincidan con el patrón
    matching_sessions = list(sessions_dir.glob(session_pattern))
    
    if not matching_sessions:
        logger.warning(f"No se encontraron sesiones para el usuario {username}")
        return None
    
    # Ordenar por tiempo de modificación (más reciente primero)
    matching_sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Devolver la sesión más reciente
    return matching_sessions[0]

# Función para cargar el archivo de sesión
def load_session(username=None, specific_file=None):
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        raise Exception('Directorio de sesiones no encontrado.')
    
    if specific_file:
        # Si se especifica un archivo concreto, usarlo
        session_path = sessions_dir / specific_file
        if not session_path.exists():
            raise Exception(f'Archivo de sesión no encontrado: {specific_file}')
    elif username:
        # Si se especifica un usuario, buscar su sesión más reciente
        session_path = find_user_session(username)
        if not session_path:
            raise Exception(f'No se encontraron sesiones para el usuario {username}')
    else:
        # Si no se especifica ni usuario ni archivo, usar la sesión más reciente
        session_files = []
        for file in sessions_dir.glob('x_session_*.json'):
            session_files.append({
                'name': file.name,
                'path': file,
                'time': file.stat().st_mtime
            })
        
        if len(session_files) == 0:
            raise Exception('No se encontraron archivos de sesión.')
        
        # Ordenar por tiempo (más reciente primero)
        session_files.sort(key=lambda x: x['time'], reverse=True)
        session_path = session_files[0]['path']
    
    # Cargar el archivo de sesión
    with open(session_path, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    logger.info(f'Sesión cargada desde: {session_path.name}')
    
    # Verificar la edad de la sesión
    session_timestamp = datetime.fromisoformat(session_data['timestamp'])
    session_age_hours = (datetime.now() - session_timestamp).total_seconds() / 3600
    
    if session_age_hours > 12:
        logger.warning(f'Advertencia: La sesión tiene {session_age_hours:.1f} horas y podría haber expirado.')
    else:
        logger.info(f'La sesión tiene {session_age_hours:.1f} horas de antigüedad.')
    
    return session_data

# Función para analizar la estructura HTML y encontrar indicadores de sesión
async def analyze_page_structure(page):
    # Obtener el HTML completo de la página
    html_content = await page.content()
    
    # Analizar con BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Variables para almacenar la información
    session_indicators = []
    profile_info = {}
    
    # Buscar elementos que indiquen sesión iniciada
    logger.info("\nAnalizando estructura de la página...")
    
    # 1. Buscar enlaces de navegación principal (Home, Profile, etc.)
    navigation_links = []
    
    # Buscar enlaces con etiqueta aria-label
    for link in soup.find_all('a', attrs={'aria-label': True}):
        label = link.get('aria-label')
        href = link.get('href', '')
        navigation_links.append({'label': label, 'href': href})
        if label in ['Home', 'Profile', 'Messages', 'Notifications']:
            session_indicators.append(f"Enlace de navegación: {label}")
            
            # Si es el perfil, intentar obtener el nombre de usuario
            if label == 'Profile' and href and href.startswith('/'):
                profile_info['username'] = href.strip('/')
    
    # 2. Buscar el botón de cambio de cuenta en la barra lateral
    account_switcher = soup.find(attrs={'data-testid': 'SideNav_AccountSwitcher_Button'})
    if account_switcher:
        session_indicators.append("Botón de cambio de cuenta encontrado")
        
        # Intentar extraer nombre y handle
        display_name_el = account_switcher.select_one('div[dir="ltr"] span span')
        if display_name_el and display_name_el.text:
            profile_info['display_name'] = display_name_el.text.strip()
            
        handle_el = account_switcher.select_one('div[dir="ltr"][class*="r-1wvb978"] span')
        if handle_el and handle_el.text:
            profile_info['handle'] = handle_el.text.strip()
    
    # 3. Buscar timeline de inicio
    timeline = soup.find(attrs={'aria-label': 'Home timeline'})
    if timeline:
        session_indicators.append("Timeline de inicio encontrado")
    
    # 4. Buscar campo de búsqueda
    search_input = soup.find('input', attrs={'aria-label': 'Search query'})
    if search_input:
        session_indicators.append("Campo de búsqueda encontrado")
    
    # 5. Buscar el campo "What's happening?" para tweetear
    tweet_input = soup.find(attrs={'aria-label': ["What's happening?", "¿Qué está pasando?"]})
    if tweet_input:
        session_indicators.append("Campo para twittear encontrado")
    
    # 6. Buscar menú de navegación lateral
    side_nav = soup.find(attrs={'data-testid': 'sidebarColumn'})
    if side_nav:
        session_indicators.append("Menú de navegación lateral encontrado")
    
    # 7. Buscar logo de X en la esquina superior
    x_logo = soup.find('h1', attrs={'role': 'heading'})
    if x_logo and x_logo.find('svg'):
        session_indicators.append("Logo de X encontrado")
    
    # Devolver resultados
    return {
        'indicators': session_indicators,
        'profile_info': profile_info,
        'is_logged_in': len(session_indicators) > 0,
        'navigation_links': navigation_links
    }

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

async def open_browser_with_session(headless=False, url=None, username=None, specific_session=None, keep_open=True, update_session=True):
    """
    Abre un navegador con una sesión guardada de X.com.
    
    Args:
        headless (bool): Si se ejecuta en modo sin interfaz gráfica.
        url (str): URL a la que navegar (por defecto: https://x.com/home).
        username (str): Nombre de usuario específico para cargar su sesión.
        specific_session (str): Nombre específico del archivo de sesión a usar.
        keep_open (bool): Si mantener el navegador abierto hasta que el usuario lo cierre.
        update_session (bool): Si actualizar el archivo de sesión al cerrar o periódicamente.
    """
    # Cargar la sesión
    session_data = load_session(username, specific_session)
    session_path = None
    
    # Obtener la ruta completa del archivo de sesión
    sessions_dir = Path('sessions')
    if specific_session:
        session_path = sessions_dir / specific_session
    elif username:
        session_path = find_user_session(username)
    else:
        # Encontrar la sesión más reciente
        session_files = sorted(sessions_dir.glob('x_session_*.json'), 
                              key=lambda x: x.stat().st_mtime, 
                              reverse=True)
        if session_files:
            session_path = session_files[0]
    
    # Extraer el nombre de usuario de los datos de la sesión si no se proporcionó
    if not username:
        # Intentar obtener de profileInfo
        if 'profileInfo' in session_data and 'loginUsername' in session_data['profileInfo']:
            username = session_data['profileInfo']['loginUsername']
        else:
            # Intentar extraer del nombre del archivo
            if session_path:
                file_name = session_path.stem  # x_session_username_date
                parts = file_name.split('_')
                if len(parts) > 2:
                    username = parts[2]  # Asumiendo formato x_session_username_date
            
    # Crear directorio para capturas de pantalla si no existe
    screenshot_dir = Path('browser_screenshots')
    screenshot_dir.mkdir(exist_ok=True)
    
    # Obtener configuración de proxy desde variables de entorno
    proxy_config = get_proxy_config()
    
    # Iniciar el navegador
    async with async_playwright() as p:
        logger.info("Iniciando navegador...")
        
        # Argumentos del navegador para evitar detección
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=20,
            args=browser_args
        )
        
        # Parámetros del contexto
        context_params = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': session_data.get('userAgent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'storage_state': session_data['sessionState'],
            'bypass_csp': True,
            'ignore_https_errors': True
        }
        
        # Añadir proxy si está configurado
        if proxy_config:
            context_params['proxy'] = proxy_config
        
        # Crear contexto con el estado de sesión guardado
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
            # Navegar a la URL especificada o a X.com por defecto
            target_url = url if url else 'https://x.com/home'
            logger.info(f"Navegando a: {target_url}")
            
            try:
                # Intentar con timeout más corto y sin esperar networkidle
                await page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
            except Exception as e:
                logger.warning(f"Advertencia al navegar: {e}")
                logger.info("Continuando de todos modos...")
            
            # Esperar un momento para que la página se estabilice
            await asyncio.sleep(3)
            
            # Tomar captura de pantalla para verificar estado
            screenshot_path = str(screenshot_dir / f'session_loaded_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
            await page.screenshot(path=screenshot_path)
            logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
            
            # Usar BeautifulSoup para analizar la estructura de la página
            page_analysis = await analyze_page_structure(page)
            
            # Mostrar indicadores encontrados
            if page_analysis['indicators']:
                print("\nIndicadores de sesión encontrados:")
                for indicator in page_analysis['indicators']:
                    print(f"✓ {indicator}")
                
                # Mostrar información del perfil si está disponible
                if page_analysis['profile_info']:
                    print("\nInformación del perfil detectada:")
                    for key, value in page_analysis['profile_info'].items():
                        print(f"  {key}: {value}")
                
                print("\n Estás conectado en X.com correctamente")
            else:
                # Verificación secundaria con selectores específicos
                logger.warning("No se encontraron indicadores mediante análisis HTML.")
                print("Intentando verificación secundaria con selectores específicos...")
                
                # Intentar detectar la sesión con selectores específicos
                session_active = False
                login_indicators = [
                    'a[data-testid="AppTabBar_Home_Link"]',
                    'a[data-testid="AppTabBar_Profile_Link"]',
                    'a[aria-label="Profile"][role="link"]',
                    '[data-testid="SideNav_AccountSwitcher_Button"]',
                    'div[aria-label="Home timeline"]',
                    'div[data-testid="primaryColumn"]'
                ]
                
                for selector in login_indicators:
                    try:
                        element = await page.wait_for_selector(selector, timeout=2000)
                        if element:
                            session_active = True
                            print(f"✓ Indicador de sesión encontrado: {selector}")
                            break
                    except Exception:
                        continue
                
                if session_active:
                    print("\n Sesión verificada mediante selectores específicos")
                else:
                    print("\n No se pudo verificar la sesión. Verifica manualmente si estás conectado.")
            
            if keep_open:
                print("\nEl navegador permanecerá abierto hasta que presiones Enter para cerrarlo.")
                print("Puedes navegar manualmente mientras tanto.")
                
                if update_session and session_path:
                    print("La sesión se actualizará: primera actualización en 1 minuto, luego cada 5 minutos.")
                
                # Banderas para controlar las actualizaciones
                first_update_done = False
                exit_requested = False
                
                # Programar la primera actualización después de 1 minuto
                first_update_time = time.time() + 60  # 1 minuto
                next_update_time = first_update_time
                
                # Utilizar asyncio.run_in_executor para no bloquear
                loop = asyncio.get_event_loop()
                input_future = loop.run_in_executor(None, input, "Presiona Enter para cerrar el navegador cuando hayas terminado...\n")
                
                # Bucle principal para mantener el navegador abierto y actualizar periódicamente
                while not exit_requested:
                    # Verificar si hay entrada del usuario (sin bloquear)
                    if input_future.done():
                        exit_requested = True
                        continue
                    
                    # Verificar si es tiempo de actualizar
                    current_time = time.time()
                    if current_time >= next_update_time and update_session and session_path:
                        # Actualizar la sesión
                        logger.info(f"{'Primera actualización' if not first_update_done else 'Actualizando'} de la sesión...")
                        await update_session_file(context, page, session_path, username)
                        
                        if not first_update_done:
                            # Después de la primera actualización, programar las siguientes cada 5 minutos
                            first_update_done = True
                            next_update_time = current_time + 300  # 5 minutos
                        else:
                            # Programar la siguiente actualización en 5 minutos
                            next_update_time = current_time + 300  # 5 minutos
                    
                    # Pequeña pausa para no sobrecargar la CPU
                    await asyncio.sleep(0.5)
            else:
                # Esperar un momento antes de cerrar
                await asyncio.sleep(5)
            
            # Actualizar la sesión antes de cerrar si está habilitado
            if update_session and session_path:
                logger.info("Actualizando sesión antes de cerrar...")
                await update_session_file(context, page, session_path, username)
        
        except Exception as e:
            logger.error(f"Error durante la navegación: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            await browser.close()
            logger.info("Navegador cerrado.")

# Función auxiliar para actualizar el archivo de sesión
async def update_session_file(context, page, session_path, username):
    """
    Actualiza el archivo de sesión con el estado actual.
    
    Args:
        context: Contexto del navegador Playwright
        page: Página actual de Playwright
        session_path: Ruta al archivo de sesión original
        username: Nombre de usuario asociado a la sesión
    """
    try:
        logger.info('Actualizando estado de la sesión...')
        session_state = await context.storage_state()
        
        # Obtener información del perfil usando BeautifulSoup
        profile_info = {}
        try:
            page_analysis = await analyze_page_structure(page)
            if page_analysis['is_logged_in']:
                profile_info = page_analysis['profile_info']
                # Asegurar que mantenemos el nombre de usuario original
                if username:
                    profile_info['loginUsername'] = username
        except Exception as e:
            logger.error(f"Error al obtener información del perfil: {e}")
        
        # Cargar datos originales para mantener el timestamp de creación y otros metadatos
        with open(session_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        # Actualizar solo el estado de sesión y la información de perfil
        current_time = datetime.now()
        updated_data = {
            'timestamp': original_data.get('timestamp', current_time.isoformat()),  # Mantener timestamp original
            'timestamp_updated': current_time.isoformat(),  # Añadir timestamp de actualización
            'userAgent': await page.evaluate('navigator.userAgent'),
            'platform': await page.evaluate('navigator.platform'),
            'sessionState': session_state,
            'profileInfo': profile_info
        }
        
        # Guardar la sesión actualizada
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2)
        
        logger.info(f'Sesión actualizada exitosamente en: {session_path}')
        return True
    except Exception as e:
        logger.error(f'Error al actualizar sesión: {e}')
        return False


# Función para listar todas las sesiones disponibles
def list_sessions():
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        logger.warning("No hay directorio de sesiones.")
        return
    
    session_files = []
    for file in sessions_dir.glob('x_session_*.json'):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            timestamp = datetime.fromisoformat(data['timestamp'])
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            
            # Intentar extraer el nombre de usuario del archivo
            filename = file.name
            username = "Desconocido"
            
            # Intentar extraer el nombre de usuario de la información de perfil
            profile_info = data.get('profileInfo', {})
            if profile_info:
                username = profile_info.get('loginUsername', username)
            
            session_files.append({
                'name': file.name,
                'username': username,
                'time': timestamp,
                'age_hours': age_hours
            })
        except Exception as e:
            logger.error(f"Error al leer {file.name}: {e}")
    
    if not session_files:
        logger.warning("No se encontraron archivos de sesión.")
        return
    
    # Ordenar por tiempo (más reciente primero)
    session_files.sort(key=lambda x: x['time'], reverse=True)
    
    print("\n=== Sesiones disponibles ===")
    for i, session in enumerate(session_files):
        status = "🟢" if session['age_hours'] < 12 else "🟠" if session['age_hours'] < 24 else "🔴"
        print(f"{i+1}. {status} {session['username']} - {session['name']} - {session['time'].strftime('%Y-%m-%d %H:%M')} ({session['age_hours']:.1f} horas)")
    print("")

# Punto de entrada del script
if __name__ == "__main__":
    show_banner()
    
    parser = argparse.ArgumentParser(description='Abre un navegador con una sesión guardada de X.com')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    parser.add_argument('--url', type=str, help='URL a la que navegar (por defecto: https://x.com/home)')
    parser.add_argument('--session', type=str, help='Nombre específico del archivo de sesión a usar')
    parser.add_argument('--list', action='store_true', help='Listar todas las sesiones disponibles')
    parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de cargar')
    parser.add_argument('--account', type=str, help='Nombre de usuario específico para cargar su sesión')
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions()
    elif args.account:
        # Si se especifica una cuenta directamente por línea de comandos
        logger.info(f"Usando cuenta especificada: {args.account}")
        asyncio.run(open_browser_with_session(
            headless=args.headless,
            url=args.url,
            username=args.account,
            specific_session=args.session,
            keep_open=not args.autoclose
        ))
    elif args.session:
        # Si se especifica un archivo de sesión directamente
        logger.info(f"Usando archivo de sesión especificado: {args.session}")
        asyncio.run(open_browser_with_session(
            headless=args.headless,
            url=args.url,
            specific_session=args.session,
            keep_open=not args.autoclose
        ))
    else:
        # Por defecto, mostrar las cuentas disponibles para selección
        accounts = load_accounts()
        if accounts:
            selected_username = select_account(accounts)
            if selected_username:
                logger.info(f"Cuenta seleccionada: {selected_username}")
                asyncio.run(open_browser_with_session(
                    headless=args.headless,
                    url=args.url,
                    username=selected_username,
                    keep_open=not args.autoclose
                ))
            else:
                logger.warning("No se seleccionó ninguna cuenta. Saliendo...")
        else:
            # Si no hay cuentas, usar el comportamiento original
            logger.warning("No se encontraron cuentas en login_accounts.json. Utilizando la sesión más reciente...")
            asyncio.run(open_browser_with_session(
                headless=args.headless,
                url=args.url,
                keep_open=not args.autoclose
            ))

