#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
X.com Bot - Herramienta de automatización para interacciones en X.com
"""

import os
import argparse
import asyncio
import logging
from app.config.proxy import get_random_proxy

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("x_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Función principal
async def main():
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(description="Bot de Automatización para X.com")
    parser.add_argument('--no-proxy', action='store_true', help='Desactivar el uso de proxies')
    parser.add_argument('--proxy-country', type=str, default='mexico', choices=['mexico', 'united_states', 'spain'],
                        help='País del proxy a utilizar (por defecto: mexico)')
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
    # Comando: login - Iniciar sesión manualmente
    login_parser = subparsers.add_parser('login', help='Iniciar sesión manualmente')
    
    # Comando: session - Usar sesión guardada
    session_parser = subparsers.add_parser('session', help='Usar sesión guardada')
    session_parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    session_parser.add_argument('--url', type=str, help='URL a la que navegar (por defecto: https://x.com/home)')
    session_parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de cargar')
    session_parser.add_argument('--list', action='store_true', help='Listar todas las sesiones disponibles')
    session_parser.add_argument('--account', type=str, help='Nombre de usuario específico para cargar su sesión')
    session_parser.add_argument('--session', type=str, help='Nombre específico del archivo de sesión a usar')
    
    # Comando: profile - Actualizar perfil de una cuenta
    profile_parser = subparsers.add_parser('profile', help='Actualizar perfil de una cuenta')
    profile_parser.add_argument('--account', type=str, help='Nombre de usuario (recover_user) cuyo perfil se actualizará')
    profile_parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    profile_parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de actualizar el perfil')
    
    args = parser.parse_args()
    
    # Configurar uso de proxy si está habilitado
    use_proxy = not args.no_proxy
    
    if use_proxy:
        logger.info(f"Configurando proxy del país: {args.proxy_country}")
        try:
            proxy_config = get_random_proxy(country=args.proxy_country)
            if proxy_config:
                # Configurar variables de entorno para que los módulos puedan usar el proxy
                os.environ["USE_PROXY"] = "true"
                os.environ["PROXY_SERVER"] = proxy_config.get("server", "")
                os.environ["PROXY_USERNAME"] = proxy_config.get("username", "")
                os.environ["PROXY_PASSWORD"] = proxy_config.get("password", "")
                if "type" in proxy_config:
                    os.environ["PROXY_TYPE"] = proxy_config.get("type", "")
                logger.info(f"Proxy configurado: {proxy_config['server']}")
            else:
                logger.warning(f"No se pudo obtener un proxy para {args.proxy_country}")
        except Exception as e:
            logger.error(f"Error al configurar proxy: {e}")
    else:
        # Si se especifica --no-proxy, nos aseguramos de que las variables de entorno no estén configuradas
        logger.info("Uso de proxies desactivado")
        os.environ.pop("USE_PROXY", None)
        os.environ.pop("PROXY_SERVER", None)
        os.environ.pop("PROXY_USERNAME", None)
        os.environ.pop("PROXY_PASSWORD", None)
        os.environ.pop("PROXY_TYPE", None)
    
    try:
        # Ejecutar comando seleccionado
        if args.command == 'login':
            # Iniciar sesión manual
            from app.login.login_manual import manual_login
            await manual_login()
            
        elif args.command == 'session':
            # Cargar sesión guardada
            from app.login.login_sesion import open_browser_with_session, list_sessions
            
            # Si se solicita listar las sesiones
            if args.list:
                list_sessions()
                return
            
            # Usar los parámetros específicos si se proporcionan
            await open_browser_with_session(
                headless=args.headless,
                url=args.url,
                username=args.account,
                specific_session=args.session,
                keep_open=not args.autoclose
            )
        
        elif args.command == 'profile':
            # Actualizar perfil
            from app.login.login_sesion import open_browser_with_session, load_accounts, select_account, get_recover_user
            from app.actions.profile_actions import ProfileActions
            
            # Cargar cuentas
            accounts = load_accounts()
            if not accounts:
                logger.error("No se encontraron cuentas en login_accounts.json. Saliendo...")
                return
            
            # Usar el recover_user proporcionado o mostrar selección si no se proporciona
            recover_user = args.account
            username = None
            
            if recover_user:
                # Buscar el username correspondiente al recover_user
                for account in accounts:
                    if account.get("recover_user") == recover_user:
                        username = account.get("username")
                        break
                
                if not username:
                    logger.error(f"No se encontró ninguna cuenta con recover_user={recover_user} en login_accounts.json")
                    return
                
                logger.info(f"Usando cuenta {username} para actualizar perfil de {recover_user}")
            else:
                # Si no se proporciona recover_user, mostrar selección de cuentas
                username = select_account(accounts)
                if username:
                    # Buscar el recover_user correspondiente al username
                    for account in accounts:
                        if account.get("username") == username:
                            recover_user = account.get("recover_user")
                            break
                    
                    if not recover_user:
                        logger.error(f"No se encontró recover_user para la cuenta {username}")
                        return
                else:
                    logger.info("No se seleccionó ninguna cuenta. Saliendo...")
                    return
            
            # Abrir navegador con la sesión pero sin esperar a que el usuario lo cierre
            # Esto evitará que la página se cierre antes de que podamos usarla
            browser = None
            context = None
            page = None
            
            try:
                # Importar PlayWright aquí para usar su API directamente
                from playwright.async_api import async_playwright
                
                # Más control sobre la creación del navegador y la página
                async with async_playwright() as p:
                    # Configurar variables para la sesión
                    from app.login.login_sesion import get_proxy_config, load_session, find_user_session
                    
                    # Cargar sesión
                    session_data = load_session(username)
                    
                    # Obtener configuración de proxy
                    proxy_config = get_proxy_config()
                    
                    # Configurar el navegador con anti-detección
                    browser_args = [
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                    
                    # Iniciar navegador
                    logger.info("Iniciando navegador para actualización de perfil...")
                    browser = await p.chromium.launch(
                        headless=args.headless,
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
                    
                    # Crear contexto
                    context = await browser.new_context(**context_params)
                    
                    # Agregar scripts anti-detección
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
                    
                    # Crear página
                    page = await context.new_page()
                    
                    # Navegar a la página de inicio
                    logger.info("Navegando a X.com/home...")
                    await page.goto("https://x.com/home", wait_until="domcontentloaded")
                    
                    # Esperar a que la página cargue completamente
                    await asyncio.sleep(5)
                    
                    # Verificar que estamos conectados correctamente
                    # Tomar captura de pantalla para verificar
                    screenshot_dir = "browser_screenshots"
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"profile_update_{recover_user}_{username.replace('@', '_')}.png")
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Captura de pantalla guardada en: {screenshot_path}")
                    
                    # Crear instancia de ProfileActions y actualizar perfil
                    logger.info(f"Iniciando actualización de perfil para {recover_user}...")
                    profile_actions = ProfileActions(page)
                    result = await profile_actions.update_profile(recover_user)
                    
                    # Mostrar resultado
                    if result["status"] == "success":
                        logger.info(f"Perfil de {recover_user} actualizado correctamente")
                        print(f"\n✅ Perfil de {recover_user} actualizado correctamente.")
                        if "fields_updated" in result:
                            print("Campos actualizados:")
                            for field in result["fields_updated"]:
                                print(f"- {field}")
                    else:
                        logger.error(f"Error al actualizar perfil de {recover_user}: {result['message']}")
                        print(f"\n❌ Error al actualizar perfil de {recover_user}: {result['message']}")
                    
                    # Si no es autoclose, esperar a que el usuario cierre manualmente
                    if not args.autoclose:
                        await asyncio.sleep(1)  # Pequeña pausa
                        print("\nPerfil actualizado. Presiona Enter para cerrar el navegador...")
                        await asyncio.get_event_loop().run_in_executor(None, input, "")
            
            except Exception as e:
                logger.error(f"Error en el proceso de actualización de perfil: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            finally:
                # Cerrar todo
                try:
                    if page:
                        logger.info("Cerrando página...")
                        await page.close()
                    if context:
                        logger.info("Cerrando contexto...")
                        await context.close()
                    if browser:
                        logger.info("Cerrando navegador...")
                        await browser.close()
                except Exception as e:
                    logger.error(f"Error al cerrar el navegador: {e}")
        
        else:
            # Si no se especifica comando, mostrar ayuda
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Limpiar variables de entorno de proxy
        os.environ.pop("USE_PROXY", None)
        os.environ.pop("PROXY_SERVER", None)
        os.environ.pop("PROXY_USERNAME", None)
        os.environ.pop("PROXY_PASSWORD", None)
        os.environ.pop("PROXY_TYPE", None)

# Punto de entrada
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.error(f"Error inesperado: {e}", exc_info=True)

# #!/usr/bin/env python
# # -*- coding: utf-8 -*-

# """
# X.com Bot - Herramienta de automatización para interacciones en X.com
# """

# import os
# import argparse
# import asyncio
# import logging
# from app.config.proxy import get_random_proxy

# # Configuración de logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("x_bot.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# # Función principal
# async def main():
#     # Configurar el parser de argumentos
#     parser = argparse.ArgumentParser(description="Bot de Automatización para X.com")
#     parser.add_argument('--no-proxy', action='store_true', help='Desactivar el uso de proxies')
#     parser.add_argument('--proxy-country', type=str, default='mexico', choices=['mexico', 'united_states', 'spain'],
#                         help='País del proxy a utilizar (por defecto: mexico)')
    
#     subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
#     # Comando: login - Iniciar sesión manualmente
#     login_parser = subparsers.add_parser('login', help='Iniciar sesión manualmente')
    
#     # Comando: session - Usar sesión guardada
#     session_parser = subparsers.add_parser('session', help='Usar sesión guardada')
#     session_parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
#     session_parser.add_argument('--url', type=str, help='URL a la que navegar (por defecto: https://x.com/home)')
#     session_parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de cargar')
#     session_parser.add_argument('--list', action='store_true', help='Listar todas las sesiones disponibles')
#     session_parser.add_argument('--account', type=str, help='Nombre de usuario específico para cargar su sesión')
#     session_parser.add_argument('--session', type=str, help='Nombre específico del archivo de sesión a usar')
    
#     args = parser.parse_args()
    
#     # Configurar uso de proxy si está habilitado
#     use_proxy = not args.no_proxy
    
#     if use_proxy:
#         logger.info(f"Configurando proxy del país: {args.proxy_country}")
#         try:
#             proxy_config = get_random_proxy(country=args.proxy_country)
#             if proxy_config:
#                 # Configurar variables de entorno para que los módulos puedan usar el proxy
#                 os.environ["USE_PROXY"] = "true"
#                 os.environ["PROXY_SERVER"] = proxy_config.get("server", "")
#                 os.environ["PROXY_USERNAME"] = proxy_config.get("username", "")
#                 os.environ["PROXY_PASSWORD"] = proxy_config.get("password", "")
#                 if "type" in proxy_config:
#                     os.environ["PROXY_TYPE"] = proxy_config.get("type", "")
#                 logger.info(f"Proxy configurado: {proxy_config['server']}")
#             else:
#                 logger.warning(f"No se pudo obtener un proxy para {args.proxy_country}")
#         except Exception as e:
#             logger.error(f"Error al configurar proxy: {e}")
#     else:
#         # Si se especifica --no-proxy, nos aseguramos de que las variables de entorno no estén configuradas
#         logger.info("Uso de proxies desactivado")
#         os.environ.pop("USE_PROXY", None)
#         os.environ.pop("PROXY_SERVER", None)
#         os.environ.pop("PROXY_USERNAME", None)
#         os.environ.pop("PROXY_PASSWORD", None)
#         os.environ.pop("PROXY_TYPE", None)
    
#     try:
#         # Ejecutar comando seleccionado
#         if args.command == 'login':
#             # Iniciar sesión manual
#             from app.login.login_manual import manual_login
#             await manual_login()
            
#         elif args.command == 'session':
#             # Cargar sesión guardada
#             from app.login.login_sesion import open_browser_with_session, list_sessions
            
#             # Si se solicita listar las sesiones
#             if args.list:
#                 session_name = list_sessions()
#                 if not session_name:
#                     logger.info("No se seleccionó ninguna sesión. Saliendo...")
#                     return
                
#                 # Usar la sesión seleccionada desde la lista
#                 await open_browser_with_session(
#                     headless=args.headless,
#                     url=args.url,
#                     specific_session=session_name,
#                     keep_open=not args.autoclose
#                 )
#             else:
#                 # Usar los parámetros específicos si se proporcionan
#                 await open_browser_with_session(
#                     headless=args.headless,
#                     url=args.url,
#                     username=args.account,
#                     specific_session=args.session,
#                     keep_open=not args.autoclose
#                 )
            
#         else:
#             # Si no se especifica comando, mostrar ayuda
#             parser.print_help()
    
#     except Exception as e:
#         logger.error(f"Error durante la ejecución: {e}")
    
#     finally:
#         # Limpiar variables de entorno de proxy
#         os.environ.pop("USE_PROXY", None)
#         os.environ.pop("PROXY_SERVER", None)
#         os.environ.pop("PROXY_USERNAME", None)
#         os.environ.pop("PROXY_PASSWORD", None)
#         os.environ.pop("PROXY_TYPE", None)

# # Punto de entrada
# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\nOperación interrumpida por el usuario")
#     except Exception as e:
#         print(f"\nError inesperado: {e}")
#         logger.error(f"Error inesperado: {e}", exc_info=True)

# #!/usr/bin/env python
# # -*- coding: utf-8 -*-

# """
# X.com Bot - Herramienta de automatización para interacciones en X.com
# """

# import os
# import argparse
# import asyncio
# import logging
# from app.config.proxy import get_random_proxy

# # Configuración de logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("x_bot.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# # Función principal
# async def main():
#     # Configurar el parser de argumentos
#     parser = argparse.ArgumentParser(description="Bot de Automatización para X.com")
#     parser.add_argument('--no-proxy', action='store_true', help='Desactivar el uso de proxies')
#     parser.add_argument('--proxy-country', type=str, default='mexico', choices=['mexico', 'united_states', 'spain'],
#                         help='País del proxy a utilizar (por defecto: mexico)')
    
#     subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
#     # Comando: login - Iniciar sesión manualmente
#     login_parser = subparsers.add_parser('login', help='Iniciar sesión manualmente')
    
#     # Comando: session - Usar sesión guardada
#     session_parser = subparsers.add_parser('session', help='Usar sesión guardada')
#     session_parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
#     session_parser.add_argument('--url', type=str, help='URL a la que navegar (por defecto: https://x.com/home)')
#     session_parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de cargar')
    
#     args = parser.parse_args()
    
#     # Configurar uso de proxy si está habilitado
#     use_proxy = not args.no_proxy
    
#     if use_proxy:
#         logger.info(f"Configurando proxy del país: {args.proxy_country}")
#         try:
#             proxy_config = get_random_proxy(country=args.proxy_country)
#             if proxy_config:
#                 # Configurar variables de entorno para que los módulos puedan usar el proxy
#                 os.environ["USE_PROXY"] = "true"
#                 os.environ["PROXY_SERVER"] = proxy_config.get("server", "")
#                 os.environ["PROXY_USERNAME"] = proxy_config.get("username", "")
#                 os.environ["PROXY_PASSWORD"] = proxy_config.get("password", "")
#                 if "type" in proxy_config:
#                     os.environ["PROXY_TYPE"] = proxy_config.get("type", "")
#                 logger.info(f"Proxy configurado: {proxy_config['server']}")
#             else:
#                 logger.warning(f"No se pudo obtener un proxy para {args.proxy_country}")
#         except Exception as e:
#             logger.error(f"Error al configurar proxy: {e}")
#     else:
#         # Si se especifica --no-proxy, nos aseguramos de que las variables de entorno no estén configuradas
#         logger.info("Uso de proxies desactivado")
#         os.environ.pop("USE_PROXY", None)
#         os.environ.pop("PROXY_SERVER", None)
#         os.environ.pop("PROXY_USERNAME", None)
#         os.environ.pop("PROXY_PASSWORD", None)
#         os.environ.pop("PROXY_TYPE", None)
    
#     try:
#         # Ejecutar comando seleccionado
#         if args.command == 'login':
#             # Iniciar sesión manual
#             from app.login.login_manual import manual_login
#             await manual_login()
            
#         elif args.command == 'session':
#             # Cargar sesión guardada
#             from app.login.login_sesion_iniciada import open_browser_with_session
            
#             # Las opciones de cuenta/sesión ya se manejan dentro de la función
#             await open_browser_with_session(
#                 headless=args.headless,
#                 url=args.url,
#                 keep_open=not args.autoclose
#             )
            
#         else:
#             # Si no se especifica comando, mostrar ayuda
#             parser.print_help()
    
#     except Exception as e:
#         logger.error(f"Error durante la ejecución: {e}")
    
#     finally:
#         # Limpiar variables de entorno de proxy
#         os.environ.pop("USE_PROXY", None)
#         os.environ.pop("PROXY_SERVER", None)
#         os.environ.pop("PROXY_USERNAME", None)
#         os.environ.pop("PROXY_PASSWORD", None)
#         os.environ.pop("PROXY_TYPE", None)

# # Punto de entrada
# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except KeyboardInterrupt:
#         print("\nOperación interrumpida por el usuario")
#     except Exception as e:
#         print(f"\nError inesperado: {e}")
#         logger.error(f"Error inesperado: {e}", exc_info=True)