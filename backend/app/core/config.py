from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = frozenset(
    {
        "",
        "dev-jwt-secret-change-me",
        "dev-session-secret-change-me",
        "change-me-jwt",
        "change-me-session",
    }
)


class Settings(BaseSettings):
    PROJECT_NAME: str = "MCHAV Analytics Backend"
    VERSION: str = "1.2.0"
    API_V1_PREFIX: str = "/api"

    DB_USER: str = "mchav"
    DB_PASSWORD: str = "mchav123"
    DB_NAME: str = "mchav_db"
    DB_HOST: str = "postgres"
    DB_PORT: str = "5432"

    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_CLIENT_ID: str = ""
    JIRA_CLIENT_SECRET: str = ""
    JIRA_REDIRECT_URI: str = "http://localhost:8000/api/auth/oauth/callback"
    ALLOWED_EMAIL_DOMAIN: str = "grupoasd.com"

    JIRA_SPRINT_FIELD: str = "customfield_10020"
    JIRA_STORY_POINT_FIELDS: str = "customfield_10016,customfield_10002,storyPoints"

    ENV: str = "dev"
    # Orígenes CORS separados por coma (API-first, sin frontend embebido).
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    AUTH_RETURN_JSON: bool = True
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-me"
    SESSION_SECRET_KEY: str = "dev-session-secret-change-me"
    UVICORN_RELOAD: bool = True

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def story_point_field_names(self) -> tuple[str, ...]:
        return tuple(
            field.strip()
            for field in self.JIRA_STORY_POINT_FIELDS.split(",")
            if field.strip()
        )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.ENV != "prod":
            return self

        missing: list[str] = []
        if self.JWT_SECRET_KEY in _INSECURE_SECRETS:
            missing.append("JWT_SECRET_KEY")
        if self.SESSION_SECRET_KEY in _INSECURE_SECRETS:
            missing.append("SESSION_SECRET_KEY")
        if not self.DB_PASSWORD or self.DB_PASSWORD == "mchav123":
            missing.append("DB_PASSWORD")

        if missing:
            raise ValueError(
                f"Variables inseguras o sin configurar en producción: {', '.join(missing)}"
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
