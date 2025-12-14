"""
Service Factory - Centralized Service Creation
===============================================
Factory pattern for creating service instances based on SERVICE_MODE.

This factory:
- Creates service instances based on configuration
- Manages dependency injection (DB sessions)
- Supports mock/real mode switching
- Provides clean abstraction for testing

Usage:
    from services.factory import ServiceFactory
    
    factory = ServiceFactory(mode="real")
    booking_service = factory.create_booking_service()
    client_service = factory.create_client_service()
"""
from typing import Literal
from sqlalchemy.orm import Session
from loguru import logger

# Import real service implementations
from services.booking_service import BookingService
from services.client_service import ClientService
from services.office_info_service import OfficeInfoService

# Import database utilities
from database import SessionLocal, get_db


# Type for service mode
ServiceMode = Literal["mock", "real"]


class ServiceFactory:
    """
    Factory for creating service instances.
    
    Centralizes service creation logic and dependency injection.
    Supports switching between mock and real implementations.
    
    Attributes:
        mode: Service mode ("mock" or "real")
        db_session: Optional database session (if provided, reused)
    """
    
    def __init__(
        self, 
        mode: ServiceMode = "real",
        db_session: Session | None = None
    ):
        """
        Initialize service factory.
        
        Args:
            mode: Service mode ("mock" or "real")
            db_session: Optional DB session to reuse
        
        Raises:
            ValueError: If mode is not "mock" or "real"
        """
        if mode not in ["mock", "real"]:
            raise ValueError(
                f"Invalid service mode: '{mode}'\n"
                f"Must be 'mock' or 'real'"
            )
        
        self.mode = mode
        self._db_session = db_session
        
        logger.info(f"🏭 ServiceFactory initialized in {mode.upper()} mode")
    
    def _get_db_session(self) -> Session:
        """
        Get database session.
        
        Returns existing session if provided, otherwise creates new one.
        
        WARNING: If factory creates session, caller is responsible for closing it.
        """
        if self._db_session:
            return self._db_session
        
        # Create new session
        logger.debug("Creating new database session")
        return SessionLocal()
    
    def create_booking_service(self) -> BookingService:
        """
        Create BookingService instance.
        
        Returns:
            BookingService configured for current mode
        """
        db = self._get_db_session()
        
        if self.mode == "mock":
            # In mock mode, we still use real BookingService
            # but could add logging/simulation wrapper
            logger.debug("Creating BookingService (real implementation)")
            return BookingService(db_session=db)
        
        else:  # real mode
            logger.debug("Creating BookingService (real implementation)")
            return BookingService(db_session=db)
    
    def create_client_service(self) -> ClientService:
        """
        Create ClientService instance.
        
        Returns:
            ClientService configured for current mode
        """
        db = self._get_db_session()
        
        if self.mode == "mock":
            logger.debug("Creating ClientService (real implementation)")
            return ClientService(db_session=db)
        
        else:  # real mode
            logger.debug("Creating ClientService (real implementation)")
            return ClientService(db_session=db)
    
    def create_office_info_service(self) -> OfficeInfoService:
        """
        Create OfficeInfoService instance.
        
        Returns:
            OfficeInfoService configured for current mode
        """
        db = self._get_db_session()
        
        if self.mode == "mock":
            logger.debug("Creating OfficeInfoService (real implementation)")
            return OfficeInfoService(db_session=db)
        
        else:  # real mode
            logger.debug("Creating OfficeInfoService (real implementation)")
            return OfficeInfoService(db_session=db)
    
    def create_all_services(self) -> dict:
        """
        Create all services at once.
        
        Useful for initialization where all services are needed.
        
        Returns:
            Dictionary with all service instances:
            {
                'booking': BookingService,
                'client': ClientService,
                'office_info': OfficeInfoService
            }
        """
        logger.info("Creating all services...")
        
        return {
            'booking': self.create_booking_service(),
            'client': self.create_client_service(),
            'office_info': self.create_office_info_service(),
        }
    
    def close(self):
        """
        Close database session if factory created it.
        
        Only closes session if factory created it (not provided externally).
        """
        if self._db_session is None:
            # Factory didn't create session, nothing to close
            return
        
        # Session was provided externally, don't close it
        # (caller is responsible)
        pass


# ============================================================================
# MOCK SERVICE WRAPPERS (for future use)
# ============================================================================

class MockBookingServiceWrapper:
    """
    Wrapper for BookingService that simulates behavior without DB writes.
    
    Currently unused - kept for future mock mode implementation.
    This would wrap BookingService and intercept DB operations.
    """
    
    def __init__(self, real_service: BookingService):
        self.real_service = real_service
        self.mock_appointments = []
    
    def check_availability(self, *args, **kwargs):
        """Mock check_availability - returns fake slots"""
        from datetime import datetime, timedelta
        
        # Return some fake available slots
        base_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        return [
            base_time + timedelta(hours=i)
            for i in range(5)
        ]
    
    def create_appointment(self, *args, **kwargs):
        """Mock create_appointment - stores in memory"""
        # Don't actually write to DB
        logger.info("MOCK: Appointment created (in memory only)")
        
        # Create fake appointment object
        from models import Appointment
        appointment = Appointment(
            id="mock-" + str(len(self.mock_appointments) + 1),
            **kwargs
        )
        self.mock_appointments.append(appointment)
        return appointment
    
    def __getattr__(self, name):
        """Forward other methods to real service"""
        return getattr(self.real_service, name)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_service_factory(mode: ServiceMode | None = None) -> ServiceFactory:
    """
    Get ServiceFactory instance with automatic mode detection.
    
    Args:
        mode: Service mode (if None, reads from config.SERVICE_MODE)
    
    Returns:
        ServiceFactory instance
    
    Example:
        from services.factory import get_service_factory
        
        factory = get_service_factory()  # Uses config.SERVICE_MODE
        booking_service = factory.create_booking_service()
    """
    if mode is None:
        # Import here to avoid circular dependency
        import config
        mode = config.SERVICE_MODE
    
    return ServiceFactory(mode=mode)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'ServiceFactory',
    'ServiceMode',
    'get_service_factory',
    'MockBookingServiceWrapper',  # For future use
]