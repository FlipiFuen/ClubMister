from django.db import DatabaseError
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login, logout
from django.contrib.auth.forms import PasswordChangeForm

from clubs.models import Equipo, Futbolista
from clubs.plantilla import Plantilla
from .formulario import FormularioCambiarEmail

def asignar_division_grupo():
    """
    Asigna la división y el grupo al nuevo equipo.
    
    Returns:
        tuple: (int: division, int: grupo)
    """
    
    # Obtenemos el último equipo registrado
    ultimo_equipo = Equipo.objects.order_by('-division','-grupo','-id').first()

    # Si no hay equipos asignamos división 1 y grupo 1
    if ultimo_equipo is None:
        return 1, 1
    
    # Obtenemos la división y el grupo del último equipo
    division = ultimo_equipo.division
    grupo = ultimo_equipo.grupo

    # Comprobamos si el grupo ya tiene 8 equipos
    equipos_grupo = Equipo.objects.filter(division=division, grupo=grupo).count()
    if equipos_grupo >= 8:
        grupo += 1

    # Si la división ya tiene 8 grupos aumentamos la división y asignamos el grupo 1
    if grupo > 8:
        division += 1
        grupo = 1

    return division, grupo

def crear_equipo_inicial(usuario, nombre_equipo, abreviatura):
    
    # Generamos el equipo asociado al nuevo usuario
    plantilla = Plantilla()
    futbolistas = plantilla.crear_equipo()
    
    # Asignamos la división y el grupo
    division, grupo = asignar_division_grupo()
    
    # Creamos el equipo y lo asignamso al usuario
    equipo = Equipo.objects.create(
        user=usuario, 
        nombre_equipo = nombre_equipo,
        abreviatura = abreviatura, 
        division = division, 
        grupo = grupo,
        temporada = 1
    )
    
    # Asignamos los futbolistas al equipo
    Futbolista.objects.bulk_create([
        Futbolista(
            equipo = equipo,
            nombre = futbolista['nombre'],
            nacionalidad = futbolista['nacionalidad'],
            edad = futbolista['edad'],
            lado_preferido = futbolista['lado_preferido'],
            posicion = futbolista['posicion'],
            st = futbolista['habilidades']['st'],
            tk = futbolista['habilidades']['tk'],
            ps = futbolista['habilidades']['ps'],
            sh=futbolista['habilidades']['sh'],
            resistencia=futbolista['resistencia'],
            agresividad=futbolista['agresividad'],
            st_hab=futbolista['st_hab'],
            tk_hab=futbolista['tk_hab'],
            ps_hab=futbolista['ps_hab'],
            sh_hab=futbolista['sh_hab'],
            partidos=futbolista['partidos'],
            paradas=futbolista['paradas'],
            takling=futbolista['takling'],
            asistencias=futbolista['asistencias'],
            tiros=futbolista['tiros'],
            goles=futbolista['goles'],
            disciplina=futbolista['disciplina'],
            lesion=futbolista['lesion'],
            suspension=futbolista['suspension'],
            adaptacion=futbolista['adaptacion'],
            pases_buenos=futbolista['pases_buenos'],
            )
           for futbolista in futbolistas
        ])
    
    return equipo

def cambiar_email(request):
    """Procesa el formulario de cambio de email.

    Args:
        request: El objeto HttpRequest que contiene los datos del POST.

    Returns:
        True si el formulario es válido y el email se ha guardado.
        El objeto de formulario con errores si la validación falla.
    """
    form_email = FormularioCambiarEmail(request.POST, instance=request.user)
    if form_email.is_valid():
        form_email.save()
        messages.success(request, "Tu correo ha sido actualizado correctamente")
        return True
    
    return form_email

def cambiar_password(request):
    """Procesa el formulario de cambio de contraseña.

    Args:
        request: El objeto HttpRequest que contiene los datos del POST.

    Returns:
        True si el formulario es válido y la contraseña se ha cambiado.
        El objeto de formulario con errores si la validación falla.
    """
    form_password = PasswordChangeForm(user=request.user, data=request.POST)
    if form_password.is_valid():
        user = form_password.save()
        update_session_auth_hash(request, user) # Mantiene la sesión iniciada
        messages.success(request, "Tu contraseña ha sido actualizada con éxito")
        return True
    
    return form_password

def borrar_cuenta(request):
    """Procesa la eliminación de la cuenta de un usuario.

    Verifica la contraseña proporcionada. Si es correcta, cierra la sesión
    del usuario y elimina su cuenta de la base de datos.

    Args:
        request: El objeto HttpRequest.

    Returns:
        True si la cuenta fue eliminada, False si la contraseña es incorrecta.
    """
    password = request.POST.get("password")
    usuario = request.user
    
    if not usuario.check_password(password):
        messages.error(request, "La contraseña es incorrecta. No se ha podido eliminar la cuenta")
        return False
    
    logout(request)
    usuario.delete()
    messages.success(request, "Tu cuenta ha sido eliminada permanentemente con éxito")
    return True

def procesar_ajustes_cuenta(request):
    """Procesa los ajustes de la cuenta del usuario, incluyendo cambio de email, cambio de contraseña y eliminación de la cuenta.
    
    Args:
        request: El objeto HttpRequest que contiene los datos del POST.
        
    Returns:
        dict: Un diccionario con el resultado del procesamiento.
    """
    form_email = FormularioCambiarEmail(instance=request.user)
    form_password = PasswordChangeForm(user=request.user)
    
    if request.method != "POST":
        return {"redirect": None, "form_email": form_email, "form_password": form_password}
    
    accion = request.POST.get("accion")
    
    try:
        # Cambiar email
        if accion == "actualizar_email":
            resultado = cambiar_email(request)
            if resultado is True:
                return {"redirect": "flipigames:ajustes_cuenta"}
            return {"redirect": None, "form_email": resultado, "form_password": form_password}
                        
        # Cambiar contraseña
        elif accion == "actualizar_password":
            resultado = cambiar_password(request)
            if resultado is True:
                return {"redirect": "flipigames:ajustes_cuenta"}
            return {"redirect": None, "form_email": form_email, "form_password": resultado}
        
        # Darse de baja
        elif accion == "borrar_cuenta":
            if borrar_cuenta(request):
                return {"redirect": "flipigames:home"}
            return {"redirect": "flipigames:ajustes_cuenta", "form_email": form_email, "form_password": form_password}
        
    except DatabaseError:
        messages.error(request, "Ha ocurrido un error con la base de datos. Inténtalo de nuevo")
    
    return {"redirect": None, "form_email": form_email, "form_password": form_password}