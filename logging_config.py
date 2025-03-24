import os
import logging
from logging.handlers import RotatingFileHandler

# Crear directorio para logs
os.makedirs('logs', exist_ok=True)

def setup_logger(name):
    """Configura y devuelve un logger con nombre específico"""
    logger = logging.getLogger(name)
    
    # Nivel de logging
    logger.setLevel(logging.INFO)
    
    # Formato para logs
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler para archivo con rotación
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
