from app.core.config import Settings


def test_settings_defaults_match_architecture_section_10_1():
    settings = Settings(_env_file=None)

    # Core
    assert settings.app_env == "development"
    assert settings.app_host == "0.0.0.0"
    assert settings.app_port == 8000
    assert settings.jwt_access_ttl_minutes == 15
    assert settings.refresh_ttl_days == 30
    assert settings.refresh_grace_seconds == 30
    assert settings.argon2_memory_cost == 65536
    assert settings.argon2_time_cost == 3
    assert settings.argon2_parallelism == 4

    # Rate limiting
    assert settings.rate_limit_login_ip == 5
    assert settings.rate_limit_login_user == 20
    assert settings.rate_limit_register_ip == 3
    assert settings.rate_limit_refresh_ip == 30
    assert settings.rate_limit_refresh_user == 60
    assert settings.rate_limit_mfa_ip == 10
    assert settings.rate_limit_mfa_user == 20

    # CORS
    assert settings.cors_allow_origins_list == [
        "http://localhost:3000",
        "http://localhost:4321",
    ]

    # Bootstrap
    assert settings.bootstrap_superadmin_email == "admin@reunionai.local"

    # Frontend
    assert settings.frontend_url == "http://localhost:4321"


def test_settings_load_overrides_from_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/reunionai")
    monkeypatch.setenv("JWT_ACCESS_TTL_MINUTES", "7")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_IP", "99")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.database_url == "postgresql+asyncpg://u:p@db/reunionai"
    assert settings.jwt_access_ttl_minutes == 7
    assert settings.rate_limit_login_ip == 99
