import os
import random
import schedule
import time
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from Weather import Weather
from Calendar import Calendar

import threading  # Añadido para manejar tareas en paralelo

class Main():
    
    def __init__(self) -> None:
        self.app = Flask(__name__)

        # Variables globales
        self.current_location = '28079'  # Ubicación por defecto
        self.current_municipality = "Madrid"
        self.user_name = 'Pelayo'  # Nombre del usuario

        # Claves de AEMET y Twilio ahora se leen desde variables de entorno
        AEMET_API_KEY = os.getenv('AEMET_API_KEY')
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        calendars_env = os.getenv('CALENDAR_LIST')
        self.to = os.getenv('DEST_NUMBER')
        self._from = os.getenv('TWILIO_NUMBER')
  
        self.client = Client(account_sid, auth_token)

        # Lista de emoticonos para saludo aleatorio
        self.emojis = ['😊', '🌞', '🌻', '🌅', '☀️', '✨', '😎', '🤩', '🔥', '🌈', '⭐', '💫', '🌺']
        
        self.calendar = Calendar(calendars_env)
        self.weather = Weather(AEMET_API_KEY)

        # Lock para evitar duplicados
        self.scheduler_lock = threading.Lock()

        # Programar el envío diario a las 7:30 AM
        schedule.every().day.at("09:30").do(self.safe_send_daily_update)

        # Definir rutas de Flask dentro del constructor
        self.setup_routes()

    # Función para enviar un mensaje a WhatsApp
    def send_message(self, body):
        self.client.messages.create(
            from_=self._from,  # Número de Twilio
            body=body,
            to=self.to
        )
    
    # Método seguro para el envío diario
    def safe_send_daily_update(self):
        with self.scheduler_lock:
            self.send_daily_update()

    # Función para enviar la actualización diaria de clima y eventos
    def send_daily_update(self):
        # Obtener los eventos y cumpleaños
        events, birthdays, all_day_events = self.calendar.get_calendar_events()
        
        # Obtener el pronóstico del tiempo
        weather = self.weather.get_weather_from_aemet(self.current_location)
        
        # Mensaje 1: Buenos días con emoji aleatorio
        emoji = random.choice(self.emojis)
        message_1 = f"Buenos días {self.user_name}!! {emoji}"
        self.send_message(message_1)
        
        # Mensaje 2: El tiempo del día
        message_2 = (f"El tiempo del día en {self.current_municipality} es {emoji}:\n\n"
                     f"Madrugada 🌄: {weather['madrugada']}\n"
                     f"Mañana 🌅: {weather['mañana']}\n"
                     f"Tarde 🌇: {weather['tarde']}\n"
                     f"Noche 🌆: {weather['noche']}\n\n"
                     f"Probabilidad de lluvia en intervalos 🌧️: {', '.join(weather['intervalos_lluvia'])}")
        self.send_message(message_2)
        
        # # Mensaje 3: Tus eventos del día
        message_3 = "Tus eventos del día son 🗒️:\n"
        for event in events:
            message_3 += f"{event}\n"
        if birthdays:
            message_3 += "\n" + "\n".join(birthdays)
        if all_day_events:
            message_3 += "\n" + "\n".join(all_day_events)
        self.send_message(message_3)

    # Configuración de rutas de Flask
    def setup_routes(self):
        @self.app.route('/whatsapp', methods=['POST'])
        def whatsapp_reply():
            incoming_msg = request.values.get('Body', '').strip().lower()
            resp = MessagingResponse()
            msg = resp.message()

            # Solicitar el pronóstico del tiempo
            if 'tiempo' in incoming_msg:
                if self.current_location:
                    # Obtener el tiempo del municipio actual
                    weather = self.weather.get_weather_from_aemet(self.current_location)
                    
                    if weather:
                        # Si la API devuelve el tiempo, envía el mensaje
                        msg.body(f"El tiempo del día en {self.current_municipality} es:\n\n"
                                f"Madrugada 🌄: {weather['madrugada']}\n"
                                f"Mañana 🌅: {weather['mañana']}\n"
                                f"Tarde 🌇: {weather['tarde']}\n"
                                f"Noche 🌆: {weather['noche']}\n\n"
                                f"Probabilidad de lluvia en intervalos 🌧️: {', '.join(weather['intervalos_lluvia'])}")
                    else:
                        # Si hay algún error con la API
                        msg.body("Hubo un problema al obtener el pronóstico del tiempo. Intenta nuevamente más tarde.")
                else:
                    msg.body("No se ha establecido ninguna ubicación. Usa 'cambiar ubicación' para actualizarla.")

            # Solicitar los eventos del día
            elif 'eventos' in incoming_msg:
                events, birthdays, all_day_events = self.calendar.get_calendar_events()

                # Mensaje con los eventos del día
                message = "Tus eventos del día son:\n"
                if events:
                    for event in events:
                        message += f"{event}\n"
                else:
                    message += "No tienes eventos hoy.\n"
                
                # Añadir cumpleaños si hay
                if birthdays:
                    message += "\n".join(birthdays)
                
                # Añadir eventos de todo el día si hay
                if all_day_events:
                    message += "\n".join(all_day_events)

                # Enviar el mensaje de eventos
                msg.body(message)

            # Cambiar la ubicación del tiempo
            elif 'cambiar ubicación' in incoming_msg:
                msg.body("Escribe el nombre de tu municipio para actualizar la ubicación.")
            
            # Verificar si el mensaje es un nombre de municipio (después de procesar palabras clave)
            elif incoming_msg.replace(" ", "").isalpha():
                new_location = self.weather.get_municipio_code(incoming_msg.title())  # Usar title() para manejar mayúsculas/minúsculas
                
                if new_location:
                    self.current_municipality = incoming_msg.title()
                    self.current_location = new_location
                    msg.body(f"Ubicación actualizada a {self.current_municipality}, código {self.current_location}.")
                else:
                    # Si no se encuentra el municipio
                    msg.body("No se ha encontrado el municipio, intenta de nuevo o verifica el nombre correctamente.")

            else:
                # Respuesta predeterminada si no se reconoce el mensaje
                msg.body("Lo siento, no he entendido tu mensaje. Intenta usar 'tiempo', 'eventos' o 'cambiar ubicación'.")

            return str(resp)


    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == '__main__':
    main = Main()

    # Crear un hilo separado para el programador
    scheduler_thread = threading.Thread(target=main.run_scheduler)
    scheduler_thread.start()

    # Iniciar el servidor Flask
    main.app.run(host='0.0.0.0', port=5000, debug=True)
