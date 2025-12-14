"""
Verificar estado de appointments ANTES del test
"""
from database import get_db_session
from models import Appointment
from datetime import datetime

print("="*70)
print("ESTADO DE LA BASE DE DATOS - ANTES DEL TEST")
print("="*70)

with get_db_session() as db:
    # Count total appointments
    total = db.query(Appointment).count()
    print(f"\n📊 Total appointments en DB: {total}")
    
    # Show last 5 appointments
    print("\n📋 Últimos 5 appointments (seed data):\n")
    appointments = db.query(Appointment).order_by(
        Appointment.created_at.desc()
    ).limit(5).all()
    
    for apt in appointments:
        print(f"ID: {apt.id}")
        print(f"  Cliente: {apt.client.company_name if apt.client else 'N/A'}")
        print(f"  Comercialista: {apt.accountant.name if apt.accountant else 'N/A'}")
        print(f"  Fecha/Hora: {apt.datetime}")
        print(f"  Status: {apt.status}")
        print(f"  Notas: {apt.notes}")
        print(f"  Creado: {apt.created_at}")
        print("-" * 50)
    
    # Count by status
    from models import AppointmentStatus
    for status in AppointmentStatus:
        count = db.query(Appointment).filter(
            Appointment.status == status.value
        ).count()
        print(f"  {status.value}: {count}")

print("\n" + "="*70)
print("GUARDA ESTE NÚMERO: Total appointments = ", total)
print("="*70)