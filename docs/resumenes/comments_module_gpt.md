## Resumen de `comment_on_post` (nuevo enfoque)

### Funcionalidades principales
1. **Listar tweets** en perfil con selector `tweet_articles`.
2. **Extraer enlace** al hilo: `//a[contains(@href, "/status/")]`.
3. **Navegar** a la página del tweet (`page.goto(tweet_url)`).
4. **Simular delay humano** antes de teclear.
5. **Escribir comentario** en `//div[@data-testid="tweetTextarea_0"]` con `_human_typing()`.
6. **Enviar** con `//button[@data-testid="tweetButton"]`.
7. **Esperar** al ocultamiento del progress bar (`//div[@role="progressbar"]//div[@data-testid="progressBar-bar"]`).
8. **Regresar** a la URL de perfil y pequeño delay.
9. **Loggear** la acción (ahora incluye `tweet_url`).

### Qué se simplificó
- Eliminación de la gestión manual del modal (apertura/cierre).
- Centralización de navegación y comentarios en un único flujo lineal.
- Reutilización de `_find_element()` con `context` para buscar selectores en distintas páginas.

### Posibles mejoras a futuro
- **Persistencia de metadatos**: método para guardar `{tweet_url, comment_text, timestamp, status}` en base de datos o fichero.  
- **Reintentos**: lógica de retry/backoff en caso de fallos transitorios (ej. elementos no cargan).  
- **Configuración dinámica**: exponer timeouts, delays y límites de scroll en `action_config.json`.  
- **Validación post-envío**: comprobar que el contador de replies aumentó antes de confirmar éxito.  
- **Estadísticas y métricas**: recolectar latencias, tasas de fallo y generar reportes periódicos.  
- **Modo dry-run**: posibilidad de ejecutar comentarios en un entorno de staging (sin publicar realmente).  
- **Pruebas unitarias**: desacoplar lógica en funciones mockeables para testeo local sin navegador.  
