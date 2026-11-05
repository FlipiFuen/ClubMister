import os

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404

from clubs.models import Equipo

from .models import CalendarioTemporada, ReportePartido
from .forms import GenerarCalendarioForm, SimularPartidosForm
from .services import (
    calendario_desde_bd, generar_calendario_liga, simular_individual, simular_jornada,
    )
from .Partidos.constantes import PARTIDOS_DIR

@staff_member_required
def gestion(request):
    
    context = {"titulo": "Gestión del sitio"}
    
    return render(request, "administracion/gestion.html", context)

@staff_member_required
def generar_calendario(request):
    
    calendario = None
    
    if request.method =="POST":
        formulario = GenerarCalendarioForm(request.POST)
        if formulario.is_valid():
            division = formulario.cleaned_data["division"]
            grupo = formulario.cleaned_data["grupo"]
            fecha_inicio = formulario.cleaned_data["fecha_inicio"].strftime("%d-%m-%Y")
            
            try:
                calendario = generar_calendario_liga(division, grupo, fecha_inicio)
                messages.success(request, f"Calendario para la División {division} - Grupo {grupo} generado correctamente")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, "Ocurrió un error inesperado al generar el calendario")
    else:
        formulario = GenerarCalendarioForm()
            
    return render(request, "administracion/generar_calendario.html", {"form": formulario, "calendario": calendario})
    
@staff_member_required
def simular_partidos(request):
    
    resultados = None
    reporte = None
    
    if request.method == "POST":
        formulario = SimularPartidosForm(request.POST)
        if formulario.is_valid():
            datos = formulario.cleaned_data
            oficial = datos["tipo"] == "oficial"
            try:
                if datos["modo"] == "jornada":
                    resultados = simular_jornada(datos["division"], datos["grupo"], datos["jornada"])
                    messages.success(request, "Jornada procesada")
                else:
                    reporte = simular_individual(
                        datos["equipo_local"], datos["equipo_visitante"], oficial,
                        datos.get("fecha_amistoso"), datos.get("hora_amistoso"),
                    )
                    messages.success(request, "Partido simulado correctamente")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error inesperado al simular: {e}")
    else:
        formulario = SimularPartidosForm()
            
    return render(request, "administracion/simular_partidos.html", {
        "form": formulario, "resultados": resultados, "reporte": reporte,
    }) 
    
def usuario_puede_ver_reporte(usuario, reporte):
    """Indica si el usuario tiene permiso para ver el reporte de un partido
    
    Pueden verlo el staff, los propietarios de los dos equipos y, sólo en partidos de Liga,
    los equipos de la misma división y grupo
    """
    if usuario.is_staff:
        return True
    if usuario in (reporte.equipo_local.user, reporte.equipo_visitante.user):
        return True
    if reporte.competicion == ReportePartido.Competicion.LIGA:
        return Equipo.objects.filter(
            user=usuario, division=reporte.division, grupo=reporte.grupo
        ).exists()
    return False

@login_required
def ver_reporte(request, reporte_id):
    """Sirve el HTML de un reporte guardado si el usuario tiene permiso"""
    reporte = get_object_or_404(
        ReportePartido.objects.select_related("equipo_local__user", "equipo_visitante__user"),
        pk=reporte_id,
    )
    if not usuario_puede_ver_reporte(request.user, reporte):
        raise Http404("Reporte no disponible")
    
    # Evita salir de la carpeta de partido con una ruta manipulada
    ruta = os.path.realpath(reporte.ruta_archivo)
    base = os.path.realpath(PARTIDOS_DIR)
    if os.path.commonpath([ruta, base]) != base or not os.path.isfile(ruta):
        raise Http404("Archivo de reporte no encontrado")
    
    return FileResponse(open(ruta, "rb"), content_type="text/html; charset=utf-8")

def usuario_puede_ver_calendario(usuario, calendario):
    """
    Indica si el usuario tiene permiso para ver el calendario de una división y grupo
    Puede verlo el staff y los usuarios con un equipo en esa misma división y grupo
    """
    if usuario.is_staff:
        return True
    return Equipo.objects.filter(
        user=usuario, division=calendario.division, grupo=calendario.grupo
    ).exists()
    
@login_required
def ver_calendario(request, calendario_id):
    """Muestra el calendario de una temporada si el usuario pertenece a su división y grupo"""
    calendario = get_object_or_404(CalendarioTemporada, pk=calendario_id)
    # Se responde 404 y no 403 para no revelar que el calendario existe
    if not usuario_puede_ver_calendario(request.user, calendario):
        raise Http404("Calendario no disponible")
    
    return render(request, "clubs/calendario_temporada.html", {
        "division": calendario.division,
        "grupo": calendario.grupo,
        "temporada": calendario.temporada,
        "calendario": calendario_desde_bd(
            calendario.temporada, calendario.division, calendario.grupo
        ),
    })
    
@login_required
def mi_calendario(request):
    """Redirige al calendario de la temporada actual de la división y grupo del usuario"""
    equipo = getattr(request.user, "equipo", None)
    if equipo is None:
        raise Http404("El usuario no tiene equipo")
    
    calendario = CalendarioTemporada.objects.filter(
        temporada=equipo.temporada, division=equipo.division, grupo=equipo.grupo,
    ).first()
    if calendario is None:
        messages.info(request, "Todavía no se ha generado el calendario de tu división y grupo")
        return redirect("clubs:division")
    
    return redirect("administracion:ver_calendario", calendario_id=calendario.id)