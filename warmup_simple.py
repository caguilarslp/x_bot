#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Warmup Simple para X.com

Este script implementa un proceso de aclimatación gradual para cuentas de X.com,
utilizando los módulos existentes de login_sesion y social_actions.
No requiere clases adicionales, todo está integrado en un flujo simple.
"""

import os
import sys
import asyncio
import argparse
import logging
import json
import random
from datetime import datetime
from pathlib import Path

# Configuración de logging para archivos y consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("x_simple_warmup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos necesarios
from app.login.login_sesion import (
    load_accounts, select_account, load_session, analyze_page_structure, 
    find_user_session, update_session_file, get_proxy_config
)
from app.actions.social_actions import SocialActions

# Función para cargar configuración de warmup
def load_warmup_config():
    """
    Carga la configuración de warmup desde archivos JSON.
    
    Returns:
        dict: Configuración de warmup
    """
    config_paths = [
        "app/config/warmup_config.json",
        "warmup_config.json"
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Configuración cargada desde {path}")
                return config
            except Exception as e:
                logger.warning(f"Error al cargar configuración desde {path}: {e}")
    
    # Si no se encuentra, crear configuración por defecto
    logger.warning("No se encontró archivo de configuración. Usando valores por defecto.")
    default_config = {
        "phases": {
            "1": {  # Fase 1 - Aclimatación inicial
                "days": {
                    "1": {  # Día 1 - Solo navegación pasiva
                        "profile_visits": {"min": 5, "max": 8},
                        "feed_scrolls": {"min": 3, "max": 7},
                        "post_views": {"min": 8, "max": 15},
                        "follows": {"min": 0, "max": 0},
                        "likes": {"min": 0, "max": 0},
                        "comments": {"min": 0, "max": 0}
                    },
                    "2": {  # Día 2 - Navegación + Primeros follows
                        "profile_visits": {"min": 6, "max": 10},
                        "feed_scrolls": {"min": 4, "max": 8},
                        "post_views": {"min": 10, "max": 18},
                        "follows": {"min": 2, "max": 5},
                        "likes": {"min": 0, "max": 0},
                        "comments": {"min": 0, "max": 0}
                    },
                    "3": {  # Día 3 - Navegación + Follows + Primeros likes
                        "profile_visits": {"min": 8, "max": 12},
                        "feed_scrolls": {"min": 5, "max": 10},
                        "post_views": {"min": 12, "max": 20},
                        "follows": {"min": 3, "max": 6},
                        "likes": {"min": 1, "max": 3},
                        "comments": {"min": 0, "max": 0}
                    }
                }
            },
            "2": {  # Fase 2 - Actividad moderada
                "days": {
                    "1": {
                        "profile_visits": {"min": 10, "max": 15},
                        "feed_scrolls": {"min": 6, "max": 12},
                        "post_views": {"min": 15, "max": 25},
                        "follows": {"min": 5, "max": 8},
                        "likes": {"min": 3, "max": 7},
                        "comments": {"min": 0, "max": 1}
                    },
                    "2": {
                        "profile_visits": {"min": 12, "max": 18},
                        "feed_scrolls": {"min": 8, "max": 15},
                        "post_views": {"min": 18, "max": 30},
                        "follows": {"min": 6, "max": 10},
                        "likes": {"min": 5, "max": 10},
                        "comments": {"min": 1, "max": 2}
                    },
                    "3": {
                        "profile_visits": {"min": 15, "max": 20},
                        "feed_scrolls": {"min": 10, "max": 18},
                        "post_views": {"min": 20, "max": 35},
                        "follows": {"min": 8, "max": 12},
                        "likes": {"min": 8, "max": 15},
                        "comments": {"min": 2, "max": 4}
                    }
                }
            },
            "3": {  # Fase 3 - Actividad plena
                "days": {
                    "1": {
                        "profile_visits": {"min": 15, "max": 25},
                        "feed_scrolls": {"min": 12, "max": 20},
                        "post_views": {"min": 25, "max": 40},
                        "follows": {"min": 10, "max": 15},
                        "likes": {"min": 10, "max": 20},
                        "comments": {"min": 3, "max": 5}
                    }
                }
            }
        },
        "target_accounts": {
            "influencers": [
                "LuisitoComunica", "EugenioDerbez", "dannapaola", "Thalia",
                "yuyacst", "Arigameplays", "JuanpaZurita", "alexoficial"
            ],
            "news": [
                "CarlosLoret", "AristeguiOnline", "Adela_Micha", "ChumelTorres",
                "DeniseDresserG", "PaolaRojas", "beltrandelrio", "SalCamarena"
            ],
            "politicians": [
                "lopezobrador_", "Claudiashein", "RicardoBSalinas", "m_ebrard",
                "tatclouthier", "JoseRLopezB", "AlfonsoDurazo", "JLozanoA"
            ],
            "brands": [
                "CocaColaMx", "AeroMexico", "Liverpool_Mexico", "XboxMexico",
                "gruposalinas", "PromericaMEX", "Cinemex", "NetflixLAT"
            ]
        },
        "delays": {
            "between_actions": {"min": 2, "max": 8},
            "between_profiles": {"min": 5, "max": 15},
            "viewing_post": {"min": 3, "max": 12},
            "before_like": {"min": 2, "max": 7},
            "before_follow": {"min": 3, "max": 8},
            "before_comment": {"min": 5, "max": 15}
        }
    }
    
    return default_config

# Función para cargar datos de warmup de una cuenta
def load_warmup_data(username):
    """
    Carga los datos de progreso de warmup para una cuenta específica.
    
    Args:
        username: Nombre de usuario
        
    Returns:
        dict: Datos de warmup para la cuenta
    """
    warmup_dir = Path("warmup_data")
    warmup_dir.mkdir(exist_ok=True)
    
    warmup_file = warmup_dir / f"{username}_warmup.json"
    
    if warmup_file.exists():
        try:
            with open(warmup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"Datos de warmup cargados: Fase {data.get('current_phase', 1)}, Día {data.get('current_day', 1)}")
            return data
        except Exception as e:
            logger.error(f"Error al cargar datos de warmup: {e}")
    
    # Si no existe o hay error, crear datos nuevos
    today = datetime.now().strftime("%Y-%m-%d")
    
    new_data = {
        "username": username,
        "start_date": today,
        "current_phase": 1,
        "current_day": 1,
        "history": [],
        "followed_accounts": [],
        "liked_posts": [],
        "commented_posts": []
    }
    
    logger.info(f"Nuevos datos de warmup inicializados para {username}")
    return new_data

# Función para guardar datos de warmup
def save_warmup_data(username, data):
    """
    Guarda los datos de progreso de warmup para una cuenta.
    
    Args:
        username: Nombre de usuario
        data: Datos a guardar
        
    Returns:
        bool: True si se guardó correctamente
    """
    warmup_dir = Path("warmup_data")
    warmup_dir.mkdir(exist_ok=True)
    
    warmup_file = warmup_dir / f"{username}_warmup.json"
    
    try:
        with open(warmup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Datos de warmup guardados en {warmup_file}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar datos de warmup: {e}")
        return False

# Función para actualizar fase y día basados en la última sesión
def update_phase_and_day(warmup_data):
    """
    Actualiza la fase y día basados en la última sesión registrada.
    
    Args:
        warmup_data: Datos de warmup
        
    Returns:
        tuple: (phase, day) actualizado
    """
    history = warmup_data.get("history", [])
    
    if not history:
        logger.info("No hay historial previo. Iniciando en Fase 1, Día 1.")
        return 1, 1
    
    # Obtener la última sesión registrada
    last_session = history[-1]
    last_date_str = last_session.get("date")
    
    if not last_date_str:
        logger.warning("Fecha no encontrada en última sesión. Manteniendo fase/día actual.")
        return warmup_data.get("current_phase", 1), warmup_data.get("current_day", 1)
    
    # Calcular días transcurridos desde la última sesión
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        today = datetime.now()
        days_elapsed = (today - last_date).days
        
        if days_elapsed < 1:
            logger.info("Menos de un día desde la última sesión. Manteniendo fase/día actual.")
            return warmup_data.get("current_phase", 1), warmup_data.get("current_day", 1)
        
        # Avanzar al siguiente día
        logger.info(f"Han pasado {days_elapsed} días desde la última sesión.")
        
        current_phase = last_session.get("phase", 1)
        current_day = last_session.get("day", 1) + 1
        
        # Si completamos el día 3, avanzar a la siguiente fase
        if current_day > 3:
            current_phase += 1
            current_day = 1
        
        # Si completamos la fase 3, mantenernos en fase 3 día 1
        if current_phase > 3:
            current_phase = 3
            current_day = 1
        
        logger.info(f"Avanzando a: Fase {current_phase}, Día {current_day}")
        return current_phase, current_day
        
    except Exception as e:
        logger.error(f"Error al actualizar fase/día: {e}")
        return warmup_data.get("current_phase", 1), warmup_data.get("current_day", 1)

# Función para mostrar estado del warmup
def print_warmup_status(username, warmup_data, current_config):
    """
    Muestra información sobre el estado actual del warmup.
    
    Args:
        username: Nombre de usuario
        warmup_data: Datos de warmup
        current_config: Configuración de la fase/día actual
    """
    phase = warmup_data.get("current_phase", 1)
    day = warmup_data.get("current_day", 1)
    
    print("\n" + "="*60)
    print(f"  ESTADO DEL WARMUP: @{username}")
    print("="*60)
    
    print(f"Fase actual:         {phase}")
    print(f"Día actual:          {day}")
    print(f"Fecha de inicio:     {warmup_data.get('start_date', 'N/A')}")
    
    # Datos de interacciones
    follows = len(warmup_data.get("followed_accounts", []))
    likes = len(warmup_data.get("liked_posts", []))
    comments = len(warmup_data.get("commented_posts", []))
    sessions = len(warmup_data.get("history", []))
    
    print(f"Sesiones completadas: {sessions}")
    print(f"Cuentas seguidas:     {follows}")
    print(f"Publicaciones con like: {likes}")
    print(f"Comentarios realizados: {comments}")
    
    # Próxima fecha recomendada
    if warmup_data.get("history"):
        last_session = warmup_data["history"][-1]
        last_date_str = last_session.get("date")
        
        if last_date_str:
            try:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                from datetime import timedelta
                next_date = last_date + timedelta(days=1)
                print(f"Próxima sesión recomendada: {next_date.strftime('%Y-%m-%d')}")
            except Exception:
                pass
    
    print("-"*60)
    
    # Mostrar configuración de la fase/día actual
    print("\nAcciones programadas para la próxima sesión:")
    print(f"  Visitas a perfiles:  {current_config.get('profile_visits', {}).get('min', 0)}-{current_config.get('profile_visits', {}).get('max', 0)}")
    print(f"  Scrolls en feed:    {current_config.get('feed_scrolls', {}).get('min', 0)}-{current_config.get('feed_scrolls', {}).get('max', 0)}")
    print(f"  Follows a realizar:  {current_config.get('follows', {}).get('min', 0)}-{current_config.get('follows', {}).get('max', 0)}")
    print(f"  Likes a realizar:    {current_config.get('likes', {}).get('min', 0)}-{current_config.get('likes', {}).get('max', 0)}")
    
    comments_min = current_config.get('comments', {}).get('min', 0)
    comments_max = current_config.get('comments', {}).get('max', 0)
    
    if comments_max > 0:
        print(f"  Comentarios a realizar: {comments_min}-{comments_max}")
    else:
        print("  Comentarios a realizar: Ninguno")
    
    print("\n" + "-"*60)

# Función para obtener cuentas objetivo
def get_target_accounts(config, count=10):
    """
    Obtiene una selección de cuentas objetivo para interactuar.
    
    Args:
        config: Configuración de warmup
        count: Número de cuentas a obtener
        
    Returns:
        list: Lista de nombres de usuario para interactuar
    """
    accounts = []
    
    # Obtener cuentas de cada categoría
    categories = ["influencers", "news", "politicians", "brands"]
    
    for category in categories:
        category_accounts = config.get("target_accounts", {}).get(category, [])
        if category_accounts:
            # Tomar algunos de cada categoría
            sample_size = min(len(category_accounts), count // len(categories) + 1)
            accounts.extend(random.sample(category_accounts, sample_size))
    
    # Si no hay suficientes cuentas, usar cuentas de respaldo
    if len(accounts) < count:
        fallback_accounts = [
            "elonmusk", "twitter", "YouTube", "NBA", "cnnbrk", "BBCBreaking", 
            "YouTube", "Drake", "TheEllenShow", "KingJames", "KevinHart4real"
        ]
        remaining = count - len(accounts)
        accounts.extend(random.sample(fallback_accounts, min(remaining, len(fallback_accounts))))
    
    # Eliminar duplicados y mezclar
    unique_accounts = list(set(accounts))
    random.shuffle(unique_accounts)
    
    return unique_accounts[:count]

# Función para ejecutar una sesión de warmup
async def execute_warmup_session(page, username, phase, day, config):
    """
    Ejecuta una sesión de warmup según la fase y día especificados.
    
    Args:
        page: Página de Playwright con sesión activa
        username: Nombre de usuario
        phase: Fase de warmup (1-3)
        day: Día dentro de la fase (1-3)
        config: Configuración de warmup
        
    Returns:
        dict: Resultados de la sesión
    """
    # Inicializar SocialActions
    social_actions = SocialActions(page)
    
    # Obtener configuración específica para la fase y día actual
    try:
        day_config = config["phases"][str(phase)]["days"][str(day)]
    except (KeyError, TypeError):
        logger.error(f"No se encontró configuración para Fase {phase}, Día {day}")
        # Usar valores por defecto
        day_config = {
            "profile_visits": {"min": 5, "max": 8},
            "feed_scrolls": {"min": 3, "max": 7},
            "follows": {"min": 0, "max": 0},
            "likes": {"min": 0, "max": 0},
            "comments": {"min": 0, "max": 0}
        }
    
    # Resultados de la sesión
    session_results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "phase": phase,
        "day": day,
        "actions": {
            "profile_visits": [],
            "feed_activity": {},
            "follows": [],
            "likes": [],
            "comments": []
        }
    }
    
    try:
        # 1. Navegar a home y hacer scroll inicial
        print("\nIniciando sesión de warmup...\n")
        logger.info(f"Iniciando sesión de warmup - Fase {phase}, Día {day}")
        
        # Ir a home
        await social_actions.navigate_to_home()
        
        # Determinar número de scrolls en feed
        feed_min = day_config.get("feed_scrolls", {}).get("min", 3)
        feed_max = day_config.get("feed_scrolls", {}).get("max", 7)
        feed_scrolls = random.randint(feed_min, feed_max)
        
        # Hacer scroll en feed
        print(f"Haciendo scroll en feed ({feed_scrolls} scrolls)...")
        logger.info(f"Realizando {feed_scrolls} scrolls en feed")
        
        _, feed_posts = await social_actions.scroll_feed(feed_scrolls, feed_scrolls)
        
        # Registrar actividad en feed
        session_results["actions"]["feed_activity"] = {
            "scrolls": feed_scrolls,
            "posts_found": len(feed_posts),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 2. Determinar acciones según la fase/día
        # Visitas a perfiles
        profile_visits = random.randint(
            day_config.get("profile_visits", {}).get("min", 5),
            day_config.get("profile_visits", {}).get("max", 8)
        )
        
        # Follows a realizar
        follows_to_do = random.randint(
            day_config.get("follows", {}).get("min", 0),
            day_config.get("follows", {}).get("max", 0)
        )
        
        # Likes a dar
        likes_to_do = random.randint(
            day_config.get("likes", {}).get("min", 0),
            day_config.get("likes", {}).get("max", 0)
        )
        
        # Comentarios a hacer
        comments_to_do = random.randint(
            day_config.get("comments", {}).get("min", 0),
            day_config.get("comments", {}).get("max", 0)
        )
        
        # 3. Obtener cuentas objetivo
        target_accounts = get_target_accounts(config, profile_visits + 5)  # Pedir más para tener reserva
        
        # Contadores de acciones realizadas
        visits_done = 0
        follows_done = 0
        likes_done = 0
        comments_done = 0
        
        print(f"Visitando {profile_visits} perfiles...")
        logger.info(f"Visitando {profile_visits} perfiles")
        
        # 4. Visitar perfiles y realizar interacciones
        for username_to_visit in target_accounts:
            # Si ya completamos todas las visitas, salir
            if visits_done >= profile_visits:
                break
                
            try:
                # Navegar al perfil
                print(f"Visitando perfil de @{username_to_visit}...")
                profile_success = await social_actions.navigate_to_profile(username_to_visit)
                
                if profile_success:
                    # Registrar visita
                    visits_done += 1
                    session_results["actions"]["profile_visits"].append({
                        "username": username_to_visit,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Hacer scroll en el perfil
                    print(f"Explorando perfil de @{username_to_visit}...")
                    scroll_success, posts = await social_actions.scroll_profile(
                        min_scrolls=random.randint(2, 4),
                        max_scrolls=random.randint(4, 7)
                    )
                    
                    # Determinar acciones para este perfil
                    should_follow = follows_done < follows_to_do
                    should_like = likes_done < likes_to_do
                    should_comment = comments_done < comments_to_do
                    
                    # Follow si corresponde
                    if should_follow:
                        print(f"Siguiendo a @{username_to_visit}...")
                        follow_result = await social_actions.follow_user(username_to_visit)
                        
                        if follow_result["status"] == "success":
                            follows_done += 1
                            session_results["actions"]["follows"].append(follow_result)
                        elif follow_result["status"] == "info" and "Ya sigues" in follow_result["message"]:
                            # Ya seguimos esta cuenta, intentar con otra
                            pass
                    
                    # Like si corresponde y hay posts
                    if should_like and scroll_success and posts:
                        # Determinar cuántos likes dar en este perfil
                        likes_remaining = likes_to_do - likes_done
                        likes_this_profile = min(likes_remaining, random.randint(1, 3))
                        
                        if likes_this_profile > 0:
                            print(f"Dando {likes_this_profile} likes en perfil de @{username_to_visit}...")
                            
                            like_results = await social_actions.perform_likes(likes_this_profile)
                            
                            if like_results["status"] in ["success", "info"]:
                                likes_done += like_results["successful"]
                                session_results["actions"]["likes"].append(like_results)
                    
                    # Comment si corresponde, hay posts, y estamos en fase 2+
                    if should_comment and scroll_success and posts and phase >= 2:
                        if len(posts) > 0:
                            print(f"Comentando en post de @{username_to_visit}...")
                            
                            # Generar texto de comentario aleatorio
                            comments = [
                                "¡Excelente contenido!", 
                                "Muy interesante 👍", 
                                "Gracias por compartir esto",
                                "Totalmente de acuerdo",
                                "Información muy valiosa",
                                "Me encanta este contenido",
                                "Muy buen punto de vista"
                            ]
                            comment_text = random.choice(comments)
                            
                            comment_result = await social_actions.comment_on_post(index=0, comment_text=comment_text)
                            
                            if comment_result["status"] == "success":
                                comments_done += 1
                                session_results["actions"]["comments"].append(comment_result)
                
                # Ir a home entre perfiles (30% de probabilidad)
                if random.random() < 0.3:
                    print("Volviendo a home temporalmente...")
                    await social_actions.navigate_to_home()
                    await social_actions.scroll_feed(1, 3)  # Scroll breve
                
                # Pausa entre perfiles
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Error al interactuar con perfil @{username_to_visit}: {e}")
        
        # 5. Finalizar sesión volviendo a home
        await social_actions.navigate_to_home()
        
        # Registrar estadísticas
        session_results["statistics"] = {
            "profiles_visited": visits_done,
            "follows_performed": follows_done,
            "likes_given": likes_done,
            "comments_made": comments_done
        }
        
        print("\nAcciones realizadas:")
        print(f"  - Perfiles visitados: {visits_done}")
        print(f"  - Scrolls en feed: {feed_scrolls}")
        print(f"  - Follows realizados: {follows_done}")
        print(f"  - Likes dados: {likes_done}")
        if comments_done > 0:
            print(f"  - Comentarios realizados: {comments_done}")
        
        logger.info(f"Sesión de warmup completada con éxito: {session_results['statistics']}")
        
        return {
            "status": "success",
            "message": f"Sesión de warmup completada - Fase {phase}, Día {day}",
            "results": session_results
        }
        
    except Exception as e:
        logger.error(f"Error durante la sesión de warmup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "message": f"Error durante la sesión de warmup: {str(e)}",
            "results": session_results
        }

# Función para iniciar navegador y ejecutar warmup
async def run_simple_warmup(username, phase=None, headless=False, use_proxy=False, auto_close=False):
    """
    Ejecuta una sesión de warmup completa para una cuenta.
    
    Args:
        username: Nombre de usuario
        phase: Fase específica (opcional)
        headless: Si se ejecuta en modo sin UI
        use_proxy: Si se usa proxy
        auto_close: Si se cierra automáticamente
        
    Returns:
        bool: True si fue exitoso
    """
    from playwright.async_api import async_playwright
    
    resources = None
    
    try:
        # 1. Configurar sesión y navegador
        logger.info(f"Iniciando sesión de warmup para {username}")
        
        # Buscar sesión para el usuario
        session_path = find_user_session(username)
        if not session_path:
            logger.error(f"No se encontró sesión para {username}")
            return False
        
        # Cargar datos de sesión
        session_data = load_session(username=username)
        
        # Configurar proxy si es necesario
        proxy_config = None
        if use_proxy:
            proxy_config = get_proxy_config()
        
        # Iniciar Playwright
        playwright = await async_playwright().start()
        
        # Lanzar navegador
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
        
        browser = await playwright.chromium.launch(
            headless=headless,
            slow_mo=20,
            args=browser_args
        )
        
        # Configurar contexto
        context_params = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': session_data.get('userAgent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'storage_state': session_data['sessionState'],
            'bypass_csp': True,
            'ignore_https_errors': True
        }
        
        if proxy_config:
            context_params['proxy'] = proxy_config
        
        context = await browser.new_context(**context_params)
        
        # Script anti-detección
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { 
                get: () => undefined 
            });
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
            
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
        
        # Crear nueva página
        page = await context.new_page()
        
        # Navegar a home
        await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)  # Esperar estabilización
        
        # Screenshot para verificar
        screenshot_dir = Path('browser_screenshots')
        screenshot_dir.mkdir(exist_ok=True)
        screenshot_path = str(screenshot_dir / f'session_loaded_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        await page.screenshot(path=screenshot_path)
        
        # Verificar sesión
        session_check = await analyze_page_structure(page)
        if not session_check['indicators']:
            logger.warning("No se detectaron indicadores de sesión activa, pero continuando")
        
        resources = (playwright, browser, context, page)
        
        # 2. Cargar configuración y datos de warmup
        warmup_config = load_warmup_config()
        warmup_data = load_warmup_data(username)
        
        # 3. Determinar fase y día
        current_phase, current_day = update_phase_and_day(warmup_data)
        
        # Si se especificó fase, sobrescribir
        if phase is not None:
            current_phase = phase
            current_day = 1
            logger.info(f"Sobrescribiendo fase a {phase}, día 1 por parámetro")
        
        # Actualizar datos
        warmup_data["current_phase"] = current_phase
        warmup_data["current_day"] = current_day
        
        # 4. Obtener configuración específica para la fase/día
        try:
            current_config = warmup_config["phases"][str(current_phase)]["days"][str(current_day)]
        except (KeyError, TypeError):
            logger.warning(f"No se encontró configuración para Fase {current_phase}, Día {current_day}. Usando defaults.")
            current_config = {
                "profile_visits": {"min": 5, "max": 8},
                "feed_scrolls": {"min": 3, "max": 7},
                "follows": {"min": 0, "max": 0},
                "likes": {"min": 0, "max": 0},
                "comments": {"min": 0, "max": 0}
            }
        
        # 5. Mostrar estado del warmup
        print_warmup_status(username, warmup_data, current_config)
        
        # 6. Ejecutar sesión de warmup
        print("\nIniciando sesión de warmup...")
        result = await execute_warmup_session(
            page, 
            username, 
            current_phase, 
            current_day, 
            warmup_config
        )
        
        # 7. Actualizar datos de warmup con los resultados
        if result["status"] == "success":
            # Actualizar historial
            warmup_data["history"].append(result["results"])
            
            # Registrar follows
            for follow in result["results"]["actions"]["follows"]:
                if follow.get("status") == "success":
                    # Verificar si ya existe para no duplicar
                    exists = False
                    for existing in warmup_data.get("followed_accounts", []):
                        if existing.get("username") == follow.get("username"):
                            exists = True
                            break
                    
                    if not exists:
                        warmup_data.setdefault("followed_accounts", []).append({
                            "username": follow.get("username"),
                            "timestamp": follow.get("timestamp", datetime.now().isoformat()),
                            "phase": current_phase,
                            "day": current_day
                        })
            
            # Registrar likes
            for like in result["results"]["actions"]["likes"]:
                for i in range(like.get("successful", 0)):
                    warmup_data.setdefault("liked_posts", []).append({
                        "post_url": like.get("post_url", "unknown"),
                        "username": like.get("username", "unknown"),
                        "timestamp": like.get("timestamp", datetime.now().isoformat()),
                        "phase": current_phase,
                        "day": current_day
                    })
            
            # Registrar comentarios
            for comment in result["results"]["actions"]["comments"]:
                if comment.get("status") == "success":
                    warmup_data.setdefault("commented_posts", []).append({
                        "post_url": comment.get("post_url", "unknown"),
                        "username": comment.get("username", "unknown"),
                        "comment_text": comment.get("comment_text", ""),
                        "timestamp": comment.get("timestamp", datetime.now().isoformat()),
                        "phase": current_phase,
                        "day": current_day
                    })
            
            # Guardar datos actualizados
            save_warmup_data(username, warmup_data)
            
            print(f"\n✅ {result['message']}")
            print("\nSesión de warmup completada con éxito.")
        else:
            print(f"\n❌ Error: {result['message']}")
        
        # 8. Actualizar sesión antes de cerrar
        try:
            logger.info("Actualizando estado de la sesión...")
            await update_session_file(context, page, session_path, username)
        except Exception as e:
            logger.error(f"Error al actualizar sesión: {e}")
        
        # 9. Esperar confirmación antes de cerrar si no es auto_close
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
                # Cerrar recursos en orden
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

# Función para listar cuentas disponibles
def list_accounts_with_warmup_status():
    """
    Muestra las cuentas disponibles con su estado de warmup.
    
    Returns:
        list: Lista de cuentas
    """
    try:
        # Cargar cuentas
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

# Función principal
async def main():
    """
    Función principal del script.
    """
    parser = argparse.ArgumentParser(description='Script Simple de Warmup para X.com')
    parser.add_argument('--username', '-u', type=str, help='Nombre de usuario específico')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], default=None, help='Fase específica (1-3)')
    parser.add_argument('--no-proxy', action='store_true', help='Desactivar uso de proxies')
    parser.add_argument('--list', '-l', action='store_true', help='Listar cuentas disponibles')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    parser.add_argument('--auto-close', action='store_true', help='Cerrar automáticamente al finalizar')
    
    args = parser.parse_args()
    
    # Si solo queremos listar cuentas
    if args.list:
        list_accounts_with_warmup_status()
        return 0
    
    # Determinar username
    username = args.username
    
    if not username:
        # Mostrar cuentas disponibles
        accounts_info = list_accounts_with_warmup_status()
        
        if not accounts_info:
            logger.error("No hay cuentas disponibles")
            return 1
        
        # Solicitar selección
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
    success = await run_simple_warmup(
        username=username,
        phase=args.phase,
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