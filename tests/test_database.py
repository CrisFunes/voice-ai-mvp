from database import get_db_session
from models import Accountant, Client, Appointment, OfficeInfo, AccountantStatus

def test_table_counts():
    with get_db_session() as session:
        counts = {
            'accountants': session.query(Accountant).count(),
            'clients': session.query(Client).count(),
            'appointments': session.query(Appointment).count(),
            'office_info': session.query(OfficeInfo).count()
        }
        
        # Demo DB can legitimately drift (e.g., repeated seeding, extra manual inserts), so we
        # assert minimum expected records rather than exact counts.
        assert counts['accountants'] >= 10, f"Expected >=10 accountants, got {counts['accountants']}"
        assert counts['clients'] >= 50, f"Expected >=50 clients, got {counts['clients']}"
        assert counts['appointments'] >= 30, f"Expected >=30 appointments, got {counts['appointments']}"
        assert counts['office_info'] >= 18, f"Expected >=18 office info, got {counts['office_info']}"
        
        print("✓ All table counts correct")
        

def test_accountant_distribution():
    with get_db_session() as session:
        tax_count = session.query(Accountant).filter(
            Accountant.specialization == "tax"
        ).count()
        
        active_count = session.query(Accountant).filter(
            Accountant.status == AccountantStatus.ACTIVE.value
        ).count()
        
        assert tax_count == 4, f"Expected 4 TAX specialists, got {tax_count}"
        assert active_count == 9, f"Expected 9 ACTIVE accountants, got {active_count}"
        
        print("✓ Accountant distribution correct")

def test_relationships():
    with get_db_session() as session:
        # Test client -> accountant relationship
        client = session.query(Client).first()
        assert client.accountant is not None, "Client missing accountant relationship"
        assert client.accountant_id == client.accountant.id, "FK mismatch"
        
        # Test appointment -> client/accountant relationships
        appointment = session.query(Appointment).first()
        assert appointment.client is not None, "Appointment missing client"
        assert appointment.accountant is not None, "Appointment missing accountant"
        
        print("✓ All relationships valid")

def test_tax_codes():
    with get_db_session() as session:
        clients = session.query(Client).all()
        
        for client in clients:
            tax_code = client.tax_code
            assert tax_code, f"Client {client.id} missing tax code"
            
            # Company tax code: 11 digits
            # Personal tax code: 16 alphanumeric
            assert len(tax_code) in [11, 16], f"Invalid tax code length: {tax_code}"
            
        print("✓ All tax codes valid")

def test_business_hours():
    with get_db_session() as session:
        appointments = session.query(Appointment).all()
        
        for appt in appointments:
            hour = appt.datetime.hour
            assert 9 <= hour < 18, f"Appointment outside business hours: {appt.datetime}"
            
        print("✓ All appointments within business hours (9-18)")

if __name__ == "__main__":
    print("="*70)
    print("DATABASE VERIFICATION TESTS")
    print("="*70)
    
    test_table_counts()
    test_accountant_distribution()
    test_relationships()
    test_tax_codes()
    test_business_hours()
    
    print("="*70)
    print("ALL TESTS PASSED ✓")
    print("="*70)
    with get_db_session() as session:
        counts = {
            'accountants': session.query(Accountant).count(),
            'clients': session.query(Client).count(),
            'appointments': session.query(Appointment).count(),
            'office_info': session.query(OfficeInfo).count()
        }

    print("\nDatabase Summary:")
    for table, count in counts.items():
        print(f"  {table}: {count} records")