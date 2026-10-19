
import json
import os
import sys

# Añadir la ruta del directorio padre al sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from administracion.Partidos.simulador import Partido as PartidoSimulador

def jugar_partido(partido):
    """Simula un partido de fútbol entre dos equipos."""
    equipo_local, equipo_visitante, fecha, hora = partido[:4]

    partido_simulado = PartidoSimulador(
        equipo_local, 
        equipo_visitante, 
        fecha, 
        hora, 
        False
    )

    eventos = partido_simulado.simular_partido()

    # Imprimir los eventos del partido
    if eventos:
        # Devolver un resumen del partido
        return f"Partido entre {equipo_local} y {equipo_visitante} finalizado. Fecha: {fecha}, Hora: {hora}."
    else:
        return f"No se han registrado eventos para el partido entre {equipo_local} y {equipo_visitante}."

if __name__ == "__main__":
    print("Bienvenido al gestor de partidos de fútbol")

    fecha = input("Introduce la fecha de los partidos (DD-MM-AAAA): ").strip()
    ruta_json = os.path.join(os.path.dirname(__file__), "Calendarios", "calendario_1_1.json")
    print("Ruta JSON utilizada:", ruta_json)
    
    if not os.path.exists(ruta_json):
        print(f"Error: No se pudo encontrar el archivo de calendario en: {ruta_json}")
    else:
        try:
            with open(ruta_json, "r", encoding="utf-8") as file:
                datos_json = json.load(file)
                
            partidos_hoy = []
            for encuentros in datos_json:
                for partido in encuentros:
                    if len(partido) >= 3 and partido[2] == fecha:
                        partidos_hoy.append(partido)
                        
            if partidos_hoy:
                for partido in partidos_hoy:
                    resultado = jugar_partido(partido)
                    print(resultado)
            else:
                print(f"No hay partidos programados para la fecha: {fecha}")
        except json.JSONDecodeError as e:
            print(f"Error al leer el archivo JSON del calnedario: {e}")
    