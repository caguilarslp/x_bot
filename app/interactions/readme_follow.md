## Simple Follow and Extract

Este script hace exactamente lo que pediste, siguiendo un flujo automático:

1. Accede al perfil de usuario
2. Espera unos segundos
3. Verifica si ya lo seguimos:
   - Si ya lo seguimos → Continúa al siguiente paso
   - Si no lo seguimos → Hace clic en Follow
4. Extrae las URLs de las publicaciones
5. Hace scroll y extrae más URLs (número de scrolls configurable)
6. Actualiza la sesión

## Uso


DanielAlan05 

```bash
# Uso básico (con selección de cuenta)
python simple_follow_extract.py elonmusk

# Especificar cuenta para automatizar completamente
python simple_follow_extract.py elonmusk --account antonioreverteandujar@gmx.com

# Más scrolls para extraer más publicaciones
python simple_follow_extract.py elonmusk --scrolls 10

# Modo headless para entornos sin interfaz gráfica
python simple_follow_extract.py elonmusk --account antonioreverteandujar@gmx.com --headless
```

## Ventajas

- **Automático**: Realiza todo el proceso sin intervención del usuario
- **Simple**: Sin complicaciones ni parámetros innecesarios
- **Rápido**: Flujo directo sin bifurcaciones complejas
- **Efectivo**: Hace exactamente lo necesario
- **Práctico**: Guarda resultados en formato estándar

Las URLs extraídas se guardan en la carpeta `posts/` con el formato `username_posts_fecha_hora.json` para ser utilizadas posteriormente por otros scripts.

Este script está listo para usar y se puede ejecutar simplemente indicando el usuario objetivo.