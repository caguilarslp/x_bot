import os
import json
import time
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Función para cargar el archivo de sesión más reciente o uno específico
def load_session(specific_file=None):
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        raise Exception('Directorio de sesiones no encontrado.')
    
    if specific_file:
        session_path = sessions_dir / specific_file
        if not session_path.exists():
            raise Exception(f'Archivo de sesión no encontrado: {specific_file}')
        
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        print(f'Sesión cargada desde archivo específico: {specific_file}')
    else:
        # Obtener todos los archivos de sesión y ordenarlos por tiempo de creación (más reciente primero)
        session_files = []
        for file in sessions_dir.glob('x_session_*.json'):
            session_files.append({
                'name': file.name,
                'path': file,
                'time': file.stat().st_mtime
            })
        
        if len(session_files) == 0:
            raise Exception('No se encontraron archivos de sesión.')
        
        # Ordenar por tiempo (más reciente primero)
        session_files.sort(key=lambda x: x['time'], reverse=True)
        
        # Cargar el archivo más reciente
        with open(session_files[0]['path'], 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        print(f'Sesión cargada desde el archivo más reciente: {session_files[0]["name"]}')
    
    # Verificar la edad de la sesión
    session_timestamp = datetime.fromisoformat(session_data['timestamp'])
    session_age_hours = (datetime.now() - session_timestamp).total_seconds() / 3600
    
    if session_age_hours > 12:
        print(f'⚠️ Advertencia: La sesión tiene {session_age_hours:.1f} horas y podría haber expirado.')
    else:
        print(f'✓ La sesión tiene {session_age_hours:.1f} horas de antigüedad.')
    
    return session_data

# Función principal
async def open_browser_with_session(headless=False, url=None, specific_session=None, keep_open=True):
    # Cargar la sesión
    session_data = load_session(specific_session)
    
    # Crear directorio para capturas de pantalla si no existe
    screenshot_dir = Path('browser_screenshots')
    screenshot_dir.mkdir(exist_ok=True)
    
    # Iniciar el navegador
    async with async_playwright() as p:
        print("Iniciando navegador...")
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=20,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Crear contexto con el estado de sesión guardado
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=session_data.get('userAgent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'),
            locale='en-US',
            timezone_id='America/New_York',
            storage_state=session_data['sessionState'],
            bypass_csp=True,
            ignore_https_errors=True
        )
        
        # Crear una nueva página
        page = await context.new_page()
        
        # Navegar a la URL especificada o a X.com por defecto
        target_url = url if url else 'https://x.com/home'
        print(f"Navegando a: {target_url}")
        await page.goto(target_url, wait_until='networkidle')
        
        # Tomar captura de pantalla para verificar estado
        screenshot_path = str(screenshot_dir / f'session_loaded_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        await page.screenshot(path=screenshot_path)
        print(f"Captura de pantalla guardada en: {screenshot_path}")
        
        # Verificar si la sesión está activa
        try:
            await page.wait_for_selector('a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
            print("✅ Sesión verificada correctamente. Estás conectado en X.com")
        except Exception:
            print("⚠️ No se pudo verificar la sesión automáticamente. Verifica manualmente si estás conectado.")
        
        if keep_open:
            print("\nEl navegador permanecerá abierto hasta que presiones Enter para cerrarlo.")
            print("Puedes navegar manualmente mientras tanto.")
            input("Presiona Enter para cerrar el navegador cuando hayas terminado...\n")
        else:
            # Esperar un momento antes de cerrar
            await asyncio.sleep(5)
        
        await browser.close()
        print("Navegador cerrado.")

# Función para listar todas las sesiones disponibles
def list_sessions():
    sessions_dir = Path('sessions')
    if not sessions_dir.exists():
        print("No hay directorio de sesiones.")
        return
    
    session_files = []
    for file in sessions_dir.glob('x_session_*.json'):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            timestamp = datetime.fromisoformat(data['timestamp'])
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            
            session_files.append({
                'name': file.name,
                'time': timestamp,
                'age_hours': age_hours
            })
        except Exception as e:
            print(f"Error al leer {file.name}: {e}")
    
    if not session_files:
        print("No se encontraron archivos de sesión.")
        return
    
    # Ordenar por tiempo (más reciente primero)
    session_files.sort(key=lambda x: x['time'], reverse=True)
    
    print("\n=== Sesiones disponibles ===")
    for i, session in enumerate(session_files):
        status = "🟢" if session['age_hours'] < 12 else "🟠" if session['age_hours'] < 24 else "🔴"
        print(f"{i+1}. {status} {session['name']} - {session['time'].strftime('%Y-%m-%d %H:%M')} ({session['age_hours']:.1f} horas)")
    print("")

# Punto de entrada del script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Abre un navegador con una sesión guardada de X.com')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo sin interfaz gráfica')
    parser.add_argument('--url', type=str, help='URL a la que navegar (por defecto: https://x.com/home)')
    parser.add_argument('--session', type=str, help='Nombre específico del archivo de sesión a usar')
    parser.add_argument('--list', action='store_true', help='Listar todas las sesiones disponibles')
    parser.add_argument('--autoclose', action='store_true', help='Cerrar automáticamente el navegador después de cargar')
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions()
    else:
        asyncio.run(open_browser_with_session(
            headless=args.headless,
            url=args.url,
            specific_session=args.session,
            keep_open=not args.autoclose
        ))