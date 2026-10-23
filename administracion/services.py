from datetime import datetime, timedelta

from administracion.models import PartidoProgramado
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
    try:
        dia_empieza = datetime.strptime(fecha_inicio_str, "%d-%m-%Y")
    except ValueError as e:
        raise ValueError("El formato de fecha de inicio no es válido. Debe ser: DD-MM-YYYY") from e
    equipos_qs = Equipo.objects.filter(division=division, grupo=grupo)
    equipos_por_nombre = {equipo.nombre_equipo: equipo for equipo in equipos_qs}
    equipos = list(equipos_por_nombre)
    
    if not equipos:
        raise ValueError(f"No hay equipos registrados en la Division {division} - grupo {grupo}")
    
    temporada = equipos_qs[0].temporada
    if PartidoProgramado.objects.filter(temporada=temporada, division=division, grupo=grupo).exists():
        raise ValueError(
            f"Ya existe un calendario para la temporada {temporada}, "
            f"División {division} - grupo {grupo}"
        )
    jornadas = 7
    partidos = [[] for _ in range(jornadas)]
    
    # --- Lógica de primera vuelta
    for i in range(jornadas):
        partidos[i] = []
        for j in range(len(equipos) // 2):
            local, visitante = equipos[j], equipos[len(equipos) - 1 - j]
            if i % 2 == 1:
                local, visitante = visitante, local
            
            partidos[i].append((local, visitante))
        equipos.insert(1, equipos.pop())
                
    # --- Lógica de segunda vuelta
    for i in range(jornadas):
        segunda_vuelta = [(partido[1], partido[0]) for partido in partidos[i]]
        partidos.append(segunda_vuelta)
        
    # --- Asignar fechas y hora
    calendario_resultado = []
    partidos_programados = []
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
            partidos_programados.append(PartidoProgramado(
                division = division,
                grupo = grupo,
                temporada = temporada,
                jornada = i + 1,
                equipo_local = equipos_por_nombre[local],
                equipo_visitante = equipos_por_nombre[visitante],
                fecha = fecha_jornada.date(),
                hora = datetime.strptime(hora_partido, "%H:%M").time(),
            ))
        calendario_resultado.append(jornada_datos)
    
    PartidoProgramado.objects.bulk_create(partidos_programados)
    return calendario_resultado
