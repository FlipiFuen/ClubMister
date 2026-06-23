from django.contrib import admin
from clubs.models import Equipo, Futbolista

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    # Columnas visibles
    list_display = "user", "nombre_equipo", "abreviatura", "division", "grupo", "temporada", "partidos_jugados", "victorias", "empates", "derrotas", "goles_favor", "goles_contra", "puntos", "posicion"

    # Campos de busqueda
    search_fields = "nombre_equipo", "abreviatura", "user", "temporada"
    
    # Filtros laterales
    list_filter = "division", "grupo", "temporada"
    
@admin.register(Futbolista)
class FutbolistaAdmin(admin.ModelAdmin):
    # Columnas visibles
    list_display = "equipo", "nombre", "nacionalidad", "edad", "lado_preferido", "posicion", "st", "tk", "ps", "sh", "resistencia", "agresividad", "st_hab", "tk_hab", "ps_hab", "sh_hab", "partidos", "paradas", "takling", "asistencias"
    
    # Campos de busqueda
    search_fields = "nombre", "equipo", "posicion", "edad"
    
    # Filtros laterales
    list_filter = "equipo", "posicion", "edad"
    

