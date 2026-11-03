from django.contrib import admin

from administracion.models import Arbitro

@admin.register(Arbitro)
class ArbitroAdmin(admin.ModelAdmin):
    
    list_display =("nombre", "severidad", "origen", "activo")
    list_filter = ("activo", "origen")
    search_fields = ("nombre",)
