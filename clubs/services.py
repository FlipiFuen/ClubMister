from django.utils.translation import gettext_lazy as _ 

from clubs.models import Equipo, Futbolista

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
    if valor == 'D':
        mola = _("DERECHA")
    elif valor == 'I':
      mola = _("IZQUIERDA")
    elif valor == 'C':
      mola = _("CENTRO")
    elif valor == 'D-I':
      mola = _("IZQUIERDA-DERECHA")
    elif valor == 'D-C':
      mola = _("CENTRO-DERECHA")
    elif valor == 'I-C':
      mola = _("IZQUIERDA-CENTRO")
    elif valor == 'D-L-C':
      mola = _("IZQUIERDA-CENTRO-DERECHA")
    elif valor == 'D-I-C':
      mola = _("IZQUIERDA-CENTRO-DERECHA")

    return mola

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
