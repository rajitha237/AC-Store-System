import pytest
from pydantic import ValidationError

from app.core.config import Settings


def secure_production_settings(
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


def test_secure_production_startup_policy():
    settings = (
        secure_production_settings()
    )

    assert (
        settings.startup_seed_enabled
        is False
    )

    assert (
        settings
        .startup_create_admin_enabled
        is False
    )


def test_production_startup_seed_rejected():
    with pytest.raises(
        ValidationError,
        match=(
            "STARTUP_SEED_ENABLED "
            "must be false"
        ),
    ):
        secure_production_settings(
            startup_seed_enabled=True,
        )


def test_production_admin_bootstrap_rejected():
    with pytest.raises(
        ValidationError,
        match=(
            "STARTUP_CREATE_ADMIN_ENABLED "
            "must be false"
        ),
    ):
        secure_production_settings(
            startup_create_admin_enabled=True,
        )


def test_development_startup_defaults_preserved():
    settings = Settings(
        _env_file=None,
        environment="development",
    )

    assert (
        settings.startup_seed_enabled
        is True
    )

    assert (
        settings
        .startup_create_admin_enabled
        is True
    )


def test_test_environment_startup_defaults_preserved():
    settings = Settings(
        _env_file=None,
        environment="test",
    )

    assert (
        settings.startup_seed_enabled
        is True
    )

    assert (
        settings
        .startup_create_admin_enabled
        is True
    )
