"""
Módulo 'utils.py': Contiene funciones y variables útiles.

Autores:
    - García Escamilla Bryan Alexis
    - Meléndez Macedonio Rodrigo

Fecha: 09/11/2025
"""
import os

# Colores ANSI
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
ORANGE = "\033[33m"
RESET = "\033[0m"

def limpiar_terminal() -> None:
    """Limpia la terminal para cualquier sistema operativo."""
    os.system('cls' if os .name == 'nt' else 'clear')