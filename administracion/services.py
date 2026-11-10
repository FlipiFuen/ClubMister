import os
import random

from datetime import datetime, timedelta
from pathlib import Path

from django.db import transaction
from django.db.models import Count, Q
from django.template.loader import render_to_string

from administracion.models import Arbitro, CalendarioTemporada, PartidoProgramado, ReportePartido
from administracion.Partidos.constantes import PARTIDOS_DIR
from clubs.models import Equipo, Alineacion

def guardar_calendario_html(division, grupo, temporada, calendario):
    """
    Renderiza el calendario a HTML, lo guarda en disco y registra su ruta en la Base de datos
    
    Args:
        division (int): División del calendario.
        grupo (int): Grupo del calendario.
        temporada (int): Temporada del calendario.
        calendario (list): Lista de jornadas, cada una con sus partidos (dicts).

    Returns:
        CalendarioTemporada: Registro con la ruta del archivo generado.
    """
    html = render_to_string("clubs/calendario_temporada.html", {
        "division": division,
        "grupo": grupo,
        "temporada": temporada,
        "calendario": calendario,
    })
    
    # Misma carpeta que los reportes de liga de esa temporada, división y grupo
    carpeta = os.path.join(
        PARTIDOS_DIR,
        f"reportes_temporada_{temporada}_division_{division}_grupo_{grupo}",
    )
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "calendario.html")
    
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write(html)
        
    # Si ya había registro sólo se actualiza la ruta
    registro, _ = CalendarioTemporada.objects.update_or_create(
        temporada = temporada, division = division, grupo = grupo,
        defaults = {"ruta_archivo": ruta},
    )
    return registro

def calendario_desde_bd(temporada, division, grupo):
    """
    Reconstruye desde la BD el calendario de una temporada, división y grupo
    
    Devuelve la misma estructura que generar_calendario_liga: una lista de jornadas,
    cada una con los partidos como diccionarios
    """
    partidos = PartidoProgramado.objects.filter(
        temporada=temporada, division=division, grupo=grupo,
    ).select_related("equipo_local", "equipo_visitante")
    
    jornadas = {}
    for partido in partidos:
        jornadas.setdefault(partido.jornada, []).append({
            "id": partido.id,
            "jornada": partido.jornada,
            "local": partido.equipo_local.nombre_equipo,
            "visitante": partido.equipo_visitante.nombre_equipo,
            "fecha": partido.fecha.strftime("%d-%m-%Y"),
            "hora": partido.hora.strftime("%H:%M"),
        })
        
    return list(jornadas.values())

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
    carga = carga_arbitros(temporada)
    for i, jornada in enumerate(partidos):
        jornada_datos = []
        fecha_jornada = dia_empieza + timedelta(days=i * 7)
        arbitros_jornada = elegir_arbitros(temporada, len(jornada), carga)
        hora_partido = "20:00"
        
        for (local, visitante), arbitro in zip(jornada, arbitros_jornada):
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
                arbitro = arbitro,
            ))
        calendario_resultado.append(jornada_datos)
    
    # Si falla el guardado del HTML se revierten también los partidos
    with transaction.atomic():
        PartidoProgramado.objects.bulk_create(partidos_programados)
        guardar_calendario_html(division, grupo, temporada, calendario_resultado)
        
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
    # Partido de liga: el árbitro ya viene asignado. Amistoso: se elige ahora
    if programado and programado.arbitro_id:
        arbitro = programado.arbitro
    else:
        arbitro = asignar_arbitro(local.temporada)
        
    partido = Partido(
        local.nombre_equipo,
        visitante.nombre_equipo,
        fecha.strftime("%d-%m-%Y"),
        hora.strftime("%H:%M"),
        es_oficial = es_oficial,
        competicion = competicion,
        partido_programado = programado,
        arbitro = arbitro,
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
            resultados.append({"programado": p, "estado": "ya_simulado", "reporte": None, "sin_alineacion": []})
            continue
        
        # Comprobar si los equipos enviaron su alineación en BD para este partido
        sin_alineacion = []
        if not Alineacion.objects.filter(equipo=p.equipo_local, partido=p).exists():
            sin_alineacion.append(p.equipo_local.nombre_equipo)
        if not Alineacion.objects.filter(equipo=p.equipo_visitante, partido=p).exists():
            sin_alineacion.append(p.equipo_visitante.nombre_equipo)
        
        reporte = _simular(p.equipo_local, p.equipo_visitante, p.fecha, p.hora, True, "liga", p)
        resultados.append({
            "programado": p,
            "estado": "ok" if reporte else "error",
            "reporte": reporte,
            "sin_alineacion": sin_alineacion,
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


ORIGENES_ARBITROS = [
    "España", "Inglaterra", "Francia", "Italia", "Alemania", "Portugal",
    "Argentina", "Brasil", "Chile", "Croacia", "Dinamarca", "Bulgaria",
]

def generar_arbitros(cantidad):
    """
    Genera árbitros aleatorios y los guarda en la base de datos.
    El nombre se forma con dos apellidos de apellidos.txt (formato Apellido_Apellido)
    evitando los nombres que ya existen. La severidad (1-20) y el origen son aleatorios.

    Args:
        cantidad (int): Número de árbitros a crear.

    Returns:
        list: Lista de objetos Arbitro creados.

    Raises:
        ValueError: Si la cantidad no es mayor que 0.
    """
    if cantidad < 1:
        raise ValueError("La cantidad de árbitros debe ser mayor que 0")
    
    ruta_apellidos = Path(__file__).resolve().parent.parent / "clubs" / "futbolistas" / "apellidos.txt"
    try:
        with ruta_apellidos.open(encoding="utf-8-sig") as archivo:
            apellidos = [linea.strip() for linea in archivo if linea.strip()]
    except OSError:
        # En caso de error usamos unos apellidos por defecto
        apellidos = ["García", "López", "Pérez", "Gutierrez", "Smith", "Sevchenko", "Maldini"]
        
    existentes = set(Arbitro.objects.values_list("nombre", flat=True))
    nuevos = []
    intentos = 0
    while len(nuevos) < cantidad and intentos < cantidad * 50:
        intentos += 1
        nombre = f"{random.choice(apellidos)}"
        if nombre in existentes:
            continue
        existentes.add(nombre)
        nuevos.append(Arbitro(
            nombre = nombre,
            severidad = random.randint(1, 20),
            origen = random.choice(ORIGENES_ARBITROS)
        ))
        
    return Arbitro.objects.bulk_create(nuevos)
 
def carga_arbitros(temporada):
    """
    Calcula cuántos partidos tiene asignados cada árbitro activo en una temporada.
    Cuenta los partidos programados y los reportes sin partido programado
    (amistosos e independientes).

    Args:
        temporada (int): Temporada a consultar.

    Returns:
        dict: Diccionario {id_arbitro: numero_de_partidos}.
    """
    arbitros = Arbitro.objects.filter(activo=True).annotate(
        n_programados = Count(
            "partidos_programados",
            filter = Q(partidos_programados__temporada=temporada),
            distinct = True,
        ),
        n_reportes = Count(
            "reportes",
            filter = Q(partidos_programados__temporada = temporada),
            distinct = True
        )
    )
    return {a.id: a.n_programados + a.n_reportes for a in arbitros}

def elegir_arbitros(temporada, cantidad, carga=None):
    """
    Elige árbitros para un grupo de partidos (por ejemplo, una jornada).
    Se eligen primero los árbitros con menos partidos en la temporada, desempatando
    al azar. No se repite árbitro dentro del grupo salvo que no haya suficientes.

    Args:
        temporada (int): Temporada de los partidos.
        cantidad (int): Número de árbitros a elegir.
        carga (dict, optional): Carga actual {id_arbitro: partidos}. Se actualiza con
            las nuevas asignaciones para poder encadenar varias jornadas sin consultar la BD.

    Returns:
        list: Lista de objetos Arbitro, uno por partido.

    Raises:
        ValueError: Si no hay árbitros activos.
    """
    arbitros = list(Arbitro.objects.filter(activo=True))
    if not arbitros:
        raise ValueError("No hay árbitros activos. Importa o genera primero")
    if carga is None:
        carga = carga_arbitros(temporada)
        
    elegidos = []
    for _ in range(cantidad):
        usados = {a.id for a in elegidos}
        candidatos = [a for a in arbitros if a.id not in usados] or arbitros
        minimo = min(carga.get(a.id, 0) for a in candidatos)
        elegido = random.choice([a for a in candidatos if carga.get(a.id, 0) == minimo])
        carga[elegido.id] = carga.get(elegido.id, 0) + 1
        elegidos.append(elegido)
        
    return elegidos

def asignar_arbitro(temporada):
    """
    Elige un único árbitro para un partido suelto (amistoso o independiente).

    Args:
        temporada (int): Temporada del partido.

    Returns:
        Arbitro: Árbitro menos usado de la temporada.

    Raises:
        ValueError: Si no hay árbitros activos.
    """
    return elegir_arbitros(temporada, 1)[0]
            