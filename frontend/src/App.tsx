import { AuthCallbackPage } from "./features/auth/AuthCallbackPage";
import { getAccessToken } from "./features/auth/authStorage";
import { LoginPage } from "./features/auth/LoginPage";

export function App() {
  const path = window.location.pathname;

  if (path === "/auth/callback") {
    return <AuthCallbackPage />;
  }

  const token = getAccessToken();

  if (token) {
    return (
      <main className="auth-page">
        <section className="auth-card auth-card-centered">
          <p className="eyebrow">MCHAV Analytics</p>
          <div className="status-badge status-success">Sesión lista</div>
          <h2>Sesión activa</h2>
          <p className="description">
            El token quedó guardado en sesión del navegador. La siguiente fase puede
            construir el dashboard o consumir endpoints protegidos.
          </p>
          <a className="secondary-link" href="/auth/callback">
            Ver estado del login
          </a>
        </section>
      </main>
    );
  }

  return <LoginPage />;
}
