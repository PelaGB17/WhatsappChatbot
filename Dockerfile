# Usa Python 3.9 como imagen base
FROM python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requisitos
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código fuente
COPY . .

# Crea directorios necesarios
RUN mkdir -p data logs credentials

# Expone el puerto donde se ejecuta Flask
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "Main.py"]
