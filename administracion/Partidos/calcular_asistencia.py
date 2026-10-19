import random

from clubs.models import Estadio, Futbolista, Equipo

# Constantes
BASE_ASISTENCIA_LOCAL = 1000
BASE_ASISTENCIA_VISITANTE = 500
SKILL_FACTOR = 15
CAPACIDAD_DEFECTO = 1000
PRECIO_ENTRADA_DEFECTO = 10
BONUS_DIVISION_POR_NIVEL = 100
FACTOR_ALEATORIO = 50

def _calcular_factor_division(equipo_obj, base):
    """Calcula el factor de asistencia según la división del equipo"""
    factor = base
    if hasattr(equipo_obj, "division") and isinstance(equipo_obj.division, int):
        factor += (5 - min(equipo_obj.division, 5)) * BONUS_DIVISION_POR_NIVEL / 2
    return factor

def get_average_skill(equipo_obj, skill_attr='resistencia', top_n=11):
    """
    Calcula la habilidad media del atributo especificado para los primeros 'top_n' jugadores del equipo.
    """
    jugadores = Futbolista.objects.filter(equipo=equipo_obj).order_by(f'-{skill_attr}')[:top_n]
    if not jugadores:
        return 5.0  # Valor por defecto si no hay jugadores
    total_skill = sum(getattr(jugador, skill_attr, 5) for jugador in jugadores)
    return total_skill / len(jugadores)

def calcular_asistencia(nombre_equipo_local, nombre_equipo_visitante, record=True):
    """
    Calcula la asistencia esperada para un partido entre dos equipos.
    Devuelve un número entero sin exceder la capacidad del estadio
    """
    try:
        equipo_local = Equipo.objects.get(nombre_equipo=nombre_equipo_local)
        equipo_visitante = Equipo.objects.get(nombre_equipo=nombre_equipo_visitante)
    except Equipo.DoesNotExist:
        print(f"Error: No se encontró el equipo {nombre_equipo_local} o {nombre_equipo_visitante}.")
        return 0

    capacidad_estadio = CAPACIDAD_DEFECTO

    try:
        estadio_local_obj = Estadio.objects.get(equipo=equipo_local)
        capacidad_estadio = estadio_local_obj.capacidad
        precio_entrada = estadio_local_obj.precio
    except Estadio.DoesNotExist:
        print(f"Advertencia: No se encontró el estadio para el equipo {nombre_equipo_local}. Usando valores por defecto.")
    except Exception as e:
        print(f"Error al obtener el estadio: {e}")
    
    # Calculo de factores de asistencia
    h_factor = _calcular_factor_division(equipo_local, BASE_ASISTENCIA_LOCAL)

    # Factor de asistencia visitante
    a_factor = _calcular_factor_division(equipo_visitante, BASE_ASISTENCIA_VISITANTE)

    # Factor de habilidad
    skill_local = get_average_skill(equipo_local, skill_attr = 'resistencia')
    skill_visitante = get_average_skill(equipo_visitante, skill_attr='resistencia')

    # Calculo de asistencia
    asistencia = h_factor + (skill_local * SKILL_FACTOR)
    asistencia += a_factor + (skill_visitante * SKILL_FACTOR / 4)
    # Factor aleatorio
    asistencia += random.randint(0, FACTOR_ALEATORIO - 1)
    # Asegurar que no sea negativa y no supere la capacidad del estadio
    asistencia_final = min(max(0, int(asistencia)), capacidad_estadio)

    return asistencia_final
        