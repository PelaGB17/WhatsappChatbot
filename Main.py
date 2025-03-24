import random
import schedule
import time
import threading
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from config import (
    AEMET_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER, 
    DEST_NUMBER, CALENDAR_LIST, DEFAULT_LOCATION, DEFAULT_MUNICIPALITY, 
    DEFAULT_USER_NAME, GREETING_EMOJIS, DAILY_UPDATE_TIME, FLASK_HOST, 
    FLASK_PORT, DEBUG_MODE, TOKEN_CHECK_INTERVAL
)
from Weather import Weather
from Calendar import Calendar
from logging_config import setup_logger
from state_management import (
    load_state, update_last_run_time, get_last_run_time, 
    update_location, get_location
)

# Configurar logger
logger = setup_logger(__name__)

class Main:
    
    def __init__(self) -> None:
        """Inicializa la aplicación principal"""
        logger.info("Iniciando aplicación...")
        
        # Inicializar Flask
        self.app = Flask(__name__)

        # Cargar estado o usar valores por defecto
        self.current_location, self.current_municipality = get_location()
        if not self.current_location:
            self.current_location = DEFAULT_LOCATION
            self.current_municipality = DEFAULT_MUNICIPALITY
            update_location(DEFAULT_MUNICIPALITY, DEFAULT_LOCATION)
            
        self.user_name = DEFAULT_USER_NAME
        
        # Verificar credenciales
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            logger.error("Faltan credenciales de Twilio")
            raise ValueError("Se requieren credenciales de Twilio")
            
        # Inicializar cliente de Twilio
        try:
            self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            self.to = DEST_NUMBER
            self._from = TWILIO_NUMBER
        except Exception as e:
            logger.error(f"Error al inicializar Twilio: {e}")
            raise
  
        # Emojis para saludo aleatorio
        self.emojis = GREETING_EMOJIS
        
        # Inicializar componentes
        try:
            self.calendar = Calendar(CALENDAR_LIST)
            self.weather = Weather(AEMET_API_KEY)
        except Exception as e:
            logger.error(f"Error al inicializar componentes: {e}")
            raise

        # Lock para evitar duplicados
        self.scheduler_lock = threading.Lock()

        # Programar el envío diario
        schedule.every().day.at(DAILY_UPDATE_TIME).do(self.safe_send_daily_update)
        logger.info(f"Programador configurado para las {DAILY_UPDATE_TIME}")
        
        # Programar verificación del token cada n minutos
        schedule.every(TOKEN_CHECK_INTERVAL).minutes.do(self.check_and_refresh_token)
        logger.info(f"Scheduler de renovación de token configurado cada {TOKEN_CHECK_INTERVAL} minutos")

        # Definir rutas de Flask
        self.setup_routes()
        logger.info("Aplicación iniciada correctamente")

    def check_and_refresh_token(self):
        """Verifica y renueva el token de Google Calendar"""
        try:
            logger.info("Verificando estado del token...")
            result = self.calendar.check_and_refresh_token()
            if result:
                logger.info("Token verificado correctamente")
            else:
                logger.warning("No se pudo verificar el token")
            return result
        except Exception as e:
            logger.error(f"Error al actualizar token desde Main: {e}")
            return False
            
    def send_message(self, body):
        """Envía un mensaje por WhatsApp"""
        try:
            self.client.messages.create(
                from_=self._from,
                body=body,
                to=self.to
            )
            logger.info(f"Mensaje enviado a {self.to}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar mensaje: {e}")
            return False
    
    def safe_send_daily_update(self):
        """Método seguro para envío diario que evita duplicados"""
        with self.scheduler_lock:
            current_time = time.time()
            last_run_time = get_last_run_time()
            
            if not last_run_time or current_time - last_run_time > 86400:
                logger.info("Iniciando envío de actualización diaria")
                self.send_daily_update()
                update_last_run_time()
                return True
            else:
                logger.info("Actualización ya enviada hoy")
                return False

    def send_daily_update(self):
        """Envía actualización diaria de clima y eventos"""
        try:
            # Verificar y refrescar token si es necesario
            self.check_and_refresh_token()
            
            events, birthdays, all_day_events = self.calendar.get_calendar_events()
            
            weather = self.weather.get_weather_from_aemet(self.current_location)
            if not weather:
                logger.error("No se pudo obtener pronóstico")
                return False
            
            # Mensaje 1: Buenos días
            emoji = random.choice(self.emojis)
            message_1 = f"Buenos días {self.user_name}!! {emoji}"
            if not self.send_message(message_1):
                return False
            
            # Mensaje 2: El tiempo
            lluvia_text = ', '.join(weather['intervalos_lluvia']) if weather['intervalos_lluvia'] else 'No hay probabilidad de lluvia'
            message_2 = (f"El tiempo del día en {self.current_municipality} es {emoji}:\n\n"
                         f"Madrugada 🌄: {weather['madrugada']}\n"
                         f"Mañana 🌅: {weather['mañana']}\n"
                         f"Tarde 🌇: {weather['tarde']}\n"
                         f"Noche 🌆: {weather['noche']}\n\n"
                         f"Probabilidad de lluvia en intervalos 🌧️: {lluvia_text}")
            if not self.send_message(message_2):
                return False
            
            # Mensaje 3: Eventos
            message_3 = "Tus eventos del día son 🗒️:\n"
            if events:
                for event in events:
                    message_3 += f"{event}\n"
            else:
                message_3 += "No tienes eventos programados para hoy.\n"
                
            if birthdays:
                message_3 += "\n" + "\n".join(birthdays)
            if all_day_events:
                message_3 += "\n" + "\n".join(all_day_events)
                
            return self.send_message(message_3)
            
        except Exception as e:
            logger.error(f"Error en actualización diaria: {e}")
            return False

    def setup_routes(self):
        """Configura rutas de Flask"""
        
        @self.app.route('/whatsapp', methods=['POST'])
        def whatsapp_reply():
            try:
                incoming_msg = request.values.get('Body', '').strip().lower()
                resp = MessagingResponse()
                msg = resp.message()

                logger.info(f"Mensaje recibido: {incoming_msg}")

                # Tiempo
                if 'tiempo' in incoming_msg:
                    if self.current_location:
                        weather = self.weather.get_weather_from_aemet(self.current_location)
                        
                        if weather:
                            lluvia_text = ', '.join(weather['intervalos_lluvia']) if weather['intervalos_lluvia'] else 'No hay probabilidad'
                            msg.body(f"El tiempo del día en {self.current_municipality} es:\n\n"
                                    f"Madrugada 🌄: {weather['madrugada']}\n"
                                    f"Mañana 🌅: {weather['mañana']}\n"
                                    f"Tarde 🌇: {weather['tarde']}\n"
                                    f"Noche 🌆: {weather['noche']}\n\n"
                                    f"Probabilidad de lluvia 🌧️: {lluvia_text}")
                        else:
                            msg.body("Hubo un problema al obtener el pronóstico. Intenta más tarde.")
                    else:
                        msg.body("No hay ubicación establecida. Usa 'cambiar ubicación'.")

                # Eventos
                elif 'eventos' in incoming_msg:
                    try:
                        # Verificar y refrescar token si es necesario
                        self.check_and_refresh_token()
                        
                        events, birthdays, all_day_events = self.calendar.get_calendar_events()

                        message = "Tus eventos del día son:\n"
                        if events:
                            for event in events:
                                message += f"{event}\n"
                        else:
                            message += "No tienes eventos hoy.\n"
                        
                        if birthdays:
                            message += "\n" + "\n".join(birthdays)
                        
                        if all_day_events:
                            message += "\n" + "\n".join(all_day_events)

                        msg.body(message)
                    except Exception as e:
                        logger.error(f"Error al obtener eventos: {e}")
                        msg.body("Hubo un problema al obtener tus eventos. Intenta más tarde.")

                # Cambiar ubicación
                elif 'cambiar ubicación' in incoming_msg:
                    msg.body("Escribe el nombre de tu municipio para actualizar la ubicación.")
                
                # Renovar token manualmente
                elif 'renovar token' in incoming_msg:
                    try:
                        if self.check_and_refresh_token():
                            msg.body("Token de Google Calendar verificado/renovado correctamente.")
                        else:
                            msg.body("No se pudo renovar el token. Es posible que necesites reautenticarte.")
                    except Exception as e:
                        logger.error(f"Error al renovar token manualmente: {e}")
                        msg.body("Error al intentar renovar el token.")
                
                # Nombre de municipio
                elif incoming_msg.replace(" ", "").isalpha():
                    try:
                        new_location = self.weather.get_municipio_code(incoming_msg.title())
                        
                        if new_location:
                            self.current_municipality = incoming_msg.title()
                            self.current_location = new_location
                            update_location(self.current_municipality, self.current_location)
                            msg.body(f"Ubicación actualizada a {self.current_municipality}, código {self.current_location}.")
                        else:
                            msg.body("No se ha encontrado el municipio, intenta de nuevo.")
                    except Exception as e:
                        logger.error(f"Error al cambiar ubicación: {e}")
                        msg.body("Hubo un problema al actualizar la ubicación. Intenta más tarde.")

                else:
                    msg.body("Lo siento, no entiendo tu mensaje. Prueba con 'tiempo', 'eventos', 'renovar token' o 'cambiar ubicación'.")

                return str(resp)
            except Exception as e:
                logger.error(f"Error al procesar mensaje: {e}")
                resp = MessagingResponse()
                resp.message("Ha ocurrido un error. Inténtalo más tarde.")
                return str(resp)

    def run_scheduler(self):
        """Ejecuta el programador de tareas"""
        logger.info("Iniciando programador")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except Exception as e:
            logger.error(f"Error en programador: {e}")
            raise

def main():
    """Función principal"""
    try:
        app = Main()
        
        # Hilo para el programador
        scheduler_thread = threading.Thread(target=app.run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Iniciar Flask
        logger.info(f"Iniciando servidor en {FLASK_HOST}:{FLASK_PORT}")
        app.app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG_MODE)
    except Exception as e:
        logger.critical(f"Error fatal: {e}")
        raise

if __name__ == '__main__':
    main()
