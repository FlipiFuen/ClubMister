import os
import json
import random

from collections import defaultdict

from clubs.models import Equipo, Futbolista

from administracion.Partidos.constantes import *

class Arbitro:
    def __init__(self, nombre, severidad, origen, usado):
        self.nombre = nombre.strip()
        self.severidad = int(severidad)
        self.origen = origen.strip()
        self.usado = int(usado)

    def __str__(self):
        # Formatear la salida para que coincida con el formato de los árbitros en el archivo
        return f"{self.nombre:<24} {self.severidad:<16} {self.origen:<24} {self.usado}"

    def marcar_usado(self):
        """Marca al árbitro como usado."""
        self.usado += 1

    def cargar_arbitros(ruta_archivo=RUTA_ARBITROS):
        """Carga los árbitros desde un archivo y devuelve una lista de objetos Arbitro."""
        arbitros_cargados = []
        if not os.path.exists(ruta_archivo):
            print(f"El archivo de árbitros no existe: {ruta_archivo}")
            return None

        with open(ruta_archivo, "r") as file:
            lineas = file.readlines()
        if len(lineas) < 2:
            print("El archivo de árbitros está vacío o no tiene el formato correcto.")
            return None

        for linea_raw in lineas[2:]: # Saltar las dos primeras líneas
            linea = linea_raw.strip()
            if not linea:
                continue
            try:
                nombre = linea[0:24].strip()
                severidad_str = linea[24:40].strip()
                origen = linea[40:64].strip()
                usado_str = linea[64:].strip()
                if not nombre or not severidad_str or not origen or not usado_str:
                    print(f"Datos incompletos en la línea: {linea}")
                    continue
                arbitros_cargados.append(Arbitro(nombre, severidad_str, origen, usado_str))
            except (ValueError, IndexError) as e:
                print(f"Error al procesar la línea '{linea}': {e}")
                continue
        return arbitros_cargados

    def seleccionar_arbitro_disponible(lista_arbitros_actual):
        """Selecciona un árbitro disponible de la lista de árbitros cargados."""
        if not lista_arbitros_actual:
            print("No hay árbitros disponibles.")
            return None
        disponibles = [arbitro for arbitro in lista_arbitros_actual if arbitro.usado <= 3]
        if not disponibles:
            print("No hay árbitros disponibles.")
            return None
        arbitro_seleccionado = random.choice(disponibles)
        arbitro_seleccionado.marcar_usado()
        print(f"Árbitro seleccionado: {arbitro_seleccionado}")
        return arbitro_seleccionado

    def guardar_arbitros(lista_arbitros_actual, ruta_archivo=RUTA_ARBITROS):
        """ Actualiza el archivo de árbitros con la lista actualizada."""
        if lista_arbitros_actual is None:
            print("No hay árbitros para guardar.")
            return
        with open(ruta_archivo, "w") as file:
            file.write("Name                Strictness        From                  Used\n")
            file.write("----------------------------------------------------------------\n")
            for arbitro in lista_arbitros_actual:
                file.write(str(arbitro) + "\n")
        print(f"Árbitros guardados en {ruta_archivo}")

class EquipoSimulado:
    def __init__(self, nombre_equipo, ruta_archivo_alineacion, es_local, juego): # juego es una referencia al objeto Partido
        self.django_equipo = nombre_equipo # Objeto Equipo de Django
        self.nombre = self.django_equipo.nombre_equipo
        self.es_local = es_local
        self.juego = juego # Referencia al objeto Partido para acceder a configuraciones globales o al oponente

        self.alineacion_data = self._cargar_alineacion(ruta_archivo_alineacion)
        if self.alineacion_data is None:
            print(f"Error al cargar la alineación para el equipo {self.nombre}. Alineación no cargada.")
            return
        self.tactica_actual = self.alineacion_data.get("tactica", "N")[-1] # Táctica del equipo, por defecto "N"
        self.instrucciones_condicionales = self.alineacion_data.get("instrucciones", {
            "cambiosTactica": [],
            "substituciones": [],
            "reposiciones": []
        })

        self.jugadores_campo = {} # Diccionario de objetos JugadorPartido
        self.jugadores_banquillo = {} 
        self._inicializar_plantilla()

        # Metricas del partido
        self.team_tackling = 0.0
        self.team_passing = 0.0
        self.team_shooting = 0.0
        self.agresion = 0.0
        self.probabilidad_tiro = 0.0
        self.probabilidad_pase = 0.0
        self.goles = 0
        self.minutos_posesion = 0
        self.faltas_cometidas_equipo = 0
        self.tarjetas_amarillas = 0
        self.tarjetas_rojas = 0
        self.lesion = 0
        self.corners = 0

        # Array de tácticas para este equipo
        num_posicion_categorias = 6
        num_skill_categorias = 4
        self.tact_array_equipo = [[0.0 for _ in range(num_skill_categorias)] for _ in range(num_posicion_categorias)]

    def _cargar_alineacion(self, ruta_archivo):
        """ Carga la alineación del equipo desde un archivo JSON y devuelve un diccionario con la información de la alineación.
        """
        try:
            with open(ruta_archivo, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Archivo de alineación no encontrado: {ruta_archivo}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error al decodificar el archivo JSON: {e}")
            return None

    def _inicializar_plantilla(self):
        """ Inicializa la plantilla del equipo cargando los jugadores desde la base de datos de Django. """
        if self.alineacion_data is None:
            print(f"No se pudo inicializar la plantilla del equipo {self.nombre} porque la alineación no está cargada.")
            return
        jugadores_seleccionados = self.alineacion_data.get("jugador_seleccionado", {})
        posiciones_seleccionadas = self.alineacion_data.get("posicion_seleccionada", {})

        claves_jugadores_ordenadas = sorted(
            [k for k in jugadores_seleccionados.keys() if k.startswith("jug")],
            key=lambda x: int(x[3:])  # Ordenar por el número después de "jug"
        )

        for i, key_jugador in enumerate(claves_jugadores_ordenadas):
            nombre_jugador = jugadores_seleccionados.get(key_jugador)
            if not nombre_jugador:
                continue
            try:
                futbolista_obj = Futbolista.objects.get(nombre=nombre_jugador, equipo=self.django_equipo)
                # Determinar posicion inicial
                clave_posicion = f"pos{key_jugador[3:]}"
                posicion_inicial = posiciones_seleccionadas.get(clave_posicion)

                if not posicion_inicial:
                    print(f"Posición no encontrada para el jugador {nombre_jugador}. Asignando posición por defecto.")
                    posicion_inicial = "Central"

                jugador_partido_obj = JugadorPartido(futbolista_obj, posicion_inicial, key_jugador)
                
                if i < 11:  # Los primeros 11 jugadores son titulares
                    self.jugadores_campo[key_jugador] = jugador_partido_obj
                    if key_jugador == "jug0":
                        jugador_partido_obj.posicion_actual = "Portero"  # Asegurar que el primer jugador es el portero
                        jugador_partido_obj.posicion_inicial = "Portero"
                else:  # Los demás son suplentes
                    self.jugadores_banquillo[key_jugador] = jugador_partido_obj
                    jugador_partido_obj.esta_en_campo = False
            except Futbolista.DoesNotExist:
                print(f"Jugador {nombre_jugador} no encontrado en la base de datos para el equipo {self.nombre}.")
                continue
        print(f"Plantilla del equipo {self.nombre} inicializada con {len(self.jugadores_campo)} jugadores en campo y {len(self.jugadores_banquillo)} en el banquillo.")

    def aplicar_bonus_tactica(self, tactica_oponente_char=None):
        """Aplica el bonus de tactica al array de tácticas del equipo."""
        detalles_tactica = BASE_TACTICS_CONFIG.get(self.tactica_actual)
        if not detalles_tactica:
            print(f"Táctica {self.tactica_actual} no válida para el equipo {self.nombre}.")
            # Asignar valores por defecto
            detalles_tactica = BASE_TACTICS_CONFIG.get("N")


        # Aplicar valores base de la táctica
        for pos, skill, val in detalles_tactica.get("base", []):
            self.tact_array_equipo[pos][skill] = val

        # Aplicar modificaciones de posiciones
        for pos, skill, val in detalles_tactica.get("positions_mods", []):
            self.tact_array_equipo[pos][skill] = val

        # Aplicar modificaciones según la táctica del oponente
        condicion_oponente_cfg = detalles_tactica.get("opponent_condition")
        if condicion_oponente_cfg and tactica_oponente_char:
            config_para_check = {"tactical_ver": True}
            if condicion_oponente_cfg["check"](tactica_oponente_char, config_para_check):
                for pos, skill, val_mod in condicion_oponente_cfg.get("mods", []):
                    self.tact_array_equipo[pos][skill] = val_mod

        # Aplicar modificaciones específicas contra tácticas concretas
        if tactica_oponente_char:
            specific_vs_bonuses = detalles_tactica.get("vs_specific_tactics", {}).get(tactica_oponente_char, [])
            if specific_vs_bonuses:
                print(f"Aplicando bonificaciones específicas contra la táctica {tactica_oponente_char} para el equipo {self.nombre}.")
                for pos, skill, val_bonus_aditivo in specific_vs_bonuses:
                    self.tact_array_equipo[pos][skill] += val_bonus_aditivo
                    print(f"Bonus en Pos {pos}, Skill {skill}: +{val_bonus_aditivo:.2f}. Nuevo valor: {self.tact_array_equipo[pos][skill]:.2f}")

    def calcular_probabilidad_tiro(self, equipo_oponente_sim, es_equipo_local):
        """Calcula la probabilidad de tiro para un equipo."""
        agresion = self.agresion
        team_shooting = self.team_shooting
        team_passing = self.team_passing
        oponente_team_tackling = equipo_oponente_sim.team_tackling if equipo_oponente_sim else 0.0

        team_aggression = agresion / 50.0
        numerador_skills = (1.0/3.0 * float(team_shooting)) + (2.0/3.0 * float(team_passing))
        denominador_skills = oponente_team_tackling + 1.0
        skills_ratio_sq = (numerador_skills / denominador_skills) ** 2 if denominador_skills != 0 else 0
        probabilidad_calculada = 2.7 * (team_aggression + 1400.0 * skills_ratio_sq)
        if es_equipo_local:
            probabilidad_calculada += bonus_local
        self.probabilidad_tiro = probabilidad_calculada

    def calcular_probabilidad_pase(self, pasador, zona_actual_balon, equipo_oponente_sim):
        """
        Calcula la probabilidad de que un pase realizado por 'pasador' sea exitoso.

        Args:
            pasador (JugadorPartido): El jugador que realiza el pase.
            zona_actual_balon (str): La zona del campo desde donde se realiza el pase.
            equipo_oponente_sim (EquipoSimulado): El equipo defensor.

        Returns:
            float: Una probabilidad entre 0 y 9999 (para usar con random.randint).
        """
        if not pasador or not pasador.esta_en_campo or pasador.lesionado or pasador.expulsado:
            return 0.0
        
        # Habilidad del pasador y fatiga
        try:
            habilidad_ps_pasador = float(pasador.django_futbolista.ps)
        except (AttributeError, ValueError):
            habilidad_ps_pasador = 50 # Valor por defecto si no se encuentra la habilidad

        factor_fatiga = pasador.resistencia_actual / 100.0

        prob_base_habilidad = ( habilidad_ps_pasador * factor_fatiga ) * 80 # Base de probabilidad de pase, escala de 0 a 8000

        # Presion defensiva del oponente
        presion_oponente = equipo_oponente_sim.team_tackling if equipo_oponente_sim else 0.0
        mod_presion = max(0, 1000 - (presion_oponente * 5))  # Modificador de presión defensiva, escala de 0 a 1000

        # Modificador por zona de campo
        base_zona_pase, banda_pase = descomponer_zona(zona_actual_balon)
        mod_zona = 0
        if base_zona_pase == ZONA_BASE_DEFENSIVA_PROPIA:
            mod_zona = 1500 # Pases mas seguros en la zona defensiva
        elif base_zona_pase == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
            mod_zona = 900
        elif base_zona_pase == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
            mod_zona = -200 # Pases menos seguros en el medio campo ofensivo
            if banda_pase and banda_pase != BANDA_CENTRO:
                mod_zona -= 80 # Mas dificil en las bandas
        elif base_zona_pase == ZONA_BASE_ATAQUE:
            mod_zona = -700 # Pases menos seguros en la zona de ataque
            if banda_pase and banda_pase != BANDA_CENTRO:
                mod_zona -= 100 # Mas dificil en las bandas
        elif zona_actual_balon == ZONA_BASE_AREA_RIVAL:
            mod_zona = -1100 # Pases muy arriesgados en el área rival
            if banda_pase and banda_pase != BANDA_CENTRO:
                mod_zona -= 150 # Mas dificil en las bandas

        # Tactica del equipo
        mod_tactica = 0
        if self.tactica_actual == "P":
            mod_tactica = 500 # Táctica P favorece los pases
            if banda_pase and banda_pase != BANDA_CENTRO:
                mod_tactica += 200
        elif self.tactica_actual == "L":
            mod_tactica = -300 # Táctica L favorece los pases menos 
            if banda_pase and banda_pase != BANDA_CENTRO:
                mod_tactica += 150 # Por banda es efectivo
        elif self.tactica_actual == "A":
            if base_zona_pase in [ZONA_BASE_ATAQUE, ZONA_BASE_AREA_RIVAL]:
                mod_tactica += 200


        # Calcular la probabilidad final
        probabilidad_final = prob_base_habilidad + mod_presion + mod_zona + mod_tactica
        probabilidad_final = max(500, min(probabilidad_final, 9900))  # Limitar entre 500 y 9500
        return int(probabilidad_final)

    def actualizar_metricas_equipo(self, jugador):
        """Actualiza las métricas del equipo con las estadísticas del jugador."""
        if hasattr(jugador, 'tk_contrib') and hasattr(jugador, 'ps_contrib') and hasattr(jugador, 'sh_contrib'):
            self.team_tackling += jugador.tk_contrib
            self.team_passing += jugador.ps_contrib
            self.team_shooting += jugador.sh_contrib

    def calcular_agresion_equipo(self):
        """Calcula la agresión del equipo basado en las estadísticas de los jugadores."""
        total_agresion = 0.0
        team_agg_tactic = 10.0 # Táctica de agresión del equipo
        for jugador_obj in self.jugadores_campo.values():
            if jugador_obj and jugador_obj.esta_en_campo and not jugador_obj.lesionado and not jugador_obj.expulsado: # django_futbolista es el objeto JugadorPartido
                total_agresion += float(getattr(jugador_obj.django_futbolista, 'agresividad', 20.0))  # Valor por defecto de agresión si no existe
        agresion_calculada = (total_agresion * team_agg_tactic) / 100.0
        self.agresion = agresion_calculada

    def _evaluar_condicion_numerica(self, valor_actual, operador, valor_objetivo_str):
        """Evalúa una condición numérica (minuto, resultado, resistencia)."""
        if valor_objetivo_str is None:
            return True # La condicion no esta activa
        try:
            valor_objetivo = int(valor_objetivo_str)
        except ValueError:
            print(f"Valor objetivo no válido: {valor_objetivo_str}. Debe ser un número entero.")
            return False

        if operador == ">=":
            return valor_actual >= valor_objetivo
        elif operador == "<=":
            return valor_actual <= valor_objetivo
        elif operador == "=":
            return valor_actual == valor_objetivo
        elif operador == ">":
            return valor_actual > valor_objetivo
        elif operador == "<":
            return valor_actual < valor_objetivo
        return False

    def get_alineacion_str(self):
        """Devuelve una representación en cadena de la alineación del equipo."""
        if not self.alineacion_data:
            return "No hay alineación cargada.\n"
        
        output_lines = []

        tactica_config = self.alineacion_data.get("tactica", "N")
        tactica_inicial_char = tactica_config[-1]
        if isinstance(tactica_config, list) and tactica_config:
            tactica_inicial_char = tactica_config[-1]
        elif isinstance(tactica_config, list) and not tactica_config:
            tactica_inicial_char = "N" # Por defecto
        output_lines.append(f"Táctica inicial: {tactica_inicial_char}\n")

        jugadores_seleccionados = self.alineacion_data.get("jugador_seleccionado", {})
        posiciones_seleccionadas = self.alineacion_data.get("posicion_seleccionada", {})

        claves_jugadores_ordenadas = sorted(
            [k for k in jugadores_seleccionados.keys() if k.startswith("jug") and k[3:].isdigit()],
            key=lambda x: int(x[3:])  # Ordenar por el número después de "jug"
        )
        output_lines.append("Alineación titular:\n")
        titulares_count = 0
        for key_jugador in claves_jugadores_ordenadas:
            if titulares_count >= 11:
                break
            nombre_jugador = jugadores_seleccionados.get(key_jugador)
            if not nombre_jugador:
                continue

            clave_posicion_num_str = key_jugador[3:]
            posicion_jugador_original = posiciones_seleccionadas.get(f"pos{clave_posicion_num_str}")

            if key_jugador == "jug0":
                posicion_display = "Portero"
            elif not posicion_jugador_original:
                posicion_display = "Central"
            else:
                posicion_display = posicion_jugador_original

            output_lines.append(f"               - {nombre_jugador} ({posicion_display})\n")
            titulares_count += 1


        capitan_nombre = self.alineacion_data.get("capitan")
        tirador_nombre = self.alineacion_data.get("tirador_seleccionado")

        if capitan_nombre:
            output_lines.append(f"Capitán: {capitan_nombre}\n")
        if tirador_nombre:
            output_lines.append(f"Lanzador de penaltis: {tirador_nombre}\n")

        output_lines.append("Jugadores en el banquillo:\n")
        suplentes_info_list = []
        for i, key_jugador in enumerate(claves_jugadores_ordenadas):
            if i < 11:
                continue
            nombre_jugador = jugadores_seleccionados.get(key_jugador)
            if not nombre_jugador:
                continue
            clave_posicion_num_str = key_jugador[3:]
            posicion_jugador_original = posiciones_seleccionadas.get(f"pos{clave_posicion_num_str}", "Banquillo")
            suplentes_info_list.append(f"               - {nombre_jugador} ({posicion_jugador_original})\n")
        if suplentes_info_list:
            output_lines.extend(suplentes_info_list)
        else:
            output_lines.append("               - No hay suplentes definidos.\n")

        return "".join(output_lines)

    def _verificar_condicion_tarjeta_lesion(self, tipo_evento, especificacion):
        """Verifica si se debe aplicar una condición de tarjeta o lesión."""
        if not especificacion:
            return True # Si no hay especificación, la condición no está activa

        equipo_revisar = self
        oponente = self.juego.get_oponente(self)  # Método que debe implementarse en la clase Partido para obtener el equipo contrario

        if especificacion.startswith("OPP:"):
            if not oponente:
                return False # No hay oponente para verificar
                equipo_revisar = oponente
                especificacion = especificacion[4:]  # Eliminar "OPP:" para procesar el número
        elif especificacion.startswith("OPP_TOTAL:"):
            if not oponente: 
                return False # No hay oponente para verificar
            try:
                num_objetivo = int(especificacion[10:])
                count = 0
                for jug_p in oponente.jugadores_campo.values():
                    if tipo_evento == "roja" and jug_p.expulsado: 
                        count += 1
                    elif tipo_evento == "amarilla" and jug_p.tarjeta_amarilla > 0:
                        count += 1
                    elif tipo_evento == "lesion" and jug_p.lesionado:
                        count += 1
                return count >= num_objetivo
            except ValueError:
                print(f"Especificación no válida para oponente: {especificacion}. Debe ser 'OPP:<número>'.")
                return False
        if especificacion.startswith("TOTAL:"):
            try:
                num_objetivo = int(especificacion[6:])
                count = 0
                for jug_p in self.jugadores_campo.values():
                    if tipo_evento == "roja" and jug_p.expulsado: 
                        count += 1
                    elif tipo_evento == "amarilla" and jug_p.tarjeta_amarilla > 0:
                        count += 1
                    elif tipo_evento == "lesion" and jug_p.lesionado:
                        count += 1
                return count >= num_objetivo
            except ValueError:
                print(f"Especificación no válida: {especificacion}. Debe ser 'TOTAL:<número>'.")
                return False
        # Comprobar por posicion
        for jug_p in equipo_revisar.jugadores_campo.values():
            if not jug_p.esta_en_campo or jug_p.lesionado or jug_p.expulsado:
                continue
            cumple_evento = False
            if tipo_evento == "roja" and jug_p.expulsado:
                cumple_evento = True
            elif tipo_evento == "amarilla" and jug_p.tarjeta_amarilla > 0:
                cumple_evento = True
            elif tipo_evento == "lesion" and jug_p.lesionado:
                cumple_evento = True

            if cumple_evento:
                rol_jugador = CATEGORIAS_POSICIONES.get(jug_p.posicion_actual)
                map_idx_rol = {
                    0: "GK", 1: "DFC", 1: "DFL", 1: "DFR", 1: "DFCR", 1: "DFCL",
                    2: "MCD", 2: "MC", 2: "MCI", 2: "MCDR", 2: "MCDL",
                    3: "DC", 3: "DCL", 3: "DCR", 3: "ED", 3: "EI",
                    4: "DML", 4: "DMR",
                    5: "MPL", 5: "MPR", 5: "MP"
                } 
                rol_str = map_idx_rol.get(rol_jugador)

                if especificacion == "ANY" or especificacion == rol_str:
                    return True
        return False

    def procesar_instrucciones_minuto(self, minuto_actual):
        """Procesa las instrucciones condicionales para el minuto actual del partido."""
        if not self.juego:
            print("No hay referencia al partido para procesar las instrucciones.")
            return
        oponente = self.juego.get_equipo_oponente(self)
        goles_oponente = oponente.goles if oponente else 0
        diferencia_goles = self.goles - goles_oponente

        for i, instruccion in enumerate(self.instrucciones_condicionales.get("cambiosTactica", [])):
            if instruccion.get("usada_una_vez", False):
                continue

            activada = True
            # Evaluar minuto
            if not self._evaluar_condicion_numerica(minuto_actual, instruccion.get("minOp"), instruccion.get("minVal")):
                activada = False
            # Evaluar resultado
            if not self._evaluar_condicion_numerica(diferencia_goles, instruccion.get("resOp"), instruccion.get("resVal")):
                activada = False
            # Evaluar tarjetas rojas
            if activada and not self._verificar_condicion_tarjeta_lesion("roja", instruccion.get("roja")):
                activada = False
            # Evaluar tarjetas amarillas
            if activada and not self._verificar_condicion_tarjeta_lesion("amarilla", instruccion.get("amarilla")):
                activada = False
            # Evaluar lesiones
            if activada and not self._verificar_condicion_tarjeta_lesion("lesion", instruccion.get("lesion")):
                activada = False

            if activada:
                nueva_tactica_char = instruccion.get("nueva")
                if nueva_tactica_char and nueva_tactica_char != self.tactica_actual:
                    self.cambiar_tactica(nueva_tactica_char)
                    self.instrucciones_condicionales["cambiosTactica"][i]["usada_una_vez"] = True # 
                    break # Solo se aplica una táctica por minuto
        # Procesar sustituciones
        substituciones_hechas_minuto = 0
        for i, instruccion in enumerate(self.instrucciones_condicionales.get("substituciones", [])):
            if self.juego.substituciones_realizadas_equipo[self.nombre] >= self.juego.num_substituciones:
                print(f"Máximo de sustituciones alcanzado para {self.nombre}. No se pueden realizar más sustituciones.")
                break
            if instruccion.get("fue_activada_antes", False) and instruccion.get("fue_activada_antes", False):
                continue
                 
            activada = True
            # Evaluar minuto, resultado, tarjetas y lesiones
            if not self._evaluar_condicion_numerica(minuto_actual, instruccion.get("minOp"), instruccion.get("minVal")):
                activada = False
            if activada and not self._evaluar_condicion_numerica(diferencia_goles, instruccion.get("resOp"), instruccion.get("resVal")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("roja", instruccion.get("roja")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("amarilla", instruccion.get("amarilla")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("lesion", instruccion.get("lesion")):
                activada = False

            # Evaluar condicion especifica de jugador
            jugador_sustituir = None
            if activada and "condicion_jugador" in instruccion:
                cond_jug = instruccion["condicion_jugador"]
                for nombre_jug_campo, jug_p in self.jugadores_campo.items():
                    if not jug_p.esta_en_campo or jug_p.lesionado or jug_p.expulsado:
                        continue
                    
                    # Comprobar rol/nombre
                    rol_coincide = False
                    if cond_jug.get("rol"):
                        if jug_p.posicion_actual == cond_jug["rol"] or jug_p.nombre == cond_jug.get("rol"):
                            rol_coincide = True
                    else:
                        rol_coincide = True # Si no hay rol, se asume que cualquier jugador puede ser sustituido

                    if rol_coincide:
                        # Comprobar resistencia
                        if "resistenciaMax" in cond_jug:
                            if not self._evaluar_condicion_numerica(jug_p.resistencia_actual, "<=", cond_jug.get("resistenciaMax")):
                                continue

                        # Si se cumplen todas las condiciones
                        jugador_sustituir = jug_p
                        break # Salir del bucle si se encuentra un jugador que cumple las condiciones
                if not jugador_sustituir:
                    print(f"Condición de sustitución no cumplida para {instruccion}. No se encontró un jugador adecuado.")
                    activada = False
            if activada:
                sale_ref = instruccion.get("sale")
                entra_ref = instruccion.get("entra")
                pos_entra = instruccion.get("posicion")

                jugador_sale_obj = None
                jugador_entra_obj = None

                if jugador_sustituir:
                    jugador_sale_obj = jugador_sustituir
                elif sale_ref == "ANY_ROL" and jugador_sustituir:
                    jugador_sale_obj = jugador_sustituir
                elif sale_ref:
                    # Buscar jugador por nombre, rol o dorsal
                    prefijo = "jug"
                    for key, jug_p_obj in self.jugadores_campo.items():
                        if jug_p_obj.esta_en_campo and not jug_p_obj.lesionado and not jug_p_obj.expulsado:
                            if jug_p_obj.nombre == sale_ref or jug_p_obj.posicion_actual == sale_ref:
                                jugador_sale_obj = jug_p_obj
                                break
                        if sale_ref.isdigit():
                            try:
                                dorsal_buscado = int(sale_ref)
                                dorsal_sale = int(jug_p_obj.key_jugador[len(prefijo):]) + 1
                                if dorsal_sale == dorsal_buscado:
                                    jugador_sale_obj = jug_p_obj
                                    break
                            except ValueError:
                                pass
                if jugador_sale_obj and (jugador_sale_obj.lesionado or jugador_sale_obj.expulsado):
                    print(f"Jugador {jugador_sale_obj} no esta en el campo para ser substituido")
                    jugador_sale_obj = None

                if entra_ref:
                    prefijo = "jug"
                    for key, jug_p_obj in self.jugadores_banquillo.items():
                        if jug_p_obj.nombre == entra_ref or jug_p_obj.posicion_original == entra_ref:
                            jugador_entra_obj = jug_p_obj
                            break
                        if entra_ref.isdigit():
                            try:
                                dorsal_buscado = int(entra_ref)
                                dorsal_entra = int(jug_p_obj.key_jugador[len(prefijo):]) + 1
                                if dorsal_entra == dorsal_buscado:
                                    jugador_entra_obj = jug_p_obj
                                    break
                            except ValueError:
                                pass

                if jugador_sale_obj and jugador_entra_obj and pos_entra:
                    print(f"MIN {minuto_actual}: {self.nombre} - Condición de sustitución activada. Sustituyendo a {jugador_sale_obj.nombre} ({jugador_sale_obj.posicion_actual}) por {jugador_entra_obj.nombre} ({pos_entra}).")
                    exito_sustitucion = self.juego.realizar_sustitucion(self, jugador_sale_obj, jugador_entra_obj, pos_entra)
                    if exito_sustitucion:
                        self.juego.generar_comentario_evento("SUB", self, jugador_entra_obj, jugador_sale_obj, datos_adicionales={"<posi>": pos_entra})
                        self.instrucciones_condicionales["substituciones"][i]["fue_activada_antes"] = True
                        substituciones_hechas_minuto += 1
                        if substituciones_hechas_minuto >= self.juego.num_substituciones:
                            print(f"Máximo de sustituciones alcanzado para {self.nombre}. No se pueden realizar más sustituciones.")
                            break
                else:
                    if not jugador_sale_obj:
                        print(f"Error: No se encontró un jugador para sustituir en {self.nombre} con referencia '{sale_ref}'.")
                        if not jugador_entra_obj and entra_ref:
                            print(f"Error: No se encontró un jugador para entrar en {self.nombre} con referencia '{entra_ref}'.")

        # Procesar reposiciones
        for i, instruccion in enumerate(self.instrucciones_condicionales.get("reposiciones", [])):
            if instruccion.get("fue_activada_antes", False):
                continue

            activada = True
            # Evaluar minuto, resultado, tarjetas y lesiones
            if not self._evaluar_condicion_numerica(minuto_actual, instruccion.get("minOp"), instruccion.get("minVal")):
                activada = False
            if activada and not self._evaluar_condicion_numerica(diferencia_goles, instruccion.get("resOp"), instruccion.get("resVal")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("roja", instruccion.get("roja")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("amarilla", instruccion.get("amarilla")):
                activada = False
            if activada and not self._verificar_condicion_tarjeta_lesion("lesion", instruccion.get("lesion")):
                activada = False

            if activada:
                jugador_mover_obj = None
                dorsal_buscado = None
                prefijo = "jug"
                nombre_jugador_mover = instruccion.get("jugador")
                if nombre_jugador_mover.isdigit():
                    dorsal_buscado = int(nombre_jugador_mover)

                nueva_pos = instruccion.get("posicion")
                for jug_p_obj in self.jugadores_campo.values():
                    if jug_p_obj == nombre_jugador_mover and jug_p_obj.esta_en_campo and not jug_p_obj.lesionado and not jug_p_obj.expulsado:
                        jugador_mover_obj = jug_p_obj
                        break
                    if dorsal_buscado and int(jug_p_obj.key_jugador[len(prefijo):]) + 1 == dorsal_buscado:
                        jugador_mover_obj = jug_p_obj
                        break
                if jugador_mover_obj and nueva_pos:
                    print(f"MIN {minuto_actual}: {self.nombre} - Condición de reposicionamiento activada. Moviendo a {jugador_mover_obj.nombre} de {jugador_mover_obj.posicion_actual} a {nueva_pos}.")
                    jugador_mover_obj = jug_p_obj
                    self.juego.generar_comentario_evento("CHANGEPOSITION", self, jugador_principal=jugador_mover_obj, jugador_secundario=nueva_pos)
                    jugador_mover_obj.posicion_actual = nueva_pos
                    self.instrucciones_condicionales["reposiciones"][i]["fue_activada_antes"] = True
                    break

    def cambiar_tactica(self, nueva_tactica_char):
        """Cambia la táctica del equipo."""
        if nueva_tactica_char == self.tactica_actual:
            print(f"La táctica {nueva_tactica_char} ya está activa para el equipo {self.nombre}.")
            return 

        self.tactica_actual = nueva_tactica_char

        oponente = self.juego.get_equipo_oponente(self)  # Método que debe implementarse en la clase Partido para obtener el equipo contrario
        tactica_oponente_char = oponente.tactica_actual if oponente and hasattr(oponente, 'tactica_actual') else None

        self.juego.generar_comentario_evento("CHANGETACTIC", self, nueva_tactica_char)

        self.aplicar_bonus_tactica(tactica_oponente_char)
        if oponente:
            oponente.aplicar_bonus_tactica(self.tactica_actual)

    def seleccionar_jugador_contribucion(self, tipo_contribucion, zona_actual_balon):
        """Selecciona un jugador del equipo basado en su contribucion, priorizando la posicion."""
        jugadores_aptos_todos = [
            jug_p for jug_p in self.jugadores_campo.values()
            if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and hasattr(jug_p, tipo_contribucion)               
        ]
        if not jugadores_aptos_todos:
            print(f"No hay jugadores aptos para la contribución {tipo_contribucion} en el equipo {self.nombre}.")
            return None

        _base_zona_balon, banda_balon = descomponer_zona(zona_actual_balon)

        jugadores_zona_preferida = []
        if banda_balon:
            for jug_p in jugadores_aptos_todos:
                bandas_jugador = get_bandas_para_posicion(jug_p.posicion_actual)
                if banda_balon in bandas_jugador:
                    jugadores_zona_preferida.append(jug_p)
        jugadores_a_considerar = jugadores_zona_preferida if jugadores_zona_preferida else jugadores_aptos_todos

        total_contribucion = sum(getattr(jug_p, tipo_contribucion, 0) for jug_p in jugadores_a_considerar)
        
        # Aplicar bonus de zona/posicion
        contribuciones_ajustadas = []
        total_contribucion_ajustado = 0.0

        base_zona_balon, _ = descomponer_zona(zona_actual_balon)
        
        for jug_p in jugadores_a_considerar:
            base_contrib = getattr(jug_p, tipo_contribucion, 0)
            bonus_factor_posicion = 1.0
            pos_category_idx = CATEGORIAS_POSICIONES.get(jug_p.posicion_actual)

            if pos_category_idx is not None:
                tipos_zona_aplicables = []
                if base_zona_balon in [ZONA_BASE_DEFENSIVA_PROPIA, ZONA_BASE_MEDIO_CAMPO_DEFENSIVO]:
                    tipos_zona_aplicables.append('Defensivo')
                if base_zona_balon in [ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, ZONA_BASE_MEDIO_CAMPO_OFENSIVO]:
                    tipos_zona_aplicables.append('Medios')
                if base_zona_balon in [ZONA_BASE_MEDIO_CAMPO_OFENSIVO, ZONA_BASE_ATAQUE, ZONA_BASE_AREA_RIVAL]:
                    tipos_zona_aplicables.append('Ofensivo')

                max_bonus = 1.0
                for tipo_zona in tipos_zona_aplicables:
                    if tipo_zona in BONUS_POSICION_ZONA and pos_category_idx in BONUS_POSICION_ZONA[tipo_zona]:
                        max_bonus = max(max_bonus, BONUS_POSICION_ZONA[tipo_zona][pos_category_idx])

                bonus_factor_posicion = max_bonus

            contribucion_ajustada = base_contrib * bonus_factor_posicion
            contribuciones_ajustadas.append((jug_p, contribucion_ajustada))
            total_contribucion_ajustado += contribucion_ajustada                   

        if total_contribucion <= 0:
            if not jugadores_a_considerar:
                return random.choice(jugadores_aptos_todos) if jugadores_aptos_todos else None
            return random.choice(jugadores_a_considerar)

        valor_aleatorio = random.uniform(0, total_contribucion)
        contribucion_acumulada = 0
        for jug_p, contribucion_ajustada in contribuciones_ajustadas:
            contribucion_acumulada += contribucion_ajustada
            if valor_aleatorio <= contribucion_acumulada:
                return jug_p

        return random.choice(jugadores_a_considerar) if jugadores_a_considerar else None  # En caso de que algo falle, seleccionar aleatoriamente

    def get_portero_actual(self):
        """Obtiene el portero actual del equipo."""
        for jug_p in self.jugadores_campo.values():
            if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and jug_p.posicion_actual == "Portero":
                return jug_p
        return None

    def seleccionar_jugador_por_agresion(self):
        """Selecciona un jugador del equipo basado en su agresividad."""
        jugadores_aptos = [
            jug_p for jug_p in self.jugadores_campo.values()
            if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado
        ]      
        if not jugadores_aptos:
            return None

        total_agresion_ponderada = 0
        jugadores_con_peso = []
        for jug_p in jugadores_aptos:
            try:
                base_agresion = float(jug_p.django_futbolista.agresividad)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error al obtener estadísticas del jugador {jug_p.nombre}: {e}")
                base_agresion = 20.0 # Valor por defecto

            factor_posicion = 0.2 if jug_p.posicion_actual == "Portero" else 1.0
            peso = base_agresion * factor_posicion * (jug_p.resistencia_actual / 100.0) # Considerar fatiga
            total_agresion_ponderada += peso
            jugadores_con_peso.append((jug_p, peso))

        if total_agresion_ponderada <= 0:
            return random.choice(jugadores_aptos) if jugadores_aptos else None

        valor_aleatorio = random.uniform(0, total_agresion_ponderada)
        agresion_acumulada = 0
        for jug_p, peso in jugadores_con_peso:
            agresion_acumulada += peso
            if valor_aleatorio <= agresion_acumulada:
                return jug_p

        return random.choice(jugadores_aptos) if jugadores_aptos else None


class JugadorPartido:
    def __init__(self, django_futbolista_obj, posicion_inicial, key_jugador):
        self.django_futbolista = django_futbolista_obj
        self.key_jugador = key_jugador 
        self.nombre = self.django_futbolista.nombre
        self.posicion_actual = posicion_inicial
        self.posicion_original = posicion_inicial # Posición original del jugador

        # Atributos de estado durante el partido
        self.resistencia_actual = float(self.django_futbolista.resistencia)
        self.minutos_jugados = 0
        self.esta_en_campo = True

        # Contribuciones, se calculan por minuto
        self.tk_contrib = 0.0
        self.ps_contrib = 0.0
        self.sh_contrib = 0.0

        # Estadisticas del jugador
        self.pases_completados_partido = 0
        self.pases_intentados_partido = 0
        self.intercepciones_partido = 0
        self.asistencias_partido = 0
        self.goles_partido = 0
        self.goles_propia_partido = 0
        self.paradas_partido = 0
        self.goles_concedidos_partido = 0
        self.disparos_puerta_partido = 0
        self.disparos_fuera_partido = 0

        # Estado disciplinario y médico
        self.faltas_cometidas_partido = 0
        self.faltas_recibidas = 0
        self.advertido = False
        self.tarjeta_amarilla_partido = 0
        self.tarjeta_roja_partido = 0
        self.expulsado = False
        self.lesionado = False
        self.semanas_lesionado = 0
        self.minuto_lesion = 0

    def __str__(self):
        return f"{self.nombre} ({self.posicion_actual}) - Resistencia: {self.resistencia_actual:.0f}"

    def reducir_resistencia(self, REDUCCION_RESISTENCIA_POR_MINUTO):
        """Reduce la resistencia del jugador por minuto."""
        if self.esta_en_campo and not self.lesionado and not self.expulsado:
            self.resistencia_actual *= REDUCCION_RESISTENCIA_POR_MINUTO
            self.resistencia_actual = max(0, self.resistencia_actual)

    def incrementar_minutos_jugados(self):
        """Incrementa los minutos jugados por el jugador."""
        if self.esta_en_campo and not self.lesionado and not self.expulsado:
            self.minutos_jugados += 1

    def calcular_contribuciones(self, tact_array_equipo):
        """Calcula las contribuciones del jugador basadas en su táctica y posición."""
        self.tk_contrib = 0.0
        self.ps_contrib = 0.0
        self.sh_contrib = 0.0

        if self.posicion_actual == "Portero" or not self.esta_en_campo or self.lesionado or self.expulsado:
            return

        try:
            player_tk = float(self.django_futbolista.tk)
            player_ps = float(self.django_futbolista.ps)
            player_sh = float(self.django_futbolista.sh)
            player_fatiga_factor = self.resistencia_actual / 100.0  # Factor de fatiga basado en la resistencia actual
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error al obtener estadísticas del jugador {self.nombre}: {e}")
            return

        pos_category_idx = CATEGORIAS_POSICIONES.get(self.posicion_actual)
        if pos_category_idx is None:
            print(f"Posición desconocida para el jugador {self.nombre}: {self.posicion_actual}")
            return

        tk_modifier = tact_array_equipo[pos_category_idx][SKILL_TK_IDX]
        ps_modifier = tact_array_equipo[pos_category_idx][SKILL_PS_IDX]
        sh_modifier = tact_array_equipo[pos_category_idx][SKILL_SH_IDX]

        self.tk_contrib = tk_modifier * player_tk * player_fatiga_factor
        self.ps_contrib = ps_modifier * player_ps * player_fatiga_factor
        self.sh_contrib = sh_modifier * player_sh * player_fatiga_factor

    def es_disparo_puerta(self):
        """Determina si el disparo del jugador es a puerta."""
        if not self.esta_en_campo or self.lesionado or self.expulsado:
            return False
        factor_fatiga = self.resistencia_actual / 100.0  # Factor de fatiga basado en la resistencia actual

        probabilidad_base = 5800.0
        bonus_habilidad_tiro = float(self.django_futbolista.sh) * 60.0

        probabilidad_puerta = (probabilidad_base + bonus_habilidad_tiro) * factor_fatiga

        return random.randint(0, 9999) < probabilidad_puerta

    def calcular_probabilidad_gol_vs_potero(self, portero_oponente):
        """Calcula la probabilidad de gol contra el portero."""
        if not self.esta_en_campo or self.lesionado or self.expulsado:
            return 0.0

        if not portero_oponente or not portero_oponente.esta_en_campo:
            return 7500

        factor_fatiga_propio = self.resistencia_actual / 100.0  # Factor de fatiga basado en la resistencia actual
        habilidad_tiro_propia = float(self.django_futbolista.sh)

        habilidad_portero = float(portero_oponente.django_futbolista.st)

        valor_calculado = (habilidad_tiro_propia * factor_fatiga_propio) * 300.0 \
                        - (habilidad_portero) * 170.0 + 2800.0

        return max(1, int(valor_calculado))  # Asegurarse de que la probabilidad sea al menos 1
    
    def recibir_tarjeta(self, tipo_tarjeta, minuto):
        """Recibe una tarjeta y actualiza el estado del jugador."""
        if self.expulsado:
            return
        if tipo_tarjeta == "amarilla":
            self.tarjeta_amarilla_partido += 1
            self.advertido = False # Tarjeta amarilla anula una advertencia previa
            if self.tarjeta_amarilla_partido >= 2:
                self.expulsado = True
        elif tipo_tarjeta == "roja":
            self.tarjeta_roja_partido += 1
            self.expulsado = True
