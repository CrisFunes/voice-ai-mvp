"""
Test con horario que sabemos está libre
"""
from orchestrator import Orchestrator
from database import get_db_session
from models import Appointment
from datetime import datetime, timedelta

print("="*70)
print("TEST: BOOKING EN HORARIO LIBRE")
print("="*70)

# PASO 1: Encontrar un horario libre
print("\n🔍 Buscando horarios libres para mañana...")
tomorrow = datetime.now() + timedelta(days=1)

with get_db_session() as db:
    count_before = db.query(Appointment).count()
    print(f"📊 Appointments en DB ANTES: {count_before}")
    
    # Check slots 10:00, 11:00, 14:00, 16:00
    test_slots = [10, 11, 14, 16]
    free_slot = None
    
    for hour in test_slots:
        test_time = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
        existing = db.query(Appointment).filter(
            Appointment.datetime == test_time
        ).count()
        
        if existing == 0:
            free_slot = hour
            print(f"✅ Slot libre encontrado: {hour}:00")
            break
        else:
            print(f"❌ Slot ocupado: {hour}:00")
    
    if not free_slot:
        print("⚠️ Todos los slots probados están ocupados. Usando 9:00")
        free_slot = 9

# PASO 2: Crear appointment en slot libre
print(f"\n🤖 Intentando crear appointment a las {free_slot}:00...")

orchestrator = Orchestrator()
user_input = f"Vorrei un appuntamento domani alle {free_slot}"
print(f"💬 User input: '{user_input}'")

result = orchestrator.process(user_input=user_input)

print(f"\n📌 Intent: {result.get('intent')}")
print(f"📌 Action: {result.get('action_taken')}")
print(f"\n🗣️ Response:")
print("-" * 70)
print(result.get('response'))
print("-" * 70)

# PASO 3: Verificar DB
print("\n🔍 Verificando base de datos...")
with get_db_session() as db:
    count_after = db.query(Appointment).count()
    print(f"📊 Appointments en DB DESPUÉS: {count_after}")
    
    if count_after > count_before:
        print(f"\n✅ ¡ÉXITO! Appointment creado")
        
        newest = db.query(Appointment).order_by(
            Appointment.created_at.desc()
        ).first()
        
        print(f"\n📋 DETALLES DEL NUEVO APPOINTMENT:")
        print(f"🆔 ID: {newest.id}")
        print(f"📅 DateTime: {newest.datetime}")
        print(f"👤 Cliente: {newest.client.company_name}")
        print(f"👨‍💼 Comercialista: {newest.accountant.name}")
        print(f"📝 Notas: {newest.notes}")
        print(f"📊 Status: {newest.status}")
        
    else:
        print(f"\n❌ FALLO: No se creó appointment")
        print(f"Error: {result.get('error', 'Unknown')}")

print("\n" + "="*70)