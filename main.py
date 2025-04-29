#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
X.com Bot - Herramienta de automatización para interacciones en X.com
"""

import os
import argparse
import asyncio
import logging
import json
import random
from pathlib import Path
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
    parser.add_argument('--proxy-country', type=str, default='mexico',
                        choices=['mexico', 'united_states', 'spain'],
                        help='País del proxy a utilizar (por defecto: mexico)')
    parser.add_argument('--account', type=str, help='Cuenta a usar')
    parser.add_argument('--headless', action='store_true', help='Modo sin UI')
    parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador')
    
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')

    # Comando: login - Iniciar sesión manualmente
    login_parser = subparsers.add_parser('login', help='Iniciar sesión manualmente')

    # Comando: session - Usar sesión guardada
    session_parser = subparsers.add_parser('session', help='Usar sesión guardada')
    session_parser.add_argument('--url', type=str, help='URL a la que navegar')
    session_parser.add_argument('--list', action='store_true', help='Listar sesiones')
    session_parser.add_argument('--session', type=str, help='Archivo de sesión específico')

    # Comando: profile - Actualizar perfil
    profile_parser = subparsers.add_parser('profile', help='Actualizar perfil de una cuenta')
    profile_parser.add_argument('--account', type=str, help='recover_user cuyo perfil se actualizará')

    # Comando: social - Realizar interacciones sociales
    social_parser = subparsers.add_parser('social', help='Realizar interacciones sociales')
    social_subparsers = social_parser.add_subparsers(dest='social_command', help='Tipo de interacción')
    
    # Subcomando: follow - Seguir a un usuario
    follow_parser = social_subparsers.add_parser('follow', help='Seguir usuario')
    follow_parser.add_argument('username', type=str, help='Usuario a seguir')

    # Subcomando: like - Dar likes a publicaciones de un usuario
    like_parser = social_subparsers.add_parser('like', help='Dar likes a publicaciones')
    like_parser.add_argument('username', type=str, help='Usuario en cuyo perfil dar likes')
    like_parser.add_argument('--count', type=int, default=2, help='Número de likes a dar (por defecto: 2)')
    
    # Subcomando: comment - Comentar en una publicación
    comment_parser = social_subparsers.add_parser('comment', help='Comentar publicación')
    comment_parser.add_argument('username', type=str, help='Usuario en cuyo perfil comentar')
    comment_parser.add_argument('--text', type=str, default="¡Excelente contenido!", help='Texto del comentario')
    
    # Subcomando: batch - Procesar lote de usuarios
    batch_parser = social_subparsers.add_parser('batch', help='Procesar lote de interacciones')
    batch_parser.add_argument('file', type=str, help='Archivo JSON con perfiles (ej: batch_profiles.json)')
    
    # Subcomando: interact - Interacción completa con un usuario (home -> perfil -> follow -> likes -> comment)
    interact_parser = social_subparsers.add_parser('interact', help='Interacción completa con un usuario')
    interact_parser.add_argument('username', type=str, help='Usuario con el que interactuar')
    interact_parser.add_argument('--likes', type=int, default=2, help='Número de likes a dar (por defecto: 2)')
    interact_parser.add_argument('--comment', type=str, help='Texto del comentario (opcional)')

    args = parser.parse_args()

    # Configurar o despejar proxy
    if not args.no_proxy:
        logger.info(f"Configurando proxy para {args.proxy_country}")
        try:
            proxy_config = get_random_proxy(country=args.proxy_country)
            if proxy_config:
                os.environ["USE_PROXY"] = "true"
                os.environ["PROXY_SERVER"] = proxy_config.get("server", "")
                os.environ["PROXY_USERNAME"] = proxy_config.get("username", "")
                os.environ["PROXY_PASSWORD"] = proxy_config.get("password", "")
                if proxy_config.get("type"):
                    os.environ["PROXY_TYPE"] = proxy_config["type"]
                logger.info(f"Proxy configurado: {proxy_config['server']}")
            else:
                logger.warning("No se obtuvo proxy")
        except Exception as e:
            logger.error(f"Error proxy: {e}")
    else:
        logger.info("Uso de proxies desactivado")
        for var in ["USE_PROXY","PROXY_SERVER","PROXY_USERNAME","PROXY_PASSWORD","PROXY_TYPE"]:
            os.environ.pop(var, None)

    try:
        if args.command == 'login':
            # Login manual
            from app.login.login_manual import manual_login
            await manual_login()

        elif args.command == 'session':
            # Sesión guardada
            from app.login.login_sesion import open_browser_with_session, list_sessions
            if args.list:
                list_sessions()
            else:
                await open_browser_with_session(
                    headless=args.headless,
                    url=args.url,
                    username=args.account,
                    specific_session=args.session,
                    keep_open=not args.autoclose
                )

        elif args.command == 'profile':
            # Actualizar perfil
            from app.login.login_sesion import (
                load_accounts,
                select_account,
                load_session,
                find_user_session,
                get_proxy_config,
                update_session_file
            )
            from app.actions.profile_actions import ProfileActions

            # 1) Cargar cuentas
            accounts = load_accounts()
            if not accounts:
                logger.error("No hay cuentas en login_accounts.json")
                return

            # 2) Determinar recover_user y username
            recover_user = args.account
            username = None
            if recover_user:
                for acct in accounts:
                    if acct.get("recover_user") == recover_user:
                        username = acct.get("username")
                        break
                if not username:
                    logger.error(f"No existe recover_user={recover_user}")
                    return
                logger.info(f"Cuenta seleccionada: {username}")
            else:
                username = select_account(accounts)
                if not username:
                    logger.info("Sin selección. Saliendo.")
                    return
                for acct in accounts:
                    if acct.get("username") == username:
                        recover_user = acct.get("recover_user")
                        break

            # 3) Saltar si profile_completed == True
            account_obj = next((a for a in accounts if a.get("recover_user") == recover_user), None)
            if account_obj and account_obj.get("profile_completed", False):
                logger.info(f"Perfil {recover_user} ya completado")
                print(f"✅ Perfil de {recover_user} ya estaba completado.")
                return

            # 4) Abrir navegador con Playwright
            browser = None
            context = None
            page = None
            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    # Cargar session_state
                    session_data = load_session(username)
                    proxy_cfg = get_proxy_config()

                    browser = await p.chromium.launch(
                        headless=args.headless,
                        slow_mo=20,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--no-sandbox',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process'
                        ]
                    )
                    ctx_params = {
                        'viewport': {'width': 1280, 'height': 800},
                        'user_agent': session_data.get('userAgent'),
                        'locale': 'en-US',
                        'timezone_id': 'America/New_York',
                        'storage_state': session_data['sessionState'],
                        'bypass_csp': True,
                        'ignore_https_errors': True
                    }
                    if proxy_cfg:
                        ctx_params['proxy'] = proxy_cfg

                    context = await browser.new_context(**ctx_params)
                    # Anti-detección
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        const orig = window.navigator.permissions.query;
                        window.navigator.permissions.query = params =>
                          params.name === 'notifications'
                            ? Promise.resolve({state: Notification.permission})
                            : orig(params);
                        Object.defineProperty(navigator, 'plugins', {
                          get: () => [1,2,3,4,5].map(() => ({length:1}))
                        });
                    """)

                    page = await context.new_page()
                    await page.goto("https://x.com/home", wait_until="domcontentloaded")
                    await asyncio.sleep(5)

                    # Ejecutar ProfileActions
                    profile_actions = ProfileActions(page, recover_user)
                    result = await profile_actions.update_profile(recover_user)

                    # Mostrar resultado
                    if result["status"] == "success":
                        logger.info("Perfil actualizado")
                        print(f"\n✅ Perfil de {recover_user} actualizado.")
                    else:
                        logger.error("Error perfil: %s", result["message"])
                        print(f"\n❌ Error: {result['message']}")

                    # Actualizar la sesión justo al terminar
                    session_path = find_user_session(username)
                    if session_path:
                        logger.info("Actualizando estado de la sesión tras edición de perfil...")
                        await update_session_file(context, page, session_path, username)

                    # Esperar cierre manual si no autoclose
                    if not args.autoclose:
                        print("\nPresiona Enter para cerrar navegador...")
                        await asyncio.get_event_loop().run_in_executor(None, input, "")

            except Exception as e:
                logger.error("Error proceso profile: %s", e, exc_info=True)
            finally:
                if page:    await page.close()
                if context: await context.close()
                if browser: await browser.close()

        elif args.command == 'social':
            # Importaciones necesarias
            from app.login.login_sesion import (
                load_accounts, 
                select_account, 
                load_session,
                find_user_session,
                get_proxy_config
            )
            from app.actions.social_actions import SocialActions
            
            # 1) Cargar cuentas
            accounts = load_accounts()
            if not accounts:
                logger.error("No hay cuentas en login_accounts.json")
                return
            
            # 2) Determinar username
            username = args.account
            if not username:
                username = select_account(accounts)
                if not username:
                    logger.info("Sin selección. Saliendo.")
                    return
                logger.info(f"Cuenta seleccionada: {username}")
            
            # 3) Para el comando 'social', abrimos la sesión manualmente sin usar open_browser_with_session
            # para tener más control sobre el ciclo de vida de la página
            browser = None
            context = None
            page = None
            
            try:
                from playwright.async_api import async_playwright
                
                async with async_playwright() as p:
                    # Cargar session_state
                    session_data = load_session(username)
                    proxy_cfg = get_proxy_config()
                    
                    # Lanzar el navegador
                    browser = await p.chromium.launch(
                        headless=args.headless,
                        slow_mo=20,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--no-sandbox',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process'
                        ]
                    )
                    
                    # Configurar contexto del navegador
                    ctx_params = {
                        'viewport': {'width': 1280, 'height': 800},
                        'user_agent': session_data.get('userAgent'),
                        'locale': 'en-US',
                        'timezone_id': 'America/New_York',
                        'storage_state': session_data['sessionState'],
                        'bypass_csp': True,
                        'ignore_https_errors': True
                    }
                    
                    if proxy_cfg:
                        ctx_params['proxy'] = proxy_cfg
                        
                    context = await browser.new_context(**ctx_params)
                    
                    # Agregar script anti-detección
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        const orig = window.navigator.permissions.query;
                        window.navigator.permissions.query = params =>
                          params.name === 'notifications'
                            ? Promise.resolve({state: Notification.permission})
                            : orig(params);
                        Object.defineProperty(navigator, 'plugins', {
                          get: () => [1,2,3,4,5].map(() => ({length:1}))
                        });
                    """)
                    
                    # Crear página y navegar a home
                    page = await context.new_page()
                    await page.goto("https://x.com/home", wait_until="domcontentloaded")
                    await asyncio.sleep(3)
                    
                    # Inicializar SocialActions
                    social = SocialActions(page)
                    
                    # Realizar acción según subcomando
                    if args.social_command == 'follow':
                        print(f"\nSiguiendo a usuario: @{args.username}")
                        result = await social.follow_user(args.username)
                        
                        if result["status"] == "success":
                            print(f"✅ Ahora sigues a @{args.username}")
                        elif result["status"] == "info":
                            print(f"ℹ️ {result['message']}")
                        else:
                            print(f"❌ Error: {result['message']}")
                    
                    elif args.social_command == 'like':
                        print(f"\nDando {args.count} likes en el perfil de @{args.username}")
                        
                        # Navegar al perfil
                        success = await social.navigate_to_profile(args.username)
                        if success:
                            # Scroll para ver publicaciones
                            await social._random_scroll(2, 4)
                            
                            # Dar likes
                            result = await social.perform_like(args.count)
                            
                            if result["status"] == "success":
                                print(f"✅ Se dieron {result['statistics']['liked']} likes")
                                if result['statistics']['already_liked'] > 0:
                                    print(f"ℹ️ {result['statistics']['already_liked']} publicaciones ya tenían like")
                            else:
                                print(f"❌ Error: {result['message']}")
                        else:
                            print(f"❌ Error: No se pudo navegar al perfil de @{args.username}")
                    
                    elif args.social_command == 'comment':
                        print(f"\nComentando en el perfil de @{args.username}")
                        
                        # Navegar al perfil
                        success = await social.navigate_to_profile(args.username)
                        if success:
                            # Scroll para ver publicaciones
                            await social._random_scroll(2, 4)
                            
                            # Comentar
                            result = await social.comment_on_post(0, args.text)
                            
                            if result["status"] == "success":
                                print(f"✅ Comentario publicado: '{args.text}'")
                            else:
                                print(f"❌ Error: {result['message']}")
                        else:
                            print(f"❌ Error: No se pudo navegar al perfil de @{args.username}")
                    
                    elif args.social_command == 'batch':
                        # Procesar lote de interacciones
                        from pathlib import Path
                        import json
                        
                        # Buscar archivo
                        batch_file = Path(args.file)
                        if not batch_file.exists():
                            # Intentar en app/config/
                            alt_path = Path('app/config') / batch_file.name
                            if alt_path.exists():
                                batch_file = alt_path
                            else:
                                print(f"❌ Error: Archivo no encontrado: {args.file}")
                                return
                        
                        # Cargar archivo
                        try:
                            with open(batch_file, 'r', encoding='utf-8') as f:
                                batch_data = json.load(f)
                            
                            if "profiles" not in batch_data:
                                print("❌ Error: El archivo debe contener una clave 'profiles'")
                                return
                            
                            profiles = batch_data["profiles"]
                            template = batch_data.get("template", {"follow": True})
                            
                            print(f"\nIniciando procesamiento por lotes de {len(profiles)} perfiles")
                            results = await social.batch_interact(profiles, template)
                            
                            # Guardar resultados
                            results_dir = Path('logs/batch_results')
                            results_dir.mkdir(parents=True, exist_ok=True)
                            
                            results_file = results_dir / f"batch_results_{username}_{batch_file.stem}.json"
                            with open(results_file, 'w', encoding='utf-8') as f:
                                json.dump(results, f, indent=2)
                            
                            print(f"\n✅ Procesamiento por lotes completado:")
                            print(f"   - Exitosos: {results['profiles_processed']}")
                            print(f"   - Fallidos: {results['profiles_failed']}")
                            print(f"   - Resultados guardados en: {results_file}")
                            
                        except Exception as e:
                            logger.error(f"Error en procesamiento por lotes: {e}")
                            print(f"❌ Error: {e}")
                    
                    elif args.social_command == 'interact':
                        print(f"\n🔄 Iniciando interacción natural con @{args.username}")
                        
                        try:
                            # 1. Primero navegar a home y hacer scroll
                            print("📱 Navegando a home...")
                            await page.goto("https://x.com/home", wait_until="domcontentloaded")
                            await asyncio.sleep(random.uniform(2, 4))
                            
                            # Hacer scroll en home
                            print("📜 Explorando timeline...")
                            await social._random_scroll(3, 6)
                            await asyncio.sleep(random.uniform(1, 3))
                            
                            # 2. Navegar al perfil del usuario
                            print(f"🔍 Visitando perfil de @{args.username}...")
                            success = await social.navigate_to_profile(args.username)
                            
                            if success:
                                # 3. Seguir al usuario si no lo seguimos ya
                                print("👥 Verificando seguimiento...")
                                follow_result = await social.follow_user(args.username)
                                
                                if follow_result["status"] == "success":
                                    print(f"✅ Ahora sigues a @{args.username}")
                                elif follow_result["status"] == "info":
                                    print(f"ℹ️ {follow_result['message']}")
                                
                                # Breve pausa después de seguir
                                await asyncio.sleep(random.uniform(2, 5))
                                
                                # 4. Hacer scroll para ver publicaciones
                                print("📜 Explorando publicaciones...")
                                await social._random_scroll(2, 4)
                                
                                # 5. Dar likes a publicaciones
                                if args.likes > 0:
                                    print(f"👍 Dando {args.likes} likes...")
                                    like_result = await social.perform_like(args.likes)
                                    
                                    if like_result["status"] == "success":
                                        print(f"✅ Se dieron {like_result['statistics']['liked']} likes")
                                        if like_result['statistics']['already_liked'] > 0:
                                            print(f"ℹ️ {like_result['statistics']['already_liked']} publicaciones ya tenían like")
                                    else:
                                        print(f"❌ Error al dar likes: {like_result['message']}")
                                
                                # 6. Comentar en una publicación si se especificó un comentario
                                if args.comment:
                                    # Pequeña pausa antes de comentar
                                    await asyncio.sleep(random.uniform(3, 6))
                                    
                                    print(f"💬 Comentando: '{args.comment}'")
                                    comment_result = await social.comment_on_post(0, args.comment)
                                    
                                    if comment_result["status"] == "success":
                                        print(f"✅ Comentario publicado: '{args.comment}'")
                                    else:
                                        print(f"❌ Error al comentar: {comment_result['message']}")
                                
                                print(f"✨ Interacción con @{args.username} completada")
                            else:
                                print(f"❌ Error: No se pudo navegar al perfil de @{args.username}")
                        
                        except Exception as e:
                            logger.error(f"Error en interacción: {e}")
                            print(f"❌ Error durante la interacción: {e}")
                    
                    else:
                        print("\nNo se especificó ninguna acción social.")
                        social_parser.print_help()
                    
                    # Actualizar la sesión antes de cerrar
                    session_path = find_user_session(username)
                    if session_path:
                        from app.login.login_sesion import update_session_file
                        logger.info("Actualizando estado de la sesión...")
                        await update_session_file(context, page, session_path, username)
                    
                    # Esperar confirmación del usuario si no es autoclose
                    if not args.autoclose:
                        print("\nPresiona Enter para cerrar el navegador...")
                        await asyncio.get_event_loop().run_in_executor(None, input, "")
                
            except Exception as e:
                logger.error(f"Error en acciones sociales: {e}", exc_info=True)
                import traceback
                logger.error(traceback.format_exc())
            finally:
                # Cerramos los recursos manualmente para asegurarnos
                if page:
                    try:
                        await page.close()
                        logger.info("Página cerrada.")
                    except Exception as e:
                        logger.error(f"Error al cerrar página: {e}")
                
                if context:
                    try:
                        await context.close()
                        logger.info("Contexto cerrado.")
                    except Exception as e:
                        logger.error(f"Error al cerrar contexto: {e}")
                
                if browser:
                    try:
                        await browser.close()
                        logger.info("Navegador cerrado.")
                    except Exception as e:
                        logger.error(f"Error al cerrar navegador: {e}")

        else:
            parser.print_help()

    except Exception as e:
        logger.error("Error en main: %s", e, exc_info=True)
    finally:
        # Limpiar proxy
        for var in ["USE_PROXY","PROXY_SERVER","PROXY_USERNAME","PROXY_PASSWORD","PROXY_TYPE"]:
            os.environ.pop(var, None)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.error("Error inesperado: %s", e, exc_info=True)

