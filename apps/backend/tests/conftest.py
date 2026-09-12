import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.main import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Migration tests target a real PostgreSQL (the schema uses INET/JSONB/TIMESTAMPTZ
# and gen_random_uuid()). Start one with:
#   docker run -d --name reunionai-test-pg \
#     -e POSTGRES_USER=reunionai -e POSTGRES_PASSWORD=reunionai -e POSTGRES_DB=reunionai \
#     -p 5433:5432 postgres:16-alpine
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def alembic_cfg() -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    cfg.set_main_option("prepend_sys_path", str(BACKEND_ROOT))
    return cfg


@pytest.fixture(scope="session")
def migrated_engine(alembic_cfg: Config) -> Iterator[AsyncEngine]:
    """Migrate the test database to ``head`` and expose an async engine."""
    command.upgrade(alembic_cfg, "head")
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    yield engine
    command.downgrade(alembic_cfg, "base")


def generate_rsa_keypair() -> tuple[str, str]:
    """Return ``(private_pem, public_pem)`` for an ephemeral 2048-bit RSA key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture(scope="session")
def rsa_keys() -> tuple[str, str]:
    """Primary RS256 keypair shared across security/dependency tests."""
    return generate_rsa_keypair()


@pytest.fixture(scope="session")
def rsa_keys_other() -> tuple[str, str]:
    """A distinct RS256 keypair used to prove wrong-key rejection."""
    return generate_rsa_keypair()
