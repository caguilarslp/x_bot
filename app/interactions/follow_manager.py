#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple para seguir un perfil y extraer URLs de publicaciones en X.com
"""

import os
import asyncio
import argparse
import json
import logging
import random
from datetime import datetime
from pathlib import Path

# Corregir la importación para que funcione desde cualquier ubicación
import sys
# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

try:
    from app.login.login_sesion import (
        load_accounts, 
        select_account, 
        load_session,
        get_proxy_config,
        update_session_file,
        find_user_session
    )
except ImportError:
    # Alternativa si falla la primera importación
    print("Intentando importación alternativa...")
    # Asumiendo que estamos en app/interactions/ y queremos importar de app/login/
    login_sesion_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../login"))
    sys.path.insert(0, login_sesion_path)
    from login_sesion import (
        load_accounts, 
        select_account, 
        load_session,
        get_proxy_config,
        update_session_file,
        find_user_session
    )

from playwright.async_api import async_playwright

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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
        # 1. Navegar al perfil
        target_username = target_username.lstrip('@')
        profile_url = f"https://x.com/{target_username}"
        print(f"Navegando a: {profile_url}")
        
        await page.goto(profile_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # Esperar a que cargue
        
        # 2. Verificar si ya lo seguimos
        following_button = page.locator(f'//button[contains(@aria-label, "Following @{target_username}")]')
        following_count = await following_button.count()
        
        if following_count > 0:
            print(f"✓ Ya estás siguiendo a @{target_username}")
            result["was_following"] = True
        else:
            # 3. Si no lo seguimos, hacer clic en el botón Follow
            follow_button = page.locator(f'//button[contains(@aria-label, "Follow @{target_username}")]')
            follow_count = await follow_button.count()
            
            if follow_count > 0:
                print(f"Siguiendo a @{target_username}...")
                await follow_button.first.click()
                await asyncio.sleep(2)  # Esperar a que se procese
                
                # Verificar que ahora lo seguimos
                following_after = page.locator(f'//button[contains(@aria-label, "Following @{target_username}")]')
                if await following_after.count() > 0:
                    print(f"✓ Ahora estás siguiendo a @{target_username}")
                    result["followed"] = True
                else:
                    print(f"✗ Error al seguir a @{target_username}")
            else:
                print(f"✗ No se encontró el botón para seguir a @{target_username}")
        
        # 4. Extraer URLs de publicaciones
        print(f"Extrayendo publicaciones de @{target_username}...")
        
        seen_urls = set()  # Para evitar duplicados
        
        # 5. Hacer scroll y extraer
        for i in range(scroll_times):
            print(f"Scroll {i+1}/{scroll_times}...")
            
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
        
        # 6. Guardar las URLs en un archivo JSON
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
        
        print(f"✓ Se extrajeron {len(result['urls_extracted'])} publicaciones")
        print(f"✓ Guardadas en: {filepath}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        result["status"] = "error"
        result["error_message"] = str(e)
    
    return result

async def main():
    parser = argparse.ArgumentParser(description="Seguir usuario y extraer publicaciones en X.com")
    parser.add_argument("username", nargs="?", help="Usuario a seguir y extraer (sin @)")
    parser.add_argument("--account", type=str, help="Cuenta de X.com a usar")
    parser.add_argument("--scrolls", type=int, default=5, help="Número de scrolls a realizar")
    parser.add_argument("--headless", action="store_true", help="Ejecutar en modo sin interfaz gráfica")
    args = parser.parse_args()
    
    # Verificar si se proporcionó el nombre de usuario
    if not args.username:
        print("Error: Debes proporcionar un nombre de usuario")
        parser.print_help()
        return
    
    # 1. Seleccionar cuenta a usar
    accounts = load_accounts()
    if not accounts:
        print("Error: No hay cuentas disponibles")
        return
    
    login_username = args.account
    if not login_username:
        login_username = select_account(accounts)
        if not login_username:
            print("Error: No se seleccionó ninguna cuenta")
            return
    
    print(f"Usando cuenta: {login_username}")
    
    # 2. Iniciar navegador con la sesión
    async with async_playwright() as p:
        # Cargar sesión
        session_data = load_session(login_username)
        proxy_config = get_proxy_config()
        
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
            # 3. Seguir y extraer
            result = await follow_and_extract(page, args.username, args.scrolls)
            
            # 4. Actualizar sesión
            session_path = find_user_session(login_username)
            if session_path:
                print("Actualizando sesión...")
                await update_session_file(context, page, session_path, login_username)
                print("✓ Sesión actualizada")
            
            print("¡Proceso completado!")
            if args.headless:
                # Si es headless cerrar automáticamente
                await browser.close()
            else:
                # Si no es headless, permitir cerrar manualmente
                print("\nPresiona Enter para cerrar...")
                await asyncio.get_event_loop().run_in_executor(None, input)
                await browser.close()
            
        except Exception as e:
            logger.error(f"Error en el proceso: {e}")
            # Asegurar que se actualice la sesión incluso si hay error
            try:
                session_path = find_user_session(login_username)
                if session_path:
                    await update_session_file(context, page, session_path, login_username)
            except:
                pass
            
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")