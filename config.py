import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración común
TIMEZONE = 'Europe/Madrid'
DEFAULT_LOCATION = '28079'  # Madrid por defecto
DEFAULT_MUNICIPALITY = 'Madrid'
DEFAULT_USER_NAME = 'Pelayo'

# API keys y credenciales
AEMET_API_KEY = os.getenv('AEMET_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_NUMBER')
DEST_NUMBER = os.getenv('DEST_NUMBER')
CALENDAR_LIST = os.getenv('CALENDAR_LIST')

# Configuración de la aplicación
FLASK_HOST = '0.0.0.0'
FLASK_PORT = int(os.getenv('PORT', 5000))
DEBUG_MODE = os.getenv('ENVIRONMENT', 'development') != 'production'

# Hora de actualización diaria
DAILY_UPDATE_TIME = "09:30"

# Emojis para saludos
GREETING_EMOJIS = ['😊', '🌞', '🌻', '🌅', '☀️', '✨', '😎', '🤩', '🔥', '🌈', '⭐', '💫', '🌺']

# Rutas de archivos
MUNICIPALITIES_FILE = 'data/municipios.xlsx'
TOKEN_FILE = 'credentials/token.json'
CREDENTIALS_FILE = 'credentials/credentials.json'
STATE_FILE = 'data/app_state.json'

# Configuración para renovación de token
TOKEN_CHECK_INTERVAL = 20  # minutos
