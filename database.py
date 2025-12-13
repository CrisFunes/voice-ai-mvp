"""
Database Connection & Session Management
Supports SQLite (V.B) and PostgreSQL (V.A) via configuration
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import os
from pathlib import Path
from loguru import logger

import config
from models import Base

# ============================================================================
# ENGINE CONFIGURATION
# ============================================================================

def get_database_url() -> str:
    """
    Get database URL from environment or config.
    
    Returns appropriate connection string for SQLite or PostgreSQL.
    """
    # Check environment variable first (production override)
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        logger.info(f"Using DATABASE_URL from environment")
        return db_url
    
    # Default to SQLite for V.B
    sqlite_path = Path(__file__).parent / "demo_v2.db"
    db_url = f"sqlite:///{sqlite_path}"
    logger.info(f"Using SQLite database: {sqlite_path}")
    
    return db_url


def create_db_engine():
    """
    Create SQLAlchemy engine with appropriate configuration.
    
    CRITICAL: Different settings for SQLite vs PostgreSQL
    """
    database_url = get_database_url()
    
    # Detect database type
    is_sqlite = database_url.startswith("sqlite")
    is_postgres = database_url.startswith("postgresql")
    
    if is_sqlite:
        logger.info("Configuring SQLite engine...")
        
        # SQLite-specific configuration
        engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,  # Allow multi-threading
                "timeout": 30  # 30 second timeout for locks
            },
            poolclass=StaticPool,  # Single connection pool for SQLite
            echo=False  # Set to True for SQL debugging
        )
        
        # Enable foreign keys for SQLite (disabled by default)
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.close()
        
        logger.success("SQLite engine configured with foreign keys enabled")
    
    elif is_postgres:
        logger.info("Configuring PostgreSQL engine...")
        
        # PostgreSQL-specific configuration
        engine = create_engine(
            database_url,
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Max connections beyond pool_size
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False
        )
        
        logger.success("PostgreSQL engine configured with connection pooling")
    
    else:
        raise ValueError(
            f"Unsupported database type in URL: {database_url}\n"
            "Supported: sqlite:/// or postgresql://"
        )
    
    return engine


# Global engine instance (created once)
engine = create_db_engine()

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for database sessions.
    
    Usage in services:
        def my_service():
            db = next(get_db())
            try:
                # Use db
                result = db.query(Client).all()
                return result
            finally:
                db.close()
    
    Or with context manager:
        with get_db_session() as db:
            # Use db
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as db:
            client = db.query(Client).first()
            print(client.name)
    
    Automatically commits on success, rolls back on error.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error, rolling back: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db(drop_existing: bool = False) -> None:
    """
    Initialize database: create all tables.
    
    Args:
        drop_existing: If True, drop all tables first (DANGEROUS!)
    
    CRITICAL: Use this for V.B (SQLite). For V.A (PostgreSQL), use Alembic.
    """
    if drop_existing:
        logger.warning("⚠️  Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("All tables dropped")
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.success("✅ All tables created successfully")
    
    # Log table count
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    logger.info(f"Database has {len(table_names)} tables: {', '.join(table_names)}")


def reset_db() -> None:
    """
    DANGEROUS: Drop all tables and recreate.
    
    Only use in development!
    """
    logger.warning("🚨 RESETTING DATABASE - ALL DATA WILL BE LOST!")
    init_db(drop_existing=True)
    logger.success("Database reset complete")


def verify_db() -> dict:
    """
    Verify database connection and schema.
    
    Returns:
        Dictionary with verification results
    """
    results = {
        "connected": False,
        "tables_exist": False,
        "table_count": 0,
        "table_names": [],
        "error": None
    }
    
    try:
        # Test connection
        with engine.connect() as conn:
            results["connected"] = True
            logger.info("✅ Database connection successful")
        
        # Check tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        results["table_count"] = len(table_names)
        results["table_names"] = table_names
        results["tables_exist"] = len(table_names) > 0
        
        if results["tables_exist"]:
            logger.info(f"✅ Found {len(table_names)} tables")
        else:
            logger.warning("⚠️  No tables found. Run init_db() to create them.")
        
    except Exception as e:
        results["error"] = str(e)
        logger.error(f"❌ Database verification failed: {e}")
    
    return results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_table_counts() -> dict:
    """
    Get row counts for all tables.
    
    Useful for monitoring and debugging.
    """
    from models import Client, Accountant, Appointment, OfficeInfo, Lead
    
    counts = {}
    
    with get_db_session() as db:
        counts["clients"] = db.query(Client).count()
        counts["accountants"] = db.query(Accountant).count()
        counts["appointments"] = db.query(Appointment).count()
        counts["office_info"] = db.query(OfficeInfo).count()
        counts["leads"] = db.query(Lead).count()
        counts["total"] = sum(counts.values())
    
    return counts


def health_check() -> dict:
    """
    Comprehensive database health check.
    
    Returns status information for monitoring.
    """
    health = {
        "status": "unknown",
        "database_type": "sqlite" if "sqlite" in str(engine.url) else "postgresql",
        "connection": False,
        "tables": 0,
        "total_records": 0,
        "details": {}
    }
    
    try:
        # Connection test
        with engine.connect():
            health["connection"] = True
        
        # Table verification
        verify_result = verify_db()
        health["tables"] = verify_result["table_count"]
        
        # Record counts
        if health["tables"] > 0:
            counts = get_table_counts()
            health["total_records"] = counts["total"]
            health["details"] = counts
        
        # Overall status
        if health["connection"] and health["tables"] > 0:
            health["status"] = "healthy"
        elif health["connection"]:
            health["status"] = "connected_no_tables"
        else:
            health["status"] = "error"
    
    except Exception as e:
        health["status"] = "error"
        health["error"] = str(e)
        logger.error(f"Health check failed: {e}")
    
    return health


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("DATABASE.PY - Connection & Configuration Test")
    print("="*70)
    
    # Test 1: Connection
    print("\n1. Testing database connection...")
    verify_result = verify_db()
    
    if verify_result["connected"]:
        print(f"   ✅ Connected to database")
        print(f"   📊 Tables found: {verify_result['table_count']}")
        if verify_result["table_names"]:
            print(f"   📋 Tables: {', '.join(verify_result['table_names'])}")
    else:
        print(f"   ❌ Connection failed: {verify_result['error']}")
        exit(1)
    
    # Test 2: Initialize if needed
    if verify_result["table_count"] == 0:
        print("\n2. No tables found. Creating database schema...")
        init_db()
    else:
        print(f"\n2. Database schema already exists ({verify_result['table_count']} tables)")
    
    # Test 3: Session management
    print("\n3. Testing session management...")
    try:
        with get_db_session() as db:
            from models import Accountant, Specialization, AccountantStatus
            
            # Check if test accountant exists
            existing = db.query(Accountant).filter(
                Accountant.email == "test@database.py"
            ).first()
            
            if existing:
                print(f"   ℹ️  Test accountant already exists: {existing.name}")
            else:
                # Create test accountant
                test_acc = Accountant(
                    name="Test Accountant (database.py)",
                    email="test@database.py",
                    phone="+39 02 0000000",
                    specialization=Specialization.GENERAL.value,
                    status=AccountantStatus.ACTIVE.value
                )
                db.add(test_acc)
                db.commit()
                print(f"   ✅ Created test accountant: {test_acc.name}")
        
        print("   ✅ Session management working correctly")
    
    except Exception as e:
        print(f"   ❌ Session test failed: {e}")
        exit(1)
    
    # Test 4: Record counts
    print("\n4. Testing record counts...")
    try:
        counts = get_table_counts()
        print(f"   📊 Database Statistics:")
        print(f"      - Clients: {counts['clients']}")
        print(f"      - Accountants: {counts['accountants']}")
        print(f"      - Appointments: {counts['appointments']}")
        print(f"      - Office Info: {counts['office_info']}")
        print(f"      - Leads: {counts['leads']}")
        print(f"      - TOTAL: {counts['total']} records")
    except Exception as e:
        print(f"   ❌ Count test failed: {e}")
    
    # Test 5: Health check
    print("\n5. Running health check...")
    health = health_check()
    print(f"   Status: {health['status'].upper()}")
    print(f"   Database: {health['database_type']}")
    print(f"   Connection: {'✅' if health['connection'] else '❌'}")
    print(f"   Tables: {health['tables']}")
    print(f"   Records: {health['total_records']}")
    
    # Summary
    print("\n" + "="*70)
    if health['status'] == 'healthy':
        print("✅ ALL TESTS PASSED - database.py is working correctly!")
    else:
        print(f"⚠️  Status: {health['status']}")
    print("="*70)