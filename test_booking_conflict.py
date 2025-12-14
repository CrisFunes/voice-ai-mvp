"""
Test que el sistema detecta conflictos de horario
"""
from orchestrator import Orchestrator

print("="*70)
print("TEST: BOOKING CONFLICT DETECTION")
print("="*70)

orchestrator = Orchestrator()

# INTENTO 1: Crear appointment
print("\n📝 INTENTO 1: Crear appointment a las 15:00")
result1 = orchestrator.process(user_input="Vorrei un appuntamento domani alle 15:00")
print(result1.get('response', 'No response')[:200])

# INTENTO 2: Intentar crear OTRO appointment al MISMO horario
print("\n📝 INTENTO 2: Intentar crear OTRO appointment al MISMO horario")
result2 = orchestrator.process(user_input="Vorrei un appuntamento domani alle 15:00")
print(result2.get('response', 'No response')[:200])

# Análisis
if "confermato" in result1.get('response', '').lower():
    print("\n✅ Intento 1: Appointment creado")
else:
    print("\n⚠️ Intento 1: No se creó appointment")

if "error" in result2.get('response', '').lower() or "non" in result2.get('response', '').lower():
    print("✅ Intento 2: Sistema detectó conflicto correctamente")
else:
    print("❌ Intento 2: Sistema NO detectó conflicto (creó duplicado)")