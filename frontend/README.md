# MCHAV Frontend

Frontend inicial para el acceso con Jira de MCHAV Analytics.

## Estructura

```text
frontend/
  public/              # assets estáticos (logo, favicon)
  src/
    features/auth/     # pantallas y lógica de login
    App.tsx            # enrutamiento simple por path
    main.tsx           # entry point
    styles.css         # estilos globales
  index.html
  package.json
  vite.config.ts
  tsconfig.json
```

Los archivos `*.tsbuildinfo`, `vite.config.js` y `dist/` son generados al compilar y no deben versionarse.

## Flujo implementado

1. La pantalla principal muestra el botón `Ingresar con Jira`.
2. El frontend llama a `GET /api/auth/login`.
3. El backend devuelve `auth_url`.
4. El navegador redirige a Atlassian.
5. Atlassian vuelve al backend en `/api/auth/callback`.
6. El backend valida OAuth y redirige a `/auth/callback?token=<jwt>`.
7. El frontend guarda el token en `sessionStorage`.

## Ejecutar en desarrollo

```bash
npm install
npm run dev
```

La app corre en `http://localhost:3000` y usa proxy hacia el backend en `http://localhost:8080`.

## Nota de seguridad

El token en query string es una solución práctica para desarrollo. Para producción se recomienda que el backend entregue la sesión en cookie segura `HttpOnly`, `Secure` y `SameSite=Lax`.
