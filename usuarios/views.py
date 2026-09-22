from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.db import transaction

from .formulario import RegistroForm
from .services import crear_equipo_inicial

def registro(request):
    """ 
    Muestra el formulario de registro y procesa el registro del usuario 

    Requests:
        GET: Muestra el formulario de registro
        POST: Procesa el formulario de registro
        
    Returns:
        render: Renderiza el template registro.html o redirige a la página de inicio si el registro es exitoso
    """
    
    if request.method != "POST":
        # Si no envía el formulario muestra uno vacío
        formulario = RegistroForm()
    else:
        # Si se envía el formulario procesamos los datos
        formulario = RegistroForm(data=request.POST)

        if formulario.is_valid():
            # Guardamos el usuario
            with transaction.atomic():
                usuario = formulario.save()  
                crear_equipo_inicial(
                    usuario = usuario,
                    nombre_equipo = formulario.cleaned_data["nombre_equipo"],
                    abreviatura = formulario.cleaned_data["abreviatura"],
                )
            
            # Autenticamos al usuario y redirigimos a la página principal
            login(request, usuario)
            return redirect('club_mister:principal')
        
    return render(request, 'usuarios/registro.html', {'formulario': formulario})
