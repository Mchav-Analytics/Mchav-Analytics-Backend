import { NavLink, Outlet } from "react-router-dom";

import { logout } from "../../features/auth/authApi";

export function AppLayout() {
  async function handleLogout() {
    await logout();
    window.location.assign("/");
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar__brand">
          <img src="/mchav-logo.png" alt="MCHAV Analytics" />
          <div>
            <strong>MCHAV</strong>
            <span>Analytics</span>
          </div>
        </div>
        <nav className="app-sidebar__nav">
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
        </nav>
        <button type="button" className="app-sidebar__logout" onClick={handleLogout}>
          Cerrar sesión
        </button>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div>
            <p className="app-topbar__eyebrow">Capa intermedia Jira</p>
            <h1>Métricas y calidad operativa</h1>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
