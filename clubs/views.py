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
