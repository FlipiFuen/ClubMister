import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.contrib.auth.models import User

from usuarios.formulario import RegistroForm
from usuarios.services import asignar_division_grupo, crear_equipo_inicial
from clubs.models import Equipo

@pytest.fixture
def datos_validos():
    """Datos mínimos y válidos para el formulario de registro"""
    return {
        "username": "nuevo_usuario",
        "email": "nuevo@ejemplo.com",
        "password1": "contraseñaSegura789",
        "password2": "contraseñaSegura789",
        "nombre_equipo": "Deportivo Pytest",
        "abreviatura": "DPT",
    }
    
@pytest.fixture
def crear_equipo_en(django_user_model):
    """Crea equipos con división/grupos concretos"""
    contador = [0]
    
    def _crear(division, grupo):
        contador[0] += 1
        usuario = django_user_model.objects.create_user(
            username = f"user_{contador[0]}", password = "clave-segura-123"
        )
        return Equipo.objects.create(
            user = usuario,
            nombre_equipo = f"Equipo {contador[0]}",
            abreviatura = f"E{contador[0]:02d}",
            division = division,
            grupo = grupo,
            temporada = 1,
        )
    return _crear

@pytest.fixture
def usuario_login(django_user_model):
    """Usuario común para probar el inicio y cierre de sesión."""
    return django_user_model.objects.create_user(
        username="usuario_login",
        password="ClaveSegura789!",
    )
    
@pytest.mark.django_db
class TestRegistroForm:
    """Pruebas para el formulario de registro de usuarios y equipos."""

    # --- Caso Normal
    def test_formulario_valido_con_datos_validos(self, datos_validos):
        """El formulario debe ser válido cuando se proporcionan datos correctos"""
        form = RegistroForm(data=datos_validos)
        
        assert form.is_valid(), form.errors
        
    def test_save_crea_usuario_con_email_asignado(self, datos_validos):
        """El método save del formulario debe crear un usuario con el email asignado"""
        form = RegistroForm(data=datos_validos)
        form.is_valid()
        usuario = form.save()
        
        assert User.objects.filter(username="nuevo_usuario").exists()
        assert usuario.email == "nuevo@ejemplo.com"
        
    # --- Caso Limite
    def test_abreviatura_minusculas_pasa_a_mayusculas(self, datos_validos):
        """La abreviatura del equipo debe convertirse a mayúsculas"""
        datos_validos["abreviatura"] = "dpt"
        form = RegistroForm(data=datos_validos)
        
        assert form.is_valid(), form.errors
        assert form.cleaned_data["abreviatura"] == "DPT"
        
    def test_nombre_equipo_con_espacios_se_recorta(self, datos_validos):
        """Los espacios al inicio y al final del nombre del equipo deben recortarse"""
        datos_validos["nombre_equipo"] = "  Deportivo Pytest  "
        form = RegistroForm(data=datos_validos)
        
        assert form.is_valid(), form.errors
        assert form.cleaned_data["nombre_equipo"] == "Deportivo Pytest"
        
    @pytest.mark.parametrize("abreviatura_invalida", ["", "a", "ab", "abcd", "123", "!@#"])
    def test_abreviatura_longitud_o_caracteres_invalidos(self, datos_validos, abreviatura_invalida):
        """La abreviatura del equipo no debe ser válida si no cumple con la longitud o contiene caracteres inválidos"""
        datos_validos["abreviatura"] = abreviatura_invalida
        form = RegistroForm(data=datos_validos)
        
        assert not form.is_valid()
        assert "abreviatura" in form.errors
        
    # --- Casos de Error
    def test_nombre_equipo_duplicado_lanza_error(self, datos_validos, django_user_model):
        """Un nombre_equipo ya existente (case insensitive) debe invalidar el formulario"""
        otro_usuario = django_user_model.objects.create_user(
            username="ya_existe",
            password="password123",
        )
        Equipo.objects.create(
            user = otro_usuario,
            nombre_equipo="Deportivo Pytest",
            abreviatura="DPT",
            temporada = 1,  
        )
        datos_validos["nombre_equipo"] = "deportivo pytest" # Mismo nombre pero en minúsculas
        
        form = RegistroForm(data=datos_validos)
        
        assert not form.is_valid()
        assert "El nombre del equipo ya existe" in form.errors["nombre_equipo"]
        
    def test_passwords_no_coinciden_lanza_error(self, datos_validos):
        """El formulario debe ser inválido si las contraseñas no coinciden"""
        datos_validos["password1"] = "contraseñaSegura789"
        datos_validos["password2"] = "contraseñaDistinta456"
        form = RegistroForm(data=datos_validos)
        
        assert not form.is_valid()
        assert "password2" in form.errors

@pytest.mark.django_db
class TestEquipo:
    """Pruebas de creación de equipo y asignar división y grupo"""
    
    # --- Caso Normal
    def test_sin_equipos_devuelve_division1_grupo1(self):
        """Sin ningún equipo en la BD, el primero debe ir a división 1 grupo 1"""
        division, grupo = asignar_division_grupo()
        
        assert (division, grupo) == (1, 1)
        
    def test_con_equipo_existente_mantiene_division_grupo_si_hueco(self, crear_equipo_en):
        """Si el último equipo está en un grupo con menos de 8 equipos, se mantiene división y grupo"""
        crear_equipo_en(division=1, grupo=1)
        division, grupo = asignar_division_grupo()
        
        assert (division, grupo) == (1, 1)
        
    def test_crea_equipo_con_29_futbolistas(self, django_user_model):
        """Debe crear el equipo y poblarlo con la plantilla de 29 jugadores"""
        usuario = django_user_model.objects.create_user(username="dt", password="clave-segura-123")
        equipo = crear_equipo_inicial(usuario, "Deportivo Servicio", "DSV")
        
        assert equipo.pk is not None
        assert equipo.futbolistas.count() == 29
        assert equipo.temporada == 1
        
    # --- Caso Límite 
    def test_grupo_lleno_pasa_al_siguiente_grupo(self, crear_equipo_en):
        """Con 8 equipos el grupo 1, el siguiente debe asignarse al grupo 2"""
        for _ in range(8):
            crear_equipo_en(division=1, grupo=1)
            
        division, grupo = asignar_division_grupo()
        
        assert (division, grupo) == (1 ,2)
        
    def test_division_con_8_grupos_llenos_pasa_siguiente_division(self, crear_equipo_en):
        """Con el grupo 8 de la división 1 lleno, debe pasar a división 2 grupo 1"""
        for _ in range(8):
            crear_equipo_en(division=1, grupo=8)
                    
        division, grupo = asignar_division_grupo()
                
        assert (division, grupo) == (2, 1)
        
    def test_equipo_creado_hereda_division_grupo_calculados(self, django_user_model, crear_equipo_en):
        """El equipo creado debe usar la división/grupo que calcula asignar_division_grupo"""
        for _ in range(8):
            crear_equipo_en(division=1, grupo=1)
        
        usuario = django_user_model.objects.create_user(username="dt2", password="clave-segura-123")
        equipo = crear_equipo_inicial(usuario, "Deportivo Servicio 2", "DS2")
        
        assert (equipo.division, equipo.grupo) == (1, 2)
        
    # --- Gestión de errores
    def test_nombre_equipo_duplicado_lanza_integrityerror(self, django_user_model):
        """Crear 2 equipos con el mismo nombre debe fallar"""
        usuario1 = django_user_model.objects.create_user(username="dt3", password="clave-segura-123")
        usuario2 = django_user_model.objects.create_user(username="dt4", password="clave-segura-123")
        crear_equipo_inicial(usuario1, "Nombre Repetido", "NR1")
        
        with pytest.raises(IntegrityError):
            crear_equipo_inicial(usuario2, "Nombre Repetido", "NR2")
            
@pytest.mark.django_db
class TestRegistroView:
    """Pruebas para la vista de registro"""
    
    def test_get_muestra_formulario(self, client):
        """GET debe renderizar la página con un formulario de registro"""
        respuesta = client.get(reverse("usuarios:registro"))
        
        assert respuesta.status_code == 200
        assert "usuarios/registro.html" in [plantilla.name for plantilla in respuesta.templates]
        assert isinstance(respuesta.context["formulario"], RegistroForm)
        
    def test_post_invalido_vuelve_a_mostrar_errores(self, client, datos_validos):
        """Un POST inválido debe mostrar errores sin crear el usuario."""
        datos_validos["password2"] = "OtraClaveInvalida789"
        respuesta = client.post(reverse("usuarios:registro"), data=datos_validos)

        assert respuesta.status_code == 200
        assert "password2" in respuesta.context["formulario"].errors
        assert not User.objects.filter(username=datos_validos["username"]).exists()

    def test_post_valido_crea_usuario_equipo_e_inicia_sesion(self, client, datos_validos):
        """Un registro válido debe crear el equipo, autenticar al usuario y redirigir al inicio."""
        respuesta = client.post(reverse("usuarios:registro"), data=datos_validos)

        assert respuesta.status_code == 302
        assert respuesta.url == reverse("club_mister:principal")

        usuario = User.objects.get(username=datos_validos["username"])
        equipo = Equipo.objects.get(user=usuario)

        assert equipo.nombre_equipo == datos_validos["nombre_equipo"]
        assert equipo.futbolistas.count() == 29
        assert str(usuario.pk) == client.session["_auth_user_id"]
     
@pytest.mark.django_db
class TestAutenticacionViews:
    """Pruebas de las vistas de login y logout."""

    def test_login_valido_autentica_y_redirige(self, client, usuario_login):
        """Credenciales válidas deben iniciar sesión y redirigir al inicio."""
        respuesta = client.post(
            reverse("usuarios:login"),
            {"username": "usuario_login", "password": "ClaveSegura789!"},
        )

        assert respuesta.status_code == 302
        assert respuesta.url == reverse("club_mister:principal")
        assert str(usuario_login.pk) == client.session["_auth_user_id"]

    def test_login_invalido_muestra_error(self, client, usuario_login):
        """Una contraseña incorrecta debe dejar al usuario en el formulario de login."""
        respuesta = client.post(
            reverse("usuarios:login"),
            {"username": usuario_login.username, "password": "incorrecta"},
        )

        assert respuesta.status_code == 200
        assert respuesta.context["form"].errors
        assert "_auth_user_id" not in client.session

    def test_logout_cierra_sesion_y_redirige(self, client, usuario_login):
        """Cerrar sesión debe eliminar la autenticación y redirigir al inicio."""
        client.force_login(usuario_login)

        respuesta = client.post(reverse("usuarios:logout"))

        assert respuesta.status_code == 302
        assert respuesta.url == reverse("club_mister:principal")
        assert "_auth_user_id" not in client.session   
            