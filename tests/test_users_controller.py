import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.api.v1.controllers.users_controller import (
    _verify_admin,
    list_users,
    list_roles,
    update_user_status,
    update_user_role,
    get_user_projects,
    assign_user_projects,
    get_user_logs,
    UserStatusPayload,
    UserRolePayload,
    UserProjectsPayload
)
import app.models as models
from app.models.audit import AuditLog

def test_verify_admin():
    admin = MagicMock(rol=MagicMock(nombre_rol="Administrador"))
    _verify_admin(admin) # Should not raise

    non_admin = MagicMock(rol=MagicMock(nombre_rol="Desarrollador"))
    with pytest.raises(HTTPException) as exc:
        _verify_admin(non_admin)
    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_list_users_and_roles():
    mock_db = MagicMock()
    admin = MagicMock(rol=MagicMock(nombre_rol="Administrador"))
    
    u1 = MagicMock(id_usuario=1, email="a@a.com", nombre="User 1", id_rol=1, activo=True, proyectos_asignados=[], rol=MagicMock(nombre_rol="Admin"))
    mock_db.query.return_value.all.return_value = [u1]
    
    users = await list_users(db=mock_db, current_user=admin)
    assert len(users) == 1
    assert users[0]["id_usuario"] == 1

    roles = await list_roles(db=mock_db, current_user=admin)
    assert roles == [u1]

@pytest.mark.asyncio
async def test_update_user_status():
    mock_db = MagicMock()
    admin = MagicMock(id_usuario=1, rol=MagicMock(nombre_rol="Administrador"))
    
    # 1. Admin deactivating self
    with pytest.raises(HTTPException) as exc:
        await update_user_status(1, UserStatusPayload(activo=False), db=mock_db, current_user=admin)
    assert exc.value.status_code == 400

    # 2. Target user not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc404:
        await update_user_status(2, UserStatusPayload(activo=False), db=mock_db, current_user=admin)
    assert exc404.value.status_code == 404

    # 3. Success
    target = MagicMock(id_usuario=2, email="u2@test.com", activo=True)
    mock_db.query.return_value.filter.return_value.first.return_value = target
    res = await update_user_status(2, UserStatusPayload(activo=False), db=mock_db, current_user=admin)
    assert res["status"] == "success"
    assert target.activo is False

@pytest.mark.asyncio
async def test_update_user_role():
    mock_db = MagicMock()
    admin = MagicMock(id_usuario=1, rol=MagicMock(nombre_rol="Administrador"))
    target = MagicMock(id_usuario=2, email="u2@test.com", id_rol=1)
    role_obj = MagicMock(id_rol=2, nombre_rol="Planificador")

    # Success by name
    def query_handler(model):
        m = MagicMock()
        if model == models.User:
            m.filter.return_value.first.return_value = target
        elif model == models.Role:
            m.filter.return_value.first.return_value = role_obj
        return m

    mock_db.query.side_effect = query_handler
    
    res = await update_user_role(2, UserRolePayload(role="LIDER"), db=mock_db, current_user=admin)
    assert res["status"] == "success"
    assert target.id_rol == 2

@pytest.mark.asyncio
async def test_get_and_assign_user_projects():
    mock_db = MagicMock()
    admin = MagicMock(id_usuario=1, rol=MagicMock(nombre_rol="Administrador"))
    target = MagicMock(id_usuario=2, email="u2@test.com", proyectos_asignados=[MagicMock(id_proyecto="P1")])

    def query_handler(model):
        m = MagicMock()
        if model == models.User:
            m.filter.return_value.first.return_value = target
        elif model == models.Proyecto:
            m.filter.return_value.first.return_value = MagicMock()
        return m

    mock_db.query.side_effect = query_handler

    # Get
    p_info = await get_user_projects(2, db=mock_db, current_user=admin)
    assert p_info["proyectos"] == ["P1"]

    # Assign
    res_assign = await assign_user_projects(2, UserProjectsPayload(id_proyectos=["P1", "P2"]), db=mock_db, current_user=admin)
    assert res_assign["status"] == "success"

def test_get_user_logs():
    mock_db = MagicMock()
    admin = MagicMock(id_usuario=1, rol=MagicMock(nombre_rol="Administrador"))
    target = MagicMock(id_usuario=2, email="u2@test.com")

    def query_handler(model):
        m = MagicMock()
        if model == models.User:
            m.filter.return_value.first.return_value = target
        elif model == AuditLog:
            m.filter.return_value.order_by.return_value.all.return_value = ["log1"]
        return m

    mock_db.query.side_effect = query_handler

    logs = get_user_logs(2, db=mock_db, current_user=admin)
    assert logs == ["log1"]
