from django.urls import path
from . import views

app_name = 'club_mister'

urlpatterns = [
    path('', views.principal, name='principal')
]
