from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages 
from django.contrib.auth.decorators import login_required 
from django.contrib.auth.forms import PasswordChangeForm
from django.db import DatabaseError, transaction

from . import services
from .forms import FormularioCambiarEmail, FormularioRegistroUsuario

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

@login_required    
def ajustes_cuenta(request):
    """Gestiona los ajustes de la cuenta del usuario, incluyendo cambio de email,
    cambio de contraseña y eliminación de la cuenta
    
    Args:
        request: El objeto HttpRequest.
        
        Returns:
            Un HttpResponse que redirige a la página de perfil tras una acción exitosa,
            o que renderiza la plantilla de ajustes con los formularios correspondientes.
    """
    form_email = FormularioCambiarEmail(instance=request.user)
    form_password = PasswordChangeForm(user=request.user)
    
    # Si la petición no es POST, simplemente renderizamos los formularios con los datos actuales.
    if request.method == "POST":
        try:
            respuesta = services.procesar_ajustes_cuenta(request)
            
            if respuesta.get("redirect"):
                return redirect(respuesta["redirect"])
            
            form_email = respuesta.get("form_email", form_email)
            form_password = respuesta.get("form_password", form_password)
        except DatabaseError:
            messages.error(request, "Ha ocurrido un error en la base de datos. Inténtalo de nuevo")
    
    # Si la petición no es POST, simplemente renderizamos los formularios con los datos actuales.
    contexto = {
        "form_email": form_email,
        "form_password": form_password,
    }
    
    return render(request, "flipigames/ajustes_cuenta.html", contexto)