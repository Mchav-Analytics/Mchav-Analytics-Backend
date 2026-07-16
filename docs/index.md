# 📚 Índice de Documentación - MCHAV Analytics

Este documento sirve como el índice principal de toda la documentación técnica, arquitectónica y de instalación del backend y frontend de **MCHAV Analytics**.

---

## ⚡ Arranque e Instalación Rápida
*   **[Guía de Instalación y Arranque (Local/Docker)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/GUIA_INSTALACION.md):** 
    Instrucciones detalladas paso a paso para desplegar el proyecto mediante el script automatizado local o de forma centralizada con **Docker Compose**.
*   **[Control de Versiones y Requisitos del Entorno](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/versionamiento_tecnologias.md):** 
    Matriz detallada de compatibilidad del sistema operativo, motores y dependencias de Node.js/Python requeridas.

---

## 🎓 Sustentaciones y Evaluaciones del Proyecto
*   **[Tutorial de Sustentación Pedagógica Completa](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/tutorial_sustentacion_completa.md):** 
    Explicación paso a paso de los conceptos matemáticos (Lead/Cycle Time), seguridad (HMAC), problemas de rendimiento resueltos (N+1 queries en SQL) y testing. Redactado de forma sumamente descriptiva.
*   **[Sustentación Técnica del Proyecto](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/sustentacion_proyecto.md):** 
    Resumen técnico quirúrgico y justificación de cómo se resolvió cada uno de los puntos del Syllabus del proyecto para las Fases 1 y 2.
*   **[Checklist de Entregables del Syllabus](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/analisis_entregables.md):** 
    Semáforo de cumplimiento detallado de los entregables del backend por semanas. **(Completado al 100% en verde 🟢)**.

---

## 📐 Lógica del Negocio, Métricas y Base de Datos
*   **[Mapeo de Datos de Jira](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/mapeo_datos_jira.md):** 
    Detalle de cómo se mapean los objetos JSON y campos personalizados de Atlassian Jira Cloud a las tablas relacionales de nuestra base de datos.
*   **[Análisis de Caché en el Backend](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/cache_analysis.md):** 
    Análisis de la arquitectura de caché en memoria local, seguridad multiusuario y su aplicación en la API.
*   **[Tutorial de Swagger y Conexión de API](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/swagger_jira_tutorial.md):** 
    Guía interactiva para realizar pruebas manuales del API REST utilizando la interfaz autogenerada de Swagger OpenAPI.

---

## 🔒 Seguridad y Control de Accesos
*   **[Autenticación con HMAC (Firmado de Cookies)](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/autenticacion_hmac.md):** 
    Análisis profundo del esquema de seguridad stateless mediante firmado criptográfico de cookies con HMAC SHA-256 para prevenir ataques de secuestro de sesión y suplantación de ID.
*   **[Seguridad de Endpoints vs Middleware](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/seguridad_endpoints_vs_middleware.md):** 
    Comparativa de las metodologías aplicadas en el backend para la autorización de llamadas a las APIs.

---

## 🏗️ Arquitectura y Estructura
*   **[Documentación Técnica General del Backend](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/technical_documentation.md):** 
    Manual del arquitecto con el flujo macro de información, capas lógicas y diagramas de componentes.
*   **[Controladores vs Servicios](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/controladores_vs_servicios.md):** 
    Guía sobre la separación de responsabilidades entre enrutadores FastAPI y servicios de negocio.
*   **[Estructura de Directorios](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Backend/docs/estructura_directorios.md):** 
    Organización física de archivos del código base.
*   **[Guía de la Arquitectura del Frontend](file:///c:/Users/msalamanca/Desktop/Proyecto%20Mchav/Mchav-Frontend/README.md):** 
    Manual de estructura y consumo de APIs de la interfaz React + Vite.
