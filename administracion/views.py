from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def gestion(request):
    
    context = {"titulo": "Gestión del sitio"}
    
    return render(request, "administracion/gestion.html", context)
