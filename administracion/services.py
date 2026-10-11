from datetime import datetime, timedelta
from clubs.models import Equipo

def generar_calendario_liga(division, grupo, fecha_inicio_str):
    """
    Genera un calendario de liga para una división y grupo específicos.

    Args:
        division (str): La división de los equipos.
        grupo (str): El grupo de los equipos.
        fecha_inicio_str (str): Fecha de inicio de la liga en formato "dd-mm-YYYY".

    Returns:
        list: Una lista de jornadas, cada una con los partidos programados.
    """
    dia_empieza = datetime.strptime(fecha_inicio_str, "%d-%m-%Y")
    equipos_qs = Equipo.objects.filter(division, grupo)
    equipos = [equipo.nombre_equipo for equipo in equipos_qs]
    jornadas = 7
    partidos = [[] for _ in range(jornadas)]
    
    # --- Lógica de primera vuelta
    for i in range(jornadas):
        partidos[i] = []
        for j in range(len(equipos) // 2):
            if i % 2 == 0:
                partidos[i].append((equipos[j], equipos[len(equipos) - 1 - j]))
            else:
                partidos[i].append((equipos[len(equipos) - 1 - j], equipos[j]))
                equipos.insert(1, equipos.pop())
                
    # --- Lógica de segunda vuelta
    for i in range(jornadas):
        segunda_vuelta = [(partido[1], partido[0]) for partido in partidos[i]]
        partidos.append(segunda_vuelta)
        
    # --- Asignar fechas y hora
    calendario_resultado = []
    for i, jornada in enumerate(partidos):
        jornada_datos = []
        fecha_jornada = dia_empieza + timedelta(days=i * 7)
        hora_partido = "20:00"
        
        for local, visitante in jornada:
            jornada_datos.append({
                "jornada": i + 1,
                "local": local,
                "visitante": visitante,
                "fecha": fecha_jornada.strftime("%d-%m-%Y"),
                "hora": hora_partido
            })
        calendario_resultado.append(jornada_datos)
        
    return calendario_resultado