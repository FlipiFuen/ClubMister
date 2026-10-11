from django.shortcuts import render
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required

from .forms import GenerarCalendarioForm
from .services import generar_calendario_liga

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
            fecha_inicio = formulario.cleaned_data["fecha_inicio"].strftime("%d-%m_%Y")
            
            try:
                calendario = generar_calendario_liga(division, grupo, fecha_inicio)
                messages.success(request, f"Calendario para la División {division} - Grupo {grupo} generado correctamente")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, "OÇcurrió un error inesperado al generar el calendario")
    else:
        formulario = GenerarCalendarioForm()
            
    return render(request, "administracion/generar_calendario.html", {"form": formulario, "calendario": calendario})
    
    
    
