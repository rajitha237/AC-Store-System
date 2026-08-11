from app.core.config import Settings


def test_default_cors_origins_are_local_only():
    settings = Settings(
        _env_file=None,
        environment="development",
    )

    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_cors_origins_are_configurable():
    settings = Settings(
        _env_file=None,
        environment="development",
        cors_origins=(
            "https://app.example.com,"
            "https://admin.example.com"
        ),
    )

    assert settings.cors_origin_list == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_environment_detection_is_normalized():
    settings = Settings(
        _env_file=None,
        environment=" Production ",
        debug=False,
        jwt_secret_key=(
            "secure-production-secret-"
            "0123456789abcdef0123456789abcdef"
        ),
        initial_admin_password=(
            "StrongAdminPassword!2026"
        ),
        startup_seed_enabled=False,
        startup_create_admin_enabled=False,
    )

    assert settings.is_production is True
