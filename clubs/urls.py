from django.urls import path, include
from . import views

app_name = 'clubs'

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', views.club, name='club'),
    path('equipo/', views.equipo, name='equipo'),
]