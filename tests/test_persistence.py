from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.repositories import project_repo, sprint_repo, issue_repo, transition_repo
import app.models as models

@pytest.fixture(name="db_session")
def fixture_db_session():
    """Configura una base de datos SQLite en memoria limpia para cada test."""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_proyecto_and_sprint_crud(db_session):
    """Verifica la persistencia básica (creación, lectura, actualización y borrado) de Proyectos y Sprints."""
    # 1. Crear
    proyecto_in = {"id_proyecto": "P-1", "key_proyecto": "KEY-1", "nombre": "Proyecto Prueba"}
    proyecto = project_repo.create(db_session, obj_in=proyecto_in)
    
    assert proyecto.id_proyecto == "P-1"
    assert proyecto.nombre == "Proyecto Prueba"
    
    sprint_in = {
        "id_sprint": "S-1",
        "id_proyecto": "P-1",
        "nombre": "Sprint 1",
        "estado": "active",
        "fecha_inicio": datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    }
    sprint = sprint_repo.create(db_session, obj_in=sprint_in)
    
    assert sprint.id_sprint == "S-1"
    assert sprint.id_proyecto == "P-1"
    
    # 2. Leer
    db_project = project_repo.get(db_session, id="P-1")
    assert db_project is not None
    assert len(db_project.sprints) == 1
    assert db_project.sprints[0].id_sprint == "S-1"
    
    # 3. Actualizar
    project_repo.update(db_session, db_obj=db_project, obj_in={"nombre": "Proyecto Renombrado"})
    updated_project = project_repo.get(db_session, id="P-1")
    assert updated_project.nombre == "Proyecto Renombrado"
    
    # 4. Eliminar
    project_repo.remove(db_session, id="P-1")
    assert project_repo.get(db_session, id="P-1") is None
    assert sprint_repo.get(db_session, id="S-1") is None  # Cascade delete verification


def test_issue_and_transitions_crud(db_session):
    """Verifica la persistencia de Issues y Transiciones, incluyendo relaciones."""
    # Crear Proyecto y Sprint dependientes
    project_repo.create(db_session, obj_in={"id_proyecto": "P-2", "key_proyecto": "KEY-2", "nombre": "Proj 2"})
    sprint_repo.create(db_session, obj_in={"id_sprint": "S-2", "id_proyecto": "P-2", "nombre": "Sprint 2", "estado": "active"})
    
    # 1. Crear Issue
    issue_in = {
        "id_jira": "ISS-99",
        "key_issue": "KEY-2-99",
        "id_proyecto": "P-2",
        "id_sprint": "S-2",
        "summary": "Implementar login",
        "status_actual": "In Progress",
        "story_points": 3.0,
        "created_at": datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc),
        "resolved_at": None
    }
    issue = issue_repo.create(db_session, obj_in=issue_in)
    assert issue.id_jira == "ISS-99"
    assert issue.story_points == 3.0
    
    # 2. Crear Transición
    trans_in = {
        "id_jira": "ISS-99",
        "estado_anterior": "To Do",
        "estado_nuevo": "In Progress",
        "fecha_cambio": datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    }
    transition = transition_repo.create(db_session, obj_in=trans_in)
    assert transition.id_transicion is not None
    assert transition.id_jira == "ISS-99"
    
    # 3. Leer relaciones
    db_issue = issue_repo.get(db_session, id="ISS-99")
    assert db_issue is not None
    assert len(db_issue.transiciones) == 1
    assert db_issue.transiciones[0].estado_nuevo == "In Progress"
    
    # 4. Eliminar transiciones de forma aislada
    transition_repo.delete_by_issue(db_session, issue_id="ISS-99")
    db_session.refresh(db_issue)
    assert len(db_issue.transiciones) == 0
