#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script mejorado para seguir perfiles y extraer URLs de publicaciones en X.com
con soporte para manejo de lista de usuarios, tiempo entre acciones y proxy.
"""

import os
import sys
import asyncio
import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("follow_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración y ruta para la lista de usuarios
USERS_LIST_PATH = Path(project_root) / "app" / "config" / "target_users.json"
USERS_LIST_PATH = USERS_LIST_PATH.resolve()

# Importaciones de proyecto
from app.login.login_sesion import (
    load_accounts, 
    select_account, 
    load_session,
    get_proxy_config,
    update_session_file,
    find_user_session
)
from app.config.proxy import get_best_proxy, get_random_proxy

from playwright.async_api import async_playwright

def load_target_users():
    """
    Cargar lista de usuarios objetivo desde un archivo JSON.
    
    Returns:
        list: Lista de usuarios objetivo
    """
    try:
        # Asegurar que el directorio exista
        USERS_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo si no existe
        if not USERS_LIST_PATH.exists():
            with open(USERS_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump({"users": []}, f, indent=2)
            logger.info(f"Archivo de usuarios creado en {USERS_LIST_PATH}")
        
        with open(USERS_LIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('users', [])
    except Exception as e:
        logger.error(f"Error al cargar usuarios: {e}")
        return []

def add_target_user(username):
    """
    Añadir un usuario a la lista de usuarios objetivo.
    
    Args:
        username (str): Usuario a añadir
    """
    try:
        users = load_target_users()
        
        # Evitar duplicados
        if username not in users:
            users.append(username)
            
            with open(USERS_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump({"users": users}, f, indent=2)
            
            logger.info(f"Usuario {username} añadido a la lista")
            print(f"✓ {username} añadido a la lista de usuarios objetivo")
        else:
            print(f"ℹ️ {username} ya estaba en la lista")
    
    except Exception as e:
        logger.error(f"Error al añadir usuario: {e}")
        print(f"❌ Error al añadir usuario: {e}")

def remove_target_user(username):
    """
    Eliminar un usuario de la lista de usuarios objetivo.
    
    Args:
        username (str): Usuario a eliminar
    """
    try:
        users = load_target_users()
        
        if username in users:
            users.remove(username)
            
            with open(USERS_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump({"users": users}, f, indent=2)
            
            logger.info(f"Usuario {username} eliminado de la lista")
            print(f"✓ {username} eliminado de la lista de usuarios objetivo")
        else:
            print(f"ℹ️ {username} no estaba en la lista")
    
    except Exception as e:
        logger.error(f"Error al eliminar usuario: {e}")
        print(f"❌ Error al eliminar usuario: {e}")

async def follow_and_extract(page, target_username, scroll_times=5):
    """
    Seguir a un usuario (si no lo seguimos ya) y extraer URLs de sus publicaciones.
    
    Args:
        page: Página de Playwright
        target_username: Usuario a seguir y extraer (sin @)
        scroll_times: Número de veces a hacer scroll
        
    Returns:
        dict: Resultado de la operación
    """
    result = {
        "followed": False,
        "was_following": False,
        "urls_extracted": [],
        "status": "success"
    }
    
    try:
        # Navegar al perfil
        target_username = target_username.lstrip('@')
        profile_url = f"https://x.com/{target_username}"
        logger.info(f"Navegando a perfil de @{target_username}")
        print(f"📍 Navegando a: {profile_url}")
        
        await page.goto(profile_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # Esperar a que cargue
        
        # Verificar si ya lo seguimos
        following_button = page.locator(f'//button[contains(@aria-label, "Following @{target_username}")]')
        following_count = await following_button.count()
        
        if following_count > 0:
            logger.info(f"Ya estás siguiendo a @{target_username}")
            print(f"✓ Ya sigues a @{target_username}")
            result["was_following"] = True
        else:
            # Buscar botón Follow
            follow_button = page.locator(f'//button[contains(@aria-label, "Follow @{target_username}")]')
            follow_count = await follow_button.count()
            
            if follow_count > 0:
                logger.info(f"Intentando seguir a @{target_username}")
                print(f"🔗 Siguiendo a @{target_username}...")
                await follow_button.first.click()
                await asyncio.sleep(2)  # Esperar a que se procese
                
                # Verificar que ahora lo seguimos
                following_after = page.locator(f'//button[contains(@aria-label, "Following @{target_username}")]')
                if await following_after.count() > 0:
                    logger.info(f"Follow exitoso para @{target_username}")
                    print(f"✓ Ahora sigues a @{target_username}")
                    result["followed"] = True
                else:
                    logger.warning(f"No se pudo seguir a @{target_username}")
                    print(f"✗ Error al seguir a @{target_username}")
            else:
                logger.warning(f"No se encontró botón de follow para @{target_username}")
                print(f"✗ No se encontró el botón para seguir a @{target_username}")
        
        # Extraer URLs de publicaciones
        logger.info(f"Extrayendo publicaciones de @{target_username}")
        print(f"📋 Extrayendo publicaciones...")
        
        seen_urls = set()  # Para evitar duplicados
        
        # Hacer scroll y extraer
        for i in range(scroll_times):
            print(f"📜 Scroll {i+1}/{scroll_times}...")
            
            # Extraer URLs de publicaciones
            all_links = page.locator('//a[contains(@href, "/status/")]')
            count = await all_links.count()
            
            for j in range(count):
                link = all_links.nth(j)
                href = await link.get_attribute("href")
                
                if href:
                    # Filtrar para obtener solo enlaces principales a posts
                    if '/status/' in href and not any(x in href for x in ['/photo/', '/analytics/', '/video/']):
                        # Normalizar URL
                        full_url = f"https://x.com{href}" if href.startswith('/') else href
                        
                        # Evitar duplicados
                        if full_url not in seen_urls:
                            seen_urls.add(full_url)
                            result["urls_extracted"].append({
                                "url": full_url,
                                "extracted_at": datetime.now().isoformat()
                            })
            
            # Hacer scroll para cargar más contenido
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(random.uniform(1, 3))  # Delay aleatorio entre scrolls
        
        # Guardar las URLs en un archivo JSON
        posts_dir = Path("posts")
        posts_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_username}_posts_{timestamp}.json"
        filepath = posts_dir / filename
        
        data = {
            "username": target_username,
            "extracted_at": datetime.now().isoformat(),
            "post_count": len(result["urls_extracted"]),
            "posts": result["urls_extracted"]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Extracción completada para @{target_username}")
        print(f"✓ Se extrajeron {len(result['urls_extracted'])} publicaciones")
        print(f"✓ Guardadas en: {filepath}")
        
    except Exception as e:
        logger.error(f"Error al procesar @{target_username}: {e}")
        result["status"] = "error"
        result["error_message"] = str(e)
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Seguir usuarios y extraer publicaciones en X.com")
    parser.add_argument("--scrolls", type=int, default=5, help="Número de scrolls a realizar")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo sin interfaz gráfica")
    parser.add_argument("--no-proxy", action="store_true", help="Desactivar uso de proxy")
    
    # Grupo de comandos mutuamente excluyentes
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--add", type=str, help="Añadir usuario a la lista")
    action_group.add_argument("--remove", type=str, help="Eliminar usuario de la lista")
    
    args = parser.parse_args()
    
    # Manejo de añadir/eliminar usuarios
    if args.add:
        add_target_user(args.add)
        return
    
    if args.remove:
        remove_target_user(args.remove)
        return
    
    # Cargar lista de usuarios
    target_users = load_target_users()
    if not target_users:
        print("❌ No hay usuarios en la lista. Usa --add para añadir usuarios.")
        return
    
    # Seleccionar cuentas
    accounts = load_accounts()
    if not accounts:
        print("❌ No hay cuentas disponibles en login_accounts.json")
        return
    
    # Mostrar cuentas para selección
    print("\n=== Cuentas Disponibles ===")
    for i, account in enumerate(accounts, 1):
        username = account.get("username", "Sin nombre de usuario")
        description = account.get("description", "")
        print(f"{i}. {username} - {description}")
    
    # Seleccionar cuenta de login
    while True:
        try:
            account_index = int(input("\nSelecciona el número de cuenta para login (o '0' para salir): "))
            if account_index == 0:
                return
            login_username = accounts[account_index - 1]["username"]
            break
        except (ValueError, IndexError):
            print("❌ Selección inválida. Intenta de nuevo.")
    
    # Ejecución asíncrona del procesamiento
    async def async_main():
        # Iniciar navegador con proxy por defecto
        async with async_playwright() as p:
            # Configurar proxy
            proxy_config = None
            if not args.no_proxy:
                logger.info("Obteniendo proxy...")
                print("🌐 Configurando proxy...")
                proxy_config = get_best_proxy("mexico")
                if not proxy_config:
                    logger.warning("No se pudo obtener proxy, continuando sin proxy")
                    print("⚠️ No se pudo obtener proxy, continuando sin proxy")
            
            try:
                # Cargar sesión
                session_data = load_session(login_username)
                
                # Configurar navegador
                browser = await p.chromium.launch(
                    headless=args.headless,
                    slow_mo=20,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                
                # Configurar contexto
                context_params = {
                    'viewport': {'width': 1280, 'height': 800},
                    'user_agent': session_data.get('userAgent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'),
                    'storage_state': session_data['sessionState'],
                    'bypass_csp': True,
                    'ignore_https_errors': True
                }
                
                if proxy_config:
                    context_params['proxy'] = proxy_config
                
                context = await browser.new_context(**context_params)
                
                # Anti-detección básica
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """)
                
                page = await context.new_page()
                
                try:
                    # Procesar todos los usuarios objetivo
                    for target_username in target_users:
                        logger.info(f"Procesando usuario: @{target_username}")
                        print(f"🔍 Procesando @{target_username}")
                        
                        # Procesar cada usuario
                        await follow_and_extract(page, target_username, args.scrolls)
                        
                        # Tiempo entre acciones
                        action_delay = random.uniform(4, 5)
                        logger.info(f"Esperando {action_delay:.2f} segundos antes del próximo usuario...")
                        await asyncio.sleep(action_delay)
                    
                    # Actualizar sesión
                    session_path = find_user_session(login_username)
                    if session_path:
                        logger.info("Actualizando sesión...")
                        print("🔄 Actualizando sesión...")
                        await update_session_file(context, page, session_path, login_username)
                    
                    print("✅ Proceso completado")
                    
                    # Cerrar navegador
                    await browser.close()
                    
                except Exception as e:
                    logger.error(f"Error durante el proceso: {e}")
                    await browser.close()
            
            except Exception as main_e:
                logger.error(f"Error principal: {main_e}")

    # Ejecutar el bucle de eventos asíncrono
    asyncio.run(async_main())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")