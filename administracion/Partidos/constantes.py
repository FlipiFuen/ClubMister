import os
import random

# Ruta de la carpeta Partidos
PARTIDOS_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_ARBITROS = os.path.join(PARTIDOS_DIR, "Referees.dat")
RUTA_COMENTARIOS = os.path.join(PARTIDOS_DIR, "comentarios.dat")

# Indice de habilidades para tact_array
SKILL_TK_IDX = 1
SKILL_PS_IDX = 2
SKILL_SH_IDX = 3

# Valores base de las tacticas
BASE_TACTICS_CONFIG = {
    "N": {
        "base": [
            (1, 1, 1.0), (1, 2, 0.5), (1, 3, 0.3), (2, 1, 0.3), (2, 2, 1.0), 
            (2, 3, 0.3), (3, 1, 0.3), (3, 2, 0.3), (3, 3, 1.0),
        ],
        "positions_mods": [
            (4, 1, 0.7), (4, 2, 0.9), (4, 3, 0.3), (5, 1, 0.3), (5, 2, 0.9), (5, 3, 0.7),
        ],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: (opp_tactic == "E" or opp_tactic == "A") and cfg["tactical_ver"],
            "mods": [(2, 3, 0.55), (3, 2, 0.55), (2, 1, 0.55), (5, 3, 0.9), (5, 2, 1.0), (4, 1, 0.9)],
        },
        "vs_specific_tactics": {
            # N no tiene modificaciones específicas contra otras tácticas
        }
    },
    
    "D": {
        "base": [
            (1,1,1.25),(1,2,0.25),(1,3,0.0),(2,1,1.0),(2,2,0.75),(2,3,0.25),
            (3,1,0.5),(3,2,0.25),(3,3,0.75)
        ],
        "positions_mods": [
            (4,1,1.1),(4,2,0.65),(4,3,0.05),(5,1,0.65),(5,2,0.65),(5,3,0.5)
        ],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: opp_tactic == "L" or (opp_tactic == "P" and cfg["tactical_ver"]),
            "mods": [(1,1,1.5),(4,1,1.25)]
        },
        "vs_specific_tactics": {
            "L": [(1, SKILL_TK_IDX, 0.15)] # Bonus a la defensa contra L
        }
    },
    "A": {
        "base": [(1,1,1.0),(1,2,0.5),(1,3,0.5),(2,1,0.0),(2,2,1.0),(2,3,0.75),(3,1,0.0),(3,2,0.65),(3,3,1.5)],
        "positions_mods": [(4,1,0.5),(4,2,0.9),(4,3,0.5),(5,1,0.0),(5,2,0.9),(5,3,1.15)],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: opp_tactic == "D" or opp_tactic == "E",
            "mods": [(3,3,2.0),(5,3,1.4)]
        },
        "vs_specific_tactics": {
            # A no tiene modificaciones específicas contra otras tácticas
        }
    },
    "C": {
        "base": [(1,1,1.0),(1,2,0.5),(1,3,0.25),(2,1,0.5),(2,2,1.0),(2,3,0.25),(3,1,0.5),(3,2,0.5),(3,3,1.0)],
        "positions_mods": [(4,1,0.75),(4,2,0.85),(4,3,0.25),(5,1,0.6),(5,2,0.85),(5,3,0.6)],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: opp_tactic == "A" or opp_tactic == "P",
            "mods": [(2,3,0.75),(1,2,0.75),(1,3,0.5),(5,3,1.0),(4,1,0.85)]
        },
        "vs_specific_tactics": {
            "A": [(2, SKILL_PS_IDX, 0.15), (3, SKILL_SH_IDX, 0.1)], # Bonus a mediocampo
            "P": [(2, SKILL_PS_IDX, 0.15), (3, SKILL_SH_IDX, 0.1)], # Bonus a mediocampo
        }
    },
    "L": {
        "base": [(1,1,1.1),(1,2,0.25),(1,3,0.35),(2,1,0.5),(2,2,0.5),(2,3,0.65),(3,1,0.25),(3,2,0.25),(3,3,1.3)],
        "positions_mods": [(4,1,0.75),(4,2,0.4),(4,3,0.5),(5,1,0.3),(5,2,0.4),(5,3,0.9)],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: opp_tactic == "C" or ((opp_tactic == "N" or opp_tactic == "T") and cfg["tactical_ver"]),
            "mods": [(1,1,1.3),(1,2,0.5),(4,1,0.85)]
        },
        "vs_specific_tactics": {
            "C": [(1, SKILL_TK_IDX, 0.2), (2, SKILL_PS_IDX, 0.1)], # Bonus a defensa
        }
    },
    "P": {
        "base": [(1,1,1.0),(1,2,0.75),(1,3,0.3),(2,1,0.25),(2,2,1.0),(2,3,0.25),(3,1,0.25),(3,2,0.75),(3,3,1.0)],
        "positions_mods": [(4,1,0.65),(4,2,0.85),(4,3,0.2),(5,1,0.25),(5,2,0.85),(5,3,0.65)],
        "opponent_condition": {
            "check": lambda opp_tactic, cfg: opp_tactic == "L" or ((opp_tactic == "N" or opp_tactic == "T") and cfg["tactical_ver"]),
            "mods": [(2,3,0.5),(2,1,0.5),(3,3,1.25),(4,1,0.9),(5,3,0.9)]
        },
        "vs_specific_tactics": {
            "L": [(1, SKILL_TK_IDX, 0.1), (3, SKILL_SH_IDX, 0.15)], # Bonus a defensa
        }
    }
}

# Mapeo de posiciones a categorías
CATEGORIAS_POSICIONES = {
    "por": 0, "Portero": 0, # Portero
    # Defensas
    "def": 1, "Central": 1, "Central-Izquierdo": 1, "Central-Derecho": 1, "Lateral Izquierdo": 1, "Lateral Derecho": 1, "DFL": 1, "DFR":1, "DFC": 1,
    # Centrocampistas
    "Medio-Derecho": 2, "Medio-Izquierdo": 2, "Medio": 2, "MFC": 2, "MFR": 2, "MFL": 2,
    # Delanteros
    "Delantero-Izquierdo": 3, "Delantero-Derecho": 3, "Delantero-Centro": 3, "Extremo-Derecho": 3, "Extremo-Izquierdo": 3, "FWC": 3, "FWL": 3, "FWR": 3,
    # Centrocampistas defensivos
    "Mediocentro-Defensivo": 4, "DML": 4, "DMR": 4, "DMC": 4,
    # Centrocampistas ofensivos
    "Mediapunta": 5, "AML": 5, "AMR": 5, "mp": 5, "AMC": 5,
}

bonus_local = 100 # Bonificación del equipo local

# Constantes para el partido
TIEMPO_REGLAMENTARIO_PARTE = 45 # Minutos de cada parte del partido
PROBABILIDAD_BASE_EVENTO_MINUTO = 0.1 # probabilidad base de que ocurra un evento en un minuto
FACTOR_PROBABILIDAD_GOL_LOCAL = 1.0 # Factor de probabilidad de gol para el equipo local
FACTOR_PROBABILIDAD_GOL_VISITANTE = 0.9 # Factor de probabilidad de gol para el equipo visitante
REDUCCION_RESISTENCIA_POR_MINUTO = 0.996 # Reducción de resistencia por minuto

# Progreso de habilidades
AB_GOAL = 40
AB_ASSIST = 17  
AB_VICTORY_RANDOM = 34
AB_CLEAN_SHEET_GK = 26
AB_CLEAN_SHEET_DF = 11
AB_KTK = 15
AB_KPS = 8
AB_SHT_ON = 10
AB_SHT_OFF = 5
AB_SAV = 15
AB_OWN_GOAL = -8
AB_DEFEAT_RANDOM = -20
AB_CONCEDE = -10 # Goles encajados
AB_YELLOW = -2
AB_RED = -10
AB_PORT_ZERO_RANDOM = 20
SUB_SKILL_THRESHOLD = 1000
SUB_SKILL_RESET_VALUE = 300
MAIN_SKILL_INCREMENT = 1
MIN_SUB_SKILL_VALUE = 0

# Faltas y tarjetas
FACTOR_AGRESION_FALTA = 25
PROB_PENALTY_AREA_FOUL = 1000 # Base del 10% oportunidad para penalty
PROB_PENALTY_GK_FOUL_AREA = 7200 # Base del 72% si la falta es del portero
PROB_ROJA_DIRECTA_UMBRAL = 200
PROB_AMARILLA_UMBRAL = 3000
PROB_AVISO_UMBRAL = 4500
FACTOR_ESCALA_SEVERIDAD_ARBITRO = 0.05
PROB_TIRO_LIBRE_ZONA_ATAQUE = 9000 # 90% tiro directo en zona de ataque
PROB_TIRO_DIRECTO_ZONA_MCO = 5000 # 50% tiro directo en zona de medio campo ofensivo
PROB_TIRO_DIRECTO_OBJETIVO_BASE = 7500 # 75% base de que un tiro vaya a puerta
FACTOR_SH_TIRO_LIBRE_OBJETIVO = 70 # Factor de habilidad SH para ir a puerta (Puntos de prob por punto de SH >60)
MOD_RESISTENCIA_TIRO_LIBRE = 0.8 # Modificador por resistencia (resistencia_actual /100 * MOD)
MULTIPLICADOR_GOL_TIRO_LIBRE = 1.15 # Multiplicador a la prob de gol normal en un tiro libre
PROB_TIRO_LIBRE_ES_CORNER = 3500 # 35% de que una parada de falta acabe en corner
PROB_TIRO_LIBRE_BARRERA = 4500 # 45% de que un tiro pegue en la barrera
PROB_TIRO_LIBRE_BARRERA_CORNER = 2000 # 20% de que un tiro pegue en la barrera y termine en corner

# Penalty
PROB_PENALTY_BASE_GOL = 7500
TIRADOR_PENALTY_SH_FACTOR = 20
PENALTY_GK_ST_FACTOR = 25
PROB_PENALTY_PARADO_VS_FUERA = 6500 # Si no es gol; 65% es una parada
PROB_PENALTY_PARADO_CORNER = 2500

# Lesiones
PROB_LESION_BASE = 10 # Base: 20/10000 = 0.1% probabilidad de lesion por equipo por minuto
FACTOR_AGRESION_OPONENTE_PROB = 0.3 # Puntos añadidos por cada punto de agresion del rival
EFECTO_LESION_SALUD = True # Si True, la baja resistencia aumenta el riesgo y la selección es ponderada. Si False, la probabilidad general aumenta y la selección es aleatoria.
MULTIPLICADOR_PROB_NO_EFECTO_LESION = 2.0 # Multiplicador d probabilidad de si EFECTO_SALUD_LESION es False
PESO_RESISTENCIA_SELECCION_BASE = 5 # Peso base para la seleccion del jugador lesionado
FACTOR_PESO_RESISTENCIA_SELECCION_LESIONADO = 1.5 # Cuánto más influye la baja resistencia: (100-res) * factor
MINIMO_SEMANAS_LESION = 1
MAXIMO_SEMANAS_LESION_DEFECTO = 6
PROB_LESION_GRAVE = 1500 # 15% de que sea una lesion grave
MAXIMO_SEMANAS_LESION_GRAVE = 12
PROB_GOLPE_LEVE_BASE = 80 # 0.8% golpe leve
FACTOR_AGRESION_GOLPE = 1

# Zonas de campo (perspectiva del equipo atacante)
BANDA_IZQUIERDA = "IZQUIERDA"
BANDA_CENTRO = "CENTRO"
BANDA_DERECHA = "DERECHA"
LISTA_BANDAS = [BANDA_IZQUIERDA, BANDA_CENTRO, BANDA_DERECHA]

ZONA_BASE_DEFENSIVA_PROPIA = "DEFENSA_PROPIA"
ZONA_BASE_MEDIO_CAMPO_DEFENSIVO = "MEDIO_CAMPO_DEF"
ZONA_BASE_MEDIO_CAMPO_OFENSIVO = "MEDIO_CAMPO_OF"
ZONA_BASE_ATAQUE = "ATAQUE"
ZONA_BASE_AREA_RIVAL = "AREA_RIVAL"

BASES_ZONAS_CAMPO = [
    ZONA_BASE_DEFENSIVA_PROPIA, ZONA_BASE_MEDIO_CAMPO_DEFENSIVO,
    ZONA_BASE_MEDIO_CAMPO_OFENSIVO, ZONA_BASE_ATAQUE, ZONA_BASE_AREA_RIVAL
]

def crear_nombre_zona(base_zona, banda):
    """Crea un nombre de zona compuesto, ej: 'ATAQUE_IZQUIERDA"""
    return f"{base_zona}_{banda}"

# Generacion dinamica de las constantes de zona
for base_zona in BASES_ZONAS_CAMPO:
    for banda in LISTA_BANDAS:
        globals()[f"{base_zona}_{banda}"] = crear_nombre_zona(base_zona, banda)

def descomponer_zona(zona_str: str):
    """Descompone un nombre de zona en base y banda"""
    if not isinstance(zona_str, str):
        return None, None
    
    for banda_key in LISTA_BANDAS:
        sufijo = f"_{banda_key}"
        if zona_str.endswith(sufijo):
            base_zona = zona_str[:-len(sufijo)]
            if base_zona in BASES_ZONAS_CAMPO:
                return base_zona, banda_key
    if zona_str in BASES_ZONAS_CAMPO:
        return zona_str, None # Es una zona base, sin banda especifica asignada aun
    
    return "MEDIO_CAMPO_DEF", random.choice(LISTA_BANDAS)

# Mapeo de posiciones a su banda principal
POSICION_A_BANDA_MAP = {
    #Portero
    "Portero": [BANDA_CENTRO], "por": [BANDA_CENTRO],
    # Defensas
    "Central": [BANDA_CENTRO], "def": [BANDA_CENTRO],
    "Central-Izquierdo": [BANDA_IZQUIERDA, BANDA_CENTRO], "DFCL": [BANDA_IZQUIERDA, BANDA_CENTRO],
    "Central-Derecho": [BANDA_DERECHA, BANDA_CENTRO], "DFCR": [BANDA_DERECHA, BANDA_CENTRO],
    "Lateral Izquierdo": [BANDA_IZQUIERDA], "DFL": [BANDA_IZQUIERDA],
    "Lateral Derecho": [BANDA_DERECHA], "DFR": [BANDA_DERECHA],
    # Centrocampistas
    "Medio-Derecho": [BANDA_DERECHA], "MCDR": [BANDA_DERECHA],
    "Medio-Izquierdo": [BANDA_IZQUIERDA], "MCI": [BANDA_IZQUIERDA],
    "Medio": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA], "MC": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA],
    # Delanteros
    "Delantero-Izquierdo": [BANDA_IZQUIERDA, BANDA_CENTRO], "DCL": [BANDA_IZQUIERDA, BANDA_CENTRO],
    "Delantero-Derecho": [BANDA_DERECHA, BANDA_CENTRO], "DCR": [BANDA_DERECHA, BANDA_CENTRO],
    "Delantero-Centro": [BANDA_CENTRO], "DC": [BANDA_CENTRO],
    "Extremo-Derecho": [BANDA_DERECHA], "ED": [BANDA_DERECHA],
    "Extremo-Izquierdo": [BANDA_IZQUIERDA], "EI": [BANDA_IZQUIERDA],
    # Centrocampistas defensivos
    "Mediocentro-Defensivo": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA], "MCD": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA],
    "DML": [BANDA_IZQUIERDA, BANDA_CENTRO], "DMR": [BANDA_DERECHA, BANDA_CENTRO],
    # Centrocampistas ofensivos
    "Mediapunta": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA], "MP": [BANDA_CENTRO, BANDA_IZQUIERDA, BANDA_DERECHA],
    "AML": [BANDA_IZQUIERDA, BANDA_CENTRO], "AMR": [BANDA_DERECHA, BANDA_CENTRO],
    "MPL": [BANDA_IZQUIERDA, BANDA_CENTRO], "MPR": [BANDA_DERECHA, BANDA_CENTRO],
}
def get_bandas_para_posicion(posicion_str):
    return POSICION_A_BANDA_MAP.get(posicion_str, [BANDA_CENTRO]) # Al centro por defecto si no se encuentra

# Bonificaciones por zona y posicion para la seleccion de jugador protagonista
BONUS_POSICION_ZONA = {
    'Defensivo': { # Aplica a ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, ZONA_BASE_DEFENSIVA_PROPIA
        1: 1.5, # Defensas
        4: 1.3, # Centrocampistas defensivos
    },
    'Medios': { # Aplica a ZONA_BASE_MEDIO_CAMPO_OFENSIVO, ZONA_BASE_MEDIO_CAMPO_DEFENSIVO
        2: 1.5, # Centrocampistas
        5: 1.3, # Centrocampistas ofensivos
        4: 1.3, # Centrocampistas defensivos
    },
    'Ofensivo': { # Aplica a ZONA_BASE_ATAQUE, ZONA_BASE_MEDIO_CAMPO_OFENSIVO, ZONA_BASE_AREA_RIVAL
        3: 1.5, # Delanteros
        5: 1.3, # Centrocampistas ofensivos
    }
}
