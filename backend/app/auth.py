from hashlib import sha256
import hmac
import re
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)

from app.config import Settings, get_settings
from app.db import WriterAttemptStore


class WriterCredentials(BaseModel):
    writer_name: str = Field(min_length=1, max_length=200)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("writer_name")
    @classmethod
    def normalize_writer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("writer_name must not be blank")
        return value


class WriterContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    writer_name: str


def _attempt_store(request: Request) -> WriterAttemptStore:
    return getattr(request.app.state, "writer_attempt_store", None) or WriterAttemptStore()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _decode_writer_name(value: str) -> str:
    if re.search(r"%(?![0-9a-fA-F]{2})", value):
        raise ValueError("Malformed percent-encoded writer name")
    return unquote(value, encoding="utf-8", errors="strict")


def _verify_credentials(
    credentials: WriterCredentials,
    request: Request,
    settings: Settings,
) -> WriterContext:
    client_ip = _client_ip(request)
    store = _attempt_store(request)
    expected_hash = settings.voc_writer_password_hash.get_secret_value().lower()
    if not expected_hash:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Writer verification is not configured",
        )
    supplied_hash = sha256(
        credentials.password.get_secret_value().encode("utf-8")
    ).hexdigest()
    succeeded = hmac.compare_digest(supplied_hash, expected_hash)
    locked = store.record_and_check_locked(
        credentials.writer_name, client_ip, succeeded
    )
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Writer verification is locked for 15 minutes",
            headers={"Retry-After": "900"},
        )
    if not succeeded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid writer credentials",
        )
    return WriterContext(writer_name=credentials.writer_name)


def require_writer(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    writer_name: Annotated[
        str | None, Header(alias="X-Writer-Name")
    ] = None,
    password: Annotated[
        str | None, Header(alias="X-Writer-Password")
    ] = None,
) -> WriterContext:
    if not writer_name or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Writer headers are required",
        )
    try:
        credentials = WriterCredentials(
            writer_name=_decode_writer_name(writer_name), password=password
        )
    except (ValidationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid writer credentials",
        ) from error
    return _verify_credentials(credentials, request, settings)


router = APIRouter(prefix="/api/writer", tags=["writer"])


@router.post("/verify", response_model=WriterContext)
def verify_writer(
    credentials: WriterCredentials,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> WriterContext:
    return _verify_credentials(credentials, request, settings)
