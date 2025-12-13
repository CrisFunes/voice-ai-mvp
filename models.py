"""
SQLAlchemy Models for Voice AI Agent Demo V2
Optimized for SQLite: Enums stored as strings with valid SQL CHECK constraints.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Text, 
    Boolean, Index, CheckConstraint, func
)
from sqlalchemy.orm import declarative_base, relationship, validates

# ============================================================================
# BASE
# ============================================================================

Base = declarative_base()

# ============================================================================
# ENUMS (Python side)
# ============================================================================

class Specialization(str, PyEnum):
    TAX = "tax"
    PAYROLL = "payroll"
    CORPORATE = "corporate"
    GENERAL = "general"

class AccountantStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class AppointmentStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class LeadCategory(str, PyEnum):
    NEW_BUSINESS = "new_business"
    NEW_FREELANCE = "new_freelance"
    TAX_ISSUE = "tax_issue"
    COMPETITOR_SWITCH = "competitor_switch"
    INFORMATION = "information"

# ============================================================================
# MODELS
# ============================================================================

class Accountant(Base):
    """Accountant/Commercialista working at the firm"""
    __tablename__ = "accountants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    
    specialization = Column(String(50), nullable=False, default=Specialization.GENERAL.value)
    status = Column(String(20), nullable=False, default=AccountantStatus.ACTIVE.value)
    
    bio = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    clients = relationship("Client", back_populates="accountant")
    appointments = relationship("Appointment", back_populates="accountant", cascade="all, delete-orphan")

    # FIX: Use tuple() to ensure SQL uses parentheses () instead of brackets []
    __table_args__ = (
        CheckConstraint(
            f"specialization IN {tuple(s.value for s in Specialization)}", 
            name='valid_spec'
        ),
        CheckConstraint(
            f"status IN {tuple(s.value for s in AccountantStatus)}", 
            name='valid_status'
        ),
    )

    def __repr__(self):
        return f"<Accountant {self.name} ({self.specialization})>"


class Client(Base):
    """Client company or individual professional"""
    __tablename__ = "clients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(200), nullable=False)
    tax_code = Column(String(16), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    address = Column(String(300), nullable=True)
    
    accountant_id = Column(String(36), ForeignKey("accountants.id"), nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    accountant = relationship("Accountant", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client")

    def __repr__(self):
        return f"<Client {self.company_name} ({self.tax_code})>"


class Appointment(Base):
    """Scheduled appointment between client and accountant"""
    __tablename__ = "appointments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    accountant_id = Column(String(36), ForeignKey("accountants.id", ondelete="CASCADE"), nullable=False)
    
    datetime = Column(DateTime, nullable=False, index=True)
    duration = Column(Integer, nullable=False, default=60) # Matches 'duration' in seed_data.py
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=AppointmentStatus.PENDING.value)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    accountant = relationship("Accountant", back_populates="appointments")

    __table_args__ = (
        CheckConstraint(
            f"status IN {tuple(s.value for s in AppointmentStatus)}", 
            name='valid_appointment_status'
        ),
    )

    def __repr__(self):
        return f"<Appointment {self.datetime} - {self.status}>"


class OfficeInfo(Base):
    """Office information key-value store"""
    __tablename__ = "office_info"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String(50), nullable=True, index=True)
    description = Column(String(200), nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<OfficeInfo {self.key}={self.value[:30]}>"


class Lead(Base):
    """Lead/potential new client"""
    __tablename__ = "leads"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    company_name = Column(String(200), nullable=True)
    
    category = Column(String(50), nullable=False, default=LeadCategory.INFORMATION.value)
    notes = Column(Text, nullable=True)
    source = Column(String(50), nullable=True, default="voice_ai")
    
    contacted = Column(Boolean, default=False)
    is_converted = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"category IN {tuple(c.value for c in LeadCategory)}", 
            name='valid_lead_category'
        ),
    )
    
    def __repr__(self):
        return f"<Lead {self.name or self.company_name} ({self.category})>"

# ============================================================================
# INITIALIZATION UTILITY
# ============================================================================

def init_db(engine):
    """Create all tables defined in the Base."""
    Base.metadata.create_all(engine)