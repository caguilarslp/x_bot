# Sistema de Warmup para X.com

Este sistema implementa una estrategia de "warmup" gradual para cuentas de X.com (anteriormente Twitter), diseñado para simular comportamiento humano y establecer un historial de uso natural antes de iniciar interacciones más intensivas.

## Descripción

El sistema de warmup está diseñado para aclimatar cuentas nuevas o reactivar cuentas inactivas de forma progresiva, siguiendo un plan estructurado en fases y días. Esto ayuda a:

1. Minimizar riesgos de detección de automatización
2. Establecer un patrón de uso natural y orgánico
3. Crear una presencia creíble en la plataforma
4. Preparar la cuenta para operaciones automatizadas futuras

## Fases del sistema de warmup

El sistema implementa una estrategia progresiva dividida en tres fases, cada una con tres días de actividades específicas:

### Fase 1 - Aclimatación inicial (3 días)
- **Día 1**: Solo navegación pasiva - Visita 5-8 perfiles, hace scrolling en el feed, observa publicaciones.
- **Día 2**: Navegación pasiva + Sigue 2-5 cuentas populares y seguras.
- **Día 3**: Navegación pasiva + Sigue 3-6 cuentas + Primeros likes selectivos (1-3).

### Fase 2 - Actividad moderada (3 días)
- **Día 1**: Navegación activa (más perfiles) + 5-8 follows + 3-7 likes + Posibilidad de primer comentario.
- **Día 2**: Actividad incrementada (12-18 perfiles visitados) + 6-10 follows + 5-10 likes + 1-2 comentarios.
- **Día 3**: Actividad consolidada con mayor interacción en comentarios (2-4) y likes (8-15).

### Fase 3 - Actividad plena (3 días)
- **Día 1**: Actividad alta con 15-25 perfiles visitados, 10-15 follows, 10-20 likes y 3-5 comentarios.
- **Día 2**: Mayor actividad con 20-30 perfiles, 12-18 follows, 15-25 likes y 4-8 comentarios.
- **Día 3**: Actividad completa con 25-35 perfiles, 15-20 follows, 20-30 likes y 5-10 comentarios.

El sistema avanza automáticamente entre días y fases cuando detecta que ha pasado al menos un día desde la última sesión.

## Características

- **Navegación realista**: Recorrido natural en perfiles y feed con patrones variables
- **Comportamiento humano simulado**: Pausas aleatorias, tiempo variable entre acciones
- **Progresión gradual**: Incremento natural de actividad a lo largo de los días y fases
- **Gestión inteligente de interacciones**: Selección estratégica de cuentas a seguir y publicaciones para interactuar
- **Registro detallado**: Historial completo de todas las actividades para cada cuenta
- **Integración con sistema existente**: Uso de las mismas funciones de login, navegación e interacción
- **Gestión eficiente de sesiones**: Actualización automática de cookies y sesiones en cada ejecución
- **Avance automático entre fases**: Detección de días transcurridos y progresión natural
- **Soporte para múltiples cuentas**: Gestión independiente del estado de cada cuenta

## Estructura

```
warmup.py                        # Script principal independiente
warmup_config.json               # Configuración de fases y parámetros
app/
  └── actions/
      └── warmup_actions.py      # Funciones específicas para acciones de warmup
warmup_data/                     # Directorio para almacenar datos de cada cuenta
  └── [username]_warmup.json     # Registro de acciones para cada cuenta
```

## Uso

### Requisitos previos

- Python 3.8+
- Playwright instalado (`pip install playwright`)
- Instalar navegadores de Playwright (`playwright install chromium`)
- Archivo `login_accounts.json` con información de cuentas

### Ejecución

El script principal se puede ejecutar de varias formas:

#### Modo interactivo (recomendado)
```bash
python warmup.py
```
Esto mostrará una lista de todas las cuentas disponibles en `login_accounts.json` con información sobre su estado actual de warmup, permitiéndote seleccionar una cuenta de manera interactiva.

#### Con credenciales específicas
```bash
python warmup.py --username [X_USERNAME] [--phase 1] [--no-proxy]
```

#### Solo listar cuentas disponibles
```bash
python warmup.py --list
```

### Parámetros disponibles

- `--username` o `-u`: Nombre de usuario de X.com (opcional)
- `--phase`: Fase de warmup a ejecutar (1-3, por defecto 1)
- `--no-proxy`: Ejecutar sin usar proxy (por defecto usa proxy)
- `--list` o `-l`: Solo listar las cuentas disponibles sin ejecutar warmup

### Ejemplo de uso

Ejecución interactiva:
```bash
python warmup.py
```

Ver estado de las cuentas:
```bash
python warmup.py --list
```

Uso con parámetros específicos:
```bash
python warmup.py --username mi_cuenta_twitter --phase 1
```

## Configuración

El archivo `warmup_config.json` contiene la configuración detallada del comportamiento para cada fase y día, así como las cuentas objetivo para interacción.

La configuración incluye:
- Número de perfiles a visitar
- Número de scrolls en perfiles y feed
- Número de publicaciones a visualizar
- Número de cuentas a seguir
- Número de likes a realizar
- Número de comentarios a realizar
- Listas de cuentas objetivo categorizadas (influencers, noticias, políticos, marcas)
- Configuración de delays para simular comportamiento humano
- Comentarios predefinidos para usar en distintos contextos

## Almacenamiento de datos

### Ubicación de los archivos de datos

Los datos del proceso de warmup se almacenan en dos ubicaciones:

1. **Datos de warmup**: `warmup_data/[username]_warmup.json`
   - Contiene el historial completo de sesiones, cuentas seguidas, posts con like
   - Registra la fase y día actual de la cuenta
   - Ejemplo: `warmup_data/nombre_usuario_warmup.json`

2. **Archivos de sesión**: `sessions/`
   - Contiene las cookies y datos de sesión de X.com
   - Se actualiza automáticamente en cada ejecución del warmup

### Estructura del archivo de datos de warmup

El archivo JSON de cada cuenta contiene:

```json
{
  "username": "nombre_cuenta",
  "start_date": "2025-04-29",
  "current_phase": 1,
  "current_day": 2,
  "history": [
    {
      "date": "2025-04-29",
      "time": "10:15:23",
      "phase": 1,
      "day": 1,
      "actions": {
        "profile_visits": [...],
        "feed_activity": {...},
        "follows": [...],
        "likes": [],
        "comments": []
      }
    }
  ],
  "followed_accounts": [
    {
      "username": "cuenta_seguida",
      "followed_at": "2025-04-30T14:22:18",
      "category": "influencer"
    }
  ],
  "liked_posts": [
    {
      "post_url": "https://x.com/usuario/status/123456789",
      "username": "propietario_post",
      "timestamp": "2025-05-01T15:33:42"
    }
  ]
}
```

El sistema utiliza estos archivos para mantener la continuidad entre sesiones y asegurar la progresión natural del proceso de warmup.

## Funcionamiento técnico

### Proceso de ejecución

1. **Selección de cuenta**: El script carga las cuentas desde `login_accounts.json` y permite seleccionar una.

2. **Carga de datos de warmup**: Determina la fase y día actuales, o crea un nuevo registro si es la primera ejecución.

3. **Autenticación**: 
   - Intenta cargar una sesión existente desde el directorio `sessions/`
   - Si no hay sesión válida, realiza login completo utilizando el módulo `login_sesion.py`

4. **Ejecución de acciones**:
   - Navega por el feed con patrones realistas
   - Visita perfiles aleatorios según los parámetros de la fase/día
   - Realiza follows según la configuración de la fase/día
   - Realiza likes y comentarios si está configurado para la fase/día actual

5. **Registro de actividad**:
   - Actualiza el archivo de historial con todas las acciones realizadas
   - Actualiza las cookies y sesión en el directorio `sessions/`

### Avance entre fases

- El sistema detecta automáticamente si ha pasado al menos un día desde la última sesión
- Cuando se completan los 3 días de una fase, avanza automáticamente a la siguiente
- Cuando se completan los 3 días de la Fase 3, reinicia a día 1 de Fase 3 (mantiene la actividad plena)

### Implementación de comportamiento humano

El sistema utiliza varias técnicas para simular comportamiento humano:

- **Tiempos de espera variables**: Pausas aleatorias entre acciones (2-8 segundos)
- **Exploración natural**: Patrones de scrolling no lineales
- **Observación de contenido**: Tiempo variable observando publicaciones
- **Interacciones diferenciadas**: Diferentes proporciones de likes, follows y comentarios según la fase
- **Errores de escritura**: Simulación ocasional de errores de tipeo y corrección
- **Velocidad de escritura variable**: Tiempo diferente para escribir cada caracter
- **Sesiones consistentes**: Mantenimiento de cookies y sesiones como un usuario real

## Integración con x_bot

El sistema de warmup está diseñado para integrarse con el bot principal de X.com, compartiendo:

1. **Sistema de login y sesiones**
2. **Gestión de proxies**
3. **Selectores y acciones base**
4. **Estructura de datos y configuración**

Para utilizar el warmup como parte del flujo principal de trabajo:

1. Primero ejecutar el proceso de warmup completo para nuevas cuentas
2. Una vez finalizada la Fase 3, pasar a operaciones normales con x_bot
3. Mantener sesiones periódicas de actividad natural para evitar patrones sospechosos

## Consideraciones de seguridad

Para maximizar la seguridad de las cuentas durante el proceso de warmup:

1. **Usar proxies diferentes** para cada cuenta
2. **Mantener intervalos de al menos 24 horas** entre sesiones
3. **Evitar patrones exactos** de tiempo o cantidad de interacciones
4. **Rotar dispositivos y user agents**
5. **No iniciar interacciones intensivas** hasta completar al menos la Fase 2
6. **Priorizar calidad sobre cantidad** en las interacciones

## Solución de problemas comunes

| Problema | Solución |
|----------|----------|
| Error de login | Verificar credenciales en login_accounts.json |
| Sesión expirada | Ejecutar con modo interactivo para renovar sesión |
| No avanza de fase | Verificar que ha pasado al menos un día entre sesiones |
| Errores en selectores | Actualizar warmup_actions.py con los selectores actualizados |
| Bloqueo de cuenta | Pausar actividad por 48-72 horas y reiniciar en Fase 1 |

---

Este sistema de warmup es una herramienta fundamental para establecer cuentas de X.com con un historial de uso natural y minimizar riesgos de detección al utilizar automatización.