import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from dateutil import parser
import pytz

class Calendar:
    def __init__(self, calendars_env) -> None:
        self.calendars_env = calendars_env

    def get_credentials(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        # Comprobar si existe el archivo token.json
        if os.path.exists('token.json'):
            # Cargar credenciales desde token.json
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            # Si el token ha caducado, renovarlo
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Guardar el token renovado en token.json
                with open('token.json', 'w') as token_file:
                    token_file.write(creds.to_json())
                    
        else:
            # Si no existe token.json, iniciar el flujo de autenticación
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Guardar el nuevo token en token.json
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())

        return creds

    @staticmethod
    def format_event_time(iso_time):
        """Convierte un formato de tiempo ISO a formato de solo horas y minutos."""
        try:
            dt = parser.isoparse(iso_time)
            return dt.strftime("%H:%M")
        except Exception as e:
            print(f"Error al formatear la hora: {e}")
            return iso_time

    @staticmethod
    def get_emoji_for_color(color_id):
        """Obtiene el emoticono según el color_id."""
        COLOR_EMOJI_MAP = {
            '1': '🔴',  # Rojo
            '2': '🟠',  # Naranja
            '3': '🟡',  # Amarillo
            '4': '🟢',  # Verde
            '5': '🔵',  # Azul claro
            '6': '🔷',  # Azul oscuro
            '7': '🟣',  # Púrpura
            '8': '🟤',  # Marrón
            '9': '⚫',  # Negro
            '10': '⚪', # Blanco
            '11': '🟡', # Dorado
        }
        return COLOR_EMOJI_MAP.get(color_id, '🔘')  # '🔘' por defecto si el color no está en el mapa

    def get_calendar_events(self):
        """Obtiene los eventos del calendario para el día actual."""
        if not self.calendars_env:
            raise ValueError("La variable de entorno 'CALENDARS' no está definida")
        
        # Convertir la cadena en una lista de nombres de calendarios
        calendar_names = [name.strip() for name in self.calendars_env.split(',')]
        
        # Autenticación con Google Calendar
        creds = self.get_credentials()
        service = build('calendar', 'v3', credentials=creds)

        # Obtener el inicio y fin del día en la hora local
        local_tz = pytz.timezone('Europe/Madrid')  # Cambia esto por tu zona horaria si es diferente
        now = datetime.now(local_tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

        event_list = []
        birthday_list = []
        all_day_events = []

        # Listar todos los calendarios disponibles en la cuenta
        calendar_list = service.calendarList().list().execute()
        available_calendars = calendar_list.get('items', [])

        # Buscar IDs de los calendarios a partir de los nombres proporcionados
        calendar_ids = {}
        calendar_colors = {}
        for calendar in available_calendars:
            calendar_name = calendar.get('summary')
            if calendar_name in calendar_names:
                calendar_ids[calendar_name] = calendar.get('id')
                calendar_colors[calendar_name] = calendar.get('colorId')  # Obtener el colorId

        if not calendar_ids:
            raise ValueError("No se encontraron calendarios coincidentes con los nombres proporcionados.")
        
        # Obtener eventos de los calendarios indicados
        for calendar_name, calendar_id in calendar_ids.items():
            color_emoji = self.get_emoji_for_color(calendar_colors[calendar_name])  # Obtener el emoji para este calendario
            try:
                events_result = service.events().list(
                    calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day,
                    maxResults=10, singleEvents=True, orderBy='startTime').execute()
                events = events_result.get('items', [])
            except Exception as e:
                print(f"Error al obtener eventos de {calendar_name}: {e}")
                continue  # Continuar al siguiente calendario si hay un error

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                summary = event['summary']

                # Añadir eventos con formato y hora
                if event.get('start').get('dateTime') and event.get('end').get('dateTime'):
                    start_formatted = self.format_event_time(start)
                    end_formatted = self.format_event_time(end)
                    event_list.append({
                        'start': start,  # Guardar el tiempo de inicio original para ordenar
                        'description': f"{color_emoji} De {start_formatted} a {end_formatted}: {summary}"
                    })
                
                # Eventos de todo el día (excluyendo cumpleaños)
                if event.get('start').get('date') and calendar_name.lower() != "cumpleaños":
                    all_day_events.append(f"{color_emoji} Hoy es el día de {summary}")

        # Obtener cumpleaños si "cumpleaños" está en los calendarios seleccionados
        if "Cumpleaños" in calendar_ids:
            try:
                birthdays_result = service.events().list(
                    calendarId=calendar_ids["Cumpleaños"], timeMin=start_of_day, timeMax=end_of_day,
                    maxResults=10, singleEvents=True, orderBy='startTime').execute()
                birthday_events = birthdays_result.get('items', [])

                for birthday in birthday_events:
                    birthday_list.append(f"🎂 Hoy es el cumpleaños de {birthday['summary']}")
            except Exception as e:
                print(f"Error al obtener cumpleaños: {e}")

        # Ordenar los eventos por el tiempo de inicio
        event_list.sort(key=lambda x: x['start'])

        # Retornar todos los eventos ordenados por tiempo
        sorted_events = [event['description'] for event in event_list]
        
        return sorted_events, birthday_list, all_day_events