"""Datos iniciales para roles, KPIs y usuario administrador."""

from sqlalchemy.orm import Session

from app.features.jira.models import KpiType, Role, User
from app.services.kpi import DEFAULT_KPI_TYPES


def seed_roles(db: Session) -> None:
    defaults = (
        ("Administrador", "Acceso total a configuración y sincronización"),
        ("Consultor", "Acceso de lectura a métricas y proyectos"),
    )
    for name, description in defaults:
        if db.query(Role).filter(Role.name == name).first():
            continue
        db.add(Role(name=name, description=description))
    db.commit()


def seed_kpi_types(db: Session) -> None:
    for name, description, unit in DEFAULT_KPI_TYPES:
        if db.query(KpiType).filter(KpiType.name == name).first():
            continue
        db.add(KpiType(name=name, description=description, unit=unit))
    db.commit()


def seed_admin_user(db: Session, email: str, full_name: str) -> None:
    admin_role = db.query(Role).filter(Role.name == "Administrador").first()
    if not admin_role:
        raise RuntimeError("Debes ejecutar seed_roles antes de seed_admin_user")

    user = db.query(User).filter(User.email == email).first()
    if user:
        return

    db.add(
        User(
            email=email,
            full_name=full_name,
            status="active",
            id_role=admin_role.id_role,
        )
    )
    db.commit()


def run_all(db: Session, admin_email: str, admin_name: str) -> None:
    seed_roles(db)
    seed_kpi_types(db)
    seed_admin_user(db, email=admin_email, full_name=admin_name)
