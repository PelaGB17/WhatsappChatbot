import requests
import pandas as pd

class Weather():
    def __init__(self, AEMET_API_KEY) -> None:
        self.AEMET_API_KEY = AEMET_API_KEY

    @staticmethod
    def load_excel():
        # Ajusta la ruta del archivo según sea necesario
        return pd.read_excel('municipios.xlsx')

    def get_municipio_code(self, municipality_name):
        df = self.load_excel()

        # Filtramos las filas a partir de la fila 3 (ignorar las dos primeras)
        self.df = df.iloc[2:, :]  # Ignorar las primeras dos filas
        row = df[df.iloc[:, 4] == municipality_name]  # La columna E es el índice 4 (contando desde 0)

        if not row.empty:
            # Concatenar las columnas C (índice 2) y D (índice 3)
            return str(row.iloc[0, 1]) + str(row.iloc[0, 2])  # Cambiado el orden a C y D
        return None

    def get_weather_from_aemet(self, municipality_code):
        url = f'https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipality_code}'
        headers = {
            'accept': 'application/json',
            'api_key': self.AEMET_API_KEY
        }
        
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Error al obtener datos: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        datos_prediccion_url = data['datos']  # URL con los datos en crudo
        prediccion_response = requests.get(datos_prediccion_url)

        if prediccion_response.status_code != 200:
            print(f"Error al obtener datos de predicción: {prediccion_response.status_code} - {prediccion_response.text}")
            return None
        
        # Obtener los datos en crudo
        prediccion_data = prediccion_response.json()
        
        # Procesamos los datos para extraer las predicciones
        prediccion = self.procesar_datos_prediccion(prediccion_data)
        return prediccion

    def procesar_datos_prediccion(self, prediccion_data):
        # Tomamos la predicción del primer día disponible
        dia = prediccion_data[0]['prediccion']['dia'][0]

        # Inicializar variables para las descripciones
        tiempo_madrugada = "No disponible"
        tiempo_manana = "No disponible"
        tiempo_tarde = "No disponible"
        tiempo_noche = "No disponible"
        
        # Verificar si 'estadoCielo' existe y tiene al menos 4 elementos
        if 'estadoCielo' in dia and len(dia['estadoCielo']) >= 4:
            # Obtener los últimos cuatro estados del cielo
            estado_cielo = dia['estadoCielo'][-4:]
        else:
            # Si no hay suficientes datos, tomar toda la lista
            estado_cielo = dia['estadoCielo']

        # Asignar valores a cada variable según el rango de periodo
        for estado in estado_cielo:
            periodo = estado['periodo']
            descripcion = estado['descripcion']

            # Comprobar el rango de periodo y asignar la descripción correspondiente
            if "00-06" in periodo:
                tiempo_madrugada = descripcion
            elif "06-12" in periodo:
                tiempo_manana = descripcion
            elif "12-18" in periodo:
                tiempo_tarde = descripcion
            elif "18-24" in periodo:
                tiempo_noche = descripcion

        # Comprobamos los períodos con más del 50% de probabilidad de lluvia
        prob_lluvia = dia['probPrecipitacion'][-4:]
        intervalos_lluvia = []

        for prob in prob_lluvia:
            if int(prob['value']) > 50:
                intervalos_lluvia.append(prob['periodo'])

        print(intervalos_lluvia)
                
        intervalos_consolidados = self.consolidar_intervalos(intervalos_lluvia)

        return {
            "madrugada": tiempo_madrugada,
            "mañana": tiempo_manana,
            "tarde": tiempo_tarde,
            "noche": tiempo_noche,
            "intervalos_lluvia": intervalos_consolidados
        }

    def consolidar_intervalos(self, intervalos):
        # Consolidar intervalos consecutivos
        intervalos_consolidados = []
        intervalo_actual = None

        for intervalo in intervalos:
            inicio, fin = intervalo.split('-')

            if not intervalo_actual:
                # Inicializa el primer intervalo
                intervalo_actual = {"inicio": inicio, "fin": fin}
            elif intervalo_actual["fin"] == inicio:
                # Si el intervalo es consecutivo, actualiza el fin del intervalo actual
                intervalo_actual["fin"] = fin
            else:
                # Si no es consecutivo, guarda el intervalo actual y empieza uno nuevo
                intervalos_consolidados.append(f"{intervalo_actual['inicio']}-{intervalo_actual['fin']}")
                intervalo_actual = {"inicio": inicio, "fin": fin}

        # Añadir el último intervalo consolidado
        if intervalo_actual:
            intervalos_consolidados.append(f"{intervalo_actual['inicio']}-{intervalo_actual['fin']}")

        return intervalos_consolidados