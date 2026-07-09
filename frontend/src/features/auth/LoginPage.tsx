import { useState } from "react";

import { requestJiraLogin } from "./authApi";

function LockIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="inline-icon">
      <path d="M7 10V8a5 5 0 0 1 10 0v2" />
      <path d="M6 10h12v10H6z" />
      <path d="M12 14v2" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="check-icon">
      <path d="M5 12.5l4.2 4.2L19 7" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="pill-icon">
      <path d="M3 7h7l2 2h9v9H3z" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="pill-icon">
      <path d="M5 5h14v15H5z" />
      <path d="M8 3v4M16 3v4M5 10h14" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="pill-icon">
      <path d="M5 19V9" />
      <path d="M12 19V5" />
      <path d="M19 19v-7" />
    </svg>
  );
}

type ConnectionStatus = "idle" | "loading" | "success" | "error";

export function LoginPage() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const isConnecting = connectionStatus === "loading" || connectionStatus === "success";

  async function handleLogin() {
    setConnectionStatus("loading");
    setError(null);

    try {
      const { auth_url } = await requestJiraLogin();
      setConnectionStatus("success");
      window.setTimeout(() => {
        window.location.assign(auth_url);
      }, 450);
    } catch {
      setError("No se pudo conectar, intenta de nuevo");
      setConnectionStatus("error");
    }
  }

  return (
    <main className="auth-page">
      <div className="rain-pattern" aria-hidden="true" />

      <section className="login-card" aria-label="Integración Jira MCHAV">
        <div className="logo-lockup">
          <img src="/mchav-logo.png" alt="Logo MCHAV Analytics" />
        </div>

        <h1>Conecta Jira</h1>
        <p className="description">
          Vincula tu espacio de trabajo para traer proyectos, sprints e indicadores a MCHAV.
        </p>

        <button
          className={`primary-button primary-button-${connectionStatus}`}
          type="button"
          onClick={handleLogin}
          disabled={isConnecting}
        >
          {connectionStatus === "loading" ? <span className="spinner" aria-hidden="true" /> : null}
          {connectionStatus === "success" ? <CheckIcon /> : null}
          {connectionStatus === "idle" || connectionStatus === "error" ? (
            <span className="button-icon">J</span>
          ) : null}
          {connectionStatus === "loading"
            ? "Conectando..."
            : connectionStatus === "success"
              ? "Conectado"
              : "Conectar con Jira"}
        </button>

        <p className="security-copy">
          <LockIcon />
          Conexión segura vía OAuth · Solo lectura de proyectos, sprints y métricas
        </p>

        <a className="privacy-link" href="/privacy">
          ¿Cómo usamos tus datos?
        </a>

        {error ? <p className="error-message">{error}</p> : null}

        <div className="quick-points" aria-label="Resumen de la integración">
          <span>
            <FolderIcon />
            Proyectos
          </span>
          <span>
            <CalendarIcon />
            Sprints
          </span>
          <span>
            <ChartIcon />
            Métricas
          </span>
        </div>
      </section>
    </main>
  );
}
