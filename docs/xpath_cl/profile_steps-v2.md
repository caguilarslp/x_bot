
## 🧭 FLUJO COMPLETO: "Set up profile" en X.com

---

### 🟢 Paso 0: Comenzar configuración
- **Acción:** Se detecta que el usuario aún no ha completado el perfil.
- **Texto en pantalla:** `"Set up profile"`
- **XPath:**
  ```xpath
  //span[text()="Set up profile"]
  ```

---

### 🖼 Paso 1: Subir imagen de perfil
- **Modal abierto con título:** `Pick a profile picture`
- **Botón para subir imagen:**
  ```xpath
  //button[@aria-label="Add photos or video"]
  ```
- **Campo input para subir archivo:**
  ```xpath
  //input[@type="file" and @data-testid="fileInput"]
  ```
- **Botón "Skip for now":**
  ```xpath
  //button[@data-testid="ocfSelectAvatarSkipForNowButton"]
  ```
- **Si se sube imagen → botón "Apply" para confirmar:**
  ```xpath
  //button[@data-testid="applyButton"]
  ```
- **Luego botón "Next":**
  ```xpath
  //button[@data-testid="ocfSelectAvatarNextButton"]
  ```

---

### 🖼 Paso 2: Imagen de cabecera (opcional)
- **Modal con título:** `Pick a header`
- **Botón para subir header:**
  ```xpath
  //button[@aria-label="Add photos or video"]
  ```
- **Input file para header:**
  ```xpath
  //input[@type="file" and @data-testid="fileInput"]
  ```
- **Omitir esta sección con botón Skip:**
  ```xpath
  //button[@data-testid="ocfSelectBannerSkipForNowButton"]
  ```

---

### ✍ Paso 3: Bio y nombre de usuario
- **Nombre de usuario (ya mostrado):**
  ```xpath
  //h1[@role="heading"]//span[contains(text()," ")]
  ```
- **Username o @handle:**
  ```xpath
  //span[starts-with(text(),"@")]
  ```

---

### 🛠️ Controles adicionales útiles
- **Botón volver (flecha hacia la izquierda):**
  ```xpath
  //button[@data-testid="app-bar-back"]
  ```
- **Cerrar modal con la X:**
  ```xpath
  //svg[@aria-label="X"]
  ```

---

### 🧪 Ejemplo de flujo básico en XPath:

```python
# Playwright (sync)
page.locator('//span[text()="Set up profile"]').click()
page.locator('//input[@type="file" and @data-testid="fileInput"]').set_input_files("imagen.jpg")
page.locator('//button[@data-testid="applyButton"]').click()
page.locator('//button[@data-testid="ocfSelectAvatarNextButton"]').click()
page.locator('//button[@data-testid="ocfSelectBannerSkipForNowButton"]').click()
```
