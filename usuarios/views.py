from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm

# Create your views here.

def registro(request):
    # Si envía un formulario procesamos los datos
    if request.method == 'POST':
        formulario = UserCreationForm(request.POST)
        
        if formulario.is_valid():
            formulario.save() # Guardamos el usuario
            return redirect('usuarios:login')
        
    else:
        formulario = UserCreationForm()
        
    return render(request, 'usuarios/registro.html', {'formulario': formulario})
