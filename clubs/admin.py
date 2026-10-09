from django.contrib import admin

from .models import Equipo, Estadio, Futbolista

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre_equipo', 'user')
    search_fields = ('nombre_equipo', 'abreviatura')
    list_filter = ('nombre_equipo', 'abreviatura')

@admin.register(Estadio)
class EstadioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'capacidad')
    search_fields = ('nombre', 'equipo')
    list_filter = ('nombre', 'equipo')

@admin.register(Futbolista)
class FutbolistaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'equipo', 'posicion')
    search_fields = ('nombre', 'equipo')
    list_filter = ('posicion',)
