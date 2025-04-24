#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import asyncio
import argparse
import json
import logging
from pathlib import Path
from app.login.login_sesion import open_browser_with_session, load_accounts, select_account
from app.actions.social_actions import SocialActions

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("x_social.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(description="Interacciones Sociales en X.com")
    parser.add_argument('--account', type=str, help='Nombre de usuario específico para cargar su sesión')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    parser.add_argument('--follow', type=str, help='Usuario a seguir')
    parser.add_argument('--unfollow', type=str, help='Usuario a dejar de seguir')
    parser.add_argument('--like', type=str, help='Usuario en cuyo perfil dar likes')
    parser.add_argument('--like-count', type=int, default=2, help='Número de likes a dar (por defecto: 2)')
    parser.add_argument('--comment', type=str, help='Usuario en cuyo perfil comentar')
    parser.add_argument('--comment-text', type=str, default="¡Excelente contenido!", help='Texto del comentario')
    parser.add_argument('--batch', type=str, help='Archivo JSON con lista de usuarios para interacción por lotes')
    
    args = parser.parse_args()

    try:
        # 1. Identificar cuenta a usar
        accounts = load_accounts()
        if not accounts:
            logger.error("No hay cuentas disponibles en login_accounts.json")
            return
        
        username = args.account
        if not username:
            username = select_account(accounts)
            
        if not username:
            logger.error("No se seleccionó ninguna cuenta.")
            return
            
        logger.info(f"Usando cuenta: {username}")
        
        # 2. Abrir navegador con sesión activa
        page = await open_browser_with_session(
            headless=args.headless,
            username=username,
            keep_open=True,
            return_page=True  # Importante: obtener la página para usar en SocialActions
        )
        
        if not page:
            logger.error("No se pudo abrir el navegador con la sesión.")
            return
            
        # 3. Inicializar SocialActions
        actions = SocialActions(page)
        
        # 4. Realizar acciones según parámetros
        
        # Procesamiento por lotes desde archivo
        if args.batch:
            # Buscar el archivo en la ubicación proporcionada o en app/config/
            batch_file = Path(args.batch)
            if not batch_file.exists():
                # Intentar buscar en app/config/
                alt_path = Path('app/config') / Path(args.batch).name
                if alt_path.exists():
                    batch_file = alt_path
                    logger.info(f"Usando archivo de lotes desde ubicación alternativa: {alt_path}")
                else:
                    logger.error(f"Archivo de lotes no encontrado: {args.batch}")
                    # No retornar, continuar con otras acciones si las hay
            
            if batch_file.exists():
                try:
                    with open(batch_file, 'r', encoding='utf-8') as f:
                        batch_data = json.load(f)
                    
                    if isinstance(batch_data, dict) and "profiles" in batch_data:
                        profiles = batch_data["profiles"]
                        template = batch_data.get("template", {"follow": True})
                        
                        logger.info(f"Iniciando procesamiento por lotes de {len(profiles)} perfiles")
                        results = await actions.batch_interact(profiles, template)
                        
                        # Guardar resultados en app/logs/batch_results/
                        results_dir = Path('logs/batch_results')
                        results_dir.mkdir(parents=True, exist_ok=True)
                        
                        results_file = results_dir / f"batch_results_{username}_{batch_file.stem}.json"
                        with open(results_file, 'w', encoding='utf-8') as f:
                            json.dump(results, f, indent=2)
                            
                        logger.info(f"Resultados guardados en {results_file}")
                        print(f"\nProcesamiento por lotes completado: {results['profiles_processed']} exitosos, {results['profiles_failed']} fallidos.")
                        
                    else:
                        logger.error("Formato de archivo de lotes inválido. Debe contener una clave 'profiles' con lista de usuarios.")
                
                except Exception as e:
                    logger.error(f"Error al procesar archivo de lotes: {e}")
        
        # Acción: Follow
        if args.follow:
            print(f"\nSiguiendo a usuario: @{args.follow}")
            result = await actions.follow_user(args.follow)
            
            if result["status"] == "success":
                print(f"✅ Ahora sigues a @{args.follow}")
            elif result["status"] == "info":
                print(f"ℹ️ {result['message']}")
            else:
                print(f"❌ Error: {result['message']}")
        
        # Acción: Unfollow
        if args.unfollow:
            print(f"\nDejando de seguir a usuario: @{args.unfollow}")
            result = await actions.unfollow_user(args.unfollow)
            
            if result["status"] == "success":
                print(f"Has dejado de seguir a @{args.unfollow}")
            elif result["status"] == "info":
                print(f"ℹ️ {result['message']}")
            else:
                print(f"Error: {result['message']}")
        
        # Acción: Like
        if args.like:
            print(f"\nDando {args.like_count} likes en el perfil de @{args.like}")
            
            # Primero navegar al perfil
            success = await actions.navigate_to_profile(args.like)
            
            if success:
                # Realizar scroll para ver publicaciones
                await actions._random_scroll(2, 4)
                
                # Dar likes
                result = await actions.perform_like(args.like_count)
                
                if result["status"] == "success":
                    print(f"Se dieron {result['statistics']['liked']} likes en el perfil de @{args.like}")
                    if result['statistics']['already_liked'] > 0:
                        print(f"ℹ️ {result['statistics']['already_liked']} publicaciones ya tenían like")
                else:
                    print(f"Error: {result['message']}")
            else:
                print(f"Error: No se pudo navegar al perfil de @{args.like}")
        
        # Acción: Comment
        if args.comment:
            print(f"\nComentando en el perfil de @{args.comment}")
            
            # Primero navegar al perfil
            success = await actions.navigate_to_profile(args.comment)
            
            if success:
                # Realizar scroll para ver publicaciones
                await actions._random_scroll(2, 4)
                
                # Comentar en la primera publicación
                result = await actions.comment_on_post(0, args.comment_text)
                
                if result["status"] == "success":
                    print(f"Comentario publicado en el perfil de @{args.comment}")
                    print(f"💬 '{args.comment_text}'")
                else:
                    print(f"Error: {result['message']}")
            else:
                print(f"Error: No se pudo navegar al perfil de @{args.comment}")
        
        # Si no se especificó ninguna acción individual y tampoco batch, mostrar ayuda
        if not any([args.follow, args.unfollow, args.like, args.comment, args.batch]):
            print("\nNo se especificaron acciones a realizar. Usa --help para ver las opciones disponibles.")
        
        # 5. Esperar input del usuario para cerrar
        print("\nPresiona Enter para cerrar el navegador...")
        await asyncio.get_event_loop().run_in_executor(None, input)
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        print("\nFinalizando...")
        # No necesitamos cerrar el navegador aquí, lo maneja login_sesion.py

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.error(f"Error inesperado: {e}", exc_info=True)