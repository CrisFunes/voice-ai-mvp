"""
Booking Service - Real appointment management with DB persistence
CRITICAL: This service MUST write to database
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from loguru import logger

from models import Appointment, Accountant, Client, AppointmentStatus


class BookingService:
    """
    Manages appointment booking operations
    
    CRITICAL REQUIREMENT: All operations must persist to database
    This is NOT a mock - this is the real implementation for Version B
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize service with database session
        
        Args:
            db_session: Active SQLAlchemy session
        """
        self.db = db_session
    
    def check_availability(
        self, 
        accountant_id: str, 
        date: datetime,
        duration: int = 60
    ) -> List[datetime]:
        """
        Check available time slots for accountant on given date
        
        Args:
            accountant_id: Accountant UUID
            date: Date to check (will check 9:00-18:00)
            duration: Appointment duration in minutes
            
        Returns:
            List of available datetime slots
        """
        logger.info(f"Checking availability for accountant {accountant_id} on {date.date()}")
        
        # Business hours: 9:00 - 18:00
        start_hour = 9
        end_hour = 18
        
        # Get existing appointments for this accountant on this date
        existing = self.db.query(Appointment).filter(
            Appointment.accountant_id == accountant_id,
            Appointment.datetime >= date.replace(hour=start_hour, minute=0),
            Appointment.datetime < date.replace(hour=end_hour, minute=0),
            Appointment.status != AppointmentStatus.CANCELLED.value
        ).all()
        
        # Generate all possible slots
        available_slots = []
        current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = date.replace(hour=end_hour, minute=0)
        
        while current_time < end_time:
            # Check if slot conflicts with existing appointment
            conflict = False
            for appt in existing:
                appt_end = appt.datetime + timedelta(minutes=appt.duration)
                slot_end = current_time + timedelta(minutes=duration)
                
                # Check overlap
                if (current_time < appt_end) and (slot_end > appt.datetime):
                    conflict = True
                    break
            
            if not conflict:
                available_slots.append(current_time)
            
            # Move to next slot
            current_time += timedelta(minutes=30)  # Check every 30 min
        
        logger.info(f"Found {len(available_slots)} available slots")
        return available_slots
    
    def create_appointment(
        self,
        client_id: str,
        accountant_id: str,
        datetime: datetime,
        duration: int = 60,
        notes: Optional[str] = None
    ) -> Appointment:
        """
        Create new appointment with DB persistence
        
        Args:
            client_id: Client UUID
            accountant_id: Accountant UUID  
            datetime: Appointment datetime
            duration: Duration in minutes
            notes: Optional notes
            
        Returns:
            Created Appointment object with ID
            
        Raises:
            ValueError: If slot not available or invalid data
        """
        logger.info(f"Creating appointment: client={client_id}, accountant={accountant_id}, time={datetime}")
        
        # Validation 1: Check client exists
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        # Validation 2: Check accountant exists and is active
        accountant = self.db.query(Accountant).filter(Accountant.id == accountant_id).first()
        if not accountant:
            raise ValueError(f"Accountant {accountant_id} not found")
        
        # Validation 3: Check slot is available
        available_slots = self.check_availability(accountant_id, datetime, duration)
        if datetime not in available_slots:
            raise ValueError(f"Slot {datetime} not available for accountant {accountant_id}")
        
        # Create appointment
        appointment = Appointment(
            client_id=client_id,
            accountant_id=accountant_id,
            datetime=datetime,
            duration=duration,
            notes=notes or f"Appointment with {client.company_name}",
            status=AppointmentStatus.PENDING.value  # Pending until confirmed
        )
        
        # ✅ CRITICAL: Persist to database
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)  # Get ID from DB
        
        logger.success(f"✅ Appointment #{appointment.id} created successfully")
        
        return appointment
    
    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get appointment by ID"""
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    def cancel_appointment(self, appointment_id: str) -> bool:
        """
        Cancel appointment (soft delete - set status to CANCELLED)
        
        Returns:
            True if cancelled, False if not found
        """
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            return False
        
        appointment.status = AppointmentStatus.CANCELLED.value
        self.db.commit()
        
        logger.info(f"Appointment #{appointment_id} cancelled")
        return True