import os
import json
import logging
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from dateutil import parser
import pytz
from config import TIMEZONE, TOKEN_FILE, CREDENTIALS_FILE
from logging_config import setup_logger

# Configurar logger
logger = setup_logger(__name__)

class Calendar:
    def __init__(self, calendars_env) -> None:
        """Inicializa la clase Calendar"""
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        
        if not calendars_env:
            logger.error("Lista de calendarios vacía")
            raise ValueError("No se ha definido la variable CALENDAR_LIST")
            
        self.calendars_env = calendars_env
        # Crear directorio para credenciales
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

    def get_credentials(self):
        """Obtiene credenciales para Google Calendar API"""
        try:
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, self.SCOPES)
                
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(TOKEN_FILE, 'w') as token_file:
                        token_file.write(creds.to_json())
                        
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(f"No se encontró {CREDENTIALS_FILE}")
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, 
                    self.SCOPES,
                    # Parámetros para obtener un refresh_token de larga duración
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                    access_type='offline',
                    prompt='consent'  # Fuerza la obtención del refresh_token
                )
                creds = flow.run_local_server(port=0)
                
                with open(TOKEN_FILE, 'w') as token_file:
                    token_file.write(creds.to_json())

            return creds
            
        except Exception as e:
            logger.error(f"Error de autenticación: {e}")
            raise

    def check_and_refresh_token(self):
        """Verifica y renueva el token si está próximo a expirar"""
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                
                # Verificar si el token expirará pronto (en los próximos 30 minutos)
                expires_at = token_data.get('expires_at', 0)
                current_time = time.time()
                
                # Si expira en menos de 30 minutos, renovarlo
                if expires_at - current_time < 1800:
                    logger.info("Token próximo a expirar, renovando...")
                    refresh_token = token_data.get('refresh_token')
                    
                    if refresh_token:
                        # Usar el refresh_token para obtener un nuevo token
                        creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
                        creds.refresh(Request())
                        
                        # Guardar el nuevo token
                        with open(TOKEN_FILE, 'w') as token:
                            token.write(creds.to_json())
                        logger.info("Token renovado correctamente")
                        return True
                    else:
                        logger.error("No hay refresh_token disponible")
                        return False
                return True  # Token válido y no próximo a expirar
            else:
                logger.warning("No existe el archivo token.json")
                return False
        except Exception as e:
            logger.error(f"Error al verificar/renovar token: {e}")
            return False

    @staticmethod
    def format_event_time(iso_time):
        """Convierte tiempo ISO a formato HH:MM"""
        try:
            dt = parser.isoparse(iso_time)
            return dt.strftime("%H:%M")
        except Exception as e:
            logger.error(f"Error al formatear hora: {e}")
            return iso_time

    @staticmethod
    def get_emoji_for_color(color_id):
        """Devuelve emoji según color_id"""
        COLOR_EMOJI_MAP = {
            '1': '🔴', '2': '🟠', '3': '🟡', '4': '🟢', '5': '🔵',
            '6': '🔷', '7': '🟣', '8': '🟤', '9': '⚫', '10': '⚪', '11': '🟡'
        }
        return COLOR_EMOJI_MAP.get(color_id, '🔘')

    def get_calendar_events(self, timezone=TIMEZONE):
        """Obtiene eventos del calendario para hoy"""
        # Primero verificar y refrescar el token si es necesario
        if not self.check_and_refresh_token():
            logger.warning("No se pudo verificar/refrescar el token")
            
        try:
            calendar_names = [name.strip() for name in self.calendars_env.split(',')]
            
            creds = self.get_credentials()
            service = build('calendar', 'v3', credentials=creds)

            local_tz = pytz.timezone(timezone)
            now = datetime.now(local_tz)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

            event_list = []
            birthday_list = []
            all_day_events = []

            calendar_list = service.calendarList().list().execute()
            available_calendars = calendar_list.get('items', [])

            calendar_ids = {}
            calendar_colors = {}
            for calendar in available_calendars:
                calendar_name = calendar.get('summary')
                if calendar_name in calendar_names:
                    calendar_ids[calendar_name] = calendar.get('id')
                    calendar_colors[calendar_name] = calendar.get('colorId')

            if not calendar_ids:
                logger.error("No se encontraron calendarios coincidentes")
                raise ValueError("No se encontraron calendarios coincidentes")
            
            for calendar_name, calendar_id in calendar_ids.items():
                color_emoji = self.get_emoji_for_color(calendar_colors.get(calendar_name))
                try:
                    events_result = service.events().list(
                        calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day,
                        maxResults=10, singleEvents=True, orderBy='startTime').execute()
                    events = events_result.get('items', [])
                    
                    for event in events:
                        start = event['start'].get('dateTime', event['start'].get('date'))
                        end = event['end'].get('dateTime', event['end'].get('date'))
                        summary = event['summary']

                        if event.get('start').get('dateTime') and event.get('end').get('dateTime'):
                            start_formatted = self.format_event_time(start)
                            end_formatted = self.format_event_time(end)
                            event_list.append({
                                'start': start,
                                'description': f"{color_emoji} De {start_formatted} a {end_formatted}: {summary}"
                            })
                        
                        if event.get('start').get('date') and calendar_name.lower() != "cumpleaños":
                            all_day_events.append(f"{color_emoji} Hoy es el día de {summary}")
                            
                except Exception as e:
                    logger.error(f"Error al obtener eventos de {calendar_name}: {e}")
                    continue

            if "Cumpleaños" in calendar_ids:
                try:
                    birthdays_result = service.events().list(
                        calendarId=calendar_ids["Cumpleaños"], timeMin=start_of_day, timeMax=end_of_day,
                        maxResults=10, singleEvents=True, orderBy='startTime').execute()
                    birthday_events = birthdays_result.get('items', [])

                    for birthday in birthday_events:
                        birthday_list.append(f"🎂 Hoy es el cumpleaños de {birthday['summary']}")
                except Exception as e:
                    logger.error(f"Error al obtener cumpleaños: {e}")

            event_list.sort(key=lambda x: x['start'])
            sorted_events = [event['description'] for event in event_list]
            
            return sorted_events, birthday_list, all_day_events
            
        except Exception as e:
            logger.error(f"Error al obtener eventos: {e}")
            return [], [], []
