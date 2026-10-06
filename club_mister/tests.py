import pytest
from django.urls import reverse, NoReverseMatch
        
@pytest.fixture
def principal_url():
    """URL de la página principal, generada una sola vez para todos los tests"""
    return reverse("club_mister:principal")

class TestPrincipalView:
    """Pruebas de la vista principal"""
    
    # --- Caso Normal
    def test_principal_devuelve_codigo_200(self, client, principal_url):
        """Petición GET típica, la página debe responder correctamente"""
        respuesta = client.get(principal_url)
        
        assert respuesta.status_code == 200
        
    def test_principal_usa_plantilla_correcta(self, client, principal_url):
        """Verifica que se renderiza la plantilla esperada"""
        respuesta = client.get(principal_url)
        
        assert "club_mister/principal.html" in [t.name for t in respuesta.templates]
        
    # --- Caso Límite
    def test_prinicpal_responde_post(self, client, principal_url):
        """La vista no restringe métodos POST"""
        respuesta = client.get(principal_url)
        
        assert respuesta.status_code == 200
        
    # --- Gestión de Errores
    def test_reverse_con_nombre_incorrecto_lanza_excepcion(self):
        """Un nombre de ruta inexistente debe lanzar NoReverseMatch"""
        with pytest.raises(NoReverseMatch):
            reverse("club_mister:no_existe")
