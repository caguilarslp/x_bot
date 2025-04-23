#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import logging
import json
import random
from pathlib import Path

class ProfileActions:
    """
    Class to manage profile editing actions on X.com
    using Playwright with human-like interactions.
    """

    def __init__(self, page, recover_user, config_path='app/config/profile_config.json'):
        """
        Initialize ProfileActions with the Playwright page and the user handle.

        Args:
            page: Playwright Page object with an active session.
            recover_user: The X.com handle (username) to update.
            config_path: Path to the JSON configuration file.
        """
        self.page = page
        self.recover_user = recover_user  # store the handle for direct navigation
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Selectores XPath para edición de perfil
        self.selectors = {
            # Navigate to the profile
            "profile_link": "//a[@data-testid='AppTabBar_Profile_Link']",
            
            # Button to open the single-modal editor
            "edit_profile_button": [
                "//span[contains(text(), 'Edit profile')]",   # lowercase p
                "//span[contains(text(), 'Edit Profile')]"    # uppercase P
            ],
            
            # Fields inside the single-modal editor
            "name_input": "//input[@name='displayName']",
            "bio_textarea": "//textarea[@name='description']",
            "location_input": "//input[@name='location']",
            "profile_picture_input": "//input[@type='file' and contains(@accept, 'image/')]",
            "save_button": "//button[@data-testid='Profile_Save_Button']",
            
            # Buttons to open the modal (single or step-by-step)
            "setup_profile_button": [
                "//span[contains(text(), 'Set up profile')]",   # lowercase p
                "//span[contains(text(), 'Set up Profile')]",   # uppercase P
                "//span[contains(text(), 'SET UP PROFILE')]",   # all caps
                "//span[contains(text(), 'Edit profile')]",     # fallback to single edit
                "//span[contains(text(), 'Edit Profile')]"      # fallback uppercase P
            ],
            
            # Step-by-step: upload avatar
            "photo_upload_input": "//input[@data-testid='fileInput' and @type='file']",
            "photo_skip_button": "//button[@data-testid='ocfSelectAvatarSkipForNowButton']",
            "photo_next_button": "//button[@data-testid='ocfSelectAvatarNextButton']",
            
            # Step-by-step: bio entry
            "bio_step_textarea": "//textarea[@data-testid='ocfEnterTextTextInput' and @name='text']",
            "bio_skip_button": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "bio_next_button": "//button[@data-testid='ocfEnterTextNextButton']",
            
            # Step-by-step: location entry
            "location_step_input": "//input[@data-testid='ocfEnterTextTextInput' and @name='text']",
            "location_skip_button": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "location_next_button": "//button[@data-testid='ocfEnterTextNextButton']",
            
            # Final call-to-action save
            "final_save_button": "//button[@data-testid='OCF_CallToAction_Button']",
            "close_button": "//button[@data-testid='app-bar-close']"
        }
    
    def _load_config(self, config_path):
        """
        Cargar configuración de acciones de perfil desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
        
        Returns:
            dict: Configuración de acciones de perfil
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            self.logger.warning(f"Archivo de configuración no encontrado: {config_path}")
            return self._create_default_config()
        except json.JSONDecodeError:
            self.logger.error(f"Error de formato en {config_path}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """
        Crear configuración por defecto para acciones de perfil.
        
        Returns:
            dict: Configuración por defecto
        """
        return {
            "edit_delay": {
                "min": 1.5,  # segundos
                "max": 4.0   # segundos
            },
            "typing_speed": {
                "min": 0.05,  # segundos por caracter
                "max": 0.15   # segundos por caracter
            },
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 2  # segundos
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
            min_delay = self.config['edit_delay']['min']
        if max_delay is None:
            max_delay = self.config['edit_delay']['max']
        
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def _human_typing(self, element, text):
        """
        Simular escritura humana con variaciones en la velocidad de escritura.
        
        Args:
            element: Elemento del DOM donde escribir
            text: Texto a escribir
        """
        # Limpiar el campo primero
        await element.fill("")
        await self._human_delay(0.5, 1.0)
        
        # Escribir caracter por caracter con variaciones en la velocidad
        for char in text:
            await element.press(char)
            
            # Velocidad variable por caracter
            char_delay = random.uniform(
                self.config['typing_speed']['min'],
                self.config['typing_speed']['max']
            )
            await asyncio.sleep(char_delay)
            
            # Pausas ocasionales para simular pensamiento
            if random.random() < 0.05:  # 5% de probabilidad
                await self._human_delay(0.2, 0.8)
    
    async def _wait_for_selector_with_retry(self, selector, timeout=10000, visible=True):
        """
        Esperar por un selector con reintentos en caso de error.
        
        Args:
            selector: Selector XPath a esperar
            timeout: Tiempo máximo de espera en ms
            visible: Si el elemento debe ser visible
        
        Returns:
            El elemento encontrado o None si no se encuentra
        """
        # Verificar que la página sigue siendo válida
        try:
            if self.page.is_closed():
                self.logger.error("La página ha sido cerrada")
                return None
        except Exception:
            self.logger.error("Error al verificar si la página está cerrada")
            return None
            
        max_retries = self.config["error_handling"]["max_retries"]
        retry_delay = self.config["error_handling"]["retry_delay"]
        
        for attempt in range(max_retries):
            try:
                if isinstance(selector, list):
                    # Intentar múltiples selectores alternativos
                    for sel in selector:
                        try:
                            element = await self.page.wait_for_selector(sel, timeout=timeout, state="visible" if visible else "attached")
                            if element:
                                return element
                        except:
                            continue
                    # Si llegamos aquí, ningún selector funcionó
                    raise Exception(f"Ninguno de los selectores alternativos encontrados: {selector}")
                else:
                    # Selector único
                    return await self.page.wait_for_selector(selector, timeout=timeout, state="visible" if visible else "attached")
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Intento {attempt+1} fallido para selector {selector}: {e}. Reintentando...")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"Error al esperar por selector {selector}: {e}")
                    return None
        
        return None
    
    async def _load_profile_data(self, recover_user):
        """
        Cargar datos del perfil desde archivos de configuración.
        
        Args:
            recover_user: Nombre de usuario de recuperación
        
        Returns:
            dict: Datos del perfil a actualizar
        """
        account_path = os.path.join("assets", recover_user)
        profile_path = os.path.join(account_path, "profile.json")
        
        if not os.path.exists(profile_path):
            self.logger.warning(f"Archivo de perfil no encontrado: {profile_path}")
            return {}
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            return profile_data
        except Exception as e:
            self.logger.error(f"Error al cargar datos del perfil: {e}")
            return {}
    


    async def navigate_to_profile(self):
        """
        Navigate directly to the user's profile URL.
        """
        try:
            # Build profile URL from the handle
            profile_url = f"https://x.com/{self.recover_user.lower()}"
            self.logger.info(f"Navigating directly to profile: {profile_url}")
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)  # wait for profile to load
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to profile {self.recover_user}: {e}")
            return False


    async def edit_profile_single_modal(self, recover_user):
        """
        Edit profile using the single-modal workflow.
        Tries both 'Edit profile' and 'Set up Profile'.
        """
        # 1. Sanity check: page must be open
        try:
            if self.page.is_closed():
                self.logger.error("The page has been closed")
                return {"status": "error", "message": "Page closed"}
        except Exception as e:
            self.logger.error(f"Error checking page state: {e}")
            return {"status": "error", "message": str(e)}

        # 2. Navigate to the user's profile (now direct URL)
        self.logger.info("Navigating to profile for single-modal edit")
        if not await self.navigate_to_profile():
            return {"status": "error", "message": "Failed to navigate to profile"}

        # 3. Open the edit modal (covers both button variants)
        self.logger.info("Attempting to open profile edit modal")
        edit_button = await self._wait_for_selector_with_retry(
            self.selectors["setup_profile_button"],  # ["//span[contains(text(),'Set up Profile')]", "//span[contains(text(),'Edit profile')]"]
            timeout=10000
        )
        if not edit_button:
            return {"status": "error", "message": "Edit profile button not found"}

        await edit_button.click()
        await self._human_delay()

        # 4. Load profile data from assets/<recover_user>/profile.json
        profile_data = await self._load_profile_data(recover_user)
        if not profile_data:
            return {"status": "error", "message": "Profile data not found"}

        fields_updated = {}

        # 5. Update fields as before...
        if "name" in profile_data:
            self.logger.info("Updating display name")
            name_input = await self._wait_for_selector_with_retry(self.selectors["name_input"])
            if name_input:
                await self._human_typing(name_input, profile_data["name"])
                fields_updated["name"] = True

        if "bio" in profile_data:
            self.logger.info("Updating bio")
            bio_input = await self._wait_for_selector_with_retry(self.selectors["bio_textarea"])
            if bio_input:
                await self._human_typing(bio_input, profile_data["bio"])
                fields_updated["bio"] = True

        if "location" in profile_data:
            self.logger.info("Updating location")
            loc_input = await self._wait_for_selector_with_retry(self.selectors["location_input"])
            if loc_input:
                await self._human_typing(loc_input, profile_data["location"])
                fields_updated["location"] = True

        if "profile_picture" in profile_data:
            self.logger.info("Updating profile picture")
            img_path = os.path.join("assets", recover_user, profile_data["profile_picture"])
            if os.path.exists(img_path):
                pic_input = await self._wait_for_selector_with_retry(self.selectors["profile_picture_input"])
                if pic_input:
                    await pic_input.set_input_files(img_path)
                    await self._human_delay(2.0, 5.0)
                    fields_updated["profile_picture"] = True
            else:
                self.logger.warning(f"Profile picture not found at {img_path}")

        # 6. Save changes
        self.logger.info("Saving profile changes")
        save_btn = await self._wait_for_selector_with_retry(self.selectors["save_button"])
        if not save_btn:
            return {"status": "error", "message": "Save button not found"}

        await self._human_delay()
        await save_btn.click()
        await self._human_delay(3.0, 6.0)

        return {
            "status": "success",
            "message": "Profile updated",
            "fields_updated": fields_updated
        }
    
    
    async def edit_profile_step_by_step(self, recover_user):
        """
        Edit profile using the step-by-step setup workflow.
        """
        # 1. Ensure page is still open
        try:
            if self.page.is_closed():
                self.logger.error("The page has been closed")
                return {"status": "error", "message": "Page closed"}
        except Exception as e:
            self.logger.error(f"Error checking page state: {e}")
            return {"status": "error", "message": str(e)}

        # 2. Navigate directly to the profile
        self.logger.info("Navigating to profile for step-by-step edit")
        if not await self.navigate_to_profile():
            return {"status": "error", "message": "Failed to navigate to profile"}

        # 3. Open the setup/edit modal (handles both variants)
        self.logger.info("Opening setup/edit profile modal")
        setup_button = await self._wait_for_selector_with_retry(
            self.selectors["setup_profile_button"],
            timeout=10000
        )
        if not setup_button:
            return {"status": "error", "message": "Setup/Edit profile button not found"}

        await setup_button.click()
        await self._human_delay()

        # 4. Load profile configuration
        profile_data = await self._load_profile_data(recover_user)
        if not profile_data:
            return {"status": "error", "message": "Profile data not found"}

        # 5. Step 1: Upload or skip profile photo
        if "profile_picture" in profile_data:
            photo_header = await self._wait_for_selector_with_retry(
                "//h1[contains(text(), 'Pick a profile picture')]", timeout=5000
            )
            if photo_header:
                img_path = os.path.join("assets", recover_user, profile_data["profile_picture"])
                if os.path.exists(img_path):
                    upload_input = await self._wait_for_selector_with_retry(self.selectors["photo_upload_input"])
                    if upload_input:
                        self.logger.info("Uploading profile picture")
                        await upload_input.set_input_files(img_path)
                        await self._human_delay(2.0, 5.0)
                next_btn = await self._wait_for_selector_with_retry(self.selectors["photo_next_button"])
                if next_btn:
                    await next_btn.click()
                    await self._human_delay()

        # 6. Step 2: Enter bio or skip
        if "bio" in profile_data:
            bio_header = await self._wait_for_selector_with_retry(
                "//h1[contains(text(), 'Describe yourself')]", timeout=5000
            )
            if bio_header:
                bio_input = await self._wait_for_selector_with_retry(self.selectors["bio_step_textarea"])
                if bio_input:
                    self.logger.info("Entering bio")
                    await self._human_typing(bio_input, profile_data["bio"])
                next_btn = await self._wait_for_selector_with_retry(self.selectors["bio_next_button"])
                if next_btn:
                    await next_btn.click()
                    await self._human_delay()

        # 7. Step 3: Enter location or skip
        if "location" in profile_data:
            loc_header = await self._wait_for_selector_with_retry(
                "//h1[contains(text(), 'Where do you live?')]", timeout=5000
            )
            if loc_header:
                loc_input = await self._wait_for_selector_with_retry(self.selectors["location_step_input"])
                if loc_input:
                    self.logger.info("Entering location")
                    await self._human_typing(loc_input, profile_data["location"])
                next_btn = await self._wait_for_selector_with_retry(self.selectors["location_next_button"])
                if next_btn:
                    await next_btn.click()
                    await self._human_delay()

        # 8. Finalize by clicking the call-to-action button
        final_btn = await self._wait_for_selector_with_retry(self.selectors["final_save_button"], timeout=5000)
        if final_btn:
            self.logger.info("Saving final profile setup")
            await final_btn.click()
            await self._human_delay(3.0, 6.0)

        return {"status": "success", "message": "Profile configured step-by-step"}

    
    async def update_profile(self, recover_user):
        """
        Actualizar el perfil de una cuenta utilizando el método más adecuado.
        
        Args:
            recover_user: Nombre de usuario de recuperación (identificador de la carpeta en assets)
        
        Returns:
            dict: Resultado de la acción
        """
        # Verificar existencia de la carpeta de cuenta
        account_path = os.path.join("assets", recover_user)
        if not os.path.exists(account_path):
            return {
                "status": "error",
                "message": f"La carpeta de cuenta para el usuario {recover_user} no existe"
            }
        
        # Verificar que la página sigue siendo válida
        try:
            if self.page.is_closed():
                self.logger.error("La página ha sido cerrada")
                return {"status": "error", "message": "La página ha sido cerrada"}
        except Exception as e:
            self.logger.error(f"Error al verificar si la página está cerrada: {e}")
            return {"status": "error", "message": f"Error al verificar la página: {str(e)}"}
        
        # Intentar primero el método de modal único
        self.logger.info(f"Iniciando actualización de perfil para {recover_user} usando modal único")
        result = await self.edit_profile_single_modal(recover_user)
        
        # Si falla, intentar el método paso a paso
        if result["status"] == "error":
            self.logger.info("Método de modal único falló, intentando método paso a paso")
            result = await self.edit_profile_step_by_step(recover_user)
        
        return result

