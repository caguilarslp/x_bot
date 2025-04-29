#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo de acciones específicas para el sistema de warmup de X.com

Este módulo implementa las funciones especializadas para realizar acciones
graduales en el proceso de warmup de cuentas en X.com, integrándose
con el sistema principal.
"""

import asyncio
import random
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Configurar logger
logger = logging.getLogger(__name__)

class WarmupActions:
    """
    Clase para realizar acciones específicas del proceso de warmup de X.com.
    Se integra con el sistema principal y utiliza técnicas avanzadas para
    simular comportamiento humano.
    """
    
    def __init__(self, page, config_path='app/config/warmup_config.json'):
        """
        Inicializar acciones de warmup con página y configuración.
        
        Args:
            page: Página de Playwright con sesión activa
            config_path: Ruta al archivo de configuración de warmup
        """
        self.page = page
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
        
        # Selectores para acciones específicas
        self.selectors = {
            "follow": {
                "primary": 'css=button[aria-label^="Follow @"]',
                "fallback": [
                    'css=button[data-testid$="-follow"]',
                    'css=button:has-text("Follow")',
                ]
            },
            "following": {
                "primary": 'css=button[aria-label^="Following @"]',
                "fallback": [
                    'css=button[data-testid$="-unfollow"]',
                    'css=button:has-text("Following")',
                ]
            },
            "like": {
                # First look for unliked posts, then detect already-liked state
                "primary": 'css=button[aria-label$=". Like"]',
                "fallback": [
                    'css=button[aria-label$=". Liked"]',
                ]
            },
            "tweet_articles": {
                "primary": 'css=article[data-testid="tweet"]',
                "fallback": [
                    'css=div[role="article"]',
                ]
            },
            "reply": {
                "primary": 'css=button[data-testid="reply"]',
                "fallback": [
                    'css=button[aria-label^="Reply"]',
                    'css=button:has-text("Reply")'
                ]
            },
            "comment_field": {
                "primary": 'css=[aria-label="Post text"]',
                "fallback": [
                    'css=div[role="textbox"]'
                ]
            },
            "send_comment": {
                "primary": 'css=button[data-testid="tweetButtonInline"]',
                "fallback": [
                    'css=button:has-text("Reply to")'
                ]
            },
            "feed_tweets": {
                "primary": 'css=div[aria-label="Timeline: Home timeline"] article',
                "fallback": [
                    'css=div[data-testid="primaryColumn"] article'
                ]
            },
            "profile_tweets": {
                "primary": 'css=div[data-testid="primaryColumn"] article',
                "fallback": [
                    'css=section[aria-labelledby$="accessible-list"] article'
                ]
            },
            "search_box": {
                "primary": 'css=input[data-testid="SearchBox_Search_Input"]',
                "fallback": [
                    'css=input[placeholder="Search"]'
                ]
            }
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Cargar configuración de warmup desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            dict: Configuración de warmup
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Archivo de configuración no encontrado: {config_path}")
            # Intentar ruta alternativa
            try:
                alt_path = "warmup_config.json"
                with open(alt_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except FileNotFoundError:
                self.logger.warning(f"Tampoco se encontró configuración en: {alt_path}")
                # Usar valores por defecto
                return self._create_default_config()
        except json.JSONDecodeError:
            self.logger.error(f"Error de formato en {config_path}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict:
        """
        Crear configuración por defecto para warmup.
        
        Returns:
            dict: Configuración por defecto
        """
        return {
            "delays": {
                "between_actions": {"min": 2, "max": 8},
                "between_profiles": {"min": 5, "max": 15},
                "viewing_post": {"min": 3, "max": 12},
                "before_like": {"min": 2, "max": 7},
                "before_follow": {"min": 3, "max": 8},
                "before_comment": {"min": 5, "max": 15}
            },
            "behavior": {
                "random_scroll_distance": {"min": 300, "max": 800},
                "read_post_probability": 0.6,
                "return_to_home_probability": 0.3,
                "typing_speed": {"min": 0.05, "max": 0.15},
                "error_correction_probability": 0.02
            }
        }
    
    async def _find_element(self, selector_key: str, context=None) -> Any:
        """
        Buscar un elemento usando selectores con fallbacks.
        
        Args:
            selector_key: Clave del selector en self.selectors
            context: Contexto opcional de búsqueda (por defecto self.page)
        
        Returns:
            El elemento encontrado o None
        """
        search_context = context or self.page
        selector_config = self.selectors.get(selector_key)
        
        if not selector_config:
            self.logger.error(f"No se encontró configuración para el selector: {selector_key}")
            return None
        
        # Intentar con el selector principal primero
        primary_selector = selector_config["primary"]
        try:
            element = await search_context.query_selector(primary_selector)
            if element:
                return element
        except Exception as e:
            self.logger.debug(f"Error con selector primario {primary_selector}: {e}")
        
        # Intentar con fallbacks
        for fallback in selector_config.get("fallback", []):
            try:
                element = await search_context.query_selector(fallback)
                if element:
                    self.logger.debug(f"Usando selector fallback para {selector_key}: {fallback}")
                    return element
            except Exception as e:
                self.logger.debug(f"Error con selector fallback {fallback}: {e}")
        
        return None
    
    async def _find_elements(self, selector_key: str, context=None) -> List:
        """
        Buscar múltiples elementos usando selectores con fallbacks.
        
        Args:
            selector_key: Clave del selector en self.selectors
            context: Contexto opcional de búsqueda (por defecto self.page)
        
        Returns:
            Lista de elementos encontrados o lista vacía
        """
        search_context = context or self.page
        selector_config = self.selectors.get(selector_key)
        
        if not selector_config:
            self.logger.error(f"No se encontró configuración para el selector: {selector_key}")
            return []
        
        # Intentar con el selector principal primero
        primary_selector = selector_config["primary"]
        try:
            elements = await search_context.query_selector_all(primary_selector)
            if elements and len(elements) > 0:
                return elements
        except Exception as e:
            self.logger.debug(f"Error con selector primario {primary_selector}: {e}")
        
        # Intentar con fallbacks
        for fallback in selector_config.get("fallback", []):
            try:
                elements = await search_context.query_selector_all(fallback)
                if elements and len(elements) > 0:
                    self.logger.debug(f"Usando selector fallback para {selector_key}: {fallback}")
                    return elements
            except Exception as e:
                self.logger.debug(f"Error con selector fallback {fallback}: {e}")
        
        return []
    
    async def _human_delay(self, delay_type: str = "between_actions") -> None:
        """
        Aplicar un retraso aleatorio con comportamiento humano.
        
        Args:
            delay_type: Tipo de retraso a aplicar (definido en config["delays"])
        """
        delay_config = self.config.get("delays", {}).get(delay_type, {"min": 2, "max": 5})
        delay = random.uniform(delay_config["min"], delay_config["max"])
        self.logger.debug(f"Delay {delay_type}: {delay:.2f}s")
        await asyncio.sleep(delay)
    
    async def _human_typing(self, element, text: str) -> None:
        """
        Simular escritura humana con variaciones en velocidad y errores ocasionales.
        
        Args:
            element: Elemento DOM donde escribir
            text: Texto a escribir
        """
        # Limpiar campo primero
        await element.fill("")
        await self._human_delay(0.5, 1.5)
        
        typing_config = self.config.get("behavior", {}).get("typing_speed", {"min": 0.05, "max": 0.15})
        error_prob = self.config.get("behavior", {}).get("error_correction_probability", 0.02)
        
        # Escribir caracter por caracter
        for i, char in enumerate(text):
            # Posible error de escritura
            if random.random() < error_prob and i < len(text) - 1:
                # Escribir un caracter erróneo
                wrong_char = random.choice("asdfghjklqwertyuiopzxcvbnm")
                await element.type(wrong_char, delay=int(random.uniform(50, 150)))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Borrar el error
                await element.press("Backspace")
                await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Escribir el caracter correcto
            delay_ms = int(random.uniform(typing_config["min"], typing_config["max"]) * 1000)
            await element.type(char, delay=delay_ms)
            
            # Pausas ocasionales para simular pensamiento
            if random.random() < 0.05:  # 5% de probabilidad
                await asyncio.sleep(random.uniform(0.3, 1.2))
    
    async def navigate_to_home(self) -> bool:
        """
        Navegar a la página de inicio de X.com.
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded")
            await self._human_delay("between_actions")
            
            # Verificar que estamos en home
            current_url = self.page.url.lower()
            if "/home" in current_url:
                self.logger.info("Navegación a home exitosa")
                return True
            else:
                self.logger.warning(f"URL inesperada después de navegar a home: {current_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al navegar a home: {e}")
            return False
    
    async def navigate_to_profile(self, username: str) -> bool:
        """
        Navegar al perfil de un usuario específico.
        
        Args:
            username: Nombre de usuario a visitar
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.logger.info(f"Navegando al perfil de @{username}")
            
            # Limpiar el @ si existe
            username = username.lstrip('@')
            
            # Navegar directamente a la URL del perfil
            await self.page.goto(f"https://x.com/{username}", wait_until="domcontentloaded")
            await self._human_delay("between_actions")
            
            # Verificar si estamos en el perfil correcto
            current_url = self.page.url.lower()
            if username.lower() in current_url:
                self.logger.info(f"Navegación exitosa al perfil @{username}")
                return True
            else:
                self.logger.warning(f"URL inesperada: {current_url}, esperaba perfil de @{username}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al navegar al perfil de @{username}: {e}")
            return False
    
    async def scroll_feed(self, min_scrolls: int = 3, max_scrolls: int = 7) -> Dict:
        """
        Realizar scroll en el feed con comportamiento natural.
        
        Args:
            min_scrolls: Mínimo número de scrolls
            max_scrolls: Máximo número de scrolls
        
        Returns:
            dict: Resultado de la acción con métricas
        """
        result = {
            "scrolls_performed": 0,
            "posts_viewed": 0,
            "time_spent": 0
        }
        
        try:
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            self.logger.info(f"Realizando {num_scrolls} scrolls en el feed")
            
            start_time = datetime.now()
            scroll_config = self.config.get("behavior", {}).get("random_scroll_distance", {"min": 300, "max": 800})
            read_prob = self.config.get("behavior", {}).get("read_post_probability", 0.6)
            
            # Buscar tweets en el feed
            feed_tweets = await self._find_elements("feed_tweets")
            initial_tweets_count = len(feed_tweets)
            
            for i in range(num_scrolls):
                # Scroll aleatorio
                scroll_distance = random.randint(scroll_config["min"], scroll_config["max"])
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # Incrementar contador
                result["scrolls_performed"] += 1
                
                # Pausa breve después del scroll
                await self._human_delay("between_actions")
                
                # Ocasionalmente detenerse más tiempo para simular lectura de post
                if random.random() < read_prob:
                    await self._human_delay("viewing_post")
                    result["posts_viewed"] += 1
            
            # Contar cuántos tweets nuevos aparecieron
            feed_tweets = await self._find_elements("feed_tweets")
            new_tweets_count = len(feed_tweets) - initial_tweets_count
            if new_tweets_count > 0:
                result["posts_viewed"] += new_tweets_count
            
            # Calcular tiempo total
            end_time = datetime.now()
            result["time_spent"] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Scroll completado: {result['scrolls_performed']} scrolls, {result['posts_viewed']} posts, {result['time_spent']:.1f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Error durante scroll del feed: {e}")
            
            # Actualizar resultado con lo que se logró hacer
            end_time = datetime.now()
            result["time_spent"] = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0
            
            return result
    
    async def scroll_profile(self, username: str, min_scrolls: int = 2, max_scrolls: int = 5) -> Dict:
        """
        Realizar scroll en un perfil de usuario.
        
        Args:
            username: Nombre de usuario del perfil
            min_scrolls: Mínimo número de scrolls
            max_scrolls: Máximo número de scrolls
        
        Returns:
            dict: Resultado de la acción con métricas
        """
        result = {
            "username": username,
            "scrolls_performed": 0,
            "posts_viewed": 0,
            "time_spent": 0
        }
        
        try:
            # Asegurarse de estar en el perfil correcto
            current_url = self.page.url.lower()
            if username.lower() not in current_url:
                success = await self.navigate_to_profile(username)
                if not success:
                    return result
            
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            self.logger.info(f"Realizando {num_scrolls} scrolls en perfil de @{username}")
            
            start_time = datetime.now()
            scroll_config = self.config.get("behavior", {}).get("random_scroll_distance", {"min": 300, "max": 800})
            read_prob = self.config.get("behavior", {}).get("read_post_probability", 0.6)
            
            for i in range(num_scrolls):
                # Scroll aleatorio
                scroll_distance = random.randint(scroll_config["min"], scroll_config["max"])
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # Incrementar contador
                result["scrolls_performed"] += 1
                
                # Pausa breve después del scroll
                await self._human_delay("between_actions")
                
                # Ocasionalmente detenerse más tiempo para simular lectura de post
                if random.random() < read_prob:
                    await self._human_delay("viewing_post")
                    result["posts_viewed"] += 1
            
            # Calcular tiempo total
            end_time = datetime.now()
            result["time_spent"] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Scroll en perfil @{username} completado: {result['scrolls_performed']} scrolls, {result['time_spent']:.1f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Error durante scroll del perfil @{username}: {e}")
            
            # Actualizar resultado con lo que se logró hacer
            end_time = datetime.now()
            result["time_spent"] = (end_time - start_time).total_seconds() if 'start_time' in locals() else 0
            
            return result
    
    async def follow_user(self, username: str) -> Dict:
        """
        Seguir a un usuario desde su perfil.
        
        Args:
            username: Nombre de usuario a seguir
        
        Returns:
            dict: Resultado de la acción de seguir
        """
        result = {
            "username": username,
            "action": "follow",
            "status": "error",
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Asegurarse de estar en el perfil correcto
            current_url = self.page.url.lower()
            if username.lower() not in current_url:
                success = await self.navigate_to_profile(username)
                if not success:
                    result["message"] = "No se pudo navegar al perfil"
                    return result
            
            # Verificar si ya seguimos al usuario
            following_button = await self._find_element("following")
            if following_button:
                result["status"] = "info"
                result["message"] = "Ya sigues a este usuario"
                self.logger.info(f"Ya sigues a @{username}")
                return result
            
            # Buscar botón de seguir
            follow_button = await self._find_element("follow")
            if not follow_button:
                result["message"] = "No se encontró botón de seguir"
                self.logger.warning(f"No se encontró botón de seguir para @{username}")
                return result
            
            # Añadir pequeña pausa antes de seguir
            await self._human_delay("before_follow")
            
            # Hacer clic en el botón de seguir
            await follow_button.click()
            
            # Esperar a que cambie el estado del botón
            await self._human_delay("between_actions")
            
            # Verificar si se completó correctamente
            following_button = await self._find_element("following")
            if following_button:
                result["status"] = "success"
                result["message"] = "Usuario seguido correctamente"
                self.logger.info(f"Siguiendo a @{username}")
            else:
                result["message"] = "No se pudo confirmar la acción de seguir"
                self.logger.warning(f"No se pudo confirmar que se sigue a @{username}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al seguir a @{username}: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def like_post(self, post_index: int = 0, username: str = None) -> Dict:
        """
        Dar like a una publicación en el perfil actual o en el feed.
        
        Args:
            post_index: Índice de la publicación (0 = primera)
            username: Nombre de usuario opcional para contexto
        
        Returns:
            dict: Resultado de la acción de like
        """
        result = {
            "action": "like",
            "status": "error",
            "post_index": post_index,
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        if username:
            result["username"] = username
        
        try:
            # Buscar botones de like en la página actual
            like_buttons = await self._find_elements("like")
            
            if not like_buttons or len(like_buttons) == 0:
                result["message"] = "No se encontraron botones de like"
                self.logger.warning(f"No se encontraron botones de like en la página actual")
                return result
            
            # Verificar si el índice está en rango
            if post_index >= len(like_buttons):
                result["message"] = f"Índice fuera de rango: {post_index} (max: {len(like_buttons)-1})"
                self.logger.warning(f"Índice de post fuera de rango: {post_index}")
                return result
            
            # Obtener el botón específico
            target_button = like_buttons[post_index]
            
            # Verificar si ya tiene like (el selector puede variar)
            button_label = await target_button.get_attribute("aria-label")
            if button_label and ". Liked" in button_label:
                result["status"] = "info"
                result["message"] = "La publicación ya tiene like"
                self.logger.info(f"La publicación {post_index} ya tiene like")
                return result
            
            # Añadir pequeña pausa antes de dar like
            await self._human_delay("before_like")
            
            # Dar like
            await target_button.click()
            
            # Esperar un momento para verificar
            await self._human_delay("between_actions")
            
            # Verificar si se dio like correctamente (aquí podríamos buscar el cambio visual)
            result["status"] = "success"
            result["message"] = "Like dado correctamente"
            self.logger.info(f"Like dado a publicación {post_index}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al dar like a publicación {post_index}: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def like_multiple_posts(self, count: int = 1, username: str = None) -> Dict:
        """
        Dar like a múltiples publicaciones en el perfil o feed actual.
        
        Args:
            count: Número de likes a dar
            username: Nombre de usuario opcional para contexto
        
        Returns:
            dict: Resultado de las acciones de like
        """
        result = {
            "action": "like_multiple",
            "status": "error",
            "requested": count,
            "successful": 0,
            "already_liked": 0,
            "failed": 0,
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        if username:
            result["username"] = username
        
        try:
            # Buscar botones de like en la página actual
            like_buttons = await self._find_elements("like")
            
            if not like_buttons or len(like_buttons) == 0:
                result["message"] = "No se encontraron botones de like"
                self.logger.warning(f"No se encontraron botones de like en la página actual")
                return result
            
            # Limitar cantidad según disponibilidad
            available = len(like_buttons)
            actual_count = min(count, available)
            
            # Seleccionar índices aleatorios sin repetición
            if actual_count < available:
                indices = random.sample(range(available), actual_count)
            else:
                indices = range(available)
            
            self.logger.info(f"Intentando dar {actual_count} likes de {available} disponibles")
            
            # Procesar cada botón
            for idx in indices:
                # Obtener el botón específico
                target_button = like_buttons[idx]
                
                # Verificar si ya tiene like
                button_label = await target_button.get_attribute("aria-label")
                if button_label and ". Liked" in button_label:
                    result["already_liked"] += 1
                    self.logger.info(f"Publicación {idx} ya tiene like")
                    continue
                
                try:
                    # Añadir pequeña pausa antes de dar like
                    await self._human_delay("before_like")
                    
                    # Dar like
                    await target_button.click()
                    
                    # Esperar un momento entre likes
                    await self._human_delay("between_actions")
                    
                    # Registrar éxito
                    result["successful"] += 1
                    self.logger.info(f"Like dado a publicación {idx}")
                    
                except Exception as e:
                    self.logger.error(f"Error al dar like a publicación {idx}: {e}")
                    result["failed"] += 1
            
            # Actualizar estado general
            if result["successful"] > 0:
                result["status"] = "success"
                result["message"] = f"Se dieron {result['successful']} likes correctamente"
            elif result["already_liked"] > 0:
                result["status"] = "info"
                result["message"] = f"No se dieron nuevos likes, {result['already_liked']} ya tenían like"
            else:
                result["message"] = "No se pudo dar ningún like"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al dar múltiples likes: {e}")
            result["message"] = f"Error general: {str(e)}"
            return result
    
    async def comment_on_post(self, post_index: int = 0, comment_text: str = None, username: str = None) -> Dict:
        """
        Comentar en una publicación.
        
        Args:
            post_index: Índice de la publicación (0 = primera)
            comment_text: Texto del comentario (si es None, se genera uno aleatorio)
            username: Nombre de usuario opcional para contexto
        
        Returns:
            dict: Resultado de la acción de comentar
        """
        result = {
            "action": "comment",
            "status": "error",
            "post_index": post_index,
            "comment_text": comment_text,
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        if username:
            result["username"] = username
        
        # Si no se proporcionó texto, generar uno aleatorio
        if not comment_text:
            comments = self.config.get("comments", {}).get("generic", [
                "Excelente contenido", "Muy interesante", "Gracias por compartir"
            ])
            comment_text = random.choice(comments)
            result["comment_text"] = comment_text
        
        try:
            # Buscar botones de respuesta (reply)
            reply_buttons = await self._find_elements("reply")
            
            if not reply_buttons or len(reply_buttons) == 0:
                result["message"] = "No se encontraron botones de respuesta"
                self.logger.warning("No se encontraron botones de respuesta en la página actual")
                return result
            
            # Verificar si el índice está en rango
            if post_index >= len(reply_buttons):
                result["message"] = f"Índice fuera de rango: {post_index} (max: {len(reply_buttons)-1})"
                self.logger.warning(f"Índice de post fuera de rango: {post_index}")
                return result
            
            # Obtener el botón específico
            target_button = reply_buttons[post_index]
            
            # Añadir pequeña pausa antes de hacer clic
            await self._human_delay("before_comment")
            
            # Hacer clic en el botón de respuesta
            await target_button.click()
            
            # Esperar a que aparezca el campo de texto
            await self._human_delay("between_actions")
            
            # Buscar el campo de comentario
            comment_field = await self._find_element("comment_field")
            if not comment_field:
                result["message"] = "No se encontró campo de comentario"
                self.logger.warning("No se encontró campo de comentario después de hacer clic en Reply")
                return result
            
            # Escribir el comentario con comportamiento humano
            await self._human_typing(comment_field, comment_text)
            
            # Pequeña pausa antes de enviar
            await self._human_delay("between_actions")
            
            # Buscar botón de envío
            send_button = await self._find_element("send_comment")
            if not send_button:
                result["message"] = "No se encontró botón de enviar comentario"
                self.logger.warning("No se encontró botón para enviar el comentario")
                return result
            
            # Enviar comentario
            await send_button.click()
            
            # Esperar a que se procese
            await asyncio.sleep(3)  # Espera más larga para asegurar
            
            # Registrar éxito
            result["status"] = "success"
            result["message"] = "Comentario enviado correctamente"
            self.logger.info(f"Comentario enviado: '{comment_text}'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al comentar: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def perform_warmup_session(self, phase: int, day: int) -> Dict:
        """
        Realizar una sesión completa de warmup según la fase y día.
        
        Args:
            phase: Número de fase (1-3)
            day: Número de día dentro de la fase (1-3)
        
        Returns:
            dict: Resultados completos de la sesión
        """
        result = {
            "phase": phase,
            "day": day,
            "status": "error",
            "actions": {
                "feed_activity": {},
                "profile_visits": [],
                "follows": [],
                "likes": [],
                "comments": []
            },
            "message": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Cargar config para la fase/día
            phase_config = self.config.get("phases", {}).get(str(phase), {}).get("days", {}).get(str(day), {})
            
            if not phase_config:
                result["message"] = f"No se encontró configuración para Fase {phase}, Día {day}"
                self.logger.error(f"Configuración no encontrada para Fase {phase}, Día {day}")
                return result
            
            # 1. Navegar a home
            home_success = await self.navigate_to_home()
            if not home_success:
                result["message"] = "No se pudo navegar a home"
                return result
            
            # 2. Scroll en feed
            feed_scrolls = random.randint(
                phase_config.get("feed_scrolls", {}).get("min", 3),
                phase_config.get("feed_scrolls", {}).get("max", 7)
            )
            
            feed_result = await self.scroll_feed(feed_scrolls, feed_scrolls)
            result["actions"]["feed_activity"] = feed_result
            
            # 3. Navegar a perfiles y realizar acciones según config
            profiles_to_visit = random.randint(
                phase_config.get("profile_visits", {}).get("min", 5),
                phase_config.get("profile_visits", {}).get("max", 8)
            )
            
            follows_to_do = random.randint(
                phase_config.get("follows", {}).get("min", 0),
                phase_config.get("follows", {}).get("max", 0)
            )
            
            likes_to_do = random.randint(
                phase_config.get("likes", {}).get("min", 0),
                phase_config.get("likes", {}).get("max", 0)
            )
            
            comments_to_do = random.randint(
                phase_config.get("comments", {}).get("min", 0),
                phase_config.get("comments", {}).get("max", 0)
            )
            
            # Obtener usuarios objetivo de diferentes categorías
            target_users = []
            categories = ["influencers", "news", "politicians", "brands"]
            
            for category in categories:
                category_accounts = self.config.get("target_accounts", {}).get(category, [])
                if category_accounts:
                    # Tomar algunos de cada categoría
                    sample_size = min(len(category_accounts), profiles_to_visit // len(categories) + 1)
                    target_users.extend(random.sample(category_accounts, sample_size))
            
            # Mezclar y limitar
            random.shuffle(target_users)
            target_users = target_users[:profiles_to_visit]
            
            # Contadores de acciones realizadas
            follows_done = 0
            likes_done = 0
            comments_done = 0
            
            # Visitar cada perfil y realizar acciones
            for username in target_users:
                # Navegar al perfil
                profile_success = await self.navigate_to_profile(username)
                
                if profile_success:
                    # Registrar visita al perfil
                    result["actions"]["profile_visits"].append({
                        "username": username,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Scroll en el perfil
                    await self.scroll_profile(username, 2, 4)
                    
                    # Follow (si queda por hacer)
                    if follows_done < follows_to_do:
                        follow_result = await self.follow_user(username)
                        
                        if follow_result["status"] == "success":
                            follows_done += 1
                            result["actions"]["follows"].append(follow_result)
                    
                    # Likes (si queda por hacer)
                    if likes_done < likes_to_do:
                        # Determinar cuántos likes dar en este perfil
                        likes_remaining = likes_to_do - likes_done
                        likes_this_profile = min(likes_remaining, random.randint(1, 3))
                        
                        like_result = await self.like_multiple_posts(likes_this_profile, username)
                        
                        if like_result["status"] in ["success", "info"]:
                            likes_done += like_result["successful"]
                            result["actions"]["likes"].append(like_result)
                    
                    # Comment (si queda por hacer y solo en fases avanzadas)
                    if comments_done < comments_to_do and phase >= 2:
                        comment_result = await self.comment_on_post(0, None, username)
                        
                        if comment_result["status"] == "success":
                            comments_done += 1
                            result["actions"]["comments"].append(comment_result)
                
                # Ir a home entre perfiles ocasionalmente
                if random.random() < 0.3:  # 30% de probabilidad
                    await self.navigate_to_home()
                    await self.scroll_feed(1, 3)  # Scroll breve
                
                # Pausa entre perfiles
                await self._human_delay("between_profiles")
            
            # Navegar a home para finalizar
            await self.navigate_to_home()
            
            # Actualizar resultado final
            result["status"] = "success"
            result["message"] = f"Sesión de warmup completada: Fase {phase}, Día {day}"
            
            # Estadísticas
            result["statistics"] = {
                "profiles_visited": len(result["actions"]["profile_visits"]),
                "follows_performed": follows_done,
                "likes_given": likes_done,
                "comments_made": comments_done
            }
            
            self.logger.info(f"Sesión de warmup completada: {result['statistics']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error durante sesión de warmup: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            result["message"] = f"Error general: {str(e)}"
            return result