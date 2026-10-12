import pytest

from django.urls import reverse
from django.contrib.messages import get_messages

from administracion.forms import GenerarCalendarioForm

@pytest.mark.django_db
class TestGestionView:
    """Pruebas para la vista de gestión"""
    
    # --- Caso Normal
    def test_usuario_staff_puede_acceder_gestion(self, client, usuario_staff):
        """Un usuario con rol staff debe recibir código 200 y la plantilla correcta"""
        client.force_login(usuario_staff)
        url = reverse("administracion:gestion")
        respuesta = client.get(url)
        
        assert respuesta.status_code == 200
        assert "administracion/gestion.html" in [p.name for p in respuesta.templates]
        assert respuesta.context["titulo"] == "Gestión del sitio"
        
    # --- Casos Límite
    def test_usuario_anonimo_es_redirigido_a_login_admin(self, client):
        """Un usuario no staff no puede acceder a gestion y es redirigido (302)"""
        url = reverse("administracion:gestion")
        respuesta = client.get(url)
        
        assert respuesta.status_code == 302
        assert "/admin/login/" in respuesta.url
        
    def test_usuario_normal_es_redirigido(self, client, usuario_normal):
        """Un usuario autenticado pero sin rol de staff debe ser redirigido"""
        client.force_login(usuario_normal)
        url = reverse("administracion:gestion")
        respuesta = client.get(url)
        
        assert respuesta.status_code == 302
        assert "admin/login/" in respuesta.url
        
@pytest.mark.django_db
class TestGenerarCalendarioView:
    """Pruebas para la vista generar_calendario"""
    
    # --- Casos Normales
    def test_get_muestra_formulario_vacio(self, client, usuario_staff):
        """GET debe renderizar la página con una instancia vacía de GenerarCalendarioForm"""
        client.force_login(usuario_staff)
        url = reverse("administracion:generar_calendario")
        respuesta = client.get(url)
        
        assert respuesta.status_code == 200
        assert "administracion/generar_calendario.html" in [p.name for p in respuesta.templates]
        assert isinstance(respuesta.context["form"], GenerarCalendarioForm)
        assert respuesta.context["calendario"] is None
        
    def test_post_valido_genera_calendario_mensaje_exito(self, client, usuario_staff, bd_equipos_validos):
        """POST válido debe generar el calendario en contexto y emitir un mensaje de éxito"""
        client.force_login(usuario_staff)
        url = reverse("administracion:generar_calendario")
        datos_post = {
            "division": str(bd_equipos_validos["division"]),
            "grupo": str(bd_equipos_validos["grupo"]),
            "fecha_inicio": "2026-10-15",
        }
        respuesta = client.post(url, data=datos_post)
        
        assert respuesta.status_code == 200
        assert respuesta.context["calendario"] is not None
        assert len(respuesta.context["calendario"]) == 14
        
        mensajes = [m.message for m in get_messages(respuesta.wsgi_request)]
        assert any("generado correctamente" in m for m in mensajes)
        
    # --- Gestión de Errores
    def test_post_invalido_no_genera_calendario_muestra_errores(self, client, usuario_staff):
        """POST con datos incompletos no debe generar el calendario"""
        client.force_login(usuario_staff)
        url = reverse("administracion:generar_calendario")
        respuesta = client.post(url, data={})
        
        assert respuesta.status_code == 200
        assert respuesta.context["calendario"] is None
        assert respuesta.context["form"].errors
        
    def test_post_con_division_sin_equipos_muestra_error(self, client, usuario_staff):
        """Si el servicio lanza ValueError (división vacía), la vista debe mostrar un mensaje de error"""
        client.force_login(usuario_staff)
        url = reverse("administracion:generar_calendario")
        datos_post = {
            "division": "99",
            "grupo": "99",
            "fecha_inicio": "2026-10-15"
        }
        respuesta = client.post(url, data=datos_post)
        
        assert respuesta.status_code == 200
        assert respuesta.context["calendario"] is None
        
        mensajes = [m.message for m in get_messages(respuesta.wsgi_request)]
        assert any("No hay equipos registrados" in m for m in mensajes)
        
    