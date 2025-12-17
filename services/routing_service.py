"""
Routing Service - find accountant and log call routing
"""
from typing import Optional
from sqlalchemy.orm import Session
from loguru import logger
from sqlalchemy import func

from models import Accountant, Client, CallLog, CallLogStatus


class RoutingService:
    """Handles routing requests and call logging"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def find_accountant_by_name(self, name: str) -> Optional[Accountant]:
        """Find accountant by name (case-insensitive partial)"""
        if not name:
            return None
        return (
            self.db.query(Accountant)
            .filter(func.lower(Accountant.name).like(f"%{name.lower()}%"))
            .first()
        )

    def find_accountant_by_specialization(self, specialization: str) -> Optional[Accountant]:
        """Find first active accountant matching specialization"""
        if not specialization:
            return None
        return (
            self.db.query(Accountant)
            .filter(Accountant.specialization == specialization)
            .filter(Accountant.status == "active")
            .first()
        )

    def log_call(
        self,
        caller_phone: Optional[str] = None,
        client_id: Optional[str] = None,
        accountant_id: Optional[str] = None,
        reason: Optional[str] = None,
        urgency: Optional[str] = None,
        callback_requested: bool = False,
        status: str = CallLogStatus.PENDING.value,
        call_sid: Optional[str] = None,
    ) -> CallLog:
        """Create a call log entry"""
        log = CallLog(
            call_sid=call_sid,
            client_id=client_id,
            accountant_id=accountant_id,
            caller_phone=caller_phone,
            reason=reason,
            urgency=urgency,
            callback_requested=callback_requested,
            status=status,
        )
        self.db.add(log)
        logger.info(f"CallLog created for {caller_phone or client_id}: {status}")
        return log

    def resolve_client(self, phone: str) -> Optional[Client]:
        """Resolve client by phone exact match"""
        if not phone:
            return None
        return self.db.query(Client).filter(Client.phone == phone).first()
