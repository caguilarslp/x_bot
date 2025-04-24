#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import random
import logging
import json
import os
from datetime import datetime
from pathlib import Path

class SocialActions:
    """
    Clase para manejar acciones sociales en X.com como seguir usuarios,
    dar likes y comentar publicaciones usando técnicas anti-detección.
    """
    
    def __init__(self, page, config_path='app/config/action_config.json'):
        """
        Inicializa SocialActions con configuraciones y página de Playwright.
        
        Args:
            page: Página de Playwright con sesión activa
            config_path: Ruta al archivo de configuración de acciones
        """
        self.page = page
        self.logger = logging.getLogger(__name__)
        
        # Configuración de acciones
        self.config = self._load_config(config_path)
        
        # Estado de la sesión actual
        self.session_start_time = datetime.now()
        self.actions_performed = 0
        self.action_log = []
        
        # Selectores XPath para interacciones sociales
        self.selectors = {
            "follow": '//button[@data-testid="1589450359-follow"]',
            "following": '//button[@data-testid="1626214836-unfollow"]',
            "like": '//button[@data-testid="like"]',
            "reply": '//button[@data-testid="reply"]',
            "comment_field": '//div[@data-testid="tweetTextarea_0"]',
            "send_comment": '//button[@data-testid="tweetButton"]',
            "close_modal": '//button[@data-testid="app-bar-close"]',
            "tweet_articles": '//article[@data-testid="tweet"]'
        }
    
    def _load_config(self, config_path):
        """
        Cargar configuración de acciones desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            dict: Configuración de acciones
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            self.logger.warning(f"Archivo de configuración no encontrado: {config_path}")
            # Intentar en rutas alternativas
            alt_path = os.path.join("app", config_path)
            try:
                with open(alt_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return config
            except FileNotFoundError:
                self.logger.warning(f"Archivo alternativo tampoco encontrado: {alt_path}")
                return self._create_default_config()
        except json.JSONDecodeError:
            self.logger.error(f"Error de formato en {config_path}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """
        Crear configuración por defecto si no existe el archivo.
        
        Returns:
            dict: Configuración por defecto
        """
        return {
            "session_config": {
                "max_actions_per_session": 50,
                "session_duration_hours": 4
            },
            "action_delay": {
                "min": 2,
                "max": 10
            },
            "detection_risk_threshold": 0.7,
            "action_types": {
                "follow": {
                    "max_per_hour": 10,
                    "cool_down_time": 300,
                    "risk_level": 0.6
                },
                "like": {
                    "max_per_hour": 30,
                    "cool_down_time": 120,
                    "risk_level": 0.4
                },
                "comment": {
                    "max_per_hour": 5,
                    "cool_down_time": 600,
                    "risk_level": 0.8
                }
            }
        }
    
    async def _human_delay(self, min_delay=None, max_delay=None):
        """
        Simular retraso con comportamiento humano.
        
        Args:
            min_delay: Tiempo mínimo de espera (opcional)
            max_delay: Tiempo máximo de espera (opcional)
        """
        if min_delay is None:
            min_delay = self.config.get('action_delay', {}).get('min', 2)
        if max_delay is None:
            max_delay = self.config.get('action_delay', {}).get('max', 10)
        
        delay = random.uniform(min_delay, max_delay)
        self.logger.debug(f"Esperando {delay:.2f} segundos...")
        await asyncio.sleep(delay)
    
    async def _human_typing(self, element, text):
        """
        Simular escritura humana con variaciones en la velocidad.
        
        Args:
            element: Elemento DOM donde escribir
            text: Texto a escribir
        """
        # Limpiar el campo primero si es necesario
        await element.fill("")
        await self._human_delay(0.5, 1.5)
        
        # Velocidad base de escritura (caracteres por segundo)
        base_speed = random.uniform(0.05, 0.15)
        
        # Escribir caracter por caracter con variaciones
        for char in text:
            # Aplicar delay variable por caracter
            char_delay = base_speed * random.uniform(0.8, 1.2)
            await asyncio.sleep(char_delay)
            await element.press(char)
            
            # Pausas ocasionales para simular pensamiento
            if random.random() < 0.05:  # 5% de probabilidad
                thinking_pause = random.uniform(0.3, 1.5)
                await asyncio.sleep(thinking_pause)
    
    def _check_action_risk(self, action_type):
        """
        Evaluar el riesgo de detección para una acción.
        
        Args:
            action_type: Tipo de acción a realizar
        
        Returns:
            bool: Si la acción es segura de realizar
        """
        # Obtener configuración del tipo de acción
        action_config = self.config.get('action_types', {}).get(action_type, {})
        max_per_hour = action_config.get('max_per_hour', 10)
        risk_level = action_config.get('risk_level', 0.5)
        
        # Verificar límite de acciones por sesión
        session_config = self.config.get('session_config', {})
        max_session_actions = session_config.get('max_actions_per_session', 50)
        if self.actions_performed >= max_session_actions:
            self.logger.warning(f"Límite de acciones por sesión alcanzado ({max_session_actions})")
            return False
        
        # Calcular acciones de este tipo en la última hora
        one_hour_ago = datetime.now().timestamp() - 3600
        actions_this_hour = sum(
            1 for a in self.action_log 
            if a['type'] == action_type and a['timestamp'] > one_hour_ago
        )
        
        if actions_this_hour >= max_per_hour:
            self.logger.warning(f"Límite de acciones por hora alcanzado para {action_type} ({max_per_hour})")
            return False
        
        # Verificar umbral de riesgo de detección
        threshold = self.config.get('detection_risk_threshold', 0.7)
        if risk_level > threshold:
            # Si el nivel de riesgo es alto, aplicar restricciones adicionales
            # Por ejemplo, reducir el límite a la mitad si nos acercamos al umbral
            reduced_limit = max(1, max_per_hour // 2)
            if actions_this_hour >= reduced_limit:
                self.logger.warning(f"Acción de alto riesgo {action_type} limitada a {reduced_limit} por hora")
                return False
        
        return True
    
    def _log_action(self, action_type, result):
        """
        Registrar acción realizada en el log interno y en archivo.
        
        Args:
            action_type: Tipo de acción realizada
            result: Resultado de la acción
        """
        # Registrar en log interno
        action_record = {
            'type': action_type,
            'timestamp': datetime.now().timestamp(),
            'datetime': datetime.now().isoformat(),
            'result': result
        }
        self.action_log.append(action_record)
        
        # Registrar en archivo
        log_dir = Path(self.config.get('logging', {}).get('log_directory', 'logs/actions'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"social_actions_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            # Cargar log existente o crear nuevo
            if log_file.exists():
                with open(log_file, 'r+', encoding='utf-8') as f:
                    try:
                        log_data = json.load(f)
                    except json.JSONDecodeError:
                        log_data = []
                    
                    log_data.append(action_record)
                    f.seek(0)
                    json.dump(log_data, f, indent=2)
            else:
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([action_record], f, indent=2)
        except Exception as e:
            self.logger.error(f"Error al guardar log de acción: {e}")
    
    async def navigate_to_profile(self, username):
        """
        Navegar al perfil de un usuario específico.
        
        Args:
            username: Nombre de usuario a visitar (sin @)
        
        Returns:
            bool: Si la navegación fue exitosa
        """
        try:
            self.logger.info(f"Navegando al perfil de @{username}")
            
            # Asegurar que el username no incluye @ al principio
            username = username.lstrip('@')
            
            # Navegar a la URL del perfil
            profile_url = f"https://x.com/{username}"
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            
            # Esperar a que cargue el perfil (puede variar según la velocidad de conexión)
            await self._human_delay(3, 6)
            
            # Verificar que estamos en la página correcta
            current_url = self.page.url
            if username.lower() in current_url.lower():
                self.logger.info(f"Navegación exitosa a @{username}")
                return True
            else:
                self.logger.warning(f"Posible redirección: {current_url}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error al navegar al perfil @{username}: {e}")
            return False
    
    async def follow_user(self, username):
        """
        Seguir a un usuario específico.
        
        Args:
            username: Nombre de usuario a seguir
        
        Returns:
            dict: Resultado de la acción
        """
        # Verificar riesgo de la acción
        if not self._check_action_risk("follow"):
            return {
                "status": "error",
                "action": "follow",
                "username": username,
                "message": "Acción denegada por riesgo de detección"
            }
        
        try:
            # Navegar al perfil si no estamos ya en él
            current_url = self.page.url
            if f"/{username.lower()}" not in current_url.lower():
                success = await self.navigate_to_profile(username)
                if not success:
                    return {
                        "status": "error",
                        "action": "follow",
                        "username": username,
                        "message": "No se pudo navegar al perfil"
                    }
            
            # Esperar a que la página cargue completamente
            await self._human_delay(2, 4)
            
            # Buscar el botón de seguir
            follow_button = await self.page.locator(self.selectors["follow"]).first
            following_button = await self.page.locator(self.selectors["following"]).first
            
            # Verificar si ya estamos siguiendo al usuario
            if following_button:
                self.logger.info(f"Ya estamos siguiendo a @{username}")
                return {
                    "status": "info",
                    "action": "follow",
                    "username": username,
                    "message": "Ya siguiendo al usuario"
                }
            
            # Si no lo seguimos, hacer clic en el botón follow
            if follow_button:
                self.logger.info(f"Haciendo clic en el botón Follow para @{username}")
                
                # Simulación de comportamiento humano antes de hacer clic
                await self._human_delay(1, 3)
                
                # Hacer clic en el botón
                await follow_button.click()
                
                # Esperar después del clic para ver el resultado
                await self._human_delay(2, 4)
                
                # Verificar si el botón cambió a "Following"
                following_check = await self.page.locator(self.selectors["following"]).first
                
                if following_check:
                    result = {
                        "status": "success",
                        "action": "follow",
                        "username": username,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Registrar la acción exitosa
                    self._log_action("follow", result)
                    self.actions_performed += 1
                    
                    self.logger.info(f"Follow exitoso para @{username}")
                    return result
                else:
                    return {
                        "status": "error",
                        "action": "follow",
                        "username": username,
                        "message": "No se pudo confirmar el follow"
                    }
            else:
                return {
                    "status": "error",
                    "action": "follow",
                    "username": username,
                    "message": "Botón Follow no encontrado"
                }
            
        except Exception as e:
            self.logger.error(f"Error al seguir a @{username}: {e}")
            return {
                "status": "error",
                "action": "follow",
                "username": username,
                "message": str(e)
            }
    
    async def _random_scroll(self, min_scrolls=2, max_scrolls=5, scroll_range_min=300, scroll_range_max=800):
        """
        Realizar scroll aleatorio en la página actual.
        
        Args:
            min_scrolls: Número mínimo de scrolls
            max_scrolls: Número máximo de scrolls
            scroll_range_min: Distancia mínima de scroll
            scroll_range_max: Distancia máxima de scroll
        """
        num_scrolls = random.randint(min_scrolls, max_scrolls)
        self.logger.debug(f"Realizando {num_scrolls} scrolls aleatorios")
        
        for _ in range(num_scrolls):
            scroll_distance = random.randint(scroll_range_min, scroll_range_max)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            
            # Esperar un tiempo aleatorio entre scrolls
            await self._human_delay(1, 3)
    
    async def perform_like(self, post_count=1):
        """
        Dar like a X número de publicaciones en la página actual.
        
        Args:
            post_count: Número de publicaciones a las que dar like
        
        Returns:
            dict: Resultado de la acción con estadísticas
        """
        # Verificar riesgo de la acción
        if not self._check_action_risk("like"):
            return {
                "status": "error",
                "action": "like",
                "message": "Acción denegada por riesgo de detección"
            }
        
        try:
            self.logger.info(f"Buscando {post_count} publicaciones para dar like")
            
            # Realizar scroll para cargar más publicaciones
            await self._random_scroll()
            
            # Buscar todos los botones de like disponibles
            like_buttons = await self.page.locator(self.selectors["like"]).all()
            self.logger.info(f"Se encontraron {len(like_buttons)} botones de like")
            
            # Si no hay suficientes, hacer más scroll
            if len(like_buttons) < post_count:
                self.logger.debug("Haciendo más scroll para encontrar más publicaciones")
                await self._random_scroll(3, 6)
                like_buttons = await self.page.locator(self.selectors["like"]).all()
            
            # Inicializar contadores
            likes_given = 0
            already_liked = 0
            
            # Limitar el número de likes al mínimo entre el conteo solicitado y disponible
            target_count = min(post_count, len(like_buttons))
            
            # Elegir botones aleatorios si hay más de los necesarios
            if len(like_buttons) > target_count:
                indices = random.sample(range(len(like_buttons)), target_count)
                selected_buttons = [like_buttons[i] for i in indices]
            else:
                selected_buttons = like_buttons
            
            for button in selected_buttons:
                # Verificar si ya le dimos like (generalmente por la clase o atributo)
                try:
                    is_liked = await button.get_attribute("aria-pressed") == "true"
                    if is_liked:
                        already_liked += 1
                        continue
                except Exception:
                    # Si no podemos verificar, intentar de todos modos
                    pass
                
                # Simular comportamiento humano antes de hacer clic
                await self._human_delay(1.5, 4)
                
                # Dar like
                await button.click()
                
                # Esperar un poco después del like
                await self._human_delay(0.5, 2)
                
                # Verificar si el like fue exitoso
                try:
                    if await button.get_attribute("aria-pressed") == "true":
                        likes_given += 1
                        self.logger.debug(f"Like exitoso #{likes_given}")
                        
                        # Registrar la acción
                        result = {
                            "status": "success",
                            "action": "like",
                            "post_index": likes_given,
                            "timestamp": datetime.now().isoformat()
                        }
                        self._log_action("like", result)
                        self.actions_performed += 1
                    else:
                        self.logger.debug("Like posiblemente fallido")
                except Exception as e:
                    self.logger.debug(f"Error al verificar resultado del like: {e}")
                
                # Si ya hemos dado suficientes likes, parar
                if likes_given >= post_count:
                    break
            
            # Resultado final
            return {
                "status": "success",
                "action": "like",
                "statistics": {
                    "requested": post_count,
                    "available": len(like_buttons),
                    "liked": likes_given,
                    "already_liked": already_liked
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error al dar likes: {e}")
            return {
                "status": "error",
                "action": "like",
                "message": str(e)
            }
    
    async def comment_on_post(self, index=0, comment_text=""):
        """
        Comentar en una publicación específica.
        
        Args:
            index: Índice de la publicación (0 para la primera visible)
            comment_text: Texto del comentario
        
        Returns:
            dict: Resultado de la acción
        """
        # Verificar riesgo de la acción
        if not self._check_action_risk("comment"):
            return {
                "status": "error",
                "action": "comment",
                "message": "Acción denegada por riesgo de detección"
            }
        
        # Verificar que el comentario no esté vacío
        if not comment_text:
            return {
                "status": "error",
                "action": "comment",
                "message": "El texto del comentario no puede estar vacío"
            }
        
        try:
            self.logger.info(f"Intentando comentar en la publicación #{index}")
            
            # Asegurarse de que hay publicaciones cargadas
            tweets = await self.page.locator(self.selectors["tweet_articles"]).all()
            
            if not tweets or len(tweets) <= index:
                # Hacer scroll para cargar más
                await self._random_scroll(3, 5)
                tweets = await self.page.locator(self.selectors["tweet_articles"]).all()
            
            if not tweets or len(tweets) <= index:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": f"No se encontró la publicación #{index}"
                }
            
            # Obtener la publicación objetivo
            target_tweet = tweets[index]
            
            # Buscar el botón de reply dentro de esta publicación
            reply_button = await target_tweet.locator(self.selectors["reply"]).first
            
            if not reply_button:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Botón de respuesta no encontrado"
                }
            
            # Hacer clic en el botón de respuesta
            self.logger.debug("Haciendo clic en el botón de respuesta")
            await self._human_delay(1, 3)
            await reply_button.click()
            
            # Esperar a que aparezca el campo de comentario
            await self._human_delay(2, 4)
            
            # Buscar el campo de texto del comentario
            comment_field = await self.page.locator(self.selectors["comment_field"]).first
            
            if not comment_field:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Campo de comentario no encontrado"
                }
            
            # Escribir el comentario con simulación de escritura humana
            self.logger.debug(f"Escribiendo comentario: {comment_text}")
            await self._human_typing(comment_field, comment_text)
            
            # Pequeña pausa antes de enviar
            await self._human_delay(1, 3)
            
            # Buscar el botón de enviar comentario
            send_button = await self.page.locator(self.selectors["send_comment"]).first
            
            if not send_button:
                # Intentar cerrar el modal si no podemos comentar
                try:
                    close_button = await self.page.locator(self.selectors["close_modal"]).first
                    if close_button:
                        await close_button.click()
                except Exception:
                    pass
                
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Botón de enviar comentario no encontrado"
                }
            
            # Comprobar si el botón está deshabilitado
            is_disabled = await send_button.get_attribute("disabled") == "true"
            if is_disabled:
                # Intentar cerrar el modal
                try:
                    close_button = await self.page.locator(self.selectors["close_modal"]).first
                    if close_button:
                        await close_button.click()
                except Exception:
                    pass
                
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Botón de enviar comentario deshabilitado"
                }
            
            # Enviar el comentario
            await send_button.click()
            
            # Esperar a que se procese el comentario
            await self._human_delay(3, 6)
            
            # Registrar la acción
            result = {
                "status": "success",
                "action": "comment",
                "post_index": index,
                "comment_text": comment_text,
                "timestamp": datetime.now().isoformat()
            }
            
            self._log_action("comment", result)
            self.actions_performed += 1
            
            self.logger.info("Comentario enviado exitosamente")
            return result
            
        except Exception as e:
            self.logger.error(f"Error al comentar: {e}")
            
            # Intentar cerrar el modal si hubo error
            try:
                close_button = await self.page.locator(self.selectors["close_modal"]).first
                if close_button:
                    await close_button.click()
            except Exception:
                pass
            
            return {
                "status": "error",
                "action": "comment",
                "message": str(e)
            }
    
    async def interact_with_profile(self, username, actions=None):
        """
        Realizar múltiples interacciones con un perfil específico.
        
        Args:
            username: Nombre de usuario con el que interactuar
            actions: Diccionario con acciones a realizar y sus parámetros
                    Ejemplo: {
                        "follow": True,
                        "like": 2,
                        "comment": "Gran contenido!"
                    }
        
        Returns:
            dict: Resultado de las interacciones
        """
        if actions is None:
            actions = {"follow": True}
        
        results = {
            "profile": username,
            "actions": []
        }
        
        try:
            # Navegar al perfil
            success = await self.navigate_to_profile(username)
            if not success:
                return {
                    "status": "error",
                    "message": f"No se pudo navegar al perfil de @{username}"
                }
            
            # Esperar a que la página cargue completamente
            await self._human_delay(2, 4)
            
            # Follow si está especificado
            if "follow" in actions and actions["follow"] is True:
                result = await self.follow_user(username)
                if result:
                    results["actions"].append(result)
            
            # Realizar scroll para ver publicaciones
            await self._random_scroll(2, 4)
            
            # Dar likes si está especificado
            if "like" in actions and actions["like"] > 0:
                like_result = await self.perform_like(actions["like"])
                results["actions"].append(like_result)
            
            # Comentar si está especificado
            if "comment" in actions and actions["comment"]:
                comment_result = await self.comment_on_post(0, actions["comment"])
                results["actions"].append(comment_result)
            
            # Establecer estado general
            results["status"] = "success"
            return results
            
        except Exception as e:
            self.logger.error(f"Error en interacción con @{username}: {e}")
            return {
                "status": "error",
                "profile": username,
                "message": str(e)
            }
    
    async def batch_interact(self, profiles, action_template=None):
        """
        Realizar interacciones con múltiples perfiles, siguiendo un patrón.
        
        Args:
            profiles: Lista de nombres de usuario
            action_template: Plantilla de acciones a realizar (opcional)
        
        Returns:
            dict: Resultados de todas las interacciones
        """
        if action_template is None:
            action_template = {"follow": True}
        
        # Establecer el template para comentarios variables si se solicitan
        comments = [
            "¡Excelente contenido!",
            "Muy interesante, gracias por compartir.",
            "Totalmente de acuerdo con tu punto de vista.",
            "Me encanta tu forma de explicarlo.",
            "Increíble análisis, ¡felicidades!",
            "Excelente labor, licenciado!!!",
            "Contenido valioso como siempre.",
            "Gracias por tu aporte a la comunidad."
        ]
        
        results = {
            "batch_status": "success",
            "profiles_processed": 0,
            "profiles_failed": 0,
            "details": []
        }
        
        for username in profiles:
            try:
                # Clonar el template para evitar modificar el original
                current_actions = action_template.copy()
                
                # Si hay comentario en el template pero es True, seleccionar uno aleatorio
                if "comment" in current_actions and current_actions["comment"] is True:
                    current_actions["comment"] = random.choice(comments)
                
                # Realizar la interacción
                self.logger.info(f"Iniciando interacción con @{username}")
                
                # Aplicar delay entre perfiles para comportamiento natural
                if results["profiles_processed"] > 0:
                    await self._human_delay(15, 45)  # Esperar entre 15-45 segundos entre perfiles
                
                # Ejecutar interacción
                result = await self.interact_with_profile(username, current_actions)
                
                # Registrar resultado
                results["details"].append(result)
                
                if result["status"] == "success":
                    results["profiles_processed"] += 1
                else:
                    results["profiles_failed"] += 1
                
                # Aplicar retraso variable para evitar patrones de tiempo
                cooldown = random.uniform(
                    self.config.get("action_types", {}).get("follow", {}).get("cool_down_time", 300) * 0.5,
                    self.config.get("action_types", {}).get("follow", {}).get("cool_down_time", 300) * 1.5
                )
                
                self.logger.info(f"Esperando {cooldown:.2f} segundos antes de la próxima interacción")
                await asyncio.sleep(cooldown)
                
            except Exception as e:
                self.logger.error(f"Error en interacción batch con @{username}: {e}")
                results["profiles_failed"] += 1
                results["details"].append({
                    "status": "error",
                    "profile": username,
                    "message": str(e)
                })
        
        # Actualizar estado general
        if results["profiles_failed"] > results["profiles_processed"]:
            results["batch_status"] = "partial_failure"
        elif results["profiles_failed"] == len(profiles):
            results["batch_status"] = "failure"
        
        return results