import csv
from datetime import date, datetime
from io import BytesIO, StringIO
import re
from typing import Annotated, Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, Query, Response

from app.auth import WriterContext, require_writer
from app.schemas import ArchiveQuery


EXPORT_COLUMNS = (
    "case_id",
    "customer_name",
    "product_equipment",
    "voc_type",
    "voc_subtype",
    "customer_request",
    "responsible_departments",
    "received_at",
    "final_status",
    "record_origin",
)
XML_INVALID_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _archive_rows(search_service: Any, query: ArchiveQuery) -> list[dict[str, Any]]:
    effective_sort = query.sort or ("relevance" if query.q else "latest")
    rows = []
    page = 1
    while True:
        result = search_service.search_archive(
            query.model_copy(update={"page": page, "page_size": 100}),
            effective_sort,
        )
        rows.extend(result["items"])
        if len(rows) >= result["total"]:
            break
        page += 1
    return [{column: row.get(column) for column in EXPORT_COLUMNS} for row in rows]


def _cell(value: Any, reference: str) -> str:
    if isinstance(value, (date, datetime)):
        value = value.isoformat()
    text = _safe_text(value)
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def _safe_text(value: Any) -> str:
    return XML_INVALID_CONTROLS.sub("", "" if value is None else str(value))


def _csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for row in rows:
        values = {}
        for column, value in row.items():
            if isinstance(value, str):
                value = _safe_text(value)
                if value.lstrip().startswith(("=", "+", "-", "@")):
                    value = "'" + value
            values[column] = value
        sanitized.append(values)
    return sanitized


def _xlsx(rows: list[dict[str, Any]]) -> bytes:
    all_rows = [dict(zip(EXPORT_COLUMNS, EXPORT_COLUMNS)), *rows]
    sheet_rows = []
    for row_number, row in enumerate(all_rows, 1):
        cells = "".join(
            _cell(row[column], f"{chr(65 + index)}{row_number}")
            for index, column in enumerate(EXPORT_COLUMNS)
        )
        sheet_rows.append(f'<row r="{row_number}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Archive" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": sheet,
    }
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as workbook:
        for name, content in files.items():
            workbook.writestr(name, content.encode("utf-8"))
    return output.getvalue()


def create_export_router(search_service: Any) -> APIRouter:
    router = APIRouter(prefix="/api/export", tags=["export"])

    @router.get("/archive.csv")
    def export_csv(
        query: Annotated[ArchiveQuery, Query()],
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        stream = StringIO(newline="")
        csv_writer = csv.DictWriter(stream, fieldnames=EXPORT_COLUMNS)
        csv_writer.writeheader()
        csv_writer.writerows(_csv_rows(_archive_rows(search_service, query)))
        return Response(
            content=stream.getvalue().encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="voc-archive.csv"'},
        )

    @router.get("/archive.xlsx")
    def export_xlsx(
        query: Annotated[ArchiveQuery, Query()],
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return Response(
            content=_xlsx(_archive_rows(search_service, query)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="voc-archive.xlsx"'},
        )

    return router
