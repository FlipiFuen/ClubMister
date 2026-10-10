from django.urls import path

from . import views

app_name = "administracion"

urlpatterns = [
    path('gestion/', views.gestion, name='gestion'),
]
