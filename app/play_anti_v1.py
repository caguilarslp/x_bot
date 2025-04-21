#!/usr/bin/env python3
"""
Script que intenta interactuar directamente con el iframe de Arkose
utilizando una combinación de técnicas avanzadas.
"""

import os
import time
import json
from playwright.sync_api import sync_playwright

# Credenciales
USERNAME = "antonioreverteandujar@gmx.com"

def main():
    # Crear carpeta para capturas
    os.makedirs("captures", exist_ok=True)
    
    with sync_playwright() as p:
        # Lanzar navegador con capacidades extra de depuración
        browser = p.chromium.launch(
            headless=False,
            devtools=True,  # Abre las herramientas de desarrollo para inspección
            args=[
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
                '--no-sandbox',
                '--disable-web-security',  # Reduce restricciones de seguridad entre frames
            ]
        )
        
        # Crear contexto con permisos extra
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            locale="es-ES",
            timezone_id="Europe/Madrid",
            permissions=["geolocation"],  # Añadir permisos que pueden ser requeridos
            ignore_https_errors=True,  # Ignorar errores HTTPS que podrían ocurrir
        )
        
        # Ocultar WebDriver y añadir propiedades más "humanas"
        context.add_init_script("""
        (() => {
            // Eliminar webdriver
            delete Object.getPrototypeOf(navigator).webdriver;
            
            // Simular plugins y características de navegador real
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    name: `Plugin ${Math.random().toString(36).substring(7)}`,
                    description: 'This is a plugin that would be present in a real browser',
                    filename: 'plugin.dll'
                }))
            });
            
            // Simular una hardware concurrency realista
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            
            // Ajustar comportamiento de setTimeout para que sea menos predecible
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(callback, delay) {
                const jitter = Math.random() * 10;
                return originalSetTimeout(callback, delay + jitter);
            };
        })();
        """)
        
        # Abrir página con timeout más largo para cargas lentas
        page = context.new_page()
        page.set_default_timeout(60000)  # 60 segundos de timeout para operaciones
        
        try:
            # Navegar a la página de inicio de sesión
            print("Navegando a X.com...")
            page.goto("https://x.com/i/flow/login", wait_until="networkidle")  # Esperar hasta que la red esté inactiva
            time.sleep(3)
            
            # Tomar captura de pantalla inicial
            page.screenshot(path="captures/1_login_page.png")
            
            # Ingresar nombre de usuario con comportamiento humano (variaciones de tiempo)
            print("Ingresando usuario...")
            username_input = page.query_selector('input[name="text"], input[type="text"]')
            if username_input:
                username_input.click()
                time.sleep(0.5)
                
                # Escribir caracter por caracter con tiempos variables
                for char in USERNAME:
                    username_input.type(char, delay=100 + (ord(char) % 5) * 20)  # Variación en velocidad de escritura
                    time.sleep(0.05 + (ord(char) % 3) * 0.02)  # Variación en pausa entre caracteres
                
                time.sleep(1)
                page.screenshot(path="captures/2_username_filled.png")
                
                # Hacer clic en el botón "Siguiente" o presionar Enter
                page.keyboard.press("Enter")
                time.sleep(3)
                page.screenshot(path="captures/3_after_enter.png")
            else:
                print("No se encontró campo de usuario")
                return False
            
            # Técnica principal: Esperar a que el iframe aparezca y cargue
            print("\n=== ESPERANDO IFRAME DE ARKOSE ===")
            iframe = None
            for attempt in range(10):
                print(f"Intento {attempt+1} de localizar iframe...")
                iframes = page.query_selector_all('iframe')
                
                if iframes:
                    for i, frame in enumerate(iframes):
                        src = frame.get_attribute('src') or ""
                        id_attr = frame.get_attribute('id') or ""
                        print(f"  Frame {i+1}: ID={id_attr}, SRC={src[:80]}...")
                        
                        if "arkoselabs" in src or id_attr == "arkoseFrame":
                            iframe = frame
                            print(f"  ✓ Encontrado iframe de Arkose: {id_attr}")
                            break
                
                if iframe:
                    break
                    
                time.sleep(2)
            
            if not iframe:
                print("No se pudo encontrar el iframe de Arkose después de varios intentos")
                return False
            
            # Esperar a que el iframe cargue completamente
            print("Esperando a que el iframe cargue completamente...")
            time.sleep(5)
            page.screenshot(path="captures/4_iframe_loaded.png")
            
            # Método 1: Intentar dibujar un rectángulo rojo alrededor del botón para identificarlo
            print("\n=== INTENTANDO IDENTIFICAR EL BOTÓN ===")
            try:
                box_js = page.evaluate("""
                () => {
                    const highlightElement = (element) => {
                        const oldBorder = element.style.border;
                        const oldBackground = element.style.background;
                        element.style.border = '3px solid red';
                        element.style.background = 'rgba(255, 0, 0, 0.2)';
                        
                        // Restaurar después de 2 segundos
                        setTimeout(() => {
                            element.style.border = oldBorder;
                            element.style.background = oldBackground;
                        }, 2000);
                        
                        return {
                            text: element.innerText,
                            tag: element.tagName,
                            id: element.id,
                            classes: element.className
                        };
                    };
                    
                    // Intentar en el documento principal
                    let button = document.querySelector('button[data-theme="home.verifyButton"]');
                    if (button) return highlightElement(button);
                    
                    // Intentar en todos los iframes
                    const frames = document.querySelectorAll('iframe');
                    for (const frame of frames) {
                        try {
                            const doc = frame.contentDocument || frame.contentWindow.document;
                            const frameButton = doc.querySelector('button[data-theme="home.verifyButton"]') || 
                                              doc.querySelector('button:has-text("Autentificar")');
                                              
                            if (frameButton) return highlightElement(frameButton);
                        } catch (e) {
                            console.log("Error accediendo al iframe:", e);
                        }
                    }
                    
                    return null;
                }
                """)
                
                if box_js:
                    print(f"Elemento identificado: {json.dumps(box_js, indent=2)}")
                    time.sleep(2)  # Dar tiempo para ver el rectángulo rojo
                else:
                    print("No se pudo identificar visualmente el botón")
            except Exception as e:
                print(f"Error al intentar identificar el botón: {str(e)}")
            
            # Método 2: Intentar simular clic en el centro del iframe
            print("\n=== INTENTANDO CLIC EN EL CENTRO DEL IFRAME ===")
            try:
                # Obtener las dimensiones del iframe
                box = iframe.bounding_box()
                if box:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    
                    print(f"Dimensiones del iframe: {box}")
                    print(f"Haciendo clic en el centro: ({center_x}, {center_y})")
                    
                    # Simular movimiento de ratón al centro
                    page.mouse.move(center_x, center_y)
                    time.sleep(1)
                    
                    # Hacer clic en el centro del iframe
                    page.mouse.click(center_x, center_y)
                    time.sleep(2)
                    page.screenshot(path="captures/5_center_iframe_click.png")
                    
                    # También intentar hacer clic en la parte inferior del iframe (donde suele estar el botón)
                    bottom_center_y = box['y'] + box['height'] * 0.8  # 80% abajo
                    
                    print(f"Haciendo clic en la parte inferior: ({center_x}, {bottom_center_y})")
                    page.mouse.move(center_x, bottom_center_y)
                    time.sleep(1)
                    page.mouse.click(center_x, bottom_center_y)
                    time.sleep(2)
                    page.screenshot(path="captures/6_bottom_iframe_click.png")
                else:
                    print("No se pudieron obtener las dimensiones del iframe")
            except Exception as e:
                print(f"Error al hacer clic en el centro del iframe: {str(e)}")
            
            # Método 3: Intento directo con JavaScript para hacer clic en el botón
            print("\n=== INTENTO FINAL CON JAVASCRIPT ===")
            try:
                success = page.evaluate("""
                () => {
                    const attemptClickInFrames = (frames, depth = 0) => {
                        if (depth > 3) return false; // Limitar recursión
                        
                        for (const frame of frames) {
                            try {
                                const doc = frame.contentDocument || frame.contentWindow.document;
                                
                                // Intentar encontrar el botón con varios métodos
                                const button = 
                                    doc.querySelector('button[data-theme="home.verifyButton"]') || 
                                    doc.querySelector('button.eZxMRy') ||
                                    Array.from(doc.querySelectorAll('button')).find(btn => 
                                        btn.innerText === 'Autentificar' || 
                                        btn.innerText === 'Autentificar');
                                
                                if (button) {
                                    console.log("¡Botón encontrado! Intentando clic...");
                                    button.click();
                                    return true;
                                }
                                
                                // Recursivamente buscar en los iframes anidados
                                const nestedFrames = doc.querySelectorAll('iframe');
                                if (nestedFrames.length > 0) {
                                    if (attemptClickInFrames(nestedFrames, depth + 1)) {
                                        return true;
                                    }
                                }
                            } catch (e) {
                                console.log("Error accediendo al iframe:", e);
                            }
                        }
                        return false;
                    };
                    
                    // Intentar en todos los iframes
                    return attemptClickInFrames(document.querySelectorAll('iframe'));
                }
                """)
                
                if success:
                    print("JavaScript reporta éxito en hacer clic en el botón")
                else:
                    print("JavaScript no pudo hacer clic en el botón")
                
                time.sleep(3)
                page.screenshot(path="captures/7_after_js_attempt.png")
            except Exception as e:
                print(f"Error en el intento final con JavaScript: {str(e)}")
            
            # Verificar si el captcha se activó
            print("\n=== VERIFICANDO RESULTADO ===")
            captcha_frame = page.query_selector('iframe[src*="challenge"], iframe[src*="arkoselabs"][src*="data"]')
            if captcha_frame:
                print("¡ÉXITO! Se activó el captcha")
                captcha_src = captcha_frame.get_attribute('src')
                print(f"URL del captcha: {captcha_src[:100]}...")
                
                # Opción para el usuario
                print("\n===== CAPTCHA MANUAL =====")
                print("Por favor:")
                print("1. Resuelve el captcha manualmente en el navegador")
                print("2. Una vez resuelto, presiona Enter para continuar")
                input("Presiona Enter cuando hayas completado el captcha... ")
                
                page.screenshot(path="captures/8_after_manual_captcha.png")
            else:
                print("No se detectó activación del captcha")
            
            # Buscar campo de contraseña por si acaso ya pasamos el captcha
            password_input = page.query_selector('input[name="password"], input[type="password"]')
            if password_input:
                print("¡Se detectó campo de contraseña! Parece que se pasó la autenticación.")
                page.screenshot(path="captures/8_password_field.png")
            
            print("\nScript completado. Revisa las capturas de pantalla en la carpeta 'captures'.")
            
        except Exception as e:
            print(f"Error general: {str(e)}")
            import traceback
            traceback.print_exc()
            page.screenshot(path="captures/error.png")
            return False
        
        finally:
            print("\nScript finalizado. Presiona Enter para cerrar el navegador...")
            input()
            browser.close()

if __name__ == "__main__":
    main()


# #!/usr/bin/env python3
# """
# Script para iniciar sesión en X.com, con manejo mejorado del botón Authenticate.
# """

# import os
# import time
# import random
# import re
# import json
# from playwright.sync_api import sync_playwright
# from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless

# # Credenciales
# USERNAME = "antonioreverteandujar@gmx.com"
# PASSWORD = "xJHuc@EhMFNBgJd3"
# ANTICAPTCHA_KEY = "c20ef01b3a86bda0cf99cddef67a1477"

# def main():
#     # Crear carpeta para capturas
#     os.makedirs("captures", exist_ok=True)
    
#     with sync_playwright() as p:
#         # Lanzar navegador
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--window-size=1920,1080',
#                 '--no-sandbox',
#             ]
#         )
        
#         # Crear contexto
#         context = browser.new_context(
#             viewport={'width': 1366, 'height': 768},
#             locale="es-ES",
#             timezone_id="Europe/Madrid"
#         )
        
#         # Ocultar WebDriver
#         context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
        
#         # Abrir página
#         page = context.new_page()
        
#         try:
#             # Navegar a la página de inicio de sesión
#             print("Navegando a X.com...")
#             page.goto("https://x.com/i/flow/login")
#             time.sleep(3)
            
#             # Captura de pantalla inicial
#             page.screenshot(path="captures/1_login_page.png")
            
#             # Ingresar nombre de usuario
#             print("Ingresando usuario...")
#             username_input = page.query_selector('input[name="text"], input[type="text"]')
#             if username_input:
#                 username_input.click()
#                 time.sleep(0.5)
#                 username_input.fill(USERNAME)
#                 time.sleep(1)
#                 page.screenshot(path="captures/2_username_filled.png")
                
#                 # Hacer clic en el botón "Siguiente" o "Next"
#                 print("Buscando botón Siguiente...")
                
#                 # Método 1: Botón específico de X.com (color gris claro)
#                 next_button = page.query_selector('button[style*="background-color: rgb(239, 243, 244)"]')
                
#                 if not next_button:
#                     # Método 2: Por texto
#                     next_button = page.query_selector('button:has-text("Next"), button:has-text("Siguiente"), span:has-text("Next"), span:has-text("Siguiente")')
                
#                 if not next_button:
#                     # Método 3: Cualquier botón visible después del input
#                     buttons = page.query_selector_all('button')
#                     for button in buttons:
#                         if button.is_visible():
#                             next_button = button
#                             break
                
#                 if next_button:
#                     print("Haciendo clic en Siguiente...")
#                     next_button.click()
#                     time.sleep(3)
#                     page.screenshot(path="captures/3_after_next.png")
#                 else:
#                     print("No se encontró botón Siguiente, intentando Enter...")
#                     username_input.press("Enter")
#                     time.sleep(3)
#                     page.screenshot(path="captures/3_after_enter.png")
#             else:
#                 print("No se encontró campo de usuario")
#                 return False
            
#             # ===== MEJORADO: Búsqueda y clic en botón Authenticate =====
#             print("Buscando botón Authenticate/Autenticar...")
#             time.sleep(3)  # Esperar a que aparezca el botón
            
#             # Métodos múltiples para encontrar el botón de autenticación
#             auth_button = None
            
#             # Método 1: Por atributo data-theme (más preciso)
#             auth_button = page.query_selector('button[data-theme="home.verifyButton"]')
            
#             # Método 2: Por clase
#             if not auth_button:
#                 auth_button = page.query_selector('button.sc-nkuzb1-0.sc-d5trka-0.eZxMRy.button')
            
#             # Método 3: Por texto
#             if not auth_button:
#                 auth_button = page.query_selector('button:has-text("Authenticate"), button:has-text("Autenticar"), button:has-text("Autentificar")')
            
#             # Método 4: Cualquier botón visible
#             if not auth_button:
#                 buttons = page.query_selector_all('button')
#                 for button in buttons:
#                     if button.is_visible():
#                         text = button.inner_text().lower()
#                         if "auth" in text:
#                             auth_button = button
#                             break
            
#             # Si encontramos el botón, hacer clic
#             if auth_button:
#                 print("Botón Authenticate/Autenticar encontrado. Haciendo clic...")
#                 auth_button.click()
#                 time.sleep(3)  # Esperar a que se cargue el captcha
#                 page.screenshot(path="captures/4_after_auth_click.png")
#             else:
#                 print("No se encontró botón de autenticación")
#                 page.screenshot(path="captures/4_no_auth_button.png")
            
#             # Buscar iframe de captcha
#             print("Buscando iframe de captcha...")
#             captcha_iframe = page.query_selector('#arkoseFrame, iframe[src*="arkoselabs"]')
#             if captcha_iframe:
#                 print("Captcha detectado, intentando resolver...")
                
#                 # Extraer src del iframe
#                 iframe_src = captcha_iframe.get_attribute('src')
#                 print(f"Iframe captcha encontrado: {iframe_src[:100]}...")
                
#                 # Ignorar si es un iframe de Google
#                 if iframe_src and ("google" in iframe_src.lower() or "accounts.google.com" in iframe_src.lower()):
#                     print("Es un iframe de Google, no un captcha. Continuando...")
#                 else:
#                     # Extraer data parameter si existe
#                     data_param = None
#                     if iframe_src and 'data=' in iframe_src:
#                         data_param_match = re.search(r'data=([^&]+)', iframe_src)
#                         if data_param_match:
#                             data_param = data_param_match.group(1)
#                             print(f"Data parameter encontrado: {data_param[:30]}...")
                    
#                     # Resolver captcha con AntiCaptcha (con reintento)
#                     print("Intentando resolver captcha con AntiCaptcha...")
                    
#                     # Primer intento
#                     captcha_solved = False
#                     for attempt in range(2):  # Dos intentos
#                         try:
#                             solver = funcaptchaProxyless()
#                             solver.set_verbose(1)
#                             solver.set_key(ANTICAPTCHA_KEY)
#                             solver.set_website_url("https://x.com")
#                             solver.set_website_key("2F4F0B28-BC94-4271-8AD7-A51662E3C91C")
                            
#                             if data_param:
#                                 solver.set_data_blob(data_param)
                            
#                             token = solver.solve_and_return_solution()
                            
#                             if token != 0:
#                                 captcha_solved = True
#                                 print("Captcha resuelto, inyectando token...")
                                
#                                 # Inyectar token
#                                 page.evaluate(f"""
#                                 (token) => {{
#                                     try {{
#                                         // Método estándar
#                                         if (window.arkose && window.arkose.setTokenResponse) {{
#                                             window.arkose.setTokenResponse(token);
#                                             return true;
#                                         }}
                                        
#                                         // Comunicar con iframe
#                                         const arkoseFrame = document.getElementById('arkoseFrame') || 
#                                                          document.querySelector('iframe[src*="arkoselabs"]');
                                        
#                                         if (arkoseFrame && arkoseFrame.contentWindow) {{
#                                             arkoseFrame.contentWindow.postMessage(
#                                                 JSON.stringify({{ token: token, type: "token response" }}),
#                                                 '*'
#                                             );
#                                             return true;
#                                         }}
                                        
#                                         return false;
#                                     }} catch (e) {{
#                                         console.error('Error:', e);
#                                         return false;
#                                     }}
#                                 }}
#                                 """, token)
                                
#                                 time.sleep(5)
#                                 page.screenshot(path="captures/5_token_injected.png")
                                
#                                 # Buscar y hacer clic en el botón Submit/Enviar
#                                 submit_button = page.query_selector('button:has-text("Submit"), button:has-text("Enviar")')
#                                 if submit_button:
#                                     print("Haciendo clic en Submit/Enviar...")
#                                     submit_button.click()
#                                     time.sleep(3)
#                                     page.screenshot(path="captures/6_after_submit.png")
                                
#                                 break
#                             else:
#                                 print(f"Error en intento {attempt+1}: {solver.error_code}")
#                                 time.sleep(2)  # Esperar antes de reintentar
#                         except Exception as e:
#                             print(f"Error en AntiCaptcha: {str(e)}")
#                             time.sleep(2)
                    
#                     # Si no se pudo resolver automáticamente, dar opción manual
#                     if not captcha_solved:
#                         print("\n===== CAPTCHA MANUAL =====")
#                         print("AntiCaptcha no está disponible. Por favor:")
#                         print("1. Resuelve el captcha manualmente en el navegador")
#                         print("2. Una vez resuelto, presiona Enter para continuar")
#                         input("Presiona Enter cuando hayas completado el captcha... ")
#                         page.screenshot(path="captures/6_manual_captcha.png")
#             else:
#                 print("No se detectó iframe de captcha")
#                 page.screenshot(path="captures/5_no_captcha.png")
            
#             # Buscar campo de contraseña
#             print("Buscando campo de contraseña...")
#             time.sleep(3)  # Esperar a que aparezca el campo de contraseña
            
#             password_input = page.query_selector('input[name="password"], input[type="password"]')
#             if password_input:
#                 print("Ingresando contraseña...")
#                 password_input.click()
#                 time.sleep(0.5)
#                 password_input.fill(PASSWORD)
#                 time.sleep(1)
#                 page.screenshot(path="captures/7_password_filled.png")
                
#                 # Hacer clic en el botón "Iniciar sesión" o "Log in"
#                 login_button = page.query_selector('div:has-text("Iniciar sesión"), div:has-text("Log in"), button:has-text("Iniciar sesión"), button:has-text("Log in")')
#                 if login_button:
#                     print("Haciendo clic en Iniciar sesión...")
#                     login_button.click()
#                     time.sleep(5)
#                     page.screenshot(path="captures/8_after_login.png")
#                 else:
#                     print("No se encontró botón de inicio de sesión, intentando Enter...")
#                     password_input.press("Enter")
#                     time.sleep(5)
#                     page.screenshot(path="captures/8_after_enter.png")
#             else:
#                 print("No se encontró campo de contraseña")
#                 page.screenshot(path="captures/7_no_password_field.png")
                
#                 # Intentar verificar si ya iniciamos sesión (a veces el login es más rápido)
#                 if "home" in page.url or "foryou" in page.url:
#                     print("Parece que ya iniciamos sesión a pesar de no encontrar el campo de contraseña")
#                 else:
#                     return False
            
#             # Verificar resultado
#             print("Verificando inicio de sesión...")
#             success = False
            
#             # Verificar por URL
#             if "home" in page.url or "foryou" in page.url:
#                 success = True
            
#             # Verificar por elementos en la página
#             if not success:
#                 timeline = page.query_selector('[data-testid="primaryColumn"], [aria-label="Timeline"]')
#                 profile = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
#                 if timeline or profile:
#                     success = True
            
#             if success:
#                 print("¡Inicio de sesión exitoso!")
#                 page.screenshot(path="captures/9_success.png")
                
#                 # Guardar cookies
#                 cookies = context.cookies()
#                 with open("captures/cookies.json", "w") as f:
#                     json.dump(cookies, f, indent=2)
                
#                 print("\nSesión iniciada correctamente.")
#                 print("Las cookies se han guardado en captures/cookies.json")
#                 print("\nOpciones disponibles:")
#                 print("1. Capturar datos de red")
#                 print("2. Salir")
                
#                 option = input("\nSelecciona una opción (1-2): ")
#                 if option == "1":
#                     current_url = page.url
#                     network_data = []
                    
#                     # Recargar la página para capturar todas las peticiones
#                     page.reload()
#                     time.sleep(5)
                    
#                     # Capturar headers y datos de red
#                     for request in page.context.pages[0].request_all():
#                         try:
#                             response = request.response()
#                             if response:
#                                 network_data.append({
#                                     "url": request.url,
#                                     "method": request.method,
#                                     "request_headers": request.headers,
#                                     "response_headers": response.headers,
#                                     "status": response.status
#                                 })
#                         except:
#                             pass
                    
#                     # Guardar captura completa
#                     capture_data = {
#                         "url": current_url,
#                         "cookies": cookies,
#                         "network": network_data
#                     }
                    
#                     with open("captures/network_data.json", "w") as f:
#                         json.dump(capture_data, f, indent=2)
                    
#                     print("Datos de red capturados y guardados en captures/network_data.json")
#             else:
#                 print("No se pudo verificar el inicio de sesión")
#                 page.screenshot(path="captures/9_failure.png")
#                 return False
            
#         except Exception as e:
#             print(f"Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             page.screenshot(path="captures/error.png")
#             return False
        
#         finally:
#             print("\nPresiona Enter para cerrar el navegador...")
#             input()
#             browser.close()

# if __name__ == "__main__":
#     main()


# #!/usr/bin/env python3
# """
# Script para iniciar sesión en X.com, con manejo de captchas manual o automático.
# """

# import os
# import time
# import random
# import re
# import json
# from playwright.sync_api import sync_playwright
# from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless

# # Credenciales
# USERNAME = "antonioreverteandujar@gmx.com"
# PASSWORD = "xJHuc@EhMFNBgJd3"
# ANTICAPTCHA_KEY = "c20ef01b3a86bda0cf99cddef67a1477"

# def main():
#     # Crear carpeta para capturas
#     os.makedirs("captures", exist_ok=True)
    
#     with sync_playwright() as p:
#         # Lanzar navegador
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--window-size=1920,1080',
#                 '--no-sandbox',
#             ]
#         )
        
#         # Crear contexto
#         context = browser.new_context(
#             viewport={'width': 1366, 'height': 768},
#             locale="es-ES",
#             timezone_id="Europe/Madrid"
#         )
        
#         # Ocultar WebDriver
#         context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
        
#         # Abrir página
#         page = context.new_page()
        
#         try:
#             # Navegar a la página de inicio de sesión
#             print("Navegando a X.com...")
#             page.goto("https://x.com/i/flow/login")
#             time.sleep(3)
            
#             # Captura de pantalla inicial
#             page.screenshot(path="captures/1_login_page.png")
            
#             # Ingresar nombre de usuario
#             print("Ingresando usuario...")
#             username_input = page.query_selector('input[name="text"], input[type="text"]')
#             if username_input:
#                 username_input.click()
#                 time.sleep(0.5)
#                 username_input.fill(USERNAME)
#                 time.sleep(1)
#                 page.screenshot(path="captures/2_username_filled.png")
                
#                 # Hacer clic en el botón "Siguiente" o "Next"
#                 print("Buscando botón Siguiente...")
                
#                 # Método 1: Botón específico de X.com (color gris claro)
#                 next_button = page.query_selector('button[style*="background-color: rgb(239, 243, 244)"]')
                
#                 if not next_button:
#                     # Método 2: Por texto
#                     next_button = page.query_selector('button:has-text("Next"), button:has-text("Siguiente"), span:has-text("Next"), span:has-text("Siguiente")')
                
#                 if not next_button:
#                     # Método 3: Cualquier botón visible después del input
#                     buttons = page.query_selector_all('button')
#                     for button in buttons:
#                         if button.is_visible():
#                             next_button = button
#                             break
                
#                 if next_button:
#                     print("Haciendo clic en Siguiente...")
#                     next_button.click()
#                     time.sleep(3)
#                     page.screenshot(path="captures/3_after_next.png")
#                 else:
#                     print("No se encontró botón Siguiente, intentando Enter...")
#                     username_input.press("Enter")
#                     time.sleep(3)
#                     page.screenshot(path="captures/3_after_enter.png")
#             else:
#                 print("No se encontró campo de usuario")
#                 return False
            
#             # Verificar si hay captcha
#             print("Verificando captcha...")
#             page.screenshot(path="captures/4_before_captcha_check.png")
            
#             # Buscar botón de autenticación
#             auth_button = page.query_selector('button:has-text("Authenticate"), button:has-text("Autentificar")')
#             if auth_button:
#                 print("Encontrado botón de autenticación, haciendo clic...")
#                 auth_button.click()
#                 time.sleep(3)
#                 page.screenshot(path="captures/5_after_auth_click.png")
            
#             # Buscar iframe de captcha
#             captcha_iframe = page.query_selector('#arkoseFrame, iframe[src*="arkoselabs"]')
#             if captcha_iframe:
#                 print("Captcha detectado, intentando resolver...")
                
#                 # Extraer src del iframe
#                 iframe_src = captcha_iframe.get_attribute('src')
                
#                 # Ignorar si es un iframe de Google
#                 if iframe_src and ("google" in iframe_src.lower() or "accounts.google.com" in iframe_src.lower()):
#                     print("Es un iframe de Google, no un captcha. Continuando...")
#                 else:
#                     # Extraer data parameter si existe
#                     data_param = None
#                     if iframe_src and 'data=' in iframe_src:
#                         data_param_match = re.search(r'data=([^&]+)', iframe_src)
#                         if data_param_match:
#                             data_param = data_param_match.group(1)
                    
#                     # Resolver captcha con AntiCaptcha (con reintento)
#                     print("Intentando resolver captcha con AntiCaptcha...")
                    
#                     # Primer intento
#                     captcha_solved = False
#                     for attempt in range(2):  # Dos intentos
#                         try:
#                             solver = funcaptchaProxyless()
#                             solver.set_verbose(1)
#                             solver.set_key(ANTICAPTCHA_KEY)
#                             solver.set_website_url("https://x.com")
#                             solver.set_website_key("2F4F0B28-BC94-4271-8AD7-A51662E3C91C")
                            
#                             if data_param:
#                                 solver.set_data_blob(data_param)
                            
#                             token = solver.solve_and_return_solution()
                            
#                             if token != 0:
#                                 captcha_solved = True
#                                 print("Captcha resuelto, inyectando token...")
                                
#                                 # Inyectar token
#                                 page.evaluate(f"""
#                                 (token) => {{
#                                     try {{
#                                         // Método estándar
#                                         if (window.arkose && window.arkose.setTokenResponse) {{
#                                             window.arkose.setTokenResponse(token);
#                                             return true;
#                                         }}
                                        
#                                         // Comunicar con iframe
#                                         const arkoseFrame = document.getElementById('arkoseFrame') || 
#                                                          document.querySelector('iframe[src*="arkoselabs"]');
                                        
#                                         if (arkoseFrame && arkoseFrame.contentWindow) {{
#                                             arkoseFrame.contentWindow.postMessage(
#                                                 JSON.stringify({{ token: token, type: "token response" }}),
#                                                 '*'
#                                             );
#                                             return true;
#                                         }}
                                        
#                                         return false;
#                                     }} catch (e) {{
#                                         console.error('Error:', e);
#                                         return false;
#                                     }}
#                                 }}
#                                 """, token)
                                
#                                 time.sleep(5)
#                                 break
#                             else:
#                                 print(f"Error en intento {attempt+1}: {solver.error_code}")
#                                 time.sleep(2)  # Esperar antes de reintentar
#                         except Exception as e:
#                             print(f"Error en AntiCaptcha: {str(e)}")
#                             time.sleep(2)
                    
#                     # Si no se pudo resolver automáticamente, dar opción manual
#                     if not captcha_solved:
#                         print("\n===== CAPTCHA MANUAL =====")
#                         print("AntiCaptcha no está disponible. Por favor:")
#                         print("1. Resuelve el captcha manualmente en el navegador")
#                         print("2. Una vez resuelto, presiona Enter para continuar")
#                         input("Presiona Enter cuando hayas completado el captcha... ")
                    
#                     page.screenshot(path="captures/6_after_captcha.png")
            
#             # Buscar campo de contraseña
#             print("Buscando campo de contraseña...")
#             time.sleep(3)  # Esperar a que aparezca el campo de contraseña
            
#             password_input = page.query_selector('input[name="password"], input[type="password"]')
#             if password_input:
#                 print("Ingresando contraseña...")
#                 password_input.click()
#                 time.sleep(0.5)
#                 password_input.fill(PASSWORD)
#                 time.sleep(1)
#                 page.screenshot(path="captures/7_password_filled.png")
                
#                 # Hacer clic en el botón "Iniciar sesión" o "Log in"
#                 login_button = page.query_selector('div:has-text("Iniciar sesión"), div:has-text("Log in"), button:has-text("Iniciar sesión"), button:has-text("Log in")')
#                 if login_button:
#                     print("Haciendo clic en Iniciar sesión...")
#                     login_button.click()
#                     time.sleep(5)
#                     page.screenshot(path="captures/8_after_login.png")
#                 else:
#                     print("No se encontró botón de inicio de sesión, intentando Enter...")
#                     password_input.press("Enter")
#                     time.sleep(5)
#                     page.screenshot(path="captures/8_after_enter.png")
#             else:
#                 print("No se encontró campo de contraseña")
#                 page.screenshot(path="captures/7_no_password_field.png")
                
#                 # Intentar verificar si ya iniciamos sesión (a veces el login es más rápido)
#                 if "home" in page.url or "foryou" in page.url:
#                     print("Parece que ya iniciamos sesión a pesar de no encontrar el campo de contraseña")
#                 else:
#                     return False
            
#             # Verificar resultado
#             print("Verificando inicio de sesión...")
#             success = False
            
#             # Verificar por URL
#             if "home" in page.url or "foryou" in page.url:
#                 success = True
            
#             # Verificar por elementos en la página
#             if not success:
#                 timeline = page.query_selector('[data-testid="primaryColumn"], [aria-label="Timeline"]')
#                 profile = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
#                 if timeline or profile:
#                     success = True
            
#             if success:
#                 print("¡Inicio de sesión exitoso!")
#                 page.screenshot(path="captures/9_success.png")
                
#                 # Guardar cookies
#                 cookies = context.cookies()
#                 with open("captures/cookies.json", "w") as f:
#                     json.dump(cookies, f, indent=2)
                
#                 print("\nSesión iniciada correctamente.")
#                 print("Las cookies se han guardado en captures/cookies.json")
#                 print("\nOpciones disponibles:")
#                 print("1. Capturar datos de red")
#                 print("2. Salir")
                
#                 option = input("\nSelecciona una opción (1-2): ")
#                 if option == "1":
#                     current_url = page.url
#                     network_data = []
                    
#                     # Recargar la página para capturar todas las peticiones
#                     page.reload()
#                     time.sleep(5)
                    
#                     # Capturar headers y datos de red
#                     for request in page.context.pages[0].request_all():
#                         try:
#                             response = request.response()
#                             if response:
#                                 network_data.append({
#                                     "url": request.url,
#                                     "method": request.method,
#                                     "request_headers": request.headers,
#                                     "response_headers": response.headers,
#                                     "status": response.status
#                                 })
#                         except:
#                             pass
                    
#                     # Guardar captura completa
#                     capture_data = {
#                         "url": current_url,
#                         "cookies": cookies,
#                         "network": network_data
#                     }
                    
#                     with open("captures/network_data.json", "w") as f:
#                         json.dump(capture_data, f, indent=2)
                    
#                     print("Datos de red capturados y guardados en captures/network_data.json")
#             else:
#                 print("No se pudo verificar el inicio de sesión")
#                 page.screenshot(path="captures/9_failure.png")
#                 return False
            
#         except Exception as e:
#             print(f"Error: {str(e)}")
#             import traceback
#             traceback.print_exc()
#             page.screenshot(path="captures/error.png")
#             return False
        
#         finally:
#             print("\nPresiona Enter para cerrar el navegador...")
#             input()
#             browser.close()

# if __name__ == "__main__":
#     main()




# #!/usr/bin/env python3
# """
# Script mejorado para iniciar sesión en X.com con humanización y manejo de captchas.
# Utiliza Playwright para emular navegación humana y AntiCaptcha para resolver los captchas.
# """

# import json
# import os
# import time
# import random
# import math
# import re
# import asyncio
# from urllib.parse import urlparse
# from playwright.sync_api import sync_playwright
# from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless

# def human_like_mouse_movement(page, x1, y1, x2, y2, steps=25):
#     """Simula un movimiento de ratón humano con curva y velocidad variable"""
#     # Valida que las coordenadas estén en rangos razonables para evitar errores
#     # Asegura que los números sean enteros
#     x1, y1 = int(x1), int(y1)
#     x2, y2 = int(x2), int(y2)
    
#     # Ajustar puntos de control para que no se salgan demasiado de la pantalla
#     # Distancia máxima de desviación con respecto a la línea recta
#     max_deviation = min(abs(x2 - x1), abs(y2 - y1)) * 0.5 + 50
    
#     # Crea puntos de control para una curva de Bezier, con desviación controlada
#     cp1x = x1 + random.uniform(20, max_deviation) * (1 if x2 > x1 else -1)
#     cp1y = y1 + random.uniform(20, max_deviation) * (1 if y2 > y1 else -1)
#     cp2x = x2 + random.uniform(20, max_deviation) * (-1 if x2 > x1 else 1)
#     cp2y = y2 + random.uniform(20, max_deviation) * (-1 if y2 > y1 else 1)
    
#     for i in range(steps + 1):
#         t = i / steps
#         # Fórmula de curva de Bezier cúbica
#         pow_t = t ** 3
#         pow_1_t = (1 - t) ** 3
        
#         x = pow_1_t * x1 + 3 * (1 - t) ** 2 * t * cp1x + 3 * (1 - t) * t ** 2 * cp2x + pow_t * x2
#         y = pow_1_t * y1 + 3 * (1 - t) ** 2 * t * cp1y + 3 * (1 - t) * t ** 2 * cp2y + pow_t * y2
        
#         # Convertir coordenadas a enteros para evitar errores
#         page.mouse.move(int(x), int(y))
        
#         # Velocidad variable, más lento al principio y al final
#         sleep_time = random.uniform(0.001, 0.01) * (1 + math.sin(math.pi * t))
#         time.sleep(sleep_time)

# def human_like_typing(page, selector, text, delay_range=(0.05, 0.15)):
#     """Escribe texto con velocidad variable como un humano"""
#     page.click(selector)
#     time.sleep(random.uniform(0.5, 1.2))  # Pausa antes de empezar a escribir
    
#     for char in text:
#         page.keyboard.type(char)
#         # Diferentes tiempos entre pulsaciones de teclas
#         time.sleep(random.uniform(*delay_range))
        
#         # Ocasionalmente hacer una pausa más larga
#         if random.random() < 0.05:
#             time.sleep(random.uniform(0.3, 0.7))

# def scroll_like_human(page, distance, duration=1000):
#     """Realiza un scroll como un humano, no constante sino con aceleración/desaceleración"""
#     steps = int(duration / 50)  # ~50ms por paso
    
#     # Asegurar que hay al menos 5 pasos para hacer el scroll
#     steps = max(steps, 5)
    
#     # Inicializar el desplazamiento acumulado
#     accumulated_scroll = 0
    
#     for i in range(1, steps + 1):
#         # Scroll con curva sinusoidal para simular aceleración y desaceleración
#         factor = (1 - math.cos(i / steps * math.pi)) / 2
#         target_scroll = int(distance * factor)
        
#         # Calcular cuánto hay que desplazar en este paso (diferencial)
#         delta = target_scroll - accumulated_scroll
        
#         # Realizar el desplazamiento diferencial
#         page.mouse.wheel(0, delta)
        
#         # Actualizar el desplazamiento acumulado
#         accumulated_scroll += delta
        
#         # Pequeña variación en el tiempo entre pasos
#         time.sleep(random.uniform(0.04, 0.06))
    
#     # Asegurar que llegamos exactamente al desplazamiento deseado
#     if accumulated_scroll != distance:
#         page.mouse.wheel(0, distance - accumulated_scroll)

# def get_random_viewport_size():
#     """Devuelve un tamaño de viewport común pero con ligeras variaciones"""
#     common_sizes = [
#         (1920, 1080), (1366, 768), (1536, 864), (1440, 900), 
#         (1280, 720), (1600, 900), (1280, 800)
#     ]
#     base_width, base_height = random.choice(common_sizes)
#     # Añade pequeñas variaciones aleatorias al tamaño
#     width = base_width + random.randint(-10, 10)
#     height = base_height + random.randint(-10, 10)
#     return width, height

# def get_user_agent():
#     """Devuelve un User-Agent común de navegador actual"""
#     user_agents = [
#         # Chrome en Windows
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
#         # Chrome en Mac
#         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
#         # Firefox en Windows
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
#         # Edge en Windows
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
#         # Safari en Mac
#         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
#     ]
#     return random.choice(user_agents)

# def setup_browser_fingerprint(context):
#     """Configura varios aspectos del navegador para reducir la huella digital"""
#     # Configurar una localización de geolocalización aleatoria
#     latitude = random.uniform(35.0, 45.0)  # Rango de latitudes comunes de EE.UU/Europa
#     longitude = random.uniform(-120.0, 10.0)  # Rango de longitudes comunes de EE.UU/Europa
#     context.grant_permissions(['geolocation'])
#     context.set_geolocation({"latitude": latitude, "longitude": longitude})
    
#     # Establecer idioma y zona horaria
#     languages = ["es-ES", "es", "en-US", "en-GB"]  # Priorizar español para x.com en español
#     context.locale = random.choice(languages)
    
#     timezones = ["Europe/Madrid", "Europe/Paris", "America/Mexico_City", "America/Bogota"]
#     context.timezone_id = random.choice(timezones)
    
#     # Otros plugins y capacidades del navegador
#     return context

# def solve_captcha(page, api_key="TU_API_KEY_ANTICAPTCHA"):
#     """
#     Detecta y resuelve captchas usando AntiCaptcha
#     Retorna True si se resolvió el captcha correctamente, False en caso contrario
#     """
#     print("Comprobando si hay captcha...")
    
#     # Esperar un poco para que el iframe del captcha se cargue completamente si existe
#     time.sleep(3)
    
#     # Verificar varias formas en que puede aparecer el captcha
#     arkose_iframe = page.query_selector('#arkoseFrame')
    
#     # Si no encontramos el iframe por ID, buscar cualquier iframe que pueda ser el captcha
#     if not arkose_iframe:
#         arkose_iframe = page.query_selector('iframe[src*="arkoselabs"]')
    
#     # Si no encontramos ningún iframe, buscar signos del modal de captcha
#     if not arkose_iframe:
#         captcha_modal = page.query_selector('div[aria-modal="true"] iframe, [data-testid="modalDialog"] iframe')
#         if captcha_modal:
#             arkose_iframe = captcha_modal
    
#     # Buscar botón de Authenticate o Autentificar
#     auth_button = page.query_selector('button:has-text("Authenticate"), button:has-text("Autentificar"), button:has-text("Autentificar")')
    
#     if not arkose_iframe and not auth_button:
#         print("No se detectó captcha, continuando...")
#         return True
    
#     print("Captcha de Arkose Labs detectado. Procesando...")
    
#     # Si hay un botón de autenticar, hacer clic en él primero
#     if auth_button:
#         print("Haciendo clic en botón de autenticación...")
#         auth_button.click()
#         time.sleep(5)  # Esperar a que aparezca el iframe
        
#         # Buscar nuevamente el iframe después de hacer clic
#         arkose_iframe = page.query_selector('#arkoseFrame')
#         if not arkose_iframe:
#             arkose_iframe = page.query_selector('iframe[src*="arkoselabs"]')
    
#     # Si aún no encontramos el iframe, puede ser que la autenticación ya se completó
#     if not arkose_iframe:
#         print("No se encontró el iframe del captcha después de la autenticación. Continuando...")
#         return True
    
#     try:
#         # Extraer el website_key y datos adicionales del iframe si están disponibles
#         iframe_src = arkose_iframe.get_attribute('src')
#         print(f"URL del iframe: {iframe_src[:100]}...")
        
#         # El website_key para X.com es "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"
#         website_key = "2F4F0B28-BC94-4271-8AD7-A51662E3C91C"
        
#         # Extraer el data parameter si está presente
#         data_param = None
#         if iframe_src and 'data=' in iframe_src:
#             data_param_match = re.search(r'data=([^&]+)', iframe_src)
#             if data_param_match:
#                 data_param = data_param_match.group(1)
#                 print(f"Data parameter encontrado: {data_param[:30]}...")
        
#         # Usar AntiCaptcha para resolver
#         solver = funcaptchaProxyless()
#         solver.set_verbose(1)
#         solver.set_key(api_key)
#         solver.set_website_url("https://x.com")
#         solver.set_website_key(website_key)
        
#         if data_param:
#             print("Configurando data_param en el solver...")
#             solver.set_data_blob(data_param)
        
#         print("Resolviendo captcha con AntiCaptcha... (esto puede tardar hasta 1 minuto)")
#         token = solver.solve_and_return_solution()
        
#         if token == 0:
#             print(f"Error al resolver captcha: {solver.error_code}")
#             return False
        
#         print(f"Captcha resuelto correctamente. Token: {token[:30]}...")
        
#         # Aquí necesitamos inyectar la solución al captcha
#         # Primero veamos si podemos acceder al iframe
#         frame_element = arkose_iframe
        
#         # Intentar acceder al contenido del iframe
#         if frame_element:
#             try:
#                 frame = page.frame_locator('iframe[id="arkoseFrame"], iframe[src*="arkoselabs"]')
                
#                 # Buscar el botón para enviar el token dentro del iframe
#                 submit_button = frame.locator('button:has-text("Submit"), button:has-text("Enviar")').first
                
#                 if submit_button:
#                     print("Encontrado botón de envío dentro del iframe. Intentando hacer clic...")
#                     submit_button.click()
#                     time.sleep(3)
                
#                 # Si no podemos interactuar directamente, inyectar el token vía JS
#                 print("Inyectando token via JavaScript...")
#                 page.evaluate(f"""
#                 (token) => {{
#                     try {{
#                         // Intentar varias formas de inyectar el token
#                         // 1. Método estándar para FunCaptcha/ArkoseLabs
#                         if (window.arkose && window.arkose.setTokenResponse) {{
#                             window.arkose.setTokenResponse(token);
#                             console.log('Token establecido via arkose.setTokenResponse');
#                             return true;
#                         }}
                        
#                         // 2. Buscar el iframe y comunicarse con él
#                         const arkoseFrame = document.getElementById('arkoseFrame') || 
#                                           document.querySelector('iframe[src*="arkoselabs"]');
                        
#                         if (arkoseFrame && arkoseFrame.contentWindow) {{
#                             // Enviar mensaje al iframe
#                             arkoseFrame.contentWindow.postMessage(
#                                 JSON.stringify({{ token: token, type: "token response" }}),
#                                 '*'
#                             );
#                             console.log('Token enviado como mensaje al iframe');
                            
#                             // Intentar acceder a los objetos internos
#                             try {{
#                                 if (arkoseFrame.contentWindow.arkose) {{
#                                     arkoseFrame.contentWindow.arkose.setTokenResponse(token);
#                                     console.log('Token establecido en iframe via arkose.setTokenResponse');
#                                 }}
#                             }} catch (e) {{
#                                 console.log('No se pudo acceder a objetos internos del iframe:', e);
#                             }}
                            
#                             return true;
#                         }}
                        
#                         // 3. Despachar un evento personalizado
#                         const tokenEvent = new CustomEvent('funcaptcha:token', {{ 
#                             detail: {{ token: token }},
#                             bubbles: true
#                         }});
#                         document.dispatchEvent(tokenEvent);
#                         console.log('Token despachado como evento personalizado');
                        
#                         return true;
#                     }} catch (e) {{
#                         console.error('Error al inyectar token:', e);
#                         return false;
#                     }}
#                 }}
#                 """, token)
                
#                 # Esperar a que la página procese el token
#                 print("Esperando que la página procese el token...")
#                 time.sleep(5)
                
#                 # Intentar hacer clic en el botón de enviar/submit si está disponible
#                 submit_button = page.query_selector('button.sc-nkuzb1-0, button:has-text("Submit"), button:has-text("Enviar")')
#                 if submit_button:
#                     print("Haciendo clic en botón Enviar/Submit...")
#                     submit_button.click()
#                     time.sleep(3)
#             except Exception as e:
#                 print(f"Error al interactuar con el iframe: {str(e)}")
        
#         # Esperar a que desaparezca el captcha
#         print("Esperando a que el captcha desaparezca...")
#         captcha_gone = False
#         timeout = time.time() + 15  # 15 segundos de timeout
        
#         while time.time() < timeout and not captcha_gone:
#             # Comprobar si el iframe ya no está presente
#             if not page.query_selector('#arkoseFrame, iframe[src*="arkoselabs"]'):
#                 captcha_gone = True
#                 break
            
#             # O si hay algún mensaje de éxito
#             success_msg = page.query_selector('text="ha demostrado que es un humano"')
#             if success_msg:
#                 captcha_gone = True
#                 break
                
#             time.sleep(1)
        
#         if captcha_gone:
#             print("¡Captcha resuelto exitosamente!")
#             return True
#         else:
#             print("No se pudo verificar que el captcha se resolviera correctamente.")
            
#             # Intento final: Ver si aparece el input de contraseña, lo que indicaría que el captcha fue resuelto
#             if page.query_selector('input[name="password"], input[type="password"]'):
#                 print("Se detectó campo de contraseña, parece que el captcha fue resuelto.")
#                 return True
                
#             return False
        
#     except Exception as e:
#         print(f"Error al resolver captcha: {str(e)}")
#         return False

# def login_to_twitter(username, password, captcha_api_key="TU_API_KEY_ANTICAPTCHA"):
#     with sync_playwright() as p:
#         # Configuraciones del viewport y User-Agent
#         viewport_width, viewport_height = get_random_viewport_size()
#         user_agent = get_user_agent()
        
#         # Lanza el navegador con configuraciones más humanas
#         browser = p.chromium.launch(
#             headless=False,
#             args=[
#                 '--disable-blink-features=AutomationControlled',
#                 '--disable-features=IsolateOrigins,site-per-process',
#                 f'--user-agent={user_agent}',
#                 '--window-size=1920,1080',  # Tamaño de ventana del navegador
#                 '--no-sandbox',
#                 '--disable-web-security',
#                 '--disable-features=IsolateOrigins',
#                 '--disable-site-isolation-trials',
#                 '--disable-features=BlockInsecurePrivateNetworkRequests',
#             ]
#         )
        
#         # Crear contexto con configuraciones personalizadas
#         context = browser.new_context(
#             viewport={'width': viewport_width, 'height': viewport_height},
#             user_agent=user_agent,
#             is_mobile=False,
#             has_touch=random.random() > 0.7,  # Algunos usuarios tienen pantalla táctil
#             device_scale_factor=random.choice([1, 1.25, 1.5, 2]),  # Variación en la escala
#             java_script_enabled=True,
#             locale="es-ES",  # Forzar español para que X.com muestre la interfaz en español
#             timezone_id="Europe/Madrid",
#         )
        
#         # Añadir comportamiento más aleatorio al navegador
#         context = setup_browser_fingerprint(context)
        
#         # Configurar cookies persistentes y almacenamiento local
#         context.add_cookies([{
#             'name': 'user_session_preference',
#             'value': f'session_{random.randint(1000, 9999)}',
#             'domain': '.x.com',
#             'path': '/',
#         }])
        
#         # Añadir plugins comunes (esto se simula, no es funcional)
#         context.add_init_script("""
#             Object.defineProperty(navigator, 'plugins', {
#                 get: () => [
#                     {
#                         name: 'Chrome PDF Plugin',
#                         filename: 'internal-pdf-viewer',
#                         description: 'Portable Document Format'
#                     },
#                     {
#                         name: 'Chrome PDF Viewer',
#                         filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
#                         description: 'Portable Document Format'
#                     },
#                     {
#                         name: 'Native Client',
#                         filename: 'internal-nacl-plugin',
#                         description: 'Native Client Executable'
#                     }
#                 ]
#             });
#         """)
        
#         # Ocultar el WebDriver
#         context.add_init_script("""
#             delete Object.getPrototypeOf(navigator).webdriver;
#             navigator.languages = ['es-ES', 'es', 'en-US', 'en'];
            
#             // Canvas fingerprinting aleatorio
#             const originalGetContext = HTMLCanvasElement.prototype.getContext;
#             HTMLCanvasElement.prototype.getContext = function(type) {
#                 const context = originalGetContext.apply(this, arguments);
#                 if (type === '2d') {
#                     const originalFillText = context.fillText;
#                     context.fillText = function() {
#                         arguments[0] = arguments[0] + ' ';  // Añadir un pequeño cambio aleatorio
#                         return originalFillText.apply(this, arguments);
#                     }
#                 }
#                 return context;
#             };
#         """)
        
#         # Crear una nueva página
#         page = context.new_page()
        
#         # Variables para rastrear la posición actual del ratón
#         current_mouse_x = random.randint(20, viewport_width - 20)
#         current_mouse_y = random.randint(20, viewport_height - 20)
        
#         # Enviar evento de movimiento de ratón inicial
#         page.mouse.move(current_mouse_x, current_mouse_y)
        
#         # Almacenar todas las respuestas de red
#         responses = []
#         page.on("response", lambda response: responses.append(response))
        
#         try:
#             print("Navegando a X.com...")
#             page.goto("https://x.com/login")
#             time.sleep(random.uniform(3.0, 5.0))  # Esperar que cargue la página
            
#             # Verificar si estamos en la página de login
#             if "login" not in page.url:
#                 print("Redirigiendo a la página de login...")
#                 # Buscar el botón de iniciar sesión y hacer clic
#                 login_button = page.query_selector('span:has-text("Iniciar sesión")')
#                 if login_button:
#                     # Mover el cursor hasta el botón
#                     login_box = login_button.bounding_box()
#                     if login_box:
#                         human_like_mouse_movement(
#                             page, 
#                             current_mouse_x, current_mouse_y,
#                             login_box['x'] + login_box['width'] / 2,
#                             login_box['y'] + login_box['height'] / 2
#                         )
#                         current_mouse_x = login_box['x'] + login_box['width'] / 2
#                         current_mouse_y = login_box['y'] + login_box['height'] / 2
                    
#                     login_button.click()
#                     time.sleep(random.uniform(2.0, 3.0))
            
#             # Ingresar nombre de usuario o email
#             username_input = page.query_selector('input[name="text"], input[autocomplete="username"]')
#             if username_input:
#                 # Mover el cursor hasta el campo de usuario
#                 input_box = username_input.bounding_box()
#                 if input_box:
#                     human_like_mouse_movement(
#                         page, 
#                         current_mouse_x, current_mouse_y,
#                         input_box['x'] + input_box['width'] / 2,
#                         input_box['y'] + input_box['height'] / 2
#                     )
#                     current_mouse_x = input_box['x'] + input_box['width'] / 2
#                     current_mouse_y = input_box['y'] + input_box['height'] / 2
                
#                 # Escribir el nombre de usuario como un humano
#                 human_like_typing(page, 'input[name="text"], input[autocomplete="username"]', username)
#                 time.sleep(random.uniform(0.8, 1.5))
                
#                 # Hacer clic en el botón "Siguiente"
#                 print("Buscando el botón 'Siguiente'...")
                
#                 # Esperar un poco más para asegurar que el botón esté disponible
#                 time.sleep(random.uniform(1.0, 2.0))
                
#                 # Intentar varias formas de encontrar el botón "Siguiente"
#                 next_button = None
                
#                 # Opción 1: Buscar por texto exacto
#                 next_button = page.query_selector('div:has-text("Siguiente")')
                
#                 # Opción 2: Buscar por texto contenido en span
#                 if not next_button:
#                     next_button = page.query_selector('span:has-text("Siguiente")')
                
#                 # Opción 3: Buscar por selector CSS más específico basado en el HTML proporcionado
#                 if not next_button:
#                     next_button = page.query_selector('div[dir="ltr"].css-146c3p1.r-bcqeeo.r-qvutc0')
                
#                 # Opción 4: Usar XPath para encontrar el botón
#                 if not next_button:
#                     next_button = page.query_selector('//div[contains(text(), "Siguiente")]')
                
#                 # Opción 5: Buscar cualquier botón o elemento clickeable después del input
#                 if not next_button:
#                     next_button = page.query_selector('input[name="text"] ~ div[role="button"]')
                
#                 # Si aún no lo encontramos, buscar cualquier elemento que pueda ser el botón siguiente
#                 if not next_button:
#                     # Intentar encontrar por atributos de role o data-testid
#                     next_button = page.query_selector('[data-testid="Flow_next_button"], [role="button"]')
                
#                 if next_button:
#                     print("Botón 'Siguiente' encontrado. Haciendo clic...")
#                     # Mover el cursor hasta el botón
#                     button_box = next_button.bounding_box()
#                     if button_box:
#                         human_like_mouse_movement(
#                             page, 
#                             current_mouse_x, current_mouse_y,
#                             button_box['x'] + button_box['width'] / 2,
#                             button_box['y'] + button_box['height'] / 2
#                         )
#                         current_mouse_x = button_box['x'] + button_box['width'] / 2
#                         current_mouse_y = button_box['y'] + button_box['height'] / 2
                    
#                     # Hacer clic con un pequeño retraso
#                     time.sleep(random.uniform(0.3, 0.7))
#                     next_button.click()
                    
#                     # Esperar más tiempo para que la página responda
#                     time.sleep(random.uniform(3.0, 5.0))
#                 else:
#                     print("ADVERTENCIA: No se pudo encontrar el botón 'Siguiente'.")
                    
#                     # Plan B: Presionar Enter en el campo de usuario
#                     print("Intentando presionar Enter en el campo de usuario...")
#                     username_input.press("Enter")
#                     time.sleep(random.uniform(3.0, 5.0))
            
#             # Verificar si aparece captcha después de ingresar el usuario
#             captcha_solved = solve_captcha(page, captcha_api_key)
#             if not captcha_solved:
#                 print("No se pudo resolver el captcha después de ingresar el usuario.")
#                 return False
            
#             # Ingresar contraseña
#             password_input = page.query_selector('input[name="password"], input[type="password"]')
#             if password_input:
#                 print("Campo de contraseña encontrado. Ingresando contraseña...")
#                 # Mover el cursor hasta el campo de contraseña
#                 input_box = password_input.bounding_box()
#                 if input_box:
#                     human_like_mouse_movement(
#                         page, 
#                         current_mouse_x, current_mouse_y,
#                         input_box['x'] + input_box['width'] / 2,
#                         input_box['y'] + input_box['height'] / 2
#                     )
#                     current_mouse_x = input_box['x'] + input_box['width'] / 2
#                     current_mouse_y = input_box['y'] + input_box['height'] / 2
                
#                 # Escribir la contraseña como un humano
#                 human_like_typing(page, 'input[name="password"], input[type="password"]', password)
#                 time.sleep(random.uniform(0.8, 1.5))
                
#                 # Hacer clic en el botón "Iniciar sesión"
#                 print("Buscando botón 'Iniciar sesión'...")
#                 login_button = None
                
#                 # Intentar varias formas de encontrar el botón
#                 login_button = page.query_selector('div:has-text("Iniciar sesión")')
                
#                 if not login_button:
#                     login_button = page.query_selector('span:has-text("Iniciar sesión")')
                
#                 if not login_button:
#                     login_button = page.query_selector('[data-testid="LoginForm_Login_Button"]')
                
#                 if not login_button:
#                     login_button = page.query_selector('div[role="button"]:has-text("Iniciar sesión")')
                
#                 if login_button:
#                     print("Botón 'Iniciar sesión' encontrado. Haciendo clic...")
#                     # Mover el cursor hasta el botón
#                     button_box = login_button.bounding_box()
#                     if button_box:
#                         human_like_mouse_movement(
#                             page, 
#                             current_mouse_x, current_mouse_y,
#                             button_box['x'] + button_box['width'] / 2,
#                             button_box['y'] + button_box['height'] / 2
#                         )
#                         current_mouse_x = button_box['x'] + button_box['width'] / 2
#                         current_mouse_y = button_box['y'] + button_box['height'] / 2
                    
#                     login_button.click()
#                     time.sleep(random.uniform(3.0, 5.0))
#                 else:
#                     print("ADVERTENCIA: No se pudo encontrar el botón 'Iniciar sesión'")
#                     # Intentar presionar Enter como alternativa
#                     print("Intentando presionar Enter en el campo de contraseña...")
#                     password_input.press("Enter")
#                     time.sleep(random.uniform(3.0, 5.0))
#             else:
#                 print("No se encontró el campo de contraseña.")
            
#             # Verificar si aparece captcha después de intentar iniciar sesión
#             captcha_solved = solve_captcha(page, captcha_api_key)
#             if not captcha_solved:
#                 print("No se pudo resolver el captcha después de ingresar la contraseña.")
#                 return False
            
#             # Verificar si el inicio de sesión fue exitoso
#             print("Verificando si el inicio de sesión fue exitoso...")
#             time.sleep(random.uniform(3.0, 5.0))  # Dar tiempo para que cargue la página principal
            
#             # Si estamos en la página principal o en la página de inicio de X.com, el login fue exitoso
#             success = False
            
#             # Comprobar URL para verificar éxito
#             if page.url == "https://x.com/home" or page.url == "https://twitter.com/home" or "foryou" in page.url:
#                 success = True
            
#             # Comprobar elementos de la página para verificar éxito (timeline, menú lateral, etc.)
#             if not success:
#                 try:
#                     # Intentar identificar elementos que solo aparecen después del login exitoso
#                     timeline = page.query_selector('[data-testid="primaryColumn"], [aria-label="Timeline"]')
#                     profile_menu = page.query_selector('[data-testid="AppTabBar_Profile_Link"], [aria-label="Profile"]')
                    
#                     if timeline or profile_menu:
#                         success = True
#                 except:
#                     pass
            
#             if success:
#                 print("¡Inicio de sesión exitoso!")
                
#                 # Guardar las cookies y la información de la sesión
#                 cookies = context.cookies()
#                 os.makedirs("captures", exist_ok=True)
#                 timestamp = time.strftime("%Y%m%d_%H%M%S")
#                 with open(f"captures/x_session_{timestamp}.json", "w", encoding="utf-8") as f:
#                     json.dump({
#                         "cookies": cookies,
#                         "user_agent": user_agent,
#                         "viewport": {"width": viewport_width, "height": viewport_height}
#                     }, f, indent=2)
                
#                 print(f"Sesión guardada en captures/x_session_{timestamp}.json")
                
#                 # Comando interactivo para el usuario
#                 print("\nSesión activa. Comandos disponibles:")
#                 print("  'capture' - Captura headers, cookies y datos de red")
#                 print("  'move' - Realiza movimientos de ratón aleatorios")
#                 print("  'scroll' - Realiza scroll aleatorio en la página")
#                 print("  'wait' - Espera un tiempo aleatorio (simula leer)")
#                 print("  'exit' - Cierra el navegador y sale del script")
                
#                 while True:
#                     command = input("\n>> ").strip().lower()
                    
#                     if command == "capture":
#                         current_url = page.url
#                         parsed = urlparse(current_url)
#                         domain = parsed.netloc.replace(":", "_")
#                         timestamp = time.strftime("%Y%m%d_%H%M%S")
#                         filename = f"capture_{domain}_{timestamp}.json"

#                         # Extraer cookies
#                         cookies = context.cookies()

#                         # Extraer headers de petición y respuesta para cada respuesta del mismo dominio
#                         data = []
#                         for response in responses:
#                             if urlparse(response.url).netloc == parsed.netloc:
#                                 try:
#                                     data.append({
#                                         "url": response.url,
#                                         "request_headers": response.request.headers,
#                                         "response_headers": response.headers,
#                                         "status": response.status
#                                     })
#                                 except:
#                                     # Ignora respuestas que no se puedan procesar
#                                     pass

#                         output = {
#                             "url": current_url,
#                             "user_agent": user_agent,
#                             "viewport": {"width": viewport_width, "height": viewport_height},
#                             "cookies": cookies,
#                             "network": data
#                         }

#                         path = os.path.join("captures", filename)
#                         with open(path, "w", encoding="utf-8") as f:
#                             json.dump(output, f, indent=2)
#                         print(f"Captura guardada en {path}")
                        
#                         # Limpiar las respuestas después de capturar para evitar duplicados
#                         responses.clear()
                    
#                     elif command == "move":
#                         print("Realizando movimientos de ratón aleatorios...")
#                         for _ in range(random.randint(3, 7)):
#                             x1, y1 = current_mouse_x, current_mouse_y
#                             x2, y2 = random.randint(50, viewport_width - 50), random.randint(50, viewport_height - 50)
#                             human_like_mouse_movement(page, x1, y1, x2, y2)
#                             # Actualizar la posición actual después del movimiento
#                             current_mouse_x, current_mouse_y = x2, y2
#                             time.sleep(random.uniform(0.3, 1.0))
#                         print("Movimientos completados.")
                    
#                     elif command == "scroll":
#                         print("Realizando scroll aleatorio...")
#                         scroll_distance = random.randint(300, 1000)
#                         scroll_direction = 1 if random.random() > 0.3 else -1  # Mayormente hacia abajo
#                         scroll_like_human(page, scroll_distance * scroll_direction)
#                         print("Scroll completado.")
                    
#                     elif command == "wait":
#                         wait_time = random.uniform(5, 15)
#                         print(f"Esperando {wait_time:.1f} segundos (simulando lectura)...")
#                         time.sleep(wait_time)
#                         print("Espera completada.")
                    
#                     elif command == "exit":
#                         print("Cerrando navegador y saliendo del script.")
#                         break
                    
#                     else:
#                         print("Comando desconocido. Comandos disponibles: capture, move, scroll, wait, exit")
                
#                 return True
#             else:
#                 print(f"No se pudo verificar el inicio de sesión. URL actual: {page.url}")
#                 return False
            
#         except Exception as e:
#             print(f"Error durante el proceso de inicio de sesión: {str(e)}")
#             return False
        
#         finally:
#             browser.close()

# if __name__ == "__main__":
#     # Credenciales de acceso a X.com
#     USERNAME = "antonioreverteandujar@gmx.com"
#     PASSWORD = "xJHuc@EhMFNBgJd3"
#     ANTICAPTCHA_KEY = "c20ef01b3a86bda0cf99cddef67a1477"
    
#     login_to_twitter(USERNAME, PASSWORD, ANTICAPTCHA_KEY)