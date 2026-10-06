import random
import math
from pathlib import Path

# Constantes
N_GAUSS = 1000

def fill_gaussian_vars_arr(amount):
    """Llena la lista gaussian_vars con valores gaussianos"""
    # Generar una lista de valores gaussianos
    valores_gausianos = []

    for _ in range(amount):
        salida = False
        while not salida:
            u1 = random.random()
            u2 = random.random()
            v1 = 2 * u1 - 1
            v2 = 2 * u2 - 1
            s = v1 * v1 + v2 * v2
                
            if s < 1.0:
                x = v1 * math.sqrt(-2 * math.log(s) / s)
                    
                if -1.0 < x < 1.0:
                    valores_gausianos.append(x)
                    salida = True
                    
    return valores_gausianos
    


class Plantilla:
    def __init__(self):
        self.jugadores = [] # Lista para almacenar los jugadores del equipo
        # Llamar a la función para llenar la lista de valores gaussianos                    
        self.gaussian_vars = fill_gaussian_vars_arr(N_GAUSS)
    
    def agregar_jugador(self, jugador):
        """Agrega un jugador a la lsita de jugadores del equipo"""
        self.jugadores.append(jugador)
        
    def obtener_jugadores(self):
        """Devuelve la lista de jugadores del equipo"""
        return self.jugadores
    
    def generar_nombres(self):
        """Genera nombres de los futbolistas del equipo
        
            Returns:
                list: Lista de nombres generados de los futbolistas del equipo.
        """
        ruta_apellidos = Path(__file__).resolve().parent/"futbolistas"/"apellidos.txt"
        
        with ruta_apellidos.open(encoding="utf-8") as archivo:
            apellidos = [linea.strip() for linea in archivo if linea.strip()]
            
        apellidos_elegidos = random.sample(apellidos, 29)
        
        # Devolvemos la lista de nombres generados
        return [f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}. {apellido}" for apellido in apellidos_elegidos]
    
    def generar_nacionalidad(self):
        """Genera una nacionalidad aleatoria para el futbolista"""
        # Definimos una lista de nacionalidades
        nacion = [
            "arg", "aus", "bra", "bul",
            "cam", "cro", "den", "eng",
            "fra", "ger", "hol", "ire",
            "cor", "ita", "jap", "nig",
            "nor", "saf", "spa", "usa",
            "chi", "jap", "mex", "phi",
            "lit", "por", "rus", "swe",
            "tur", "ukr", "uru", "mor",
            "bel", "can", "ecu", "par",
            "col", "bol", "per", "dom",
            "sui", "hon", "con", "sud"
        ]
        return random.choice(nacion)
    
    def generar_lado_preferido(self):
        """Genera un lado de preferencia aleatorio para el futbolista"""
        lados = ["D-I-C", "D-I", "D-C", "I-C", "D", "I" ]
        return random.choice(lados)
    
    def generar_posicion(self, posiciones):
        """Genera una posición aleatoria para el futbolista"""
        limites = {"por": 2, "def": 8, "mcd": 3, "mc": 6, "mp": 3, "del": 7}
        numeros_puesto = {1: "por", 2: "def", 3: "mcd", 4: "mc", 5: "mp", 6: "del"}
        num_posiciones = [1, 2, 2, 2, 2, 2, 3, 4, 4, 4, 4, 5, 6, 6, 6, 6]
        posicion = random.choice(num_posiciones)
        
        # Si ya no queda hueco en ninguna posición, avisamos con una excepción
        if all(posiciones[puesto] >= limites[puesto] for puesto in limites):
            raise ValueError("No quedan huecos disponibles en ninguna posición")
        
        while True:
            posicion = random.choice(num_posiciones)
            puesto = numeros_puesto[posicion]
            if posiciones[puesto] < limites[puesto]:
                self.posiciones[puesto] += 1
                return puesto
    
    def uniform_random(self, max_value):
        """Genera un número aleatorio uniforme entre 0 y max_value"""
        return random.randint(0, max_value)
    
    def averaged_random(self, average, max_deviation):
        """Genera un número aleatorio con una desvición estandar a partir de un promedio dado"""
        # Seleccionamos un valor aleatorio de la lista de valores gaussianos
        rand_gaussian = self.gaussian_vars[self.uniform_random(N_GAUSS - 1)]
        # Calculamos la desviación esandar a partir del promedio y la desviación máxima
        deviation = max_deviation * rand_gaussian
        return int(average + deviation)
    
    def averaged_random_part_dev(self, average, div):
        """Genera un número aleatorio con una desviación estandar a partir de un promedio dado y una desviación máxima"""
        return self.averaged_random(average, average // div)
    
    def generar_habilidades(self, posicion):
        """Genera habilidades aleatorias para un futbolista"""
        habilidades = {
                    "st": 0,
                    "tk": 0,
                    "ps": 0,
                    "sh": 0,
                }
        
        # Asignamos un valor inicial a las habilidades para el cálculo de las habilidades del futbolista
        habilidad_principal = 14 
        habilidad_media = 11
        habilidad_secundaria = 7
        mitad_habili_secundaria = habilidad_secundaria // 2
        
        # Generamos las habilidades según la posición del futbolista
        # La desviación se ajusta según la importancia de la habilidad para la posición del futbolista
        if posicion == "por":
            habilidades["st"] = self.averaged_random_part_dev(habilidad_principal, 4) # Habilidad principal: 14, desviación: 4
            habilidades["tk"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["ps"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["sh"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
        elif posicion == "def":
            habilidades["st"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["tk"] = self.averaged_random_part_dev(habilidad_principal, 4)
            habilidades["ps"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
            habilidades["sh"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
        elif posicion == "mcd":
            habilidades["st"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["tk"] = self.averaged_random_part_dev(habilidad_media, 3)
            habilidades["ps"] = self.averaged_random_part_dev(habilidad_media, 3)
            habilidades["sh"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
        elif posicion == "mc":
            habilidades["st"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["tk"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
            habilidades["ps"] = self.averaged_random_part_dev(habilidad_principal, 4)
            habilidades["sh"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
        elif posicion == "mp":
            habilidades["st"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["tk"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
            habilidades["ps"] = self.averaged_random_part_dev(habilidad_media, 3)
            habilidades["sh"] = self.averaged_random_part_dev(habilidad_media, 3)
        elif posicion == "del":
            habilidades["st"] = self.averaged_random_part_dev(mitad_habili_secundaria, 2)
            habilidades["tk"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
            habilidades["ps"] = self.averaged_random_part_dev(habilidad_secundaria, 2)
            habilidades["sh"] = self.averaged_random_part_dev(habilidad_principal, 4)
        # Devolver las habilidades generadas
        return habilidades
    
    def atributos_futbolistas(self, nombres):
        """Asigna atributos aleatorios a los futbolistas"""
        futbolista = {} # Diccionario para guardar los atributos de cada futbolista
        plantilla = [] # Lista para guardar los futbolistas del equipo
        self.posiciones = {
            "por": 0,
            "def": 0,
            "mcd": 0,
            "mc": 0,
            "mp": 0,
            "del": 0
        } # Diccionario para contar la cantidad de jugadores por posición
        
        # Asignamos un valor inicial a las 4 habilidades de los furbolistas
        st_hab = 300
        tk_hab = 300
        ps_hab = 300
        sh_hab = 300
        
        # Habilidades generales iniciadas a 0
        partidos = 0
        paradas = 0
        takling = 0
        asistencias = 0
        tiros = 0
        goles = 0
        disciplina = 0
        lesion = 0
        suspension = 0
        adaptacion = 0
        pases_buenos = 0
        
        # Habilidades individuales 
        for nombre in nombres:
            nacionalidad = self.generar_nacionalidad()
            edad = random.randint(18, 35)
            lado_preferido = self.generar_lado_preferido()
            posicion = self.generar_posicion(self.posiciones)
            habilidades = self.generar_habilidades(posicion)
            resistencia = self.averaged_random_part_dev(60, 2)
            agresividad = self.averaged_random_part_dev(30, 3)
            futbolista = {
                "nombre": nombre,
                "nacionalidad": nacionalidad,
                "edad": edad,
                "lado_preferido": lado_preferido,
                "posicion": posicion,
                "habilidades": habilidades,
                "resistencia": resistencia,
                "agresividad": agresividad,
                "st_hab": st_hab,
                "tk_hab": tk_hab,
                "ps_hab": ps_hab,
                "sh_hab": sh_hab,
                "partidos": partidos,
                "paradas": paradas,
                "takling": takling,
                "asistencias": asistencias,
                "tiros": tiros,
                "goles": goles,
                "disciplina": disciplina,
                "lesion": lesion,
                "suspension": suspension,
                "adaptacion": adaptacion,
                "pases_buenos": pases_buenos
            }
            plantilla.append(futbolista)
        return plantilla
    
    def crear_equipo(self):
        """Crea un equipo asociado al nuevo usuario"""
        nombres = self.generar_nombres()
        plantilla = self.atributos_futbolistas(nombres)
        return plantilla