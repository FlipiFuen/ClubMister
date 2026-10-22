
import json
import random
import time
import os
import sys
import re
import html

from datetime import datetime
from collections import defaultdict

from django.db import transaction
from django.template.loader import render_to_string

# Añadir la ruta del directorio padre al sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from administracion.Partidos.calcular_asistencia import calcular_asistencia
from administracion.Partidos.constantes import *
from administracion.Partidos.entidades import Arbitro, EquipoSimulado, JugadorPartido

# Importar el modelo Equipo, Futbolista y Estadio
from clubs.models import Estadio, Equipo, Futbolista

class Partido:
    def __init__(self, equipo_local_nombre, equipo_visitante_nombre, fecha_partido_str, hora_partido_str, es_copa=False, es_oficial=True):
        self.equipo_local_nombre_str = equipo_local_nombre
        self.equipo_visitante_nombre_str = equipo_visitante_nombre
        self.fecha_partido_str = fecha_partido_str
        self.hora_partido_str = hora_partido_str
        self.es_copa = es_copa
        self.es_oficial = es_oficial

        self.equipo_local_sim = None
        self.equipo_visitante_sim = None
        self.nombre_estadio = "Estadio Municipal"
        self.arbitro = None

        self.goles_local = 0
        self.goles_visitante = 0
        self.goles_descanso_local = 0
        self.goles_descanso_visitante = 0

        self.eventos_partido = []  # Lista de eventos del partido
        self.minuto_actual_display = 0

        # Configuraciones del partido
        self.num_substituciones = 3
        self.faltas_local = 0
        self.faltas_visitante = 0
        self.asistencia = 0
        self.lesionados_partido_info = []
        self.semanas_maximos_lesionado = 8
        self.ttactic_bonus_local = 100

        banda_inicial = random.choice(LISTA_BANDAS)
        self.equipo_con_balon = None
        self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, banda_inicial)
        self.equipo_saca_primera_parte = self.equipo_con_balon
        
        self.eventos_partido_reporte = []  # Lista de eventos del partido para el reporte final
        self.substituciones_realizadas_equipo = defaultdict(int)  # Substituciones realizadas por cada equipo
        self.comentarios_cargados = defaultdict(list)  # Comentarios cargados por minuto
        self.ruta_archivos_comentarios = os.path.join(PARTIDOS_DIR, "comentarios.dat")
        self._cargar_comentarios()

    def _configurar_partido(self):
        """Carga los equipos, arbitro y configuraciones del partido."""
        try:
            equipo_local_django = Equipo.objects.get(nombre_equipo=self.equipo_local_nombre_str)
            equipo_visitante_django = Equipo.objects.get(nombre_equipo=self.equipo_visitante_nombre_str)
        except Equipo.DoesNotExist:
            msg = f"Error: Equipo {self.equipo_local_nombre_str} o {self.equipo_visitante_nombre_str} no encontrado."
            print(msg)
            self.eventos_partido.append(msg)
            return False

        # Ruta a los archivos de alineación
        base_path_alineaciones = os.path.join(PARTIDOS_DIR,"alineaciones")
        ruta_alineacion_local = os.path.join(base_path_alineaciones, f"{self.equipo_local_nombre_str}.json")
        ruta_alineacion_visitante = os.path.join(base_path_alineaciones, f"{self.equipo_visitante_nombre_str}.json")

        self.equipo_local_sim = EquipoSimulado(equipo_local_django, ruta_alineacion_local, True, self)
        self.equipo_visitante_sim = EquipoSimulado(equipo_visitante_django, ruta_alineacion_visitante, False, self)

        # Resetear participo_ultimo_partido
        if self.es_oficial and self.equipo_local_sim and self.equipo_local_sim.django_equipo and \
            self.equipo_visitante_sim and self.equipo_visitante_sim.django_equipo:
            try:
                ids_futbolistas_locales = list(Futbolista.objects.filter(equipo=self.equipo_local_sim.django_equipo).values_list('id', flat=True))
                ids_futbolistas_visitantes = list(Futbolista.objects.filter(equipo=self.equipo_visitante_sim.django_equipo).values_list('id', flat=True))

                ids_resetear = list(set(ids_futbolistas_locales + ids_futbolistas_visitantes))
                if ids_resetear:
                    Futbolista.objects.filter(id__in=ids_resetear).update(participo_ultimo_partido=False)
                    print(f"Reseteado participo_ultimo_partido para los jugadores: {ids_resetear}")
            except Exception as e:
                print(f"Error al resetear participo_ultimo_partido: {e}")

        # Decidir quien saca inicialmente
        self.equipo_con_balon = random.choice([self.equipo_local_sim, self.equipo_visitante_sim])
        self.equipo_saca_primera_parte = self.equipo_con_balon

        # Aplicar bonus de táctica
        self.equipo_local_sim.aplicar_bonus_tactica(self.equipo_visitante_sim.tactica_actual)
        self.equipo_visitante_sim.aplicar_bonus_tactica(self.equipo_local_sim.tactica_actual)

        # Obtener nombre del estadio
        try:
            estadio_obj = Estadio.objects.filter(equipo=equipo_local_django).first()
            self.nombre_estadio = estadio_obj.nombre if estadio_obj else "Estadio Municipal"
        except (AttributeError, Estadio.DoesNotExist):
            print(f"Advertencia!: No se pudo obtener el estadio para {self.equipo_local_nombre_str}")
            try:
                # fallback
                estadio_obj = Estadio.objects.filter(equipo=equipo_local_django).first()
                if estadio_obj:
                    self.nombre_estadio = estadio_obj.nombre
                else:
                    self.nombre_estadio = "Estadio Municipal"
            except Exception as e:
                print(f"Error al obtener el estadio: {e}")
                self.nombre_estadio = "Estadio Municipal"
        # Cargar árbitros y seleccionar uno disponible
        todos_los_arbitros = Arbitro.cargar_arbitros()
        if todos_los_arbitros:
            self.arbitro = Arbitro.seleccionar_arbitro_disponible(todos_los_arbitros)
            if self.arbitro:
                if self.es_oficial:
                    Arbitro.guardar_arbitros(todos_los_arbitros)
            else:
                print("No se pudo seleccionar un árbitro disponible.")
                self.eventos_partido.append("No se pudo seleccionar un árbitro disponible.")
        else:
            self.eventos_partido.append("No se pudieron cargar los árbitros.")
        self.asistencia = calcular_asistencia(self.equipo_local_nombre_str, self.equipo_visitante_nombre_str)
        return True

    def _actualizar_estado_equipos_minuto(self):
        """Actualiza el estado de los equipos para el minuto actual del partido."""
        equipos_procesar = [self.equipo_local_sim, self.equipo_visitante_sim]
        for equipo_sim in equipos_procesar:
            if not equipo_sim:
                continue

            equipo_sim.team_tackling = 0.0
            equipo_sim.team_passing = 0.0
            equipo_sim.team_shooting = 0.0

            for jugador_partido in equipo_sim.jugadores_campo.values():
                if jugador_partido:
                    jugador_partido.reducir_resistencia(REDUCCION_RESISTENCIA_POR_MINUTO)
                    jugador_partido.calcular_contribuciones(equipo_sim.tact_array_equipo)
                    equipo_sim.actualizar_metricas_equipo(jugador_partido)

            equipo_sim.calcular_agresion_equipo()

        # Calcular probabilidad de tiro
        if self.equipo_local_sim and self.equipo_visitante_sim:
            self.equipo_local_sim.calcular_probabilidad_tiro(self.equipo_visitante_sim, True)
            self.equipo_visitante_sim.calcular_probabilidad_tiro(self.equipo_local_sim, False)

    def _determinar_posesion_y_transicion_zona(self):
        """
        Determina qué equipo gana la posesión para el minuto actual y
        simula una posible transición de la zona del balón.
        """
        if not self.equipo_local_sim or not self.equipo_visitante_sim:
            self.equipo_con_balon = None
            return

        # Calcular quien gana la posesión
        team_passing_local = self.equipo_local_sim.team_passing
        team_passing_visitante = self.equipo_visitante_sim.team_passing
        team_tackling_local = self.equipo_local_sim.team_tackling
        team_tackling_visitante = self.equipo_visitante_sim.team_tackling

        tempap = int((team_passing_local * 500) / (team_tackling_visitante if team_tackling_visitante != 0 else 0.1))
        tempbp = int((team_passing_visitante * 500) / (team_tackling_local if team_tackling_local != 0 else 0.1))

        if tempbp == 0:
            temppos = 6500 if tempap > 0 else 3250
        else:
            temppos = int((5000 * tempap) / tempbp)

        temppos = max(0, min(temppos, 6500))
        equipo_anterior_posesion = self.equipo_con_balon

        if random.randint(0, 9999) < temppos:
            self.equipo_local_sim.minutos_posesion += 1
            self.equipo_con_balon = self.equipo_local_sim
        else:
            self.equipo_visitante_sim.minutos_posesion += 1
            self.equipo_con_balon = self.equipo_visitante_sim

        # --- Simular transición de zona del balón ---
        zona_anterior_transicion = self.zona_balon
        if self.equipo_con_balon != equipo_anterior_posesion and equipo_anterior_posesion is not None:
            # Si hay un cambio de posesión
            base_zona_actual, banda_zona_actual = descomponer_zona(self.zona_balon) # Zona donde se perdio
            nueva_base_zona_defensor = base_zona_actual

            if base_zona_actual == ZONA_BASE_ATAQUE or base_zona_actual == ZONA_BASE_AREA_RIVAL:
                nueva_base_zona_defensor = ZONA_BASE_DEFENSIVA_PROPIA
            elif base_zona_actual == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                nueva_base_zona_defensor = ZONA_BASE_MEDIO_CAMPO_DEFENSIVO
            elif base_zona_actual == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
                nueva_base_zona_defensor = ZONA_BASE_MEDIO_CAMPO_OFENSIVO
            
            banda_recuperacion = banda_zona_actual if banda_zona_actual else random.choice(LISTA_BANDAS)
            self.zona_balon = crear_nombre_zona(nueva_base_zona_defensor, banda_recuperacion)

        else:
            # Si no hay cambio de posesión intenta avanzar
            prob_avanzar = 60
            if self.equipo_con_balon and self.equipo_con_balon.tactica_actual == "A":
                prob_avanzar = 80
            elif self.equipo_con_balon and self.equipo_con_balon.tactica_actual == "D":
                prob_avanzar = 30
            
            if random.randint(1, 100) <= prob_avanzar:
                base_zona_anterior, banda_zona_anterior = descomponer_zona(self.zona_balon)
                nueva_base_zona = None
                banda_mantener = banda_zona_anterior

                if base_zona_anterior == ZONA_BASE_DEFENSIVA_PROPIA:
                    nueva_base_zona = ZONA_BASE_MEDIO_CAMPO_OFENSIVO
                elif base_zona_anterior == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
                    nueva_base_zona = ZONA_BASE_MEDIO_CAMPO_OFENSIVO
                elif base_zona_anterior == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                    nueva_base_zona = ZONA_BASE_ATAQUE
                elif base_zona_anterior == ZONA_BASE_ATAQUE:
                    nueva_base_zona = ZONA_BASE_AREA_RIVAL
            
                if nueva_base_zona:
                    banda_mantener = banda_zona_anterior if banda_zona_anterior else BANDA_CENTRO

                if random.randint(1, 100) <= 70: # 70% de mantener la banda
                    nueva_banda = banda_mantener
                else:
                    posibles_nuevas_bandas = [b for b in LISTA_BANDAS if b != banda_mantener]
                    if not posibles_nuevas_bandas:
                        nueva_banda = banda_mantener
                    else:
                        nueva_banda = random.choice(posibles_nuevas_bandas)

                self.zona_balon = crear_nombre_zona(nueva_base_zona, nueva_banda)
        if zona_anterior_transicion != self.zona_balon and self.equipo_con_balon:
            # registrar si la zona cambio
            self.registrar_evento_partido(f"Zona del balón cambiada de {zona_anterior_transicion} a {self.zona_balon}.")

    def _actualizar_minutos_jugados_partido(self):
        """Actualiza los minutos jugados de los jugadores en el partido."""
        if self.equipo_local_sim:
            for jugador in self.equipo_local_sim.jugadores_campo.values():
                if jugador:
                    jugador.incrementar_minutos_jugados()

        if self.equipo_visitante_sim:
            for jugador in self.equipo_visitante_sim.jugadores_campo.values():
                if jugador:
                    jugador.incrementar_minutos_jugados() 

    def registrar_evento_partido(self, evento, minuto=None):
        """
        Registra un evento del partido en la lista de eventos y opcionalmente lo imprime.

        Args:
            evento_descripcion (str): La descripción del evento.
            minuto_display (int, optional): El minuto en el que ocurrió el evento. 
                                            Si se proporciona, se antepone a la descripción.
        """
        if minuto is not None:
            mensaje_completo = f"Min {minuto}: {evento}"
        else:
            mensaje_completo = evento

        self.eventos_partido.append(mensaje_completo)
        print(mensaje_completo) # para imprimir el evento en la consola en fase de desarrollo

    def _cargar_comentarios(self):
        """Carga los comentarios desde un archivo."""
        try:
            with open(self.ruta_archivos_comentarios, 'r', encoding='utf-8') as file:
                current_event_type = None
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('|'):
                        continue

                    match = re.match(r"\[([A-Z_0-9]+)\]\s*\{(.*)\}", line)
                    if match:
                        current_event_type = match.group(1)
                        frase_content = match.group(2).strip()
                        if frase_content:
                            self.comentarios_cargados[current_event_type].append(frase_content)
                    elif current_event_type and line.startswith('{') and line.endswith('}'):
                        frase_content = line[1:-1].strip() # remover llaves
                        if frase_content:
                            self.comentarios_cargados[current_event_type].append(frase_content)
                    elif current_event_type and not line.startswith('['):
                        frase_content = line.strip()
                        if frase_content:
                            self.comentarios_cargados[current_event_type].append(frase_content)
        except FileNotFoundError:
            print(f"El archivo {self.ruta_archivos_comentarios} no fue encontrado.")
        except Exception as e:
            import traceback
            print(f"Error al cargar comentarios: {e}")
            traceback.print_exc() # Imprime el rastreo completo para mejor depuración

    def _get_datos_placeholder(self, equipo_evento, jugador_principal=None, jugador_secundario=None):
        """Genera un diccionario con datos de placeholder para los comentarios."""
        equipo_no_evento = self.get_equipo_oponente(equipo_evento)

        nombre_g1 = "Portero Local"
        if equipo_evento:
            portero_actual = equipo_evento.get_portero_actual()
            if portero_actual:
                nombre_g1 = portero_actual.nombre

        nombre_g2 = "Portero Visitante"
        if equipo_no_evento:
            portero_actual = equipo_no_evento.get_portero_actual()
            if portero_actual:
                nombre_g2 = portero_actual.nombre


        datos = {
            "<t1>": equipo_evento.nombre if equipo_evento else "Equipo Local",
            "<t2>": equipo_no_evento.nombre if equipo_no_evento else "Equipo Visitante",
            "<g1>": nombre_g1,
            "<g2>": nombre_g2,
            "<ref>": self.arbitro.nombre if self.arbitro else "Árbitro",
            "<m1>": equipo_evento.django_equipo.user.username if equipo_evento and equipo_evento.django_equipo else "Manager Local",
            "<m2>": equipo_no_evento.django_equipo.user.username if equipo_no_evento and equipo_no_evento.django_equipo else "Manager Visitante",
        }

        return datos, jugador_principal, jugador_secundario

    def generar_comentario_evento(self, tipo_evento, equipo_evento, jugador_principal=None, jugador_secundario=None, datos_adicionales=None):
        """
        Selecciona una frase aleatoria para el tipo de evento, la formatea y la registra.
        Args:
            tipo_evento (str): Ej. "TACKLE", "ONE_GOAL".
            equipo_evento (EquipoSimulado): El equipo que realiza/sufre el evento principal.
            jugador_principal (JugadorPartido, optional): El jugador protagonista del evento.
            jugador_secundario (JugadorPartido, optional): Otro jugador implicado.
            datos_adicionales (dict, optional): Otros datos específicos para placeholders.
        """
        if tipo_evento not in self.comentarios_cargados or not self.comentarios_cargados[tipo_evento]:
            abreviatura_str = ""
            if equipo_evento and equipo_evento.django_equipo:
                abrv = equipo_evento.django_equipo.abreviatura
                if abrv:
                    abreviatura_str = f" ({abrv}) "
            # Fallback si no hay comentarios para este tipo de evento
            fallback_comentario = f"{abreviatura_str}Evento {tipo_evento} ocurrido."
            if jugador_principal:
                fallback_comentario += f" Jugador: {jugador_principal}."
            if equipo_evento:
                fallback_comentario += f" Equipo: {equipo_evento.nombre}."
            self.registrar_evento_reporte(fallback_comentario, self.minuto_actual_display)
            return

        frase_seleccionada = random.choice(self.comentarios_cargados[tipo_evento])
        abreviatura_str = ""
        if equipo_evento and equipo_evento.django_equipo:
            abrv = equipo_evento.django_equipo.abreviatura
            if abrv:
                abreviatura_str = f" ({abrv}) "

        placeholders_data, p1_obj, p2_obj = self._get_datos_placeholder(
            equipo_evento, jugador_principal, jugador_secundario
        )
        if datos_adicionales:
            placeholders_data.update(datos_adicionales)

        comentario_formateado = frase_seleccionada
        for placeholder, valor in placeholders_data.items():
            comentario_formateado = comentario_formateado.replace(placeholder, str(valor))

        # Manejo de %s, el primero es jugador principal, el segundo es jugador secundario
        nombres_para_s = []
        if isinstance(p1_obj, JugadorPartido):
            nombres_para_s.append(p1_obj.nombre)
        if isinstance(p2_obj, JugadorPartido):
            nombres_para_s.append(p2_obj.nombre)

        # Reemplazar %s con los nombres de los jugadores
        try:
            # Contar cuántos %s hay
            num_s_placeholders = comentario_formateado.count('%s')
            if tipo_evento == "CHANGETACTIC":
                nombres_para_s = []
                nombres_para_s.append(equipo_evento.nombre)
                nombres_para_s.append(jugador_principal)
            if tipo_evento == "CHANGEPOSITION":
                nombres_para_s = []
                nombres_para_s.append(jugador_principal.nombre)
                nombres_para_s.append(jugador_secundario)
            if num_s_placeholders > 0:
                if nombres_para_s:
                    if len(nombres_para_s) >= num_s_placeholders:
                        comentario_formateado = comentario_formateado % tuple(nombres_para_s[:num_s_placeholders])
                    else:
                        temp_comentario_formateado = comentario_formateado
                        for nombre_jug in nombres_para_s:
                            temp_comentario_formateado = temp_comentario_formateado.replace('%s', nombre_jug, 1)     
                        comentario_formateado = temp_comentario_formateado.replace('%s', 'el jugador', 1)
                        print(f"Advertencia!: no suficienes jugadores para %s. en {frase_seleccionada}")
                else:
                    comentario_formateado = comentario_formateado.replace('%s', 'el jugador', 1)
        except TypeError as e:
            print(f"Error al reemplazar %s: {e}")
            temp_comentario = comentario_formateado
            for nombre in nombres_para_s:
                if '%s' in temp_comentario:
                    temp_comentario = temp_comentario.replace('%s', nombre, 1)
                else:
                    break
            comentario_formateado = temp_comentario.replace('%s', 'el jugador')

        comentario_formateado = abreviatura_str + comentario_formateado

        # Reemplazar \n por saltos de línea reales para la consola/reporte
        comentario_formateado = comentario_formateado.replace("\\n", "\n").replace("\\t", "\t")

        self.registrar_evento_reporte(comentario_formateado, self.minuto_actual_display)

    def registrar_evento_reporte(self, evento_descripcion, minuto_display=None):
        """Registra un evento en la lista de eventos del partido para el reporte final."""
        if minuto_display is not None:
            mensaje_completo = f"Min {minuto_display}: {evento_descripcion}"
        else:
            mensaje_completo = evento_descripcion

        self.eventos_partido_reporte.append(mensaje_completo)
        print(mensaje_completo) # para imprimir el evento en la consola en fase de desarrollo

    def _simular_eventos_minuto(self):
        """Simula los eventos del minuto actual del partido."""
        if not self.equipo_local_sim or not self.equipo_visitante_sim:
            return
        self._determinar_posesion_y_transicion_zona()

        if not self.equipo_con_balon:
            print("No hay equipo con el balón, no se pueden simular eventos.")
            return

        equipo_atacante = self.equipo_con_balon
        equipo_defensor = self.get_equipo_oponente(equipo_atacante)
        es_local_atacante = (equipo_atacante == self.equipo_local_sim)
        if equipo_atacante and equipo_defensor:
            # Modificar probabilidad de tiro según la zona del balón
            prob_base_tiro = equipo_atacante.probabilidad_tiro
            prob_tiro_ajustada = prob_base_tiro

            base_zona_balon, banda_balon = descomponer_zona(self.zona_balon)

            if base_zona_balon == ZONA_BASE_AREA_RIVAL:
                prob_tiro_ajustada *= 2.0
                if banda_balon == BANDA_CENTRO:
                    prob_tiro_ajustada *= 1.1
                else:
                    prob_tiro_ajustada *= 0.9
            elif base_zona_balon == ZONA_BASE_ATAQUE:
                prob_tiro_ajustada *= 1.2
                if banda_balon and banda_balon != BANDA_CENTRO:
                    prob_tiro_ajustada *= 0.9
            elif base_zona_balon == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                prob_tiro_ajustada *= 0.5
            elif base_zona_balon == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
                prob_tiro_ajustada *= 0.1
            else:
                prob_tiro_ajustada *= 0

            prob_tiro_ajustada = min(prob_tiro_ajustada, 9500)  # Limitar a un máximo del 95%

            if random.randint(0, 9999) < prob_tiro_ajustada:
                # Determinar asistencia
                asistente = equipo_atacante.seleccionar_jugador_contribucion("ps_contrib", self.zona_balon)
                # Quien dispara
                disparador = equipo_atacante.seleccionar_jugador_contribucion("sh_contrib", self.zona_balon)
                if disparador == asistente:
                # Filtrar el asistente
                    temp_disparador = equipo_atacante.seleccionar_jugador_contribucion("sh_contrib", self.zona_balon)
                    if temp_disparador != asistente:
                        disparador = temp_disparador
                    else:
                        disparador = random.choice(list(equipo_atacante.jugadores_campo.values()))
                if not disparador:
                    return  # No hay jugador para disparar
                self.generar_comentario_evento(
                    "CHANCE",
                    equipo_atacante,
                    jugador_principal = asistente if asistente != disparador else "el jugador atacante",
                    jugador_secundario = disparador,
                    )
                asistente.asistencias_partido += 1

                # Gol en propia puerta
                if random.randint(0, 9999) < 26:
                    defensor_desafortunado = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", self.zona_balon)
                    if defensor_desafortunado:
                        if es_local_atacante:
                            self.goles_local += 1
                        else:
                            self.goles_visitante += 1

                        # Actualizar estadisticas del jugador y portero
                        defensor_desafortunado.goles_propia_partido += 1
                        portero_defensor = equipo_defensor.get_portero_actual()
                        if portero_defensor:
                            portero_defensor.goles_concedidos_partido += 1
                            self.generar_comentario_evento(
                                "OWNGOAL",
                                equipo_atacante,
                                jugador_principal=defensor_desafortunado,
                            )
                        self.equipo_con_balon = equipo_defensor
                        self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, random.choice(LISTA_BANDAS))
                                # Logica para AddGoalToReport
                        return
                # Disparo interceptado?
                jugador_tacklea = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", self.zona_balon)
                numerador_tackle = equipo_defensor.team_tackling * 3.0
                denominador_tackle = (equipo_atacante.team_passing * 2.0 + equipo_atacante.team_shooting)
                if denominador_tackle > 0:
                    prob_tackle = int(3000.0 * (numerador_tackle / denominador_tackle))
                    if random.randint(0, 9999) < prob_tackle:
                        jugador_tacklea.intercepciones_partido += 1
                        # Corner?
                        prob_corner_tras_bloqueo = 2500 # 25% posibilidad de corner
                        base_zona_actual, _ = descomponer_zona(self.zona_balon)
                        if base_zona_actual == ZONA_BASE_AREA_RIVAL and random.randint(0, 9999) < prob_corner_tras_bloqueo:
                            self.generar_comentario_evento(
                                "TACKLE4CORNER",
                                equipo_defensor,
                                jugador_principal = jugador_tacklea,
                            )
                            self._simular_corner(equipo_atacante)
                        else:
                            self.generar_comentario_evento(
                                "TACKLE",
                                equipo_defensor,
                                jugador_principal = jugador_tacklea,
                                jugador_secundario = disparador,
                            )
                        return  # Disparo interceptado
                    else:
                        self.generar_comentario_evento(
                            "GETS_PAST",
                            equipo_atacante,
                            jugador_principal = asistente if asistente != disparador else disparador,
                            jugador_secundario = jugador_tacklea,
                        )
                # Disparo a puerta?
                if disparador.es_disparo_puerta():
                    disparador.disparos_puerta_partido
                    equipo_atacante.disparos_a_puerta = getattr(equipo_atacante, 'disparos_a_puerta', 0) + 1
                    base_zona_actual, _ = descomponer_zona(self.zona_balon)
                    if base_zona_actual == ZONA_BASE_AREA_RIVAL:
                        self.generar_comentario_evento(
                            "ASSISTEDCHANCE",
                            equipo_atacante,
                            jugador_principal = asistente,
                            jugador_secundario = disparador,
                        )
                        self.generar_comentario_evento(
                        "SHOT",
                        equipo_atacante,
                        jugador_principal = disparador,
                        )
                    else:
                        self.generar_comentario_evento(
                                "ASSISTEDCHANCE",
                                equipo_atacante,
                                jugador_principal = asistente if asistente != disparador else None,
                                jugador_secundario = disparador,
                            )
                        self.generar_comentario_evento(
                        "SHOT",
                        equipo_atacante,
                        jugador_principal = disparador,
                        )

                    portero_defensor = equipo_defensor.get_portero_actual()
                    prob_gol_calculada = disparador.calcular_probabilidad_gol_vs_potero(portero_defensor)

                    if random.randint(0, 9999) < prob_gol_calculada: # es gol
                        if random.randint(0, 9999) < 350: # Gol anulado?
                            self.generar_comentario_evento(
                                "GOALCANCELLED",
                                equipo_atacante,
                            )
                            return  # Gol anulado
                        else:
                            if es_local_atacante:
                                self.goles_local += 1
                            else:
                                self.goles_visitante += 1

                        disparador.goles_partido += 1
                        # Actualizar estadisticas del jugador y portero
                        if portero_defensor:
                            portero_defensor.goles_concedidos_partido += 1

                        if self.zona_balon == ZONA_BASE_AREA_RIVAL:
                            self.generar_comentario_evento(
                                "ONE_GOAL",
                                equipo_atacante,
                                jugador_principal = disparador,
                            )
                        else:
                            self.generar_comentario_evento(
                                "GOAL",
                                equipo_atacante,
                                jugador_principal = disparador,
                            )
                        # Devolver posesion a equipo contrario, colocar balon en el centro para saque y sumar el gol al equipo
                        self.equipo_con_balon.goles += 1
                        self.equipo_con_balon = equipo_defensor
                        self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, random.choice(LISTA_BANDAS))
                            # Logica para AddGoalToReport
                    else: # Parada del portero
                        portero_defensor.paradas_partido += 1
                        base_zona_actual, _ = descomponer_zona(self.zona_balon)
                        if base_zona_actual == ZONA_BASE_AREA_RIVAL:
                            # probabilidad de corner
                            prob_corner_tras_parada = 4000 # 40% posibilidad de corner
                            if random.randint(0, 9999) < prob_corner_tras_parada:
                                self.generar_comentario_evento(
                                    "SAVE4CORNER",
                                    equipo_defensor,
                                    jugador_principal = portero_defensor,
                                )
                                self._simular_corner(equipo_atacante)
                            else:
                                self.generar_comentario_evento(
                                    "ONE_SAVE",
                                    equipo_defensor,
                                    jugador_principal = portero_defensor,
                                )
                            return
                        else:
                            self.generar_comentario_evento(
                                "SAVE",
                                equipo_defensor,
                                jugador_principal = portero_defensor if portero_defensor else "el guardameta",
                            )
                        if portero_defensor:
                            portero_defensor.paradas = getattr(portero_defensor, 'paradas', 0) + 1

                else: # Disparo fuera
                    disparador.disparos_fuera_partido += 1       
                    equipo_atacante.disparos_fuera = getattr(equipo_atacante, 'disparos_fuera', 0) + 1
                    self.generar_comentario_evento(
                        "ASSISTEDCHANCE",
                        equipo_atacante,
                        jugador_principal = asistente,
                        jugador_secundario = disparador,
                    )
                    base_zona_actual, _ = descomponer_zona(self.zona_balon)
                    if base_zona_actual == ZONA_BASE_AREA_RIVAL:
                        self.generar_comentario_evento(
                            "ONE_OFFTARGET",
                            equipo_atacante,
                            jugador_principal = disparador,
                        )
                        prob_rechace_corner = 2000 # 20% posibilidad de corner
                        if random.randint(0, 9999) < prob_rechace_corner:
                            self.generar_comentario_evento(
                                "DEFLECTION4CORNER",
                                equipo_atacante,
                                jugador_principal = disparador,
                            )
                            
                    else:
                        self.generar_comentario_evento(
                            "SHOT",
                            equipo_atacante,
                            jugador_principal = disparador,
                        )
                        prob_rechace_corner = 2000 # 20% posibilidad de corner
                        if random.randint(0, 9999) < prob_rechace_corner:
                            self.generar_comentario_evento(
                                "DEFLECTION4CORNER",
                                equipo_atacante,
                                jugador_principal = disparador,
                            )
                            self._simular_corner(equipo_atacante)
                        else:   
                            self.generar_comentario_evento(
                                "OFFTARGET",
                                equipo_atacante,
                            )
            else:
                zona_anterior = self.zona_balon
                # Si no se dispara, se intenta un pase
                pasador = equipo_atacante.seleccionar_jugador_contribucion("ps_contrib", self.zona_balon)
                if pasador:
                    prob_exito_pase = equipo_atacante.calcular_probabilidad_pase(
                        pasador, self.zona_balon, 
                        equipo_defensor
                    )
                
                    if random.randint(0, 9999) < prob_exito_pase:
                        base_zona_actual, banda_actual = descomponer_zona(self.zona_balon)
                        nueva_base_zona_pase = base_zona_actual

                        # Avanzar el balón a la siguiente zona si el pase es exitoso
                        if base_zona_actual == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
                            nueva_base_zona_pase = ZONA_BASE_MEDIO_CAMPO_OFENSIVO
                        elif base_zona_actual == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                            nueva_base_zona_pase = ZONA_BASE_ATAQUE
                        elif base_zona == ZONA_BASE_ATAQUE:
                            nueva_base_zona_pase = ZONA_BASE_AREA_RIVAL

                        # Mantenemos la banda actual
                        if nueva_base_zona_pase != base_zona_actual and banda_actual:
                            self.zona_balon = crear_nombre_zona(nueva_base_zona_pase, banda_actual)

                        # Determinar quién recibe el pase
                        posibles_receptores_todos= [
                            jug_p for jug_p in equipo_atacante.jugadores_campo.values()
                            if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and jug_p.posicion_actual != "Portero"
                            and jug_p != pasador
                        ]
                        receptor = None
                        if not posibles_receptores_todos:
                            self.registrar_evento_partido("No hay jugadores disponibles para recibir el pase.", self.minuto_actual_display)
                        else:
                            receptores_con_peso = []
                            for jug_p_receptor in posibles_receptores_todos:
                                peso = 1.0
                                # Bonus por misma banda que el balon
                                bandas_jugador_receptor = get_bandas_para_posicion(jug_p_receptor.posicion_actual)
                                if banda_actual in bandas_jugador_receptor:
                                    peso *= 2.5
                                elif BANDA_CENTRO in bandas_jugador_receptor and banda_actual != BANDA_CENTRO:# Jugador en centro, balon en banda
                                    peso *= 1.3
                                elif BANDA_CENTRO in bandas_jugador_receptor and (BANDA_IZQUIERDA in bandas_jugador_receptor or BANDA_DERECHA in bandas_jugador_receptor):
                                    peso *= 1.2
                                
                                # Bonus por rol adecuado
                                pos_categoria_receptor = CATEGORIAS_POSICIONES.get(jug_p_receptor.posicion_actual)
                                if pos_categoria_receptor is not None:
                                    if base_zona_actual == ZONA_BASE_DEFENSIVA_PROPIA:
                                        if pos_categoria_receptor in [1, 2, 4]: # DEF, MED, MCD
                                            peso *= 1.2
                                    elif base_zona_actual == ZONA_BASE_MEDIO_CAMPO_DEFENSIVO:
                                        if pos_categoria_receptor in [2, 5]: # MED, MP
                                            peso *= 1.5
                                        elif pos_categoria_receptor == 3: # DEL (bajando a recibir)
                                            peso *= 1.1
                                        elif pos_categoria_receptor == 4: # MCD
                                            peso *= 1.3
                                    elif base_zona_actual == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                                        if pos_categoria_receptor == 3: # DEL
                                            peso *= 2.0
                                        elif pos_categoria_receptor == 5: # MP
                                            peso *= 1.8
                                        elif pos_categoria_receptor == 2: # MED (llegando desde atras)
                                            peso *= 1.5
                                    elif base_zona_actual == ZONA_BASE_ATAQUE:
                                        if pos_categoria_receptor == 3: # DEL
                                            peso *= 2.5
                                        elif pos_categoria_receptor == 5: # MP
                                            peso *= 2.0
                                
                                peso *= random.uniform(0.9, 1.1)
                                receptores_con_peso.append((jug_p_receptor, max(0.1, peso))) # Asegurar peso minimo

                            if receptores_con_peso:
                                jugadores_seleccionables = [item[0] for item in receptores_con_peso]
                                pesos_seleccionables = [item[1] for item in receptores_con_peso]
                                try:
                                    receptor = random.choices(jugadores_seleccionables, weights=pesos_seleccionables, k=1)[0]
                                except ValueError:
                                    receptor = random.choice(posibles_receptores_todos)
                            else:
                                receptor = random
                                    
                        nombre_receptor = receptor.nombre if receptor else "Un compañero"

                        if zona_anterior != base_zona_actual and nueva_base_zona_pase != base_zona_actual:
                            defensor = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", self.zona_balon)
                            self.generar_comentario_evento(
                                "GETS_PAST_ASS",
                                equipo_atacante,
                                jugador_principal = pasador,
                                jugador_secundario = defensor,
                                datos_adicionales = {"<receptor>": nombre_receptor}
                            )
                            self.generar_comentario_evento(
                                "ONE_ON_ONE",
                                equipo_atacante,
                                jugador_principal = receptor,
                                jugador_secundario = defensor,
                            )
                            self.generar_comentario_evento(
                                "TACKLE",
                                equipo_defensor,
                                jugador_principal = defensor,
                                jugador_secundario = receptor,
                            )
                        # Aumentar estadísticas de pase
                        pasador.pases_completados_partido += 1
                    else:
                        # Pase fallido
                        pasador.pases_intentados_partido += 1
                        self.equipo_con_balon = equipo_defensor  # Cambiar la posesión al equipo defensor
                        # Podria cambiar de zona al ser interceptado
                        base_zona_intercepcion, banda_intercepcion = descomponer_zona(self.zona_balon)
                        nueva_base_intercepcion = base_zona_intercepcion

                        if base_zona == ZONA_BASE_ATAQUE or base_zona_intercepcion == ZONA_BASE_AREA_RIVAL:
                            nueva_base_intercepcion = ZONA_BASE_DEFENSIVA_PROPIA # Defensor recupera en su area
                        elif base_zona_intercepcion == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
                            nueva_base_intercepcion = ZONA_BASE_MEDIO_CAMPO_DEFENSIVO

                        banda_final_intercepcion = banda_intercepcion if banda_intercepcion else random.choice(LISTA_BANDAS)
                        self.zona_balon = crear_nombre_zona(nueva_base_intercepcion, banda_final_intercepcion)

                        # Incrementar estadísticas de pase fallido e intercepciones
                        pasador.pases_fallidos = getattr(pasador, 'pases_fallidos', 0) + 1
                        jugador_interceptor = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", self.zona_balon)
                        if jugador_interceptor:
                            jugador_interceptor.intercepciones = getattr(jugador_interceptor, 'intercepciones', 0) + 1
                else:
                    self.registrar_evento_partido(f"{equipo_atacante.nombre} no tiene jugadores disponibles para pasar el balón.", self.minuto_actual_display)
        else:
            self.registrar_evento_partido("No hay equipo atacante definido, no se pueden simular eventos.", self.minuto_actual_display)

    def _simular_falta_y_sancion(self, equipo_comete_falta, equipo_recibe_falta):
        """Simula una falta y posibles sanciones."""
        if not equipo_comete_falta or not equipo_recibe_falta:
            return

        # Probabilidad de que el equipo cometa una falta
        prob_cometer_falta = int(equipo_comete_falta.agresion * FACTOR_AGRESION_FALTA)
        prob_cometer_falta = max(0, min(prob_cometer_falta, 9000))

        if random.randint(0, 9999) > prob_cometer_falta:
            return False # No hay falta
        
        equipo_comete_falta.faltas_cometidas_equipo *= 1
        if equipo_comete_falta == self.equipo_local_sim:
            self.faltas_local += 1
        else:
            self.faltas_visitante += 1

        infractor = equipo_comete_falta.seleccionar_jugador_por_agresion()
        if not infractor:
            return False
        
        # Jugador que recibe la falta
        candidatos_reciben_falta = [
            jugador for jugador in equipo_recibe_falta.jugadores_campo.values()
            if jugador.esta_en_campo and not jugador.lesionado and not jugador.expulsado and jugador.posicion_actual != "Portero"
        ]
        if not candidatos_reciben_falta:
            return False
        else:
            jugador_recibe_falta = random.choice(candidatos_reciben_falta)
        infractor.faltas_cometidas_partido += 1
        jugador_recibe_falta.faltas_recibidas_jugador = getattr(jugador_recibe_falta, 'faltas_recibidas_jugador', 0) + 1

        # Determinar si hay tarjeta
        rand_card_draw = random.randint(0, 9999)

        # Umbral de tarjeta por severidad del arbitro
        umbral_probabilidad_roja_actual = PROB_ROJA_DIRECTA_UMBRAL
        umbral_probabilidad_amarilla_actual = PROB_AMARILLA_UMBRAL
        umbral_probabilidad_aviso = PROB_AVISO_UMBRAL

        if self.arbitro:
            # Severidad: 1 (muy pervisivo) a 20 (muy estricto)
            ajuste = (self.arbitro.severidad - 10) * FACTOR_ESCALA_SEVERIDAD_ARBITRO
            umbral_probabilidad_roja_actual = int(PROB_ROJA_DIRECTA_UMBRAL * (1 - ajuste))
            umbral_probabilidad_amarilla_actual = int(PROB_AMARILLA_UMBRAL * (1 - ajuste))
            umbral_probabilidad_aviso = int(PROB_AVISO_UMBRAL * (1 - ajuste))

            # Asegurar que los umbrales no sean negativos
            umbral_probabilidad_roja_actual = max(50, umbral_probabilidad_roja_actual)
            umbral_probabilidad_amarilla_actual = max(umbral_probabilidad_roja_actual + 50, umbral_probabilidad_amarilla_actual)
            umbral_probabilidad_aviso = max(umbral_probabilidad_amarilla_actual + 50, umbral_probabilidad_aviso)

        tipo_sancion = None
        if rand_card_draw < umbral_probabilidad_roja_actual:
            tipo_sancion = "roja"    
        elif rand_card_draw < umbral_probabilidad_amarilla_actual:
            tipo_sancion = "amarilla"
        elif rand_card_draw < umbral_probabilidad_aviso:
            tipo_sancion = "aviso"
                    
        es_penalty = False

        if self.equipo_con_balon == equipo_recibe_falta and self.zona_balon.startswith(ZONA_BASE_AREA_RIVAL):
            prob_cometer_penalty = PROB_PENALTY_AREA_FOUL
            if infractor.posicion_actual == "Portero":
                prob_cometer_penalty = PROB_PENALTY_GK_FOUL_AREA
            if random.randint(0, 9999) < prob_cometer_penalty:         
                # Penalty
                es_penalty = True
                self.generar_comentario_evento("PENALTY", equipo_comete_falta, jugador_principal = equipo_recibe_falta.alineacion_data.get("tirador_seleccionado"))
                self._procesar_sancion(infractor, tipo_sancion, equipo_comete_falta)
                self._simular_penalty(equipo_recibe_falta, equipo_comete_falta)
        if not es_penalty:
            # Comprobar si es tiro libre
            base_zona_falta, _ = descomponer_zona(self.zona_balon)
            es_tiro_libre = False
            if base_zona_falta == ZONA_BASE_ATAQUE or base_zona_falta == ZONA_BASE_MEDIO_CAMPO_OFENSIVO and random.randint(0, 9999) < 4000:
                es_tiro_libre = True

            if es_tiro_libre:
                self.generar_comentario_evento("SERIOUSFOUL", equipo_recibe_falta, jugador_principal = infractor)
                self._procesar_sancion(infractor, tipo_sancion, equipo_comete_falta)
                self._simular_tiro_libre(equipo_recibe_falta, equipo_comete_falta, self.zona_balon)
            else:
                self.generar_comentario_evento("FOUL", equipo_comete_falta, jugador_principal = infractor)
                self._procesar_sancion(infractor, tipo_sancion, equipo_comete_falta)
                self.equipo_con_balon = equipo_recibe_falta
        if infractor.expulsado:
            self._manejar_expulsion(equipo_comete_falta, infractor)

        return True
    
    def _procesar_sancion(self, infractor, tipo_sancion_str, equipo_infractor):
        """
        Aplica la sanción disciplinaria (tarjeta/aviso) al jugador infractor,
        actualiza las estadísticas del equipo y genera el comentario correspondiente.
        """
        if tipo_sancion_str == "roja":
            infractor.recibir_tarjeta("roja", self.minuto_actual_display)
            equipo_infractor.tarjetas_rojas += 1
            infractor.expulsado = True
            infractor.tarjeta_roja_partido += 1
            self.generar_comentario_evento("REDCARD", equipo_infractor, jugador_principal = infractor)
        elif tipo_sancion_str == "amarilla":
            infractor.recibir_tarjeta("amarilla", self.minuto_actual_display)
            if infractor.expulsado: # Segunda amarilla
                equipo_infractor.tarjetas_amarillas += 1
                infractor.tarjeta_amarilla_partido -= 1
                infractor.tarjeta_roja_partido += 1
                self.generar_comentario_evento("SECONDYELLOWCARD", equipo_infractor, jugador_principal = infractor)
            else: # Primera amarilla
                equipo_infractor.tarjetas_amarillas += 1
                infractor.tarjeta_amarilla_partido += 1
                self.generar_comentario_evento("YELLOWCARD", equipo_infractor, jugador_principal = infractor)
        elif tipo_sancion_str == "aviso":
            if not infractor.advertido and infractor.tarjeta_amarilla_partido == 0:
                infractor.advertido = True
                self.generar_comentario_evento("WARNED", equipo_infractor, jugador_principal = infractor)
            elif infractor.advertido and infractor.tarjeta_amarilla_partido == 0:
                infractor.recibir_tarjeta("amarilla", self.minuto_actual_display)
                equipo_infractor.tarjetas_amarillas += 1
                self.generar_comentario_evento("YELLOWCARD", equipo_infractor, jugador_principal = infractor)
    
    def _simular_tiro_libre(self, equipo_patea, equipo_defiende, zona_falta_str):
        """Simula un tiro libre."""
        self.minuto_actual_display += 1

        if not equipo_patea or not equipo_defiende:
            return

        # Seleccionar lanzador
        lanzador = None
        tirador_designado = equipo_patea.alineacion_data.get("tirador_seleccionado")
        if tirador_designado:
            for jug_p in equipo_patea.jugadores_campo.values():
                if jug_p.nombre == tirador_designado and jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado:
                    lanzador = jug_p
                    break
        if not lanzador:
            mejor_lanzador_en_campo = None
            max_sh_skill = -1
            for jug_p in equipo_patea.jugadores_campo.values():
                if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and jug_p.posicion_actual != "Portero":
                    try:
                        sh_skill = float(jug_p.django_futbolista.sh)
                        if sh_skill > max_sh_skill:
                            max_sh_skill = sh_skill
                            mejor_lanzador_en_campo = jug_p
                    except (ValueError, AttributeError):
                        continue
            lanzador = mejor_lanzador_en_campo

        if not lanzador:
            self.registrar_evento_reporte(f"No hay jugadores para lanzar el tiro libre para {equipo_patea.nombre}.", self.minuto_actual_display)
            self.equipo_con_balon = equipo_defiende
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            return
        
        portero_defensor = equipo_defiende.get_portero_actual()
        if not portero_defensor:
            self.registrar_evento_reporte("No hay portero para defender el tiro libre.", self.minuto_actual_display)
        self.generar_comentario_evento("FREEKICK_TAKEN", equipo_patea, jugador_principal = lanzador)
        
        # Tiro directo o pase
        base_zona_falta, _ = descomponer_zona(zona_falta_str)
        prob_intento_directo = 0
        if base_zona_falta == ZONA_BASE_ATAQUE:
            prob_intento_directo = PROB_TIRO_LIBRE_ZONA_ATAQUE
        elif base_zona_falta == ZONA_BASE_MEDIO_CAMPO_OFENSIVO:
            prob_intento_directo = PROB_TIRO_DIRECTO_ZONA_MCO

        if random.randint(0, 9999) < prob_intento_directo:
            # Intento tiro directo
            prob_a_puerta = PROB_TIRO_DIRECTO_OBJETIVO_BASE
            prob_a_puerta += (float(lanzador.django_futbolista.sh) - 40) * FACTOR_SH_TIRO_LIBRE_OBJETIVO
            prob_a_puerta *= (lanzador.resistencia_actual / 100.0 * MOD_RESISTENCIA_TIRO_LIBRE + (1 - MOD_RESISTENCIA_TIRO_LIBRE))
            prob_a_puerta = int(max(1000, min(9000, prob_a_puerta)))

            if random.randint(0, 9999) < prob_a_puerta: # Tiro a puerta
                lanzador.disparos_puerta_partido += 1
                prob_gol_base = lanzador.calcular_probabilidad_gol_vs_potero(portero_defensor)
                prob_gol_final = int(prob_gol_base * MULTIPLICADOR_GOL_TIRO_LIBRE)
                prob_gol_final = max(500, min(prob_gol_final, 9500))

                if random.randint(0, 9999) < prob_gol_final: # Gol
                    if equipo_patea == self.equipo_local_sim:
                        self.goles_local += 1
                    else:
                        self.goles_visitante += 1
                    equipo_patea.goles += 1
                    lanzador.goles_partido += 1
                    if portero_defensor:
                        portero_defensor.goles_concedidos_partido += 1
                    self.generar_comentario_evento("FREEKICK_GOAL", equipo_patea, jugador_principal = lanzador)
                    self.equipo_con_balon = equipo_defiende
                    self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                else: # Parada
                    portero_defensor.paradas_partido += 1
                    self.generar_comentario_evento("FREEKICK_SAVE", equipo_defiende, jugador_principal = lanzador)
                    self.equipo_con_balon = equipo_defiende
                    self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            else: # Tiro fuera o barrera
                lanzador.disparos_fuera_partido += 1
                if random.randint(0, 9999) < PROB_TIRO_LIBRE_BARRERA:
                    self.generar_comentario_evento("FREEKICK_HITS_WALL", equipo_patea, jugador_principal = lanzador)
                    if random.randint(0, 9999) < PROB_TIRO_LIBRE_BARRERA_CORNER:
                        self.generar_comentario_evento("FREEKICK_WALL_CORNER", equipo_patea, jugador_principal = lanzador)
                        self._simular_corner(equipo_patea)
                    else:
                        self.equipo_con_balon = equipo_defiende
                        self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                else: # Fuera
                    self.generar_comentario_evento("FREEKICK_OFFTARGET", equipo_patea, lanzador)
                    self.equipo_con_balon = equipo_defiende
                    self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
        else: # Jugada ensayada
            self.generar_comentario_evento("FREEKICK_OFFTARGET", equipo_patea, lanzador)
            self.equipo_con_balon = equipo_defiende
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                
    def _simular_penalty(self, equipo_patea, equipo_defiende):
        """Simula un penalty."""
        self.minuto_actual_display += 1

        tirador_penalty = None
        tirador_designado_nombre = equipo_patea.alineacion_data.get("tirador_seleccionado")
        if tirador_designado_nombre:
            for jug_p in equipo_patea.jugadores_campo.values():
                if jug_p.nombre == tirador_designado_nombre and jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado:
                    tirador_penalty = jug_p
                    break
        if not tirador_penalty:
            mejor_tirador_en_campo = None
            max_sh_skill = -1
            for jug_p in equipo_patea.jugadores_campo.values():
                if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and jug_p.posicion_actual != "Portero":
                    try:
                        sh_skill = float(jug_p.django_futbolista.sh)
                        if sh_skill > max_sh_skill:
                            max_sh_skill = sh_skill
                            mejor_tirador_en_campo = jug_p
                    except (ValueError, AttributeError):
                        continue
            tirador_penalty = mejor_tirador_en_campo

        portero = equipo_defiende.get_portero_actual()
        prob_gol = PROB_PENALTY_BASE_GOL + \
                    (float(tirador_penalty.django_futbolista.sh) * TIRADOR_PENALTY_SH_FACTOR) - \
                    (float(portero.django_futbolista.st) * PENALTY_GK_ST_FACTOR)
        prob_gol = int(max(3000, min(9500, prob_gol))) # Limitar entre 30% y 95%

        tirador_penalty.disparos_puerta_partido += 1

        if random.randint(0, 9999) < prob_gol: # Gol
            tirador_penalty.goles_partido += 1
            if equipo_patea == self.equipo_local_sim:
                self.goles_local += 1
            else:
                self.goles_visitante += 1
            equipo_patea.goles += 1
            portero.goles_concedidos_partido += 1
            self.generar_comentario_evento("PEN_GOAL", equipo_patea, jugador_principal = tirador_penalty)
            self.equipo_con_balon = equipo_defiende
            self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, random.choice(LISTA_BANDAS))
        else: # Fallo
            if random.randint(0, 9999) < PROB_PENALTY_PARADO_VS_FUERA: # Parada
                portero.paradas_partido += 1
                tirador_penalty.disparos_intentados += 1
                if random.randint(0, 9999) < PROB_PENALTY_PARADO_CORNER:
                    self.generar_comentario_evento("PEN_SAVE4CORNER", equipo_defiende, jugador_principal = portero)
                    self._simular_corner(equipo_patea)
                else:
                    self.generar_comentario_evento("PEN_SAVE", equipo_defiende, jugador_principal = portero)
                self.equipo_con_balon = equipo_defiende
                self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            else: # Fuera
                tirador_penalty.disparos_fuera_partido += 1
                self.generar_comentario_evento("PEN_OFFTARGET", equipo_patea, jugador_principal = tirador_penalty)
                self.equipo_con_balon = equipo_defiende
                self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))

    def _manejar_expulsion(self, equipo_expulsado, jugador_expulsado):
        """Maneja la expulsión de un jugador."""
        pass

    def _simular_corner(self, equipo_atacante):
        """Simula un corner."""
        self.minuto_actual_display += 1
        equipo_defensor = self.get_equipo_oponente(equipo_atacante)
        if not equipo_defensor or not equipo_atacante:
            return
        
        equipo_atacante.corners = getattr(equipo_atacante, 'corners', 0) + 1
        # Determinar la banda del corner
        _prev_base_zona, _prev_banda = descomponer_zona(self.zona_balon)
        banda_corner = _prev_banda
        if not banda_corner or banda_corner == BANDA_CENTRO:
            banda_corner = random.choice(LISTA_BANDAS)
            
        lanzador_corner = equipo_atacante.seleccionar_jugador_contribucion("ps_contrib", crear_nombre_zona(ZONA_BASE_AREA_RIVAL, banda_corner))
        if not lanzador_corner: # Fallback si no se selecciona por contribución
            posibles_lanzadores = [p for p in equipo_atacante.jugadores_campo.values() if p.esta_en_campo and not p.lesionado and not p.expulsado and p.posicion_actual != "Portero"]
            if not posibles_lanzadores:
                self.registrar_evento_reporte(f"No hay jugadores para lanzar el córner para {equipo_atacante.nombre}.", self.minuto_actual_display)
                self.equipo_con_balon = equipo_defensor 
                self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                return
            lanzador_corner = random.choice(posibles_lanzadores)

        self.generar_comentario_evento(
            "CORNER",
            equipo_atacante,
            jugador_principal = lanzador_corner,
        )     
        self.generar_comentario_evento(
            "CORNER_TAKEN",
            equipo_atacante,
            jugador_principal = lanzador_corner,
        )

        portero_defensor = equipo_defensor.get_portero_actual()
        prob_portero_atrapa = 0
        if portero_defensor:
            habilidad_st_portero = float(portero_defensor.django_futbolista.st)
            habilidad_ps_lanzador = float(lanzador_corner.django_futbolista.ps)
            prob_portero_atrapa = int(1500 + habilidad_st_portero * 70.0 - habilidad_ps_lanzador * 80.0)
            prob_portero_atrapa = max(500, min(prob_portero_atrapa, 6000)) # 5% a 60%

        if random.randint(0, 9999) < prob_portero_atrapa and portero_defensor:
            self.generar_comentario_evento(
                "CORNER_CAUGHT",
                equipo_defensor,
                jugador_principal = portero_defensor,
            )
            portero_defensor.paradas_partido += 1
            self.equipo_con_balon = equipo_defensor
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            return

        numerador_despeje = equipo_defensor.team_tackling * 3.0
        denominador_despeje = (equipo_atacante.team_passing * 2.0 + equipo_atacante.team_shooting)
        prob_defensor_despeja = 0
        if denominador_despeje > 0:
            prob_defensor_despeja = int(2500.0 * (numerador_despeje / denominador_despeje))
            prob_defensor_despeja = max(500, min(prob_defensor_despeja, 7500)) # 5% a 75%
        else:
            prob_defensor_despeja = 6000

        if random.randint(0, 9999) < prob_defensor_despeja:
            despejador = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", self.zona_balon)
            if not despejador:
                posibles_despejadores = [p for p in equipo_defensor.jugadores_campo.values() if p.esta_en_campo and not p.lesionado and not p.expulsado and p.posicion_actual != "Portero"]
                if posibles_despejadores:
                    despejador = random.choice(posibles_despejadores)
            if despejador:
                self.generar_comentario_evento(
                    "CORNER_CLEARED",
                    equipo_defensor,
                    jugador_principal = despejador,
                )
                despejador.intercepciones_partido += 1
                self.equipo_con_balon = equipo_defensor
                self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                return
            else:
                self.generar_comentario_evento(
                    "CORNER_CAUGHT",
                    equipo_defensor,
                    jugador_principal = portero_defensor,
                )
                self.equipo_con_balon = equipo_defensor
                self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                return
        # Oportunidades de remate
        posibles_rematadores = [
            jug_p for jug_p in equipo_atacante.jugadores_campo.values()
            if jug_p.esta_en_campo and not jug_p.lesionado and not jug_p.expulsado and \
                jug_p != lanzador_corner and jug_p.posicion_actual != "Portero"
        ]
        if not posibles_rematadores:
            self.registrar_evento_reporte(f"Nadie para remate para {equipo_atacante.nombre}.", self.minuto_actual_display)
            self.equipo_con_balon = equipo_defensor
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            return
        total_sh_ponderado = sum((float(jug_p.django_futbolista.sh if jug_p.django_futbolista.sh else 0) + 10) for jug_p in posibles_rematadores)
        rematador = None
        if total_sh_ponderado > 0:
            valor_aleatorio = random.uniform(0, total_sh_ponderado)
            sh_acumulado = 0
            for jug_p in posibles_rematadores:
                sh_acumulado += (float(jug_p.django_futbolista.sh if jug_p.django_futbolista.sh else 0) + 10)
                if valor_aleatorio <= sh_acumulado:
                    rematador = jug_p
                    break
        if not rematador:
            rematador = random.choice(posibles_rematadores)

        prob_remate_bloqueado = 0
        if denominador_despeje > 0:
            prob_remate_bloqueado = int(1800.0 * (numerador_despeje / denominador_despeje))
            prob_remate_bloqueado = max(500, min(prob_remate_bloqueado, 5000)) # 5% a 50%
        else:
            prob_remate_bloqueado = 500

        if random.randint(0, 9999) < prob_remate_bloqueado: 
            bloqueador = equipo_defensor.seleccionar_jugador_contribucion("tk_contrib", crear_nombre_zona(ZONA_BASE_AREA_RIVAL, banda_corner))
            if not bloqueador:
                posibles_bloqueadores = [p for p in equipo_defensor.jugadores_campo.values() if p.esta_en_campo and not p.lesionado and not p.expulsado and p.posicion_actual != "Portero"]
                if posibles_bloqueadores:
                    bloqueador = random.choice(posibles_bloqueadores)
            self.generar_comentario_evento(
                "CORNER_CLEARED",
                equipo_atacante,
                jugador_principal = bloqueador,
            )
            bloqueador.intercepciones_partido += 1
            self.equipo_con_balon = equipo_defensor
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
            return

        # Remate
        self.generar_comentario_evento(
            "CORNER_SHOT",
            equipo_atacante,
            jugador_principal = rematador,
        )

        if rematador.es_disparo_puerta():
            rematador.disparos_puerta_partido += 1 
            equipo_atacante.disparos_a_puerta = getattr(equipo_atacante, 'disparos_a_puerta', 0) + 1
            prob_gol_calculada = rematador.calcular_probabilidad_gol_vs_potero(portero_defensor)

            if random.randint(0, 9999) < prob_gol_calculada: # es gol
                if random.randint(0, 9999) < 350: # Gol anulado?
                    self.generar_comentario_evento(
                        "GOALCANCELLED",
                        equipo_atacante,
                    )
                    return  # Gol anulado
                if equipo_atacante == self.equipo_local_sim:
                    self.goles_local += 1
                else:
                    self.goles_visitante += 1

                rematador.goles_partido += 1
                equipo_atacante.goles += 1
                lanzador_corner.asistencias_partido += 1

                if portero_defensor:
                    portero_defensor.goles_concedidos = getattr(portero_defensor, 'goles_concedidos', 0) + 1
                self.generar_comentario_evento(
                    "CORNER_SHOT",
                    equipo_atacante,
                    jugador_principal = rematador,
                )
                self.generar_comentario_evento(
                    "GOAL",
                    equipo_atacante,
                    jugador_principal = rematador,
                )
                self.equipo_con_balon = equipo_defensor
                self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, random.choice(LISTA_BANDAS))
            else: # Parada del portero
                self.generar_comentario_evento(
                    "SAVE",
                    equipo_defensor,
                    jugador_principal = portero_defensor if portero_defensor else "el guardameta",
                )
                if portero_defensor:
                    portero_defensor.paradas_partido += 1
                if random.randint(0, 9999) < 1500: # 15% de otro corner
                    self.generar_comentario_evento(
                        "SAVE4CORNER",
                        equipo_defensor,
                        jugador_principal = portero_defensor,
                    )
                    self._simular_corner(equipo_atacante)
                else:
                    self.equipo_con_balon = equipo_defensor
                    self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))
                    return
        else: # Remate fuera
            rematador.disparos_fuera_partido += 1
            equipo_atacante.disparos_fuera = getattr(equipo_atacante, 'disparos_fuera', 0) + 1
            self.generar_comentario_evento(
                "OFFTARGET",
                equipo_atacante,
            )
            self.equipo_con_balon = equipo_defensor
            self.zona_balon = crear_nombre_zona(ZONA_BASE_DEFENSIVA_PROPIA, random.choice(LISTA_BANDAS))

    def _calcular_mvp(self):
        """Calcula el mejor jugador por equipo y el mejor jugador global.
        
        Retorna: (best_local, best_visitante, best_overall)
        Cada elemento: (JugadorPartido_obj, score) o (None,o.o)
        """
        def score_jugador(j):
            if not j:
                return 0.0
            goles = getattr(j, 'goles_partido', 0)
            asist = getattr(j, 'asistencias_partido', 0)
            disparos_puerta = getattr(j, 'disparos_puerta_partido', 0)
            pases = getattr(j, 'pases_completados_partido', 0)
            intercepciones = getattr(j, 'intercepciones_partido', 0)
            paradas = getattr(j, 'paradas_partido', 0)
            amarillas = getattr(j, 'tarjeta_amarilla_partido', 0)
            rojas = getattr(j, 'tarjeta_roja_partido', 0)
            minutos = getattr(j, 'minutos_jugados', 0)
            
            s = 0.0
            s += goles * 50.0
            s += asist * 30.0
            s += disparos_puerta * 5.0
            s += pases * 3.0
            s += intercepciones * 2.0
            s += paradas * 10.0
            s += minutos * 0.1
            s -= amarillas * 0.3
            s -= rojas * 0.5
            
            # Bonus por portería a cero
            try:
                if j.posicion_actual == "Portero" or j.posicion_original == "Portero":
                    equipo = self.get_equipo_jugador(j)
                    if equipo:
                        oponente = self.get_equipo_oponente(equipo)
                        if oponente and getattr(oponente, 'goles', 0) == 0:
                            s += 20.0
            except Exception:
                pass
            
            return float(s)
        
        # Inicializar flags mom en JugadorPartido
        for eq in [self.equipo_local_sim, self.equipo_visitante_sim]:
            if not eq:
                continue
            for jp in list(eq.jugadores_campo.values()) + list(eq.jugadores_banquillo.values()):
                try:
                    setattr(jp, 'mom', False)
                except Exception:
                    pass
                
        best_local = (None, 0.0)
        best_visit = (None, 0.0)
        
        if self.equipo_local_sim:
            for jp in self.equipo_local_sim.jugadores_campo.values() + list(self.equipo_local_jugadores_banquillo.values()):
                s = score_jugador(jp)
                if s > best_local[1]:
                    best_local = (jp, s)
                    
        if self.equipo_visitante_sim:
            for jp in self.equipo_visitante_sim.jugadores_campo.values() + list(self.equipo_visitante_jugadores_banquillo.values()):
                s = score_jugador(jp)
                if s > best_visit[1]:
                    best_visit = (jp, s)
                    
        # Comparar los 2 mejores para el global
        candidatos = []
        if best_local[0]:
            candidatos.append(best_local)
        if best_visit[0]:
            candidatos.append(best_visit)
        
        best_overall = (None, 0.0)
        for cand in candidatos:
            if cand[1] > best_overall[1]:
                best_overall = cand
                
        # Marcar mom en objetos JugadorPartido
        if best_local[0]:
            try:
                best_local[0].mom = True
            except Exception:
                pass
        if best_visit[0]:
            try:
                best_visit[0].mom = True
            except Exception:
                pass
        if best_overall[0]:
            try:
                best_overall[0].mom = True
            except Exception:
                pass
                
        return best_local, best_visit, best_overall
                

    def guardar_reporte_partido(self, ruta_reportes= PARTIDOS_DIR):
        """Guarda el reporte del partido en un archivo."""
        if not self.equipo_local_sim or not self.equipo_visitante_sim:
            print("Error: Equipos no cargados correctamente. No se puede guardar el reporte.")
            return
        
        equipo_django = self.equipo_local_sim.django_equipo
        nombre_carpeta = (
            f"reportes_division_{equipo_django.division}_grupo_{equipo_django.grupo}"
        )
        ruta_carpeta = os.path.join(ruta_reportes, nombre_carpeta)
        nombre_archivo = f"{self.equipo_local_nombre_str}_vs_{self.equipo_visitante_nombre_str}_{self.fecha_partido_str}.html"
        ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)

        goleadores_local_list = []
        goleadores_visitante_list = []
        amonestados_local_list = []
        amonestados_visitante_list = []
        expulsados_local_list = []
        expulsados_visitante_list = []

        def procesar_jugadores_equipo(equipo_sim, goleadores_list, amonestados_list, expulsados_list):
            if not equipo_sim:
                return

            todos_jugadores_equipo = list(equipo_sim.jugadores_campo.values()) + list(equipo_sim.jugadores_banquillo.values())
            for jugador in todos_jugadores_equipo:
                # Goleadores
                if jugador.goles_partido > 0:
                    goleadores_list.append(f"{jugador.nombre} ({jugador.goles_partido})")
                if jugador.goles_propia_partido > 0:
                    goleadores_list.append(f"{jugador.nombre} ({jugador.goles_propia_partido} p.p)")

                # Expulsados
                if jugador.expulsado:
                    expulsados_list.append(jugador.nombre)

                # Amonestados
                elif jugador.tarjeta_amarilla_partido > 0:
                    amonestados_list.append(jugador.nombre)

        procesar_jugadores_equipo(self.equipo_local_sim, goleadores_local_list, amonestados_local_list, expulsados_local_list)
        procesar_jugadores_equipo(self.equipo_visitante_sim, goleadores_visitante_list, amonestados_visitante_list, expulsados_visitante_list)       

        _, _, mejor_jugador = self._calcular_mvp()
        jugador_mvp, puntuacion_mvp = mejor_jugador
        if jugador_mvp:
            equipo_mvp = self.get_equipo_jugador(jugador_mvp)
            nombre_mejor_jugador = (
                f"{jugador_mvp.nombre} - "
                f"{equipo_mvp.nombre if equipo_mvp else 'N/A'} "
                f"(Puntuación: {puntuacion_mvp:.1f})"
            )
        else:
            nombre_mejor_jugador = "Ninguno"
        
        contexto = {
            "local": self.equipo_local_nombre_str,
            "visitante": self.equipo_visitante_nombre_str,
            "goles_local": self.goles_local,
            "goles_visitante": self.goles_visitante,
            "fecha": self.fecha_partido_str,
            "hora": self.hora_partido_str,
            "estadio": self.nombre_estadio,
            "asistencia": self.asistencia,
            "arbitro": self.arbitro.nombre if self.arbitro else "Árbitro no asignado",
            "mejor_jugador": nombre_mejor_jugador,
            "alineacion_local": self.equipo_local_sim.get_alineacion_str(),
            "alineacion_visitante": self.equipo_visitante_sim.get_alineacion_str(),
            "eventos": self.eventos_partido_reporte,
            "goleadores_local": goleadores_local_list,
            "goleadores_visitante": goleadores_visitante_list,
            "amonestados_local": amonestados_local_list,
            "amonestados_visitante": amonestados_visitante_list,
            "expulsados_local": expulsados_local_list,
            "expulsados_visitante": expulsados_visitante_list,
            "lesionados": self.lesionados_partido_info,
        }
        contenido_html = render_to_string(
            "administracion/reporte_partido.html", contexto
        )
        try:
            os.makedirs(ruta_carpeta, exist_ok=True)  # Asegurarse de que el directorio exista
            
            with open(ruta_completa, 'w', encoding='utf-8') as archivo:
                archivo.write(contenido_html)

            print(f"Reporte del partido guardado en: {ruta_completa}")
        except OSError as e:
            print(f"Error al guardar el reporte: {e}")


    def simular_parte(self, duracion_minutos, es_primera_parte=True, tiempo_añadido=0):
        """Simula una parte del partido."""
        if not self.equipo_local_sim or not self.equipo_visitante_sim:
            self.eventos_partido.append("Error: Equipos no cargados correctamente.")
            return
        self.zona_balon = crear_nombre_zona(ZONA_BASE_MEDIO_CAMPO_DEFENSIVO, random.choice(LISTA_BANDAS))
        if es_primera_parte:
            self.registrar_evento_reporte(f"--- Inicio de la primera parte: {self.equipo_local_nombre_str} vs {self.equipo_visitante_nombre_str} ---\n")
            self.equipo_con_balon = random.choice([self.equipo_local_sim, self.equipo_visitante_sim])
            self.equipo_saca_primera_parte = self.equipo_con_balon
        else:
            self.registrar_evento_reporte(f"\n--- Inicio de la segunda parte: {self.equipo_local_nombre_str} vs {self.equipo_visitante_nombre_str} ---\n")
            if self.equipo_con_balon == self.equipo_saca_primera_parte:
                self.equipo_con_balon = self.get_equipo_oponente(self.equipo_con_balon)
        for minuto in range(1, duracion_minutos + 1):
            self.minuto_actual_display = minuto if es_primera_parte else minuto + TIEMPO_REGLAMENTARIO_PARTE
            if minuto == 43:
                self.registrar_evento_reporte(
                    f"Min {self.minuto_actual_display}: Se añadirán {tiempo_añadido} minutos de tiempo extra"
                )
            self._actualizar_estado_equipos_minuto()
            self._actualizar_minutos_jugados_partido()
            if self.equipo_local_sim:
                self.equipo_local_sim.procesar_instrucciones_minuto(self.minuto_actual_display)
            if self.equipo_visitante_sim:
                self.equipo_visitante_sim.procesar_instrucciones_minuto(self.minuto_actual_display)

            # Posibilidad de falta
            equipo_potencial_infractor = None
            equipo_potencial_victima = None
            if self.equipo_con_balon:
                equipo_potencial_infractor = self.get_equipo_oponente(self.equipo_con_balon)
                equipo_potencial_victima = self.equipo_con_balon
                if equipo_potencial_infractor and not self._simular_falta_y_sancion(equipo_potencial_infractor, equipo_potencial_victima):
                    self._simular_eventos_minuto()
            
            # Simular lesion independiente de faltas
            if self.equipo_local_sim and self.equipo_visitante_sim:
                self._simular_lesion_golpe(self.equipo_local_sim, self.equipo_visitante_sim)
                self._simular_lesion_golpe(self.equipo_visitante_sim, self.equipo_local_sim)

        if es_primera_parte:
            self.registrar_evento_reporte(
                f"\n--- Final de la primera parte. Marcador al descanso: {self.equipo_local_sim.nombre} ({self.equipo_local_sim.django_equipo.abreviatura}) {self.goles_local} - {self.goles_visitante} {self.equipo_visitante_sim.nombre} ({self.equipo_visitante_sim.django_equipo.abreviatura})\n---",
                self.minuto_actual_display
            )

    def simular_partido(self):
        """Simula el partido completo."""
        if not self._configurar_partido():
            print("Error al configurar el partido. No se puede simular.")
            return
        extra_time1, extra_time2 = random.randint(1, 6), random.randint(1, 6)

        # Simular primera parte
        self.simular_parte(TIEMPO_REGLAMENTARIO_PARTE + extra_time1, es_primera_parte=True, tiempo_añadido=extra_time1)
        self.goles_descanso_local, self.goles_descanso_visitante = self.goles_local, self.goles_visitante
        self.eventos_partido.extend([
            "\n--- Descanso ---",
            f"Marcador al descanso: {self.goles_descanso_local} - {self.goles_descanso_visitante}"
        ])
        # Simular segunda parte
        self.simular_parte(duracion_minutos= TIEMPO_REGLAMENTARIO_PARTE + extra_time2, es_primera_parte=False, tiempo_añadido=extra_time2)
        self.eventos_partido.extend([
            "\n--- Fin del partido ---",
            f"Marcador final: {self.goles_local} - {self.goles_visitante}",
            f"Asistencia final: {self.asistencia}"
        ])
        if self.es_oficial:
            self._actualizar_habilidades_estadisticas_post_partido()
        self.guardar_reporte_partido()
        if self.es_copa and self.goles_local == self.goles_visitante:
            self.eventos_partido.append("El partido ha terminado en empate. Se jugará una prórroga.")
            self.simular_prorroga()
        return self.eventos_partido
    
    @transaction.atomic
    def _actualizar_habilidades_estadisticas_post_partido(self):
        """Actualiza las habilidades y estadísticas después del partido."""
        for equipo_sim in [self.equipo_local_sim, self.equipo_visitante_sim]:
            if not equipo_sim:
                continue
            
            oponente_sim = self.get_equipo_oponente(equipo_sim)
            es_ganador = equipo_sim.goles > oponente_sim.goles if oponente_sim else False
            es_perdedor = equipo_sim.goles < oponente_sim.goles if oponente_sim else False
            porteria_cero = oponente_sim.goles == 0 if oponente_sim else False
            
            # Incluir jugadores que han jugado algun minuto
            jugadores_procesar = []
            for jp_key , jp_obj in equipo_sim.jugadores_campo.items():
                if jp_obj.minutos_jugados > 0 or jp_obj.lesionado or jp_obj.expulsado:
                    jugadores_procesar.append(jp_obj)
            for jp_key , jp_obj in equipo_sim.jugadores_banquillo.items():
                if jp_obj.minutos_jugados > 0:
                    jugadores_procesar.append(jp_obj)

            for jug_p in jugadores_procesar:
                if not jug_p.django_futbolista:
                    continue

                # Actualizar habilidades en el objeto django
                df_player = jug_p.django_futbolista

                df_player.sh_hab += AB_GOAL * jug_p.goles_partido
                df_player.ps_hab += AB_ASSIST * jug_p.asistencias_partido
                df_player.tk_hab += AB_KTK * jug_p.intercepciones_partido
                df_player.ps_hab += AB_KPS * jug_p.pases_completados_partido
                df_player.sh_hab += AB_SHT_ON * jug_p.disparos_puerta_partido
                df_player.sh_hab += AB_SHT_OFF * jug_p.disparos_fuera_partido
                df_player.tk_hab += AB_OWN_GOAL * jug_p.goles_propia_partido

                if jug_p.posicion_actual == "Portero" or jug_p.posicion_original == "Portero":
                    df_player.st_hab += AB_SAV * jug_p.paradas_partido
                    df_player.st_hab += AB_CONCEDE * jug_p.goles_concedidos_partido
                    df_player.st_hab += AB_YELLOW * jug_p.tarjeta_amarilla_partido
                    if jug_p.tarjeta_roja_partido: df_player.st_hab += AB_RED
                else:
                    df_player.tk_hab += AB_YELLOW * jug_p.tarjeta_amarilla_partido
                    df_player.ps_hab += AB_YELLOW * jug_p.tarjeta_amarilla_partido
                    df_player.sh_hab += AB_YELLOW * jug_p.tarjeta_amarilla_partido
                    if jug_p.tarjeta_roja_partido:
                        df_player.tk_hab += AB_RED
                        df_player.ps_hab += AB_RED
                        df_player.sh_hab += AB_RED

                # Actualizar habilidad principal si sub-habilidad llego a 1000
                sub_habilidades_map = {
                    'st_hab': 'st', 'tk_hab': 'tk',
                    'ps_hab': 'ps', 'sh_hab': 'sh'
                }
                for sub_hab_attr, main_hab_attr in sub_habilidades_map.items():
                    valor_actual_sub_skill = getattr(df_player, sub_hab_attr, 0)
                    if valor_actual_sub_skill >= SUB_SKILL_THRESHOLD:
                        setattr(df_player, main_hab_attr,
                                getattr(df_player, main_hab_attr,  50) + MAIN_SKILL_INCREMENT)
                        setattr(df_player, sub_hab_attr, SUB_SKILL_RESET_VALUE)
                    elif valor_actual_sub_skill < MIN_SUB_SKILL_VALUE:
                        setattr(df_player, sub_hab_attr, MIN_SUB_SKILL_VALUE)

                # Actualizar estadisticas generales en BD
                df_player.partidos += 1
                df_player.goles += jug_p.goles_partido
                df_player.asistencias += jug_p.asistencias_partido
                df_player.tiros += jug_p.disparos_puerta_partido
                df_player.pases_buenos += jug_p.pases_completados_partido
                if jug_p.posicion_actual == "Portero" or jug_p.posicion_original == "Portero":
                    df_player.paradas += jug_p.paradas_partido
                else:
                    df_player.takling += jug_p.intercepciones_partido

                if jug_p.tarjeta_amarilla_partido > 0:
                    df_player.disciplina += 2 * jug_p.tarjeta_amarilla_partido
                if jug_p.tarjeta_roja_partido: 
                    df_player.disciplina += 10

                if jug_p.lesionado and jug_p.semanas_lesionado > 0:
                    df_player.lesion = jug_p.semanas_lesionado

                # Actualizar participo_ultimo_partido
                if jug_p.minutos_jugados > 0:
                    df_player.participo_ultimo_partido = True

                # Guardar cambios en la BD
                try:
                    df_player.save()
                except Exception as e:
                    print(f"Error al guardar cambios en la BD: {e}")
                    continue

            # Actualizar estadisticas del equipo
            equipo_django = equipo_sim.django_equipo
            equipo_django.partidos_jugados += 1
            equipo_django.goles_favor += equipo_sim.goles
            equipo_django.goles_contra += oponente_sim.goles if oponente_sim else 0
            
            if es_ganador:
                equipo_django.victorias += 1
                equipo_django.puntos += 3
            elif es_perdedor:
                equipo_django.derrotas += 1
            else:
                equipo_django.empates += 1
                equipo_django.puntos += 1

            try:
                equipo_django.save()
            except Exception as e:
                print(f"Error al guardar cambios en la BD para el equipo {equipo_sim.nombre}: {e}")
                continue

            # Bonificaciones/Penalizaciones por Victoria/Derrota/Porteria a 0
            jugadores_campo_activos = [jp_obj for jp_key, jp_obj in equipo_sim.jugadores_campo.items() if jp_obj.esta_en_campo and jp_obj.minutos_jugados > 0 and not jp_obj.expulsado]
            if not jugadores_campo_activos:
                continue
            
            if es_ganador:
                for _ in range (min(2, len(jugadores_campo_activos))):
                    jug_seleccionado = random.choice(jugadores_campo_activos)
                    if jug_seleccionado.posicion_actual == "Portero":
                        jug_seleccionado.django_futbolista.st_hab += AB_VICTORY_RANDOM
                    else:
                        jug_seleccionado.django_futbolista.tk_hab += AB_VICTORY_RANDOM // 3
                        jug_seleccionado.django_futbolista.ps_hab += AB_VICTORY_RANDOM // 3
                        jug_seleccionado.django_futbolista.sh_hab += AB_VICTORY_RANDOM // 3
                    jug_seleccionado.django_futbolista.save()
                    if len(jugadores_campo_activos) > 1:
                        jugadores_campo_activos.remove(jug_seleccionado)

            if es_perdedor:
                for _ in range (min(2, len(jugadores_campo_activos))):
                    jug_seleccionado = random.choice(jugadores_campo_activos)
                    if jug_seleccionado.posicion_actual == "Portero":
                        jug_seleccionado.django_futbolista.st_hab += AB_DEFEAT_RANDOM
                    else:
                        jug_seleccionado.django_futbolista.tk_hab += AB_DEFEAT_RANDOM // 3
                        jug_seleccionado.django_futbolista.ps_hab += AB_DEFEAT_RANDOM // 3
                        jug_seleccionado.django_futbolista.sh_hab += AB_DEFEAT_RANDOM // 3
                    jug_seleccionado.django_futbolista.save()
                    if len(jugadores_campo_activos) > 1:
                        jugadores_campo_activos.remove(jug_seleccionado)

            if porteria_cero:
                for _ in range (min(2, len(jugadores_campo_activos))):
                    jug_seleccionado = random.choice(jugadores_campo_activos)
                    if jug_seleccionado.posicion_actual == "Portero":
                        jug_seleccionado.django_futbolista.st_hab += AB_PORT_ZERO_RANDOM
                    else:
                        jug_seleccionado.django_futbolista.tk_hab += AB_PORT_ZERO_RANDOM // 3
                        jug_seleccionado.django_futbolista.ps_hab += AB_PORT_ZERO_RANDOM // 3
                        jug_seleccionado.django_futbolista.sh_hab += AB_PORT_ZERO_RANDOM // 3
                    jug_seleccionado.django_futbolista.save()
                    if len(jugadores_campo_activos) > 1:
                        jugadores_campo_activos.remove(jug_seleccionado)



    def get_equipo_oponente(self, equipo_actual_sim):
        """Obtiene el equipo oponente."""
        if equipo_actual_sim == self.equipo_local_sim:
            return self.equipo_visitante_sim
        elif equipo_actual_sim == self.equipo_visitante_sim:
            return self.equipo_local_sim
        else:
            return None
        
    def realizar_sustitucion(self, equipo_sim, jugador_sale_obj, jugador_entra_obj, pos_entra_str):
        """
        Realiza una sustitución de un jugador por otro en el equipo especificado.

        Args:
            equipo_sim (EquipoSimulado): El equipo que realiza la sustitución.
            jugador_sale_obj (JugadorPartido): El objeto JugadorPartido que sale del campo.
            jugador_entra_obj (JugadorPartido): El objeto JugadorPartido que entra al campo.
            pos_entra_str (str): La posición a la que entra el nuevo jugador.

        Returns:
            bool: True si la sustitución fue exitosa, False en caso contrario.
        """
        if not equipo_sim or not jugador_sale_obj or not jugador_entra_obj or not pos_entra_str:
            return False
        # Verificar limite de sustituciones
        if self.substituciones_realizadas_equipo[equipo_sim.nombre] >= self.num_substituciones:
            self.registrar_evento_reporte(f"Límite de sustituciones alcanzado para {equipo_sim.nombre}.", self.minuto_actual_display)
            return False
        
        # Encontrar las claves de los jugadores en los diccionarios del equipo
        key_jugador_sale = None
        for key, jug_p in equipo_sim.jugadores_campo.items():
            if jug_p == jugador_sale_obj:
                key_jugador_sale = key
                break

        key_jugador_entra = None
        for key, jug_p in equipo_sim.jugadores_banquillo.items():            
            if jug_p == jugador_entra_obj:
                key_jugador_entra = key
                break

        if not key_jugador_sale or not key_jugador_entra:
            self.registrar_evento_reporte("Jugador no encontrado", self.minuto_actual_display)
            return False
        
        # Realizar la sustitución
        #Mover jugador que entra al campo
        equipo_sim.jugadores_campo[key_jugador_entra] = jugador_entra_obj
        del equipo_sim.jugadores_banquillo[key_jugador_entra]
        jugador_entra_obj.esta_en_campo = True
        jugador_entra_obj.posicion_actual = pos_entra_str
        jugador_entra_obj.minutos_jugados = 0

        #Mover jugador que sale al banquillo
        equipo_sim.jugadores_banquillo[key_jugador_sale] = jugador_sale_obj
        del equipo_sim.jugadores_campo[key_jugador_sale]
        jugador_sale_obj.esta_en_campo = False
        
        # Actualizar estadísticas
        self.substituciones_realizadas_equipo[equipo_sim.nombre] += 1
        
        return True
    
    def _determinar_gravedad_lesion(self, jugador_lesionado):
        """Determina la duracion en semanas de una lesion"""
        if random.randint(0, 9999) < PROB_LESION_GRAVE:
            jugador_lesionado.semanas_lesionado = random.randint(MINIMO_SEMANAS_LESION, MAXIMO_SEMANAS_LESION_GRAVE)
            self.generar_comentario_evento("INJURY_SEVERE", self.get_equipo_jugador(jugador_lesionado), jugador_lesionado)
        else: 
            jugador_lesionado.semanas_lesionado = random.randint(MINIMO_SEMANAS_LESION, MAXIMO_SEMANAS_LESION_DEFECTO)
            self.generar_comentario_evento("INJURY", self.get_equipo_jugador(jugador_lesionado), jugador_lesionado)

        # Guardar informacion para el reporte
        info_lesion_reporte = f"{jugador_lesionado} ({self.get_equipo_jugador(jugador_lesionado).nombre if self.get_equipo_jugador(jugador_lesionado) else 'N/A'}) - Lesionado en min {jugador_lesionado.minuto_lesion}, baja {jugador_lesionado.semanas_lesionado} semanas."
        self.lesionados_partido_info.append(info_lesion_reporte)

    def get_equipo_jugador(self, jugador_obj):
        """Devuelve el objeto EquipoSimulado al que pertenece un JugadorPartido."""
        for equipo_sim in [self.equipo_local_sim, self.equipo_visitante_sim]:
            if equipo_sim:
                if jugador_obj.key_jugador in equipo_sim.jugadores_campo or \
                    jugador_obj.key_jugador in equipo_sim.jugadores_banquillo:
                    return equipo_sim
        return None

    def _buscar_sustituto_para_lesionado(self, equipo_lesionado, jugador_lesionado_obj):
        """Busca un sustituto adecuado para un jugador lesionado """
        if not equipo_lesionado or not jugador_lesionado_obj:
            return None, None
        
        posicion_cubrir = jugador_lesionado_obj.posicion_actual
        sustitutos_disponibles = [p for p in equipo_lesionado.jugadores_banquillo.values() if not p.lesionado and not p.expulsado]

        if not sustitutos_disponibles:
            return None, None
        
        # Misma posicion
        for sub_candidato in sustitutos_disponibles:
            if sub_candidato.posicion_original == jugador_lesionado_obj.posicion_original and sub_candidato.posicion_original != "Portero":
                return sub_candidato, posicion_cubrir
            if sub_candidato.posicion_original == "Portero" and jugador_lesionado_obj.posicion_actual == "Portero":
                return sub_candidato, "Portero"
            
        # Posicion compatible, defensa por defensa, medio por medio...
        categoria_lesionado = CATEGORIAS_POSICIONES.get(posicion_cubrir)
        for sub_candidato in sustitutos_disponibles:
            categoria_candidato = CATEGORIAS_POSICIONES.get(sub_candidato.posicion_original)
            if categoria_candidato == categoria_lesionado and categoria_candidato != 0:
                return sub_candidato, posicion_cubrir
        
        # Cualquier jugador de campo disponible
        for sub_candidato in sustitutos_disponibles:
            if sub_candidato.posicion_original != "Portero":
                return sub_candidato, posicion_cubrir
            
        # Si no hay mas un portero podria entrar como jugador de campo o viceversa
        if jugador_lesionado_obj.posicion_actual == "Portero" and any(s.posicion_original != "Portero" for s in sustitutos_disponibles):
            # Si no hay portero suplente se busca un jugador de campo
            mejor_opcion_campo = sorted(sustitutos_disponibles, key=lambda p: getattr(p.django_futbolista, 'ps', 0), reverse=True)
            if mejor_opcion_campo:
                return mejor_opcion_campo[0], "Portero"
            
        # Si todo lo demas falla, el primero disponible
        if sustitutos_disponibles:
            return sustitutos_disponibles[0], posicion_cubrir
        
        return None, None

    def _manejar_portero_lesionado_sin_sustituto(self, equipo_afectado):
        """Maneja el caso de portero lesionado cuando no hay sustitutos de portero o generales"""
        self.generar_comentario_evento("INJURY_GK_NO_SUB", equipo_afectado, jugador_principal=equipo_afectado.get_portero_actual())
        
        mejor_jugador_campo_portero = None
        max_habilidiad_portero_improvisado = 1

        jugadores_campo_activos = [
            p for p in equipo_afectado.jugadores_campo.values()
            if p.esta_en_campo and not p.lesionado and not p.expulsado and p.posicion_actual != "Portero"
        ]

        if not jugadores_campo_activos:
            self.generar_comentario_evento("INJURY_TEAM_CRIPPLED", equipo_afectado)
            return
        
        # Mejor st
        for jug_p in jugadores_campo_activos:
            habilidad_evaluada = float(jug_p.django_futbolista.st) * 0.5 + float(jug_p.django_futbolista.resistencia) * 0.5
            if habilidad_evaluada > max_habilidiad_portero_improvisado:
                max_habilidiad_portero_improvisado = habilidad_evaluada
                mejor_jugador_campo_portero = jug_p
        
        if mejor_jugador_campo_portero:
            pos_anterior = mejor_jugador_campo_portero.posicion_actual
            mejor_jugador_campo_portero.posicion_actual = "Portero"
            self.generar_comentario_evento("INJURY_OUTFIELDER_AS_GK", equipo_afectado, jugador_principal=mejor_jugador_campo_portero, datos_adicionales={"<old_pos>": pos_anterior})

        else:
            self.generar_comentario_evento("INJURY_GK_CRISIS", equipo_afectado)

    def _simular_lesion_golpe(self, equipo_victima, equipo_rival):
        """Simula la posibilidad de una lesion o un golpe leve para un equipo"""
        if not equipo_victima or not equipo_rival:
            return

        #Lesion grave
        prob_lesion = PROB_LESION_BASE + (equipo_rival.agresion * FACTOR_AGRESION_OPONENTE_PROB)
        if not EFECTO_LESION_SALUD:
            prob_lesion *= MULTIPLICADOR_PROB_NO_EFECTO_LESION

        prob_lesion = int(max(0, min(prob_lesion, 9000)))

        if random.randint(0, 9999) < prob_lesion:
            jugador_lesionado = None
            jugadores_campo_aptos = [
                p for p in equipo_victima.jugadores_campo.values()
                if p.esta_en_campo and not p.lesionado and not p.expulsado
            ]
            if not jugadores_campo_aptos:
                return # No hay jugadores para lesionarse
            
            if EFECTO_LESION_SALUD:
                pesos = []
                for p in jugadores_campo_aptos:
                    peso = PESO_RESISTENCIA_SELECCION_BASE + \
                    ((100.0 - p.resistencia_actual) * FACTOR_PESO_RESISTENCIA_SELECCION_LESIONADO)
                    pesos.append(max(1, peso)) # Asegurar peso minimo
                if sum(pesos) > 0:
                    jugador_lesionado = random.choices(jugadores_campo_aptos, weights=pesos, k=1)[0]
                else:
                    jugador_lesionado = random.choice(jugadores_campo_aptos)
            else:
                jugador_lesionado = random.choice(jugadores_campo_aptos)

            if jugador_lesionado:
                jugador_lesionado.lesionado = True
                jugador_lesionado.minuto_lesion = self.minuto_actual_display
                self._determinar_gravedad_lesion(jugador_lesionado)

                equipo_victima.lesion = getattr(equipo_victima, 'lesion', 0) + 1

                self.generar_comentario_evento("INJURY", equipo_victima, jugador_principal=jugador_lesionado)

                # Sustitucion
                if self.substituciones_realizadas_equipo[equipo_victima.nombre] < self.num_substituciones:
                    sustituto_obj, pos_para_sustituto = self._buscar_sustituto_para_lesionado(equipo_victima, jugador_lesionado)
                    if sustituto_obj and pos_para_sustituto:
                        exito_sub = self.realizar_sustitucion(equipo_victima, jugador_lesionado, sustituto_obj, pos_para_sustituto)
                        if exito_sub:
                            self.generar_comentario_evento("SUB_INJURY", equipo_victima, jugador_principal=jugador_lesionado, jugador_secundario=sustituto_obj)
                        else: # Fallo la sustitucion
                            jugador_lesionado.esta_en_campo = False
                            self.generar_comentario_evento("INJURY_NO_SUB_FOUND", equipo_victima, jugador_principal=jugador_lesionado)
                            if jugador_lesionado.posicion_actual == "Portero":
                                self._manejar_portero_lesionado_sin_sustituto(equipo_victima)
                    else: # No se encontro sustituto adecuado
                        jugador_lesionado.esta_en_campo = False
                        self.generar_comentario_evento("INJURY_NO_SUB_FOUND", equipo_victima, jugador_principal=jugador_lesionado)
                        if jugador_lesionado.posicion_actual == "Portero":
                            self._manejar_portero_lesionado_sin_sustituto(equipo_victima)
                else: # No quedan sustituciones
                    jugador_lesionado.esta_en_campo = False
                    self.generar_comentario_evento("INJURY_NO_SUBS_LEFT", equipo_victima, jugador_principal=jugador_lesionado)
                    if jugador_lesionado.posicion_actual == "Portero":
                        self._manejar_portero_lesionado_sin_sustituto(equipo_victima)
                return # Se proceso lesion, no comprobar golpe leve en este minuto
            
        # Golpe leve (si no hubo lesion)
        prob_golpe = PROB_GOLPE_LEVE_BASE + (equipo_rival.agresion * FACTOR_AGRESION_OPONENTE_PROB)
        prob_golpe = int(max(0, min(prob_golpe, 8000)))

        if random.randint(0, 9999) < prob_golpe:
            jugadores_campo_aptos_golpe = [
                p for p in equipo_victima.jugadores_campo.values()
                if p.esta_en_campo and not p.lesionado and not p.expulsado
            ]
            if jugadores_campo_aptos_golpe:
                jugador_golpeado = random.choice(jugadores_campo_aptos_golpe)
                self.generar_comentario_evento("KNOCK", equipo_victima, jugador_principal=jugador_golpeado)

            