"""
Export Service for managing export jobs
"""

import uuid
import hashlib
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from app.services.data_exporter import DataExporter, ExportFormat, ExportStatus, ExportJob
from app.services.email_service import get_email_service, EmailMessage
from app.services.email_templates import EmailTemplates
from app.database import AsyncSessionLocal


class ExportService:
    """Service for managing data exports"""
    
    def __init__(self, upload_dir: str = "/tmp/exports"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.exporter = DataExporter()
    
    async def create_export_job(
        self,
        user_id: str,
        tenant_id: str,
        query: str,
        sql: str,
        data: List[Dict],
        format: ExportFormat,
        email_results: bool = True
    ) -> ExportJob:
        """Create and process an export job"""
        
        job_id = self._generate_id()
        
        job = ExportJob(
            id=job_id,
            user_id=user_id,
            tenant_id=tenant_id,
            query=query,
            format=format,
            status=ExportStatus.PROCESSING,
            created_at=datetime.utcnow(),
            row_count=len(data)
        )
        
        try:
            # Generate export file
            file_content = await self.exporter.export(
                data=data,
                format=format,
                title=f"Export: {query[:50]}",
                query=query
            )
            
            # Save to file
            filename = f"export_{job_id}{self.exporter.get_extension(format)}"
            file_path = self.upload_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Update job
            job.status = ExportStatus.COMPLETE
            job.completed_at = datetime.utcnow()
            job.file_url = f"/exports/{filename}"
            job.file_size = len(file_content)
            
            # Send email if requested
            if email_results:
                await self._send_export_email(job, file_content, filename)
            
        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_message = str(e)
        
        return job
    
    async def _send_export_email(
        self,
        job: ExportJob,
        file_content: bytes,
        filename: str
    ):
        """Send export completion email with file attached"""
        try:
            email_service = get_email_service()
            
            # Get user email (would need to fetch from user service)
            user_email = await self._get_user_email(job.user_id)
            if not user_email:
                return
            
            # Determine content type
            content_type = self.exporter.get_content_type(job.format)
            
            # Create email
            html_body = EmailTemplates.export_complete(
                user_name=user_email.split('@')[0],
                query=job.query,
                row_count=job.row_count,
                format=job.format.value.upper()
            )
            
            from app.services.email_service import EmailAttachment
            
            message = EmailMessage(
                to=user_email,
                subject=f"Your Data Export is Ready: {job.query[:30]}...",
                html_body=html_body,
                text_body=f"Your export of {job.row_count} rows is ready. Query: {job.query}",
                attachments=[
                    EmailAttachment(
                        filename=filename,
                        content=file_content,
                        content_type=content_type
                    )
                ]
            )
            
            await email_service.send_email(message)
            
        except Exception as e:
            print(f"Failed to send export email: {e}")
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email from database"""
        # This would integrate with your user service
        # For now, placeholder - you'd need to fetch from User table
        return None
    
    def _generate_id(self) -> str:
        """Generate unique job ID"""
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]
    
    def get_export_path(self, filename: str) -> Path:
        """Get full path to export file"""
        return self.upload_dir / filename
    
    async def cleanup_old_exports(self, max_age_hours: int = 24):
        """Clean up export files older than specified hours"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in self.upload_dir.glob("export_*"):
            if file_path.stat().st_mtime < cutoff.timestamp():
                file_path.unlink()


# Singleton
_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get or create export service"""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service
