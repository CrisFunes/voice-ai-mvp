"""
Seed Data Generator - Populate demo database with realistic Italian data
CRITICAL: Uses .value for all enum inserts/queries (SQLite compatibility)
"""
from datetime import datetime, timedelta
import random
from typing import List
from sqlalchemy.orm import Session

from database import get_db_session, init_db
from models import (
    Client, Accountant, Appointment, OfficeInfo, Lead, OfficeConfig,
    Specialization, AccountantStatus, AppointmentStatus, LeadCategory
)
from loguru import logger

# ============================================================================
# ITALIAN NAMES DATABASE
# ============================================================================

ITALIAN_FIRST_NAMES_MALE = [
    "Marco", "Giuseppe", "Antonio", "Francesco", "Alessandro", "Andrea",
    "Luca", "Paolo", "Giovanni", "Roberto", "Stefano", "Matteo",
    "Davide", "Simone", "Federico", "Riccardo", "Fabio", "Massimo"
]

ITALIAN_FIRST_NAMES_FEMALE = [
    "Maria", "Laura", "Anna", "Francesca", "Giulia", "Chiara",
    "Valentina", "Sara", "Elena", "Alessandra", "Silvia", "Martina",
    "Federica", "Giorgia", "Beatrice", "Sofia", "Camilla", "Elisa"
]

ITALIAN_LAST_NAMES = [
    "Rossi", "Ferrari", "Russo", "Bianchi", "Romano", "Gallo",
    "Costa", "Fontana", "Ricci", "Marino", "Greco", "Bruno",
    "Galli", "Conti", "De Luca", "Mancini", "Lombardi", "Moretti",
    "Barbieri", "Fontana", "Santoro", "Marini", "Rinaldi", "Caruso",
    "Ferrara", "Gatti", "Leone", "Longo", "Martinelli", "Vitale"
]

ITALIAN_COMPANY_TYPES = ["SRL", "SPA", "SAS", "SNC", "SRLS"]

ITALIAN_BUSINESS_SECTORS = [
    "Consulting", "Architects", "Engineering", "Import Export",
    "Restaurant", "Fashion", "Technology", "Construction",
    "Real Estate", "Manufacturing", "Retail", "Services"
]

MILAN_STREETS = [
    "Via Roma", "Via Dante", "Corso Buenos Aires", "Via Torino",
    "Via Montenapoleone", "Corso Venezia", "Via Manzoni", "Via Brera",
    "Via della Moscova", "Corso Magenta", "Via Solferino", "Via Vigevano"
]

# ============================================================================
# TAX CODE GENERATOR
# ============================================================================

def generate_company_tax_code() -> str:
    """Generate realistic Italian company tax code (11 digits)"""
    registration = random.randint(1000000, 9999999)
    office = random.randint(100, 999)
    check = random.randint(0, 9)
    return f"{registration:07d}{office:03d}{check}"


def generate_personal_tax_code(first_name: str, last_name: str) -> str:
    """Generate realistic Italian personal tax code (Codice Fiscale - 16 chars)"""
    first_name = first_name.strip().upper()
    last_name = last_name.strip().upper()
    
    last_consonants = ''.join([c for c in last_name if c.isalpha() and c not in 'AEIOU'])[:3]
    last_consonants = last_consonants.ljust(3, 'X')
    
    first_consonants = ''.join([c for c in first_name if c.isalpha() and c not in 'AEIOU'])[:3]
    first_consonants = first_consonants.ljust(3, 'X')
    
    birth_year = random.randint(60, 95)
    months = 'ABCDEHLMPRST'
    birth_month = random.choice(months)
    birth_day = random.randint(1, 31)
    if random.choice(['M', 'F']) == 'F':
        birth_day += 40
    
    municipality = 'F205'  # Milan
    check = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
    tax_code = f"{last_consonants}{first_consonants}{birth_year:02d}{birth_month}{birth_day:02d}{municipality}{check}"
    tax_code = tax_code.replace(' ', '').replace('\t', '').replace('\n', '')
    
    if len(tax_code) != 16:
        tax_code = tax_code[:16].ljust(16, 'X')
    
    return tax_code


# ============================================================================
# ACCOUNTANT GENERATION
# ============================================================================

def create_accountants(session: Session) -> List[Accountant]:
    """Create 10 accountants with different specializations"""
    logger.info("Creating accountants...")
    
    accountants_data = [
        # TAX specialists
        ("Marco", "Rossi", Specialization.TAX, AccountantStatus.ACTIVE),
        ("Laura", "Bianchi", Specialization.TAX, AccountantStatus.ACTIVE),
        ("Giuseppe", "Ferrari", Specialization.TAX, AccountantStatus.ACTIVE),
        ("Francesca", "Romano", Specialization.TAX, AccountantStatus.ACTIVE),
        
        # PAYROLL specialists
        ("Andrea", "Gallo", Specialization.PAYROLL, AccountantStatus.ACTIVE),
        ("Chiara", "Costa", Specialization.PAYROLL, AccountantStatus.ACTIVE),
        
        # CORPORATE specialists
        ("Paolo", "Marino", Specialization.CORPORATE, AccountantStatus.ACTIVE),
        ("Elena", "Greco", Specialization.CORPORATE, AccountantStatus.INACTIVE),
        
        # GENERAL accountants
        ("Davide", "Bruno", Specialization.GENERAL, AccountantStatus.ACTIVE),
        ("Valentina", "Conti", Specialization.GENERAL, AccountantStatus.ACTIVE),
    ]
    
    accountants = []
    
    for first_name, last_name, spec, status in accountants_data:
        title = "Dott." if random.choice([True, False]) else "Dott.ssa"
        
        accountant = Accountant(
            name=f"{title} {first_name} {last_name}",
            email=f"{first_name.lower()}.{last_name.lower()}@studiocommercialista.it",
            phone=f"+39 02 {random.randint(1000000, 9999999)}",
            specialization=spec.value,  # ✅ USE .value
            status=status.value  # ✅ USE .value
        )
        
        session.add(accountant)
        accountants.append(accountant)
    
    session.commit()
    logger.success(f"✅ Created {len(accountants)} accountants")
    
    return accountants


# ============================================================================
# CLIENT GENERATION
# ============================================================================

def create_clients(session: Session, accountants: List[Accountant]) -> List[Client]:
    """Create 50 clients (30 companies, 20 professionals)"""
    logger.info("Creating clients...")
    
    clients = []
    
    # 30 companies
    for i in range(30):
        company_type = random.choice(ITALIAN_COMPANY_TYPES)
        sector = random.choice(ITALIAN_BUSINESS_SECTORS)
        last_name = random.choice(ITALIAN_LAST_NAMES)
        
        company_name = f"{last_name} {sector} {company_type}"
        
        client = Client(
            company_name=company_name,
            tax_code=generate_company_tax_code(),
            phone=f"+39 02 {random.randint(1000000, 9999999)}",
            email=f"info@{last_name.lower()}{sector.lower().replace(' ', '')}.it",
            address=f"{random.choice(MILAN_STREETS)} {random.randint(1, 200)}, 20121 Milano",
            accountant_id=random.choice(accountants).id
        )
        
        session.add(client)
        clients.append(client)
    
    # 20 professionals
    for i in range(20):
        first_name = random.choice(ITALIAN_FIRST_NAMES_MALE + ITALIAN_FIRST_NAMES_FEMALE)
        last_name = random.choice(ITALIAN_LAST_NAMES)
        profession = random.choice(["Architetto", "Ingegnere", "Avvocato", "Medico", "Consulente"])
        
        client = Client(
            company_name=f"{first_name} {last_name} ({profession})",
            tax_code=generate_personal_tax_code(first_name, last_name),
            phone=f"+39 33{random.randint(10000000, 99999999)}",
            email=f"{first_name.lower()}.{last_name.lower()}@gmail.com",
            address=f"{random.choice(MILAN_STREETS)} {random.randint(1, 200)}, 20121 Milano",
            accountant_id=random.choice(accountants).id
        )
        
        session.add(client)
        clients.append(client)
    
    session.commit()
    logger.success(f"✅ Created {len(clients)} clients")
    
    return clients


# ============================================================================
# APPOINTMENT GENERATION
# ============================================================================

def create_appointments(
    session: Session, 
    clients: List[Client], 
    accountants: List[Accountant]
) -> List[Appointment]:
    """Create 30 appointments (15 past, 10 future, 5 cancelled)"""
    logger.info("Creating appointments...")
    
    # ✅ Query active accountants using .value
    active_accountants = session.query(Accountant).filter(
        Accountant.status == AccountantStatus.ACTIVE.value  # ✅ USE .value
    ).all()
    
    if not active_accountants:
        logger.warning("⚠️  No active accountants found, using all")
        active_accountants = accountants
    
    logger.info(f"Found {len(active_accountants)} active accountants")
    
    appointments = []
    
    def random_business_datetime(days_offset: int) -> datetime:
        """Generate datetime within business hours (9-18)"""
        base_date = datetime.now() + timedelta(days=days_offset)
        hour = random.randint(9, 17)
        minute = random.choice([0, 30])
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # 15 past appointments (COMPLETED)
    for i in range(15):
        days_ago = random.randint(-30, -1)
        
        appointment = Appointment(
            client_id=random.choice(clients).id,
            accountant_id=random.choice(active_accountants).id,
            datetime=random_business_datetime(days_ago),
            duration=random.choice([30, 60, 90]),
            notes=random.choice([
                "Consulenza fiscale",
                "Revisione bilancio",
                "Dichiarazione IVA",
                "Paghe mensili",
                "Apertura partita IVA"
            ]),
            status=AppointmentStatus.COMPLETED.value  # ✅ USE .value
        )
        
        session.add(appointment)
        appointments.append(appointment)
    
    # 10 future appointments (CONFIRMED)
    for i in range(10):
        days_ahead = random.randint(1, 30)
        
        appointment = Appointment(
            client_id=random.choice(clients).id,
            accountant_id=random.choice(active_accountants).id,
            datetime=random_business_datetime(days_ahead),
            duration=random.choice([30, 60, 90]),
            notes=random.choice([
                "Consulenza fiscale",
                "Pianificazione tributaria",
                "Dichiarazione redditi",
                "Verifica F24",
                "Consulenza societaria"
            ]),
            status=AppointmentStatus.CONFIRMED.value  # ✅ USE .value
        )
        
        session.add(appointment)
        appointments.append(appointment)
    
    # 5 cancelled appointments
    for i in range(5):
        days_offset = random.randint(-15, 15)
        
        appointment = Appointment(
            client_id=random.choice(clients).id,
            accountant_id=random.choice(accountants).id,  # All accountants
            datetime=random_business_datetime(days_offset),
            duration=60,
            notes="Appuntamento cancellato",
            status=AppointmentStatus.CANCELLED.value  # ✅ USE .value
        )
        
        session.add(appointment)
        appointments.append(appointment)
    
    session.commit()
    logger.success(f"✅ Created {len(appointments)} appointments")
    
    return appointments


# ============================================================================
# OFFICE INFO GENERATION
# ============================================================================

def create_office_info(session: Session) -> List[OfficeInfo]:
    """Create office information entries"""
    logger.info("Creating office info...")
    
    office_data = [
        # Office hours
        ("office_hours_monday", "09:00-18:00", "hours"),
        ("office_hours_tuesday", "09:00-18:00", "hours"),
        ("office_hours_wednesday", "09:00-18:00", "hours"),
        ("office_hours_thursday", "09:00-18:00", "hours"),
        ("office_hours_friday", "09:00-17:00", "hours"),
        ("office_hours_saturday", "09:00-13:00", "hours"),
        ("office_hours_sunday", "closed", "hours"),
        
        # Contact
        ("office_phone", "+39 02 1234567", "contact"),
        ("office_email", "info@studiocommercialista.it", "contact"),
        ("office_pec", "studio@pec.commercialista.it", "contact"),
        ("office_fax", "+39 02 7654321", "contact"),
        
        # Address
        ("office_address", "Via Roma 123, 20121 Milano (MI)", "address"),
        ("office_metro", "Duomo (M1/M3)", "address"),
        ("office_parking", "Via Torino 45", "address"),
        
        # Notices
        ("august_closure", "Chiuso dal 5 al 25 agosto", "notice"),
        ("christmas_closure", "Chiuso dal 24 dicembre al 6 gennaio", "notice"),
        ("emergency_contact", "+39 333 1234567 (solo urgenze)", "notice"),
        ("appointment_policy", "Appuntamenti richiesti, no walk-in", "policy"),
    ]
    
    office_info_list = []
    
    for key, value, category in office_data:
        info = OfficeInfo(
            key=key,
            value=value,
            category=category
        )
        
        session.add(info)
        office_info_list.append(info)
    
    session.commit()
    logger.success(f"✅ Created {len(office_info_list)} office info entries")
    
    return office_info_list


def create_office_config(session: Session) -> List[OfficeConfig]:
    """Create generic office configuration entries"""
    logger.info("Creating office config...")

    config_data = [
        ("office_name", "Studio Commercialista Rossi & Bianchi", "meta", "Denominazione ufficio"),
        ("office_address", "Via Roma 123, 20121 Milano (MI)", "address", "Indirizzo principale"),
        ("office_phone", "+39 02 1234567", "contact", "Numero fisso"),
        ("office_mobile", "+39 333 1234567", "contact", "Numero mobile urgenze"),
        ("office_email", "info@studiocommercialista.it", "contact", "Email principale"),
        ("office_hours_weekday", "09:00-18:00", "hours", "Orario lun-ven"),
        ("office_hours_saturday", "09:00-13:00", "hours", "Orario sabato"),
        ("office_hours_sunday", "closed", "hours", "Chiuso domenica"),
        ("holiday_notice", "Chiuso dal 24 dicembre al 6 gennaio", "notice", "Chiusura natalizia"),
    ]

    configs = []
    for key, value, category, description in config_data:
        cfg = OfficeConfig(
            key=key,
            value=value,
            category=category,
            description=description
        )
        session.add(cfg)
        configs.append(cfg)

    session.commit()
    logger.success(f"✅ Created {len(configs)} office config entries")
    return configs


# ============================================================================
# MAIN SEEDING
# ============================================================================

def seed_database(drop_existing: bool = False):
    """Main function to seed database with all demo data"""
    logger.info("="*70)
    logger.info("DATABASE SEEDING - STARTING")
    logger.info("="*70)
    
    if drop_existing:
        logger.warning("⚠️  Dropping existing tables...")
        from database import reset_db
        reset_db()
    else:
        init_db()
    
    with get_db_session() as session:
        accountants = create_accountants(session)
        clients = create_clients(session, accountants)
        appointments = create_appointments(session, clients, accountants)
        office_info = create_office_info(session)
        office_config = create_office_config(session)
    
    logger.info("="*70)
    logger.success("DATABASE SEEDING - COMPLETE")
    logger.info("="*70)
    logger.info(f"📊 Summary:")
    logger.info(f"   - Accountants: {len(accountants)}")
    logger.info(f"   - Clients: {len(clients)}")
    logger.info(f"   - Appointments: {len(appointments)}")
    logger.info(f"   - Office Info: {len(office_info)}")
    logger.info(f"   - Office Config: {len(office_config)}")
    logger.info("="*70)
    
    from database import get_table_counts
    counts = get_table_counts()
    logger.info("\n📋 Table Verification:")
    for table, count in counts.items():
        logger.info(f"   {table}: {count} records")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("SEED_DATA.PY - Database Population Script")
    print("="*70)
    print("\n⚠️  WARNING: This will populate the database with demo data.")
    print("\nOptions:")
    print("1. Seed without dropping (add to existing data)")
    print("2. Reset database and seed fresh (DESTRUCTIVE)")
    print("3. Cancel")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        print("\n🌱 Seeding database (preserving existing data)...")
        seed_database(drop_existing=False)
    elif choice == "2":
        confirm = input("⚠️  This will DELETE ALL DATA. Type 'YES' to confirm: ").strip()
        if confirm == "YES":
            print("\n🔄 Resetting and seeding database...")
            seed_database(drop_existing=True)
        else:
            print("❌ Cancelled")
    else:
        print("❌ Cancelled")