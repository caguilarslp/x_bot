import asyncio
import random
import logging
import json
import os
from datetime import datetime
from pathlib import Path


#logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("playwright").setLevel(logging.INFO)  # opcional, para reducir ruido


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
            "close_modal": {
                "primary": 'css=button[data-testid="app-bar-close"]',
                "fallback": [
                    'css=button[aria-label="Close"]',
                    'css=button:has-text("Close")'
                ]
            },
            "modal_dialog": {
                "primary": 'css=div[aria-labelledby="modal-header"]',
                "fallback": []
            },
            "progress_bar": {
                "primary": 'css=div[role="progressbar"] div[data-testid="progressBar-bar"]',
                "fallback": []
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
    
    async def _human_typing(self, element, text: str):
        """
        Simulate human typing into an input or contenteditable element,
        character by character, using element.type() with randomized delays.
        """
        # Clear any existing content
        await element.fill("")
        # Short pause before typing
        await self._human_delay(0.5, 1.5)

        # Type each character with a small random delay
        for char in text:
            # delay is in milliseconds for element.type()
            delay_ms = int(random.uniform(0.05, 0.15) * 1000)
            await element.type(char, delay=delay_ms)

            # Occasional thinking pause (5% chance)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.3, 1.5))
    
    
    # async def _human_typing(self, element, text):
    #     """
    #     Simular escritura humana con variaciones en la velocidad.
        
    #     Args:
    #         element: Elemento DOM donde escribir
    #         text: Texto a escribir
    #     """
    #     # Limpiar el campo primero si es necesario
    #     await element.fill("")
    #     await self._human_delay(0.5, 1.5)
        
    #     # Velocidad base de escritura (caracteres por segundo)
    #     base_speed = random.uniform(0.05, 0.15)
        
    #     # Escribir caracter por caracter con variaciones
    #     for char in text:
    #         # Aplicar delay variable por caracter
    #         char_delay = base_speed * random.uniform(0.8, 1.2)
    #         await asyncio.sleep(char_delay)
    #         await element.press(char)
            
    #         # Pausas ocasionales para simular pensamiento
    #         if random.random() < 0.05:  # 5% de probabilidad
    #             thinking_pause = random.uniform(0.3, 1.5)
    #             await asyncio.sleep(thinking_pause)
    
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
        Search for an element using CSS selectors first (with fallbacks), logging each attempt.
        
        Args:
            selector_key: Key in self.selectors for the desired element.
            context: Playwright context (page or element) to search within.
            parent_context: Optional parent context if context is not provided.

        Returns:
            Locator for the found elements, or None if not found.
        """
        search_context = context or parent_context or self.page
        cfg = self.selectors.get(selector_key)
        if not cfg:
            self.logger.error(f"No selector config for: {selector_key}")
            return None

        timeout = self.config.get('timeouts', {}).get('element_visible_ms', 5000)
        # combine primary + fallbacks
        candidates = [cfg['primary']] + cfg.get('fallback', [])

        for sel in candidates:
            try:
                # sel should start with 'css=' or 'xpath='
                locator = search_context.locator(sel)
                count = await locator.count()
                self.logger.debug(f"Trying {selector_key} ⇒ {sel} (found {count})")
                if count > 0:
                    self.logger.debug(f"✅ Selector final para {selector_key}: {sel}")
                    await locator.first.wait_for(state="visible", timeout=timeout)
                    return locator
            except Exception as e:
                self.logger.debug(f"Selector failed for {selector_key} ⇒ {sel}: {e}")

        self.logger.error(f"Element not found for {selector_key}")
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
        Navigate to a user's profile page if not already there.
        Uses DOMContentLoaded for fast loads, with a fallback to 'load'
        on failure, and skips navigation when the URL already matches.
        """
        username = username.lstrip('@')
        profile_url = f"https://x.com/{username}"
        self.logger.info(f"Navigating to profile @{username}")

        # Skip navigation if we're already on the right page
        if profile_url in self.page.url:
            self.logger.info(f"Already on @{username} profile, skipping navigation")
            return True

        # Get our timeout (ms)
        nav_timeout = self.config.get('timeouts', {}).get('navigation_timeout_ms', 10000)

        # Try the lighter DOMContentLoaded event first
        try:
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=nav_timeout)
        except Exception as first_err:
            self.logger.warning(
                f"DOMContentLoaded navigation to @{username} failed ({first_err}), retrying with load"
            )
            try:
                # fallback to full 'load' event with a longer timeout
                await self.page.goto(profile_url, wait_until="load", timeout=nav_timeout * 2)
            except Exception as second_err:
                self.logger.error(f"Load navigation to @{username} also failed: {second_err}")
                return False

        # Short human-like pause
        await self._human_delay(3, 6)

        if username.lower() in self.page.url.lower():
            self.logger.info(f"Successfully on @{username} profile")
            return True
        else:
            self.logger.warning(f"Unexpected redirect to {self.page.url}")
            return False    
     
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
   
    async def follow_user(self, username: str) -> dict:
        """
        Follow a user from their profile page.

        1. Navigate if not already on their profile.
        2. Check if already following.
        3. Click the follow button and verify change.

        Returns:
            Result dict with status and message.
        """
        if not self._check_action_risk("follow"):
            return {"status": "error", "action": "follow", "username": username,
                    "message": "Action blocked due to detection risk."}

        # 1) Ensure profile page
        if f"/{username.lower()}" not in self.page.url.lower():
            if not await self.navigate_to_profile(username):
                return {"status": "error", "action": "follow", "username": username,
                        "message": "Failed to navigate to profile."}

        # Give extra time for slow proxies
        await self.page.wait_for_timeout(self.config.get('timeouts', {}).get('element_visible_ms', 5000))

        # 2) Check existing following state
        following_locator = await self._find_element("following")
        if following_locator and await following_locator.count() > 0:
            return {"status": "info", "action": "follow", "username": username,
                    "message": "Already following this user."}

        # 3) Locate and click follow
        follow_locator = await self._find_element("follow")
        if not follow_locator or await follow_locator.count() == 0:
            return {"status": "error", "action": "follow", "username": username,
                    "message": "Follow button not found."}

        # Ensure the button is visible before clicking
        visibility_timeout = self.config.get('timeouts', {}).get('element_visible_ms', 5000)
        await follow_locator.first.wait_for(state="visible", timeout=visibility_timeout)

        await self._human_delay(1, 3)
        await follow_locator.first.click()

        # Wait for UI update
        await self.page.wait_for_timeout(self.config.get('timeouts', {}).get('element_visible_ms', 5000))

        # 4) Verify follow succeeded
        confirm = await self._find_element("following")
        if confirm and await confirm.count() > 0:
            result = {"status": "success", "action": "follow", "username": username,
                      "timestamp": datetime.now().isoformat()}
            self._log_action("follow", result)
            self.actions_performed += 1
            return result

        return {"status": "error", "action": "follow", "username": username,
                "message": "Follow confirmation not detected."}


    # async def comment_on_post(self,
    #                           index: int = 0,
    #                           comment_text: str = "",
    #                           profile_url: str = None
    #                           ) -> dict:
    #     """
    #     Comment on a specific post from a user's profile.

    #     Steps:
    #     1. Locate articles on profile.
    #     2. Navigate to the selected post.
    #     3. Write and send the comment, waiting for the progress bar to hide.
    #     4. Return to profile page.

    #     Returns:
    #         Result dict with status and message.
    #     """
    #     profile_url = profile_url or self.page.url

    #     if not self._check_action_risk("comment"):
    #         return {"status": "error", "action": "comment", "message": "High detection risk."}
    #     if not comment_text:
    #         return {"status": "error", "action": "comment", "message": "Empty comment."}

    #     # 1) Load list of tweets
    #     tweets = await self._find_element("tweet_articles")
    #     if not tweets or await tweets.count() == 0:
    #         return {"status": "error", "action": "comment", "message": "No posts found."}

    #     # Ensure the first tweet is visible
    #     visibility_timeout = self.config.get('timeouts', {}).get('element_visible_ms', 5000)
    #     await tweets.first.wait_for(state="visible", timeout=visibility_timeout)

    #     total = await tweets.count()
    #     if index >= total:
    #         return {"status": "error", "action": "comment",
    #                 "message": f"Index ({index}) out of range ({total})."}

    #     # 2) Obtain post URL
    #     target = tweets.nth(index)
    #     #link = target.locator('xpath=.//a[contains(@href,"/status/")]').first
    #     link = target.locator('css=a[href*="/status/"]').first
    #     href = await link.get_attribute("href")
    #     tweet_url = href if href.startswith("http") else f"https://x.com{href}"

    #     # 3) Navigate and wait for full load
    #     nav_timeout = self.config.get('timeouts', {}).get('navigation_timeout_ms', 10000)
    #     await self.page.goto(tweet_url, wait_until="networkidle", timeout=nav_timeout)
    #     await self.page.wait_for_timeout(self.config.get('timeouts', {}).get('element_visible_ms', 5000))

    #     # 4) Write the comment
    #     field = await self._find_element("comment_field", context=self.page)
    #     if not field or await field.count() == 0:
    #         return {"status": "error", "action": "comment", "message": "Comment field not found."}
    #     await field.first.wait_for(state="visible", timeout=visibility_timeout)
    #     await self._human_typing(field.first, comment_text)

    #     # 5) Send and wait for progress
    #     send = await self._find_element("send_comment", context=self.page)
    #     if not send or await send.count() == 0:
    #         return {"status": "error", "action": "comment", "message": "Send button not found."}
    #     await send.first.wait_for(state="visible", timeout=visibility_timeout)
    #     await self._human_delay(1, 3)
    #     await send.first.click()

    #     # bar = self.page.locator(
    #     #     'xpath=//div[@role="progressbar"]//div[@data-testid="progressBar-bar"]'
    #     # )
    #     bar = self.page.locator('css=div[role="progressbar"] div[data-testid="progressBar-bar"]')
    #     await bar.wait_for(state="hidden", timeout=15000)

    #     # 6) Return to profile
    #     await self.page.goto(profile_url, wait_until="domcontentloaded")
    #     await self.page.wait_for_timeout(self.config.get('timeouts', {}).get('element_visible_ms', 5000))

    #     # 7) Log and return
    #     result = {
    #         "status": "success",
    #         "action": "comment",
    #         "post_index": index,
    #         "comment_text": comment_text,
    #         "tweet_url": tweet_url,
    #         "timestamp": datetime.now().isoformat()
    #     }
    #     self._log_action("comment", result)
    #     self.actions_performed += 1
    #     return result

    async def comment_on_post(self,
                              index: int = 0,
                              comment_text: str = "",
                              profile_url: str = None
                              ) -> dict:
        """
        Comment on a specific post from a user's profile.
        1. Ensure we have the target tweet URL.
        2. Skip navigation if already there.
        3. Use DOMContentLoaded + fallback 'load' instead of networkidle.
        4. Type and send the comment.
        5. Wait for progress bar to hide and pause.
        6. Return to profile.
        """
        profile_url = profile_url or self.page.url

        # Risk and input checks
        if not self._check_action_risk("comment"):
            return {"status": "error", "action": "comment", "message": "High detection risk."}
        if not comment_text:
            return {"status": "error", "action": "comment", "message": "Empty comment."}

        # 1) Gather tweets on profile
        tweets = await self._find_element("tweet_articles")
        if not tweets or await tweets.count() == 0:
            return {"status": "error", "action": "comment", "message": "No posts found."}
        await tweets.first.wait_for(
            state="visible",
            timeout=self.config.get('timeouts', {}).get('element_visible_ms', 5000)
        )

        total = await tweets.count()
        if index >= total:
            return {
                "status": "error",
                "action": "comment",
                "message": f"Index ({index}) out of range ({total})."
            }

        # 2) Build the tweet URL from the selected post
        target = tweets.nth(index)
        link = target.locator('css=a[href*="/status/"]').first
        href = await link.get_attribute("href")
        tweet_url = href if href.startswith("http") else f"https://x.com{href}"

        # 3) Navigate to tweet if not already there
        nav_timeout = self.config.get('timeouts', {}).get('navigation_timeout_ms', 10000)
        if tweet_url not in self.page.url:
            try:
                await self.page.goto(
                    tweet_url,
                    wait_until="domcontentloaded",
                    timeout=nav_timeout
                )
            except Exception as first_err:
                self.logger.warning(
                    f"DOMContentLoaded navigation to tweet failed ({first_err}), retrying with load"
                )
                await self.page.goto(
                    tweet_url,
                    wait_until="load",
                    timeout=nav_timeout * 2
                )
        # Brief pause for stability
        await self.page.wait_for_timeout(
            self.config.get('timeouts', {}).get('element_visible_ms', 5000)
        )

        # 4) Type and send the comment
        field = await self._find_element("comment_field")
        if not field or await field.count() == 0:
            return {"status": "error", "action": "comment", "message": "Comment field not found."}
        await field.first.wait_for(state="visible", timeout=nav_timeout)
        await self._human_typing(field.first, comment_text)

        send = await self._find_element("send_comment")
        if not send or await send.count() == 0:
            return {"status": "error", "action": "comment", "message": "Send button not found."}
        await send.first.wait_for(state="visible", timeout=nav_timeout)
        await self._human_delay(1, 3)
        await send.first.click()

        # 5) Wait for the progress bar to disappear
        bar = self.page.locator(
            'css=div[role="progressbar"] div[data-testid="progressBar-bar"]'
        )
        await bar.wait_for(state="hidden", timeout=15000)

        # 5.1) Pause so the posted comment has time to render
        await self._human_delay(2, 5)

        # 6) Return to profile
        await self.page.goto(profile_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(
            self.config.get('timeouts', {}).get('element_visible_ms', 5000)
        )

        # 7) Log and report
        result = {
            "status": "success",
            "action": "comment",
            "post_index": index,
            "comment_text": comment_text,
            "tweet_url": tweet_url,
            "timestamp": datetime.now().isoformat()
        }
        self._log_action("comment", result)
        self.actions_performed += 1
        return result

 
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