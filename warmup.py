#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X.com Warmup - Script principal para el proceso gradual de aclimatación de cuentas

Este script ejecuta el proceso de warmup para cuentas de X.com, gestionando la
sesión de navegador, selección de cuenta, y la ejecución del proceso de warmup
de manera automática sin prompts interactivos durante la ejecución.
"""

import os
import sys
import asyncio
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("x_warmup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos necesarios
try:
    # Importar desde archivos separados
    from app.login.login_sesion import (
        load_accounts, select_account, load_session, analyze_page_structure, 
        find_user_session, update_session_file, get_proxy_config
    )
    # Este será importado condicionalmente más adelante
    # from x_warmup import XWarmup
except ImportError:
    logger.warning("No se pudieron importar módulos desde app/login/, usando camino relativo")
    # Si falla, asegurar que los directorios necesarios existen
    sys.path.append(os.path.abspath('.'))

# Función para listar las cuentas disponibles con su estado de warmup
def list_accounts_with_warmup_status():
    """
    Muestra las cuentas disponibles con información sobre su estado de warmup.
    
    Returns:
        list: Lista de diccionarios con información de las cuentas
    """
    try:
        # Cargar cuentas desde login_accounts.json
        accounts = load_accounts()
        
        # Listar sesiones disponibles
        sessions_dir = Path("sessions")
        available_sessions = []
        if sessions_dir.exists():
            available_sessions = [f.name for f in sessions_dir.iterdir() if f.is_file()]
        
        # Directorio de datos de warmup
        warmup_data_dir = Path("warmup_data")
        warmup_data_dir.mkdir(exist_ok=True)
        
        # Información a mostrar y retornar
        accounts_info = []
        
        print("\n=== CUENTAS DISPONIBLES ===")
        print(f"{'#':<3} {'Usuario':<30} {'Sesión':<10} {'Warmup':<10} {'Fase/Día':<10} {'Descripción':<30}")
        print("-" * 95)
        
        for i, account in enumerate(accounts, 1):
            username = account.get("username", "")
            description = account.get("description", "")
            
            # Verificar si tiene sesión guardada
            has_session = "Sí" if username in available_sessions or any(username in s for s in available_sessions) else "No"
            
            # Verificar si tiene datos de warmup
            warmup_file = warmup_data_dir / f"{username}_warmup.json"
            has_warmup = "No"
            warmup_phase = "-"
            
            if warmup_file.exists():
                try:
                    with open(warmup_file, 'r', encoding='utf-8') as f:
                        warmup_data = json.load(f)
                    has_warmup = "Sí"
                    warmup_phase = f"{warmup_data.get('current_phase', 1)}/{warmup_data.get('current_day', 1)}"
                except:
                    pass
            
            print(f"{i:<3} {username:<30} {has_session:<10} {has_warmup:<10} {warmup_phase:<10} {description:<30}")
            
            # Guardar información para retornar
            accounts_info.append({
                "index": i,
                "username": username,
                "has_session": has_session == "Sí",
                "has_warmup": has_warmup == "Sí",
                "warmup_phase": warmup_phase,
                "description": description
            })
        
        print("-" * 95)
        return accounts_info
        
    except Exception as e:
        logger.error(f"Error al listar cuentas: {e}")
        return []

# Función para iniciar navegador con una sesión guardada
async def setup_browser_session(username, headless=False, use_proxy=False):
    """
    Configura el navegador con una sesión guardada.
    
    Args:
        username: Nombre de usuario para cargar la sesión
        headless: Si se ejecuta en modo sin interfaz gráfica
        use_proxy: Si se usa proxy
        
    Returns:
        tuple: (playwright, browser, context, page) o None si hay error
    """
    from playwright.async_api import async_playwright
    
    try:
        # Buscar sesión para el usuario
        session_path = find_user_session(username)
        if not session_path:
            logger.error(f"No se encontró sesión para {username}")
            return None
        
        # Cargar datos de sesión
        session_data = load_session(username=username)
        
        # Configurar o despejar proxy
        proxy_config = None
        if use_proxy:
            logger.info("Configurando proxy")
            try:
                # Importar getRandomProxy si existe
                try:
                    from app.config.proxy import get_random_proxy
                    proxy_config = get_random_proxy()
                except ImportError:
                    proxy_config = get_proxy_config()
                
                if proxy_config:
                    logger.info(f"Proxy configurado: {proxy_config.get('server', '')}")
                else:
                    logger.warning("No se obtuvo proxy, continuando sin proxy")
            except Exception as e:
                logger.error(f"Error al configurar proxy: {e}")
        
        # Iniciar Playwright
        playwright = await async_playwright().start()
        
        # Argumentos del navegador para evitar detección
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        # Lanzar navegador
        browser = await playwright.chromium.launch(
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
        
        # Navegar a la URL principal
        try:
            await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
        except Exception as e:
            logger.warning(f"Advertencia al navegar a home: {e}")
        
        # Esperar un momento para que la página se estabilice
        await asyncio.sleep(3)
        
        # Tomar captura de pantalla para verificar estado
        screenshot_dir = Path('browser_screenshots')
        screenshot_dir.mkdir(exist_ok=True)
        screenshot_path = str(screenshot_dir / f'session_loaded_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        await page.screenshot(path=screenshot_path)
        
        # Verificar sesión
        page_analysis = await analyze_page_structure(page)
        if not page_analysis['indicators']:
            logger.warning("No se detectaron indicadores de sesión activa")
            # Continuar de todos modos, podría ser un problema en la detección
        
        logger.info(f"Sesión de {username} iniciada correctamente")
        return playwright, browser, context, page
        
    except Exception as e:
        logger.error(f"Error al configurar sesión: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Función principal para ejecutar el warmup
async def run_warmup(username, phase=None, day=None, headless=False, use_proxy=False, auto_close=False):
    """
    Ejecuta el proceso de warmup para una cuenta.
    
    Args:
        username: Nombre de usuario para ejecutar warmup
        phase: Fase específica a ejecutar (opcional)
        day: Día específico de la fase (opcional, requiere phase)
        headless: Si se ejecuta en modo sin interfaz gráfica
        use_proxy: Si se usa proxy
        auto_close: Si se cierra automáticamente al terminar
        
    Returns:
        bool: True si fue exitoso, False en caso contrario
    """
    # Importar la clase XWarmup
    try:
        from app.actions.x_warmup import XWarmup
    except ImportError:
        try:
            # Intento alternativo por si el archivo está en otra ubicación
            from x_warmup import XWarmup
        except ImportError:
            logger.error("No se pudo importar la clase XWarmup. Verifique la instalación")
            return False
    
    resources = None
    
    try:
        # Configurar navegador y sesión
        resources = await setup_browser_session(username, headless, use_proxy)
        if not resources:
            logger.error("No se pudo iniciar la sesión. Abortando warmup")
            return False
        
        playwright, browser, context, page = resources
        
        # Inicializar XWarmup
        warmup = XWarmup(page, username)
        
        # MODIFICADO: Permitir especificar fase y/o día
        if phase is not None:
            warmup.current_phase = phase
            
            # Si se especificó día, usarlo, de lo contrario resetear a día 1
            if day is not None:
                # Validar que el día esté en rango (1-3)
                if day < 1 or day > 3:
                    logger.warning(f"Día {day} fuera de rango. Se establece día 1.")
                    day = 1
                warmup.current_day = day
            else:
                warmup.current_day = 1
                
            # Actualizar datos en el warmup
            warmup.warmup_data["current_phase"] = phase
            warmup.warmup_data["current_day"] = warmup.current_day
            
            logger.info(f"Sobrescribiendo a Fase {phase}, Día {warmup.current_day} por parámetro explícito")
        else:
            # Si solo se especificó día sin fase, advertir
            if day is not None:
                logger.warning("Se especificó --day sin --phase. El parámetro --day será ignorado.")
                
            logger.info(f"Continuando con Fase {warmup.current_phase}, Día {warmup.current_day} según historial")
        
        # Mostrar estado actual del warmup
        warmup.print_warmup_status()
        
        # Aquí NO preguntamos si desea continuar, ejecutar directamente
        logger.info("\nIniciando sesión de warmup...")
        
        # Ejecutar warmup
        result = await warmup.execute_warmup()
        
        # Mostrar resultados
        if result["status"] == "success":
            logger.info(f"\nSesión de warmup completada: {result['message']}")
            
            actions = result["results"]["actions"]
            logger.info("\nAcciones realizadas:")
            logger.info(f"  Visitas a perfiles: {len(actions['profile_visits'])}")
            logger.info(f"  Scrolls en feed: {actions['feed_activity'].get('scrolls_performed', 0)}")
            logger.info(f"  Follows realizados: {len(actions['follows'])}")
            
            total_likes = sum(like.get('count', 0) for like in actions['likes'])
            logger.info(f"  Likes dados: {total_likes}")
            
            if actions['comments']:
                logger.info(f"  Comentarios realizados: {len(actions['comments'])}")
                
            print(f"\nSesión de warmup completada: {result['message']}")
            print("\nAcciones realizadas:")
            print(f"  Visitas a perfiles: {len(actions['profile_visits'])}")
            print(f"  Scrolls en feed: {actions['feed_activity'].get('scrolls_performed', 0)}")
            print(f"  Follows realizados: {len(actions['follows'])}")
            print(f"  Likes dados: {total_likes}")
            
            if actions['comments']:
                print(f"  Comentarios realizados: {len(actions['comments'])}")
        else:
            logger.error(f"\nError: {result['message']}")
            print(f"\nError: {result['message']}")
        
        # Actualizar la sesión antes de cerrar
        try:
            session_path = find_user_session(username)
            if session_path:
                logger.info("Actualizando estado de la sesión...")
                await update_session_file(context, page, session_path, username)
        except Exception as e:
            logger.error(f"Error al actualizar sesión: {e}")
        
        # Si no es autoclose, esperar confirmación para cerrar
        if not auto_close:
            print("\nPresiona Enter para cerrar el navegador...")
            await asyncio.get_event_loop().run_in_executor(None, input)
        
        return result["status"] == "success"
        
    except Exception as e:
        logger.error(f"Error durante el proceso de warmup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
    finally:
        # Limpiar recursos
        if resources:
            playwright, browser, context, page = resources
            
            try:
                # Cerrar página, contexto y navegador en ese orden
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()
                logger.info("Recursos del navegador liberados correctamente")
            except Exception as e:
                logger.error(f"Error al cerrar recursos: {e}")

# Función principal
async def main():
    """
    Punto de entrada principal del script.
    
    Gestiona los argumentos de línea de comandos y ejecuta el proceso de warmup.
    """
    parser = argparse.ArgumentParser(description='X.com Warmup System - Sistema gradual de aclimatación para cuentas')
    parser.add_argument('--username', '-u', type=str, help='Nombre de usuario específico para cargar su sesión')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], default=None, help='Fase específica a ejecutar (1-3)')
    parser.add_argument('--day', type=int, choices=[1, 2, 3], default=None, help='Día específico a ejecutar (1-3, requiere --phase)')
    parser.add_argument('--no-proxy', action='store_true', help='Desactivar el uso de proxies')
    parser.add_argument('--list', '-l', action='store_true', help='Listar cuentas disponibles y su estado de warmup')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    parser.add_argument('--auto-close', action='store_true', help='Cerrar automáticamente al finalizar')
    
    args = parser.parse_args()
    
    # Si solo queremos listar cuentas
    if args.list:
        accounts_info = list_accounts_with_warmup_status()
        return 0
    
    # Determinar username
    username = args.username
    
    if not username:
        # Mostrar cuentas disponibles
        accounts_info = list_accounts_with_warmup_status()
        
        if not accounts_info:
            logger.error("No hay cuentas disponibles")
            return 1
        
        # Solicitar selección una sola vez, antes del warmup
        try:
            selected_index = int(input("\nSelecciona el número de cuenta a utilizar: "))
            if 1 <= selected_index <= len(accounts_info):
                selected_account = accounts_info[selected_index - 1]
                username = selected_account["username"]
                logger.info(f"Cuenta seleccionada: {username}")
            else:
                logger.error(f"Índice fuera de rango: {selected_index}")
                return 1
        except ValueError:
            logger.error("Entrada inválida. Debe ser un número")
            return 1
    
    # Ejecutar warmup
    success = await run_warmup(
        username=username,
        phase=args.phase,
        day=args.day,  # Nuevo parámetro para especificar día
        headless=args.headless,
        use_proxy=not args.no_proxy,
        auto_close=args.auto_close
    )
    
    return 0 if success else 1

# Punto de entrada
if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)