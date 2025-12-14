"""
Services package - Business logic layer
"""
from .booking_service import BookingService
from .client_service import ClientService
from .office_info_service import OfficeInfoService
from .factory import ServiceFactory, get_service_factory  # ADD THIS LINE

__all__ = [
    'BookingService',
    'ClientService', 
    'OfficeInfoService',
    'ServiceFactory',          # ADD THIS
    'get_service_factory',     # ADD THIS
]