# Arquitectura de Seguridad: HMAC vs JWT 🔐

En MCHAV Analytics, la seguridad de la información y la autenticación se gestionan mediante un sistema moderno e híbrido: **Cookies de Sesión Firmadas por HMAC (Hash-based Message Authentication Code)**, conectado directamente al flujo de OAuth2 de Atlassian Jira.

No utilizamos Autenticación Básica (usuario/contraseña en cada petición) ni JWT (JSON Web Tokens) puros. A continuación, se explica cómo funciona nuestro mecanismo y la justificación técnica de esta decisión de diseño.

---

## 🛠️ ¿Cómo funciona nuestra Autenticación (HMAC)?

El código principal que maneja esto vive en `app/core/security.py`. El ciclo de vida de una sesión es el siguiente:

1. **Autenticación Delegada (OAuth2):** El usuario hace clic en "Iniciar sesión con Jira". Es Atlassian (no nuestro servidor) quien valida las credenciales y el 2FA. Atlassian nos devuelve un *Access Token*.
2. **Generación de la Firma (HMAC):** Una vez que verificamos la identidad del usuario, nuestro backend toma su ID (por ejemplo, `5`) y lo "firma" matemáticamente combinándolo con nuestra llave maestra (`SESSION_SECRET_KEY`) mediante el algoritmo criptográfico **SHA-256**.
3. **El Token de Sesión:** El resultado es un string concatenado: `5.a94a8fe5ccb19ba61c4c08...` (El ID del usuario seguido de la firma incopiable).
4. **Entrega Vía Cookie:** Este string se inyecta en el navegador del usuario a través de una cookie segura llamada `session_id`.
5. **Validación (Stateless):** En peticiones futuras, FastAPI lee la cookie, extrae el número `5`, vuelve a calcular la firma matemática y la compara. Si coinciden, la petición pasa. Si alguien intentó cambiar el `5` por un `6`, la matemática falla y la petición es rechazada (`401 Unauthorized`).

---

## ⚖️ Justificación Técnica: ¿Por qué HMAC y no JWT?

Aunque JWT (JSON Web Tokens) es el estándar de facto en muchas aplicaciones SPA (Single Page Applications), para el caso de uso específico de MCHAV Analytics, HMAC presenta ventajas significativas:

### 1. Minimalismo y Tamaño de Carga (Payload)
* **JWT:** Un token JWT contiene un Header, un Payload (que puede incluir roles, correos, nombres) y una Firma, todo codificado en Base64. Esto resulta en strings muy largos que consumen ancho de banda en cada petición HTTP.
* **HMAC:** Nuestro token solo contiene `[ID_Usuario].[Firma_SHA256]`. Es extremadamente ligero, lo que mejora la latencia de las peticiones de red al dashboard.

### 2. Prevención de Robo (XSS)
* **JWT:** Típicamente, los desarrolladores de frontend guardan los JWT en `localStorage` o `sessionStorage`. Esto hace que el token sea vulnerable a ataques **XSS (Cross-Site Scripting)**, donde un script malicioso en la página web puede robar el token y enviarlo a un servidor atacante.
* **HMAC (con Cookies HTTP-Only):** Nuestro sistema envía el boleto firmado a través de cookies configuradas como HTTP-Only. Esto significa que el código JavaScript (ni el bueno, ni el malicioso) puede leer o robar el contenido de la cookie. El navegador la adjunta automáticamente en cada petición de forma segura.

### 3. Velocidad y Stateless (Sin Estado)
Ambos sistemas (JWT y HMAC) comparten la ventaja de ser "Stateless" (no obligan a la base de datos a buscar la sesión en cada clic, lo cual ahorra muchísimos recursos). Sin embargo, verificar una firma HMAC simple (usando `hmac.compare_digest`) toma fracciones de milisegundo menos que decodificar y validar un JSON en Base64 de un JWT clásico.

### 4. Simplicidad de Revocación
Al no empaquetar fechas de expiración complejas dentro de un Payload como lo hace JWT, nuestra sesión está intrínsecamente vinculada a la existencia del usuario en nuestra tabla local y la vigencia del token de Atlassian. Si deseamos invalidar todas las sesiones globalmente ante una brecha de seguridad, basta con cambiar la constante `SESSION_SECRET_KEY` en nuestro archivo `.env`; todas las firmas previas se romperán instantáneamente.

---

### 🎯 Conclusión
El sistema HMAC implementado ofrece la **escalabilidad** de un sistema sin estado (al igual que JWT), pero con un **perfil de seguridad más estricto** frente a ataques de inyección de scripts (XSS) y un **rendimiento superior** debido al bajo peso del token de sesión en la cabecera HTTP.
