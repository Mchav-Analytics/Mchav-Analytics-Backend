import pytest
from unittest.mock import MagicMock
from app.models.auth import Role, User
from app.models.jira import Proyecto, Sprint, Issue, TransicionEstadoIssue
from app.models.metrics import LogsSincronizacion, KpisHistoricos
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, transition_repo, mapping_repo, kpi_repo, log_repo
from app.repositories.base import CRUDBase

def test_propiedad_permisos_scopes_del_rol():
    """Verifica que la propiedad Role.scopes_list parsee correctamente la cadena de scopes."""
    role = Role(scopes="jira:read, jira:sync , projects:write ")
    assert role.scopes_list == ["jira:read", "jira:sync", "projects:write"]
    
    empty_role = Role(scopes="")
    assert empty_role.scopes_list == []

def test_repositorio_usuario_obtener_por_cuenta_jira():
    """Verifica la consulta de usuario por jira_account_id."""
    mock_db = MagicMock()
    mock_user = User(id_usuario=1, jira_account_id="acc_99")
    mock_db.query().filter().first.return_value = mock_user
    
    u = user_repo.get_by_jira_account_id(mock_db, "acc_99")
    assert u.id_usuario == 1
    assert u.jira_account_id == "acc_99"

def test_repositorio_mapeo_eliminar_por_proyecto():
    """Verifica la eliminación de mapeos de un proyecto."""
    mock_db = MagicMock()
    mapping_repo.delete_by_project(mock_db, "PROJ-1")
    mock_db.query().filter().delete.assert_called_once()
    mock_db.commit.assert_called_once()

def test_repositorio_proyectos_obtener_por_clave():
    """Verifica los métodos del repositorio de proyectos."""
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = Proyecto(id_proyecto="1", key_proyecto="P1")
    
    p = project_repo.get_by_key(mock_db, "P1")
    assert p.key_proyecto == "P1"

def test_repositorio_sprints_obtener_por_id():
    """Verifica los métodos del repositorio de sprints."""
    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = Sprint(id_sprint="100", id_proyecto="1")
    
    s = sprint_repo.get_by_id_sprint(mock_db, "100")
    assert s.id_sprint == "100"

def test_repositorio_tickets_obtener_estados_unicos():
    """Verifica la consulta de estados únicos por proyecto en issue_repo."""
    mock_db = MagicMock()
    mock_db.query().filter().distinct().all.return_value = [("To Do",), ("In Progress",), ("Done",)]
    
    statuses = issue_repo.get_distinct_statuses_by_project(mock_db, "PROJ-1")
    assert len(statuses) == 3

def test_repositorio_transiciones_eliminar_por_ticket():
    """Verifica la eliminación de transiciones previas de un ticket."""
    mock_db = MagicMock()
    transition_repo.delete_by_issue(mock_db, "10001")
    mock_db.query().filter().delete.assert_called_once()

def test_repositorio_logs_obtener_recientes():
    """Verifica la consulta paginada de logs de auditoría."""
    mock_db = MagicMock()
    mock_db.query().order_by().offset().limit().all.return_value = [LogsSincronizacion(id_log=1)]
    
    logs = log_repo.get_recent(mock_db, skip=0, limit=10)
    assert len(logs) == 1

def test_repositorio_sprints_obtener_por_proyecto():
    """Verifica la consulta de sprints ordenados por proyecto."""
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [Sprint(id_sprint="10")]
    
    sprints = sprint_repo.get_by_project(mock_db, "PROJ-1")
    assert len(sprints) == 1

def test_repositorio_transiciones_obtener_estados_distintos():
    """Verifica las consultas de estados distintos en el historial de transiciones."""
    mock_db = MagicMock()
    mock_db.query().join().filter().distinct().all.return_value = [("In Progress",)]
    
    statuses_new = transition_repo.get_distinct_new_statuses_by_project(mock_db, "PROJ-1")
    statuses_prev = transition_repo.get_distinct_prev_statuses_by_project(mock_db, "PROJ-1")
    
    assert len(statuses_new) == 1
    assert len(statuses_prev) == 1

def test_repositorio_kpi_obtener_historial_proyecto():
    """Verifica la consulta del historial de KPIs por proyecto."""
    mock_db = MagicMock()
    kpi_repo.get_all_by_project(mock_db, "PROJ-1")
    mock_db.query().filter.assert_called_once()

def test_operaciones_base_repositorio_crud():
    """Verifica los métodos genéricos de la clase CRUDBase (create, update, remove, get_multi)."""
    crud = CRUDBase(Proyecto)
    mock_db = MagicMock()
    
    mock_db.query().offset().limit().all.return_value = [Proyecto(id_proyecto="1")]
    res = crud.get_multi(mock_db, skip=0, limit=10)
    assert len(res) == 1
    
    crud.create(mock_db, obj_in={"id_proyecto": "2", "key_proyecto": "P2", "nombre": "P2"})
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    mock_db.query().get.return_value = Proyecto(id_proyecto="2")
    crud.remove(mock_db, id="2")
    mock_db.delete.assert_called_once()
