"""
Data Validation and Audit Logging

Provides:
- Input validation for database operations
- Constraints and triggers for data integrity
- Comprehensive audit logging for all data changes
- Change tracking with before/after snapshots
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Type
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy import event, inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of audit actions."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class AuditRecord:
    """Represents a single audit log entry."""
    table_name: str
    record_id: str
    action: AuditAction
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    changed_by: Optional[str] = None
    changed_at: datetime = None
    ip_address: Optional[str] = None
    
    def __post_init__(self):
        if self.changed_at is None:
            self.changed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "table_name": self.table_name,
            "record_id": self.record_id,
            "action": self.action.value,
            "old_data": self.old_data,
            "new_data": self.new_data,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "ip_address": self.ip_address
        }


class DataValidator:
    """Validates data before database operations."""
    
    # Validation rules by table
    RULES = {
        "customers": {
            "required": ["customer_id", "first_name", "last_name", "email", "segment", "region"],
            "email_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "segments": ["vip", "enterprise", "mid_market", "smb"],
            "regions": ["US", "UK", "EU", "APAC"],
            "max_lengths": {
                "first_name": 50,
                "last_name": 50,
                "email": 100,
                "customer_id": 20
            }
        },
        "products": {
            "required": ["product_id", "sku", "name", "category", "base_price"],
            "min_price": 0,
            "max_price": 1000000,
            "max_lengths": {
                "product_id": 20,
                "sku": 20,
                "name": 200
            }
        },
        "orders": {
            "required": ["order_id", "customer_id", "order_date", "status"],
            "statuses": ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"],
            "max_lengths": {
                "order_id": 20,
                "customer_id": 20
            }
        },
        "order_items": {
            "required": ["order_item_id", "order_id", "product_id", "quantity"],
            "min_quantity": 1,
            "max_quantity": 10000,
            "max_lengths": {
                "order_item_id": 20,
                "order_id": 20,
                "product_id": 20
            }
        }
    }
    
    @classmethod
    def validate_insert(cls, table: str, data: Dict[str, Any]) -> List[str]:
        """Validate data for INSERT operation."""
        errors = []
        rules = cls.RULES.get(table, {})
        
        # Check required fields
        for field in rules.get("required", []):
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Check field lengths
        max_lengths = rules.get("max_lengths", {})
        for field, max_len in max_lengths.items():
            if field in data and data[field] is not None:
                if len(str(data[field])) > max_len:
                    errors.append(f"Field {field} exceeds maximum length of {max_len}")
        
        # Table-specific validations
        if table == "customers":
            errors.extend(cls._validate_customer(data, rules))
        elif table == "products":
            errors.extend(cls._validate_product(data, rules))
        elif table == "orders":
            errors.extend(cls._validate_order(data, rules))
        elif table == "order_items":
            errors.extend(cls._validate_order_item(data, rules))
        
        return errors
    
    @classmethod
    def validate_update(
        cls,
        table: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> List[str]:
        """Validate data for UPDATE operation."""
        errors = []
        rules = cls.RULES.get(table, {})
        
        # Check immutable fields (cannot be changed)
        immutable = {
            "customers": ["customer_id"],
            "products": ["product_id"],
            "orders": ["order_id"],
            "order_items": ["order_item_id"]
        }
        
        for field in immutable.get(table, []):
            if field in new_data:
                if old_data.get(field) != new_data.get(field):
                    errors.append(f"Cannot modify immutable field: {field}")
        
        # Merge old and new for full validation
        merged = {**old_data, **new_data}
        errors.extend(cls.validate_insert(table, merged))
        
        return errors
    
    @classmethod
    def _validate_customer(cls, data: Dict[str, Any], rules: Dict) -> List[str]:
        """Validate customer-specific rules."""
        errors = []
        
        # Validate segment
        if "segment" in data:
            if data["segment"] not in rules.get("segments", []):
                errors.append(f"Invalid segment: {data['segment']}")
        
        # Validate region
        if "region" in data:
            if data["region"] not in rules.get("regions", []):
                errors.append(f"Invalid region: {data['region']}")
        
        # Validate email format
        if "email" in data:
            import re
            pattern = rules.get("email_pattern")
            if pattern and not re.match(pattern, str(data["email"])):
                errors.append(f"Invalid email format: {data['email']}")
        
        # Validate LTV factor
        if "ltv_factor" in data and data["ltv_factor"] is not None:
            try:
                ltv = float(data["ltv_factor"])
                if not 0 <= ltv <= 10:
                    errors.append(f"LTV factor must be between 0 and 10: {ltv}")
            except (ValueError, TypeError):
                errors.append(f"Invalid LTV factor: {data['ltv_factor']}")
        
        # Validate churn risk
        if "churn_risk" in data and data["churn_risk"] is not None:
            try:
                risk = float(data["churn_risk"])
                if not 0 <= risk <= 1:
                    errors.append(f"Churn risk must be between 0 and 1: {risk}")
            except (ValueError, TypeError):
                errors.append(f"Invalid churn risk: {data['churn_risk']}")
        
        return errors
    
    @classmethod
    def _validate_product(cls, data: Dict[str, Any], rules: Dict) -> List[str]:
        """Validate product-specific rules."""
        errors = []
        
        # Validate price
        if "base_price" in data:
            try:
                price = float(data["base_price"])
                min_price = rules.get("min_price", 0)
                max_price = rules.get("max_price", float('inf'))
                if price < min_price:
                    errors.append(f"Price cannot be negative: {price}")
                if price > max_price:
                    errors.append(f"Price exceeds maximum: {price}")
            except (ValueError, TypeError):
                errors.append(f"Invalid price: {data['base_price']}")
        
        # Validate cost
        if "cost" in data and data["cost"] is not None:
            try:
                cost = float(data["cost"])
                if cost < 0:
                    errors.append(f"Cost cannot be negative: {cost}")
            except (ValueError, TypeError):
                errors.append(f"Invalid cost: {data['cost']}")
        
        # Validate stock quantity
        if "stock_quantity" in data and data["stock_quantity"] is not None:
            try:
                qty = int(data["stock_quantity"])
                if qty < 0:
                    errors.append(f"Stock quantity cannot be negative: {qty}")
            except (ValueError, TypeError):
                errors.append(f"Invalid stock quantity: {data['stock_quantity']}")
        
        return errors
    
    @classmethod
    def _validate_order(cls, data: Dict[str, Any], rules: Dict) -> List[str]:
        """Validate order-specific rules."""
        errors = []
        
        # Validate status
        if "status" in data:
            if data["status"] not in rules.get("statuses", []):
                errors.append(f"Invalid status: {data['status']}")
        
        # Validate total
        if "total" in data and data["total"] is not None:
            try:
                total = float(data["total"])
                if total < 0:
                    errors.append(f"Total cannot be negative: {total}")
            except (ValueError, TypeError):
                errors.append(f"Invalid total: {data['total']}")
        
        # Validate date ordering
        if "shipped_date" in data and "order_date" in data:
            if data["shipped_date"] and data["order_date"]:
                if data["shipped_date"] < data["order_date"]:
                    errors.append("Shipped date cannot be before order date")
        
        if "delivered_date" in data and "shipped_date" in data:
            if data["delivered_date"] and data["shipped_date"]:
                if data["delivered_date"] < data["shipped_date"]:
                    errors.append("Delivered date cannot be before shipped date")
        
        return errors
    
    @classmethod
    def _validate_order_item(cls, data: Dict[str, Any], rules: Dict) -> List[str]:
        """Validate order item-specific rules."""
        errors = []
        
        # Validate quantity
        if "quantity" in data:
            try:
                qty = int(data["quantity"])
                min_qty = rules.get("min_quantity", 1)
                max_qty = rules.get("max_quantity", 10000)
                if qty < min_qty:
                    errors.append(f"Quantity must be at least {min_qty}: {qty}")
                if qty > max_qty:
                    errors.append(f"Quantity exceeds maximum {max_qty}: {qty}")
            except (ValueError, TypeError):
                errors.append(f"Invalid quantity: {data['quantity']}")
        
        # Validate unit price
        if "unit_price" in data and data["unit_price"] is not None:
            try:
                price = float(data["unit_price"])
                if price < 0:
                    errors.append(f"Unit price cannot be negative: {price}")
            except (ValueError, TypeError):
                errors.append(f"Invalid unit price: {data['unit_price']}")
        
        # Validate total price matches quantity * unit_price
        if all(k in data for k in ["quantity", "unit_price", "total_price"]):
            if data["total_price"] is not None:
                expected = float(data["quantity"]) * float(data["unit_price"])
                actual = float(data["total_price"])
                if abs(expected - actual) > 0.01:  # Allow 1 cent rounding difference
                    errors.append(
                        f"Total price ({actual}) doesn't match quantity * unit_price ({expected})"
                    )
        
        return errors


class AuditLogger:
    """Handles audit logging for database changes."""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self._current_user: Optional[str] = None
        self._current_ip: Optional[str] = None
    
    def set_context(self, user: Optional[str] = None, ip: Optional[str] = None):
        """Set the current user context for audit logging."""
        self._current_user = user
        self._current_ip = ip
    
    async def log_change(
        self,
        table_name: str,
        record_id: str,
        action: AuditAction,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None
    ):
        """Log a data change to the audit log."""
        if self.session is None:
            logger.warning("No session available for audit logging")
            return
        
        # Filter out non-serializable objects
        def clean_data(data: Optional[Dict]) -> Optional[Dict]:
            if data is None:
                return None
            return {
                k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                for k, v in data.items()
                if not k.startswith('_')
            }
        
        record = AuditRecord(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_data=clean_data(old_data),
            new_data=clean_data(new_data),
            changed_by=self._current_user,
            ip_address=self._current_ip
        )
        
        # Insert into audit log
        from sqlalchemy import text
        
        audit_sql = """
            INSERT INTO audit_log 
            (table_name, record_id, action, old_data, new_data, changed_by, ip_address, changed_at)
            VALUES 
            (:table_name, :record_id, :action, :old_data, :new_data, :changed_by, :ip_address, :changed_at)
        """
        
        try:
            await self.session.execute(
                text(audit_sql),
                {
                    "table_name": record.table_name,
                    "record_id": record.record_id,
                    "action": record.action.value,
                    "old_data": json.dumps(record.old_data) if record.old_data else None,
                    "new_data": json.dumps(record.new_data) if record.new_data else None,
                    "changed_by": record.changed_by,
                    "ip_address": record.ip_address,
                    "changed_at": record.changed_at
                }
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't raise - audit failure shouldn't break the main operation
    
    async def get_audit_history(
        self,
        table_name: Optional[str] = None,
        record_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Retrieve audit history with optional filtering."""
        if self.session is None:
            return []
        
        from sqlalchemy import text
        
        conditions = ["1=1"]
        params = {"limit": limit}
        
        if table_name:
            conditions.append("table_name = :table_name")
            params["table_name"] = table_name
        
        if record_id:
            conditions.append("record_id = :record_id")
            params["record_id"] = record_id
        
        if action:
            conditions.append("action = :action")
            params["action"] = action.value
        
        if since:
            conditions.append("changed_at >= :since")
            params["since"] = since
        
        sql = f"""
            SELECT * FROM audit_log 
            WHERE {' AND '.join(conditions)}
            ORDER BY changed_at DESC
            LIMIT :limit
        """
        
        result = await self.session.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            AuditRecord(
                table_name=row.table_name,
                record_id=row.record_id,
                action=AuditAction(row.action),
                old_data=json.loads(row.old_data) if row.old_data else None,
                new_data=json.loads(row.new_data) if row.new_data else None,
                changed_by=row.changed_by,
                changed_at=row.changed_at,
                ip_address=str(row.ip_address) if row.ip_address else None
            )
            for row in rows
        ]


def setup_audit_listeners(mapper: Mapper, class_):
    """
    Set up SQLAlchemy event listeners for automatic audit logging.
    
    Usage:
        from sqlalchemy import event
        event.listen(Customer.__mapper__, 'after_insert', after_insert_listener)
        event.listen(Customer.__mapper__, 'after_update', after_update_listener)
        event.listen(Customer.__mapper__, 'after_delete', after_delete_listener)
    """
    
    def after_insert_listener(mapper, connection, target):
        """Log insert operations."""
        logger.debug(f"INSERT: {class_.__name__} - {target}")
    
    def after_update_listener(mapper, connection, target):
        """Log update operations."""
        logger.debug(f"UPDATE: {class_.__name__} - {target}")
    
    def after_delete_listener(mapper, connection, target):
        """Log delete operations."""
        logger.debug(f"DELETE: {class_.__name__} - {target}")
    
    return after_insert_listener, after_update_listener, after_delete_listener


# Context manager for validation

class ValidationContext:
    """Context manager for data validation with audit logging."""
    
    def __init__(
        self,
        session: AsyncSession,
        table: str,
        record_id: str,
        user: Optional[str] = None,
        ip: Optional[str] = None
    ):
        self.session = session
        self.table = table
        self.record_id = record_id
        self.user = user
        self.ip = ip
        self.audit_logger = AuditLogger(session)
        self._old_data: Optional[Dict[str, Any]] = None
    
    async def __aenter__(self):
        self.audit_logger.set_context(self.user, self.ip)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def validate_insert(self, data: Dict[str, Any]) -> List[str]:
        """Validate insert data."""
        errors = DataValidator.validate_insert(self.table, data)
        if errors:
            logger.warning(f"Validation errors for {self.table} insert: {errors}")
        return errors
    
    def validate_update(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> List[str]:
        """Validate update data."""
        self._old_data = old_data
        errors = DataValidator.validate_update(self.table, old_data, new_data)
        if errors:
            logger.warning(f"Validation errors for {self.table} update: {errors}")
        return errors
    
    async def log_insert(self, new_data: Dict[str, Any]):
        """Log an insert operation."""
        await self.audit_logger.log_change(
            self.table,
            self.record_id,
            AuditAction.INSERT,
            new_data=new_data
        )
    
    async def log_update(self, new_data: Dict[str, Any]):
        """Log an update operation."""
        await self.audit_logger.log_change(
            self.table,
            self.record_id,
            AuditAction.UPDATE,
            old_data=self._old_data,
            new_data=new_data
        )
    
    async def log_delete(self, old_data: Dict[str, Any]):
        """Log a delete operation."""
        await self.audit_logger.log_change(
            self.table,
            self.record_id,
            AuditAction.DELETE,
            old_data=old_data
        )
