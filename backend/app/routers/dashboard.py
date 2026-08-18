from collections.abc import Callable
from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.schemas import TranslationRequest
from app.services.translation import TranslationService


def create_dashboard_router(
    repository: Any,
    today: Callable[[], date] = date.today,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["operations"])

    @router.get("/dashboard")
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
        return repository.list_notifications()

    @router.post("/translate")
    def translate(
        payload: TranslationRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        return TranslationService(settings).translate(payload.text)

    return router
