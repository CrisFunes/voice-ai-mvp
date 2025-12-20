#!/usr/bin/env python3
"""
Manual Test Script - Simula conversaciones completas
=====================================================

Script interactivo para probar diferentes flujos de conversación
sin necesidad de hacer llamadas reales.

Ejecutar: python test_twilio_manual.py
"""

if __name__ != "__main__":
    import pytest

    pytest.skip(
        "Manual interactive script (not an automated test). Run: python tests/test_twilio_manual.py",
        allow_module_level=True,
    )

import sys
import time
import requests
from loguru import logger

BASE_URL = "http://localhost:5000"

# ============================================================================
# ESCENARIOS DE PRUEBA
# ============================================================================

SCENARIOS = {
    "1": {
        "name": "Consulta rápida de horarios (CACHE HIT)",
        "description": "Pregunta simple que debería resolverse con cache",
        "conversation": [
            {"user": "orari", "expected_latency": 500},  # Cache debe ser <500ms
        ]
    },
    "2": {
        "name": "Reserva de cita",
        "description": "Flujo completo de booking",
        "conversation": [
            {"user": "Vorrei prenotare un appuntamento", "expected_latency": 3000},
            {"user": "Martedì alle 10", "expected_latency": 3000},
            {"user": "Mario Rossi", "expected_latency": 3000},
            {"user": "grazie", "expected_latency": 1000},  # Farewell
        ]
    },
    "3": {
        "name": "Consulta fiscal compleja",
        "description": "Pregunta que requiere RAG",
        "conversation": [
            {"user": "Come funziona la deduzione IVA per le auto aziendali?", "expected_latency": 4000},
            {"user": "E per le spese di carburante?", "expected_latency": 4000},
            {"user": "grazie mille", "expected_latency": 1000},
        ]
    },
    "4": {
        "name": "Test de interrupciones",
        "description": "Usuario cambia de tema abruptamente",
        "conversation": [
            {"user": "Vorrei sapere gli orari", "expected_latency": 3000},
            {"user": "Ah no aspetta, voglio prenotare un appuntamento invece", "expected_latency": 3000},
            {"user": "ciao", "expected_latency": 1000},
        ]
    },
    "5": {
        "name": "Input vacío/silencio",
        "description": "Simula cuando el usuario no habla",
        "conversation": [
            {"user": "", "expected_latency": 1000},  # Empty input
            {"user": "orari", "expected_latency": 500},  # Should recover
        ]
    },
    "6": {
        "name": "Múltiples consultas en una llamada",
        "description": "Conversación larga sin colgar",
        "conversation": [
            {"user": "orari", "expected_latency": 500},
            {"user": "indirizzo", "expected_latency": 500},
            {"user": "telefono", "expected_latency": 500},
            {"user": "email", "expected_latency": 500},
            {"user": "grazie", "expected_latency": 1000},
        ]
    },
    "7": {
        "name": "Respuesta larga (test truncamiento)",
        "description": "Pregunta que genera respuesta muy larga",
        "conversation": [
            {"user": "Spiegami tutto sulla dichiarazione dei redditi, le scadenze, le deduzioni, tutto quello che devo sapere", "expected_latency": 4000},
        ]
    }
}


# ============================================================================
# HELPERS
# ============================================================================

def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_turn(turn_num: int, role: str, message: str, latency: float = None):
    """Print conversation turn"""
    if role == "USER":
        print(f"\n[Turn {turn_num}] 👤 USER: {message}")
    else:
        latency_str = f" ({latency:.0f}ms)" if latency else ""
        print(f"[Turn {turn_num}] 🤖 ASSISTANT{latency_str}: {message[:150]}...")
        if len(message) > 150:
            print(f"           [Total: {len(message)} chars]")


def extract_response_from_twiml(twiml_text: str) -> str:
    """Extract <Say> text from TwiML"""
    from xml.etree import ElementTree as ET
    try:
        root = ET.fromstring(twiml_text)
        
        # Find all <Say> elements within <Gather>
        gather = root.find(".//Gather")
        if gather is not None:
            say = gather.find("Say")
            if say is not None and say.text:
                return say.text
        
        # Fallback: find any <Say>
        say = root.find(".//Say")
        if say is not None and say.text:
            return say.text
        
        return "[No response text found]"
    except Exception as e:
        return f"[Error parsing TwiML: {e}]"


def check_hangup(twiml_text: str) -> bool:
    """Check if TwiML contains <Hangup>"""
    return "<Hangup" in twiml_text


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_scenario(scenario_key: str, call_sid: str = None):
    """Run a single test scenario"""
    
    scenario = SCENARIOS[scenario_key]
    call_sid = call_sid or f"TEST_MANUAL_{scenario_key}_{int(time.time())}"
    
    print_header(f"SCENARIO {scenario_key}: {scenario['name']}")
    print(f"Description: {scenario['description']}")
    print(f"Call SID: {call_sid}")
    
    # Start call
    print("\n📞 Starting call...")
    try:
        response = requests.post(
            f"{BASE_URL}/voice/incoming",
            data={
                "CallSid": call_sid,
                "From": "+391234567890",
                "To": "+390212345678"
            },
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start call: {response.status_code}")
            return False
        
        greeting = extract_response_from_twiml(response.text)
        print(f"\n[Greeting] 🤖 ASSISTANT: {greeting}")
    
    except Exception as e:
        print(f"❌ Error starting call: {e}")
        return False
    
    # Run conversation
    turn_num = 1
    all_passed = True
    
    for turn in scenario["conversation"]:
        user_input = turn["user"]
        expected_latency = turn["expected_latency"]
        
        print_turn(turn_num, "USER", user_input or "[silence]")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/voice/gather",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": user_input,
                    "Confidence": "0.95" if user_input else "0.0"
                },
                timeout=15
            )
            actual_latency = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                print(f"❌ Failed: HTTP {response.status_code}")
                all_passed = False
                continue
            
            # Extract response
            ai_response = extract_response_from_twiml(response.text)
            print_turn(turn_num, "ASSISTANT", ai_response, actual_latency)
            
            # Check latency
            if actual_latency > expected_latency * 1.5:  # 50% tolerance
                print(f"⚠️  WARNING: High latency! Expected ~{expected_latency}ms, got {actual_latency:.0f}ms")
                all_passed = False
            else:
                print(f"✓ Latency OK: {actual_latency:.0f}ms (expected ~{expected_latency}ms)")
            
            # Check if call ended
            if check_hangup(response.text):
                print("\n📞 Call ended (Hangup detected)")
                break
            
        except Exception as e:
            print(f"❌ Error on turn {turn_num}: {e}")
            all_passed = False
        
        turn_num += 1
        time.sleep(0.5)  # Brief pause between turns
    
    # Summary
    print("\n" + "-" * 70)
    if all_passed:
        print("✅ SCENARIO PASSED")
    else:
        print("⚠️  SCENARIO COMPLETED WITH WARNINGS")
    print("-" * 70)
    
    return all_passed


def interactive_mode():
    """Interactive conversation mode"""
    print_header("INTERACTIVE MODE")
    print("Simula una conversación real paso a paso")
    print("Escribe 'quit' para salir, 'scenarios' para ver escenarios predefinidos\n")
    
    call_sid = f"INTERACTIVE_{int(time.time())}"
    
    # Start call
    print("📞 Iniciando llamada...")
    try:
        response = requests.post(
            f"{BASE_URL}/voice/incoming",
            data={
                "CallSid": call_sid,
                "From": "+391234567890",
                "To": "+390212345678"
            },
            timeout=10
        )
        
        greeting = extract_response_from_twiml(response.text)
        print(f"\n🤖 ASSISTANT: {greeting}\n")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    turn_num = 1
    
    while True:
        user_input = input(f"\n👤 USER [Turn {turn_num}]: ").strip()
        
        if user_input.lower() == 'quit':
            print("\n👋 Saliendo...")
            break
        
        if user_input.lower() == 'scenarios':
            print("\nEscenarios disponibles:")
            for key, scenario in SCENARIOS.items():
                print(f"  {key}. {scenario['name']}")
            continue
        
        if not user_input:
            print("⚠️  Input vacío - simulando silencio")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/voice/gather",
                data={
                    "CallSid": call_sid,
                    "SpeechResult": user_input,
                    "Confidence": "0.95" if user_input else "0.0"
                },
                timeout=15
            )
            latency = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                continue
            
            ai_response = extract_response_from_twiml(response.text)
            print(f"\n🤖 ASSISTANT ({latency:.0f}ms): {ai_response}")
            
            if check_hangup(response.text):
                print("\n📞 Llamada finalizada")
                break
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        turn_num += 1


# ============================================================================
# MAIN MENU
# ============================================================================

def main():
    """Main menu"""
    
    # Check server
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.RequestException:
        print(f"❌ ERROR: Server not responding at {BASE_URL}")
        print(f"Make sure server is running: python server.py\n")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("  TWILIO VOICE SERVER - MANUAL TEST SUITE")
    print("=" * 70)
    
    while True:
        print("\n📋 MENU:")
        print("\n  ESCENARIOS PREDEFINIDOS:")
        for key, scenario in SCENARIOS.items():
            print(f"    {key}. {scenario['name']}")
        
        print("\n  OTROS:")
        print("    i. Modo interactivo (conversación libre)")
        print("    a. Ejecutar TODOS los escenarios")
        print("    q. Salir")
        
        choice = input("\n👉 Selecciona una opción: ").strip().lower()
        
        if choice == 'q':
            print("\n👋 Adiós!\n")
            break
        
        elif choice == 'i':
            interactive_mode()
        
        elif choice == 'a':
            print("\n🚀 Ejecutando TODOS los escenarios...\n")
            results = []
            for key in SCENARIOS.keys():
                passed = run_scenario(key)
                results.append((SCENARIOS[key]['name'], passed))
                time.sleep(1)
            
            print_header("RESULTADOS FINALES")
            for name, passed in results:
                status = "✅ PASS" if passed else "⚠️  WARNINGS"
                print(f"  {status}: {name}")
        
        elif choice in SCENARIOS:
            run_scenario(choice)
        
        else:
            print("❌ Opción inválida")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por usuario\n")
        sys.exit(0)
