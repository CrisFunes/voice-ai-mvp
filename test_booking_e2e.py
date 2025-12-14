"""
Test END-TO-END: Booking flow con verificación manual de DB
"""
from orchestrator import Orchestrator
from database import get_db_session
from models import Appointment
from datetime import datetime

print("="*70)
print("TEST END-TO-END: BOOKING FLOW")
print("="*70)

# PASO 1: Ver estado inicial
print("\n🔍 PASO 1: Verificando estado ANTES del test...")
with get_db_session() as db:
    count_before = db.query(Appointment).count()
    print(f"📊 Appointments en DB ANTES: {count_before}")

# PASO 2: Ejecutar orchestrator con booking request
print("\n🤖 PASO 2: Ejecutando orchestrator con booking request...")

orchestrator = Orchestrator()

# Simular input del usuario
user_input = "Vorrei un appuntamento domani alle 15:00"
print(f"💬 User input: '{user_input}'")

try:
    # Procesar
    result = orchestrator.process(user_input=user_input)
    
    print(f"\n✅ Orchestrator procesó exitosamente")
    print(f"📌 Intent detectado: {result.get('intent', 'UNKNOWN')}")
    print(f"📌 Action tomada: {result.get('action_taken', 'NONE')}")
    print(f"\n🗣️ Respuesta del sistema:")
    print("-" * 70)
    print(result.get('response', 'No response'))
    print("-" * 70)
    
except Exception as e:
    print(f"\n❌ ERROR durante procesamiento: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# PASO 3: Verificar DB después del test
print("\n🔍 PASO 3: Verificando estado DESPUÉS del test...")
with get_db_session() as db:
    count_after = db.query(Appointment).count()
    print(f"📊 Appointments en DB DESPUÉS: {count_after}")
    
    # Verificación crítica
    if count_after > count_before:
        new_appointments = count_after - count_before
        print(f"\n✅ ¡ÉXITO! Se crearon {new_appointments} nuevo(s) appointment(s)")
        
        # Mostrar el nuevo appointment
        print("\n📋 NUEVO APPOINTMENT CREADO:\n")
        newest = db.query(Appointment).order_by(
            Appointment.created_at.desc()
        ).first()
        
        print(f"🆔 ID: {newest.id}")
        print(f"👤 Cliente: {newest.client.company_name if newest.client else 'N/A'}")
        print(f"👨‍💼 Comercialista: {newest.accountant.name if newest.accountant else 'N/A'}")
        print(f"📅 Fecha: {newest.datetime.strftime('%d/%m/%Y')}")
        print(f"🕐 Hora: {newest.datetime.strftime('%H:%M')}")
        print(f"⏱️ Duración: {newest.duration} minutos")
        print(f"📝 Notas: {newest.notes}")
        print(f"📊 Status: {newest.status}")
        print(f"🕐 Creado el: {newest.created_at}")
        
    else:
        print(f"\n❌ FALLO: No se creó ningún appointment nuevo")
        print(f"   Count antes: {count_before}")
        print(f"   Count después: {count_after}")

print("\n" + "="*70)
print("TEST COMPLETO")
print("="*70)