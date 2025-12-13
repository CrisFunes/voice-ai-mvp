"""
Database Models - Production-Ready SQLAlchemy ORM
Compatible with SQLite (V.B) and PostgreSQL (V.A)
"""
from sqlalchemy import (
    Column, String, DateTime, Integer, Boolean, Text,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base, validates
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum as PyEnum
import uuid
import re

Base = declarative_base()

# ============================================================================
# ENUMS - Business Logic Constants
# ============================================================================

class AppointmentStatus(PyEnum):
    """Appointment lifecycle states"""
    PENDING = "pending"        # Created but not confirmed
    CONFIRMED = "confirmed"    # Confirmed by client/accountant
    CANCELLED = "cancelled"    # Cancelled by either party
    COMPLETED = "completed"    # Appointment happened
    NO_SHOW = "no_show"       # Client didn't show up

class Specialization(PyEnum):
    """Accountant specializations"""
    TAX = "tax"              # Fiscalista (IVA, IRES, dichiarazioni)
    PAYROLL = "payroll"      # Consulente del lavoro (paghe, contributi)
    CORPORATE = "corporate"  # Societario (bilanci, SPA)
    GENERAL = "general"      # Commercialista generico

class AccountantStatus(PyEnum):
    """Accountant availability status"""
    ACTIVE = "active"        # Currently working
    INACTIVE = "inactive"    # On leave/sabbatical
    VACATION = "vacation"    # On vacation

class LeadCategory(PyEnum):
    """Lead classification for new prospects"""
    NEW_BUSINESS = "new_business"      # New company formation
    NEW_FREELANCE = "new_freelance"    # New professional
    TAX_ISSUE = "tax_issue"            # Existing client, problem
    COMPETITOR_SWITCH = "competitor_switch"  # Switching accountant
    INFORMATION = "information"        # Just asking questions

# ============================================================================
# HELPER: UUID Column (SQLite/PostgreSQL compatible)
# ============================================================================

def UUID(as_uuid=True):
    """
    Returns UUID column type compatible with both SQLite and PostgreSQL.
    
    CRITICAL: SQLite doesn't have native UUID type, stores as CHAR(32).
    PostgreSQL has native UUID type.
    This function handles both transparently.
    """
    import sys
    # Check if we're using PostgreSQL
    if 'postgresql' in sys.modules:
        return PG_UUID(as_uuid=as_uuid)
    else:
        # SQLite fallback
        return String(32)

# ============================================================================
# MODELS
# ============================================================================

class Client(Base):
    """
    Client/Company entity
    
    Represents companies or individuals that are clients of the accounting firm.
    Each client has an assigned accountant and can have multiple appointments.
    """
    __tablename__ = "clients"
    
    # Primary Key
    id = Column(
        String(36),  # UUID as string for SQLite compatibility
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Business Data
    company_name = Column(
        String(200),
        nullable=False,
        index=True,  # Frequent searches by name
        comment="Company name or individual name"
    )
    
    tax_code = Column(
        String(16),
        unique=True,
        index=True,
        nullable=False,
        comment="Italian fiscal code (Codice Fiscale or Partita IVA)"
    )
    
    # Contact Information
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(300), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, 
        default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True, comment="Internal notes about client")
    
    # Foreign Keys
    accountant_id = Column(
        String(36),
        ForeignKey("accountants.id", ondelete="SET NULL"),
        nullable=True,
        comment="Assigned accountant"
    )
    
    # Relationships
    assigned_accountant = relationship(
        "Accountant",
        back_populates="clients",
        foreign_keys=[accountant_id]
    )
    appointments = relationship(
        "Appointment",
        back_populates="client",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_client_name_active', 'company_name', 'is_active'),
        Index('idx_client_taxcode', 'tax_code'),
    )
    
    # Validations
    @validates('tax_code')
    def validate_tax_code(self, key, value):
        """
        Validate Italian tax code format.
        
        CRITICAL: Italian tax codes are either:
        - 11 digits (Partita IVA for companies)
        - 16 alphanumeric (Codice Fiscale for individuals)
        """
        if not value:
            raise ValueError("Tax code is required")
        
        value = value.strip().upper()
        
        # Partita IVA: 11 digits
        if re.match(r'^\d{11}$', value):
            return value
        
        # Codice Fiscale: 16 alphanumeric
        if re.match(r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$', value):
            return value
        
        raise ValueError(
            f"Invalid tax code format: {value}. "
            "Expected 11 digits (P.IVA) or 16 alphanumeric (C.F.)"
        )
    
    @validates('email')
    def validate_email(self, key, value):
        """Basic email validation"""
        if value and '@' not in value:
            raise ValueError(f"Invalid email format: {value}")
        return value
    
    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.company_name}', tax_code='{self.tax_code}')>"


class Accountant(Base):
    """
    Accountant/Commercialista entity
    
    Represents accountants working at the firm. Each has specialization
    and can be assigned to multiple clients.
    """
    __tablename__ = "accountants"
    
    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Personal Data
    name = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Full name (e.g., 'Dott. Marco Rossi')"
    )
    
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    
    # Professional Data
    specialization = Column(
        String(20),
        nullable=False,
        default=Specialization.GENERAL.value,
        comment="Primary area of expertise"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default=AccountantStatus.ACTIVE.value,
        comment="Current availability status"
    )
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    bio = Column(
        Text,
        nullable=True,
        comment="Professional bio for client-facing materials"
    )
    
    # Relationships
    clients = relationship(
        "Client",
        back_populates="assigned_accountant",
        foreign_keys=[Client.accountant_id]
    )
    
    appointments = relationship(
        "Appointment",
        back_populates="accountant",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_accountant_status_spec', 'status', 'specialization'),
        CheckConstraint(
            f"specialization IN {tuple(s.value for s in Specialization)}",
            name='valid_specialization'
        ),
        CheckConstraint(
            f"status IN {tuple(s.value for s in AccountantStatus)}",
            name='valid_status'
        ),
    )
    
    @validates('specialization')
    def validate_specialization(self, key, value):
        """Ensure specialization is valid enum value"""
        if isinstance(value, Specialization):
            return value.value
        if value not in [s.value for s in Specialization]:
            raise ValueError(f"Invalid specialization: {value}")
        return value
    
    @validates('status')
    def validate_status(self, key, value):
        """Ensure status is valid enum value"""
        if isinstance(value, AccountantStatus):
            return value.value
        if value not in [s.value for s in AccountantStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value
    
    def __repr__(self):
        return f"<Accountant(id={self.id}, name='{self.name}', specialization='{self.specialization}')>"


class Appointment(Base):
    """
    Appointment/Appuntamento entity
    
    Represents scheduled meetings between clients and accountants.
    """
    __tablename__ = "appointments"
    
    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Foreign Keys
    client_id = Column(
        String(36),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    accountant_id = Column(
        String(36),
        ForeignKey("accountants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Appointment Details
    datetime = Column(
        DateTime,
        nullable=False,
        index=True,
        comment="Scheduled date and time"
    )
    
    duration_minutes = Column(
        Integer,
        nullable=False,
        default=60,
        comment="Duration in minutes (30, 60, 90, 120)"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default=AppointmentStatus.PENDING.value,
        index=True
    )
    
    # Additional Info
    subject = Column(
        String(200),
        nullable=True,
        comment="Appointment subject/reason"
    )
    
    notes = Column(
        Text,
        nullable=True,
        comment="Internal notes"
    )
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    accountant = relationship("Accountant", back_populates="appointments")
    
    # Constraints & Indexes
    __table_args__ = (
        Index('idx_appointment_datetime_status', 'datetime', 'status'),
        Index('idx_appointment_accountant_datetime', 'accountant_id', 'datetime'),
        CheckConstraint(
            'duration_minutes IN (30, 60, 90, 120)',
            name='valid_duration'
        ),
        CheckConstraint(
            f"status IN {tuple(s.value for s in AppointmentStatus)}",
            name='valid_appointment_status'
        ),
    )
    
    @validates('datetime')
    def validate_datetime(self, key, value):
        """Ensure appointment is not in the past"""
        if value < datetime.now():
            raise ValueError("Cannot create appointment in the past")
        
        # Business hours check (9:00 - 18:00)
        if not (9 <= value.hour < 18):
            raise ValueError(
                f"Appointment must be during business hours (9:00-18:00). "
                f"Requested: {value.hour}:00"
            )
        
        return value
    
    @validates('duration_minutes')
    def validate_duration(self, key, value):
        """Ensure duration is valid"""
        if value not in (30, 60, 90, 120):
            raise ValueError(
                f"Invalid duration: {value}. "
                "Must be 30, 60, 90, or 120 minutes."
            )
        return value
    
    @validates('status')
    def validate_status(self, key, value):
        """Ensure status is valid enum value"""
        if isinstance(value, AppointmentStatus):
            return value.value
        if value not in [s.value for s in AppointmentStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value
    
    def __repr__(self):
        return (
            f"<Appointment(id={self.id}, "
            f"client='{self.client.company_name if self.client else 'Unknown'}', "
            f"datetime={self.datetime}, status='{self.status}')>"
        )


class OfficeInfo(Base):
    """
    Office Information key-value store
    
    Stores configurable office information like hours, contact details, etc.
    This allows easy updates without code changes.
    """
    __tablename__ = "office_info"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Key-Value
    key = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Configuration key (e.g., 'office_hours_monday')"
    )
    
    value = Column(
        Text,
        nullable=False,
        comment="Configuration value"
    )
    
    category = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Grouping category (e.g., 'hours', 'contact', 'address')"
    )
    
    description = Column(
        String(200),
        nullable=True,
        comment="Human-readable description of this setting"
    )
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<OfficeInfo(key='{self.key}', value='{self.value[:50]}...')>"


class Lead(Base):
    """
    Lead/Prospect entity
    
    Stores information about potential new clients who contact the firm.
    Used for lead capture and follow-up.
    """
    __tablename__ = "leads"
    
    # Primary Key
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Contact Information
    name = Column(String(200), nullable=True)
    company_name = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Lead Classification
    category = Column(
        String(30),
        nullable=False,
        default=LeadCategory.INFORMATION.value,
        index=True
    )
    
    source = Column(
        String(50),
        nullable=False,
        default="voice_ai",
        comment="How lead was captured (voice_ai, website, referral, etc)"
    )
    
    # Interaction Details
    initial_query = Column(
        Text,
        nullable=True,
        comment="First question/request from lead"
    )
    
    notes = Column(Text, nullable=True)
    
    # Status
    is_converted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether lead became a client"
    )
    
    converted_to_client_id = Column(
        String(36),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    converted_client = relationship("Client")
    
    # Constraints
    __table_args__ = (
        Index('idx_lead_category_converted', 'category', 'is_converted'),
        CheckConstraint(
            f"category IN {tuple(c.value for c in LeadCategory)}",
            name='valid_lead_category'
        ),
    )
    
    @validates('category')
    def validate_category(self, key, value):
        """Ensure category is valid enum value"""
        if isinstance(value, LeadCategory):
            return value.value
        if value not in [c.value for c in LeadCategory]:
            raise ValueError(f"Invalid lead category: {value}")
        return value
    
    def __repr__(self):
        return (
            f"<Lead(id={self.id}, name='{self.name}', "
            f"category='{self.category}', converted={self.is_converted})>"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def init_db(engine):
    """
    Create all tables in database.
    
    Usage:
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///demo.db")
        init_db(engine)
    """
    Base.metadata.create_all(engine)


def drop_all(engine):
    """
    Drop all tables. USE WITH CAUTION!
    
    Only for development/testing.
    """
    Base.metadata.drop_all(engine)


if __name__ == "__main__":
    # Quick test: Create tables in SQLite
    from sqlalchemy import create_engine
    
    print("Testing models.py...")
    
    engine = create_engine("sqlite:///test.db", echo=True)
    
    print("\n1. Creating tables...")
    init_db(engine)
    
    print("\n2. Creating test records...")
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Test accountant
    acc = Accountant(
        name="Dott. Marco Rossi",
        email="marco.rossi@studio.it",
        phone="+39 02 1234567",
        specialization=Specialization.TAX.value,
        status=AccountantStatus.ACTIVE.value
    )
    session.add(acc)
    session.commit()
    print(f"✅ Created accountant: {acc}")
    
    # Test client
    client = Client(
        company_name="Rossi Consulting SRL",
        tax_code="12345678901",  # 11 digits = P.IVA
        phone="+39 02 9876543",
        email="info@rossiconsulting.it",
        accountant_id=acc.id
    )
    session.add(client)
    session.commit()
    print(f"✅ Created client: {client}")
    
    # Test appointment
    from datetime import datetime, timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    
    apt = Appointment(
        client_id=client.id,
        accountant_id=acc.id,
        datetime=tomorrow,
        duration_minutes=60,
        subject="Tax consultation",
        status=AppointmentStatus.PENDING.value
    )
    session.add(apt)
    session.commit()
    print(f"✅ Created appointment: {apt}")
    
    print("\n3. Testing queries...")
    clients = session.query(Client).all()
    print(f"Clients in DB: {len(clients)}")
    
    appointments = session.query(Appointment).filter(
        Appointment.status == AppointmentStatus.PENDING.value
    ).all()
    print(f"Pending appointments: {len(appointments)}")
    
    print("\n✅ All tests passed! models.py is working correctly.")
    
    # Cleanup
    import os
    session.close()
    engine.dispose()
    
    # Wait a moment for Windows to release the lock
    import time
    time.sleep(0.5)
    
    # Cleanup (with better error handling)
    import os
    try:
        if os.path.exists("test.db"):
            os.remove("test.db")
            print("\n🗑️  Test database cleaned up.")
    except PermissionError:
        print("\n⚠️  Could not delete test.db (Windows lock). Delete manually.")
        print("   Run: Remove-Item test.db -Force")