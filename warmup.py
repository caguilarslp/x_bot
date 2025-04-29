#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
X.com Warmup System - Sistema gradual de aclimatación para cuentas en X.com

Este script implementa una estrategia progresiva para nuevas cuentas o cuentas inactivas
de X.com, simulando comportamiento humano a través de tres fases de actividad gradual.
Diseñado para establecer un historial de uso natural antes de iniciar interacciones intensivas.
"""

import os
import sys
import json
import random
import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

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

# Asegurarnos que podemos importar desde la estructura de app
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Importar módulos necesarios del sistema principal
try:
    from app.login.login_sesion import open_browser_with_session, load_accounts, select_account, load_session
    from app.config.proxy import get_random_proxy
except ImportError as e:
    logger.error(f"Error al importar módulos: {e}")
    logger.error("Asegúrate de ejecutar este script desde el directorio principal del proyecto")
    sys.exit(1)

# Clase principal para el sistema de warmup
class XWarmup:
    """
    Sistema de warmup para cuentas de X.com.
    Implementa un proceso gradual dividido en fases para establecer un patrón
    de uso natural y evitar detección como comportamiento automatizado.
    """
    
    def __init__(self, username: Optional[str] = None):
        """
        Inicializa el sistema de warmup.
        
        Args:
            username: Nombre de usuario específico para cargar su sesión (opcional)
        """
        self.username = username
        self.config = self._load_config()
        self.page = None
        self.browser = None
        self.context = None
        self.warmup_data_dir = Path("warmup_data")
        self.warmup_data_dir.mkdir(exist_ok=True)
        
        # Estado actual de warmup
        self.current_phase = 1
        self.current_day = 1
        self.start_date = None
        self.warmup_data = {}
        
        # Carga de cuentas disponibles
        self.accounts = load_accounts()
        
    def _load_config(self) -> Dict:
        """
        Cargar configuración de warmup desde archivo JSON.
        
        Returns:
            dict: Configuración de warmup
        """
        config_path = Path("app/config/warmup_config.json")
        default_config_path = Path("warmup_config.json")
        
        # Intentar con la primera ruta
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error al cargar configuración desde {config_path}: {e}")
        
        # Intentar con la ruta alternativa
        if default_config_path.exists():
            try:
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error al cargar configuración desde {default_config_path}: {e}")
        
        # Si no se encontró configuración, crear una por defecto
        logger.warning("No se encontró configuración. Usando valores por defecto.")
        return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """
        Crear configuración por defecto para el proceso de warmup.
        
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
            }
        }
        
        # Guardar configuración por defecto
        with open("warmup_config.json", 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def _load_warmup_data(self) -> None:
        """
        Cargar datos de warmup específicos para la cuenta actual.
        Si no existen, inicializa nuevos datos.
        """
        warmup_file = self.warmup_data_dir / f"{self.username}_warmup.json"
        
        if warmup_file.exists():
            try:
                with open(warmup_file, 'r', encoding='utf-8') as f:
                    self.warmup_data = json.load(f)
                
                # Cargar estado actual
                self.current_phase = self.warmup_data.get("current_phase", 1)
                self.current_day = self.warmup_data.get("current_day", 1)
                self.start_date = self.warmup_data.get("start_date")
                
                logger.info(f"Datos de warmup cargados: Fase {self.current_phase}, Día {self.current_day}")
            except Exception as e:
                logger.error(f"Error al cargar datos de warmup: {e}")
                self._initialize_warmup_data()
        else:
            logger.info(f"No se encontraron datos previos de warmup para {self.username}")
            self._initialize_warmup_data()
    
    def _initialize_warmup_data(self) -> None:
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
        
        logger.info(f"Nuevos datos de warmup inicializados para {self.username}")
        self._save_warmup_data()
    
    def _save_warmup_data(self) -> None:
        """
        Guardar datos actualizados de warmup.
        """
        warmup_file = self.warmup_data_dir / f"{self.username}_warmup.json"
        
        try:
            with open(warmup_file, 'w', encoding='utf-8') as f:
                json.dump(self.warmup_data, f, indent=2)
            logger.info(f"Datos de warmup guardados en {warmup_file}")
        except Exception as e:
            logger.error(f"Error al guardar datos de warmup: {e}")
    
    def _update_phase_and_day(self) -> None:
        """
        Actualizar fase y día basados en la última sesión registrada.
        Avanza automáticamente si ha pasado al menos un día desde la última sesión.
        """
        history = self.warmup_data.get("history", [])
        
        if not history:
            logger.info("No hay historial previo. Iniciando en Fase 1, Día 1.")
            return
        
        # Obtener la última sesión registrada
        last_session = history[-1]
        last_date_str = last_session.get("date")
        
        if not last_date_str:
            logger.warning("Fecha no encontrada en última sesión. Manteniendo fase/día actual.")
            return
        
        # Calcular días transcurridos desde la última sesión
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            today = datetime.now()
            days_elapsed = (today - last_date).days
            
            if days_elapsed < 1:
                logger.info("Menos de un día desde la última sesión. Manteniendo fase/día actual.")
                return
            
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
            
            self.current_phase = current_phase
            self.current_day = current_day
            
            # Actualizar en los datos de warmup
            self.warmup_data["current_phase"] = current_phase
            self.warmup_data["current_day"] = current_day
            
            logger.info(f"Avanzando a: Fase {current_phase}, Día {current_day}")
            
        except Exception as e:
            logger.error(f"Error al actualizar fase/día: {e}")
    
    def _get_current_config(self) -> Dict:
        """
        Obtener la configuración específica para la fase y día actual.
        
        Returns:
            dict: Configuración para la fase/día actual
        """
        try:
            return self.config["phases"][str(self.current_phase)]["days"][str(self.current_day)]
        except KeyError:
            logger.error(f"Configuración no encontrada para Fase {self.current_phase}, Día {self.current_day}")
            # Usar defaults seguros
            return {
                "profile_visits": {"min": 5, "max": 10},
                "feed_scrolls": {"min": 3, "max": 7},
                "post_views": {"min": 8, "max": 15},
                "follows": {"min": 2, "max": 5},
                "likes": {"min": 1, "max": 3},
                "comments": {"min": 0, "max": 1}
            }
    
    async def _random_delay(self, delay_type: str = "between_actions") -> None:
        """
        Aplicar un retraso aleatorio según el tipo especificado.
        
        Args:
            delay_type: Tipo de retraso a aplicar (ver config["delays"])
        """
        delay_config = self.config.get("delays", {}).get(delay_type, {"min": 2, "max": 5})
        delay = random.uniform(delay_config["min"], delay_config["max"])
        logger.debug(f"Delay {delay_type}: {delay:.2f}s")
        await asyncio.sleep(delay)
    
    async def _navigate_to_home(self) -> bool:
        """
        Navegar a la página de inicio de X.com.
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
            await self._random_delay("between_actions")
            return True
        except Exception as e:
            logger.error(f"Error al navegar a home: {e}")
            return False
    
    async def _scroll_feed(self, min_scrolls: Optional[int] = None, max_scrolls: Optional[int] = None) -> None:
        """
        Realizar scroll en el feed principal.
        
        Args:
            min_scrolls: Mínimo número de scrolls (opcional)
            max_scrolls: Máximo número de scrolls (opcional)
        """
        config = self._get_current_config()
        
        if min_scrolls is None:
            min_scrolls = config["feed_scrolls"]["min"]
        if max_scrolls is None:
            max_scrolls = config["feed_scrolls"]["max"]
        
        num_scrolls = random.randint(min_scrolls, max_scrolls)
        logger.info(f"Realizando {num_scrolls} scrolls en el feed")
        
        for i in range(num_scrolls):
            scroll_distance = random.randint(300, 1000)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            
            # Esperar un tiempo aleatorio entre scrolls
            await self._random_delay("between_actions")
            
            # Ocasionalmente detenerse más tiempo para simular lectura
            if random.random() < 0.3:  # 30% de probabilidad
                await self._random_delay("viewing_post")
    
    async def _navigate_to_profile(self, username: str) -> bool:
        """
        Navegar al perfil de un usuario específico.
        
        Args:
            username: Nombre de usuario a visitar
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            logger.info(f"Navegando al perfil de @{username}")
            
            # Limpiar el @ si existe
            username = username.lstrip('@')
            
            # Navegar directamente a la URL del perfil
            await self.page.goto(f"https://x.com/{username}", wait_until="domcontentloaded")
            await self._random_delay("between_actions")
            
            # Verificar si estamos en el perfil correcto
            current_url = self.page.url.lower()
            if username.lower() in current_url:
                return True
            else:
                logger.warning(f"No se pudo confirmar navegación al perfil de @{username}")
                return False
                
        except Exception as e:
            logger.error(f"Error al navegar al perfil de @{username}: {e}")
            return False
    
    async def _interact_with_profile(self, username: str, should_follow: bool = False, should_like: bool = False) -> Dict:
        """
        Interactuar con un perfil: visitar, scroll, opcionalmente seguir y dar likes.
        
        Args:
            username: Nombre de usuario del perfil
            should_follow: Si se debe seguir al usuario
            should_like: Si se deben dar likes a publicaciones
        
        Returns:
            dict: Resultados de las interacciones
        """
        results = {
            "profile": username,
            "visited": False,
            "followed": False,
            "liked_posts": 0,
            "details": {}
        }
        
        # Navegar al perfil
        profile_success = await self._navigate_to_profile(username)
        if not profile_success:
            results["details"]["profile_error"] = "No se pudo navegar al perfil"
            return results
        
        results["visited"] = True
        
        # Hacer scroll en el perfil
        scroll_count = random.randint(2, 5)
        for _ in range(scroll_count):
            scroll_distance = random.randint(300, 800)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await self._random_delay("between_actions")
        
        # Seguir si está indicado
        if should_follow:
            # Verificar si ya seguimos al usuario
            follow_button = await self.page.query_selector('css=button[aria-label^="Follow @"]')
            if follow_button:
                # Añadir pequeña pausa antes de seguir
                await self._random_delay("before_follow")
                
                try:
                    await follow_button.click()
                    results["followed"] = True
                    logger.info(f"Siguiendo a @{username}")
                    
                    # Registrar en warmup_data
                    self.warmup_data["followed_accounts"].append({
                        "username": username,
                        "followed_at": datetime.now().isoformat(),
                        "phase": self.current_phase,
                        "day": self.current_day
                    })
                    
                    # Esperar respuesta de la UI
                    await self._random_delay("between_actions")
                    
                except Exception as e:
                    logger.error(f"Error al seguir a @{username}: {e}")
                    results["details"]["follow_error"] = str(e)
            else:
                logger.info(f"Ya sigues a @{username} o no se encontró botón de seguir")
                results["details"]["follow_status"] = "already_following_or_button_not_found"
        
        # Dar likes si está indicado
        if should_like:
            try:
                # Buscar botones de like
                like_buttons = await self.page.query_selector_all('css=button[aria-label$=". Like"]')
                
                if like_buttons:
                    # Seleccionar un número aleatorio de publicaciones para dar like
                    max_likes = min(len(like_buttons), 3)  # Limitamos a 3 likes por perfil
                    num_likes = random.randint(1, max_likes)
                    
                    liked_count = 0
                    for i in range(min(num_likes, len(like_buttons))):
                        # Añadir pequeña pausa antes de dar like
                        await self._random_delay("before_like")
                        
                        try:
                            # Intentar obtener URL de la publicación primero
                            post_container = await like_buttons[i].evaluate('el => el.closest("article")')
                            post_link = await post_container.query_selector('a[href*="/status/"]')
                            post_url = await post_link.get_attribute('href') if post_link else "unknown"
                            
                            # Dar like
                            await like_buttons[i].click()
                            liked_count += 1
                            logger.info(f"Like dado a publicación de @{username}")
                            
                            # Registrar en warmup_data
                            self.warmup_data["liked_posts"].append({
                                "post_url": post_url,
                                "username": username,
                                "timestamp": datetime.now().isoformat(),
                                "phase": self.current_phase,
                                "day": self.current_day
                            })
                            
                            # Esperar un poco entre likes
                            await self._random_delay("between_actions")
                            
                        except Exception as e:
                            logger.error(f"Error al dar like a publicación de @{username}: {e}")
                    
                    results["liked_posts"] = liked_count
                else:
                    logger.info(f"No se encontraron botones de like en el perfil de @{username}")
                    results["details"]["like_status"] = "no_like_buttons_found"
                
            except Exception as e:
                logger.error(f"Error general al interactuar con likes en @{username}: {e}")
                results["details"]["like_error"] = str(e)
        
        return results
    
    async def _get_suggested_accounts(self, category: str = None) -> List[str]:
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
        return random.sample(available, sample_size)
    
    async def _interact_with_recommended_accounts(self) -> List[Dict]:
        """
        Interactuar con cuentas recomendadas según fase/día actual.
        
        Returns:
            list: Resultados de interacciones
        """
        config = self._get_current_config()
        follows_config = config.get("follows", {"min": 0, "max": 0})
        likes_config = config.get("likes", {"min": 0, "max": 0})
        
        # Determinar número de follows y likes
        num_follows = random.randint(follows_config["min"], follows_config["max"])
        num_likes = random.randint(likes_config["min"], likes_config["max"])
        
        # Si no hay interacciones que hacer, salir temprano
        if num_follows == 0 and num_likes == 0:
            logger.info("No hay follows ni likes programados para esta fase/día")
            return []
        
        # Obtener cuentas recomendadas
        categories = ["influencers", "news", "politicians", "brands"]
        
        # Mezclar un poco de cada categoría
        accounts = []
        for category in categories:
            category_accounts = await self._get_suggested_accounts(category)
            accounts.extend(category_accounts[:3])  # Tomar hasta 3 de cada categoría
        
        # Eliminar duplicados y mezclar
        accounts = list(set(accounts))
        random.shuffle(accounts)
        
        # Limitar según necesidades
        accounts = accounts[:max(num_follows + 3, 10)]  # Asegurar tener suficientes
        
        # Realizar interacciones
        results = []
        follows_done = 0
        likes_done = 0
        
        for username in accounts:
            # Determinar acciones para esta cuenta
            should_follow = follows_done < num_follows
            should_like = likes_done < num_likes
            
            if not should_follow and not should_like:
                break  # Ya completamos todas las interacciones programadas
            
            # Interactuar con el perfil
            result = await self._interact_with_profile(
                username=username,
                should_follow=should_follow,
                should_like=should_like
            )
            
            # Actualizar contadores
            if result["followed"]:
                follows_done += 1
            likes_done += result["liked_posts"]
            
            # Registrar resultado
            results.append(result)
            
            # Pausa entre perfiles
            await self._random_delay("between_profiles")
            
            # Regresar a home ocasionalmente para simular navegación natural
            if random.random() < 0.3:  # 30% de probabilidad
                await self._navigate_to_home()
                await self._scroll_feed(1, 3)  # Scroll breve
        
        return results
    
    async def execute_warmup(self) -> Dict:
        """
        Ejecutar la sesión de warmup completa según fase/día actual.
        
        Returns:
            dict: Resultados de la sesión de warmup
        """
        # Verificar si tenemos la página inicializada
        if not self.page:
            logger.error("Page no inicializada. Llamar a setup() primero.")
            return {"status": "error", "message": "Page no inicializada"}
        
        logger.info(f"Iniciando sesión de warmup: Fase {self.current_phase}, Día {self.current_day}")
        
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
            await self._navigate_to_home()
            
            # 2. Scroll inicial en el feed
            feed_scrolls = random.randint(
                config["feed_scrolls"]["min"],
                config["feed_scrolls"]["max"]
            )
            
            logger.info(f"Realizando {feed_scrolls} scrolls en feed")
            await self._scroll_feed(feed_scrolls, feed_scrolls)
            
            session_results["actions"]["feed_activity"] = {
                "scrolls": feed_scrolls,
                "time_spent": random.randint(30, 120)  # Tiempo estimado en segundos
            }
            
            # 3. Interactuar con cuentas recomendadas
            logger.info("Interactuando con cuentas recomendadas")
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
            
            # 4. Navegar a home para finalizar
            await self._navigate_to_home()
            
            # 5. Actualizar historial
            self.warmup_data["history"].append(session_results)
            self._save_warmup_data()
            
            return {
                "status": "success",
                "phase": self.current_phase,
                "day": self.current_day,
                "message": f"Sesión de warmup completada: Fase {self.current_phase}, Día {self.current_day}",
                "results": session_results
            }
            
        except Exception as e:
            logger.error(f"Error durante la sesión de warmup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "status": "error",
                "phase": self.current_phase,
                "day": self.current_day,
                "message": f"Error: {str(e)}",
                "partial_results": session_results
            }
    
    async def setup(self) -> bool:
        """
        Configurar la sesión para el proceso de warmup.
        
        Returns:
            bool: True si se completó correctamente
        """
        try:
            # Si no tenemos username, permitir seleccionar
            if not self.username:
                if not self.accounts:
                    logger.error("No hay cuentas disponibles")
                    return False
                    
                self.username = select_account(self.accounts)
                if not self.username:
                    logger.error("No se seleccionó ninguna cuenta")
                    return False
            
            # Cargar/inicializar datos de warmup
            self._load_warmup_data()
            
            # Actualizar fase/día basado en la última sesión
            self._update_phase_and_day()
            
            # Abrir navegador con sesión
            self.page = await open_browser_with_session(
                headless=False,  # Recomendado visible para verificar
                username=self.username,
                keep_open=True,
                return_page=True  # Necesitamos la referencia a la página
            )
            
            if not self.page:
                logger.error("No se pudo abrir el navegador con la sesión")
                return False
            
            logger.info(f"Sesión iniciada para {self.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error al configurar sesión: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def print_warmup_status(self) -> None:
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
        sessions = len(self.warmup_data.get("history", []))
        
        print(f"Sesiones completadas: {sessions}")
        print(f"Cuentas seguidas:     {follows}")
        print(f"Publicaciones con like: {likes}")
        
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
        
        if config['comments']['max'] > 0:
            print(f"  Comentarios a realizar: {config['comments']['min']}-{config['comments']['max']}")
        else:
            print("  Comentarios a realizar: Ninguno")
        
        print("\n" + "-"*60)
    
    def list_accounts(self) -> None:
        """
        Listar todas las cuentas disponibles con su estado de warmup.
        """
        if not self.accounts:
            print("\nNo hay cuentas disponibles en login_accounts.json")
            return
        
        print("\n" + "="*70)
        print("  CUENTAS DISPONIBLES Y ESTADO DE WARMUP")
        print("="*70)
        print(f"{'#':<3} {'Usuario':<20} {'Fase':<6} {'Día':<5} {'Inicio':<12} {'Última sesión':<15}")
        print("-"*70)
        
        # Buscar archivos de warmup para todas las cuentas
        for i, account in enumerate(self.accounts):
            username = account.get("username", "")
            if not username:
                continue
                
            warmup_file = self.warmup_data_dir / f"{username}_warmup.json"
            
            phase = "N/A"
            day = "N/A"
            start_date = "N/A"
            last_session = "N/A"
            
            if warmup_file.exists():
                try:
                    with open(warmup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    phase = data.get("current_phase", 1)
                    day = data.get("current_day", 1)
                    start_date = data.get("start_date", "N/A")
                    
                    if data.get("history"):
                        last_session = data["history"][-1].get("date", "N/A")
                except Exception:
                    pass
            
            print(f"{i+1:<3} {username:<20} {phase:<6} {day:<5} {start_date:<12} {last_session:<15}")
        
        print("-"*70)
        print("\nPara ejecutar el warmup de una cuenta específica:")
        print("python warmup.py --username [nombre_usuario]")
        print("\nPara ejecutar en modo interactivo:")
        print("python warmup.py")

async def main():
    """
    Función principal para ejecutar el sistema de warmup.
    """
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(description="Sistema de Warmup para X.com")
    parser.add_argument('--username', '-u', type=str, help='Nombre de usuario específico para cargar su sesión')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], default=None, help='Fase específica a ejecutar (1-3)')
    parser.add_argument('--no-proxy', action='store_true', help='Desactivar el uso de proxies')
    parser.add_argument('--list', '-l', action='store_true', help='Listar cuentas disponibles y su estado de warmup')
    
    args = parser.parse_args()
    
    # Configurar o despejar proxy
    if not args.no_proxy:
        logger.info("Configurando proxy")
        try:
            proxy_config = get_random_proxy()
            if proxy_config:
                os.environ["USE_PROXY"] = "true"
                os.environ["PROXY_SERVER"] = proxy_config.get("server", "")
                os.environ["PROXY_USERNAME"] = proxy_config.get("username", "")
                os.environ["PROXY_PASSWORD"] = proxy_config.get("password", "")
                if proxy_config.get("type"):
                    os.environ["PROXY_TYPE"] = proxy_config.get("type", "")
                logger.info(f"Proxy configurado: {proxy_config.get('server', '')}")
            else:
                logger.warning("No se obtuvo proxy, continuando sin proxy")
        except Exception as e:
            logger.error(f"Error al configurar proxy: {e}")
    else:
        logger.info("Uso de proxies desactivado")
        for var in ["USE_PROXY", "PROXY_SERVER", "PROXY_USERNAME", "PROXY_PASSWORD", "PROXY_TYPE"]:
            if var in os.environ:
                del os.environ[var]
    
    # Inicializar sistema de warmup
    warmup = XWarmup(username=args.username)
    
    # Si solo listar, mostrar cuentas y salir
    if args.list:
        warmup.list_accounts()
        return
    
    # Configurar la sesión
    setup_success = await warmup.setup()
    if not setup_success:
        logger.error("No se pudo configurar la sesión. Abortando.")
        return
    
    # Si se especificó una fase, sobrescribirla
    if args.phase:
        warmup.current_phase = args.phase
        warmup.current_day = 1
        logger.info(f"Sobrescribiendo a Fase {args.phase}, Día 1 por parámetro")
    
    # Mostrar estado actual
    warmup.print_warmup_status()
    
    # Preguntar si continuar
    try:
        response = input("\n¿Continuar con la sesión de warmup? (s/n): ")
        if response.lower() not in ['s', 'si', 'y', 'yes']:
            print("Operación cancelada por el usuario.")
            return
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        return
    
    # Ejecutar warmup
    print("\nIniciando sesión de warmup...")
    result = await warmup.execute_warmup()
    
    # Mostrar resultados
    if result["status"] == "success":
        print(f"\n✅ {result['message']}")
        print("\nAcciones realizadas:")
        
        actions = result["results"]["actions"]
        print(f"  📊 Visitas a perfiles: {len(actions['profile_visits'])}")
        print(f"  🔄 Scrolls en feed: {actions['feed_activity'].get('scrolls', 0)}")
        print(f"  👥 Follows realizados: {len(actions['follows'])}")
        print(f"  👍 Likes dados: {sum(like['count'] for like in actions['likes'])}")
        
        if actions['comments']:
            print(f"  💬 Comentarios realizados: {len(actions['comments'])}")
    else:
        print(f"\n❌ Error: {result['message']}")
    
    # Preguntar si cerrar navegador
    try:
        input("\nPresiona Enter para cerrar el navegador...")
    except KeyboardInterrupt:
        pass
    
    print("\nFinalizando...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperación interrumpida por el usuario")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.error(f"Error inesperado: {e}", exc_info=True)