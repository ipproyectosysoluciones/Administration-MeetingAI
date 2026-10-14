"""#115: dos drafts concurrentes no deben colisionar en `version` para una meeting."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.minutes.conftest import api, register_admin, seed_meeting


async def _post_draft(app: FastAPI, meeting_id: uuid.UUID, token: str) -> int:
    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/minutes",
        json={"title": "Acta junta", "content": "c"},
        token=token,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["version"]


async def test_concurrent_drafts_versions_unique(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    versions = await asyncio.gather(*[_post_draft(app, meeting_id, token) for _ in range(4)])
    assert len(set(versions)) == 4, f"race: {versions}"
