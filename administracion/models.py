from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from clubs.models import Equipo, Futbolista

class Arbitro(models.Model):
    
    nombre = models.CharField(max_length=100, unique=True)
    severidad = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="1 (muy permisivo) a 20 (muy estricto)",
    )
    origen = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["nombre"]
        
    def __str__(self):
        return f"{self.nombre} ({self.origen})"
    
class PartidoProgramado(models.Model):
    division = models.PositiveBigIntegerField()
    grupo = models.PositiveBigIntegerField()
    temporada = models.PositiveBigIntegerField()
    jornada = models.PositiveBigIntegerField()
    equipo_local = models.ForeignKey(
        Equipo, on_delete=models.CASCADE, related_name="partidos_locales_programados",
    )
    equipo_visitante = models.ForeignKey(
        Equipo, on_delete=models.CASCADE, related_name="partidos_visitantes_programados",
    )
    fecha = models.DateField()
    hora = models.TimeField()
    arbitro = models.ForeignKey(
        Arbitro,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="partidos_programados",
    )
    
    class Meta:
        ordering = ["jornada", "fecha", "hora"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "temporada",
                    "division",
                    "grupo",
                    "jornada",
                    "equipo_local",
                    "equipo_visitante",
                ],
                name="partido_programado_unico",
            ),
        ]
        
    def __str__(self):
        return(
            f"Jornada {self.jornada}: {self.equipo_local} vs "
            f"{self.equipo_visitante}"
        )
        
class CalendarioTemporada(models.Model):
    """Registra el HTML generado con el calendario de una temporada, división y grupo"""
    division = models.PositiveBigIntegerField()
    grupo = models.PositiveBigIntegerField()
    temporada = models.PositiveBigIntegerField()
    ruta_archivo = models.CharField(max_length=500, unique=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            # Sólo puede existir un calendario por temporada, división y grupo
            models.UniqueConstraint(
                fields=["temporada", "division", "grupo"],
                name="calendario_temporada_unico",
            )
        ]
        
    def __str__(self):
        return (
            f"Calendario temporada {self.temporada} - "
            f"División {self.division} - Grupo {self.grupo}"
        )

class ReportePartido(models.Model):
    class Competicion(models.TextChoices):
        LIGA = "liga", "Liga"
        AMISTOSO = "amistoso", "Amistoso"
        INDEPENDIENTE = "independiente", "Independiente"
        COPA = "copa", "Copa"
    
    partido_programado = models.OneToOneField(
        PartidoProgramado,
        on_delete=models.SET_NULL,
        related_name="reporte",
        null=True,
        blank=True,
    )   
    equipo_local = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="reportes_locales")
    equipo_visitante = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="reportes_visitantes")
    division = models.PositiveBigIntegerField()
    grupo = models.PositiveBigIntegerField()
    temporada = models.PositiveBigIntegerField()
    fecha = models.DateField()
    hora = models.TimeField()
    competicion = models.CharField(max_length=20, choices=Competicion.choices)
    es_oficial = models.BooleanField()
    arbitro = models.ForeignKey(
        Arbitro,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reportes"
    )
    goles_local = models.PositiveSmallIntegerField()
    goles_visitante = models.PositiveSmallIntegerField()
    ruta_archivo = models.CharField(max_length=500, unique=True)
    
    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante} ({self.fecha})"

class EstadisticaJugadorPartido(models.Model):
    reporte = models.ForeignKey(
        ReportePartido,
        on_delete=models.CASCADE,
        related_name="estadisticas_jugadores",
    )
    futbolista = models.ForeignKey(
        Futbolista,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estadisticas_por_partido",
    )
    nombre_jugador = models.CharField(max_length=100)
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estadisticas_en_partidos",
    )
    nombre_equipo = models.CharField(max_length=100)
    minutos_jugados = models.PositiveSmallIntegerField(default=0)
    goles = models.PositiveSmallIntegerField(default=0)
    goles_en_propia = models.PositiveSmallIntegerField(default=0)
    asistencias = models.PositiveSmallIntegerField(default=0)
    tarjetas_amarillas = models.PositiveSmallIntegerField(default=0)
    tarjetas_rojas = models.PositiveSmallIntegerField(default=0)
    tiros_a_puerta = models.PositiveSmallIntegerField(default=0)
    tiros_fuera = models.PositiveSmallIntegerField(default=0)
    pases_completados = models.PositiveSmallIntegerField(default=0)
    intercepciones = models.PositiveSmallIntegerField(default=0)
    paradas = models.PositiveSmallIntegerField(default=0)
    goles_concedidos = models.PositiveSmallIntegerField(default=0)
    lesionado = models.BooleanField(default=False)
    semanas_lesionado = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporte", "futbolista"],
                name="estadistica_jugador_partido_unica",
            ),
        ]
        
    def __str__(self):
        return f"{self.nombre_jugador} - {self.reporte}"
    

    