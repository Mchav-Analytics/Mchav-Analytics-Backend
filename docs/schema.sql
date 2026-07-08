-- ===========================================================================
-- SCRIPT DE CREACIÓN DE BASE DE DATOS - MCHAV-ANALYTICS
-- PROYECTO PARA GRUPO ASD S.A.S. - CÉLULA DE DESARROLLO 9B
-- FECHA: JULIO 2026
-- ESTÁNDAR: PostgreSQL 14+
-- ===========================================================================

-- 1. EXTENSIONES
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================================================
-- ÉPICA 01: AUTENTICACIÓN, SEGURIDAD Y GESTIÓN DE USUARIOS (RBAC)
-- ===========================================================================

CREATE TABLE roles (
    id_rol SERIAL PRIMARY KEY,
    nombre_rol VARCHAR(50) NOT NULL UNIQUE
);

-- Tabla adaptada para soportar tanto los datos de la app como los tokens de Jira
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    email VARCHAR(150) UNIQUE, -- Puede ser NULL hasta que traigamos su perfil de Jira
    nombre VARCHAR(150),       -- Puede ser NULL hasta que traigamos su perfil de Jira
    id_rol INT,                -- Puede ser NULL por defecto hasta asignar rol
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Campos requeridos para integración OAuth 2.0 (Jira)
    jira_account_id VARCHAR(100) UNIQUE,
    access_token TEXT,
    refresh_token TEXT,
    cloud_id VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuarios_roles FOREIGN KEY (id_rol) REFERENCES roles(id_rol) ON DELETE RESTRICT
);

-- ===========================================================================
-- ENTIDADES CORE EXTRAÍDAS DESDE JIRA (ÉPICA 02)
-- ===========================================================================

CREATE TABLE proyectos (
    id_proyecto VARCHAR(50) PRIMARY KEY,
    key_proyecto VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    estado VARCHAR(50) DEFAULT 'Active'
);

CREATE TABLE sprints (
    id_sprint VARCHAR(50) PRIMARY KEY,
    id_proyecto VARCHAR(50) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    fecha_inicio TIMESTAMP WITH TIME ZONE,
    fecha_fin TIMESTAMP WITH TIME ZONE,
    fecha_finalizacion TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_sprints_proyectos FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto) ON DELETE CASCADE
);

CREATE TABLE issues (
    id_jira VARCHAR(50) PRIMARY KEY,
    key_issue VARCHAR(30) NOT NULL UNIQUE,
    id_proyecto VARCHAR(50) NOT NULL,
    id_sprint VARCHAR(50),
    summary TEXT NOT NULL,
    status_actual VARCHAR(50) NOT NULL,
    story_points NUMERIC(5, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_issues_proyectos FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto) ON DELETE CASCADE,
    CONSTRAINT fk_issues_sprints FOREIGN KEY (id_sprint) REFERENCES sprints(id_sprint) ON DELETE SET NULL
);

-- Tabla intermedia opcional (issues_sprints) por si un ticket pasa por varios sprints
CREATE TABLE issues_sprints (
    id_jira VARCHAR(50) NOT NULL,
    id_sprint VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_jira, id_sprint),
    CONSTRAINT fk_is_issues FOREIGN KEY (id_jira) REFERENCES issues(id_jira) ON DELETE CASCADE,
    CONSTRAINT fk_is_sprints FOREIGN KEY (id_sprint) REFERENCES sprints(id_sprint) ON DELETE CASCADE
);

CREATE TABLE transiciones_estado_issue (
    id_transicion SERIAL PRIMARY KEY,
    id_jira VARCHAR(50) NOT NULL,
    estado_anterior VARCHAR(50),
    estado_nuevo VARCHAR(50) NOT NULL,
    fecha_cambio TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT fk_transiciones_issues FOREIGN KEY (id_jira) REFERENCES issues(id_jira) ON DELETE CASCADE
);

-- ===========================================================================
-- ÉPICA 03: MOTOR DE PROCESAMIENTO Y HISTÓRICOS DE KPIs
-- ===========================================================================

CREATE TABLE kpis_historicos (
    id_kpi SERIAL PRIMARY KEY,
    id_proyecto VARCHAR(50) NOT NULL,
    id_sprint VARCHAR(50),
    fecha_calculo TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    velocity_total_sp NUMERIC(10, 2) DEFAULT 0.00,
    velocity_promedio_historico NUMERIC(10, 2) DEFAULT 0.00,
    throughput_issues INT DEFAULT 0,
    lead_time_promedio_dias NUMERIC(8, 2) DEFAULT 0.00,
    cycle_time_promedio_dias NUMERIC(8, 2) DEFAULT 0.00,
    CONSTRAINT fk_kpis_proyectos FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto) ON DELETE CASCADE,
    CONSTRAINT fk_kpis_sprints FOREIGN KEY (id_sprint) REFERENCES sprints(id_sprint) ON DELETE SET NULL
);

-- ===========================================================================
-- ÉPICA 05 Y 06: LOGS, AUDITORÍA Y AUTOMATIZACIÓN
-- ===========================================================================

CREATE TABLE logs_sincronizacion (
    id_log SERIAL PRIMARY KEY,
    fecha_ejecucion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tipo_sincronizacion VARCHAR(50) NOT NULL,
    resultado VARCHAR(20) NOT NULL,
    tiempo_ejecucion_segundos INT NOT NULL,
    issues_procesados INT DEFAULT 0,
    detalle_error TEXT,
    ejecutado_por VARCHAR(100) DEFAULT 'SYSTEM_WORKER'
);

-- ===========================================================================
-- 2. CREACIÓN DE ÍNDICES ESTRATÉGICOS
-- ===========================================================================
CREATE INDEX idx_issues_proyecto_status ON issues(id_proyecto, status_actual);
CREATE INDEX idx_issues_sprint ON issues(id_sprint);
CREATE INDEX idx_transiciones_issue_fecha ON transiciones_estado_issue(id_jira, fecha_cambio);
CREATE INDEX idx_kpis_proyecto_fecha ON kpis_historicos(id_proyecto, fecha_calculo);
CREATE INDEX idx_logs_fecha ON logs_sincronizacion(fecha_ejecucion DESC);

-- ===========================================================================
-- 3. DATA SEEDING (Inserciones Iniciales)
-- ===========================================================================
INSERT INTO roles (nombre_rol) VALUES 
('Administrador'),
('Manager'),
('Developer')
ON CONFLICT (nombre_rol) DO NOTHING;
