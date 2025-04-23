# Documentación de Argumentos de main.py

He modificado el archivo `main.py` para que acepte todos los argumentos necesarios para el módulo de sesión. Respecto a tu pregunta sobre usar "--login" y "--session" como argumentos en lugar de subcomandos, la estructura actual utiliza subcomandos (`login` y `session`) en lugar de argumentos con guiones (como "--login"). Esto es una práctica común para herramientas de línea de comandos con múltiples funcionalidades, similar a cómo funcionan git (git pull, git push) o npm (npm install, npm update).

## Estructura de Comandos

El script `main.py` utiliza un sistema de subcomandos, donde después del nombre del script, se especifica qué acción realizar:

```
python main.py [opciones globales] <comando> [opciones del comando]
```

## Argumentos Globales (Aplicables a todos los comandos)

| Argumento | Tipo | Descripción |
|-----------|------|-------------|
| `--no-proxy` | Flag | Desactiva el uso de proxies |
| `--proxy-country` | String | País del proxy a utilizar (opciones: mexico, united_states, spain) |

## Subcomando: login

```
python main.py [opciones globales] login
```

Este comando inicia el proceso de login manual en X.com, donde el usuario debe ingresar sus credenciales.

**No tiene argumentos específicos adicionales.**

## Subcomando: session

```
python main.py [opciones globales] session [opciones de session]
```

Este comando utiliza una sesión previamente guardada para conectarse a X.com.

| Argumento | Tipo | Descripción |
|-----------|------|-------------|
| `--headless` | Flag | Ejecuta el navegador en modo invisible (sin interfaz gráfica) |
| `--url` | String | URL específica a la que navegar (por defecto: https://x.com/home) |
| `--autoclose` | Flag | Cierra automáticamente el navegador después de cargar la sesión |
| `--list` | Flag | Muestra una lista de todas las sesiones disponibles para seleccionar |
| `--account` | String | Nombre de usuario específico para cargar su sesión más reciente |
| `--session` | String | Nombre específico del archivo de sesión a utilizar |

## Ejemplos de Uso

1. Iniciar sesión manualmente sin usar proxy:
   ```
   python main.py --no-proxy login
   ```

2. Ver lista de sesiones disponibles:
   ```
   python main.py --no-proxy session --list
   ```

3. Usar sesión específica y navegar a una URL personalizada:
   ```
   python main.py --no-proxy session --session x_session_usuario_20250423.json --url https://x.com/explore
   ```

4. Usar la sesión más reciente de una cuenta específica en modo headless:
   ```
   python main.py --no-proxy session --account usuario@example.com --headless
   ```

5. Usar proxy de España y abrir la sesión más reciente con cierre automático:
   ```
   python main.py --proxy-country spain session --autoclose
   ```

El diseño actual basado en subcomandos proporciona una interfaz clara y estructurada que permite ampliar fácilmente la herramienta con nuevos comandos en el futuro.