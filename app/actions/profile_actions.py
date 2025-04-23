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
    Clase para gestionar acciones de edición de perfil en X.com
    utilizando los selectores XPath definidos.
    """
    
    def __init__(self, page, config_path='config/profile_config.json'):
        """
        Inicializar las acciones de perfil con la página de Playwright y configuración.
        
        Args:
            page: Página de Playwright con sesión activa
            config_path: Ruta al archivo de configuración de acciones de perfil
        """
        self.page = page
        self.logger = logging.getLogger(__name__)
        
        # Cargar configuración
        self.config = self._load_config(config_path)
        
        # Selectores XPath para edición de perfil
        self.selectors = {
            # Navegación al perfil
            "profile_link": "//a[@data-testid='AppTabBar_Profile_Link']",
            "edit_profile_button": "//span[contains(text(), 'Edit profile')]",
            
            # Campos del modal de edición de perfil
            "name_input": "//input[@name='displayName']",
            "bio_textarea": "//textarea[@name='description']",
            "location_input": "//input[@name='location']",
            "profile_picture_input": "//input[@type='file' and contains(@accept, 'image/')]",
            "save_button": "//button[@data-testid='Profile_Save_Button']",
            
            # Selectores para edición paso a paso
            "setup_profile_button": [
                "//span[contains(text(), 'Set up Profile')]",
                "//span[contains(text(), 'Edit profile')]"
            ],
            
            # Etapa 1: Foto de perfil
            "photo_upload_input": "//input[@data-testid='fileInput' and @type='file']",
            "photo_skip_button": "//button[@data-testid='ocfSelectAvatarSkipForNowButton']",
            "photo_next_button": "//button[@data-testid='ocfSelectAvatarNextButton']",
            
            # Etapa 3: Bio/Descripción
            "bio_step_textarea": "//textarea[@data-testid='ocfEnterTextTextInput' and @name='text']",
            "bio_skip_button": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "bio_next_button": "//button[@data-testid='ocfEnterTextNextButton']",
            
            # Etapa 4: Ubicación
            "location_step_input": "//input[@data-testid='ocfEnterTextTextInput' and @name='text']",
            "location_skip_button": "//button[@data-testid='ocfEnterTextSkipForNowButton']",
            "location_next_button": "//button[@data-testid='ocfEnterTextNextButton']",
            
            # Botones finales
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
        Navegar al perfil del usuario.
        
        Returns:
            bool: True si la navegación fue exitosa, False en caso contrario
        """
        try:
            # Hacer clic en el enlace de perfil
            profile_link = await self._wait_for_selector_with_retry(self.selectors["profile_link"])
            if not profile_link:
                return False
            
            await profile_link.click()
            await self._human_delay()
            
            return True
        except Exception as e:
            self.logger.error(f"Error al navegar al perfil: {e}")
            return False
    
    async def edit_profile_single_modal(self, recover_user):
        """
        Editar perfil utilizando el modal único de edición de perfil.
        
        Args:
            recover_user: Nombre de usuario de recuperación
        
        Returns:
            dict: Resultado de la acción
        """
        try:
            # Navegar al perfil
            if not await self.navigate_to_profile():
                return {"status": "error", "message": "Error al navegar al perfil"}
            
            # Hacer clic en el botón de editar perfil
            edit_button = await self._wait_for_selector_with_retry(self.selectors["edit_profile_button"])
            if not edit_button:
                return {"status": "error", "message": "Botón de editar perfil no encontrado"}
            
            await edit_button.click()
            await self._human_delay()
            
            # Cargar datos del perfil
            profile_data = await self._load_profile_data(recover_user)
            if not profile_data:
                return {"status": "error", "message": "No se pudieron cargar los datos del perfil"}
            
            # Actualizar campos del perfil
            fields_updated = {}
            
            # Nombre
            if "name" in profile_data:
                name_input = await self._wait_for_selector_with_retry(self.selectors["name_input"])
                if name_input:
                    await self._human_typing(name_input, profile_data["name"])
                    fields_updated["name"] = True
            
            # Bio
            if "bio" in profile_data:
                bio_textarea = await self._wait_for_selector_with_retry(self.selectors["bio_textarea"])
                if bio_textarea:
                    await self._human_typing(bio_textarea, profile_data["bio"])
                    fields_updated["bio"] = True
            
            # Ubicación
            if "location" in profile_data:
                location_input = await self._wait_for_selector_with_retry(self.selectors["location_input"])
                if location_input:
                    await self._human_typing(location_input, profile_data["location"])
                    fields_updated["location"] = True
            
            # Foto de perfil
            if "profile_picture" in profile_data:
                # Construir ruta completa a la imagen
                img_path = os.path.join("assets", recover_user, profile_data["profile_picture"])
                if os.path.exists(img_path):
                    # Esperar por el input de subida de archivo
                    profile_pic_input = await self._wait_for_selector_with_retry(self.selectors["profile_picture_input"])
                    if profile_pic_input:
                        # Subir imagen
                        await profile_pic_input.set_input_files(img_path)
                        await self._human_delay(2.0, 5.0)  # Esperar a que se cargue la imagen
                        fields_updated["profile_picture"] = True
            
            # Guardar cambios
            save_button = await self._wait_for_selector_with_retry(self.selectors["save_button"])
            if not save_button:
                return {"status": "error", "message": "Botón de guardar no encontrado"}
            
            await self._human_delay()
            await save_button.click()
            
            # Esperar a que se guarden los cambios
            await self._human_delay(3.0, 6.0)
            
            return {
                "status": "success",
                "message": "Perfil actualizado",
                "fields_updated": fields_updated
            }
            
        except Exception as e:
            self.logger.error(f"Error al editar perfil: {e}")
            return {
                "status": "error",
                "message": f"Error al editar perfil: {str(e)}"
            }
    
    async def edit_profile_step_by_step(self, recover_user):
        """
        Editar perfil utilizando el flujo paso a paso de configuración de perfil.
        
        Args:
            recover_user: Nombre de usuario de recuperación
        
        Returns:
            dict: Resultado de la acción
        """
        try:
            # Navegar al perfil
            if not await self.navigate_to_profile():
                return {"status": "error", "message": "Error al navegar al perfil"}
            
            # Hacer clic en el botón de configurar/editar perfil
            setup_button = await self._wait_for_selector_with_retry(self.selectors["setup_profile_button"])
            if not setup_button:
                return {"status": "error", "message": "Botón de configurar/editar perfil no encontrado"}
            
            await setup_button.click()
            await self._human_delay()
            
            # Cargar datos del perfil
            profile_data = await self._load_profile_data(recover_user)
            if not profile_data:
                return {"status": "error", "message": "No se pudieron cargar los datos del perfil"}
            
            # Etapa 1: Foto de perfil
            if "profile_picture" in profile_data:
                # Comprobar si estamos en la etapa de foto de perfil
                profile_pic_header = await self._wait_for_selector_with_retry("//h1[contains(text(), 'Pick a profile picture')]", timeout=5000)
                
                if profile_pic_header:
                    img_path = os.path.join("assets", recover_user, profile_data["profile_picture"])
                    if os.path.exists(img_path):
                        # Esperar por el input de subida de archivo
                        photo_upload = await self._wait_for_selector_with_retry(self.selectors["photo_upload_input"])
                        if photo_upload:
                            # Subir imagen
                            await photo_upload.set_input_files(img_path)
                            await self._human_delay(2.0, 5.0)  # Esperar a que se cargue la imagen
                    
                    # Clic en botón siguiente
                    next_button = await self._wait_for_selector_with_retry(self.selectors["photo_next_button"])
                    if next_button:
                        await next_button.click()
                        await self._human_delay()
            
            # Etapa 3: Bio
            if "bio" in profile_data:
                # Comprobar si estamos en la etapa de bio
                bio_header = await self._wait_for_selector_with_retry("//h1[contains(text(), 'Describe yourself')]", timeout=5000)
                
                if bio_header:
                    bio_textarea = await self._wait_for_selector_with_retry(self.selectors["bio_step_textarea"])
                    if bio_textarea:
                        await self._human_typing(bio_textarea, profile_data["bio"])
                    
                    # Clic en botón siguiente
                    next_button = await self._wait_for_selector_with_retry(self.selectors["bio_next_button"])
                    if next_button:
                        await next_button.click()
                        await self._human_delay()
            
            # Etapa 4: Ubicación
            if "location" in profile_data:
                # Comprobar si estamos en la etapa de ubicación
                location_header = await self._wait_for_selector_with_retry("//h1[contains(text(), 'Where do you live?')]", timeout=5000)
                
                if location_header:
                    location_input = await self._wait_for_selector_with_retry(self.selectors["location_step_input"])
                    if location_input:
                        await self._human_typing(location_input, profile_data["location"])
                    
                    # Clic en botón siguiente (que puede ser el botón final)
                    next_button = await self._wait_for_selector_with_retry(self.selectors["location_next_button"], timeout=3000)
                    if next_button:
                        await next_button.click()
                        await self._human_delay()
            
            # Botón de guardar final
            final_save = await self._wait_for_selector_with_retry(self.selectors["final_save_button"], timeout=5000)
            if final_save:
                await final_save.click()
                await self._human_delay(3.0, 6.0)
            
            return {
                "status": "success",
                "message": "Perfil configurado paso a paso"
            }
            
        except Exception as e:
            self.logger.error(f"Error al configurar perfil paso a paso: {e}")
            return {
                "status": "error",
                "message": f"Error al configurar perfil paso a paso: {str(e)}"
            }
    
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
        
        # Intentar primero el método de modal único
        result = await self.edit_profile_single_modal(recover_user)
        
        # Si falla, intentar el método paso a paso
        if result["status"] == "error":
            self.logger.info("Método de modal único falló, intentando método paso a paso")
            result = await self.edit_profile_step_by_step(recover_user)
        
        return result