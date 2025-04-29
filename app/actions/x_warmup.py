#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XWarmup - Sistema gradual de aclimatación para cuentas en X.com

Implementa una estrategia progresiva para nuevas cuentas o cuentas inactivas
de X.com, simulando comportamiento humano a través de fases graduales de actividad.
"""

import os
import asyncio
import random
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configuración de logging
logger = logging.getLogger(__name__)

class XWarmup:
    """
    Sistema de warmup para cuentas de X.com.
    Implementa un proceso gradual dividido en fases para establecer un patrón
    de uso natural y evitar detección como comportamiento automatizado.
    """
    
    def __init__(self, page, username=None, config_path='app/config/warmup_config.json'):
        """
        Inicializa el sistema de warmup.
        
        Args:
            page: Página Playwright con sesión activa
            username: Nombre de usuario de la cuenta (opcional)
            config_path: Ruta al archivo de configuración (opcional)
        """
        self.page = page
        self.username = username
        self.logger = logging.getLogger(__name__)
        
        # Cargar configuración
        self.config = self._load_config(config_path)
        
        # Datos de warmup
        self.warmup_data_dir = Path("warmup_data")
        self.warmup_data_dir.mkdir(exist_ok=True)
        
        # Estado actual del warmup
        self.current_phase = 1
        self.current_day = 1
        self.start_date = None
        self.warmup_data = {}
        
        # Estadísticas de la sesión actual
        self.session_stats = {
            "start_time": datetime.now(),
            "profiles_visited": 0,
            "follows_performed": 0,
            "likes_performed": 0,
            "comments_performed": 0,
            "feed_scrolls": 0
        }
        
        # Selectores para diferentes acciones
        self.selectors = {
            "follow": {
                "primary": '//button[@data-testid="1589450359-follow"]',
                "already_following": '//button[@data-testid="1626214836-unfollow"]',
                "confirmation": '//button[contains(text(), "Seguir") or contains(text(), "Follow")]'
            },
            "like": {
                "primary": '//button[@data-testid="like"]',
                "already_liked": '//button[@data-testid="unlike"]',
            },
            "comment": {
                "reply_button": '//button[@data-testid="reply"]',
                "tweet_textarea": '//div[@data-testid="tweetTextarea_0"]',
                "send_button": '//button[@data-testid="tweetButton"]',
                "close_button": '//button[@data-testid="app-bar-close"]'
            },
            "posts": {
                "tweet_articles": '//article[@data-testid="tweet"]',
                "post_links": '//a[contains(@href, "/status/")]'
            },
            "navigation": {
                "profile_link": '//a[@data-testid="AppTabBar_Profile_Link"]',
                "home_link": '//a[@data-testid="AppTabBar_Home_Link"]',
                "messages_link": '//a[@data-testid="AppTabBar_DirectMessage_Link"]'
            }
        }
        
        # Cargar o inicializar datos de warmup si se proporciona username
        if username:
            self._load_warmup_data()
    
    def _load_config(self, config_path):
        """
        Cargar configuración de warmup desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            dict: Configuración cargada o configuración por defecto
        """
        # Primero intentar con la ruta proporcionada
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error al cargar configuración desde {config_path}: {e}")
        
        # Intentar rutas alternativas
        alt_paths = [
            "warmup_config.json",
            os.path.join("app", "config", "warmup_config.json"),
            os.path.join("config", "warmup_config.json")
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self.logger.info(f"Configuración cargada desde {path}")
                        return json.load(f)
                except Exception as e:
                    self.logger.warning(f"Error al cargar configuración desde {path}: {e}")
        
        # Si no se encuentra configuración, usar por defecto
        self.logger.warning("No se encontró configuración válida. Usando valores por defecto")
        return self._create_default_config()
    
    def _create_default_config(self):
        """
        Crear configuración por defecto de warmup.
        
        Returns:
            dict: Configuración por defecto
        """
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
                        },
                        "2": {
                            "profile_visits": {"min": 20, "max": 30},
                            "feed_scrolls": {"min": 15, "max": 25},
                            "post_views": {"min": 30, "max": 50},
                            "follows": {"min": 12, "max": 18},
                            "likes": {"min": 15, "max": 25},
                            "comments": {"min": 4, "max": 8}
                        },
                        "3": {
                            "profile_visits": {"min": 25, "max": 35},
                            "feed_scrolls": {"min": 18, "max": 30},
                            "post_views": {"min": 35, "max": 60},
                            "follows": {"min": 15, "max": 20},
                            "likes": {"min": 20, "max": 30},
                            "comments": {"min": 5, "max": 10}
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
            },
            "comments": [
                "Excelente publicacion!",
                "Muy interesante",
                "Totalmente de acuerdo",
                "Gracias por compartir esto",
                "Informacion muy valiosa",
                "Me encanta este contenido",
                "Increible punto de vista",
                "Esto es genial, gracias",
                "Completamente de acuerdo contigo",
                "Muy util, gracias por compartir"
            ]
        }
        
        return default_config
    
    def _load_warmup_data(self):
        """
        Cargar datos de warmup específicos para la cuenta actual.
        Si no existen, inicializa nuevos datos.
        """
        if not self.username:
            self.logger.warning("No se ha especificado username, no se pueden cargar datos de warmup")
            return
            
        warmup_file = self.warmup_data_dir / f"{self.username}_warmup.json"
        
        if warmup_file.exists():
            try:
                with open(warmup_file, 'r', encoding='utf-8') as f:
                    self.warmup_data = json.load(f)
                
                # Cargar estado actual
                self.current_phase = self.warmup_data.get("current_phase", 1)
                self.current_day = self.warmup_data.get("current_day", 1)
                self.start_date = self.warmup_data.get("start_date")
                
                self.logger.info(f"Datos de warmup cargados: Fase {self.current_phase}, Día {self.current_day}")
            except Exception as e:
                self.logger.error(f"Error al cargar datos de warmup: {e}")
                self._initialize_warmup_data()
        else:
            self.logger.info(f"No se encontraron datos previos de warmup para {self.username}")
            self._initialize_warmup_data()
    
    def _initialize_warmup_data(self):
        """
        Inicializar datos de warmup para una nueva cuenta.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.warmup_data = {
            "username": self.username,
            "start_date": today,
            "current_phase": 1,
            "current_day": 1,
            "history": [],
            "followed_accounts": [],
            "liked_posts": [],
            "commented_posts": []
        }
        
        self.current_phase = 1
        self.current_day = 1
        self.start_date = today
        
        self.logger.info(f"Nuevos datos de warmup inicializados para {self.username}")
        self._save_warmup_data()
    
    def _save_warmup_data(self):
        """
        Guardar datos actualizados de warmup.
        """
        if not self.username:
            self.logger.warning("No se ha especificado username, no se pueden guardar datos de warmup")
            return
            
        warmup_file = self.warmup_data_dir / f"{self.username}_warmup.json"
        
        try:
            with open(warmup_file, 'w', encoding='utf-8') as f:
                json.dump(self.warmup_data, f, indent=2)
            self.logger.info(f"Datos de warmup guardados en {warmup_file}")
        except Exception as e:
            self.logger.error(f"Error al guardar datos de warmup: {e}")
    
    def _update_phase_and_day(self):
        """
        Actualizar fase y día basados en la última sesión registrada.
        Ahora avanza después de cada sesión exitosa, sin esperar un día completo.
        """
        history = self.warmup_data.get("history", [])
        
        if not history:
            self.logger.info("No hay historial previo. Iniciando en Fase 1, Día 1.")
            return
        
        # Obtener la última sesión registrada
        last_session = history[-1]
        
        # Avanzar al siguiente día automáticamente después de cada sesión exitosa
        current_phase = last_session.get("phase", 1)
        current_day = last_session.get("day", 1) + 1
        
        # Si completamos el día 3, avanzar a la siguiente fase
        if current_day > 3:
            current_phase += 1
            current_day = 1
        
        # Si completamos la fase 3, mantenernos en fase 3 día 3 (nivel máximo)
        if current_phase > 3:
            current_phase = 3
            current_day = 3
        
        self.current_phase = current_phase
        self.current_day = current_day
        
        # Actualizar en los datos de warmup
        self.warmup_data["current_phase"] = current_phase
        self.warmup_data["current_day"] = current_day
        
        self.logger.info(f"Avanzando a: Fase {current_phase}, Día {current_day}")
    
    def _get_current_config(self):
        """
        Obtener la configuración específica para la fase y día actual.
        
        Returns:
            dict: Configuración para la fase/día actual
        """
        try:
            return self.config["phases"][str(self.current_phase)]["days"][str(self.current_day)]
        except KeyError:
            self.logger.error(f"Configuración no encontrada para Fase {self.current_phase}, Día {self.current_day}")
            # Usar defaults seguros
            return {
                "profile_visits": {"min": 5, "max": 10},
                "feed_scrolls": {"min": 3, "max": 7},
                "post_views": {"min": 8, "max": 15},
                "follows": {"min": 2, "max": 5},
                "likes": {"min": 1, "max": 3},
                "comments": {"min": 0, "max": 1}
            }
    
    async def _human_delay(self, delay_type="between_actions"):
        """
        Aplicar un retraso aleatorio según el tipo especificado.
        
        Args:
            delay_type: Tipo de retraso a aplicar (ver config["delays"])
        """
        delay_config = self.config.get("delays", {}).get(delay_type, {"min": 2, "max": 5})
        delay = random.uniform(delay_config["min"], delay_config["max"])
        self.logger.debug(f"Delay {delay_type}: {delay:.2f}s")
        await asyncio.sleep(delay)
    
    async def _check_page_is_active(self):
        """
        Verificar si la página sigue activa con manejo robusto.
        
        Returns:
            bool: True si la página está activa, False en caso contrario
        """
        try:
            # Verificación más ligera
            await self.page.wait_for_timeout(500)  # Pequeña pausa
            # Usar una evaluación simple que tiene menos probabilidad de fallar
            await self.page.evaluate("window.innerWidth")
            return True
        except Exception as e:
            # Verificación alternativa más simple
            try:
                is_closed = await self.page.evaluate("window.closed")
                return not is_closed
            except Exception:
                self.logger.error(f"La página no está disponible: {e}")
                return False
    
    async def _navigate_to_home(self):
        """
        Navegar a la página de inicio de X.com con reintentos.
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Primero verificar si ya estamos en home
                current_url = self.page.url.lower()
                if "/home" in current_url:
                    self.logger.info("Ya estamos en home, saltando navegación")
                    await self._human_delay("between_actions")
                    return True
                
                # Verificar que la página sigue abierta
                if not await self._check_page_is_active():
                    self.logger.error("La página no está disponible antes de navegar")
                    return False
                
                # Usar timeout personalizado
                self.logger.info(f"Navegando a home (intento {attempt+1}/{max_attempts})...")
                await self.page.goto("https://x.com/home", 
                                    wait_until="domcontentloaded", 
                                    timeout=30000)
                
                # Esperar tiempo adicional para estabilización
                await self.page.wait_for_timeout(3000)
                
                await self._human_delay("between_actions")
                
                # Verificar que estamos en home
                current_url = self.page.url.lower()
                if "/home" in current_url:
                    self.logger.info("Navegación a home exitosa")
                    return True
                else:
                    self.logger.warning(f"URL inesperada después de navegar a home: {current_url}")
                    # Intentar método alternativo si es el último intento
                    if attempt == max_attempts - 1:
                        try:
                            self.logger.info("Intentando navegación alternativa...")
                            home_link = await self.page.query_selector(self.selectors["navigation"]["home_link"])
                            if home_link:
                                await home_link.click()
                                await self.page.wait_for_timeout(3000)
                                self.logger.info("Navegación a home mediante click en botón de Home")
                                return True
                        except Exception as click_err:
                            self.logger.error(f"Error al hacer clic en Home: {click_err}")
            except Exception as e:
                self.logger.error(f"Error al navegar a home (intento {attempt+1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    # Esperar más tiempo entre intentos
                    await asyncio.sleep(3)
        
        return False
    
    async def _scroll_feed(self, min_scrolls=None, max_scrolls=None):
        """
        Realizar scroll en el feed principal con verificaciones adicionales.
        
        Args:
            min_scrolls: Mínimo número de scrolls (opcional)
            max_scrolls: Máximo número de scrolls (opcional)
            
        Returns:
            dict: Resultado con métricas del scroll
        """
        result = {
            "scrolls_performed": 0,
            "posts_viewed": 0,
            "time_spent": 0
        }
        
        config = self._get_current_config()
        
        if min_scrolls is None:
            min_scrolls = config["feed_scrolls"]["min"]
        if max_scrolls is None:
            max_scrolls = config["feed_scrolls"]["max"]
        
        num_scrolls = random.randint(min_scrolls, max_scrolls)
        self.logger.info(f"Realizando {num_scrolls} scrolls en el feed")
        
        start_time = datetime.now()
        
        for i in range(num_scrolls):
            try:
                # Verificar que la página sigue abierta
                if not await self._check_page_is_active():
                    self.logger.error("La página no está disponible durante scroll")
                    break
                
                scroll_distance = random.randint(300, 1000)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # Incrementar contador
                result["scrolls_performed"] += 1
                
                # Actualizar contador en estadísticas
                self.session_stats["feed_scrolls"] += 1
                
                # Esperar un tiempo aleatorio entre scrolls
                await self._human_delay("between_actions")
                
                # Ocasionalmente detenerse más tiempo para simular lectura
                if random.random() < 0.3:  # 30% de probabilidad
                    await self._human_delay("viewing_post")
                    result["posts_viewed"] += 1
            except Exception as e:
                self.logger.warning(f"Error durante scroll #{i+1}: {e}")
                # Continuar con el siguiente scroll a pesar del error
        
        # Calcular tiempo total
        end_time = datetime.now()
        result["time_spent"] = (end_time - start_time).total_seconds()
        
        self.logger.info(f"Scroll completado: {result['scrolls_performed']} scrolls, {result['posts_viewed']} posts, {result['time_spent']:.1f}s")
        return result
    
    async def _navigate_to_profile(self, username):
        """
        Navegar al perfil de un usuario específico.
        
        Args:
            username: Nombre de usuario a visitar
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        max_attempts = 2
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Navegando al perfil de @{username}")
                
                # Verificar que la página sigue abierta
                if not await self._check_page_is_active():
                    return False
                
                # Limpiar el @ si existe
                username = username.lstrip('@')
                
                # Navegar directamente a la URL del perfil
                await self.page.goto(f"https://x.com/{username}", 
                                    wait_until="domcontentloaded",
                                    timeout=30000)
                
                # Esperar tiempo adicional para estabilización
                await self.page.wait_for_timeout(3000)
                
                await self._human_delay("between_actions")
                
                # Verificar si estamos en el perfil correcto
                current_url = self.page.url.lower()
                if username.lower() in current_url:
                    self.logger.info(f"Navegación exitosa al perfil @{username}")
                    
                    # Incrementar contador de perfiles visitados
                    self.session_stats["profiles_visited"] += 1
                    
                    return True
                else:
                    self.logger.warning(f"URL inesperada: {current_url}, esperaba perfil de @{username}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                    else:
                        return False
                    
            except Exception as e:
                self.logger.error(f"Error al navegar al perfil de @{username} (intento {attempt+1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2)
                else:
                    return False
        
        return False
    
    async def _interact_with_profile(self, username, should_follow=False, should_like=False, should_comment=False):
        """
        Interactuar con un perfil: visitar, scroll, opcionalmente seguir, dar likes y comentar.
        
        Args:
            username: Nombre de usuario del perfil
            should_follow: Si se debe seguir al usuario
            should_like: Si se deben dar likes a publicaciones
            should_comment: Si se debe comentar en una publicación
        
        Returns:
            dict: Resultados de las interacciones
        """
        results = {
            "profile": username,
            "visited": False,
            "followed": False,
            "liked_posts": 0,
            "commented": False,
            "details": {}
        }
        
        # Navegar al perfil
        profile_success = await self._navigate_to_profile(username)
        if not profile_success:
            results["details"]["profile_error"] = "No se pudo navegar al perfil"
            return results
        
        results["visited"] = True
        
        # Hacer scroll en el perfil
        try:
            scroll_count = random.randint(2, 5)
            posts_viewed = 0
            post_urls = []
            
            for _ in range(scroll_count):
                if not await self._check_page_is_active():
                    break
                
                scroll_distance = random.randint(300, 800)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await self._human_delay("between_actions")
                
                # Recolectar URLs de posts
                if random.random() < 0.5:  # 50% de probabilidad
                    try:
                        post_links = await self.page.query_selector_all(self.selectors["posts"]["post_links"])
                        for link in post_links:
                            try:
                                href = await link.get_attribute("href")
                                if href and "/status/" in href and href not in post_urls:
                                    post_urls.append(href)
                            except:
                                continue
                    except:
                        pass
                
                # Pausar ocasionalmente para simular lectura
                if random.random() < 0.3:  # 30% de probabilidad
                    await self._human_delay("viewing_post")
                    posts_viewed += 1
            
            results["details"]["scrolls"] = scroll_count
            results["details"]["posts_viewed"] = posts_viewed
            results["details"]["post_urls_found"] = len(post_urls)
            
        except Exception as e:
            self.logger.warning(f"Error durante scroll en perfil: {e}")
            results["details"]["scroll_error"] = str(e)
        
        # Seguir si está indicado
        if should_follow:
            try:
                # Espera adicional antes de intentar seguir
                await self._human_delay("before_follow")
                
                # Verificar si ya seguimos al usuario
                already_following = await self.page.query_selector(self.selectors["follow"]["already_following"])
                
                if already_following:
                    self.logger.info(f"Ya sigues a @{username}")
                    results["details"]["follow_status"] = "already_following"
                else:
                    # Buscar el botón de follow
                    follow_button = await self.page.query_selector(self.selectors["follow"]["primary"])
                    
                    if follow_button:
                        # Hacer clic para seguir
                        await follow_button.click()
                        await asyncio.sleep(2)  # Esperar a que se procese
                        
                        # Verificar si ahora seguimos al usuario
                        confirmation = await self.page.query_selector(self.selectors["follow"]["already_following"])
                        
                        if confirmation:
                            self.logger.info(f"Ahora sigues a @{username}!")
                            results["followed"] = True
                            
                            # Actualizar contador
                            self.session_stats["follows_performed"] += 1
                            
                            # Registrar en warmup_data
                            self.warmup_data["followed_accounts"].append({
                                "username": username,
                                "followed_at": datetime.now().isoformat(),
                                "phase": self.current_phase,
                                "day": self.current_day
                            })
                        else:
                            self.logger.warning(f"No se pudo confirmar que sigues a @{username}")
                    else:
                        self.logger.warning(f"No se encontró el botón de follow para @{username}")
                        results["details"]["follow_error"] = "button_not_found"
            except Exception as e:
                self.logger.error(f"Error al seguir a @{username}: {e}")
                results["details"]["follow_error"] = str(e)
        
        # Dar likes si está indicado
        if should_like and post_urls:
            try:
                likes_given = 0
                max_likes = min(3, len(post_urls))  # Máximo 3 likes por perfil
                
                # Seleccionar posts aleatorios para dar like
                posts_to_like = random.sample(post_urls, max_likes)
                
                for post_url in posts_to_like:
                    try:
                        # Navegar al post
                        await self.page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)
                        
                        # Buscar botón de like
                        await self._human_delay("before_like")
                        like_button = await self.page.query_selector(self.selectors["like"]["primary"])
                        already_liked = await self.page.query_selector(self.selectors["like"]["already_liked"])
                        
                        if already_liked:
                            self.logger.info(f"Post {post_url} ya tiene like")
                            continue
                        
                        if like_button:
                            # Dar like
                            await like_button.click()
                            await asyncio.sleep(1)
                            
                            # Verificar si se dio like
                            confirmation = await self.page.query_selector(self.selectors["like"]["already_liked"])
                            
                            if confirmation:
                                self.logger.info(f"Like dado a post de @{username}!")
                                likes_given += 1
                                
                                # Actualizar contador
                                self.session_stats["likes_performed"] += 1
                                
                                # Registrar en warmup_data
                                self.warmup_data["liked_posts"].append({
                                    "post_url": post_url,
                                    "username": username,
                                    "timestamp": datetime.now().isoformat(),
                                    "phase": self.current_phase,
                                    "day": self.current_day
                                })
                            
                            # Espera entre likes
                            await self._human_delay("between_actions")
                    except Exception as e:
                        self.logger.error(f"Error al dar like a post {post_url}: {e}")
                
                results["liked_posts"] = likes_given
                
                # Navegar de vuelta al perfil
                await self._navigate_to_profile(username)
                
            except Exception as e:
                self.logger.error(f"Error general al dar likes en @{username}: {e}")
                results["details"]["like_error"] = str(e)
        
        # Comentar si está indicado
        if should_comment and post_urls:
            try:
                # Seleccionar un post aleatorio para comentar
                post_to_comment = random.choice(post_urls)
                
                # Generar texto de comentario
                comment_text = random.choice(self.config.get("comments", ["Excelente publicacion!"]))
                
                # Navegar al post
                await self.page.goto(post_to_comment, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                
                # Buscar botón de reply
                await self._human_delay("before_comment")
                reply_button = await self.page.query_selector(self.selectors["comment"]["reply_button"])
                
                if reply_button:
                    # Hacer clic en reply
                    await reply_button.click()
                    await asyncio.sleep(2)
                    
                    # Buscar campo de texto
                    textarea = await self.page.query_selector(self.selectors["comment"]["tweet_textarea"])
                    
                    if textarea:
                        # Escribir comentario con comportamiento humano
                        for char in comment_text:
                            await textarea.type(char)
                            await asyncio.sleep(random.uniform(0.05, 0.15))
                        
                        # Buscar botón de enviar
                        send_button = await self.page.query_selector(self.selectors["comment"]["send_button"])
                        
                        if send_button:
                            # Enviar comentario
                            await send_button.click()
                            await asyncio.sleep(3)
                            
                            self.logger.info(f"Comentario publicado en post de @{username}!")
                            results["commented"] = True
                            
                            # Actualizar contador
                            self.session_stats["comments_performed"] += 1
                            
                            # Registrar en warmup_data
                            self.warmup_data["commented_posts"].append({
                                "post_url": post_to_comment,
                                "username": username,
                                "comment": comment_text,
                                "timestamp": datetime.now().isoformat(),
                                "phase": self.current_phase,
                                "day": self.current_day
                            })
                            
                            # Espera después de comentar
                            await self._human_delay("between_actions")
                
                # Navegar de vuelta al perfil
                await self._navigate_to_profile(username)
                
            except Exception as e:
                self.logger.error(f"Error al comentar en post de @{username}: {e}")
                results["details"]["comment_error"] = str(e)
        
        return results
    
    async def _get_suggested_accounts(self, category=None):
        """
        Obtener cuentas recomendadas para interactuar según la categoría.
        
        Args:
            category: Categoría de cuentas a obtener (opcional)
        
        Returns:
            list: Lista de nombres de usuario
        """
        if not category:
            # Seleccionar una categoría aleatoria
            categories = ["influencers", "news", "politicians", "brands"]
            category = random.choice(categories)
        
        target_accounts = self.config.get("target_accounts", {}).get(category, [])
        
        # Si no hay cuentas definidas, usar una lista de reserva
        if not target_accounts:
            fallback_accounts = [
                "X", "elonmusk", "YouTube", "Twitter", "cnnbrk", "nytimes",
                "BBCBreaking", "NASA", "NatGeo", "Google", "Microsoft", "Apple"
            ]
            return random.sample(fallback_accounts, min(5, len(fallback_accounts)))
        
        # Filtrar las cuentas que ya seguimos
        followed = [acc["username"] for acc in self.warmup_data.get("followed_accounts", [])]
        available = [acc for acc in target_accounts if acc not in followed]
        
        # Si hay menos de 5 disponibles, permitir algunas repeticiones
        if len(available) < 5:
            # Añadir algunas de las ya seguidas para tener variedad
            if followed:
                available.extend(random.sample(followed, min(3, len(followed))))
        
        # Seleccionar un subconjunto aleatorio
        sample_size = min(10, len(available))
        return random.sample(available, sample_size) if sample_size > 0 else available
    
    async def _interact_with_recommended_accounts(self):
        """
        Interactuar con cuentas recomendadas según fase/día actual.
        
        Returns:
            list: Resultados de interacciones
        """
        config = self._get_current_config()
        follows_config = config.get("follows", {"min": 0, "max": 0})
        likes_config = config.get("likes", {"min": 0, "max": 0})
        comments_config = config.get("comments", {"min": 0, "max": 0})
        
        # Determinar número de follows, likes y comentarios
        num_follows = random.randint(follows_config["min"], follows_config["max"])
        num_likes = random.randint(likes_config["min"], likes_config["max"])
        num_comments = random.randint(comments_config["min"], comments_config["max"])
        
        # Si no hay interacciones que hacer, salir temprano
        if num_follows == 0 and num_likes == 0 and num_comments == 0:
            self.logger.info("No hay interacciones programadas para esta fase/día")
            return []
        
        # Obtener cuentas recomendadas de varias categorías
        categories = ["influencers", "news", "politicians", "brands"]
        
        # Mezclar un poco de cada categoría
        accounts = []
        for category in categories:
            try:
                category_accounts = await self._get_suggested_accounts(category)
                accounts.extend(category_accounts[:3])  # Tomar hasta 3 de cada categoría
            except Exception as e:
                self.logger.warning(f"Error al obtener cuentas de categoría {category}: {e}")
        
        # Eliminar duplicados y mezclar
        accounts = list(set(accounts))
        random.shuffle(accounts)
        
        # Limitar según necesidades
        accounts = accounts[:max(num_follows + 3, 10)]  # Asegurar tener suficientes
        
        # Realizar interacciones
        results = []
        follows_done = 0
        likes_done = 0
        comments_done = 0
        
        for username in accounts:
            # Verificar si la página sigue activa
            if not await self._check_page_is_active():
                self.logger.error("La página no está disponible, interrumpiendo interacciones")
                break
                
            # Determinar acciones para esta cuenta
            should_follow = follows_done < num_follows
            should_like = likes_done < num_likes
            should_comment = comments_done < num_comments
            
            if not should_follow and not should_like and not should_comment:
                break  # Ya completamos todas las interacciones programadas
            
            # Interactuar con el perfil
            result = await self._interact_with_profile(
                username=username,
                should_follow=should_follow,
                should_like=should_like,
                should_comment=should_comment
            )
            
            # Actualizar contadores
            if result["followed"]:
                follows_done += 1
            likes_done += result["liked_posts"]
            if result["commented"]:
                comments_done += 1
            
            # Registrar resultado
            results.append(result)
            
            # Pausa entre perfiles
            await self._human_delay("between_profiles")
            
            # Regresar a home ocasionalmente para simular navegación natural
            if random.random() < 0.3:  # 30% de probabilidad
                self.logger.info("Regresando a home temporalmente")
                home_success = await self._navigate_to_home()
                if home_success:
                    await self._scroll_feed(1, 3)  # Scroll breve
                else:
                    self.logger.warning("No se pudo navegar a home, continuando con interacciones")
        
        return results
    
    async def execute_warmup(self):
        """
        Ejecutar la sesión de warmup completa según fase/día actual.
        
        Returns:
            dict: Resultados de la sesión de warmup
        """
        self.logger.info(f"Iniciando sesión de warmup: Fase {self.current_phase}, Día {self.current_day}")
        
        # Obtener configuración actual
        config = self._get_current_config()
        
        # Resultados a retornar
        session_results = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "phase": self.current_phase,
            "day": self.current_day,
            "actions": {
                "profile_visits": [],
                "feed_activity": {},
                "follows": [],
                "likes": [],
                "comments": []
            }
        }
        
        try:
            # 1. Navegar a home
            home_success = await self._navigate_to_home()
            if not home_success:
                return {
                    "status": "error",
                    "message": "No se pudo navegar a la página de inicio",
                    "phase": self.current_phase,
                    "day": self.current_day
                }
            
            # 2. Scroll inicial en el feed
            feed_result = await self._scroll_feed()
            
            session_results["actions"]["feed_activity"] = feed_result
            
            # 3. Interactuar con cuentas recomendadas
            self.logger.info("Interactuando con cuentas recomendadas")
            interaction_results = await self._interact_with_recommended_accounts()
            
            # Registrar resultados
            for result in interaction_results:
                if result["visited"]:
                    session_results["actions"]["profile_visits"].append({
                        "username": result["profile"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                if result["followed"]:
                    session_results["actions"]["follows"].append({
                        "username": result["profile"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                if result["liked_posts"] > 0:
                    session_results["actions"]["likes"].append({
                        "username": result["profile"],
                        "count": result["liked_posts"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                if result["commented"]:
                    session_results["actions"]["comments"].append({
                        "username": result["profile"],
                        "timestamp": datetime.now().isoformat()
                    })
            
            # 4. Navegar a home para finalizar
            await self._navigate_to_home()
            
            # 5. Actualizar historial
            self.warmup_data["history"].append(session_results)
            
            # 6. Actualizar fase y día para la próxima ejecución
            self._update_phase_and_day()
            
            # 7. Guardar datos actualizados
            self._save_warmup_data()
            
            return {
                "status": "success",
                "phase": self.current_phase,
                "day": self.current_day,
                "message": f"Sesión de warmup completada: Fase {self.current_phase}, Día {self.current_day}",
                "results": session_results
            }
            
        except Exception as e:
            self.logger.error(f"Error durante la sesión de warmup: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            return {
                "status": "error",
                "phase": self.current_phase,
                "day": self.current_day,
                "message": f"Error: {str(e)}",
                "partial_results": session_results
            }
    
    def print_warmup_status(self):
        """
        Imprimir información sobre el estado actual del warmup.
        """
        if not self.warmup_data:
            print(f"\nNo hay datos de warmup para {self.username}")
            return
        
        print("\n" + "="*60)
        print(f"  ESTADO DEL WARMUP: @{self.username}")
        print("="*60)
        
        print(f"Fase actual:         {self.current_phase}")
        print(f"Día actual:          {self.current_day}")
        print(f"Fecha de inicio:     {self.warmup_data.get('start_date', 'N/A')}")
        
        # Datos de interacciones
        follows = len(self.warmup_data.get("followed_accounts", []))
        likes = len(self.warmup_data.get("liked_posts", []))
        comments = len(self.warmup_data.get("commented_posts", []))
        sessions = len(self.warmup_data.get("history", []))
        
        print(f"Sesiones completadas: {sessions}")
        print(f"Cuentas seguidas:     {follows}")
        print(f"Publicaciones con like: {likes}")
        print(f"Comentarios realizados: {comments}")
        
        # Próxima fecha recomendada
        if self.warmup_data.get("history"):
            last_session = self.warmup_data["history"][-1]
            last_date_str = last_session.get("date")
            
            if last_date_str:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                next_date = last_date + timedelta(days=1)
                print(f"Próxima sesión recomendada: {next_date.strftime('%Y-%m-%d')}")
        
        print("-"*60)
        
        # Mostrar configuración de la fase/día actual
        config = self._get_current_config()
        
        print("\nAcciones programadas para la próxima sesión:")
        print(f"  Visitas a perfiles:  {config['profile_visits']['min']}-{config['profile_visits']['max']}")
        print(f"  Scrolls en feed:    {config['feed_scrolls']['min']}-{config['feed_scrolls']['max']}")
        print(f"  Follows a realizar:  {config['follows']['min']}-{config['follows']['max']}")
        print(f"  Likes a realizar:    {config['likes']['min']}-{config['likes']['max']}")
        
        if config.get('comments', {}).get('max', 0) > 0:
            print(f"  Comentarios a realizar: {config['comments']['min']}-{config['comments']['max']}")
        else:
            print("  Comentarios a realizar: Ninguno")
        
        print("\n" + "-"*60)