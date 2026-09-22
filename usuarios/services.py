from clubs.models import Equipo, Futbolista
from clubs.plantilla import Plantilla

def asignar_division_grupo():
    """
    Asigna la división y el grupo al nuevo equipo.
    
    Returns:
        tuple: (int: division, int: grupo)
    """
    
    # Obtenemos el último equipo registrado
    ultimo_equipo = Equipo.objects.order_by('-division','-grupo','-id').first()

    # Si no hay equipos asignamos división 1 y grupo 1
    if ultimo_equipo is None:
        return 1, 1
    
    # Obtenemos la división y el grupo del último equipo
    division = ultimo_equipo.division
    grupo = ultimo_equipo.grupo

    # Comprobamos si el grupo ya tiene 8 equipos
    equipos_grupo = Equipo.objects.filter(division=division, grupo=grupo).count()
    if equipos_grupo >= 8:
        grupo += 1

    # Si la división ya tiene 8 grupos aumentamos la división y asignamos el grupo 1
    if grupo > 8:
        division += 1
        grupo = 1

    return division, grupo

def crear_equipo_inicial(usuario, nombre_equipo, abreviatura):
    
    # Generamos el equipo asociado al nuevo usuario
    plantilla = Plantilla()
    futbolistas = plantilla.crear_equipo()
    
    # Asignamos la división y el grupo
    division, grupo = asignar_division_grupo()
    
    # Creamos el equipo y lo asignamso al usuario
    equipo = Equipo.objects.create(
        user=usuario, 
        nombre_equipo = nombre_equipo,
        abreviatura = abreviatura, 
        division = division, 
        grupo = grupo,
        temporada = 1
    )
    
    # Asignamos los futbolistas al equipo
    Futbolista.objects.bulk_create([
        Futbolista(
            equipo = equipo,
            nombre = futbolista['nombre'],
            nacionalidad = futbolista['nacionalidad'],
            edad = futbolista['edad'],
            lado_preferido = futbolista['lado_preferido'],
            posicion = futbolista['posicion'],
            st = futbolista['habilidades']['st'],
            tk = futbolista['habilidades']['tk'],
            ps = futbolista['habilidades']['ps'],
            sh=futbolista['habilidades']['sh'],
            resistencia=futbolista['resistencia'],
            agresividad=futbolista['agresividad'],
            st_hab=futbolista['st_hab'],
            tk_hab=futbolista['tk_hab'],
            ps_hab=futbolista['ps_hab'],
            sh_hab=futbolista['sh_hab'],
            partidos=futbolista['partidos'],
            paradas=futbolista['paradas'],
            takling=futbolista['takling'],
            asistencias=futbolista['asistencias'],
            tiros=futbolista['tiros'],
            goles=futbolista['goles'],
            disciplina=futbolista['disciplina'],
            lesion=futbolista['lesion'],
            suspension=futbolista['suspension'],
            adaptacion=futbolista['adaptacion'],
            pases_buenos=futbolista['pases_buenos'],
            )
           for futbolista in futbolistas
        ])
    
    return equipo