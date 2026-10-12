import pytest

from datetime import datetime, timedelta
from django.contrib.auth.models import User

from administracion.services import generar_calendario_liga
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
            
@pytest.mark.django_db
class TestGenerarCalendarioLigaEdgeCases:
    """Casos Límite"""
    
    def test_generar_calendario_con_numero_minimo_equipos(self, db):
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
    
    def test_sin_equipos_lanza_valueerror(self, db):
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
                
