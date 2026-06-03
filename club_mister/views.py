from django.shortcuts import render

# Create your views here.

def principal(request):
    # Renderiza la plantilla de inicio y la devuelve como http
    return render(request, 'club_mister/principal.html')