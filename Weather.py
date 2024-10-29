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
        url = f'https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{municipality_code}'
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
        
        # Obtener los últimos cuatro estados del cielo
        estado_cielo = dia['estadoCielo'][-4:] if len(dia['estadoCielo']) >= 4 else dia['estadoCielo']

        # Asignar descripciones a las variables según los intervalos
        for i, estado in enumerate(estado_cielo):
            if i == 0:
                tiempo_madrugada = estado['descripcion']  # 00-06
            elif i == 1:
                tiempo_manana = estado['descripcion']      # 06-12
            elif i == 2:
                tiempo_tarde = estado['descripcion']       # 12-18
            elif i == 3:
                tiempo_noche = estado['descripcion']       # 18-24

        # Comprobamos los períodos con más del 50% de probabilidad de lluvia
        prob_lluvia = dia['probPrecipitacion'][-4:] if len(dia['probPrecipitacion']) >= 4 else dia['probPrecipitacion']
        intervalos_lluvia = []

        for prob in prob_lluvia:
            if int(prob['value']) > 50:
                intervalos_lluvia.append(prob['periodo'])

        # Unir intervalos de tiempo consecutivos
        intervalos_consolidados = self.consolidar_intervalos(intervalos_lluvia)

        return {
            "madrugada": tiempo_madrugada,
            "mañana": tiempo_manana,
            "tarde": tiempo_tarde,
            "noche": tiempo_noche,
            "intervalos_lluvia": intervalos_consolidados
        }

    def consolidar_intervalos(self, intervalos):
        if not intervalos:  # Si la lista está vacía, retornamos vacío
            return []

        # Eliminar duplicados y ordenar los intervalos
        intervalos_unicos = sorted(set(intervalos))

        intervalos_consolidados = []

        # Comenzamos con el primer intervalo
        inicio, fin = intervalos_unicos[0].split('-')  # Extraemos el primer intervalo
        inicio = int(inicio)
        fin = int(fin)

        for i in range(1, len(intervalos_unicos)):
            nuevo_inicio, nuevo_fin = intervalos_unicos[i].split('-')
            nuevo_inicio = int(nuevo_inicio)
            nuevo_fin = int(nuevo_fin)

            # Comprobamos si hay superposición o si son consecutivos
            if fin == nuevo_inicio:
                fin = nuevo_fin  # Extender el intervalo actual
            else:
                # Añadimos el intervalo consolidado y comenzamos uno nuevo
                intervalos_consolidados.append(f"{str(inicio).zfill(2)}-{str(fin).zfill(2)}")
                inicio, fin = nuevo_inicio, nuevo_fin

        # Añadir el último intervalo
        intervalos_consolidados.append(f"{str(inicio).zfill(2)}-{str(fin).zfill(2)}")
        
        return intervalos_consolidados
