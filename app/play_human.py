#!/usr/bin/env python3
"""
Script mejorado para lanzar un navegador Playwright con características humanas,
navegar manualmente, y capturar datos de red cuando se desee.
Incluye movimientos de ratón aleatorios, tiempos de espera variables y configuraciones
de navegador más humanas para evitar detección de bots.
"""

import json
import os
import time
import random
import math
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def human_like_mouse_movement(page, x1, y1, x2, y2, steps=25):
    """Simula un movimiento de ratón humano con curva y velocidad variable"""
    # Valida que las coordenadas estén en rangos razonables para evitar errores
    # Asegura que los números sean enteros
    x1, y1 = int(x1), int(y1)
    x2, y2 = int(x2), int(y2)
    
    # Ajustar puntos de control para que no se salgan demasiado de la pantalla
    # Distancia máxima de desviación con respecto a la línea recta
    max_deviation = min(abs(x2 - x1), abs(y2 - y1)) * 0.5 + 50
    
    # Crea puntos de control para una curva de Bezier, con desviación controlada
    cp1x = x1 + random.uniform(20, max_deviation) * (1 if x2 > x1 else -1)
    cp1y = y1 + random.uniform(20, max_deviation) * (1 if y2 > y1 else -1)
    cp2x = x2 + random.uniform(20, max_deviation) * (-1 if x2 > x1 else 1)
    cp2y = y2 + random.uniform(20, max_deviation) * (-1 if y2 > y1 else 1)
    
    for i in range(steps + 1):
        t = i / steps
        # Fórmula de curva de Bezier cúbica
        pow_t = t ** 3
        pow_1_t = (1 - t) ** 3
        
        x = pow_1_t * x1 + 3 * (1 - t) ** 2 * t * cp1x + 3 * (1 - t) * t ** 2 * cp2x + pow_t * x2
        y = pow_1_t * y1 + 3 * (1 - t) ** 2 * t * cp1y + 3 * (1 - t) * t ** 2 * cp2y + pow_t * y2
        
        # Convertir coordenadas a enteros para evitar errores
        page.mouse.move(int(x), int(y))
        
        # Velocidad variable, más lento al principio y al final
        sleep_time = random.uniform(0.001, 0.01) * (1 + math.sin(math.pi * t))
        time.sleep(sleep_time)

def human_like_typing(page, selector, text, delay_range=(0.05, 0.15)):
    """Escribe texto con velocidad variable como un humano"""
    page.click(selector)
    time.sleep(random.uniform(0.5, 1.2))  # Pausa antes de empezar a escribir
    
    for char in text:
        page.keyboard.type(char)
        # Diferentes tiempos entre pulsaciones de teclas
        time.sleep(random.uniform(*delay_range))
        
        # Ocasionalmente hacer una pausa más larga
        if random.random() < 0.05:
            time.sleep(random.uniform(0.3, 0.7))

def scroll_like_human(page, distance, duration=1000):
    """Realiza un scroll como un humano, no constante sino con aceleración/desaceleración"""
    steps = int(duration / 50)  # ~50ms por paso
    
    # Asegurar que hay al menos 5 pasos para hacer el scroll
    steps = max(steps, 5)
    
    # Inicializar el desplazamiento acumulado
    accumulated_scroll = 0
    
    for i in range(1, steps + 1):
        # Scroll con curva sinusoidal para simular aceleración y desaceleración
        factor = (1 - math.cos(i / steps * math.pi)) / 2
        target_scroll = int(distance * factor)
        
        # Calcular cuánto hay que desplazar en este paso (diferencial)
        delta = target_scroll - accumulated_scroll
        
        # Realizar el desplazamiento diferencial
        page.mouse.wheel(0, delta)
        
        # Actualizar el desplazamiento acumulado
        accumulated_scroll += delta
        
        # Pequeña variación en el tiempo entre pasos
        time.sleep(random.uniform(0.04, 0.06))
    
    # Asegurar que llegamos exactamente al desplazamiento deseado
    if accumulated_scroll != distance:
        page.mouse.wheel(0, distance - accumulated_scroll)

def get_random_viewport_size():
    """Devuelve un tamaño de viewport común pero con ligeras variaciones"""
    common_sizes = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900), 
        (1280, 720), (1600, 900), (1280, 800)
    ]
    base_width, base_height = random.choice(common_sizes)
    # Añade pequeñas variaciones aleatorias al tamaño
    width = base_width + random.randint(-10, 10)
    height = base_height + random.randint(-10, 10)
    return width, height

def get_user_agent():
    """Devuelve un User-Agent común de navegador actual"""
    user_agents = [
        # Chrome en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # Chrome en Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # Firefox en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        # Edge en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
        # Safari en Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    ]
    return random.choice(user_agents)

def setup_browser_fingerprint(context):
    """Configura varios aspectos del navegador para reducir la huella digital"""
    # Configurar una localización de geolocalización aleatoria
    latitude = random.uniform(35.0, 45.0)  # Rango de latitudes comunes de EE.UU/Europa
    longitude = random.uniform(-120.0, 10.0)  # Rango de longitudes comunes de EE.UU/Europa
    context.grant_permissions(['geolocation'])
    context.set_geolocation({"latitude": latitude, "longitude": longitude})
    
    # Establecer idioma y zona horaria
    languages = ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"]
    context.locale = random.choice(languages)
    
    timezones = ["America/New_York", "Europe/London", "Europe/Paris", "Europe/Berlin", "America/Los_Angeles"]
    context.timezone_id = random.choice(timezones)
    
    # Otros plugins y capacidades del navegador
    return context

def main():
    with sync_playwright() as p:
        # Configuraciones del viewport y User-Agent
        viewport_width, viewport_height = get_random_viewport_size()
        user_agent = get_user_agent()
        
        # Lanza el navegador con configuraciones más humanas
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                f'--user-agent={user_agent}',
                '--window-size=1920,1080',  # Tamaño de ventana del navegador
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins',
                '--disable-site-isolation-trials',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        )
        
        # Crear contexto con configuraciones personalizadas
        context = browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent=user_agent,
            is_mobile=False,
            has_touch=random.random() > 0.7,  # Algunos usuarios tienen pantalla táctil
            device_scale_factor=random.choice([1, 1.25, 1.5, 2]),  # Variación en la escala
            java_script_enabled=True,
            locale=random.choice(["en-US", "en-GB", "es-ES"]),
            timezone_id=random.choice(["America/New_York", "Europe/Madrid", "Europe/London"]),
        )
        
        # Añadir comportamiento más aleatorio al navegador
        context = setup_browser_fingerprint(context)
        
        # Configurar cookies persistentes y almacenamiento local
        context.add_cookies([{
            'name': 'user_session_preference',
            'value': f'session_{random.randint(1000, 9999)}',
            'domain': '.x.com',
            'path': '/',
        }])
        
        # Añadir plugins comunes (esto se simula, no es funcional)
        context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format'
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        description: 'Portable Document Format'
                    },
                    {
                        name: 'Native Client',
                        filename: 'internal-nacl-plugin',
                        description: 'Native Client Executable'
                    }
                ]
            });
        """)
        
        # Ocultar el WebDriver
        context.add_init_script("""
            delete Object.getPrototypeOf(navigator).webdriver;
            navigator.languages = ['en-US', 'en', 'es'];
            
            // Canvas fingerprinting aleatorio
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type) {
                const context = originalGetContext.apply(this, arguments);
                if (type === '2d') {
                    const originalFillText = context.fillText;
                    context.fillText = function() {
                        arguments[0] = arguments[0] + ' ';  // Añadir un pequeño cambio aleatorio
                        return originalFillText.apply(this, arguments);
                    }
                }
                return context;
            };
        """)
        
        # Crear una nueva página
        page = context.new_page()
        
        # Variables para rastrear la posición actual del ratón
        current_mouse_x = random.randint(20, viewport_width - 20)
        current_mouse_y = random.randint(20, viewport_height - 20)
        
        # Enviar evento de movimiento de ratón inicial
        page.mouse.move(current_mouse_x, current_mouse_y)
        
        # Almacenar todas las respuestas de red
        responses = []
        page.on("response", lambda response: responses.append(response))
        
        # Navegar a una página inicial para establecer cookies y comportamiento de navegación
        print("Iniciando navegador con comportamiento humano...")
        page.goto("https://www.google.com")
        time.sleep(random.uniform(2.0, 4.0))
        
        # Realizar algunos movimientos de ratón aleatorios
        for _ in range(3):
            x1, y1 = current_mouse_x, current_mouse_y
            x2, y2 = random.randint(50, viewport_width - 50), random.randint(50, viewport_height - 50)
            human_like_mouse_movement(page, x1, y1, x2, y2)
            # Actualizar la posición actual después del movimiento
            current_mouse_x, current_mouse_y = x2, y2
            time.sleep(random.uniform(0.5, 1.5))
        
        print("\nNavegador listo para uso manual. Navega a la página deseada.")
        print("Comandos disponibles:")
        print("  'capture' - Captura headers, cookies y datos de red")
        print("  'move' - Realiza movimientos de ratón aleatorios para parecer humano")
        print("  'scroll' - Realiza scroll aleatorio en la página")
        print("  'wait' - Espera un tiempo aleatorio (simula leer la página)")
        print("  'url' - Muestra la URL actual")
        print("  'exit' - Cierra el navegador y sale del script")

        while True:
            command = input("\n>> ").strip().lower()
            
            if command == "capture":
                current_url = page.url
                parsed = urlparse(current_url)
                domain = parsed.netloc.replace(":", "_")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{domain}_{timestamp}.json"

                # Extraer cookies
                cookies = context.cookies()

                # Extraer headers de petición y respuesta para cada respuesta del mismo dominio
                data = []
                for response in responses:
                    if urlparse(response.url).netloc == parsed.netloc:
                        try:
                            data.append({
                                "url": response.url,
                                "request_headers": response.request.headers,
                                "response_headers": response.headers,
                                "status": response.status
                            })
                        except:
                            # Ignora respuestas que no se puedan procesar
                            pass

                output = {
                    "url": current_url,
                    "user_agent": user_agent,
                    "viewport": {"width": viewport_width, "height": viewport_height},
                    "cookies": cookies,
                    "network": data
                }

                # Asegurar que el directorio de salida existe
                os.makedirs("captures", exist_ok=True)
                path = os.path.join("captures", filename)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2)
                print(f"Captura guardada en {path}")
                
                # Limpiar las respuestas después de capturar para evitar duplicados
                responses.clear()
            
            elif command == "move":
                print("Realizando movimientos de ratón aleatorios...")
                for _ in range(random.randint(3, 7)):
                    x1, y1 = current_mouse_x, current_mouse_y
                    x2, y2 = random.randint(50, viewport_width - 50), random.randint(50, viewport_height - 50)
                    human_like_mouse_movement(page, x1, y1, x2, y2)
                    # Actualizar la posición actual después del movimiento
                    current_mouse_x, current_mouse_y = x2, y2
                    time.sleep(random.uniform(0.3, 1.0))
                print("Movimientos completados.")
            
            elif command == "scroll":
                print("Realizando scroll aleatorio...")
                scroll_distance = random.randint(300, 1000)
                scroll_direction = 1 if random.random() > 0.3 else -1  # Mayormente hacia abajo
                scroll_like_human(page, scroll_distance * scroll_direction)
                print("Scroll completado.")
            
            elif command == "wait":
                wait_time = random.uniform(5, 15)
                print(f"Esperando {wait_time:.1f} segundos (simulando lectura)...")
                time.sleep(wait_time)
                print("Espera completada.")
            
            elif command == "url":
                print(f"URL actual: {page.url}")
            
            elif command == "exit":
                print("Cerrando navegador y saliendo del script.")
                break
            
            else:
                print("Comando desconocido. Comandos disponibles: capture, move, scroll, wait, url, exit")
        
        browser.close()

if __name__ == "__main__":
    main()