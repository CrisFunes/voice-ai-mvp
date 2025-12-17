"""
Lead Service - structured lead capture and qualification
"""
from typing import Optional, Dict
from sqlalchemy.orm import Session
from loguru import logger

from models import Lead, LeadCategory


class LeadService:
    """Manage creation and updates of leads"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_lead(
        self,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company_name: Optional[str] = None,
        category: str = LeadCategory.INFORMATION.value,
        notes: Optional[str] = None,
        source: str = "voice_ai",
    ) -> Lead:
        lead = Lead(
            name=name,
            phone=phone,
            email=email,
            company_name=company_name,
            category=category,
            notes=notes,
            source=source,
        )
        self.db.add(lead)
        logger.info(f"Lead created: {name or company_name} ({category})")
        return lead

    def mark_contacted(self, lead_id: str) -> Optional[Lead]:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None
        lead.contacted = True
        return lead

    def qualify_lead(self, lead_id: str, notes: str) -> Optional[Lead]:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None
        lead.notes = (lead.notes or "") + f"\n{notes}"
        return lead
