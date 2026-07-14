from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Configuración de Base de Datos
    DB_USER: str = "mchav"
    DB_PASSWORD: str = "mchav123"
    DB_NAME: str = "mchav_db"
    DB_HOST: str = "postgres"
    DB_PORT: str = "5432"

    # Configuración de Jira (Acceso base)
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""

    # Nuevos campos para OAuth 2.0
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    JIRA_REDIRECT_URI: str = "http://localhost:8080/api/auth/callback"
    ALLOWED_EMAIL_DOMAIN: str = "grupoasd.com"

    # Configuración de aplicación
    ENV: str = "dev"
    FRONTEND_URL: str = "http://localhost:3000"
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-me"
    SESSION_SECRET_KEY: str = "dev-session-secret-change-me"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Configuración para leer el archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Instancia global para ser importada en los servicios
settings = Settings()