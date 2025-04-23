# Documentación de Selectores para Registro Automatizado en X.com

## 1. Botón de Creación de Cuenta
### Selector/Xpath
```xpath
//a[@data-testid="signupButton"]
```
#### Características
- Texto: "Create account"
- Clase CSS: Con múltiples clases de estilo Tailwind
- Color de fondo: RGB(29, 155, 240) - Azul de X

## 2. Selector de Método de Registro
### Selector "Usar email"
```xpath
//span[contains(text(), "Use email instead")]
```

## 3. Campo de Email
### Selector/Xpath
```xpath
//div[contains(@class, "r-18u37iz")]//div[contains(text(), "Email")]
```

## 4. Selectores de Fecha de Nacimiento

### Mes
```xpath
//select[@id="SELECTOR_1"]
```
- Rango: Enero (1) a Diciembre (12)

### Día
```xpath
//select[@id="SELECTOR_2"]
```
- Rango: 1 a 31

### Año
```xpath
//select[@id="SELECTOR_3"]
```
- Rango: Descendente desde 1908

## 5. Botón "Next"
```xpath
//span[contains(text(), "Next")]
```

## 6. Campo de Contraseña
```xpath
//input[@type="password" and @name="password"]
```

## 7. Selección de Nombre de Usuario
### Botones de Nombre de Usuario
```xpath
//button[contains(@class, "css-175oi2r") and contains(@role, "button") and contains(@type, "button")]//span[contains(@class, "r-bcqeeo")]
```

## 8. Seguimiento de Usuarios/Temas
### Botón de Seguimiento
```xpath
//button[@data-testid="UserCell"]
```

## 9. Siguiente en Seguimiento de Usuarios
```xpath
//button[@data-testid="UserCell"]//span[contains(text(), "Follow")]
```

## 10. Cajas de Intereses (Ejemplo: Noticias)
```xpath
//div[contains(@class, "css-175oi2r")]//span[contains(text(), "News")]
```

## Consideraciones Generales
- Usar estrategias flexibles de selección
- Tener alternativas de selección
- Manejar esperas dinámicas
- Implementar tolerancia a cambios en la estructura

## Estrategia de Automatización
1. Navegar a URL de registro
2. Rellenar campos con datos generados
3. Hacer clics en botones de avance
4. Manejar posibles variaciones en UI

### Recomendaciones Adicionales
- Implementar delays aleatorios
- Simular comportamiento humano
- Manejar excepciones de elementos
- Validar cada paso del registro