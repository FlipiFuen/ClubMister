from django.db import models

from clubs.models import Equipo

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
