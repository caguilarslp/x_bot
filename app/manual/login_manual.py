import os
import json
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError

# Función para agregar retraso de aspecto humano (tiempo variable)
async def human_delay(min_ms=500, max_ms=2000):
    delay = random.uniform(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)

# Función para simular movimiento de ratón realista
async def move_mouse_realistic(page, target_selector):
    # Obtener la posición del elemento
    try:
        element = await page.query_selector(target_selector)
        if not element:
            return False
        
        box = await element.bounding_box()
        if not box:
            return False
        
        # Calcular posición objetivo (ligeramente aleatorizada dentro del elemento)
        target_x = box["x"] + box["width"] * (0.3 + random.random() * 0.4)
        target_y = box["y"] + box["height"] * (0.3 + random.random() * 0.4)
        
        # Obtener posición actual del ratón o utilizar una posición de inicio predeterminada
        current_x = 500 + random.random() * 200
        current_y = 300 + random.random() * 100
        
        # Número de pasos para el movimiento (más pasos = movimiento más suave)
        steps = 10 + int(random.random() * 15)
        
        # Puntos de control de curva Bezier para una curva natural
        cp1x = current_x + (target_x - current_x) * (0.2 + random.random() * 0.3)
        cp1y = current_y + (target_y - current_y) * (0.3 + random.random() * 0.4)
        cp2x = current_x + (target_x - current_x) * (0.7 + random.random() * 0.2)
        cp2y = current_y + (target_y - current_y) * (0.7 + random.random() * 0.2)
        
        # Realizar el movimiento en pasos
        for i in range(steps + 1):
            t = i / steps
            
            # Fórmula de curva Bezier para bezier cúbico
            t_squared = t * t
            t_cubed = t_squared * t
            t_complement = 1 - t
            t_complement_squared = t_complement * t_complement
            t_complement_cubed = t_complement_squared * t_complement
            
            x = t_complement_cubed * current_x + \
                3 * t_complement_squared * t * cp1x + \
                3 * t_complement * t_squared * cp2x + \
                t_cubed * target_x
                    
            y = t_complement_cubed * current_y + \
                3 * t_complement_squared * t * cp1y + \
                3 * t_complement * t_squared * cp2y + \
                t_cubed * target_y
            
            await page.mouse.move(x, y)
            
            # Añadir pequeño retraso aleatorio entre movimientos
            await asyncio.sleep(0.01 + random.random() * 0.03)
        
        return True
    except Exception as e:
        print(f"Error en el movimiento del ratón: {e}")
        return False

# Función para escribir texto con velocidad variable como un humano
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
        print(f"Error al escribir texto: {e}")
        # Intentar una alternativa si el método normal falla
        try:
            await page.fill(selector, text)
        except Exception:
            print("No se pudo escribir el texto.")

# Función para esperar a un selector con posibilidad de continuar si no aparece
async def wait_for_selector_or_continue(page, selector, timeout=5000, message=None):
    try:
        await page.wait_for_selector(selector, state='visible', timeout=timeout)
        return True
    except TimeoutError:
        if message:
            print(message)
        return False

# Función para verificar y guardar la sesión en cualquier punto
async def save_session(context, page, screenshot_dir, sessions_dir):
    # Guardar el estado de la sesión
    print('Guardando estado de la sesión...')
    session_state = await context.storage_state()
    
    # Añadir timestamp y metadatos al estado de la sesión
    session_data = {
        'timestamp': datetime.now().isoformat(),
        'userAgent': await page.evaluate('navigator.userAgent'),
        'platform': await page.evaluate('navigator.platform'),
        'sessionState': session_state
    }
    
    # Crear directorio de sesiones si no existe
    sessions_dir.mkdir(exist_ok=True)
    
    # Guardar datos de sesión
    timestamp_str = datetime.now().isoformat().replace(':', '-').replace('.', '-')
    session_file_path = sessions_dir / f'x_session_{timestamp_str}.json'
    with open(session_file_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, indent=2)
    print(f'Sesión guardada en: {session_file_path}')
    
    # Tomar captura de pantalla del estado actual
    await page.screenshot(path=str(screenshot_dir / f'session_saved_{timestamp_str}.png'))
    
    return session_file_path

# Función principal
async def manual_login():
    # Obtener credenciales de variables de entorno o solicitar al usuario
    username = os.environ.get('X_USERNAME')
    password = os.environ.get('X_PASSWORD')
    
    if not username:
        username = input('Introduce tu nombre de usuario o email de X: ')
    if not password:
        password = input('Introduce tu contraseña de X: ')
    
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
        
        # Crear una nueva página
        page = await context.new_page()
        
        try:
            print('Navegando a X.com...')
            await page.goto('https://x.com', wait_until='networkidle')
            await human_delay()
            
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
                print("¡Ya hay una sesión iniciada! Guardando estado actual...")
                await save_session(context, page, screenshot_dir, sessions_dir)
            else:
                # Intentar encontrar y hacer clic en el botón de login
                login_button_found = await wait_for_selector_or_continue(
                    page, 
                    'a[data-testid="loginButton"]', 
                    timeout=5000, 
                    message="No se encontró el botón de login, comprobando si ya estamos en la pantalla de login."
                )
                
                if login_button_found:
                    print('Haciendo clic en el botón de login...')
                    await move_mouse_realistic(page, 'a[data-testid="loginButton"]')
                    await human_delay()
                    await page.click('a[data-testid="loginButton"]')
                    await human_delay()
                
                # Tomar captura de pantalla del estado actual
                await page.screenshot(path=str(screenshot_dir / '2_login_state.png'))
                
                # Comprobar si estamos en la pantalla de introducir usuario
                username_input_found = await wait_for_selector_or_continue(
                    page, 
                    'input[autocomplete="username"]', 
                    timeout=5000, 
                    message="No se encontró el campo de usuario, comprobando otras pantallas..."
                )
                
                if username_input_found:
                    print('Introduciendo nombre de usuario...')
                    await move_mouse_realistic(page, 'input[autocomplete="username"]')
                    await human_delay()
                    await type_human_like(page, 'input[autocomplete="username"]', username)
                    await human_delay()
                    
                    # Intentar hacer clic en el botón Next
                    next_button_found = False
                    for next_selector in ['div[role="button"]:text("Next")', 'div[role="button"]:text("Siguiente")', 'button:has-text("Next")']:
                        if await wait_for_selector_or_continue(page, next_selector, timeout=3000):
                            print(f'Haciendo clic en el botón Next ({next_selector})...')
                            await move_mouse_realistic(page, next_selector)
                            await human_delay()
                            await page.click(next_selector)
                            await human_delay(1000, 2000)
                            next_button_found = True
                            break
                    
                    if not next_button_found:
                        print("No se encontró el botón Next. Puedes continuar manualmente.")
                
                # Tomar captura de pantalla del estado actual
                await page.screenshot(path=str(screenshot_dir / '3_after_username.png'))
                
                # Comprobar si estamos en la pantalla de contraseña
                password_input_found = await wait_for_selector_or_continue(
                    page, 
                    'input[name="password"]', 
                    timeout=5000, 
                    message="No se encontró el campo de contraseña, comprobando otras pantallas..."
                )
                
                if password_input_found:
                    print('Introduciendo contraseña...')
                    await move_mouse_realistic(page, 'input[name="password"]')
                    await human_delay()
                    await type_human_like(page, 'input[name="password"]', password)
                    await human_delay()
                    
                    # Intentar hacer clic en el botón Log in
                    login_button_found = False
                    for login_selector in ['div[role="button"]:text("Log in")', 'div[role="button"]:text("Iniciar sesión")', 'button:has-text("Log in")']:
                        if await wait_for_selector_or_continue(page, login_selector, timeout=3000):
                            print(f'Haciendo clic en el botón Log in ({login_selector})...')
                            await move_mouse_realistic(page, login_selector)
                            await human_delay()
                            await page.click(login_selector)
                            await human_delay(1000, 2000)
                            login_button_found = True
                            break
                    
                    if not login_button_found:
                        print("No se encontró el botón Log in. Puedes continuar manualmente.")
                
                # Tomar captura de pantalla del estado actual
                await page.screenshot(path=str(screenshot_dir / '4_after_password.png'))
            
            # Mensaje para el usuario
            print('\n============= ATENCIÓN =============')
            print('El navegador permanecerá abierto para que puedas:')
            print('- Resolver cualquier captcha que aparezca')
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
                        print('Sesión verificada correctamente. Guardando...')
                    except TimeoutError:
                        print('Advertencia: No se puede verificar que el login sea exitoso.')
                        verify_anyway = input('¿Deseas guardar la sesión de todos modos? (s/n): ')
                        if verify_anyway.lower() != 's':
                            print('No se guardará la sesión. Continúa navegando y vuelve a intentarlo.')
                            continue
                    
                    # Guardar la sesión
                    session_path = await save_session(context, page, screenshot_dir, sessions_dir)
                    print(f'Sesión guardada exitosamente en: {session_path}')
                    
                    continue_browsing = input('¿Deseas continuar navegando? (s/n): ')
                    if continue_browsing.lower() != 's':
                        break
                
                elif action.lower() == 'esperar':
                    wait_time = int(input('¿Cuántos segundos deseas esperar? (predeterminado: 60): ') or '60')
                    print(f'Esperando {wait_time} segundos...')
                    await asyncio.sleep(wait_time)
                
                elif action.lower() == 'salir':
                    save_before_exit = input('¿Deseas guardar la sesión antes de salir? (s/n): ')
                    if save_before_exit.lower() == 's':
                        await save_session(context, page, screenshot_dir, sessions_dir)
                    break
                
                else:
                    print('Opción no reconocida. Por favor, elige "guardar", "esperar" o "salir".')
            
            print('Cerrando navegador...')
            
        except Exception as error:
            print('Ocurrió un error:', error)
            await page.screenshot(path=str(screenshot_dir / 'error_screenshot.png'))
            print('Captura de pantalla de error guardada. Por favor, revisa para más información.')
            
            # Intentar guardar la sesión incluso si hay un error
            try:
                save_anyway = input('¿Deseas intentar guardar la sesión a pesar del error? (s/n): ')
                if save_anyway.lower() == 's':
                    await save_session(context, page, screenshot_dir, sessions_dir)
            except Exception as save_error:
                print(f'Error al guardar la sesión: {save_error}')
        
        finally:
            await browser.close()

# Ejecutar la función principal
if __name__ == "__main__":
    asyncio.run(manual_login())