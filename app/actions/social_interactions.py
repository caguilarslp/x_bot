#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import random
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Configuración de logging
logger = logging.getLogger(__name__)

class SocialInteractions:
    """
    Clase para manejar interacciones sociales en X.com (follow, like, comment)
    con implementación de comportamiento humano y anti-detección.
    """

    def __init__(self, page, config_path='app/config/social_config.json'):
        """
        Inicializa la clase de interacciones sociales.
        
        Args:
            page: Página Playwright con sesión activa
            config_path: Ruta al archivo de configuración (opcional)
        """
        self.page = page
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
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
        
        # Estado de la sesión actual
        self.session_stats = {
            "follows_performed": 0,
            "likes_performed": 0,
            "comments_performed": 0,
            "profiles_visited": 0,
            "start_time": datetime.now()
        }
    
    def _load_config(self, config_path):
        """
        Cargar configuración de interacciones sociales desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            dict: Configuración cargada o configuración por defecto
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Intentar en rutas alternativas
                alt_path = os.path.join("app", "config", "social_config.json")
                if os.path.exists(alt_path):
                    with open(alt_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                        
                self.logger.warning(f"Archivo de configuración no encontrado: {config_path}")
                return self._create_default_config()
        except Exception as e:
            self.logger.error(f"Error al cargar configuración: {e}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """
        Crear configuración por defecto para interacciones sociales.
        
        Returns:
            dict: Configuración por defecto
        """
        return {
            "delays": {
                "between_actions": {"min": 2, "max": 8},
                "between_follows": {"min": 10, "max": 30},
                "between_likes": {"min": 5, "max": 20},
                "between_comments": {"min": 15, "max": 45},
                "before_follow": {"min": 2, "max": 5},
                "before_like": {"min": 1, "max": 3},
                "between_typing": {"min": 0.05, "max": 0.15}
            },
            "limits": {
                "max_follows_per_session": 10,
                "max_likes_per_session": 25,
                "max_comments_per_session": 5,
                "max_profiles_per_session": 20,
                "session_duration_minutes": 60
            },
            "comments": [
                "¡Excelente publicación!",
                "Muy interesante 👍",
                "Totalmente de acuerdo",
                "Gracias por compartir esto",
                "Información muy valiosa",
                "Me encanta este contenido",
                "Increíble punto de vista",
                "Esto es genial, gracias",
                "Completamente de acuerdo contigo",
                "Muy útil, gracias por compartir"
            ]
        }
    
    async def _human_delay(self, delay_type="between_actions"):
        """
        Aplicar un retraso que simula comportamiento humano.
        
        Args:
            delay_type: Tipo de retraso a aplicar
        """
        delay_config = self.config["delays"].get(delay_type, {"min": 2, "max": 8})
        delay = random.uniform(delay_config["min"], delay_config["max"])
        await asyncio.sleep(delay)
    
    async def _human_typing(self, element, text):
        """
        Simular escritura humana en un elemento con pausas realistas.
        
        Args:
            element: Elemento DOM donde escribir
            text: Texto a escribir
        """
        # Limpiar campo primero si es necesario
        try:
            await element.fill("")
        except Exception:
            self.logger.debug("No se pudo limpiar el campo antes de escribir")
        
        # Pequeña pausa antes de empezar a escribir
        await self._human_delay("before_like")
        
        # Velocidad de escritura variable por caracter
        typing_config = self.config["delays"].get("between_typing", {"min": 0.05, "max": 0.15})
        
        # Escribir caracter por caracter
        for char in text:
            typing_delay = random.uniform(typing_config["min"], typing_config["max"])
            await element.type(char, delay=int(typing_delay * 1000))  # Convertir a milisegundos
            
            # Pausas ocasionales para simular pensamiento
            if random.random() < 0.05:  # 5% de probabilidad
                await asyncio.sleep(random.uniform(0.3, 1.2))
    
    async def _within_session_limits(self, action_type):
        """
        Verificar si estamos dentro de los límites de la sesión actual.
        
        Args:
            action_type: Tipo de acción (follow, like, comment)
        
        Returns:
            bool: True si podemos realizar la acción, False en caso contrario
        """
        # Verificar duración de la sesión
        elapsed_minutes = (datetime.now() - self.session_stats["start_time"]).total_seconds() / 60
        max_duration = self.config["limits"].get("session_duration_minutes", 60)
        
        if elapsed_minutes > max_duration:
            self.logger.warning(f"Sesión ha superado la duración máxima ({max_duration} minutos)")
            return False
        
        # Verificar límites específicos por tipo de acción
        if action_type == "follow":
            limit_key = "max_follows_per_session"
            current = self.session_stats["follows_performed"]
        elif action_type == "like":
            limit_key = "max_likes_per_session"
            current = self.session_stats["likes_performed"]
        elif action_type == "comment":
            limit_key = "max_comments_per_session"
            current = self.session_stats["comments_performed"]
        elif action_type == "profile_visit":
            limit_key = "max_profiles_per_session"
            current = self.session_stats["profiles_visited"]
        else:
            self.logger.warning(f"Tipo de acción desconocido: {action_type}")
            return True  # Si no conocemos el tipo, permitimos
        
        limit = self.config["limits"].get(limit_key, 999)
        
        if current >= limit:
            self.logger.warning(f"Límite alcanzado para {action_type}: {current}/{limit}")
            return False
            
        return True
    
    async def navigate_to_profile(self, username):
        """
        Navegar al perfil de un usuario.
        
        Args:
            username: Nombre de usuario sin "@" o URL completa
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            # Limpiar el nombre de usuario si contiene "@"
            if username.startswith("@"):
                username = username[1:]
            
            # Si ya es una URL completa, usarla directamente
            if username.startswith("http"):
                url = username
            else:
                url = f"https://x.com/{username}"
            
            self.logger.info(f"Navegando al perfil: {url}")
            
            # Verificar si ya estamos en este perfil
            current_url = self.page.url.lower()
            if f"/{username.lower()}" in current_url:
                self.logger.info(f"Ya estamos en el perfil de @{username}")
                return True
            
            # Navegar al perfil
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)  # Esperar a que cargue
                
                # Verificar si llegamos correctamente comprobando la URL
                new_url = self.page.url.lower()
                if f"/{username.lower()}" in new_url:
                    self.logger.info(f"Navegación exitosa al perfil de @{username}")
                    
                    # Incrementar contador de perfiles visitados
                    self.session_stats["profiles_visited"] += 1
                    
                    # Esperar un poco para simular navegación natural
                    await self._human_delay("between_actions")
                    return True
                else:
                    self.logger.warning(f"URL incorrecta después de navegar: {new_url}")
                    return False
                
            except Exception as e:
                self.logger.error(f"Error navegando al perfil: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error general en navigate_to_profile: {e}")
            return False
    
    async def navigate_to_home(self):
        """
        Navegar a la página de inicio.
        
        Returns:
            bool: True si la navegación fue exitosa
        """
        try:
            self.logger.info("Navegando a home")
            
            # Verificar si ya estamos en home
            current_url = self.page.url.lower()
            if "/home" in current_url:
                self.logger.info("Ya estamos en home")
                return True
            
            # Intentar con el botón de home primero
            try:
                home_link = await self.page.query_selector(self.selectors["navigation"]["home_link"])
                if home_link:
                    await home_link.click()
                    await asyncio.sleep(3)
                    
                    # Verificar si llegamos a home
                    new_url = self.page.url.lower()
                    if "/home" in new_url:
                        self.logger.info("Navegación a home exitosa mediante botón")
                        return True
            except Exception as e:
                self.logger.warning(f"Error al hacer clic en botón de home: {e}")
            
            # Si falló el botón, usar navegación directa
            await self.page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # Verificar si llegamos correctamente
            new_url = self.page.url.lower()
            if "/home" in new_url:
                self.logger.info("Navegación a home exitosa")
                return True
            else:
                self.logger.warning(f"URL incorrecta después de navegar a home: {new_url}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error navegando a home: {e}")
            return False
    
    async def follow_user(self, username):
        """
        Seguir a un usuario.
        
        Args:
            username: Nombre de usuario a seguir
        
        Returns:
            dict: Resultado de la operación con detalles
        """
        result = {
            "action": "follow",
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": ""
        }
        
        # Verificar límites de sesión
        if not await self._within_session_limits("follow"):
            result["message"] = "Se ha superado el límite de follows para esta sesión"
            return result
        
        try:
            # Navegar al perfil si es necesario
            if not username.startswith("http") and f"/{username.lower()}" not in self.page.url.lower():
                profile_success = await self.navigate_to_profile(username)
                if not profile_success:
                    result["message"] = f"No se pudo navegar al perfil de @{username}"
                    return result
            
            # Verificar si ya seguimos al usuario
            already_following = await self.page.query_selector(self.selectors["follow"]["already_following"])
            if already_following:
                self.logger.info(f"Ya sigues a @{username}")
                result["status"] = "info"
                result["message"] = f"Ya sigues a @{username}"
                return result
            
            # Buscar el botón de follow
            follow_button = await self.page.query_selector(self.selectors["follow"]["primary"])
            
            if not follow_button:
                self.logger.warning(f"No se encontró el botón de follow para @{username}")
                result["message"] = "No se encontró el botón de follow"
                return result
            
            # Esperar un poco antes de hacer clic (comportamiento humano)
            await self._human_delay("before_follow")
            
            # Hacer clic en el botón de follow
            self.logger.info(f"Haciendo clic en botón de follow para @{username}")
            await follow_button.click()
            
            # Esperar un momento para que se procese la acción
            await asyncio.sleep(2)
            
            # Verificar si ahora estamos siguiendo al usuario
            confirmation = await self.page.query_selector(self.selectors["follow"]["already_following"])
            
            if confirmation:
                self.logger.info(f"¡Ahora sigues a @{username}!")
                result["status"] = "success"
                result["message"] = f"Ahora sigues a @{username}"
                
                # Actualizar contador
                self.session_stats["follows_performed"] += 1
                
                # Espera adicional después de un follow
                await self._human_delay("between_follows")
            else:
                self.logger.warning(f"No se pudo confirmar que sigues a @{username}")
                result["message"] = "No se pudo confirmar la acción de follow"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al seguir a @{username}: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def unfollow_user(self, username):
        """
        Dejar de seguir a un usuario.
        
        Args:
            username: Nombre de usuario a dejar de seguir
        
        Returns:
            dict: Resultado de la operación con detalles
        """
        result = {
            "action": "unfollow",
            "username": username,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": ""
        }
        
        try:
            # Navegar al perfil si es necesario
            if not username.startswith("http") and f"/{username.lower()}" not in self.page.url.lower():
                profile_success = await self.navigate_to_profile(username)
                if not profile_success:
                    result["message"] = f"No se pudo navegar al perfil de @{username}"
                    return result
            
            # Verificar si seguimos al usuario
            unfollow_button = await self.page.query_selector(self.selectors["follow"]["already_following"])
            
            if not unfollow_button:
                self.logger.info(f"No estás siguiendo a @{username}")
                result["status"] = "info"
                result["message"] = f"No estás siguiendo a @{username}"
                return result
            
            # Esperar un poco antes de hacer clic (comportamiento humano)
            await self._human_delay("before_follow")
            
            # Hacer clic en el botón de unfollow
            self.logger.info(f"Haciendo clic en botón de unfollow para @{username}")
            await unfollow_button.click()
            
            # Esperar confirmación modal (en algunos casos)
            try:
                # Buscar botón de confirmación (puede aparecer o no)
                confirm_button = await self.page.wait_for_selector(
                    '//span[contains(text(), "Dejar de seguir") or contains(text(), "Unfollow")]',
                    timeout=3000
                )
                
                if confirm_button:
                    self.logger.info("Confirmando unfollow en modal")
                    await confirm_button.click()
            except Exception:
                self.logger.info("No se mostró modal de confirmación para unfollow")
            
            # Esperar un momento para que se procese la acción
            await asyncio.sleep(2)
            
            # Verificar si ahora hay un botón de follow visible
            confirmation = await self.page.query_selector(self.selectors["follow"]["primary"])
            
            if confirmation:
                self.logger.info(f"Has dejado de seguir a @{username}")
                result["status"] = "success"
                result["message"] = f"Has dejado de seguir a @{username}"
                
                # Espera adicional después de un unfollow
                await self._human_delay("between_follows")
            else:
                self.logger.warning(f"No se pudo confirmar que has dejado de seguir a @{username}")
                result["message"] = "No se pudo confirmar la acción de unfollow"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error al dejar de seguir a @{username}: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def like_post(self, post_url=None, index=0):
        """
        Dar like a un post específico.
        
        Args:
            post_url: URL del post a dar like (opcional)
            index: Índice del post en la página actual si no se especifica URL
        
        Returns:
            dict: Resultado de la operación con detalles
        """
        result = {
            "action": "like",
            "post_url": post_url,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": ""
        }
        
        # Verificar límites de sesión
        if not await self._within_session_limits("like"):
            result["message"] = "Se ha superado el límite de likes para esta sesión"
            return result
        
        try:
            # Si se proporciona URL, navegar al post
            if post_url:
                self.logger.info(f"Navegando al post: {post_url}")
                await self.page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Buscar botón de like
                like_button = await self.page.query_selector(self.selectors["like"]["primary"])
                already_liked = await self.page.query_selector(self.selectors["like"]["already_liked"])
                
                if already_liked:
                    self.logger.info("Este post ya tiene like")
                    result["status"] = "info"
                    result["message"] = "Este post ya tiene like"
                    return result
                
                if not like_button:
                    self.logger.warning("No se encontró el botón de like")
                    result["message"] = "No se encontró el botón de like"
                    return result
                
                # Esperar un poco antes de dar like
                await self._human_delay("before_like")
                
                # Dar like
                await like_button.click()
                
                # Esperar para verificar
                await asyncio.sleep(1)
                
                # Verificar si se dio like (debe aparecer botón de unlike)
                confirmation = await self.page.query_selector(self.selectors["like"]["already_liked"])
                
                if confirmation:
                    self.logger.info("¡Like dado correctamente!")
                    result["status"] = "success"
                    result["message"] = "Like dado correctamente"
                    
                    # Actualizar contador
                    self.session_stats["likes_performed"] += 1
                    
                    # Espera adicional después de un like
                    await self._human_delay("between_likes")
                else:
                    self.logger.warning("No se pudo confirmar que se dio like")
                    result["message"] = "No se pudo confirmar la acción de like"
                
                return result
                
            # Si no se proporciona URL, usar índice en la página actual
            else:
                # Buscar posts en la página actual
                posts = await self.page.query_selector_all(self.selectors["posts"]["tweet_articles"])
                
                if not posts or len(posts) == 0:
                    self.logger.warning("No se encontraron posts en la página actual")
                    result["message"] = "No se encontraron posts"
                    return result
                
                if index >= len(posts):
                    self.logger.warning(f"Índice {index} fuera de rango (hay {len(posts)} posts)")
                    result["message"] = f"Índice {index} fuera de rango (hay {len(posts)} posts)"
                    return result
                
                # Obtener el post según el índice
                post = posts[index]
                
                # Buscar botón de like dentro del post
                like_button = await post.query_selector(self.selectors["like"]["primary"])
                already_liked = await post.query_selector(self.selectors["like"]["already_liked"])
                
                if already_liked:
                    self.logger.info(f"El post {index} ya tiene like")
                    result["status"] = "info"
                    result["message"] = f"El post {index} ya tiene like"
                    return result
                
                if not like_button:
                    self.logger.warning(f"No se encontró el botón de like en el post {index}")
                    result["message"] = f"No se encontró el botón de like en el post {index}"
                    return result
                
                # Intentar obtener URL del post para el registro
                try:
                    post_link = await post.query_selector('a[href*="/status/"]')
                    if post_link:
                        href = await post_link.get_attribute("href")
                        full_url = href if href.startswith("http") else f"https://x.com{href}"
                        result["post_url"] = full_url
                except Exception:
                    pass
                
                # Esperar un poco antes de dar like
                await self._human_delay("before_like")
                
                # Dar like
                await like_button.click()
                
                # Esperar para verificar
                await asyncio.sleep(1)
                
                # Verificar si se dio like (debe aparecer botón de unlike)
                confirmation = await post.query_selector(self.selectors["like"]["already_liked"])
                
                if confirmation:
                    self.logger.info(f"¡Like dado correctamente al post {index}!")
                    result["status"] = "success"
                    result["message"] = f"Like dado correctamente al post {index}"
                    
                    # Actualizar contador
                    self.session_stats["likes_performed"] += 1
                    
                    # Espera adicional después de un like
                    await self._human_delay("between_likes")
                else:
                    self.logger.warning(f"No se pudo confirmar que se dio like al post {index}")
                    result["message"] = f"No se pudo confirmar la acción de like en el post {index}"
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error al dar like: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def perform_likes(self, count=1):
        """
        Dar like a varios posts en el perfil o feed actual.
        
        Args:
            count: Número de likes a dar
        
        Returns:
            dict: Estadísticas de la operación
        """
        stats = {
            "action": "multiple_likes",
            "timestamp": datetime.now().isoformat(),
            "requested": count,
            "successful": 0,
            "already_liked": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            # Buscar posts en la página actual
            posts = await self.page.query_selector_all(self.selectors["posts"]["tweet_articles"])
            
            if not posts or len(posts) == 0:
                self.logger.warning("No se encontraron posts para dar like")
                return stats
            
            # Ajustar la cantidad según los posts disponibles
            actual_count = min(count, len(posts))
            self.logger.info(f"Se encontraron {len(posts)} posts, se intentará dar like a {actual_count}")
            
            for i in range(actual_count):
                # Verificar límites de sesión
                if not await self._within_session_limits("like"):
                    self.logger.warning("Se alcanzó el límite de likes para esta sesión")
                    break
                
                result = await self.like_post(index=i)
                stats["details"].append(result)
                
                if result["status"] == "success":
                    stats["successful"] += 1
                elif result["status"] == "info" and "ya tiene like" in result["message"]:
                    stats["already_liked"] += 1
                else:
                    stats["failed"] += 1
                
                # Pequeña pausa entre likes para evitar detección
                if i < actual_count - 1:
                    await asyncio.sleep(random.uniform(1, 3))
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error en perform_likes: {e}")
            stats["message"] = f"Error: {str(e)}"
            return stats
    
    async def comment_on_post(self, post_url=None, comment_text=None, index=0):
        """
        Comentar en un post específico.
        
        Args:
            post_url: URL del post a comentar (opcional)
            comment_text: Texto del comentario (si es None, se generará uno aleatorio)
            index: Índice del post en la página actual si no se especifica URL
        
        Returns:
            dict: Resultado de la operación con detalles
        """
        result = {
            "action": "comment",
            "post_url": post_url,
            "comment_text": comment_text,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "message": ""
        }
        
        # Verificar límites de sesión
        if not await self._within_session_limits("comment"):
            result["message"] = "Se ha superado el límite de comentarios para esta sesión"
            return result
        
        # Si no se proporciona texto, generar uno aleatorio
        if not comment_text:
            available_comments = self.config.get("comments", [
                "¡Excelente publicación!",
                "Muy interesante 👍",
                "Gracias por compartir"
            ])
            comment_text = random.choice(available_comments)
            result["comment_text"] = comment_text
        
        try:
            current_url = self.page.url
            
            # Si se proporciona URL, navegar al post
            if post_url:
                self.logger.info(f"Navegando al post: {post_url}")
                await self.page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Buscar botón de reply
                reply_button = await self.page.query_selector(self.selectors["comment"]["reply_button"])
                
                if not reply_button:
                    self.logger.warning("No se encontró el botón de reply")
                    result["message"] = "No se encontró el botón de reply"
                    return result
                
                # Hacer clic en reply
                await reply_button.click()
                await asyncio.sleep(2)
                
                # Buscar campo de texto
                textarea = await self.page.query_selector(self.selectors["comment"]["tweet_textarea"])
                
                if not textarea:
                    self.logger.warning("No se encontró el campo de texto para comentar")
                    result["message"] = "No se encontró el campo de texto para comentar"
                    return result
                
                # Escribir comentario con comportamiento humano
                await self._human_typing(textarea, comment_text)
                
                # Buscar botón de enviar
                send_button = await self.page.query_selector(self.selectors["comment"]["send_button"])
                
                if not send_button:
                    self.logger.warning("No se encontró el botón para enviar comentario")
                    result["message"] = "No se encontró el botón para enviar comentario"
                    return result
                
                # Enviar comentario
                await send_button.click()
                
                # Esperar a que se procese
                await asyncio.sleep(3)
                
                # Verificar si el comentario se publicó (difícil de verificar directamente,
                # asumimos éxito si no hubo errores evidentes)
                result["status"] = "success"
                result["message"] = "Comentario publicado correctamente"
                
                # Actualizar contador
                self.session_stats["comments_performed"] += 1
                
                # Espera adicional después de un comentario
                await self._human_delay("between_comments")
                
                # Intentar cerrar modal si existe
                try:
                    close_button = await self.page.query_selector(self.selectors["comment"]["close_button"])
                    if close_button:
                        await close_button.click()
                        await asyncio.sleep(1)
                except Exception:
                    pass
                
                return result
                
            # Si no se proporciona URL, usar índice en la página actual
            else:
                # Buscar posts en la página actual
                posts = await self.page.query_selector_all(self.selectors["posts"]["tweet_articles"])
                
                if not posts or len(posts) == 0:
                    self.logger.warning("No se encontraron posts en la página actual")
                    result["message"] = "No se encontraron posts"
                    return result
                
                if index >= len(posts):
                    self.logger.warning(f"Índice {index} fuera de rango (hay {len(posts)} posts)")
                    result["message"] = f"Índice {index} fuera de rango (hay {len(posts)} posts)"
                    return result
                
                # Obtener el post según el índice
                post = posts[index]
                
                # Intentar obtener URL del post para el registro
                try:
                    post_link = await post.query_selector('a[href*="/status/"]')
                    if post_link:
                        href = await post_link.get_attribute("href")
                        full_url = href if href.startswith("http") else f"https://x.com{href}"
                        result["post_url"] = full_url
                        
                        # Navegar al post para comentar
                        return await self.comment_on_post(post_url=full_url, comment_text=comment_text)
                except Exception as e:
                    self.logger.error(f"Error al obtener URL del post para comentar: {e}")
                    result["message"] = "No se pudo obtener URL del post para comentar"
                    return result
                
        except Exception as e:
            self.logger.error(f"Error al comentar en post: {e}")
            result["message"] = f"Error: {str(e)}"
            return result
    
    async def scroll_profile(self, min_scrolls=3, max_scrolls=7):
        """
        Realizar scroll en un perfil para ver más contenido.
        
        Args:
            min_scrolls: Mínimo número de scrolls
            max_scrolls: Máximo número de scrolls
        
        Returns:
            tuple: (éxito, lista de URLs de posts encontrados)
        """
        self.logger.info(f"Haciendo scroll en perfil ({min_scrolls}-{max_scrolls} scrolls)")
        post_urls = []
        
        try:
            # Determinar número de scrolls
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            
            for i in range(num_scrolls):
                # Simular scroll humano
                scroll_distance = random.randint(300, 800)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # Pausa variable entre scrolls
                await asyncio.sleep(random.uniform(0.8, 2.5))
                
                # Recolectar URLs de posts cada 2 scrolls
                if i % 2 == 0 or i == num_scrolls - 1:
                    post_links = await self.page.query_selector_all(self.selectors["posts"]["post_links"])
                    
                    for link in post_links:
                        try:
                            href = await link.get_attribute("href")
                            if href and "/status/" in href:
                                full_url = href if href.startswith("http") else f"https://x.com{href}"
                                if full_url not in post_urls:
                                    post_urls.append(full_url)
                        except Exception:
                            continue
                
                # Pausar ocasionalmente para simular lectura
                if random.random() < 0.3:  # 30% de probabilidad
                    await asyncio.sleep(random.uniform(1.5, 4.0))
            
            self.logger.info(f"Scroll completado: {num_scrolls} scrolls, {len(post_urls)} posts encontrados")
            return True, post_urls
            
        except Exception as e:
            self.logger.error(f"Error al hacer scroll en perfil: {e}")
            return False, post_urls
    
    async def scroll_feed(self, min_scrolls=3, max_scrolls=10):
        """
        Realizar scroll en el feed para ver más contenido.
        
        Args:
            min_scrolls: Mínimo número de scrolls
            max_scrolls: Máximo número de scrolls
        
        Returns:
            tuple: (éxito, lista de URLs de posts encontrados)
        """
        self.logger.info(f"Haciendo scroll en el feed ({min_scrolls}-{max_scrolls} scrolls)")
        post_urls = []
        
        try:
            # Asegurar que estamos en el feed
            if "/home" not in self.page.url.lower():
                self.logger.info("No estamos en el feed, navegando a home")
                home_success = await self.navigate_to_home()
                if not home_success:
                    return False, []
            
            # Determinar número de scrolls
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            
            for i in range(num_scrolls):
                # Simular scroll humano
                scroll_distance = random.randint(300, 900)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                
                # Pausa variable entre scrolls
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                # Recolectar URLs de posts cada 3 scrolls
                if i % 3 == 0 or i == num_scrolls - 1:
                    post_links = await self.page.query_selector_all(self.selectors["posts"]["post_links"])
                    
                    for link in post_links:
                        try:
                            href = await link.get_attribute("href")
                            if href and "/status/" in href:
                                full_url = href if href.startswith("http") else f"https://x.com{href}"
                                if full_url not in post_urls:
                                    post_urls.append(full_url)
                        except Exception:
                            continue
                
                # Pausar ocasionalmente para simular lectura
                if random.random() < 0.4:  # 40% de probabilidad
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                    
                    # Ocasionalmente interactuar con un post (dar like)
                    if random.random() < 0.15:  # 15% de probabilidad
                        self.logger.info("Interactuando aleatoriamente con un post durante scroll")
                        await self.like_post(index=random.randint(0, 3))
            
            self.logger.info(f"Scroll en feed completado: {num_scrolls} scrolls, {len(post_urls)} posts encontrados")
            return True, post_urls
            
        except Exception as e:
            self.logger.error(f"Error al hacer scroll en feed: {e}")
            return False, post_urls
    
    async def batch_interact(self, profiles, actions):
        """
        Realizar interacciones en lote con múltiples perfiles.
        
        Args:
            profiles: Lista de nombres de usuario
            actions: Diccionario con acciones a realizar (follow, like, comment)
        
        Returns:
            dict: Estadísticas y resultados de las interacciones
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "profiles_processed": 0,
            "profiles_failed": 0,
            "follows_successful": 0,
            "likes_successful": 0,
            "comments_successful": 0,
            "details": []
        }
        
        # Asegurar home al inicio
        await self.navigate_to_home()
        await asyncio.sleep(2)
        
        for username in profiles:
            self.logger.info(f"Iniciando interacción con perfil: @{username}")
            
            profile_result = {
                "username": username,
                "visited": False,
                "actions": []
            }
            
            try:
                # 1. Navegar al perfil
                profile_success = await self.navigate_to_profile(username)
                
                if not profile_success:
                    self.logger.warning(f"No se pudo navegar al perfil de @{username}")
                    profile_result["error"] = "No se pudo navegar al perfil"
                    results["profiles_failed"] += 1
                    results["details"].append(profile_result)
                    continue
                
                profile_result["visited"] = True
                
                # 2. Hacer scroll para simular interés y recolectar posts
                scroll_success, posts = await self.scroll_profile(
                    min_scrolls=random.randint(2, 4),
                    max_scrolls=random.randint(4, 7)
                )
                
                profile_result["posts_found"] = len(posts)
                
                # 3. Ejecutar acciones según configuración
                
                # Follow
                if actions.get("follow", False):
                    follow_result = await self.follow_user(username)
                    profile_result["actions"].append(follow_result)
                    
                    if follow_result["status"] == "success":
                        results["follows_successful"] += 1
                
                # Like
                like_count = actions.get("like_count", 0)
                if like_count > 0:
                    like_results = await self.perform_likes(like_count)
                    profile_result["actions"].append(like_results)
                    
                    results["likes_successful"] += like_results["successful"]
                
                # Comment
                if actions.get("comment", False):
                    comment_text = actions.get("comment_text", None)
                    
                    # Si hay posts disponibles, comentar en el primero
                    if posts and len(posts) > 0:
                        comment_result = await self.comment_on_post(
                            post_url=posts[0],
                            comment_text=comment_text
                        )
                        profile_result["actions"].append(comment_result)
                        
                        if comment_result["status"] == "success":
                            results["comments_successful"] += 1
                
                results["profiles_processed"] += 1
                
                # 4. Volver a home ocasionalmente
                if random.random() < 0.7:  # 70% de probabilidad
                    await self.navigate_to_home()
                    # Ocasionalmente hacer scroll en home
                    if random.random() < 0.5:
                        await self.scroll_feed(
                            min_scrolls=random.randint(1, 3),
                            max_scrolls=random.randint(3, 5)
                        )
                
                # Espera entre perfiles
                await self._human_delay("between_actions")
                
            except Exception as e:
                self.logger.error(f"Error en interacción con @{username}: {e}")
                profile_result["error"] = str(e)
                results["profiles_failed"] += 1
            
            results["details"].append(profile_result)
        
        return results