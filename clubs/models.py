from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Equipo(models.Model):
    """Modelo para registar equipos."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_equipo = models.CharField(max_length=100, unique=True)
    abreviatura = models.CharField(max_length=3)
    division = models.PositiveIntegerField(default=1)
    grupo = models.PositiveIntegerField(default=1)
    temporada = models.PositiveIntegerField()
    partidos_jugados = models.IntegerField(default=0)
    victorias = models.IntegerField(default=0)
    empates = models.IntegerField(default=0)
    derrotas = models.IntegerField(default=0)
    goles_favor = models.IntegerField(default=0)
    goles_contra = models.IntegerField(default=0)
    puntos = models.IntegerField(default=0)
    posicion = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre_equipo
    
class Futbolista(models.Model):
    """Modelo para registrar futbolistas."""
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='futbolistas')
    nombre = models.CharField(max_length=100)
    nacionalidad = models.CharField(max_length=10)
    edad = models.IntegerField()
    lado_preferido = models.CharField(max_length=5)
    posicion = models.CharField(max_length=5)
    st = models.IntegerField()
    tk = models.IntegerField()
    ps = models.IntegerField()
    sh = models.IntegerField()
    resistencia = models.IntegerField()
    agresividad = models.IntegerField()
    st_hab = models.IntegerField()
    tk_hab = models.IntegerField()
    ps_hab = models.IntegerField()
    sh_hab = models.IntegerField()
    partidos = models.IntegerField(default=0)
    paradas = models.IntegerField(default=0)
    takling = models.IntegerField(default=0)
    asistencias = models.IntegerField(default=0)
    tiros = models.IntegerField(default=0)
    goles = models.IntegerField(default=0)
    disciplina = models.IntegerField(default=0)
    lesion = models.IntegerField(default=0)
    suspension = models.IntegerField(default=0)
    adaptacion = models.IntegerField(default=0)
    pases_buenos = models.IntegerField(default=0)
    participo_ultimo_partido = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nombre
