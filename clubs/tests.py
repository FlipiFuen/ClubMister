import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.urls import reverse

from clubs.plantilla import Plantilla, fill_gaussian_vars_arr
from clubs.models import Equipo, Futbolista, Estadio
from clubs.services import calcular_calificacion, calcular_resistencia, calcular_agresividad, lado_preferido, enriquecer_jugador, obtener_equipo_plantilla

@pytest.fixture
def plantilla():
    """Instancia de Plantilla lista para usar en varios tests"""
    return Plantilla()

@pytest.fixture
def usuario_equipo():
    """Crea y devuelve un usuario de equipo para pruebas"""
    return User.objects.create_user(username="testuser", password="testpassword")

@pytest.fixture
def equipo(usuario_equipo):
    """Crea y devuelve un equipo asociado a un usuario de equipo para pruebas"""
    return Equipo.objects.create(user=usuario_equipo, nombre_equipo="Test Equipo", abreviatura="TEF", temporada=1)

@pytest.fixture
def futbolista_prueba(equipo):
    """Devuelve un futbolista con atributos conocidos para probar servicios"""
    return Futbolista.objects.create(
        equipo = equipo,
        nombre = "Carlos Test",
        nacionalidad = "esp",
        edad = 24,
        posicion = "mc",
        lado_preferido = "D",
        st = 14, # ELITE
        tk = 10, # ACEPTABLE
        ps = 8, # PRINCIPIANTE
        sh = 5, # INUTIL
        resistencia = 65, # UN TORO
        agresividad = 30, # Normal
        st_hab = 300,
        tk_hab = 300,
        ps_hab = 300,
        sh_hab = 300,
    )
    
@pytest.fixture
def estadio_prueba(usuario_equipo, equipo):
    """Devuelve un estadio asociado al usuario y equipo"""
    return Estadio.objects.create(
        user = usuario_equipo,
        equipo = equipo,
        nombre = "Estadio Viejo",
        precio = 25.0,
        capacidad = 8000,
    )

class TestFillGaussianVarsArr:
    """Pruebas para la función fill_gaussian_vars_arr"""
    
    # --- Caso Normal
    def test_devuelve_la_cantidad_solicitada(self):
        """Debe devolver exactamente la cantidad solicitada"""
        valores = fill_gaussian_vars_arr(50)
        
        assert len(valores) == 50
        
    def test_valores_estan_en_rango_esperado(self):
        """Todos los valores deben estar dentro del rango esperado (-1, 1)"""
        valores = fill_gaussian_vars_arr(100)
        
        assert all(-1.0 < v < 1.0 for v in valores)
        
    # --- Caso Límite
    def test_amount_cero_devuelve_lista_vacia(self):
        """Si se solicita 0 valores, debe devolver una lista vacía"""
        valores = fill_gaussian_vars_arr(0)
        
        assert valores == []
        

class TestPlantilla:
    """Pruebas para la clase Plantilla"""

    # --- Caso Normal
    @pytest.mark.parametrize("posicion", ["por", "def", "mcd", "mc", "mp", "del"])
    def test_genera_las_4_habilidades_para_cada_posicion(self, plantilla, posicion):
        """Toda posición válida debe devolver un diccionario con st, tk, ps y sh"""
        habilidades = plantilla.generar_habilidades(posicion)
        
        assert set(habilidades.keys()) == {"st", "tk", "ps", "sh"}
        
    def test_portero_tiene_st_habilidad_dominante(self, plantilla):
        """Para 'por', 'st' debe promediar más alto que el resto"""
        medias = [plantilla.generar_habilidades("por")["st"] for _ in range(200)]
        
        assert sum(medias) / len(medias) > 8 # media esperada ~14, con margen amplio por la desviación
        
    def test_generar_nacionalidad_devuelve_string_valido(self, plantilla):
        """Debe devolver una de las nacionalidades definidas en la lista interna"""
        nacionalidad = plantilla.generar_nacionalidad()
        
        assert isinstance(nacionalidad, str)
        assert len(nacionalidad) == 3
        
    def test_generar_lado_preferido_devuelve_opcopn_valida(self, plantilla):
        """El resultado debe ser una de las combinaciones D/I/C definidas"""
        lados_validos = {"D-I-C", "D-I", "D-C", "I-C", "D", "I", "C"}
        
        assert plantilla.generar_lado_preferido() in lados_validos
        
    def test_generar_nombres_devuelve_29_nombres_unicos(self, plantilla):
        """Debe devolver exactamente 29 nombres únicos"""
        nombres = plantilla.generar_nombres()
        
        assert isinstance(nombres, list)
        assert len(nombres) == 29
        assert len(set(nombres)) == 29
        
    def test_atributos_futbolistas_genera_un_registro_por_nombre(self, plantilla):
        """Debe devolver un futbolista completo por cada nombre recibido"""
        nombres = ["A. Test1", "B. Test2", "C. Test3"]
        futbolistas = plantilla.atributos_futbolistas(nombres)
        
        assert len(futbolistas) == len(nombres)
        assert futbolistas[0]["nombre"] == "A. Test1"
        assert "habilidades" in futbolistas[0]
        
    def test_crear_equipo_devuelve_29_futbolistas(self, plantilla):
        """crear_equipo debe generar la plantilla completa con 29 futbolistas"""
        equipo = plantilla.crear_equipo()
        
        assert len(equipo) == 29
        assert all("posicion" in futbolista for futbolista in equipo)
        
    # --- Caso Límite
    def test_generar_posicion_respeta_limite_porteros(self, plantilla):
        """Nunca debe asignar más de 2 porteros aunque se fuerce el sorteo muchas veces"""
        posiciones = {"por": 2, "def": 0, "mcd": 0, "mc": 0, "mp": 0, "del": 0}
        plantilla.posiciones = posiciones
        
        # Con "por" ya lleno, generar_posicion debe reintentar y devolver otra posición
        resultado = plantilla.generar_posicion(posiciones)
        
        assert resultado != "por"
        
    def test_posicion_no_reconocida_devuelve_habilidades_cero(self, plantilla):
        """Una posición no reconocida debe devolver un diccionario con todas las habilidades en cero"""
        habilidades = plantilla.generar_habilidades("posicion_inexistente")
        
        assert habilidades == {"st": 0, "tk": 0, "ps": 0, "sh": 0}
        
    def test_atributos_futbolista_con_lista_vacia_devuelve_lista_vacia(self, plantilla):
        """Sin nombres de entrada, debe devolver una lista vacía"""
        futbolistas = plantilla.atributos_futbolistas([])
        
        assert futbolistas == []
        
    # --- Casos de Error
    def test_generar_posicion_con_equipo_completo_lanza_valueerror(self, plantilla):
        """Si todas las posiciones están llenas, debe lanzar un ValueError"""
        posiciones = {"por": 2, "def": 8, "mcd": 3, "mc": 6, "mp": 3, "del": 7}
        plantilla.posiciones = posiciones
        
        with pytest.raises(ValueError, match="No quedan huecos disponibles en ninguna posición"):
            plantilla.generar_posicion(posiciones)
            
            
@pytest.mark.django_db
class TestEquipoModel:
    """Pruebas para el modelo Equipo."""
    
    # --- Caso Normal
    def test_creacion_equipo_con_datos_validos(self, equipo):
        """Un equipo creado con datos válidos debe persistir con los valores por defecto esperados"""
        assert equipo.pk is not None
        assert equipo.division == 1
        assert equipo.grupo == 1
        assert equipo.puntos == 0
        
    def test_str_devuelve_nombre_equipo(self, equipo):
        """El método __str__ debe devolver el nombre del equipo"""
        assert str(equipo) == "Test Equipo"
        
    # --- Caso Límite
    def test_nombre_equipo_duplicado_lanza_integrityerror(self, equipo, django_user_model):
        """Intentar crear un equipo con un nombre duplicado debe lanzar un IntegrityError"""
        otro_usuario = django_user_model.objects.create_user(
            username="otro_usuario",
            password="password123"
        )
        
        with pytest.raises(IntegrityError):
            Equipo.objects.create(
                user=otro_usuario,
                nombre_equipo="Test Equipo",
                abreviatura="OTR",
                temporada=1
            )
            
    # --- Gestión de errores
    def test_usuario_no_puede_tener_dos_equipos(self, equipo, usuario_equipo):
        """Un usuario no puede tener dos equipos; debe lanzar un IntegrityError"""
        with pytest.raises(IntegrityError):
            Equipo.objects.create(
                user=usuario_equipo,
                nombre_equipo="Otro Equipo",
                abreviatura="OTR",
                temporada=1
            )
            

@pytest.mark.django_db
class TestFutbolistaModel:
    """Pruebas para el modelo Futbolista."""
    
    # --- Caso Normal
    def test_creacion_futbolista_asociado_a_equipo(self, equipo):
        """Un futbolista creado debe estar asociado a un equipo"""
        futbolista = Futbolista.objects.create(
            equipo=equipo,
            nombre="A. Test",
            nacionalidad="esp",
            edad=25,
            posicion="Del",
            lado_preferido="D",
            st = 5, tk = 12, ps = 6, sh = 5, resistencia = 60, agresividad = 30,
            st_hab = 300, tk_hab = 300, ps_hab = 300, sh_hab = 300,
        )
        
        assert futbolista in equipo.futbolistas.all()
        assert str(futbolista) == "A. Test"
        
    # --- Caso Límite
    def test_borrar_equipo_borra_futbolistas_en_cascada(self, equipo):
        """Borrar un equipo debe borrar todos los futbolistas asociados en cascada"""
        futbolista = Futbolista.objects.create(
            equipo=equipo,
            nombre="B. Test",
            nacionalidad="esp",
            edad=22,
            posicion="Del",
            lado_preferido="I",
            st = 4, tk = 10, ps = 5, sh = 4, resistencia = 55, agresividad = 25,
            st_hab = 250, tk_hab = 250, ps_hab = 250, sh_hab = 250,
        )
        equipo.delete()

        assert Futbolista.objects.count() == 0
        
@pytest.mark.django_db
class TestClubView:
    """Pruebas de la vista protegida del club."""

    def test_usuario_autenticado_puede_ver_su_club(self, client, django_user_model):
        """Un usuario autenticado debe recibir la página del club."""
        usuario = django_user_model.objects.create_user(username="entrenador", password="Clave789!")
        client.force_login(usuario)

        respuesta = client.get(reverse("clubs:club"))

        assert respuesta.status_code == 200
        assert "clubs/club.html" in [plantilla.name for plantilla in respuesta.templates]

    def test_usuario_anonimo_es_redirigido_al_login(self, client):
        """Sin sesión, @login_required debe redirigir al login."""
        respuesta = client.get(reverse("clubs:club"))

        assert respuesta.status_code == 302
        assert respuesta.url.startswith(reverse("usuarios:login"))
        
@pytest.mark.django_db
class TestClubsServices:
    """Pruebas para services.py"""
    
    # --- Casos Normales
    @pytest.mark.parametrize(
        "valor, esperado",
        [
            (5, "INUTIL"),
            (7, "APRENDIZ"),
            (10, "ACEPTABLE"),
            (14, "ELITE"),
            (20, "GOAT"),
        ]
    )
    def test_calcular_calificacion_valores_estandar(self, valor, esperado):
        """Mapeo correcto de puntuaciones a adjetivos"""
        assert calcular_calificacion(valor) == esperado
        
    def test_enriquecer_jugador_asigna_atributos_dinamicos(self, futbolista_prueba):
        """Calcula porcentajes y etiquetas cualitativas correctamente"""
        enriquecer_jugador(futbolista_prueba)
        
        assert futbolista_prueba.porcentaje_st == 70
        assert futbolista_prueba.porcentaje_tk == 50
        assert futbolista_prueba.porcentaje_ps == 40
        assert futbolista_prueba.porcentaje_sh == 25
        assert futbolista_prueba.calificacion_st == "ELITE"
        assert futbolista_prueba.calificacion_tk == "ACEPTABLE"
        assert futbolista_prueba.calificacion_resistencia == "UN TORO"
        assert futbolista_prueba.lado == "DERECHA"
        assert futbolista_prueba.agresivo == "Normal"
        
    def test_obtener_equipo_plantilla_cocn_usuario_equipo(self, usuario_equipo, equipo, futbolista_prueba):
        """Devuelve el club del usuario y la lista de futbolistas enriquecidos"""
        club_retornado, plantilla_retornada = obtener_equipo_plantilla(usuario_equipo)
        
        assert club_retornado == equipo
        assert len(plantilla_retornada) >= 1
        jugador = plantilla_retornada[0]
        assert hasattr(jugador, "porcentaje_st")
        assert jugador.calificacion_st == "ELITE"
        
    # --- Casos Límite
    def test_enriquecer_jugador_acota_porcentajes_entre_cero_cien(self, futbolista_prueba):
        """Si un atributo es anómalo, el porcentaje no debe salir del rango 0 a 100"""
        futbolista_prueba.st = -5
        futbolista_prueba.tk = 25 # 25 * 5 = 125 -> debe acotarse a 100
        enriquecer_jugador(futbolista_prueba)
        
        assert futbolista_prueba.porcentaje_st == 0
        assert futbolista_prueba.porcentaje_tk == 100
        
    def test_lado_preferido_desconocido_devuelve_valor_defecto(self):
        """Un código de lado no registrado debe devolver "DESCONOCIDO"""
        assert lado_preferido("VALOR_INEXISTENTE") == "DESCONOCIDO"
        
    def test_calcular_resistencia_limite_superior(self):
        """Valor límite de 100 en resistencia debe devolver TANQUE"""
        assert calcular_resistencia(100) == "TANQUE"
        
    def test_obtener_equipo_plantilla_sin_equipo_devuelve_tupla_none(self, django_user_model):
        """Si el usuario no tiene equipo devuelve None"""
        usuario_sin_club = django_user_model.objects.create_user(username="sin_club", password="Password123")
        club, plantilla = obtener_equipo_plantilla(usuario_sin_club)
        
        assert club is None
        assert plantilla is None
        
@pytest.mark.django_db
class TestClubsViews:
    """Pruebas para las vistas de equipo, estadio y edición de estadio"""
    
    # --- VISTA EQUIPO ---
    
    # Caso Normal
    def test_vista_equipo_muestra_plantilla_enriquecida(self, client, usuario_equipo, equipo, futbolista_prueba):
        """Usuario autenticado con equipo recibe su plantilla"""
        client.force_login(usuario_equipo)
        respuesta = client.get(reverse("clubs:equipo"))
        
        assert respuesta.status_code == 200
        assert "clubs/equipo.html" in [t.name for t in respuesta.templates]
        assert respuesta.context["club"] == equipo
        plantilla = list(respuesta.context["plantilla"])
        assert len(plantilla) == 1
        assert hasattr(plantilla[0], "porcentaje_st")
        
    # --- Caso Límite
    def test_vista_equipo_redirige_usuario_anonimo(self, client):
        """Un usuario sin autenticar es redirigido al login"""
        respuesta = client.get(reverse("clubs:equipo"))
        
        assert respuesta.status_code == 302
        assert respuesta.url.startswith(reverse("usuarios:login"))
        
    # --- VISTA ESTADIO ---
    
    # --- Caso Normal
    def test_vista_estadio_muestra_estadio_existente(self, client, usuario_equipo, estadio_prueba):
        """Usuario con estadio ya creado recibe el contexto del estadio correcto"""
        client.force_login(usuario_equipo)
        respuesta = client.get(reverse("clubs:estadio"))
        
        assert respuesta.status_code == 200
        assert "clubs/estadio.html" in [t.name for t in respuesta.templates]
        assert respuesta.context["estadio"].nombre == "Estadio Viejo"
        
    # --- Caso Límite
    def test_vista_estadio_crea_estadio_por_defecto_si_no_existe(self, client, usuario_equipo, equipo):
        """Si el usuario no tiene estadio, la vista crea uno por defecto con valores predefinidos"""
        client.force_login(usuario_equipo)
        respuesta = client.get(reverse("clubs:estadio"))
        
        assert respuesta.status_code == 200
        estadio_creado = respuesta.context["estadio"]
        assert estadio_creado is not None
        assert estadio_creado.capacidad == 5000
        assert estadio_creado.precio == 30
        
    # --- Gestión de Errores
    def test_vista_estadio_redirige_usuario_anonimo(self, client):
        """Usuario sin autenticar es redirigido al login"""
        respuesta = client.get(reverse("clubs:estadio"))
        
        assert respuesta.status_code == 302
        assert respuesta.url.startswith(reverse("usuarios:login"))
        
    # --- VISTA EDITAR_NOMBRE_ESTADIO
    
    # --- Caso Normal
    def test_post_editar_nombre_estadio_actualiza_nombre(self, client, usuario_equipo, estadio_prueba):
        """un POST válido debe actualizar el nombre del estadio y redirigir a la vista del estadio"""
        client.force_login(usuario_equipo)
        respuesta = client.post(
            reverse("clubs:editar_nombre_estadio"),
            {"nuevo_nombre": "Estadio Nuevo"}
        )
            
        assert respuesta.status_code == 302
        assert respuesta.url == reverse("clubs:estadio")
        estadio_prueba.refresh_from_db()
        assert estadio_prueba.nombre == "Estadio Nuevo"
        
    # --- Caso Límite
    def test_post_editar_nombre_estadio_sin_nombre_no_actualiza(self, client, usuario_equipo, estadio_prueba):
        """Si nuevo_nombre está vacío, el nombre del estadio no debe cambiar"""
        client.force_login(usuario_equipo)
        client.post(
            reverse("clubs:editar_nombre_estadio"),
            {"nuevo_nombre": ""}
        )
        
        estadio_prueba.refresh_from_db()
        assert estadio_prueba.nombre == "Estadio Viejo"
        
    # --- Gestión de Errores
    def test_get_editar_nombre_estadio_redirige_sin_actuar(self, client, usuario_equipo, estadio_prueba):
        """Un GET a esta vista debe redirigir sin modificar el estadio"""
        client.force_login(usuario_equipo)
        respuesta = client.get(reverse("clubs:editar_nombre_estadio"))
        
        assert respuesta.status_code == 302
        assert respuesta.url == reverse("clubs:estadio")
        estadio_prueba.refresh_from_db()
        assert estadio_prueba.nombre == "Estadio Viejo"
        