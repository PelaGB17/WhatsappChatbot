# WhatsApp Chatbot con Flask, Twilio, Google Calendar y AEMET
Este proyecto implementa un chatbot para WhatsApp utilizando Twilio, que permite a los usuarios consultar eventos de su Google Calendar y el pronóstico del tiempo en su ubicación. El chatbot está construido con Flask y hace uso de varias APIs para responder a los usuarios.

### Características
Consulta de Agenda: Conexión con la API de Google Calendar para extraer y enviar eventos del día al usuario.
Consulta Meteorológica: Utiliza la API de AEMET para proporcionar el pronóstico del tiempo en la ubicación actual del usuario.
Actualización de Ubicación: Permite al usuario actualizar su ubicación manualmente, almacenando el municipio para futuras consultas.
Mensajes Programados: Envío diario de mensajes a las 7:30 AM con el pronóstico del tiempo y eventos del día.

### Requisitos
Antes de comenzar, asegúrate de tener instaladas las siguientes dependencias:

Python 3.7+
Twilio Account SID y Auth Token para enviar mensajes de WhatsApp.
Google Cloud API habilitada con acceso a Google Calendar.
API Key de AEMET para obtener el pronóstico del tiempo.
Instalación de Dependencias
Instala los paquetes necesarios ejecutando:

```
pip install -r requirements.txt
```

### Configuración
1. Configura Twilio:

    - Registra tu número de WhatsApp en el sandbox de Twilio.
    - Copia tu Account SID y Auth Token.
2. Configura Google Calendar:

    - Habilita la API de Google Calendar en Google Cloud Console.
    - Descarga el archivo credentials.json y colócalo en la raíz de tu proyecto.
    - La primera vez que ejecutes el bot, autentícate para generar token.json.
3. Configura AEMET:

    - Obtén tu API Key de AEMET y guárdala en el código donde se requiera.
4. Archivo de Municipios:

    - Asegúrate de tener un archivo municipios.xlsx que contenga una lista de municipios, su código y sus datos de ubicación. Se obtiene de la página de AEMET.
5. Variables de Configuración:

    - Define tus variables de configuración en el código o en un archivo .env si prefieres no tenerlas en el código.

### Ejecución
#### Iniciar el Servidor
Para iniciar el servidor Flask y el scheduler para mensajes programados:
```
python Main.py
```
El servidor estará accesible en http://localhost:5000. Si estás desplegando en un servidor en la nube, asegúrate de habilitar el puerto 5000 o de configurar HTTPS.

#### Conectar Twilio con el Servidor
Configura el webhook de Twilio para tu número de WhatsApp apuntando a la URL del servidor:

```
https://your-server-url:5000/whatsapp
```

### Ejemplo de Uso
1. Consultar el Tiempo:
    - Envia un mensaje con la palabra "tiempo" y el bot responderá con el pronóstico actual en tu ubicación.
2. Actualizar Ubicación:
    - Envía "cambiar ubicación" y el bot te pedirá el nombre de tu municipio.
    - Escribe el nombre del municipio para actualizar la ubicación.
3. Consultar Agenda:
    - Recibirás automáticamente tus eventos del día junto con el pronóstico del tiempo a las 7:30 AM.

### Despliegue en Producción
Para desplegar en un servidor en producción, considera lo siguiente:
- Configuración HTTPS: Usa Nginx o Apache para manejar el tráfico HTTPS.
- Ejecutar en un Contenedor Docker (opcional): Puedes construir una imagen de Docker para el proyecto.

```
# Usa una imagen base de Python
FROM python:3.8-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo requirements.txt y las dependencias
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia el resto de los archivos
COPY . .

# Expone el puerto 5000
EXPOSE 5000

# Comando de inicio del servidor Flask
CMD ["python", "chatbot.py"]
Construye y ejecuta el contenedor:
```

```
docker build -t whatsapp-chatbot .
docker run -p 5000:5000 whatsapp-chatbot
```
### Notas de Seguridad
- Protege las claves de API: No compartas tus credenciales de API públicamente. Usa un archivo .env o un gestor de secretos.
- HTTPS: Es importante que tu aplicación esté en HTTPS para proteger la comunicación.

### Problemas Comunes
- Error de token caducado: Si el archivo token.json caduca, elimina el archivo y autentica nuevamente.
- Error de permisos en Google Calendar: Asegúrate de que credentials.json tenga los permisos correctos.

### Contribución
- Para contribuir, realiza un fork del repositorio y envía un Pull Request con tus cambios.