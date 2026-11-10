from django.urls import path, include
from . import views

app_name = 'clubs'

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', views.club, name='club'),
    path('equipo/', views.equipo, name='equipo'),
    path('estadio/', views.estadio, name='estadio'),
    path('estadio/editar-nombre/', views.editar_nombre_estadio, name='editar_nombre_estadio'),
    path('division/', views.division, name="division"),
    path('alineacion/', views.alineacion, name="alineacion"),
    path('alineacion/<int:partido_id>', views.alineacion, name="alineacion_partido"),
    path('alineacion/guardar/', views.guardar_alineacion, name="guardar_alineacion"),
]