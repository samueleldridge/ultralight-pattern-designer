"""
Data Export API

Export query results in various formats.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.data_exporter import ExportFormat
from app.services.export_service import get_export_service
from app.middleware import get_current_user

router = APIRouter(prefix="/api/exports", tags=["exports"])


# Request/Response Models
class ExportRequest(BaseModel):
    query: str
    sql: str
    data: list  # Query results
    format: str  # csv, excel, pdf, json
    email_results: bool = True


class ExportResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    file_url: Optional[str] = None
    row_count: int
    format: str
    message: str


@router.post("", response_model=ExportResponse)
async def create_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Export query results to a file.
    
    Supports formats:
    - csv: Simple spreadsheet format
    - excel: Formatted Excel file with styling
    - pdf: Presentation-ready PDF
    - json: Machine-readable JSON
    
    The file will be emailed to the user if email_results is true.
    """
    try:
        format_enum = ExportFormat(request.format.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Choose from: csv, excel, pdf, json"
        )
    
    if not request.data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    export_service = get_export_service()
    
    # Create export job
    job = await export_service.create_export_job(
        user_id=current_user["id"],
        tenant_id=current_user["tenant_id"],
        query=request.query,
        sql=request.sql,
        data=request.data,
        format=format_enum,
        email_results=request.email_results
    )
    
    if job.status.value == "complete":
        return ExportResponse(
            success=True,
            job_id=job.id,
            file_url=job.file_url,
            row_count=job.row_count,
            format=request.format,
            message=f"Export complete! {job.row_count} rows exported to {request.format.upper()}."
        )
    else:
        return ExportResponse(
            success=False,
            job_id=job.id,
            row_count=0,
            format=request.format,
            message=f"Export failed: {job.error_message}"
        )


@router.get("/download/{filename}")
async def download_export(
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download an exported file"""
    from pathlib import Path
    
    export_service = get_export_service()
    file_path = export_service.get_export_path(filename)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type from extension
    content_types = {
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pdf': 'application/pdf',
        '.json': 'application/json'
    }
    content_type = content_types.get(file_path.suffix, 'application/octet-stream')
    
    return FileResponse(
        path=file_path,
        media_type=content_type,
        filename=filename
    )


@router.get("/formats")
async def list_export_formats():
    """List available export formats with descriptions"""
    return {
        "formats": [
            {
                "id": "csv",
                "name": "CSV (Spreadsheet)",
                "description": "Simple comma-separated values. Opens in Excel, Google Sheets, or any spreadsheet app.",
                "best_for": "Quick data analysis, importing into other tools",
                "icon": "📊"
            },
            {
                "id": "excel",
                "name": "Excel (Formatted)",
                "description": "Formatted Excel file with headers, styling, and optimized column widths.",
                "best_for": "Sharing with stakeholders, presentations",
                "icon": "📑"
            },
            {
                "id": "pdf",
                "name": "PDF (Presentation)",
                "description": "Professional PDF document with styled tables. Great for printing or sharing.",
                "best_for": "Executive presentations, printing",
                "icon": "📄"
            },
            {
                "id": "json",
                "name": "JSON (Technical)",
                "description": "Machine-readable JSON format with full data structure preserved.",
                "best_for": "API integration, technical workflows",
                "icon": "💻"
            }
        ]
    }


@router.post("/quick-export")
async def quick_export(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Quick export for immediate download (no email).
    Returns the file directly in the response.
    """
    try:
        format_enum = ExportFormat(request.format.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Choose from: csv, excel, pdf, json"
        )
    
    if not request.data:
        raise HTTPException(status_code=400, detail="No data to export")
    
    from app.services.data_exporter import DataExporter
    from fastapi.responses import StreamingResponse
    import io
    
    exporter = DataExporter()
    
    # Generate export
    content = await exporter.export(
        data=request.data,
        format=format_enum,
        title=f"Export: {request.query[:50]}",
        query=request.query
    )
    
    # Determine content type and filename
    content_type = exporter.get_content_type(format_enum)
    extension = exporter.get_extension(format_enum)
    filename = f"export_{request.query[:20].replace(' ', '_')}{extension}"
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(content),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
