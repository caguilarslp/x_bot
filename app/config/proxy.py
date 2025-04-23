"""
Módulo para gestión de proxies en X.com Bot
"""

import random
import logging
import time
import json
import os
import requests
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy_operations.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rutas para archivos de configuración
CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)
PROXY_BLACKLIST_FILE = CONFIG_DIR / "proxy_blacklist.json"

# Tiempo predeterminado para mantener un proxy en blacklist (24 horas)
DEFAULT_BLACKLIST_DURATION = 24 * 60 * 60  # segundos

# Proxies organizados por país
PROXY_LISTS = {
    "mexico": [
        f"socks5h://user-spk2w2zeri-country-mx-city-mexico_city-session-{i}:r5GaBmB79hIfq3zhy~@gate.smartproxy.com:7000"
        for i in range(1, 51)
    ],
    #"united_states": [],  # Placeholder para proxies de EE.UU.
    #"spain": []  # Placeholder para proxies de España
}

def parse_proxy(proxy_url):
    """
    Convierte una URL de proxy en el formato 'http://username:password@host:port'
    o 'socks5h://username:password@host:port' a un diccionario con las claves 
    server, username y password para Playwright.
    
    Parameters:
        proxy_url (str): La URL del proxy a analizar
    
    Returns:
        dict: Un diccionario con la configuración del proxy para Playwright
    """
    try:
        parsed = urlparse(proxy_url)
        
        # Obtener el esquema (http, https, socks5, socks5h)
        scheme = parsed.scheme
        
        # Para proxies SOCKS, el formato de servidor es diferente
        if scheme.startswith('socks'):
            proxy_config = {
                "server": f"{parsed.hostname}:{parsed.port}",
                "username": parsed.username,
                "password": parsed.password,
                "type": scheme  # Esto será 'socks5' o 'socks5h'
            }
        else:
            # Para HTTP/HTTPS
            proxy_config = {
                "server": f"{scheme}://{parsed.hostname}:{parsed.port}",
                "username": parsed.username,
                "password": parsed.password
            }
            
        logger.info(f"Proxy analizado: {proxy_config['server']}")
        return proxy_config
    except Exception as e:
        logger.error(f"Error al analizar la URL del proxy: {e}")
        return None

def is_proxy_blacklisted(proxy_url):
    """
    Verifica si un proxy está en la lista negra.
    
    Args:
        proxy_url (str): URL del proxy a verificar
    
    Returns:
        bool: True si está en blacklist, False en caso contrario
    """
    if not PROXY_BLACKLIST_FILE.exists():
        return False
    
    try:
        with open(PROXY_BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            blacklist_data = json.load(f)
        
        # Verificar si el proxy está en la blacklist
        current_time = datetime.now()
        for entry in blacklist_data.get("blacklisted", []):
            if entry["proxy_url"] == proxy_url:
                # Verificar si ya pasó el tiempo de penalización
                blacklist_time = datetime.fromisoformat(entry["timestamp"])
                
                # Si ya pasó el tiempo, remover de la blacklist
                if (current_time - blacklist_time).total_seconds() > entry.get("duration", DEFAULT_BLACKLIST_DURATION):
                    return False
                
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error al verificar blacklist de proxies: {e}")
        return False

def add_proxy_to_blacklist(proxy_url, duration=DEFAULT_BLACKLIST_DURATION, reason="Unknown"):
    """
    Añade un proxy a la lista negra.
    
    Args:
        proxy_url (str): URL del proxy a añadir
        duration (int): Duración en segundos para mantener el proxy en blacklist
        reason (str): Razón por la que se añade a la blacklist
    """
    try:
        # Cargar blacklist o crear si no existe
        if PROXY_BLACKLIST_FILE.exists():
            with open(PROXY_BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                blacklist_data = json.load(f)
        else:
            blacklist_data = {
                "last_updated": datetime.now().isoformat(),
                "blacklisted": []
            }
        
        # Verificar si ya existe este proxy en la blacklist
        for entry in blacklist_data.get("blacklisted", []):
            if entry["proxy_url"] == proxy_url:
                # Actualizar entrada existente
                entry["timestamp"] = datetime.now().isoformat()
                entry["duration"] = duration
                entry["reason"] = reason
                break
        else:
            # Añadir nueva entrada
            blacklist_data.setdefault("blacklisted", []).append({
                "proxy_url": proxy_url,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "reason": reason
            })
        
        # Actualizar last_updated
        blacklist_data["last_updated"] = datetime.now().isoformat()
        
        # Guardar blacklist
        with open(PROXY_BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(blacklist_data, f, indent=4)
        
        logger.info(f"Proxy añadido a blacklist: {proxy_url} - Razón: {reason}")
        
    except Exception as e:
        logger.error(f"Error al añadir proxy a blacklist: {e}")

def test_proxy(proxy_url, timeout=10):
    """
    Prueba si un proxy funciona correctamente.
    
    Args:
        proxy_url (str): URL del proxy a probar
        timeout (int): Tiempo máximo de espera en segundos
    
    Returns:
        bool: True si el proxy funciona, False en caso contrario
    """
    try:
        # Verificar si está en blacklist
        if is_proxy_blacklisted(proxy_url):
            logger.warning(f"Proxy en blacklist: {proxy_url}")
            return False
        
        # Parsear el proxy
        proxy_config = parse_proxy(proxy_url)
        if not proxy_config:
            logger.error(f"No se pudo parsear el proxy: {proxy_url}")
            return False
        
        # Formatear proxy para requests
        proxies = {}
        if "type" in proxy_config and proxy_config["type"].startswith("socks"):
            proxies = {
                "http": f"{proxy_config['type']}://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}",
                "https": f"{proxy_config['type']}://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}"
            }
        else:
            server = proxy_config["server"]
            if not server.startswith(("http://", "https://")):
                server = "http://" + server
                
            proxies = {
                "http": f"{server.split('://')[0]}://{proxy_config['username']}:{proxy_config['password']}@{server.split('://')[1]}",
                "https": f"{server.split('://')[0]}://{proxy_config['username']}:{proxy_config['password']}@{server.split('://')[1]}"
            }
        
        # Realizar prueba de conexión
        start_time = time.time()
        response = requests.get("https://x.com", proxies=proxies, timeout=timeout)
        response_time = time.time() - start_time
        
        # Verificar código de respuesta
        if response.status_code == 200:
            logger.info(f"Proxy funcionando: {proxy_url} - Tiempo: {response_time:.2f}s")
            return True
        else:
            logger.warning(f"Proxy respondió con código {response.status_code}: {proxy_url}")
            
            # Si falla con un código de error específico, añadir a blacklist
            if response.status_code in [403, 407, 429, 502, 503]:
                add_proxy_to_blacklist(
                    proxy_url, 
                    duration=DEFAULT_BLACKLIST_DURATION,
                    reason=f"HTTP error {response.status_code}"
                )
            
            return False
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout al probar proxy: {proxy_url}")
        
        # Añadir a blacklist por timeout (duración más corta)
        add_proxy_to_blacklist(
            proxy_url, 
            duration=DEFAULT_BLACKLIST_DURATION / 4,  # 6 horas
            reason="Connection timeout"
        )
        
        return False
    except Exception as e:
        logger.error(f"Error al probar proxy {proxy_url}: {e}")
        return False

def get_random_proxy(country="mexico"):
    """
    Selecciona un proxy aleatorio del país especificado
    
    Parameters:
        country (str): Código del país para seleccionar proxy
    
    Returns:
        dict: Un diccionario con la configuración del proxy para Playwright
    """
    # Si el país no está en la lista, usar México como fallback
    if country not in PROXY_LISTS or not PROXY_LISTS[country]:
        logger.warning(f"No hay proxies disponibles para {country}, usando proxy de México")
        country = "mexico"
    
    # Si aún no hay proxies para México, registrar error y devolver None
    if not PROXY_LISTS.get("mexico"):
        logger.error("No hay proxies disponibles para México (fallback)")
        return None
    
    # Filtrar proxies que no estén en blacklist
    available_proxies = []
    for proxy_url in PROXY_LISTS[country]:
        if not is_proxy_blacklisted(proxy_url):
            available_proxies.append(proxy_url)
    
    # Si no hay proxies disponibles, dar un warning y usar cualquiera
    if not available_proxies:
        logger.warning(f"Todos los proxies de {country} están en blacklist. Usando cualquier proxy.")
        available_proxies = PROXY_LISTS[country]
    
    # Seleccionar un proxy aleatorio
    selected_proxy_url = random.choice(available_proxies)
    proxy_config = parse_proxy(selected_proxy_url)
    
    logger.info(f"Proxy seleccionado para {country}: {proxy_config['server'] if proxy_config else 'None'}")
    return proxy_config

def get_best_proxy(country="mexico", test_top_n=3):
    """
    Selecciona el mejor proxy disponible basado en pruebas de rendimiento
    
    Parameters:
        country (str): Código del país para seleccionar proxy
        test_top_n (int): Número de proxies a probar para seleccionar el mejor
    
    Returns:
        dict: Un diccionario con la configuración del proxy para Playwright
    """
    # Si el país no está en la lista, usar México como fallback
    if country not in PROXY_LISTS or not PROXY_LISTS[country]:
        logger.warning(f"No hay proxies disponibles para {country}, usando proxy de México")
        country = "mexico"
    
    # Si aún no hay proxies para México, registrar error y devolver None
    if not PROXY_LISTS.get("mexico"):
        logger.error("No hay proxies disponibles para México (fallback)")
        return None
    
    # Filtrar proxies que no estén en blacklist
    available_proxies = []
    for proxy_url in PROXY_LISTS[country]:
        if not is_proxy_blacklisted(proxy_url):
            available_proxies.append(proxy_url)
    
    # Si no hay proxies disponibles, dar un warning y usar cualquiera
    if not available_proxies:
        logger.warning(f"Todos los proxies de {country} están en blacklist. Usando proxy aleatorio.")
        return get_random_proxy(country)
    
    # Mezclar y seleccionar un subconjunto para probar
    random.shuffle(available_proxies)
    proxies_to_test = available_proxies[:min(test_top_n, len(available_proxies))]
    
    # Probar los proxies seleccionados y elegir el primero que funcione
    for proxy_url in proxies_to_test:
        if test_proxy(proxy_url):
            proxy_config = parse_proxy(proxy_url)
            logger.info(f"Mejor proxy seleccionado para {country}: {proxy_config['server']}")
            return proxy_config
    
    # Si todos los probados fallan, usar uno aleatorio
    logger.warning(f"Todas las pruebas de proxies fallaron. Usando proxy aleatorio.")
    return get_random_proxy(country)