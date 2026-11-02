from datetime import datetime, timedelta

from administracion.models import PartidoProgramado, ReportePartido
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

def proximo_miercoles_20h(ahora=None):
    """
    Devuelve el próximo miércoles a las 20:00 a partir del momento actual o de la fecha proporcionada.
    
    Args:
        ahora (datetime, optional): Momento de referencia. Si no se proporciona, se usa la fecha y hora actual.
    
    Returns:
        datetime: Fecha y hora del próximo miércoles a las 20:00.
    """
    ahora = ahora or datetime.now()
    dias = (2 - ahora.weekday()) % 7
    fecha = (ahora + timedelta(days=dias)).replace(hour=20, minute=0, second=0, microsecond=0)
    
    if fecha <= ahora:
        fecha += timedelta(days=7)
    
    return fecha

def _simular(local, visitante, fecha, hora, es_oficial, competicion, programado=None):
    """
    Simula un partido entre dos equipos.

    Args:
        local (Equipo): Equipo local.
        visitante (Equipo): Equipo visitante.
        fecha (date): Fecha del partido.
        hora (time): Hora del partido.
        es_oficial (bool): Indica si el partido es oficial.
        competicion (str): Tipo de competición.
        programado (PartidoProgramado, optional): Partido programado asociado.

    Returns:
        ReportePartido: Reporte del partido simulado, o None si no se pudo simular.
    """
    # Import diferido: el simulador ejecuta django.setup() al importarse
    from administracion.Partidos.simulador import Partido
    
    partido = Partido(
        local.nombre_equipo,
        visitante.nombre_equipo,
        fecha.strftime("%d-%m-%Y"),
        hora.strftime("%H:%M"),
        es_oficial = es_oficial,
        competicion = competicion,
        partido_programado = programado,
    ) 
    eventos = partido.simular_partido()
    if eventos is None or not partido.ruta_reporte:
        return None
    
    return ReportePartido.objects.filter(ruta_archivo=partido.ruta_reporte).first()

def simular_jornada(division, grupo, jornada):
    """
    Simula todos los partidos de una jornada para una división y grupo específicos.

    Args:
        division (str): División del torneo.
        grupo (str): Grupo dentro de la división.
        jornada (int): Número de la jornada a simular.

    Returns:
        list: Lista de resultados de la simulación, cada uno con el estado y el reporte correspondiente.
    """
    equipo = Equipo.objects.filter(division=division, grupo=grupo).first()
    if not equipo:
        raise ValueError(f"No hay equipos en la división {division} - grupo {grupo}")
    
    programados = PartidoProgramado.objects.filter(
        temporada = equipo.temporada, division = division, grupo = grupo, jornada = jornada
    ).select_related("equipo_local", "equipo_visitante")
    if not programados:
        raise ValueError("No hay partidos programados para esa jornada. Generaste el calendario?")
    
    resultados = []
    for p in programados:
        if ReportePartido.objects.filter(partido_programado=p).exists():
            resultados.append({"programado": p, "estado": "ya_simulado", "reporte": None})
            continue
        
        reporte = _simular(p.equipo_local, p.equipo_visitante, p.fecha, p.hora, True, "liga", p)
        resultados.append({
            "programado": p,
            "estado": "ok" if reporte else "error",
            "reporte": reporte,
        })
        
    return resultados

def simular_individual(local, visitante, oficial, fecha=None, hora=None):
    """
    Simula un partido individual entre dos equipos.

    Args:
        local (Equipo): Equipo local.
        visitante (Equipo): Equipo visitante.
        oficial (bool): Indica si el partido es oficial.
        fecha (date, optional): Fecha del partido (solo para amistoso).
        hora (time, optional): Hora del partido (solo para amistoso).

    Returns:
        ReportePartido: Reporte del partido simulado.

    Raises:
        ValueError: Si no se pudo simular el partido.
    """
    if oficial:
        momento = proximo_miercoles_20h()
        reporte = _simular(local, visitante, momento.date(), momento.time(), True, "independiente")
    else:
        reporte = _simular(local, visitante, fecha, hora, False, "amistoso")
        
    if not reporte:
        raise ValueError("No se pudo simular el partido")
    
    return reporte
        
