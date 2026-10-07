from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from clubs.services import obtener_equipo_plantilla

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
    

