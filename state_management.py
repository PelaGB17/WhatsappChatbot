import os
import json
import time
from config import STATE_FILE

# Crear directorio para el archivo de estado
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

def save_state(data):
    """Guarda el estado de la aplicación"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error al guardar el estado: {e}")

def load_state():
    """Carga el estado de la aplicación"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error al cargar el estado: {e}")
    
    # Estado por defecto
    return {
        'last_run_time': None,
        'current_location': '28079',
        'current_municipality': 'Madrid'
    }

def update_last_run_time():
    """Actualiza el tiempo de última ejecución"""
    state = load_state()
    state['last_run_time'] = time.time()
    save_state(state)

def get_last_run_time():
    """Obtiene el tiempo de última ejecución"""
    state = load_state()
    return state.get('last_run_time')

def update_location(municipality, code):
    """Actualiza la ubicación actual"""
    state = load_state()
    state['current_location'] = code
    state['current_municipality'] = municipality
    save_state(state)

def get_location():
    """Obtiene la ubicación actual"""
    state = load_state()
    return state.get('current_location'), state.get('current_municipality')
