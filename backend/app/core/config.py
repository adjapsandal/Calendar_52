from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    SECRET_KEY: str
    JWT_LIFETIME_SECONDS: int = 2592000
    ANTHROPIC_API_KEY: str = "sk-hub-U3sMqao3itYnhRsO787Mbj2jiVFhv2U2"
    ANTHROPIC_BASE_URL: str = "https://api.claudehub.fun"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
