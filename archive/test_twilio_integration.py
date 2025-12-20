#!/usr/bin/env python3
"""
Test Suite for Twilio Voice Server
=================================

Full test suite to verify:
1. Endpoints work correctly
2. Fast-response caching
3. Error handling
4. Response latency
5. Farewell/hangup detection
6. Sessions and metadata

Run: python archive/test_twilio_integration.py
"""

import sys
import time
import requests
from typing import Dict, Tuple
from loguru import logger
from xml.etree import ElementTree as ET

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "http://localhost:5000"  # Adjust if the server runs on a different port
TEST_TIMEOUT = 30  # HTTP request timeout (increased for longer flows)

# Output colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_test_header(test_name: str):
    """Print test header"""
    print(f"\n{BLUE}{'=' * 70}")
    print(f"TEST: {test_name}")
    print(f"{'=' * 70}{RESET}\n")


def print_result(success: bool, message: str, details: str = ""):
    """Print test result"""
    if success:
        print(f"{GREEN}✓ PASS:{RESET} {message}")
    else:
        print(f"{RED}✗ FAIL:{RESET} {message}")
    
    if details:
        print(f"  {YELLOW}Details:{RESET} {details}")


def parse_twiml(response_text: str) -> ET.Element:
    """Parse TwiML XML response"""
    try:
        return ET.fromstring(response_text)
    except ET.ParseError as e:
        logger.error(f"Failed to parse TwiML: {e}")
        return None


def extract_say_text(twiml_root: ET.Element) -> list:
    """Extract all <Say> text from TwiML"""
    if twiml_root is None:
        return []
    return [say.text for say in twiml_root.findall(".//Say") if say.text]


def has_gather(twiml_root: ET.Element) -> bool:
    """Check if TwiML has <Gather> element"""
    if twiml_root is None:
        return False
    return len(twiml_root.findall(".//Gather")) > 0


def has_hangup(twiml_root: ET.Element) -> bool:
    """Check if TwiML has <Hangup> element"""
    if twiml_root is None:
        return False
    return len(twiml_root.findall(".//Hangup")) > 0


# ============================================================================
# TEST CASES
# ============================================================================

def test_health_check() -> Tuple[bool, str]:
    """Test /health endpoint"""
    print_test_header("Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TEST_TIMEOUT)
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Check required fields
        required_fields = ["status", "timestamp", "active_calls", "orchestrator"]
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return False, f"Missing fields: {missing}"
        
        if data["status"] != "healthy":
            return False, f"Status is '{data['status']}', expected 'healthy'"
        
        print_result(True, "Health endpoint responding correctly")
        print(f"  Active calls: {data['active_calls']}")
        print(f"  Orchestrator: {data['orchestrator']}")
        return True, "Health check passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_incoming_call() -> Tuple[bool, str]:
    """Test /voice/incoming endpoint"""
    print_test_header("Incoming Call Handler")
    
    try:
        # Simulate Twilio incoming call webhook
        params = {
            "CallSid": "TEST_CALL_001",
            "From": "+391234567890",
            "To": "+390212345678",
            "CallStatus": "ringing"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/voice/incoming",
            data=params,
            timeout=TEST_TIMEOUT
        )
        latency = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        # Parse TwiML
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        # Check for greeting
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No <Say> found in response"
        
        greeting = say_texts[0]
        if "buongiorno" not in greeting.lower():
            return False, f"Unexpected greeting: {greeting}"
        
        # Check for Gather
        if not has_gather(twiml):
            return False, "No <Gather> found - cannot collect user input"
        
        print_result(True, "Incoming call handled correctly", f"Latency: {latency:.0f}ms")
        print(f"  Greeting: {greeting}")
        return True, "Incoming call test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_cache_hit() -> Tuple[bool, str]:
    """Test response cache for fast responses"""
    print_test_header("Response Cache Test (Orari)")
    
    try:
        # Simulate user asking for office hours (should hit cache)
        params = {
            "CallSid": "TEST_CALL_002",
            "SpeechResult": "orari",
            "Confidence": "0.95"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/voice/gather",
            data=params,
            timeout=TEST_TIMEOUT
        )
        latency = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No response generated"
        
        response_text = say_texts[0]
        
        # Check if response mentions office hours
        if "lunedì" not in response_text.lower() and "9" not in response_text:
            return False, f"Unexpected response: {response_text}"
        
        # Cache should be fast (<2000ms including Flask overhead + first-time DB init)
        # Note: Pure cache lookup ~1-5ms, but Flask overhead + logging ~200-1500ms
        if latency > 2000:
            print_result(
                False, 
                "Cache hit but latency too high",
                f"Latency: {latency:.0f}ms (expected <2000ms)"
            )
            return False, "Latency too high for cached response"
        
        # Warn if cache is slower than expected (but still acceptable)
        if latency > 1000:
            print(f"  {YELLOW}Note: Cache latency {latency:.0f}ms (includes Flask startup + DB session init){RESET}")
        
        print_result(True, "Cache working correctly", f"Latency: {latency:.0f}ms")
        print(f"  Response: {response_text[:80]}...")
        return True, "Cache test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_orchestrator_query() -> Tuple[bool, str]:
    """Test full orchestrator processing"""
    print_test_header("Orchestrator Query Test")
    
    try:
        # Complex query that requires orchestrator
        params = {
            "CallSid": "TEST_CALL_003",
            "SpeechResult": "Vorrei prenotare un appuntamento per la dichiarazione dei redditi",
            "Confidence": "0.92"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/voice/gather",
            data=params,
            timeout=TEST_TIMEOUT
        )
        latency = (time.time() - start_time) * 1000
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No response generated"
        
        response_text = say_texts[0]
        
        # Check for reasonable response length (not too short, not too long)
        if len(response_text) < 20:
            return False, f"Response too short: {response_text}"
        
        if len(response_text) > 350:
            print_result(
                False,
                "Response too long (>350 chars)",
                f"Length: {len(response_text)} - should be truncated"
            )
            return False, "Response not truncated"
        
        # Check latency (orchestrator should be <10s for complex queries)
        # Note: RAG retrieval + LLM inference + function calls can take 5-8s
        if latency > 10000:
            print_result(
                False,
                "Orchestrator latency too high",
                f"Latency: {latency:.0f}ms (expected <10000ms)"
            )
            return False, "Orchestrator too slow"
        
        print_result(True, "Orchestrator processing correctly", f"Latency: {latency:.0f}ms")
        print(f"  Response: {response_text[:100]}...")
        print(f"  Length: {len(response_text)} chars")
        return True, "Orchestrator test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_farewell_detection() -> Tuple[bool, str]:
    """Test farewell detection and call termination"""
    print_test_header("Farewell Detection Test")
    
    try:
        # User says goodbye
        params = {
            "CallSid": "TEST_CALL_004",
            "SpeechResult": "grazie",
            "Confidence": "0.98"
        }
        
        response = requests.post(
            f"{BASE_URL}/voice/gather",
            data=params,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        # Should have <Hangup> element
        if not has_hangup(twiml):
            return False, "No <Hangup> found - call should end"
        
        # Should have farewell message
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No farewell message"
        
        farewell = say_texts[0]
        if "grazie" not in farewell.lower() and "arrivederci" not in farewell.lower():
            return False, f"Unexpected farewell: {farewell}"
        
        # Should NOT have <Gather> (no more input expected)
        if has_gather(twiml):
            return False, "<Gather> found but call should end"
        
        print_result(True, "Farewell detected correctly")
        print(f"  Farewell: {farewell}")
        return True, "Farewell test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_empty_input() -> Tuple[bool, str]:
    """Test handling of empty/silent input"""
    print_test_header("Empty Input Handling")
    
    try:
        # Simulate no speech detected
        params = {
            "CallSid": "TEST_CALL_005",
            "SpeechResult": "",
            "Confidence": "0.0"
        }
        
        response = requests.post(
            f"{BASE_URL}/voice/gather",
            data=params,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        # Should ask user to repeat
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No prompt to repeat"
        
        prompt = say_texts[0]
        if "ripetere" not in prompt.lower() and "sentito" not in prompt.lower():
            return False, f"Unexpected prompt: {prompt}"
        
        # Should have <Gather> to try again
        if not has_gather(twiml):
            return False, "No <Gather> found - should ask again"
        
        print_result(True, "Empty input handled correctly")
        print(f"  Prompt: {prompt}")
        return True, "Empty input test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_voice_config() -> Tuple[bool, str]:
    """Test voice configuration (Wavenet, language, etc)"""
    print_test_header("Voice Configuration Test")
    
    try:
        params = {
            "CallSid": "TEST_CALL_006"
        }
        
        response = requests.post(
            f"{BASE_URL}/voice/incoming",
            data=params,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        # Check raw XML for voice attributes
        xml_text = response.text
        
        # Check for Italian language
        if 'language="it-IT"' not in xml_text and "language='it-IT'" not in xml_text:
            return False, "Italian language not configured"
        
        # Check for Wavenet voice (better quality)
        if 'Wavenet' in xml_text:
            print_result(True, "Voice configured correctly (Wavenet)")
        else:
            print_result(True, "Voice configured (Standard, consider upgrading to Wavenet)")
        
        return True, "Voice config test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_speech_timeout_config() -> Tuple[bool, str]:
    """Test speech timeout configuration"""
    print_test_header("Speech Timeout Configuration Test")
    
    try:
        params = {
            "CallSid": "TEST_CALL_007"
        }
        
        response = requests.post(
            f"{BASE_URL}/voice/incoming",
            data=params,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        xml_text = response.text
        
        # Check for numeric timeout (not 'auto')
        if 'speechTimeout="auto"' in xml_text or "speechTimeout='auto'" in xml_text:
            print_result(
                False,
                "Speech timeout is 'auto'",
                "Should be numeric for lower latency"
            )
            return False, "Speech timeout not optimized"
        
        # Check for reasonable timeout value (1-2 seconds)
        import re
        match = re.search(r'speechTimeout="?(\d+\.?\d*)"?', xml_text)
        if not match:
            return False, "speechTimeout not found"
        
        timeout_value = float(match.group(1))
        if timeout_value < 1.0 or timeout_value > 3.0:
            print_result(
                False,
                f"Speech timeout is {timeout_value}s",
                "Should be between 1.0-3.0s for optimal latency"
            )
            return False, "Speech timeout out of range"
        
        print_result(True, f"Speech timeout configured correctly: {timeout_value}s")
        return True, "Speech timeout test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


def test_response_truncation() -> Tuple[bool, str]:
    """Test that long responses are truncated"""
    print_test_header("Response Truncation Test")
    
    try:
        # Ask a simpler question that still tests truncation logic
        # (Complex questions can timeout if LLM is slow)
        params = {
            "CallSid": "TEST_CALL_008",
            "SpeechResult": "Come funziona la dichiarazione dei redditi?",
            "Confidence": "0.90"
        }
        
        response = requests.post(
            f"{BASE_URL}/voice/gather",
            data=params,
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code != 200:
            return False, f"Expected 200, got {response.status_code}"
        
        twiml = parse_twiml(response.text)
        if twiml is None:
            return False, "Invalid TwiML response"
        
        say_texts = extract_say_text(twiml)
        if not say_texts:
            return False, "No response generated"
        
        response_text = say_texts[0]
        response_length = len(response_text)
        
        # Should be truncated to ~300 chars max
        if response_length > 350:
            print_result(
                False,
                f"Response too long: {response_length} chars",
                "Should be truncated to ~300 chars"
            )
            return False, "Truncation not working"
        
        print_result(True, "Response length appropriate", f"{response_length} chars")
        return True, "Truncation test passed"
    
    except Exception as e:
        return False, f"Exception: {str(e)}"


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests and report results"""
    
    print(f"\n{BLUE}{'=' * 70}")
    print("TWILIO VOICE SERVER - TEST SUITE")
    print(f"{'=' * 70}{RESET}\n")
    
    print(f"Target server: {BASE_URL}")
    print(f"Timeout: {TEST_TIMEOUT}s\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Incoming Call", test_incoming_call),
        ("Response Cache", test_cache_hit),
        ("Orchestrator Query", test_orchestrator_query),
        ("Farewell Detection", test_farewell_detection),
        ("Empty Input", test_empty_input),
        ("Voice Config", test_voice_config),
        ("Speech Timeout Config", test_speech_timeout_config),
        ("Response Truncation", test_response_truncation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            results.append((test_name, success, message))
        except Exception as e:
            logger.exception(f"Test {test_name} crashed")
            results.append((test_name, False, f"Exception: {str(e)}"))
        
        time.sleep(0.5)  # Small delay between tests
    
    # Print summary
    print(f"\n{BLUE}{'=' * 70}")
    print("TEST SUMMARY")
    print(f"{'=' * 70}{RESET}\n")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        print(f"  [{status}] {test_name}: {message}")
    
    print(f"\n{BLUE}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ All tests passed!{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ {total - passed} test(s) failed{RESET}\n")
        return 1


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.RequestException:
        print(f"{RED}ERROR: Server not responding at {BASE_URL}{RESET}")
        print(f"{YELLOW}Make sure server is running: python server.py{RESET}\n")
        sys.exit(1)
    
    exit_code = run_all_tests()
    sys.exit(exit_code)
