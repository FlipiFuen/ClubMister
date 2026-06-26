from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .formulario import RegistroForm
from clubs.plantilla import Plantilla
from clubs.models import Equipo, Futbolista 

# Create your views here.

def asignar_division_grupo():
    """
    Asigna la división y el grupo al nuevo equipo.
    
    Returns:
        tuple: (int: division, int: grupo)
    """
    
    # Obtenemos el último equipo registrado
    ultimo_equipo = Equipo.objects.order_by('-id').first()

    # Si no hay equipos asignamos división 1 y grupo 1
    if not ultimo_equipo:
        return 1, 1
    
    # Obtenemos la división y el grupo del último equipo
    division = ultimo_equipo.division
    grupo = ultimo_equipo.grupo

    # Comprobamos si el grupo ya tiene 8 equipos
    equipos_grupo = Equipo.objects.filter(division=division, grupo=grupo).count()
    if equipos_grupo == 8:
        grupo += 1

    # Si la división ya tiene 8 grupos aumentamos la división y asignamos el grupo 1
    grupos_division = Equipo.objects.filter(division=division).count()
    if grupos_division == 8:
        division += 1
        grupo = 1

    return division, grupo


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
            usuario = formulario.save()

            # Generamos el equipo asociado al nuevo usuario
            plantilla = Plantilla()
            futbolistas = plantilla.crear_equipo()

            # Asignamos la división y el grupo
            division, grupo = asignar_division_grupo()

            # Creamos el equipo y lo asignamso al usuario
            equipo = Equipo(
                user=usuario, 
                nombre_equipo=formulario.cleaned_data['nombre_equipo'],
                abreviatura=formulario.cleaned_data['abreviatura'], 
                division=division, 
                grupo=grupo,
                temporada = 1
            )
            equipo.save()

            # Asignamos los futbolistas al equipo
            for futbolista in futbolistas:
                Futbolista.objects.create(
                    equipo=equipo,
                    nombre=futbolista['nombre'],
                    nacionalidad=futbolista['nacionalidad'],
                    edad=futbolista['edad'],
                    lado_preferido=futbolista['lado_preferido'],
                    posicion=futbolista['posicion'],
                    st=futbolista['habilidades']['st'],
                    tk=futbolista['habilidades']['tk'],
                    ps=futbolista['habilidades']['ps'],
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
            
            # Autenticamos al usuario y redirigimos a la página principal
            login(request, usuario)
            return redirect('club_mister:principal')
        
    return render(request, 'usuarios/registro.html', {'formulario': formulario})
