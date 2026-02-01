"""
Audit logging for all database queries and security events.
Tracks who did what, when, and from where.
"""

import json
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import asyncio


class AuditEventType(Enum):
    """Types of audit events"""
    QUERY_EXECUTED = "query_executed"
    QUERY_FAILED = "query_failed"
    SECURITY_VIOLATION = "security_violation"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    EXPORT_CREATED = "export_created"
    CONNECTION_CREATED = "connection_created"
    CONNECTION_DELETED = "connection_deleted"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_HIT = "rate_limit_hit"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event record"""
    event_id: str
    event_type: str
    timestamp: str
    severity: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: str
    resource_id: Optional[str]
    action: str
    status: str
    details: Dict[str, Any]
    metadata: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: str = "",
        resource_id: Optional[str] = None,
        action: str = "",
        status: str = "success",
        details: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> "AuditEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type.value,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity.value,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details or {},
            metadata=metadata or {}
        )


class AuditLogger:
    """
    Centralized audit logging system.
    Logs to multiple destinations: database, file, external services.
    """
    
    def __init__(self):
        self._handlers: List[callable] = []
        self._buffer: List[AuditEvent] = []
        self._buffer_size = 100
        self._flush_interval = 30  # seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def add_handler(self, handler: callable):
        """Add a log handler"""
        self._handlers.append(handler)
    
    async def start(self):
        """Start background flush task"""
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
    
    async def stop(self):
        """Stop and flush remaining logs"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush_buffer()
    
    async def _flush_loop(self):
        """Periodically flush buffer"""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush buffered events to handlers"""
        if not self._buffer:
            return
        
        events = self._buffer.copy()
        self._buffer.clear()
        
        for handler in self._handlers:
            try:
                await handler(events)
            except Exception as e:
                # Log error but don't stop other handlers
                print(f"Audit handler error: {e}")
    
    async def log(self, event: AuditEvent, immediate: bool = False):
        """Log an audit event"""
        self._buffer.append(event)
        
        if immediate or len(self._buffer) >= self._buffer_size:
            await self._flush_buffer()
    
    async def log_query(
        self,
        sql: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        row_count: Optional[int] = None,
        execution_time_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log a query execution event"""
        # Hash the SQL for privacy while maintaining uniqueness
        sql_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
        
        # Truncate SQL for logging
        sql_preview = sql[:500] if len(sql) > 500 else sql
        
        event_type = AuditEventType.QUERY_EXECUTED if success else AuditEventType.QUERY_FAILED
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
        
        event = AuditEvent.create(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="query",
            resource_id=sql_hash,
            action="execute",
            status="success" if success else "failed",
            details={
                "sql_hash": sql_hash,
                "sql_preview": sql_preview,
                "connection_id": connection_id,
                "row_count": row_count,
                "execution_time_ms": execution_time_ms,
                "error": error
            }
        )
        
        await self.log(event)
    
    async def log_security_violation(
        self,
        violation_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.ERROR
    ):
        """Log a security violation"""
        event = AuditEvent.create(
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            resource_type="security",
            action=violation_type,
            status="blocked",
            details=details
        )
        
        await self.log(event, immediate=True)  # Security events are immediate
    
    async def log_auth(
        self,
        success: bool,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log authentication event"""
        event_type = AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILED
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
        
        event = AuditEvent.create(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="authentication",
            action="login",
            status="success" if success else "failed",
            details={"error": error} if error else {}
        )
        
        await self.log(event)
    
    async def log_permission_denied(
        self,
        resource: str,
        action: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        required_permission: Optional[str] = None
    ):
        """Log permission denied event"""
        event = AuditEvent.create(
            event_type=AuditEventType.PERMISSION_DENIED,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            resource_type=resource,
            action=action,
            status="denied",
            details={"required_permission": required_permission}
        )
        
        await self.log(event)
    
    async def log_export(
        self,
        export_format: str,
        row_count: int,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        query_hash: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log data export event"""
        event = AuditEvent.create(
            event_type=AuditEventType.EXPORT_CREATED,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            resource_type="export",
            action="create",
            status="success",
            details={
                "format": export_format,
                "row_count": row_count,
                "query_hash": query_hash
            }
        )
        
        await self.log(event)


class DatabaseAuditHandler:
    """Handler that writes audit logs to database"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    async def __call__(self, events: List[AuditEvent]):
        """Write events to database"""
        # Implementation depends on your ORM
        # This is a placeholder for the structure
        async with self.db_session_factory() as session:
            for event in events:
                # Convert to DB model and save
                # await session.execute(insert_audit_log(event))
                pass
            await session.commit()


class FileAuditHandler:
    """Handler that writes audit logs to file"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    async def __call__(self, events: List[AuditEvent]):
        """Append events to log file"""
        import aiofiles
        
        async with aiofiles.open(self.filepath, 'a') as f:
            for event in events:
                line = json.dumps(asdict(event), default=str)
                await f.write(line + '\n')


class ConsoleAuditHandler:
    """Handler that prints audit logs to console"""
    
    async def __call__(self, events: List[AuditEvent]):
        """Print events to console"""
        for event in events:
            print(f"[AUDIT] {event.severity.upper()}: {event.event_type} - {event.action}")


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


async def log_query_execution(
    sql: str,
    user_id: Optional[str] = None,
    success: bool = True,
    **kwargs
):
    """Convenience function to log query execution"""
    logger = get_audit_logger()
    await logger.log_query(sql, user_id=user_id, success=success, **kwargs)


async def log_security_event(
    violation_type: str,
    details: Dict[str, Any],
    **kwargs
):
    """Convenience function to log security events"""
    logger = get_audit_logger()
    await logger.log_security_violation(violation_type, details, **kwargs)
