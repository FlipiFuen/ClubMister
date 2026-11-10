import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import F

from clubs.services import (
    obtener_equipo_plantilla,
    obtener_proximo_partido,
    obtener_contexto_alineacion,
    guardar_alineacion_equipo,
    )
from clubs.models import Estadio, Equipo
from administracion.models import PartidoProgramado

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
def alineacion(request, partido_id=None):
    """
    Vista para renderizar la página de alineación.
    Si recibe partido_id, carga ese partido específico, de lo contrario busca el próximo partido del equipo
    """
    try:
        equipo = request.user.equipo
    except Equipo.DoesNotExist:
        return redirect("clubs:club")
    
    if partido_id:
        partido = get_object_or_404(PartidoProgramado, id=partido_id)
        
        # Comprobamos que el equipo del usuario participa en este partido
        if partido.equipo_local != equipo and partido.equipo_visitante != equipo:
            return HttpResponseForbidden(_("No tienes permiso para alinear en este partido"))
    else:
        partido = obtener_proximo_partido(equipo)
            
    # Obtenemos el contexto
    contexto = obtener_contexto_alineacion(equipo, partido)
    contexto["nombre_usuario"] = request.user.username
    contexto["nombre_equipo"] = equipo.nombre_equipo
            

    return render(request, 'clubs/alineacion.html', contexto)

@login_required
def guardar_alineacion(request):
    """
    Recibe los datos de la alineación en formato JSON, valida el plazo de 15 minutos y guarda en la BD y en el archivo
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "mensaje": _("Método no permitido")}, status=405)
    
    try:
        equipo = request.user.equipo
        datos = json.loads(request.body)
        partido_id = datos.get(partido_id)
        
        if partido_id:
            partido = get_object_or_404(PartidoProgramado, id=partido_id)
        else:
            partido = obtener_proximo_partido(equipo)
            
        if not partido:
            return JsonResponse({"status": "error", "mensaje": _("No hay ningún partido activo para alinear")}, status=400)
        
        if partido.equipo_local != equipo and partido.equipo_visitante != equipo:
            return JsonResponse({"status": "error", "mensaje": _("No perteneces a este partido")}, status=403)
        
        guardar_alineacion_equipo(equipo, partido, datos)
        
        return JsonResponse({"status": "ok", "mensaje": _("Alineación guardada con éxito")})
    except ValueError as e:
        # Error cuando epiro el plazo de 15 minutos
        return JsonResponse({"status": "error", "mensaje": _("Error al procesar la alineación: ") + str(e)}, status=500)
    
