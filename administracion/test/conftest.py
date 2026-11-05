import pytest

from django.contrib.auth.models import User

from clubs.models import Equipo
from administracion.models import Arbitro

@pytest.fixture
def bd_equipos_validos(db, bd_arbitros):
    """Crea 8 equipos en la base de datos para la División 1, Grupo 1"""
    division = "1"
    grupo = "1"
    nombres = [f"Equipo{i}" for i in range(1, 9)]
    equipos = []
    
    for i, nombre in enumerate(nombres, start=1):
        usuario = User.objects.create_user(username=f"manager_valido{i}", password="Password123")
        equipo = Equipo.objects.create(
            user = usuario,
            nombre_equipo = nombre,
            abreviatura = f"ED{i}",
            division = division,
            grupo = grupo,
            temporada = 1
        )
        equipos.append(equipo)
    
    return{
        "division": division,
        "grupo": grupo,
        "equipos": equipos,
        "fecha_inicio_valida": "15-10-2026",
    }
    
@pytest.fixture
def bd_equipos_impar(db, bd_arbitros):
    """Caso límite. Crea un número impar de equipos (3) para evaluar comportamientos límite en la división de parejas"""
    division = "2"
    grupo = "1"
    nombres = ["Equipo Alfa", "Equipo Beta", "Equipo Gamma"]
    equipos = []
    
    for i, nombre in enumerate(nombres, start=1):
            usuario = User.objects.create_user(username=f"manager_impar{i}", password="Password123")
            equipo = Equipo.objects.create(
                user = usuario,
                nombre_equipo = nombre,
                abreviatura = f"EI{i}",
                division = division,
                grupo = grupo,
                temporada = 1
            )
            equipos.append(equipo)
            
    return{
        "division": division,
        "grupo": grupo,
        "equipos": equipos,
        "fecha_inicio_valida": "01-11-2026",
    }
    
@pytest.fixture
def fechas_invalidas():
    """Devuelve una lista de fechas inválidas para probar la validación de excepciones"""
    return[
        "2026-10-15",
        "15/10/2026",
        "texto-invalido",
        "31-02-2026",
    ]
    
@pytest.fixture
def usuario_staff(db):
    """Usuario con permisos de administración"""
    return User.objects.create_user(
        username = "admin_staff",
        password = "StaffPassword123",
        is_staff = True,
    )
    
@pytest.fixture
def usuario_normal(db):
    """Usuario registrado común"""
    return User.objects.create_user(
            username = "usuario_normal",
            password = "Password123",
            is_staff = False,
        )
    
@pytest.fixture
def bd_arbitros(db):
    """Crea 4 árbitros activos"""
    return [
        Arbitro.objects.create(nombre=f"Arbitro{i}", severidad=10, origen="España")
        for i in range(1, 5)
    ]
    
@pytest.fixture(autouse=True)
def partidos_dir_temporal(tmp_path, monkeypatch):
    """Redirige los HTML generados a una carpeta temporal para no ensuciar PARTIDOS_DIR"""
    monkeypatch.setattr("administracion.services.PARTIDOS_DIR", str(tmp_path))
    
    return tmp_path

@pytest.fixture
def calendario_generado(bd_equipos_validos):
    """Genera el calendario de la división 1, grupo 1 y devuelve su registro"""
    from administracion.models import CalendarioTemporada
    from administracion.services import generar_calendario_liga
    
    generar_calendario_liga(
        bd_equipos_validos["division"],
        bd_equipos_validos["grupo"],
        bd_equipos_validos["fecha_inicio_valida"],
    )
    return CalendarioTemporada.objects.get()

@pytest.fixture
def equipo_otro_grupo(db):
    """Usuario con equipo en la división 1, grupo 2 (distinto grupo al calendario)"""
    usuario = User.objects.create_user(username="manager_otro_grupo", password="Password123")
    
    return Equipo.objects.create(
        user=usuario, nombre_equipo="Otro Grupo FC", abreviatura="OGR",
        division=1, grupo=2, temporada=1,
    )