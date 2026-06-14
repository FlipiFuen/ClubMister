from django.urls import path, include
from . import views

app_name = 'club_mister'

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', views.principal, name='principal'),
]
