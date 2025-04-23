# Actualización de Sesiones en X Bot

El mecanismo de actualización de sesiones en X Bot permite mantener las cookies y datos de autenticación vigentes sin necesidad de iniciar sesión manualmente cada vez. Este proceso funciona de la siguiente manera:

## Proceso de Actualización

1. **Carga Inicial**: Al iniciar el navegador con una sesión guardada, el sistema carga el archivo JSON que contiene el estado de la sesión anterior, incluyendo cookies, tokens y metadatos.

2. **Verificación de Sesión**: El sistema verifica que la sesión cargada sea válida analizando la estructura de la página para detectar indicadores de inicio de sesión exitoso.

3. **Programación de Actualizaciones**:
   - Primera actualización: Se realiza automáticamente 1 minuto después de iniciar la sesión
   - Actualizaciones posteriores: Se programan cada 5 minutos mientras el navegador permanezca abierto

4. **Proceso de Actualización de Sesión**:
   - Captura del estado actual del navegador (cookies, localStorage, sessionStorage)
   - Extracción de información del perfil mediante análisis de la estructura HTML
   - Preservación de metadatos importantes del archivo original (como timestamps de creación)
   - Generación de un nuevo timestamp de actualización
   - Escritura del archivo JSON actualizado, reemplazando el anterior

5. **Actualización Final**: Antes de cerrar el navegador, se realiza una última actualización para asegurar que se capture el estado más reciente de la sesión.

## Beneficios del Sistema de Actualización

- **Reducción de Captchas**: Al mantener sesiones "frescas", se reduce significativamente la necesidad de resolver captchas.
- **Continuidad Operativa**: Permite realizar acciones programadas sin interrupciones por caducidad de sesiones.
- **Eficiencia**: Elimina la necesidad de iniciar sesión manualmente de forma frecuente.
- **Persistencia**: Mantiene los datos de autenticación actualizados incluso durante sesiones largas.

## Almacenamiento de Datos

Los archivos de sesión se almacenan en formato JSON en el directorio `/sessions` con un nombre que sigue el patrón `x_session_{username}_{date}.json`. Cada archivo contiene:

- Estado completo del navegador (cookies, localStorage, etc.)
- Metadatos (timestamps, userAgent, plataforma)
- Información del perfil extraída durante la navegación

Esta implementación asegura que las sesiones se mantengan vigentes durante el mayor tiempo posible, reduciendo la necesidad de autenticación manual y facilitando la automatización de interacciones con X.com.