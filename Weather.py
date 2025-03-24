import os
import requests
import pandas as pd
import logging
from config import MUNICIPALITIES_FILE
from logging_config import setup_logger

# Configurar logger
logger = setup_logger(__name__)

class Weather:
    def __init__(self, AEMET_API_KEY) -> None:
        """Inicializa la clase Weather"""
        if not AEMET_API_KEY:
            logger.error("API key de AEMET no proporcionada")
            raise ValueError("Se requiere AEMET_API_KEY")
            
        self.AEMET_API_KEY = AEMET_API_KEY
        
        # Crear directorio para el archivo de municipios
        os.makedirs(os.path.dirname(MUNICIPALITIES_FILE), exist_ok=True)

    def load_excel(self):
        """Carga el Excel de municipios"""
        try:
            if not os.path.exists(MUNICIPALITIES_FILE):
                logger.error(f"No se encontró {MUNICIPALITIES_FILE}")
                raise FileNotFoundError(f"No se encontró {MUNICIPALITIES_FILE}")
                
            return pd.read_excel(MUNICIPALITIES_FILE)
        except Exception as e:
            logger.error(f"Error al cargar Excel: {e}")
            raise

    def get_municipio_code(self, municipality_name):
        """Obtiene el código del municipio"""
        if not municipality_name:
            logger.error("Nombre de municipio vacío")
            return None
            
        try:
            df = self.load_excel()
            df = df.iloc[2:, :]  # Ignorar primeras dos filas
            row = df[df.iloc[:, 4] == municipality_name]

            if not row.empty:
                code = str(row.iloc[0, 1]) + str(row.iloc[0, 2])
                logger.info(f"Código para {municipality_name}: {code}")
                return code
                
            logger.warning(f"No se encontró código para: {municipality_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error al buscar municipio: {e}")
            return None

    def get_weather_from_aemet(self, municipality_code):
        """Obtiene pronóstico desde API AEMET"""
        if not municipality_code:
            logger.error("Código de municipio vacío")
            return None
            
        try:
            url = f'https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipality_code}'
            headers = {
                'accept': 'application/json',
                'api_key': self.AEMET_API_KEY
            }
            
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                logger.error(f"Error API AEMET: {response.status_code} - {response.text}")
                return None
                
            data = response.json()
            datos_prediccion_url = data['datos']
            prediccion_response = requests.get(datos_prediccion_url)

            if prediccion_response.status_code != 200:
                logger.error(f"Error datos predicción: {prediccion_response.status_code}")
                return None
            
            prediccion_data = prediccion_response.json()
            return self.procesar_datos_prediccion(prediccion_data)
            
        except Exception as e:
            logger.error(f"Error al obtener datos del tiempo: {e}")
            return None

    def procesar_datos_prediccion(self, prediccion_data):
        """Procesa datos de predicción"""
        try:
            dia = prediccion_data[0]['prediccion']['dia'][0]

            tiempo_madrugada = "No disponible"
            tiempo_manana = "No disponible"
            tiempo_tarde = "No disponible"
            tiempo_noche = "No disponible"
            
            if 'estadoCielo' in dia and len(dia['estadoCielo']) >= 4:
                estado_cielo = dia['estadoCielo'][-4:]
            else:
                estado_cielo = dia['estadoCielo']

            for estado in estado_cielo:
                periodo = estado['periodo']
                descripcion = estado['descripcion']

                if "00-06" in periodo:
                    tiempo_madrugada = descripcion
                elif "06-12" in periodo:
                    tiempo_manana = descripcion
                elif "12-18" in periodo:
                    tiempo_tarde = descripcion
                elif "18-24" in periodo:
                    tiempo_noche = descripcion

            prob_lluvia = dia['probPrecipitacion'][-4:]
            intervalos_lluvia = []

            for prob in prob_lluvia:
                if int(prob['value']) > 50:
                    intervalos_lluvia.append(prob['periodo'])

            intervalos_consolidados = self.consolidar_intervalos(intervalos_lluvia)

            return {
                "madrugada": tiempo_madrugada,
                "mañana": tiempo_manana,
                "tarde": tiempo_tarde,
                "noche": tiempo_noche,
                "intervalos_lluvia": intervalos_consolidados
            }
            
        except Exception as e:
            logger.error(f"Error al procesar predicción: {e}")
            return {
                "madrugada": "Error al procesar datos",
                "mañana": "Error al procesar datos",
                "tarde": "Error al procesar datos",
                "noche": "Error al procesar datos",
                "intervalos_lluvia": []
            }

    def consolidar_intervalos(self, intervalos):
        """Consolida intervalos consecutivos"""
        try:
            if not intervalos:
                return []
                
            intervalos.sort()
            intervalos_consolidados = []
            intervalo_actual = None

            for intervalo in intervalos:
                inicio, fin = intervalo.split('-')

                if not intervalo_actual:
                    intervalo_actual = {"inicio": inicio, "fin": fin}
                elif intervalo_actual["fin"] == inicio:
                    intervalo_actual["fin"] = fin
                else:
                    intervalos_consolidados.append(f"{intervalo_actual['inicio']}-{intervalo_actual['fin']}")
                    intervalo_actual = {"inicio": inicio, "fin": fin}

            if intervalo_actual:
                intervalos_consolidados.append(f"{intervalo_actual['inicio']}-{intervalo_actual['fin']}")

            return intervalos_consolidados
            
        except Exception as e:
            logger.error(f"Error al consolidar intervalos: {e}")
            return []
