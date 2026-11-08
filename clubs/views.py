from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import F

from clubs.services import obtener_equipo_plantilla
from clubs.models import Estadio, Equipo

@login_required
def club(request):
    return render(request, 'clubs/club.html')

@login_required
def equipo(request):
    
    club, plantilla = obtener_equipo_plantilla(request.user)
    
    context = {
        'plantilla': plantilla,
        'club': club,
    }
    return render(request, 'clubs/equipo.html', context)

@login_required
def estadio(request):
    """Vista para mostrar el estadio del club."""
    try:
        estadio = request.user.estadio
    except Estadio.DoesNotExist:
        # Si el usuario no tiene estadio crear uno por defecto
        equipo = request.user.equipo
        estadio = Estadio.objects.create(
            user = request.user,
            equipo = equipo,
            nombre = _("Estadio Municipal"),
            precio = 30,
            capacidad = 5000
        )
    context = {'estadio': estadio,}
    return render(request, 'clubs/estadio.html', context)

@login_required
def editar_nombre_estadio(request):
    if request.method == "POST":
        nuevo_nombre = request.POST.get("nuevo_nombre")
        estadio = request.user.estadio
        if nuevo_nombre:
            estadio.nombre = nuevo_nombre
            estadio.save()
        return redirect('clubs:estadio')  # Asegúrate que este nombre de url sea correcto
    return redirect('clubs:estadio')
    
@login_required
def division(request):
    """Vista para mostrar la tabla de clasificacion para una division y grupo especificos."""
    division_id = request.user.equipo.division
    grupo_id = request.user.equipo.grupo
    equipos = Equipo.objects.filter(division=division_id, grupo=grupo_id)\
                        .annotate(diferencia_goles=F('goles_favor') - F('goles_contra'))\
                        .order_by('-puntos', '-diferencia_goles', '-goles_favor')
    context = {
      'equipos': equipos,
      'division': division_id,
      'grupo': grupo_id,
      'page_title': _("Tabla de clasificación") + f" - {division_id} - {grupo_id}"
    }

    return render(request, 'clubs/division.html', context)

@login_required
def alineacion(request):
    """Vista para mostrar la alineación del equipo."""
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
    
    # Crear un diccionario para buscar nombres por código fácilmente
    posiciones_map = {p['codigo']: p['nombre'] for p in posiciones}
    
    abrev_pos = [ "GK", "DFL", "DFR", "DFC", "DML", "DMR", "DMC", "MFL", "MFR", "MFC",
                  "AML", "AMR", "AMC", "FWL", "FWR", "FWC", 
                  ]
    
    plantilla = Futbolista.objects.filter(equipo=request.user.equipo).order_by('-st')
    nombre_usuario = request.user.username
    nombre_equipo = Equipo.objects.get(user=request.user)

    jugador_seleccionado = request.session.get("alineacion_jugadores", {})
    posicion_seleccionada = request.session.get('alineacion_posiciones', {})

    for i in range(17):
       key = f'jug{i}'
       player_name = request.GET.get(key)
       if player_name is not None:
          if player_name == "":
              jugador_seleccionado.pop(key, None)
          else:
            jugador_seleccionado[key] = player_name

    for i in range(17):
       key = f'pos{i}'
       posicion_elegida_codigo = request.GET.get(key)
       if posicion_elegida_codigo is not None:
          if posicion_elegida_codigo == "":
              posicion_seleccionada.pop(key, None)
          else:
              posicion_seleccionada[key] = posiciones_map.get(posicion_elegida_codigo, posicion_elegida_codigo)

    capitan_seleccionado = request.GET.get('capitan')
    if capitan_seleccionado is not None:
        if capitan_seleccionado == "":
            jugador_seleccionado.pop('capitan', None)
        else:
            jugador_seleccionado['capitan'] = capitan_seleccionado

    tirador_seleccionado = request.GET.get('penal')
    if tirador_seleccionado is not None:
        if tirador_seleccionado == "":
            jugador_seleccionado.pop('penal', None)
        else:
            jugador_seleccionado['penal'] = tirador_seleccionado
    
    if 'jug0' in jugador_seleccionado and jugador_seleccionado['jug0'] and 'pos0' not in posicion_seleccionada:
        posicion_seleccionada['pos0'] = posiciones_map.get('GK', _("Portero"))
            
    request.session["alineacion_jugadores"] = jugador_seleccionado
    request.session['alineacion_posiciones'] = posicion_seleccionada

    selectores = [{"index": i, "jug_key": f"jug{i}"} for i in range(11)]
    iteraciones = [{"index": i, "pos_key": f"pos{i}"} for i in range(11, 17)]
    rango_minutos = range(1, 95)
    rango_resultado = range(-5, 6)
    rango_dorsales = range(1,18)
    rango_reservas = range(12, 18)

    context = {'plantilla': plantilla, 'posiciones': posiciones,
                "jugador_seleccionado": jugador_seleccionado, 'posicion_seleccionada': posicion_seleccionada,
                'iteraciones': iteraciones, 'selectores': selectores, 'fut_seleccionado': mark_safe(json.dumps(jugador_seleccionado)),
                'pos_seleccionada': mark_safe(json.dumps(posicion_seleccionada)), 
                'nombre_usuario': nombre_usuario, 'nombre_equipo': nombre_equipo, 'abrev_pos': abrev_pos,
                'rango_dorsales': rango_dorsales, 'rango_minutos': rango_minutos, 'rango_resultado': rango_resultado,
                'rango_reservas': rango_reservas,  
                }
    return render(request, 'clubs/alineacion.html', context )
