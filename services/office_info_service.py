"""
Office Info Service - Office hours and information
"""
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from models import OfficeInfo


class OfficeInfoService:
    """
    Manages office information queries
    """
    
    ITALIAN_DAYS = {
        "monday": "lunedì",
        "tuesday": "martedì", 
        "wednesday": "mercoledì",
        "thursday": "giovedì",
        "friday": "venerdì",
        "saturday": "sabato",
        "sunday": "domenica"
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_office_hours(self, day: Optional[str] = None) -> str:
        """
        Get office hours for specific day or today
        
        Args:
            day: Day name in English (e.g., "monday") or None for today
            
        Returns:
            Office hours string in Italian
        """
        if day is None:
            day = datetime.now().strftime("%A").lower()
        
        logger.info(f"Getting office hours for {day}")
        
        key = f"office_hours_{day}"
        office_info = self.db.query(OfficeInfo).filter(OfficeInfo.key == key).first()
        
        if not office_info:
            return f"Informazioni non disponibili per {self.ITALIAN_DAYS.get(day, day)}"
        
        if office_info.value == "closed":
            return f"L'ufficio è chiuso {self.ITALIAN_DAYS.get(day, day)}"
        
        return f"L'ufficio è aperto {self.ITALIAN_DAYS.get(day, day)} dalle {office_info.value}"
    
    def get_contact_info(self) -> Dict[str, str]:
        """Get all contact information"""
        contacts = self.db.query(OfficeInfo).filter(
            OfficeInfo.category == "contact"
        ).all()
        
        return {info.key: info.value for info in contacts}
    
    def get_address(self) -> Optional[str]:
        """Get office address"""
        address = self.db.query(OfficeInfo).filter(
            OfficeInfo.key == "office_address"
        ).first()
        
        return address.value if address else None