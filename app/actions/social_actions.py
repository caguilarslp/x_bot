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
        
        # Estructura de selectores más robusta
        self.selectors = {
            "follow": {
                "primary": '//button[@data-testid="1589450359-follow"]',
                "fallback": [
                    '//button[contains(@aria-label, "Follow")]',
                    '//button[contains(text(), "Follow")]',
                    '//div[contains(@class, "follow-button")]//button',
                    '//a[contains(@href, "/follow")]'
                ]
            },
            "following": {
                "primary": '//button[@data-testid="1626214836-unfollow"]',
                "fallback": [
                    '//button[contains(@aria-label, "Following")]',
                    '//button[contains(text(), "Following")]',
                    '//button[contains(@class, "following-btn")]'
                ]
            },
            "like": {
                "primary": '//button[@data-testid="like"]',
                "fallback": [
                    '//button[@aria-label="Like"]',
                    '//div[@role="button"][contains(@aria-label, "Like")]',
                    '//span[contains(@aria-label, "Like")]//parent::button'
                ]
            },
            "tweet_articles": {
                "primary": '//article[@data-testid="tweet"]',
                "fallback": [
                    '//div[@role="article"]',
                    '//div[contains(@class, "tweet")]',
                    '//div[contains(@class, "tweet-container")]'
                ]
            },
            "reply": {
                "primary": '//button[@data-testid="reply"]',
                "fallback": [
                    '//button[@aria-label="Reply"]',
                    '//div[@role="button"][contains(@aria-label, "Reply")]'
                ]
            },
            "comment_field": {
                "primary": '//div[@data-testid="tweetTextarea_0"]',
                "fallback": [
                    '//div[@role="textbox"][contains(@aria-label, "Tweet text")]',
                    '//textarea[@name="tweet"]',
                    '//div[contains(@aria-label, "Add a comment")]'
                ]
            },
            "send_comment": {
                "primary": '//button[@data-testid="tweetButton"]',
                "fallback": [
                    '//button[contains(text(), "Tweet")]',
                    '//button[@aria-label="Tweet"]',
                    '//button[contains(@class, "tweet-btn")]'
                ]
            },
            "close_modal": {
                "primary": '//button[@data-testid="app-bar-close"]',
                "fallback": [
                    '//button[@aria-label="Close"]',
                    '//button[contains(@class, "close-modal")]'
                ]
            }
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
            
            
            
    async def _find_element(self, selector_key, context=None, parent_context=None):
        """
        Buscar un elemento con estrategia de selectores múltiples.
        
        Args:
            selector_key: Clave del selector en self.selectors
            context: Contexto de búsqueda (página o elemento padre)
            parent_context: Contexto padre opcional
        
        Returns:
            Localizador del elemento o None
        """
        # Definir el contexto de búsqueda
        search_context = context if context is not None else (parent_context if parent_context is not None else self.page)
        
        # Obtener la configuración de selectores para esta clave
        selector_config = self.selectors.get(selector_key, None)
        if not selector_config:
            self.logger.error(f"No se encontró configuración de selector para: {selector_key}")
            return None
        
        # Intentar selector principal
        try:
            primary_selector = selector_config.get('primary')
            if primary_selector:
                try:
                    # Intentar con selector primario en XPath
                    elements = search_context.locator(f'xpath={primary_selector}')
                    if await elements.count() > 0:
                        self.logger.debug(f"Elemento encontrado con selector principal para {selector_key}")
                        return elements
                except Exception as e:
                    self.logger.warning(f"Error con selector principal de {selector_key}: {e}")
        except Exception:
            pass
        
        # Intentar selectores de respaldo
        try:
            fallback_selectors = selector_config.get('fallback', [])
            for fallback_selector in fallback_selectors:
                elements = search_context.locator(f'xpath={fallback_selector}')
                if await elements.count() > 0:
                    return elements

        except Exception as e:
                    self.logger.debug(f"Selector de respaldo fallido: {fallback_selector} - {e}")
        except Exception:
            pass
        
        # Si no se encuentra ningún selector
        self.logger.error(f"No se encontró elemento para {selector_key}")
        return None
    
    
    
    async def _capture_page_html(self, filename=None):
        """
        Capturar el HTML completo de la página actual.
        
        Args:
            filename: Nombre del archivo para guardar. Si no se proporciona, 
                    se generará automáticamente con marca de tiempo.
        
        Returns:
            Ruta del archivo HTML guardado
        """
        # Crear directorio para capturas si no existe
        captures_dir = Path('page_captures')
        captures_dir.mkdir(exist_ok=True)
        
        # Generar nombre de archivo si no se proporciona
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_capture_{timestamp}.html"
        
        # Ruta completa del archivo
        filepath = captures_dir / filename
        
        # Obtener contenido HTML
        html_content = await self.page.content()
        
        # Guardar HTML
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML capturado y guardado en: {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Error al capturar HTML: {e}")
            return None
    
    
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
            
            # Buscar botones de seguir y siguiendo
            follow_button = await self._find_element("follow")
            following_button = await self._find_element("following")
            
            # Verificar si ya estamos siguiendo al usuario
            if following_button and await following_button.count() > 0:
                self.logger.info(f"Ya estamos siguiendo a @{username}")
                return {
                    "status": "info",
                    "action": "follow",
                    "username": username,
                    "message": "Ya siguiendo al usuario"
                }
            
            # Si no lo seguimos, buscar el botón de follow
            if follow_button and await follow_button.count() > 0:
                self.logger.info(f"Haciendo clic en el botón Follow para @{username}")
                
                # Simulación de comportamiento humano antes de hacer clic
                await self._human_delay(1, 3)
                
                # Hacer clic en el botón
                await follow_button.first().click()
                
                # Esperar después del clic para ver el resultado
                await self._human_delay(2, 4)
                
                # Verificar si el botón cambió a "Following"
                following_check = await self._find_element("following")
                
                if following_check and await following_check.count() > 0:
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
   
   
    async def perform_like(self, post_count: int = 1):
        """
        Dar likes a las publicaciones en el perfil actual.

        Args:
            post_count: Número de likes a dar

        Returns:
            dict: Resultado con estadísticas de likes
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

            # Obtener todos los botones de like disponibles
            like_buttons = await self._find_element("like")
            if not like_buttons:
                return {
                    "status": "error",
                    "action": "like",
                    "message": "No se encontraron botones de like"
                }

            total_buttons = await like_buttons.count()
            self.logger.info(f"Se encontraron {total_buttons} botones de like")

            # Si no hay suficientes botones, scroll extra
            if total_buttons < post_count:
                self.logger.debug("Haciendo más scroll para cargar más publicaciones")
                await self._random_scroll(3, 6)
                like_buttons = await self._find_element("like")
                total_buttons = await like_buttons.count() if like_buttons else 0

            # Determinar cuántos likes podemos dar
            target_count = min(post_count, total_buttons)

            likes_given = 0
            already_liked = 0

            # Selección aleatoria de índices de botones si hay más de los necesarios
            if total_buttons > target_count:
                indices = random.sample(range(total_buttons), target_count)
            else:
                indices = list(range(target_count))

            # Iterar con enumerate para llevar el conteo de intentos
            for attempt, button_index in enumerate(indices, start=1):
                self.logger.info(f"Liking post {attempt}/{post_count} (button index {button_index})")
                button = like_buttons.nth(button_index)

                # Delay humano ligero antes de hacer clic
                await self._human_delay(0.5, 1)

                # Dar like
                await button.click()
                self.logger.info(f"Like #{attempt} successful")

                # Registrar inmediatamente el like
                likes_given += 1
                result = {
                    "status": "success",
                    "action": "like",
                    "post_index": likes_given,
                    "timestamp": datetime.now().isoformat()
                }
                self._log_action("like", result)
                self.actions_performed += 1

                # Si ya dimos todos los likes requeridos, salir del bucle
                if likes_given >= post_count:
                    break

            # Resultado final
            return {
                "status": "success",
                "action": "like",
                "statistics": {
                    "requested": post_count,
                    "available": total_buttons,
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
   
    # async def perform_like(self, post_count=1):
    #     # Verificar riesgo de la acción
    #     if not self._check_action_risk("like"):
    #         return {
    #             "status": "error",
    #             "action": "like",
    #             "message": "Acción denegada por riesgo de detección"
    #         }
        
    #     try:
    #         self.logger.info(f"Buscando {post_count} publicaciones para dar like")
            
    #         # Realizar scroll para cargar más publicaciones
    #         #await self._random_scroll()
            
    #         # Buscar todos los botones de like disponibles
    #         like_buttons = await self._find_element("like")
            
    #         if not like_buttons:
    #             return {
    #                 "status": "error",
    #                 "action": "like",
    #                 "message": "No se encontraron botones de like"
    #             }
            
    #         total_buttons = await like_buttons.count()
    #         self.logger.info(f"Se encontraron {total_buttons} botones de like")
            
    #         # Si no hay suficientes, hacer más scroll
    #         if total_buttons < post_count:
    #             self.logger.debug("Haciendo más scroll para encontrar más publicaciones")
    #             await self._random_scroll(3, 6)
    #             like_buttons = await self._find_element("like")
    #             total_buttons = await like_buttons.count() if like_buttons else 0
            
    #         # Inicializar contadores
    #         likes_given = 0
    #         already_liked = 0
            
    #         # Limitar el número de likes al mínimo entre el conteo solicitado y disponible
    #         target_count = min(post_count, total_buttons)
            
    #         # Elegir botones aleatorios si hay más de los necesarios
    #         if total_buttons > target_count:
    #             indices = random.sample(range(total_buttons), target_count)
    #         else:
    #             indices = list(range(target_count))
            
    #         for index in indices:
    #             self.logger.info(f"Liking post {likes_given+1}/{post_count} (button index {index})")
    #             button = like_buttons.nth(index)
                
    #             # Verificar si ya le dimos like 
    #             try:
    #                 is_liked = await button.get_attribute("aria-pressed") == "true"
    #                 if is_liked:
    #                     already_liked += 1
    #                     continue
    #             except Exception:
    #                 # Si no podemos verificar, intentar de todos modos
    #                 pass
                
    #             # Simular comportamiento humano antes de hacer clic
    #             await self._human_delay(1, 2.5)
                
    #             # Dar like
    #             await button.click()
    #             self.logger.info(f"Like #{likes_given+1} successful")
                
    #             # Esperar un poco después del like
    #             await self._human_delay(0.5, 1.5)
                
    #             # Verificar si el like fue exitoso
    #             try:
    #                 if await button.get_attribute("aria-pressed") == "true":
    #                     likes_given += 1
    #                     self.logger.debug(f"Like exitoso #{likes_given}")
                        
    #                     # Registrar la acción
    #                     result = {
    #                         "status": "success",
    #                         "action": "like",
    #                         "post_index": likes_given,
    #                         "timestamp": datetime.now().isoformat()
    #                     }
    #                     self._log_action("like", result)
    #                     self.actions_performed += 1
    #                 else:
    #                     self.logger.debug("Like posiblemente fallido")
    #             except Exception as e:
    #                 self.logger.debug(f"Error al verificar resultado del like: {e}")
                
    #             # Si ya hemos dado suficientes likes, parar
    #             if likes_given >= post_count:
    #                 break
            
    #         # Resultado final
    #         return {
    #             "status": "success",
    #             "action": "like",
    #             "statistics": {
    #                 "requested": post_count,
    #                 "available": total_buttons,
    #                 "liked": likes_given,
    #                 "already_liked": already_liked
    #             },
    #             "timestamp": datetime.now().isoformat()
    #         }
            
    #     except Exception as e:
    #         self.logger.error(f"Error al dar likes: {e}")
    #         return {
    #             "status": "error",
    #             "action": "like",
    #             "message": str(e)
    #         }   
  
  
    async def comment_on_post(self, index=0, comment_text=""):
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
            
            # Buscar publicaciones
            tweets = await self._find_element("tweet_articles")
            
            if not tweets:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "No se encontraron publicaciones"
                }
            
            total_tweets = await tweets.count()
            
            if total_tweets == 0 or total_tweets <= index:
                # Hacer scroll para cargar más
                await self._random_scroll(3, 5)
                tweets = await self._find_element("tweet_articles")
                total_tweets = await tweets.count() if tweets else 0
            
            if total_tweets == 0 or total_tweets <= index:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": f"No se encontró la publicación #{index}"
                }
            
            # Obtener la publicación objetivo
            target_tweet = tweets.nth(index)
            
            # Buscar el botón de reply dentro de esta publicación
            reply_buttons = await self._find_element("reply")
            
            if not reply_buttons:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Botón de respuesta no encontrado"
                }
            
            # Hacer clic en el botón de respuesta
            self.logger.debug("Haciendo clic en el botón de respuesta")
            await self._human_delay(1, 3)
            await reply_buttons.first().click()
            
            # Esperar a que aparezca el campo de comentario
            await self._human_delay(2, 4)
            
            # Buscar el campo de texto del comentario
            comment_fields = await self._find_element("comment_field")
            
            if not comment_fields:
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Campo de comentario no encontrado"
                }
            
            # Escribir el comentario con simulación de escritura humana
            comment_field = comment_fields.first()
            self.logger.debug(f"Escribiendo comentario: {comment_text}")
            await self._human_typing(comment_field, comment_text)
            
            # Pequeña pausa antes de enviar
            await self._human_delay(1, 3)
            
            # Buscar el botón de enviar comentario
            send_buttons = await self._find_element("send_comment")
            
            if not send_buttons:
                # Intentar cerrar el modal si no podemos comentar
                try:
                    close_buttons = await self._find_element("close_modal")
                    if close_buttons:
                        await close_buttons.first().click()
                except Exception:
                    pass
                
                return {
                    "status": "error",
                    "action": "comment",
                    "message": "Botón de enviar comentario no encontrado"
                }
            
            # Comprobar si el botón está deshabilitado
            send_button = send_buttons.first()
            is_disabled = await send_button.get_attribute("disabled") == "true"
            
            if is_disabled:
                # Intentar cerrar el modal
                try:
                    close_buttons = await self._find_element("close_modal")
                    if close_buttons:
                        await close_buttons.first().click()
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
                close_buttons = await self._find_element("close_modal")
                if close_buttons:
                    await close_buttons.first().click()
            except Exception:
                pass
            
            return {
                "status": "error",
                "action": "comment",
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