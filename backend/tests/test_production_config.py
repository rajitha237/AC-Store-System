import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(
    **overrides,
) -> Settings:
    values = {
        "environment":
            "production",
        "debug":
            False,
        "jwt_secret_key":
            (
                "production-jwt-secret-"
                "0123456789abcdef0123456789abcdef"
            ),
        "initial_admin_password":
            "StrongAdminPassword!2026",
        "startup_seed_enabled":
            False,
        "startup_create_admin_enabled":
            False,
    }

    values.update(overrides)

    return Settings(
        _env_file=None,
        **values,
    )


def test_secure_production_configuration_accepted():
    settings = production_settings()

    assert settings.environment == "production"
    assert settings.debug is False
    assert len(settings.jwt_secret_key) >= 32
    assert (
        len(settings.initial_admin_password)
        >= 12
    )


@pytest.mark.parametrize(
    "jwt_secret",
    [
        "",
        "change-this-secret-key",
        "REPLACE_WITH_SECURE_RANDOM_SECRET",
        "too-short",
    ],
)
def test_insecure_production_jwt_secret_rejected(
    jwt_secret,
):
    with pytest.raises(
        ValidationError,
        match="JWT_SECRET_KEY",
    ):
        production_settings(
            jwt_secret_key=jwt_secret,
        )


@pytest.mark.parametrize(
    "password",
    [
        "",
        "Admin@12345",
        "REPLACE_WITH_STRONG_UNIQUE_PASSWORD",
        "Short123!",
    ],
)
def test_insecure_production_admin_password_rejected(
    password,
):
    with pytest.raises(
        ValidationError,
        match="INITIAL_ADMIN_PASSWORD",
    ):
        production_settings(
            initial_admin_password=password,
        )


def test_production_debug_true_rejected():
    with pytest.raises(
        ValidationError,
        match="DEBUG must be false",
    ):
        production_settings(
            debug=True,
        )


def test_development_mode_remains_compatible():
    settings = Settings(
        _env_file=None,
        environment="development",
        debug=True,
        jwt_secret_key="change-this-secret-key",
        initial_admin_password="Admin@12345",
    )

    assert settings.environment == "development"
    assert settings.debug is True


def test_test_environment_remains_compatible():
    settings = Settings(
        _env_file=None,
        environment="test",
        debug=False,
        jwt_secret_key="test-secret",
        initial_admin_password="test-password",
    )

    assert settings.environment == "test"
