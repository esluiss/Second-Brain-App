import os

# 1. Obtenemos la ruta exacta de tu proyecto, sin importar la computadora
# Esto retrocede dos pasos desde config.py -> app -> Second_Brain
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Definimos dónde debe estar la carpeta 'data'
DATA_DIR = os.path.join(BASE_DIR, "data")

# 3. LA MAGIA: Si la carpeta 'data' no existe en la PC de tu compañero, la crea automáticamente
os.makedirs(DATA_DIR, exist_ok=True)

class Config:
    # 4. Le decimos a SQLite que guarde el archivo brain.db dentro de esa carpeta
    DB_PATH = os.path.join(DATA_DIR, "brain.db")

    # 5. Clave de Groq (https://console.groq.com/keys) para el Asistente IA.
    #    ★ PON TU CLAVE AQUÍ ABAJO (reemplaza el texto entre comillas) ★
    #    No edites core/groq_assistant.py — este es el único lugar necesario.
    #    Prioridad: variable de entorno GROQ_API_KEY > este valor.
    #    No subas este archivo con tu clave real a un repositorio público.
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "tu_clave_aquí")
