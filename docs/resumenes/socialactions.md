python main.py social like --account antonioreverteandujar@gmx.com AlexisRivPon --count 3



# Seguir a un usuario
python main.py social follow AlexisRivPon --account tu_usuario

# Dar likes a publicaciones
python main.py social like AlexisRivPon --count 3 --account tu_usuario

# Comentar en un perfil
python main.py social comment AlexisRivPon --text "Excelente labor, licenciado!!!" --account tu_usuario

# Procesar perfiles por lotes
python main.py social batch batch_profiles.json --account tu_usuario




(venv) (base) PS D:\projects\x_bot> python main.py --account antonioreverteandujar@gmx.com social interact AlexisRivPon --likes 2 --comment "Excelente contenido mi lic!"
2025-04-23 20:17:15,778 - INFO - Configurando proxy para mexico
2025-04-23 20:17:15,779 - INFO - Proxy analizado: gate.decodo.com:7000
2025-04-23 20:17:15,779 - INFO - Proxy seleccionado para mexico: gate.decodo.com:7000
2025-04-23 20:17:15,780 - INFO - Proxy configurado: gate.decodo.com:7000
2025-04-23 20:17:16,529 - INFO - Sesión cargada desde: x_session_antonioreverteandujar@gmx.com_20250423.json
2025-04-23 20:17:16,529 - INFO - La sesión tiene 10.0 horas de antigüedad.
2025-04-23 20:17:16,529 - INFO - Usando proxy: gate.decodo.com:7000

🔄 Iniciando interacción natural con @AlexisRivPon
📱 Navegando a home...
📜 Explorando timeline...
🔍 Visitando perfil de @AlexisRivPon...
2025-04-23 20:17:36,843 - INFO - Navegando al perfil de @AlexisRivPon
2025-04-23 20:17:44,528 - INFO - Navegación exitosa a @AlexisRivPon
👥 Verificando seguimiento...
2025-04-23 20:17:48,114 - ERROR - Error al seguir a @AlexisRivPon: object Locator can't be used in 'await' expression
📜 Explorando publicaciones...
👍 Dando 2 likes...
2025-04-23 20:17:56,617 - INFO - Buscando 2 publicaciones para dar like
2025-04-23 20:18:06,810 - INFO - Se encontraron 8 botones de like
✅ Se dieron 0 likes
💬 Comentando: 'Excelente contenido mi lic!'
2025-04-23 20:18:20,060 - INFO - Intentando comentar en la publicación #0
2025-04-23 20:18:20,065 - ERROR - Error al comentar: object Locator can't be used in 'await' expression
❌ Error al comentar: object Locator can't be used in 'await' expression
✨ Interacción con @AlexisRivPon completada
2025-04-23 20:18:20,066 - INFO - Actualizando estado de la sesión...
2025-04-23 20:18:20,066 - INFO - Actualizando estado de la sesión...
2025-04-23 20:18:20,323 - INFO -
Analizando estructura de la página...
2025-04-23 20:18:20,358 - INFO - Sesión actualizada exitosamente en: sessions\x_session_antonioreverteandujar@gmx.com_20250423.json

Presiona Enter para cerrar el navegador...

2025-04-23 20:18:38,882 - INFO - Página cerrada.
2025-04-23 20:18:38,884 - ERROR - Error al cerrar contexto: BrowserContext.close: Target page, context or browser has been closed
2025-04-23 20:18:38,884 - INFO - Navegador cerrado.
(venv) (base) PS D:\projects\x_bot>




(venv) (base) PS D:\projects\x_bot> python main.py --account antonioreverteandujar@gmx.com session
2025-04-23 20:21:17,067 - INFO - Configurando proxy para mexico
2025-04-23 20:21:17,067 - INFO - Proxy analizado: gate.decodo.com:7000
2025-04-23 20:21:17,068 - INFO - Proxy seleccionado para mexico: gate.decodo.com:7000
2025-04-23 20:21:17,068 - INFO - Proxy configurado: gate.decodo.com:7000
2025-04-23 20:21:17,183 - INFO - Sesión cargada desde: x_session_antonioreverteandujar@gmx.com_20250423.json
2025-04-23 20:21:17,183 - INFO - La sesión tiene 10.1 horas de antigüedad.
2025-04-23 20:21:17,184 - INFO - Usando proxy: gate.decodo.com:7000
2025-04-23 20:21:17,755 - INFO - Iniciando navegador...
2025-04-23 20:21:18,551 - INFO - Navegando a: https://x.com/home
2025-04-23 20:21:25,425 - INFO - Captura de pantalla guardada en: browser_screenshots\session_loaded_20250423_202124.png
2025-04-23 20:21:25,461 - INFO -
Analizando estructura de la página...

Indicadores de sesión encontrados:
✓ Enlace de navegación: Home
✓ Enlace de navegación: Notifications
✓ Enlace de navegación: Profile
✓ Botón de cambio de cuenta encontrado
✓ Timeline de inicio encontrado
✓ Menú de navegación lateral encontrado
✓ Logo de X encontrado

Información del perfil detectada:
  username: AndujarReverte

 Estás conectado en X.com correctamente

El navegador permanecerá abierto hasta que presiones Enter para cerrarlo.
Puedes navegar manualmente mientras tanto.
La sesión se actualizará: primera actualización en 1 minuto, luego cada 5 minutos.
Presiona Enter para cerrar el navegador cuando hayas terminado...

2025-04-23 20:22:19,042 - INFO - Actualizando sesión antes de cerrar...
2025-04-23 20:22:19,042 - INFO - Actualizando estado de la sesión...
2025-04-23 20:22:19,166 - ERROR - Error al obtener información del perfil: Page.content: Target page, context or browser has been closed
2025-04-23 20:22:19,171 - ERROR - Error al actualizar sesión: Page.evaluate: Target page, context or browser has been closed
2025-04-23 20:22:19,375 - INFO - Navegador cerrado.
(venv) (base) PS D:\projects\x_bot>