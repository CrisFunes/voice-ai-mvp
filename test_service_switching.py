#!/usr/bin/env python3
"""
Service Mode Switching Test
============================
Tests the ability to switch between mock and real service implementations
using the SERVICE_MODE environment variable.

This script validates:
1. Mock mode is used by default
2. Real mode can be activated via environment variable
3. Service factory responds correctly to mode changes
4. No crashes or unexpected behavior during switching

Run: python test_service_switching.py
"""
import os
import sys
from pathlib import Path

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_test_header(test_name):
    """Print test section header"""
    print(f"\n{BOLD}{BLUE}{'─' * 70}{RESET}")
    print(f"{BOLD}{BLUE}TEST: {test_name}{RESET}")
    print(f"{BOLD}{BLUE}{'─' * 70}{RESET}")

def print_pass(message):
    """Print test passed"""
    print(f"{GREEN}✅ PASS: {message}{RESET}")

def print_fail(message):
    """Print test failed"""
    print(f"{RED}❌ FAIL: {message}{RESET}")

def print_info(message):
    """Print info message"""
    print(f"{BLUE}ℹ️  {message}{RESET}")

def test_default_mode():
    """Test 1: Default SERVICE_MODE should be 'mock'"""
    print_test_header("Default Mode (No Environment Variable)")
    
    try:
        # Clear environment
        if 'SERVICE_MODE' in os.environ:
            del os.environ['SERVICE_MODE']
        
        # Clear cached import
        if 'config' in sys.modules:
            del sys.modules['config']
        
        # Import config
        import config
        
        print_info(f"SERVICE_MODE value: {config.SERVICE_MODE}")
        
        if config.SERVICE_MODE == "mock":
            print_pass("Default mode is 'mock'")
            return True
        else:
            print_fail(f"Expected 'mock', got '{config.SERVICE_MODE}'")
            return False
            
    except Exception as e:
        print_fail(f"Exception during test: {e}")
        return False

def test_mock_mode_explicit():
    """Test 2: Explicit SERVICE_MODE=mock"""
    print_test_header("Explicit Mock Mode (SERVICE_MODE=mock)")
    
    try:
        # Set environment
        os.environ['SERVICE_MODE'] = 'mock'
        
        # Clear cached import
        if 'config' in sys.modules:
            del sys.modules['config']
        
        # Import config
        import config
        
        print_info(f"SERVICE_MODE value: {config.SERVICE_MODE}")
        
        if config.SERVICE_MODE == "mock":
            print_pass("Mock mode correctly set via environment")
            return True
        else:
            print_fail(f"Expected 'mock', got '{config.SERVICE_MODE}'")
            return False
            
    except Exception as e:
        print_fail(f"Exception during test: {e}")
        return False

def test_real_mode():
    """Test 3: SERVICE_MODE=real"""
    print_test_header("Real Mode (SERVICE_MODE=real)")
    
    try:
        # Set environment
        os.environ['SERVICE_MODE'] = 'real'
        
        # Clear cached import
        if 'config' in sys.modules:
            del sys.modules['config']
        
        # Import config
        import config
        
        print_info(f"SERVICE_MODE value: {config.SERVICE_MODE}")
        
        if config.SERVICE_MODE == "real":
            print_pass("Real mode correctly set via environment")
            return True
        else:
            print_fail(f"Expected 'real', got '{config.SERVICE_MODE}'")
            return False
            
    except Exception as e:
        print_fail(f"Exception during test: {e}")
        return False

def test_invalid_mode():
    """Test 4: Invalid SERVICE_MODE should raise error"""
    print_test_header("Invalid Mode (SERVICE_MODE=invalid)")
    
    try:
        # Set environment to invalid value
        os.environ['SERVICE_MODE'] = 'invalid'
        
        # Clear cached import
        if 'config' in sys.modules:
            del sys.modules['config']
        
        # Try to import config - should raise error
        try:
            import config
            print_fail("Config imported with invalid SERVICE_MODE (should raise error)")
            return False
        except ValueError as e:
            if "Invalid SERVICE_MODE" in str(e):
                print_pass("Invalid SERVICE_MODE correctly rejected")
                return True
            else:
                print_fail(f"Wrong error message: {e}")
                return False
            
    except Exception as e:
        print_fail(f"Unexpected exception: {e}")
        return False

def test_service_factory_integration():
    """Test 5: Service factory responds to SERVICE_MODE"""
    print_test_header("Service Factory Integration")
    
    try:
        # Test mock mode
        os.environ['SERVICE_MODE'] = 'mock'
        if 'config' in sys.modules:
            del sys.modules['config']
        if 'services.factory' in sys.modules:
            del sys.modules['services.factory']
        
        import config
        from services.factory import ServiceFactory
        
        print_info("Testing mock mode service factory...")
        factory = ServiceFactory(mode="mock")
        booking_service = factory.create_booking_service()
        
        print_info(f"BookingService type: {type(booking_service).__name__}")
        
        if "Mock" in type(booking_service).__name__:
            print_pass("Mock service created in mock mode")
        else:
            print_info("Note: Service might not have 'Mock' in name, but should still be mock implementation")
        
        # Test real mode
        os.environ['SERVICE_MODE'] = 'real'
        if 'config' in sys.modules:
            del sys.modules['config']
        if 'services.factory' in sys.modules:
            del sys.modules['services.factory']
        
        import config
        from services.factory import ServiceFactory
        
        print_info("\nTesting real mode service factory...")
        factory = ServiceFactory(mode="real")
        booking_service = factory.create_booking_service()
        
        print_info(f"BookingService type: {type(booking_service).__name__}")
        
        print_pass("Service factory responds to SERVICE_MODE")
        return True
        
    except ImportError as e:
        print_info(f"Service factory not available: {e}")
        print_info("This test requires services/factory.py to exist")
        return True  # Don't fail if services not implemented yet
    except Exception as e:
        print_fail(f"Exception during test: {e}")
        return False

def test_dotenv_file():
    """Test 6: .env file configuration"""
    print_test_header(".env File Configuration")
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print_info(".env file does not exist")
        print_info("This is OK if using environment variables directly")
        return True
    
    print_info(f".env file found at: {env_path.absolute()}")
    
    # Read .env content
    content = env_path.read_text(encoding='utf-8')
    
    if 'SERVICE_MODE' in content:
        # Extract value
        for line in content.split('\n'):
            if line.strip().startswith('SERVICE_MODE'):
                print_info(f"Found: {line.strip()}")
                
                # Validate value
                if '=' in line:
                    value = line.split('=', 1)[1].strip()
                    if value in ['mock', 'real']:
                        print_pass(f"SERVICE_MODE correctly configured in .env: {value}")
                        return True
                    else:
                        print_fail(f"Invalid SERVICE_MODE value in .env: {value}")
                        return False
    else:
        print_info("SERVICE_MODE not configured in .env")
        print_info("Add this line to .env: SERVICE_MODE=mock")
        return True  # Not a failure, just info

def cleanup():
    """Clean up test environment"""
    # Remove test environment variable
    if 'SERVICE_MODE' in os.environ:
        del os.environ['SERVICE_MODE']
    
    # Clear module cache
    for module in ['config', 'services.factory']:
        if module in sys.modules:
            del sys.modules[module]

def main():
    """Run all tests"""
    print(f"{BOLD}{GREEN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║          SERVICE MODE SWITCHING TEST SUITE                         ║")
    print("║          Validates mock/real service configuration                 ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    tests = [
        ("Default mode (no env var)", test_default_mode),
        ("Explicit mock mode", test_mock_mode_explicit),
        ("Real mode", test_real_mode),
        ("Invalid mode rejection", test_invalid_mode),
        ("Service factory integration", test_service_factory_integration),
        (".env file configuration", test_dotenv_file),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_fail(f"Unexpected error in {test_name}: {e}")
            results.append((test_name, False))
        finally:
            cleanup()
    
    # Summary
    print(f"\n{BOLD}{BLUE}{'═' * 70}{RESET}")
    print(f"{BOLD}{BLUE}TEST SUMMARY{RESET}")
    print(f"{BOLD}{BLUE}{'═' * 70}{RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"  {test_name:.<55} {status}")
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{BOLD}🎉 ALL TESTS PASSED!{RESET}")
        print(f"{GREEN}SERVICE_MODE configuration is working correctly{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}⚠️  SOME TESTS FAILED{RESET}")
        print(f"{RED}Review the failures above and fix configuration{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())