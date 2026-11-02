from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    path('gestion/', views.gestion, name='gestion'),
    path('generar_calendario/', views.generar_calendario, name="generar_calendario"),
    path('simular_partidos/', views.simular_partidos, name="simular_partidos"),
    path('reporte/<int:reporte_id>/', views.ver_reporte, name="ver_reporte"),
]
