import pytest

from datetime import datetime, timedelta, time, date
from django.contrib.auth.models import User

from administracion.services import generar_calendario_liga, generar_arbitros, elegir_arbitros, asignar_arbitro, _simular
from administracion.models import Arbitro, PartidoProgramado
from clubs.models import Equipo

@pytest.mark.django_db
class TestGenerarCalendarioLigaNormales:
    """Casos Normales"""
    def test_generar_calendario_devuelve_lista_correcta(self, bd_equipos_validos):
        """Verifica que la función devuelve una lista de jornadas y que cada partido sea un diccionario con las claves requeridas"""
        division = bd_equipos_validos["division"]
        grupo = bd_equipos_validos["grupo"]
        fecha_inicio = bd_equipos_validos["fecha_inicio_valida"]
        
        resultado = generar_calendario_liga(division, grupo, fecha_inicio)
        
        assert isinstance(resultado, list)
        assert  len(resultado) == 14
        primera_jornada = resultado[0]
        assert isinstance(primera_jornada, list)
        assert len(primera_jornada) == 4
        partido = primera_jornada[0]
        assert isinstance(partido, dict)
        claves_esperadas = {"jornada", "local", "visitante", "fecha", "hora"}
        assert claves_esperadas.issubset(partido.keys())
        assert partido["jornada"] == 1
        assert partido["hora"] == "20:00"
        
    def test_calendario_incremento_correcto_fechas(self, bd_equipos_validos):
        """Comprueba que cada jornada consecutiva tenga exactamente 7 dias de diferencia"""
        resultado = generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            bd_equipos_validos["fecha_inicio_valida"]
        )
        fecha_jornada_1 = datetime.strptime(resultado[0][0]["fecha"], "%d-%m-%Y")
        fecha_jornada_2 = datetime.strptime(resultado[1][0]["fecha"], "%d-%m-%Y")
        
        assert fecha_jornada_2 - fecha_jornada_1 == timedelta(days=7)
        
    def test_generar_calendario_segunda_vuelta_cambia_local(self, bd_equipos_validos):
        """Verifica que la segunda vuelta (jornada 8) sea el reflejo invertido de la primera (jornada 1)"""
        resultado = generar_calendario_liga(
                    bd_equipos_validos["division"],
                    bd_equipos_validos["grupo"],
                    bd_equipos_validos["fecha_inicio_valida"]
                )
        jornada_1 = resultado[0]
        jornada_8 = resultado[7]
        
        for partido_j1, partido_j8 in zip(jornada_1, jornada_8):
            assert partido_j1["local"] == partido_j8["visitante"]
            assert partido_j1["visitante"] == partido_j8["local"]
            
    def test_calendario_asigna_arbitros_sin_repetir_en_jornada(self, bd_equipos_validos):
        
        generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            bd_equipos_validos["fecha_inicio_valida"],
        )
        
        assert not PartidoProgramado.objects.filter(arbitro__isnull=True).exists()
        for jornada in range(1, 15):
            ids = list(PartidoProgramado.objects.filter(jornada=jornada).values_list("arbitro", flat=True))
            assert len(ids) == len(set(ids))
            
@pytest.mark.django_db
class TestGenerarCalendarioLigaEdgeCases:
    """Casos Límite"""
    
    def test_generar_calendario_con_numero_minimo_equipos(self, db, bd_arbitros):
        """Mínimo de equipos permmitidos para jugar una liga (2)"""
        user_a = User.objects.create_user(username="user_A", password="Password123")
        user_b = User.objects.create_user(username="user_B", password="Password123")
        Equipo.objects.create(user=user_a, nombre_equipo="Equipo A", abreviatura="EAE", division=3, grupo=1, temporada=1)
        Equipo.objects.create(user=user_b, nombre_equipo="Equipo B", abreviatura="BAB", division=3, grupo=1, temporada=1)
        
        resultado = generar_calendario_liga(division="3", grupo=1, fecha_inicio_str="10-10-2026")
        
        assert len(resultado) == 14
        assert len(resultado[0]) == 1
        assert resultado[0][0]["local"] in ["Equipo A", "Equipo B"]
        
    def test_generar_calendario_transicion_de_año(self, bd_equipos_validos):
        """Fecha de inicio a final de año para verificar el cambio de año correcto en las fechas posteriores"""
        fecha_fin_anho = "31-12-2026"
        resultado = generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            fecha_fin_anho
        )
        
        assert resultado[0][0]["fecha"] == "31-12-2026"
        assert resultado[1][0]["fecha"] == "07-01-2027"
        
@pytest.mark.django_db
class TestGenerarCalendarioLigaExcepciones:
    """Gestión de errores y excepciones"""
    
    def test_sin_equipos_lanza_valueerror(self, db, bd_arbitros):
        """Comprueba que si no existen equipos en la división/grupo se lance ValueError"""
        division_inexistente = "99"
        grupo_inexistente ="99"
        mensaje_esperado = f"No hay equipos registrados en la Division {division_inexistente} - grupo {grupo_inexistente}"
        
        with pytest.raises(ValueError, match=mensaje_esperado) as exec_info:
            generar_calendario_liga(division_inexistente, grupo_inexistente, "15-10-2026")
            
        assert str(exec_info.value) == mensaje_esperado
        
    def test_formato_fecha_invalida_lanza_valueerror(self, bd_equipos_validos, fechas_invalidas):
        """Verifica que las fechas inválidas lanzan ValueError"""
        mensaje_esperado = "El formato de fecha de inicio no es válido. Debe ser: DD-MM-YYYY"
        
        for fecha_erronea in fechas_invalidas:
            with pytest.raises(ValueError, match=mensaje_esperado):
                generar_calendario_liga(
                    bd_equipos_validos["division"],
                    bd_equipos_validos["grupo"],
                    fecha_erronea
                )
                
    def test_sin_arbitros_lanza_valueerror(self, bd_equipos_validos):
        
        Arbitro.objects.all().delete()
        with pytest.raises(ValueError, match="No hay árbitros activos"):
            generar_calendario_liga(
                bd_equipos_validos["division"],
                bd_equipos_validos["grupo"],
                bd_equipos_validos["fecha_inicio_valida"],
            )
            
        assert not PartidoProgramado.objects.exists()
                

@pytest.mark.django_db
class TestIntegridadCalendario:
    """Comprueba que el calendario es un round-robin válido"""
    
    def test_cada_equipo_juega_una_vez_por_jornada(self, bd_equipos_validos):
        
        resultado = generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            bd_equipos_validos["fecha_inicio_valida"],
        )
        
        for jornada in resultado:
            equipos_jornada = [p["local"] for p in jornada] + [p["visitante"] for p in jornada]
            assert len(equipos_jornada) == len(set(equipos_jornada))
            
    def test_primera_vuelta_sin_emparejamientos_repetidos(self, bd_equipos_validos):
        
        resultado = generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            bd_equipos_validos["fecha_inicio_valida"],
        )
        emparejamientos = [
            frozenset((p["local"], p["visitante"]))
            for jornada in resultado[:7]
            for p in jornada
        ]
        assert len(emparejamientos) == len(set(emparejamientos))
        
    def test_generar_dos_veces_lanza_valueerror(self, bd_equipos_validos):
        
        fecha = bd_equipos_validos["fecha_inicio_valida"]
        generar_calendario_liga(bd_equipos_validos["division"], bd_equipos_validos["grupo"], fecha)
        
        with pytest.raises(ValueError, match="Ya existe un calendario"):
            generar_calendario_liga(bd_equipos_validos["division"], bd_equipos_validos["grupo"], fecha)
    
@pytest.mark.django_db          
class TestArbitros:
      
    def test_generar_arbitros(self):
        
        creados = generar_arbitros(10)
        
        assert len(creados) == 10
        assert Arbitro.objects.count() == 10
        assert all(1 <= a.severidad <= 20 for a in Arbitro.objects.all())
        
    def test_generar_arbitros_cantidad_invalida(self):
        
        with pytest.raises(ValueError):
            generar_arbitros(0)  
        
    def test_sin_repetidos_en_grupo(self, bd_arbitros):
        
        elegidos = elegir_arbitros(1, 4)
        assert len({a.id for a in elegidos}) == 4
        
    def test_reparto_equilibrado(self, bd_arbitros):
        
        carga = {}
        for _ in range(5):
            elegir_arbitros(1, 2, carga) # 10 asignaciones en tre 4 árbitros
            
        assert max(carga.values()) - min(carga.values()) <= 1
        
    def test_repite_si_faltan_arbitros(self, bd_arbitros):
        
        assert len(elegir_arbitros(1, 6)) == 6
        
    def test_ignora_inactivos(self, bd_arbitros):
        
        Arbitro.objects.exclude(id=bd_arbitros[0].id).update(activo=False)
        
        assert asignar_arbitro(1) == bd_arbitros[0]
        
    def test_error_sin_arbitros(self, db):
        with pytest.raises(ValueError):
            asignar_arbitro(1)
            
@pytest.mark.django_db
class TestArbitroEnSimulacion:
    """El árbitro asignado llega al simulador"""
    
    def _falso_partido(self, monkeypatch):
        
        recibidos = {}
        
        class PartidoFalso:
            ruta_reporte = None
            
            def __init__(self, *args, **kwargs):
                recibidos.update(kwargs)
                
            def simular_partido(self):
                return None
        
        monkeypatch.setattr("administracion.Partidos.simulador.Partido", PartidoFalso)
        return recibidos
    
    def test_amistoso_recibe_arbitro(self, bd_equipos_validos, monkeypatch):
        
        recibidos = self._falso_partido(monkeypatch)
        local, visitante = bd_equipos_validos["equipos"][:2]
        
        _simular(local, visitante, date(2026, 10, 15), time(20, 0), False, "amistoso")
        
        assert isinstance(recibidos["arbitro"], Arbitro)
        
    def test_liga_usa_arbitro_del_programado(self, bd_equipos_validos, monkeypatch):
        
        recibidos = self._falso_partido(monkeypatch)
        generar_calendario_liga(
            bd_equipos_validos["division"],
            bd_equipos_validos["grupo"],
            bd_equipos_validos["fecha_inicio_valida"],
        )
        programado = PartidoProgramado.objects.first()
        
        _simular(programado.equipo_local, programado.equipo_visitante, programado.fecha,
                 programado.hora, True, "liga", programado)
        
        assert recibidos["arbitro"] == programado.arbitro
            