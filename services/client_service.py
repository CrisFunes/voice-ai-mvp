"""
Client Service - Client lookup and management
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from models import Client, Accountant


class ClientService:
    """
    Manages client lookup operations
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def find_by_company_name(self, company_name: str) -> Optional[Client]:
        """
        Find client by company name (case-insensitive, partial match)
        
        Args:
            company_name: Company name to search
            
        Returns:
            Client object or None
        """
        logger.info(f"Searching client: {company_name}")
        
        # Try exact match first (case-insensitive)
        client = self.db.query(Client).filter(
            func.lower(Client.company_name) == company_name.lower()
        ).first()
        
        if client:
            logger.success(f"✅ Found client: {client.company_name} (exact match)")
            return client
        
        # Try partial match
        client = self.db.query(Client).filter(
            func.lower(Client.company_name).like(f"%{company_name.lower()}%")
        ).first()
        
        if client:
            logger.success(f"✅ Found client: {client.company_name} (partial match)")
            return client
        
        logger.warning(f"⚠️ Client not found: {company_name}")
        return None
    
    def find_by_tax_code(self, tax_code: str) -> Optional[Client]:
        """Find client by tax code (exact match)"""
        return self.db.query(Client).filter(Client.tax_code == tax_code).first()

    def find_by_phone(self, phone: str) -> Optional[Client]:
        """Find client by phone (exact match)"""
        normalized = phone.strip()
        return self.db.query(Client).filter(Client.phone == normalized).first()
    
    def get_assigned_accountant(self, client_id: str) -> Optional[Accountant]:
        """Get accountant assigned to client"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return None
        
        return client.accountant