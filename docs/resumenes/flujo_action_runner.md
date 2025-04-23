Gran pregunta. Basándome en los archivos existentes y la estrategia de desarrollo, el flujo probable será:

### Flujo de Llamada de ActionRunner

1. **Punto de Entrada**: `main.py`
2. **Proceso de Autenticación**: 
   - Usar `login_sesion.py` para abrir una sesión
   - Este script ya maneja la apertura del navegador con una sesión existente

3. **Posible Estructura de Llamada**:
```
main.py --session --action [tipo_accion] --target [parametros]
```

Ejemplo:
```bash
# Seguir usuarios
python main.py session --action follow --target usuario1,usuario2

# Dar likes
python main.py session --action like --count 10 --target username
```

### Componentes Necesarios

1. **En `main.py`**:
   - Extender el argparse para manejar acciones
   - Importar `ActionRunner`
   - Crear lógica para instanciar y ejecutar acciones

2. **En `login_sesion_iniciada.py`**:
   - Modificar para devolver el objeto `page` de Playwright
   - Facilitar la integración con `ActionRunner`

### Flujo Detallado
```
main.py 
  ↓ 
Parsea argumentos 
  ↓
Inicia sesión con login_sesion_iniciada.py 
  ↓
Crea instancia de ActionRunner 
  ↓
Ejecuta acciones específicas
```

### Consideraciones
- Necesitamos modificar `main.py`
- Requerimos un método en `login_sesion_iniciada.py` para exponer fácilmente el objeto `page`
- `ActionRunner` debe ser lo suficientemente flexible para manejar diferentes tipos de acciones

¿Quieres que procedamos a modificar `main.py` para soportar este nuevo flujo de actions?