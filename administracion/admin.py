from django.contrib import admin

from administracion.models import Arbitro, SolicitudAmistoso

@admin.register(Arbitro)
class ArbitroAdmin(admin.ModelAdmin):
    
    list_display =("nombre", "severidad", "origen", "activo")
    list_filter = ("activo", "origen")
    search_fields = ("nombre",)

@admin.register(SolicitudAmistoso)
class SolicitudAmistoso(admin.ModelAdmin):
    
    list_display =("equipo_origen", "equipo_destino", "tipo", "estado", "fecha_partido", "hora_partido", "creado_en")
    list_filter = ("tipo", "estado", "fecha_partido")