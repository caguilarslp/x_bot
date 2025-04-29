# Sistema de Warmup para X.com

## Descripción

Este módulo implementa una estrategia gradual para establecer nuevas cuentas o reactivar cuentas inactivas en X.com (antes Twitter), simulando patrones de comportamiento humano realistas. El sistema está diseñado para integrarse con el bot principal y funciona mediante un proceso de tres fases progresivas que construyen un historial de uso natural antes de realizar interacciones más intensivas.

## Características principales

- **Simulación de comportamiento humano**: Patrones de navegación variables, tiempos de espera aleatorios, errores de escritura simulados.
- **Progresión automática**: Avance gradual entre fases y días basado en tiempo transcurrido.
- **Integración completa**: Utiliza el mismo sistema de login, navegación y acciones del bot principal.
- **Gestión multi-cuenta**: Seguimiento independiente del estado de cada cuenta.
- **Configuración personalizable**: Parámetros ajustables para todas las fases y tipos de interacción.
- **Estrategia anti-detección**: Minimiza riesgos al establecer un patrón de uso creíble.

## Estructura del warmup

### Fase 1: Aclimatación inicial
- **Día 1**: Navegación pasiva (5-8 perfiles, scrolling)
- **Día 2**: Navegación + 2-5 follows
- **Día 3**: Navegación + 3-6 follows + 1-3 likes

### Fase 2: Actividad moderada 
- **Día 1**: 10-15 perfiles, 5-8 follows, 3-7 likes, 0-1 comentarios
- **Día 2**: 12-18 perfiles, 6-10 follows, 5-10 likes, 1-2 comentarios
- **Día 3**: 15-20 perfiles, 8-12 follows, 8-15 likes, 2-4 comentarios

### Fase 3: Actividad plena
- **Día 1**: 15-25 perfiles, 10-15 follows, 10-20 likes, 3-5 comentarios
- **Día 2**: 20-30 perfiles, 12-18 follows, 15-25 likes, 4-8 comentarios
- **Día 3**: 25-35 perfiles, 15-20 follows, 20-30 likes, 5-10 comentarios

## Uso

### Requisitos previos
- Python 3.8+
- Playwright instalado
- Estructura de archivos del bot principal

### Instalación
```bash
# Asegúrate de tener playwright
pip install playwright
playwright install chromium

# Copiar archivos a la estructura del bot principal
cp warmup.py .
cp warmup_config.json app/config/
cp warmup_actions.py app/actions/
mkdir -p warmup_data
```

### Ejecución

#### Modo interactivo (recomendado)
```bash
python warmup.py
```

#### Con usuario específico
```bash
python warmup.py --username nombre_usuario
```

#### Ver estado de cuentas
```bash
python warmup.py --list
```

#### Opciones adicionales
```bash
python warmup.py --username nombre_usuario --phase 2 --no-proxy
```

## Archivos incluidos

- `warmup.py` - Script principal para ejecutar el proceso
- `warmup_config.json` - Configuración de fases, días y parámetros
- `warmup_actions.py` - Implementación de las acciones específicas
- `warmup_data/` - Directorio para almacenar el estado de cada cuenta

## Integración con x_bot

Este sistema está diseñado para integrarse perfectamente con el bot principal:
1. Comparte el mismo sistema de gestión de sesiones
2. Utiliza la misma estructura de selectores
3. Reutiliza mecanismos anti-detección
4. Comparte sistema de logging y configuración

## Recomendaciones para uso efectivo

1. **Consistencia**: Ejecutar sesiones diarias o al menos cada 48 horas
2. **Paciencia**: Completar al menos la Fase 2 antes de operaciones intensivas
3. **Privacidad**: Usar proxies y alternar user agents
4. **Monitoreo**: Revisar periódicamente el estatus de las cuentas
5. **Mantenimiento**: Actualizar selectores si cambia la interfaz de X.com

---

Para documentación más detallada, consultar `Sistema de Warmup para X.com.md`