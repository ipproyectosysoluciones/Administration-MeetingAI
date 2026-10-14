"""Documents REST router (TASK-350).

Tenant scoping is resolved server-side from the verified identity (never from a
client-supplied tenant). All uploads/downloads audit-logged.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthContext, get_db, require_permission
from app.core.exceptions import APIError
from app.modules.documents.schemas import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentVersionCreateRequest,
    DocumentVersionListResponse,
    DocumentVersionResponse,
)
from app.modules.documents.service import DocumentService

router = APIRouter(tags=["documents"])

Db = Annotated[AsyncSession, Depends(get_db)]
DocumentUpload = Annotated[AuthContext, Depends(require_permission("document.upload"))]
DocumentRead = Annotated[AuthContext, Depends(require_permission("document.read"))]
DocumentUpdate = Annotated[AuthContext, Depends(require_permission("document.update"))]
DocumentDelete = Annotated[AuthContext, Depends(require_permission("document.delete"))]


def _service(request: Request) -> DocumentService:
    return request.app.state.document_service


def _tenant(auth: AuthContext) -> uuid.UUID:
    if auth.tenant_id is None:
        raise APIError(403, "NO_ACTIVE_MEMBERSHIP", "No active tenant membership")
    return auth.tenant_id


def _pages(total: int, page_size: int) -> int:
    return (total + page_size - 1) // page_size if total else 1


# ---- document CRUD ---------------------------------------------------------


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: DocumentCreateRequest,
    request: Request,
    db: Db,
    auth: DocumentUpload,
) -> DocumentResponse:
    svc = _service(request)
    result = await svc.create(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return DocumentResponse.model_validate(result)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    db: Db,
    auth: DocumentRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    q: str | None = Query(None, alias="q"),
) -> DocumentListResponse:
    svc = _service(request)
    items, total = await svc.list(
        db,
        tenant_id=_tenant(auth),
        page=page,
        page_size=page_size,
        status=status_filter,
        doc_type=type_filter,
        search=q,
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: DocumentRead,
) -> DocumentResponse:
    svc = _service(request)
    result = await svc.get(db, document_id=document_id, tenant_id=_tenant(auth))
    return DocumentResponse.model_validate(result)


@router.patch("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    request: Request,
    db: Db,
    auth: DocumentUpdate,
) -> DocumentResponse:
    svc = _service(request)
    result = await svc.update(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        document_id=document_id,
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return DocumentResponse.model_validate(result)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: Annotated[AuthContext, Depends(require_permission("document.delete"))],
) -> None:
    svc = _service(request)
    await svc.soft_delete(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        document_id=document_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


# ---- versioning ------------------------------------------------------------


@router.post(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_version(
    document_id: uuid.UUID,
    payload: DocumentVersionCreateRequest,
    request: Request,
    db: Db,
    auth: DocumentUpload,
) -> DocumentVersionResponse:
    svc = _service(request)
    result = await svc.create_version(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        document_id=document_id,
        payload=payload,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return DocumentVersionResponse.model_validate(result)


@router.get(
    "/documents/{document_id}/versions",
    response_model=DocumentVersionListResponse,
)
async def list_document_versions(
    document_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: DocumentRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentVersionListResponse:
    svc = _service(request)
    items, total = await svc.list_versions(
        db, tenant_id=_tenant(auth), document_id=document_id, page=page, page_size=page_size
    )
    return DocumentVersionListResponse(
        items=[DocumentVersionResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
    )


# ---- file upload (uploads create document + first version) -----------------


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    response: Response,
    db: Db,
    auth: DocumentUpload,
    file: UploadFile,
    title: str,
    type: str,
    meeting_id: uuid.UUID | None = None,
    description: str | None = None,
) -> DocumentResponse:
    svc = _service(request)
    result = await svc.upload(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        upload=file,
        title=title,
        doc_type=type,
        meeting_id=meeting_id,
        description=description,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response.status_code = result.pop("_status", 201)
    return DocumentResponse.model_validate(result)


# ---- file download ---------------------------------------------------------


@router.get("/documents/{document_id}/content")
async def download_document(
    document_id: uuid.UUID,
    response: Response,
    request: Request,
    db: Db,
    auth: DocumentRead,
    version: int | None = Query(None),
) -> StreamingResponse:
    svc = _service(request)
    fh, content_type, filename = await svc.stream(
        db,
        document_id=document_id,
        tenant_id=_tenant(auth),
        version=version,
        actor_user_id=auth.user_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return StreamingResponse(
        fh,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---- OCR -------------------------------------------------------------------


@router.post("/documents/{document_id}/ocr", response_model=DocumentResponse)
async def trigger_ocr(
    document_id: uuid.UUID,
    request: Request,
    db: Db,
    auth: DocumentUpload,
) -> DocumentResponse:
    svc = _service(request)
    result = await svc.trigger_ocr(
        db,
        tenant_id=_tenant(auth),
        user_id=auth.user_id,
        document_id=document_id,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return DocumentResponse.model_validate(result)
