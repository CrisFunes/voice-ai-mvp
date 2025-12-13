"""
Database Handler - Client and Accountant Management
Handles Excel database operations for demo
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
from loguru import logger
import config

class DBHandler:
    """
    Manages client and accountant database
    For demo: Uses Excel file
    For production: Migrate to PostgreSQL
    """
    
    def __init__(self, excel_path: Optional[Path] = None):
        """Initialize database handler"""
        logger.info("Initializing Database Handler...")
        
        if excel_path is None:
            excel_path = config.PROJECT_ROOT / "DATABASE_CLIENTIPROFESSIONISTI.xlsx"
        
        try:
            # Load Excel
            self.clients_df = pd.read_excel(excel_path, sheet_name="Clients")
            self.accountants_df = pd.read_excel(excel_path, sheet_name="Accountants")
            
            logger.success(f"Loaded {len(self.clients_df)} clients, {len(self.accountants_df)} accountants")
            
        except FileNotFoundError:
            logger.warning(f"Database file not found: {excel_path}")
            # Create empty DataFrames for demo
            self.clients_df = pd.DataFrame()
            self.accountants_df = pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Failed to load database: {e}")
            raise
    
    def search_client(self, company_name: str = None, tax_code: str = None) -> Optional[Dict]:
        """
        Search for client by company name or tax code
        
        Args:
            company_name: Company name (fuzzy match)
            tax_code: Tax code (exact match)
            
        Returns:
            Client info dict or None
        """
        if self.clients_df.empty:
            logger.warning("No clients in database")
            return None
        
        # Implementation will depend on Excel structure
        pass
    
    def get_accountant(self, accountant_id: int) -> Optional[Dict]:
        """Get accountant info by ID"""
        pass
    
    def search_accountant_by_specialization(self, specialization: str) -> List[Dict]:
        """Find accountants by specialization"""
        pass