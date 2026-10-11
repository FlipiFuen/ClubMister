from datetime import datetime, timedelta
import os
import sys
import json

# Agregar el directorio raíz del proyecto al PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
# Agregar el directorio raíz del proyecto al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ClubMister.settings')  
print("Configurando el entorno de Django")
django.setup()
print("Entorno de Django configurado")
from usuarios.models import Equipo

print("Introduce división\n")
division = input()
print("Introduce grupo\n")
grupo = input()
print("Introduce fecha de inicio\n")

fecha_inicio = input()
dia_empieza = datetime.strptime(fecha_inicio, "%d-%m-%Y")
equipos = list(Equipo.objects.all())
equipos = [equipo.nombre_equipo for equipo in equipos]
partidos = [[] for _ in range(7)]  # Inicializa la lista de partidos para 7 jornadas
jornadas = 7
# Primera vuelta
for i in range(jornadas):
    partidos[i] = []
    for j in range(len(equipos) // 2):
        # Se alterna el orden de los equipos en cada jornada
        if i % 2 == 0:
            partidos[i].append((equipos[j], equipos[len(equipos) - 1 - j])) # Jornada par, el primer equipo juega en casa
        else:
            partidos[i].append((equipos[len(equipos) - 1 - j], equipos[j])) # Jornada impar, el primer equipo juega fuera de casa
        # Rotar los equipos para la siguiente jornada
    equipos.insert(1, equipos.pop())

# Segunda vuelta, se invierten los partidos
for i in range(jornadas):
    segunda_vuelta = []
    for partido in partidos[i]:
        # Se invierte el orden de los equipos
        segunda_vuelta.append((partido[1], partido[0]))
    partidos.append(segunda_vuelta)  # Añadir la segunda vuelta a la lista de partidos
# Asignar fechas a los partidos
for i in range(len(partidos)):
    for j in range(len(partidos[i])):
        # Se asigna la fecha de inicio más el número de días correspondiente a la jornada
        fecha_partido = dia_empieza + timedelta(days=i * 7)
        # Se asigna la hora del partido
        hora_partido = datetime.strptime("20:00", "%H:%M").time()
        partido = (
            partidos[i][j][0],  # Equipo local
            partidos[i][j][1],  # Equipo visitante
            fecha_partido.strftime("%d-%m-%Y"),  # Fecha del partido
            hora_partido.strftime("%H:%M")  # Hora del partido
        )
        partidos[i][j] = partido

# Guardar los partidos en un archivo json
with open(f"calendario_{division}_{grupo}.json", "w") as f:
    json.dump(partidos, f, indent=4)

