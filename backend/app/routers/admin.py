from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.auth import WriterContext, require_writer


RESOURCE_FIELDS = {
    "customers": ({"name", "active"}, {"name"}),
    "products": ({"name", "active"}, {"name"}),
    "voc_types": ({"voc_type", "voc_subtype", "active"}, {"voc_type", "voc_subtype"}),
    "people": (
        {"department", "name", "email", "role", "active"},
        {"department", "name", "email", "role"},
    ),
    "final_approver": ({"person_id"}, {"person_id"}),
    "templates": (
        {"template_key", "subject_template", "body_template", "active"},
        {"template_key", "subject_template", "body_template"},
    ),
    "notification_settings": (
        {"weekday_time", "timezone_name"},
        {"weekday_time", "timezone_name"},
    ),
}


def create_admin_router(repository: Any) -> APIRouter:
    router = APIRouter(prefix="/api/admin/master-data", tags=["admin"])

    def checked_resource(resource: str) -> str:
        if resource not in RESOURCE_FIELDS:
            raise HTTPException(status_code=404, detail="Unknown master-data resource")
        return resource

    @router.get("/{resource}")
    def list_master_data(
        resource: str,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return repository.list_master_data(checked_resource(resource))

    @router.post("/{resource}", status_code=status.HTTP_201_CREATED)
    def create_master_data(
        resource: str,
        payload: Annotated[dict[str, Any], Body()],
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        resource = checked_resource(resource)
        allowed, required = RESOURCE_FIELDS[resource]
        if not payload.keys() <= allowed or not required <= payload.keys():
            raise HTTPException(status_code=422, detail="Invalid master-data fields")
        if any(
            isinstance(payload[field], str) and not payload[field].strip()
            for field in required
        ):
            raise HTTPException(status_code=422, detail="Master-data values must not be blank")
        return repository.create_master_data(resource, payload, writer.writer_name)

    return router
