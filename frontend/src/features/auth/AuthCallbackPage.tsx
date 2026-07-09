import { useEffect, useState } from "react";

import { saveAccessToken } from "./authStorage";

type CallbackStatus = "processing" | "success" | "error";

export function AuthCallbackPage() {
  const [status, setStatus] = useState<CallbackStatus>("processing");
  const [message, setMessage] = useState("Validando respuesta de autenticación...");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (!token) {
      setStatus("error");
      setMessage("No recibimos un token de acceso desde el backend.");
      return;
    }

    saveAccessToken(token);
    window.history.replaceState({}, document.title, "/auth/callback");
    setStatus("success");
    setMessage("Autenticación exitosa. Redirigiendo al dashboard...");
    window.setTimeout(() => {
      window.location.assign("/dashboard");
    }, 700);
  }, []);

  return (
    <main className="auth-page">
      <section className="auth-card auth-card-centered">
        <p className="eyebrow">MCHAV Analytics</p>
        <div className={`status-badge status-${status}`}>
          {status === "success" ? "Autenticado" : status === "error" ? "Revisar acceso" : "Procesando"}
        </div>
        <h2>{status === "success" ? "Login completado" : "Callback de autenticación"}</h2>
        <p className={status === "error" ? "error-message" : "description"}>{message}</p>
        <a className="secondary-link" href="/dashboard">
          Ir al dashboard
        </a>
      </section>
    </main>
  );
}
