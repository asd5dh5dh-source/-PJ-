from collections.abc import Callable
from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.auth import WriterContext, require_writer
from app.schemas import DashboardResponse, TranslationRequest
from app.services.translation import TranslationService


def create_dashboard_router(
    repository: Any,
    today: Callable[[], date] = date.today,
    notification_service: Any | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["operations"])

    @router.get(
        "/dashboard",
        response_model=DashboardResponse,
        response_model_exclude_none=True,
    )
    def dashboard(
        date_from: Annotated[date | None, Query()] = None,
        date_to: Annotated[date | None, Query()] = None,
        period: Annotated[Literal["30d", "week", "month"], Query()] = "30d",
    ):
        date_to = date_to or today()
        if date_from is None:
            if period == "week":
                date_from = date_to - timedelta(days=date_to.weekday())
            elif period == "month":
                date_from = date_to.replace(day=1)
            else:
                date_from = date_to - timedelta(days=29)
        if date_from > date_to:
            raise HTTPException(status_code=422, detail="date_from must not exceed date_to")
        return repository.dashboard(date_from, date_to)

    @router.get("/notifications")
    def notifications():
        logs = repository.list_notifications()
        previews = (
            notification_service.list_pending_previews(logs)
            if notification_service is not None
            else []
        )
        return [*previews, *logs]

    @router.post("/notifications/process-daily")
    def process_daily_notifications(
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        queued = notification_service.queue_daily() if notification_service else []
        return {"queued": len(queued)}

    @router.post("/translate")
    def translate(
        payload: TranslationRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return TranslationService(settings).translate(payload.text)

    return router
