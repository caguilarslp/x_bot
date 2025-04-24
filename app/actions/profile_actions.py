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
        
        # Selectores XPath para configuración de perfil
        self.selectors = {
            "setup_start_button": "//span[text()='Set up profile']",
            "profile_picture_upload": "//input[@type='file' and @data-testid='fileInput']",
            "profile_picture_apply": "//button[@data-testid='applyButton']",
            "profile_picture_next": "//button[@data-testid='ocfSelectAvatarNextButton']",
            "profile_picture_skip": "//button[@data-testid='ocfSelectAvatarSkipForNowButton']",
            "header_picture_skip": "//button[@data-testid='ocfSelectBannerSkipForNowButton']",
            "bio_textarea": "//textarea[@data-testid='ocfEnterTextTextInput']",
            "bio_next": "//button[@data-testid='ocfEnterTextNextButton']",
            "bio_skip": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "location_input": "//input[@data-testid='ocfEnterTextTextInput']",
            "location_next": "//button[@data-testid='ocfEnterTextNextButton']",
            "location_skip": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "final_save": "//button[@data-testid='OCF_CallToAction_Button']"
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

    async def setup_profile(self, recover_user):
        """
        Configure profile using the step-by-step setup workflow for new accounts.
        """
        # 1. Ensure page is still open
        try:
            if self.page.is_closed():
                self.logger.error("The page has been closed")
                return {"status": "error", "message": "Page closed"}
        except Exception as e:
            self.logger.error(f"Error checking page state: {e}")
            return {"status": "error", "message": str(e)}

        # 2. Load profile configuration
        profile_data = await self._load_profile_data(recover_user)
        if not profile_data:
            return {"status": "error", "message": "Profile data not found"}

        # 3. Start profile setup
        setup_button = await self._wait_for_selector_with_retry(self.selectors["setup_start_button"])
        if not setup_button:
            return {"status": "error", "message": "Setup profile button not found"}
        
        await setup_button.click()
        await self._human_delay()

        # 4. Profile Picture Step
        if "profile_picture" in profile_data:
            img_path = os.path.join("assets", recover_user, profile_data["profile_picture"])
            if os.path.exists(img_path):
                upload_input = await self._wait_for_selector_with_retry(self.selectors["profile_picture_upload"])
                if upload_input:
                    self.logger.info("Uploading profile picture")
                    await upload_input.set_input_files(img_path)
                    await self._human_delay(2.0, 5.0)
                    
                    # Apply and go to next step
                    apply_btn = await self._wait_for_selector_with_retry(self.selectors["profile_picture_apply"])
                    if apply_btn:
                        await apply_btn.click()
                        await self._human_delay()
            
            # Next button (whether picture was uploaded or skipped)
            next_btn = await self._wait_for_selector_with_retry(self.selectors["profile_picture_next"])
            if next_btn:
                await next_btn.click()
                await self._human_delay()
            else:
                # Fallback skip if no next button found
                skip_btn = await self._wait_for_selector_with_retry(self.selectors["profile_picture_skip"])
                if skip_btn:
                    await skip_btn.click()
                    await self._human_delay()

        # 5. Header Picture Step (optional)
        skip_header_btn = await self._wait_for_selector_with_retry(self.selectors["header_picture_skip"])
        if skip_header_btn:
            await skip_header_btn.click()
            await self._human_delay()

        # 6. Bio Step
        if "bio" in profile_data:
            bio_input = await self._wait_for_selector_with_retry(self.selectors["bio_textarea"])
            if bio_input:
                self.logger.info("Entering bio")
                await self._human_typing(bio_input, profile_data["bio"])
            
            next_btn = await self._wait_for_selector_with_retry(self.selectors["bio_next"])
            if next_btn:
                await next_btn.click()
                await self._human_delay()
            else:
                skip_btn = await self._wait_for_selector_with_retry(self.selectors["bio_skip"])
                if skip_btn:
                    await skip_btn.click()
                    await self._human_delay()

        # 7. Location Step
        if "location" in profile_data:
            loc_input = await self._wait_for_selector_with_retry(self.selectors["location_input"])
            if loc_input:
                self.logger.info("Entering location")
                await self._human_typing(loc_input, profile_data["location"])
            
            next_btn = await self._wait_for_selector_with_retry(self.selectors["location_next"])
            if next_btn:
                await next_btn.click()
                await self._human_delay()
            else:
                skip_btn = await self._wait_for_selector_with_retry(self.selectors["location_skip"])
                if skip_btn:
                    await skip_btn.click()
                    await self._human_delay()

        # 8. Final Save/Confirmation
        final_btn = await self._wait_for_selector_with_retry(self.selectors["final_save"])
        if final_btn:
            self.logger.info("Completing profile setup")
            await final_btn.click()
            await self._human_delay(3.0, 6.0)

        return {
            "status": "success", 
            "message": "Profile setup completed",
            "fields_updated": list(profile_data.keys())
        }
    
    async def update_profile(self, recover_user):
        """
        Update the profile using the step-by-step setup workflow.
        """
        # Verify account folder exists
        account_path = os.path.join("assets", recover_user)
        if not os.path.exists(account_path):
            return {
                "status": "error",
                "message": f"Account folder for {recover_user} not found"
            }

        # Ensure page is open
        try:
            if self.page.is_closed():
                self.logger.error("The page has been closed")
                return {"status": "error", "message": "Page closed"}
        except Exception as e:
            self.logger.error(f"Error checking page state: {e}")
            return {"status": "error", "message": str(e)}

        # Always run the step-by-step setup
        self.logger.info(f"Starting profile setup for {recover_user}")
        return await self.setup_profile(recover_user)

