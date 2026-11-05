import os
import pytest

from django.urls import reverse

from administracion.models import CalendarioTemporada, PartidoProgramado
from administracion.services import (
    calendario_desde_bd, guardar_calendario_html, generar_calendario_liga
)

@pytest.mark.django_db
class TestGuardarCalendarioHtml:
    """Comprueba que se genera el archivo y su registro en la BD"""
    
    def test_generar_calendario_crea_archivo_y_registro(self, calendario_generado):
        
        assert os.path.isfile(calendario_generado.ruta_archivo)
        with open(calendario_generado.ruta_archivo, encoding="utf-8") as f:
            contenido = f.read()
        assert "Equipo1" in contenido
        assert "Equipo2" in contenido
        
    def test_registro_con_datos_de_la_temporada(self, calendario_generado):
        
        assert (calendario_generado.temporada, calendario_generado.division, calendario_generado.grupo) == (1, 1, 1)
        
    def test_regenerar_html_no_duplica_registro(self, calendario_generado):
        
        calendario = calendario_desde_bd(1, 1, 1)
        guardar_calendario_html(1, 1, 1, calendario)
        
        assert CalendarioTemporada.objects.count() == 1
        
    def test_calendario_duplicado_no_crea_segundo_registro(self, calendario_generado):
        
        with pytest.raises(ValueError, match="Ya existe un calendario"):
            generar_calendario_liga(1, 1, "15-10-2026")
            
        assert CalendarioTemporada.objects.count() == 1
        
@pytest.mark.django_db
class TestCalendarioDesdeBd:
    """Comprueba que la reconstrucción desde BD tiene la estructura esperada"""
    
    def test_estructura_igual_a_generador(self, calendario_generado):
        
        jornadas = calendario_desde_bd(1, 1, 1)
        
        assert len(jornadas) == 14
        assert all(len(jornada) == 4 for jornada in jornadas)
        assert set(jornadas[0][0]) == {"jornada", "local", "visitante", "fecha", "hora"}
        assert jornadas[0][0]["jornada"] == 1
        
    def test_total_partidos_coincide_con_bd(self, calendario_generado):
        
        total = sum(len(j) for j in calendario_desde_bd(1, 1, 1))
        assert total == PartidoProgramado.objects.count()
        
    def test_sin_calendario_devuelve_lista_vacia(self, db):
        
        assert calendario_desde_bd(1, 9, 9) == []
        
        
@pytest.mark.django_db
class TestVerCalendarioView:
    """Comprueba los permisos de acceso al calendario"""
    
    def url(self, calendario):
        
        return reverse("administracion:ver_calendario", args=[calendario.id])
    
    def test_anonimo_redirige_al_login(self, client, calendario_generado):
        
        respuesta = client.get(self.url(calendario_generado))
        
        assert respuesta.status_code == 302
        assert "login" in respuesta.url
        
    def test_usuario_de_division_y_grupo_puede_verlo(self, client, calendario_generado, bd_equipos_validos):
        
        client.force_login(bd_equipos_validos["equipos"][0].user)
        respuesta = client.get(self.url(calendario_generado))
        
        assert respuesta.status_code == 200
        assert "Equipo1" in respuesta.content.decode()
        
    def test_staff_puede_verlo(self, client, calendario_generado, usuario_staff):
        
        client.force_login(usuario_staff)
        
        assert client.get(self.url(calendario_generado)).status_code == 200
        
    def test_usuario_otro_grupo_recibe_404(self, client, calendario_generado, equipo_otro_grupo):
        
        client.force_login(equipo_otro_grupo.user)
        
        assert client.get(self.url(calendario_generado)).status_code == 404
        
    def test_usuario_sin_equipo_recibe_404(self, client, calendario_generado, usuario_normal):
        
        client.force_login(usuario_normal)
        
        assert client.get(self.url(calendario_generado)).status_code == 404
        
    def test_calendario_inexistente_recibe_404(self, client, usuario_staff):
        
        client.force_login(usuario_staff)
        
        assert client.get(reverse("administracion:ver_calendario", args=[999])).status_code == 404
        
@pytest.mark.django_db
class TestMiCalendarioView:
    """Comprueba la redirección del enlace en el menú lateral"""
    
    def test_redirige_al_calendario_del_equipo(self, client, calendario_generado, bd_equipos_validos):
        
        client.force_login(bd_equipos_validos["equipos"][0].user)
        respuesta = client.get(reverse("administracion:mi_calendario"))
        
        assert respuesta.status_code == 302
        assert respuesta.url == reverse("administracion:ver_calendario", args=[calendario_generado.id])
        
    def test_sin_calendario_redirige_a_division_con_aviso(self, client, bd_equipos_validos):
        
        from django.contrib.messages import get_messages
        
        client.force_login(bd_equipos_validos["equipos"][0].user)
        respuesta = client.get(reverse("administracion:mi_calendario"))
        
        assert respuesta.url == reverse("clubs:division")
        assert any("calendario" in str(m) for m in get_messages(respuesta.wsgi_request))
        
    def test_usuario_sin_equipo_recibe_404(self, client, usuario_normal):
        
        client.force_login(usuario_normal)
        
        assert client.get(reverse("administracion:mi_calendario")).status_code == 404
        
    def test_anonimo_redirige_al_login(self, client, db):
        respuesta = client.get(reverse("administracion:mi_calendario"))
        
        assert respuesta.status_code == 302
        assert "login" in respuesta.url 
    