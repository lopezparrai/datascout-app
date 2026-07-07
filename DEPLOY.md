# Deployment Guide: DataScout on Streamlit Community Cloud

Sigue estos pasos para publicar tu aplicación DataScout en internet, de forma gratuita y segura, usando Streamlit Community Cloud.

## 1. Subir el proyecto a GitHub (Repositorio Público)
Para que Streamlit pueda leer tu código y desplegarlo, el repositorio debe estar en GitHub. Dado que ya tienes un repositorio Git inicializado y configuramos un `.gitignore` para no subir la API Key, los pasos son:

1. Ve a [GitHub](https://github.com/) y crea un nuevo repositorio (por ejemplo, `datascout-app`). Ponlo como **Public** (Público). No le agregues un README, .gitignore ni licencia desde GitHub, déjalo completamente vacío.
2. Abre la terminal en esta carpeta de tu proyecto y ejecuta los siguientes comandos, reemplazando `TU_USUARIO` y `TU_REPO` por los tuyos:

```bash
git add .
git commit -m "Primer commit: DataScout Streamlit app"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```
> [!NOTE]
> Gracias al `.gitignore` que creamos, cualquier entorno virtual (`venv`), archivo `.env` o caché de Python será omitido automáticamente.

## 2. Conectar el proyecto a Streamlit Cloud
1. Entra a [share.streamlit.io](https://share.streamlit.io/) e inicia sesión (puedes usar tu cuenta de GitHub).
2. Haz clic en el botón **"Create app"** y luego selecciona **"Yep, I have an app"**.
3. Te pedirá permisos para conectar con tu cuenta de GitHub. Autorízalo.
4. En el formulario de despliegue, llena lo siguiente:
   - **Repository:** Busca y selecciona el repositorio que acabas de crear (ej. `TU_USUARIO/datascout-app`).
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. **Aún no hagas clic en "Deploy".** Falta configurar la API Key.

## 3. Configurar el Secret (GEMINI_API_KEY)
> [!IMPORTANT]  
> La API Key **NUNCA** debe estar en el código fuente ni subirse a GitHub. Para que tu aplicación funcione en la nube, debes pasarle la API Key de forma segura a través del panel de configuración de secretos de Streamlit.

1. En la misma pantalla del paso anterior, en la parte inferior derecha, haz clic en **"Advanced settings..."**.
2. Verás un recuadro llamado **"Secrets"**. Aquí puedes pegar variables que la aplicación leerá como si fuera un archivo de configuración segura.
3. Escribe tu API Key con este formato exacto:

```toml
GEMINI_API_KEY = "AIzaSy..."
```
*(Asegúrate de pegar tu key real dentro de las comillas).*

4. Haz clic en **"Save"**.
5. Ahora sí, haz clic en el botón azul **"Deploy!"**.

Streamlit instalará los paquetes de `requirements.txt` y en unos minutos tu aplicación estará viva en una URL pública, ¡lista para que cualquier persona la pruebe!
