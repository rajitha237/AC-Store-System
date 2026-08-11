from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


INSECURE_JWT_SECRETS = {
    "",
    "change-this-secret-key",
    "REPLACE_WITH_SECURE_RANDOM_SECRET",
}

INSECURE_ADMIN_PASSWORDS = {
    "",
    "Admin@12345",
    "REPLACE_WITH_STRONG_UNIQUE_PASSWORD",
}


class Settings(BaseSettings):
    app_name: str = "AC Store Management System"
    app_version: str = "0.2.0"

    environment: str = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    database_url: str = (
        "sqlite+aiosqlite:///./ac_store.db"
    )

    startup_seed_enabled: bool = True
    startup_create_admin_enabled: bool = True

    # Development/test fallbacks are retained temporarily
    # for local compatibility. Production validation below
    # rejects all known insecure values.
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    initial_admin_username: str = "admin"
    initial_admin_email: str = "admin@acstore.local"
    initial_admin_password: str = "Admin@12345"
    initial_admin_full_name: str = (
        "System Administrator"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return (
            self.environment.strip().lower()
            == "production"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_security(
        self,
    ) -> "Settings":
        environment = (
            self.environment
            .strip()
            .lower()
        )

        if environment != "production":
            return self

        errors: list[str] = []

        jwt_secret = (
            self.jwt_secret_key.strip()
        )

        admin_password = (
            self.initial_admin_password.strip()
        )

        if jwt_secret in INSECURE_JWT_SECRETS:
            errors.append(
                "JWT_SECRET_KEY must be explicitly "
                "configured with a secure value in "
                "production"
            )
        elif len(jwt_secret) < 32:
            errors.append(
                "JWT_SECRET_KEY must contain at least "
                "32 characters in production"
            )

        if (
            admin_password
            in INSECURE_ADMIN_PASSWORDS
        ):
            errors.append(
                "INITIAL_ADMIN_PASSWORD must be "
                "explicitly configured with a secure "
                "value in production"
            )
        elif len(admin_password) < 12:
            errors.append(
                "INITIAL_ADMIN_PASSWORD must contain "
                "at least 12 characters in production"
            )

        if self.debug:
            errors.append(
                "DEBUG must be false in production"
            )

        if self.startup_seed_enabled:
            errors.append(
                "STARTUP_SEED_ENABLED must be false "
                "in production"
            )

        if self.startup_create_admin_enabled:
            errors.append(
                "STARTUP_CREATE_ADMIN_ENABLED must be "
                "false in production"
            )

        if errors:
            raise ValueError(
                "Unsafe production configuration: "
                + "; ".join(errors)
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
