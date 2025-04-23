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
            from app.login.login_sesion_iniciada import open_browser_with_session, list_sessions
            
            # Si se solicita listar las sesiones
            if args.list:
                session_name = list_sessions()
                if not session_name:
                    logger.info("No se seleccionó ninguna sesión. Saliendo...")
                    return
                
                # Usar la sesión seleccionada desde la lista
                await open_browser_with_session(
                    headless=args.headless,
                    url=args.url,
                    specific_session=session_name,
                    keep_open=not args.autoclose
                )
            else:
                # Usar los parámetros específicos si se proporcionan
                await open_browser_with_session(
                    headless=args.headless,
                    url=args.url,
                    username=args.account,
                    specific_session=args.session,
                    keep_open=not args.autoclose
                )
            
        else:
            # Si no se especifica comando, mostrar ayuda
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
    
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