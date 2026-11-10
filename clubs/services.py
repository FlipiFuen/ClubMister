import os
import json

from datetime import datetime, timedelta

from django.shortcuts import redirect
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _ 

from clubs.models import Alineacion, Equipo, Futbolista
from administracion.models import PartidoProgramado
from administracion.Partidos.constantes import PARTIDOS_DIR

def calcular_calificacion(valor):
    """Devuelve un adjetivo de calificación según el valor."""
    if valor <= 5:
        return _("INUTIL")
    elif valor == 6 or valor == 7:
        return _("APRENDIZ")
    elif valor == 8 or valor == 9:
         return _("PRINCIPIANTE")
    elif valor == 10:
      return _("ACEPTABLE")
    elif valor == 11:
      return _("BUENO")
    elif valor == 12:
      return _("MAGNIFICO")
    elif valor == 13:
      return _("ESPLENDIDO")
    elif valor == 14:
      return _("ELITE")
    elif valor == 15:
      return _("MAESTRO")
    elif valor == 16:
      return _("ESTRELLA")
    elif valor == 17:
      return _("CRACK")
    elif valor == 18:
      return _("PLATA")
    elif valor == 19:
      return _("ORO")
    elif valor == 20:
      return _("GOAT")
  
def calcular_resistencia(valor):
    """Devuelve un adjetivo de resistencia según el valor."""
    if valor < 40:
        return _("AGOTADO")
    elif valor >= 40 and valor < 50:
        return _("CANSADO")
    elif valor >= 50 and valor < 60:
        return _("EN FORMA")
    elif valor >= 60 and valor < 80:
        return _("UN TORO")
    elif valor >= 80 and valor < 101:
        return _("TANQUE")
    
def lado_preferido(valor):
    """Devuelve un adjetivo de lado preferido según el valor."""
    lados = {
      "D": _("DERECHA"),
      "I": _("IZQUIERDA"),
      "C": _("CENTRO"),
      "D-I": _("IZQUIERDA-DERECHA"),
      "D-C": _("CENTRO-DERECHA"),
      "I-C": _("IZQUIERDA-CENTRO"),
      "D-L-C": _("IZQUIERDA-CENTRO-DERECHA"),
      "D-I-C": _("IZQUIERDA-CENTRO-DERECHA"),
    }

    return lados.get(valor, _("DESCONOCIDO"))

def calcular_agresividad(valor):
    """Devuelve un adjetivo de agresividad según el valor."""
    if valor < 29:
        calificacion = _("Calmado")
        return calificacion
    elif valor >= 29 and valor < 32:
        calificacion = _("Normal")
        return calificacion
    elif valor >= 32:
        calificacion = _("Agresivo")
        return calificacion
    
def enriquecer_jugador(jugador):
    """Calcula y asigna las propiedades dinámicas a un jugador"""
    jugador.porcentaje_st = min(max(jugador.st * 5, 0), 100)
    jugador.porcentaje_tk = min(max(jugador.tk * 5, 0), 100)
    jugador.porcentaje_ps = min(max(jugador.ps * 5, 0), 100)
    jugador.porcentaje_sh = min(max(jugador.sh * 5, 0), 100)
    jugador.calificacion_st = calcular_calificacion(jugador.st)
    jugador.calificacion_tk = calcular_calificacion(jugador.tk)
    jugador.calificacion_ps = calcular_calificacion(jugador.ps)
    jugador.calificacion_sh = calcular_calificacion(jugador.sh)
    jugador.calificacion_resistencia = calcular_resistencia(jugador.resistencia)
    jugador.lado = lado_preferido(jugador.lado_preferido)
    jugador.agresivo = calcular_agresividad(jugador.agresividad)

def obtener_equipo_plantilla(user):
    """Obtiene el equipo del usuario y su plantilla
       Devuelve una tupla (club, plantilla)"""
    try:
        club = Equipo.objects.get(user=user)
        plantilla = Futbolista.objects.filter(equipo=club).order_by('-st')
    
        for jugador in plantilla:
                enriquecer_jugador(jugador)
       
    except Equipo.DoesNotExist:
        plantilla = None
        club = None
        
    return club, plantilla

def obtener_proximo_partido(equipo):
    """Devuelve el próximo partido programado no jugado para el equipo del usuario"""
    return PartidoProgramado.objects.filter(
    Q(equipo_local=equipo) | Q(equipo_visitante=equipo),
    reporte__isnull = True
    ).order_by("jornada", "fecha", "hora").first()
    
def verificar_plazo_alineacion(partido):
    """
    Verifica si se puede enviar alineación para un partido:
    - No debe haber sido jugado aún
    - Debe enviarse al menos 15 minutos antes de la hora del partido
    Devuelve (puede_enviar: bool, mensaje: str, fecha_limite: datertime)
    """
    if hasattr(partido, "reporte") and partido.reporte is not None:
        return False, _("Este partido ya ha sido jugado"), None
    
    fecha_hora_partido = datetime.combine(partido.fecha, partido.hora)
    if timezone.is_aware(timezone.now()):
        fecha_hora_partido = timezone.make_aware(fecha_hora_partido, timezone.get_current_timezone())
        
    limite = fecha_hora_partido - timedelta(minutes=15)
    ahora = timezone.now()
    
    if ahora >= limite:
        return False, _("El plazo para enviar la alineación ha expirado (límite: 15 min antes)"), limite
    
    return True, _("Plazo abierto"), limite

def obtener_contexto_alineacion(equipo, partido=None):
    """Construye todo el diccionario de contexto necesario para renderizar alineacion.html"""
    posiciones = [
        {'codigo': 'GK', 'nombre': _("Portero")},
        {'codigo': 'DFL', 'nombre': _("Lateral Izquierdo")}, {'codigo': 'DFR', 'nombre': _("Lateral Derecho")},
        {'codigo': 'DFC', 'nombre': _("Central")}, {'codigo': 'DFCR', 'nombre': _("Central-Derecho")},
        {'codigo': 'DFCL', 'nombre': _("Central-Izquierdo")}, 
        {'codigo': 'DMR', 'nombre': _("Mediocentro-Defensivo-Der")}, {'codigo': 'DML', 'nombre': _("Mediocentro-Defensivo-Izq")},
        {'codigo': 'DMC', 'nombre': _("Mediocentro-Defensivo")}, {'codigo': 'MFC', 'nombre': _("Medio")},
        {'codigo': 'MFR', 'nombre': _("Medio-Derecho")}, {'codigo': 'MFL', 'nombre': _("Medio-Izquierdo")},
        {'codigo': 'AMC', 'nombre': _("Mediapunta")}, {'codigo': 'AMR', 'nombre': _("Mediapunta-Derecho")},
        {'codigo': 'AML', 'nombre': _("Mediapunta-Izquierdo")},
        {'codigo': 'FWR', 'nombre': _("Extremo-Derecho")}, {'codigo': 'FWL', 'nombre':_("Extremo-Izquierdo")},
        {'codigo': 'FWC', 'nombre': _("Delantero-Centro")}, {'codigo': 'FWCL', 'nombre': _("Delantero-Izquierdo")},
        {'codigo': 'FWCR', 'nombre': _("Delantero-Derecho")}, {'codigo': 'GK', 'nombre': _("Portero")},
        ]
    
    abrev_pos = [ "GK", "DFL", "DFR", "DFC", "DML", "DMR", "DMC", "MFL", "MFR", "MFC",
        "AML", "AMR", "AMC", "FWL", "FWR", "FWC", 
        ]
    plantilla = Futbolista.objects.filter(equipo=equipo).order_by('-st')
    
    # Si existe una alineación ya guardada en BD para este partido, la cargamos
    alineacion_guardada = None
    jugador_seleccionado = {}
    posicion_seleccionada = {}
    instrucciones = {}
    tiene_alineacion_guardada = False
    
    if partido:
        alineacion_obj = Alineacion.objects.filter(equipo=equipo, partido=partido).first()
        if alineacion_obj and alineacion_obj.datos:
            tiene_alineacion_guardada = True
            alineacion_guardada= alineacion_obj.datos
            jugador_seleccionado = alineacion_guardada.get("jugador_seleccionado", {})
            posicion_seleccionada = alineacion_guardada.get("posicion_seleccionada", {})
            instrucciones = alineacion_guardada.get("instrucciones", {})
            
    puede_enviar, mensaje_plazo, fecha_limite = False, _("No hay partido seleccionado"), None
    
    if partido:
        puede_enviar, mensaje_plazo, fecha_limite = verificar_plazo_alineacion(partido)
        
    return {
		"equipo": equipo,
		"partido": partido,
		"puede_enviar": puede_enviar,
		"mensaje_plazo": mensaje_plazo,
		"fecha_limite": fecha_limite,
		"plantilla": plantilla,
		"posiciones": posiciones,
        "tiene_alineacion_guardada": tiene_alineacion_guardada,
		"abev_pos": abrev_pos,
		"jugador_seleccionado": jugador_seleccionado,
		"posicion_seleccionada": posicion_seleccionada,
		"instrucciones_guardadas": mark_safe(json.dumps(instrucciones)),
		"fut_seleccionado": mark_safe(json.dumps(jugador_seleccionado)),
		"pos_seleccionada": mark_safe(json.dumps(posicion_seleccionada)),
		"selectores": [{"index": i, "jug_key": f"jug{i}"} for i in range(11)],
		"iteraciones": [{"index": i, "pos_key": f"pos{i}"} for i in range(11, 17)],
		"rango_minutos": range(1, 95),
		"rango_resultado": range(-5, 6),
		"rango_dorsales": range(1, 18),
		"rango_reservas": range(12, 18),
	}
        
def guardar_alineacion_equipo(equipo, partido, datos):
    """Valida el plazo y guarda la alineación en la BD y en el archivo json para el simulador"""
    puede_enviar, mensaje, _ = verificar_plazo_alineacion(partido)
    if not puede_enviar:
        raise ValueError(mensaje)
    
    # Guardar en la base de datos
    alineacion_obj = Alineacion.objects.update_or_create(equipo=equipo, partido=partido, defaults={"datos": datos})
        
    return alineacion_obj
