#!/usr/bin/env python3
"""
Configuration Verification Script
==================================
Brutal diagnostic tool to verify SERVICE_MODE configuration is correct.

This script will:
1. Check if SERVICE_MODE exists in config.py
2. Verify it reads from environment variables
3. Test switching between mock/real modes
4. Identify any configuration bugs

Run: python verify_config.py
"""
import os
import sys
from pathlib import Path

# Color codes for brutal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    """Print section header"""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

def print_error(text):
    """Print error message"""
    print(f"{RED}❌ ERROR: {text}{RESET}")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  WARNING: {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

def check_config_file_exists():
    """Verify config.py exists"""
    print_header("1. CHECKING CONFIG FILE")
    
    config_path = Path("config.py")
    if not config_path.exists():
        print_error("config.py not found in current directory!")
        print_info(f"Current directory: {Path.cwd()}")
        return False
    
    print_success(f"config.py found at: {config_path.absolute()}")
    return True

def analyze_config_file():
    """Analyze config.py for SERVICE_MODE implementation"""
    print_header("2. ANALYZING CONFIG.PY IMPLEMENTATION")
    
    config_path = Path("config.py")
    content = config_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Check if SERVICE_MODE exists
    service_mode_lines = [
        (i+1, line.strip()) 
        for i, line in enumerate(lines) 
        if 'SERVICE_MODE' in line and not line.strip().startswith('#')
    ]
    
    if not service_mode_lines:
        print_error("SERVICE_MODE not found in config.py!")
        return False
    
    print_info(f"Found {len(service_mode_lines)} SERVICE_MODE reference(s):\n")
    
    has_env_read = False
    has_hardcoded = False
    
    for line_num, line in service_mode_lines:
        print(f"  Line {line_num}: {line}")
        
        if 'os.getenv' in line or 'os.environ' in line:
            has_env_read = True
            print_success(f"    → Line {line_num} reads from environment ✓")
        elif '=' in line and '"' in line:
            has_hardcoded = True
            print_error(f"    → Line {line_num} is HARDCODED! ✗")
    
    print()
    
    if has_hardcoded and not has_env_read:
        print_error("SERVICE_MODE is HARDCODED - does NOT read from .env!")
        print_info("Expected pattern: SERVICE_MODE = os.getenv('SERVICE_MODE', 'mock')")
        return False
    elif has_env_read:
        print_success("SERVICE_MODE correctly reads from environment variables")
        return True
    else:
        print_warning("Could not determine SERVICE_MODE implementation pattern")
        return False

def check_env_file():
    """Check .env file configuration"""
    print_header("3. CHECKING .ENV FILE")
    
    env_path = Path(".env")
    if not env_path.exists():
        print_warning(".env file does NOT exist!")
        print_info("Create .env file with: SERVICE_MODE=mock")
        print_info("This is OK if using environment variables directly")
        return False
    
    print_success(".env file exists")
    
    # Read .env content
    env_content = env_path.read_text(encoding='utf-8')
    
    if 'SERVICE_MODE' in env_content:
        # Extract the value
        for line in env_content.split('\n'):
            if line.strip().startswith('SERVICE_MODE'):
                print_success(f"SERVICE_MODE configured in .env: {line.strip()}")
                return True
        
    print_warning("SERVICE_MODE not found in .env file")
    print_info("Add this line to .env: SERVICE_MODE=mock")
    return False

def test_import_config():
    """Test importing config module"""
    print_header("4. TESTING CONFIG MODULE IMPORT")
    
    try:
        # Clear any cached import
        if 'config' in sys.modules:
            del sys.modules['config']
        
        import config
        
        print_success("config module imported successfully")
        
        # Check if SERVICE_MODE attribute exists
        if hasattr(config, 'SERVICE_MODE'):
            current_value = config.SERVICE_MODE
            print_success(f"SERVICE_MODE attribute exists: '{current_value}'")
            
            # Validate value
            if current_value not in ['mock', 'real']:
                print_error(f"Invalid SERVICE_MODE value: '{current_value}'")
                print_info("SERVICE_MODE must be either 'mock' or 'real'")
                return False
            
            return True
        else:
            print_error("SERVICE_MODE attribute does NOT exist in config module!")
            return False
            
    except Exception as e:
        print_error(f"Failed to import config: {e}")
        return False

def test_environment_override():
    """Test if environment variables override works"""
    print_header("5. TESTING ENVIRONMENT VARIABLE OVERRIDE")
    
    try:
        # Test 1: Set to 'real' mode
        print_info("Test 1: Setting SERVICE_MODE=real in environment...")
        os.environ['SERVICE_MODE'] = 'real'
        
        # Reload config
        if 'config' in sys.modules:
            del sys.modules['config']
        
        import config
        
        if config.SERVICE_MODE == 'real':
            print_success("✓ Environment override to 'real' works!")
        else:
            print_error(f"✗ Expected 'real', got '{config.SERVICE_MODE}'")
            return False
        
        # Test 2: Set to 'mock' mode
        print_info("\nTest 2: Setting SERVICE_MODE=mock in environment...")
        os.environ['SERVICE_MODE'] = 'mock'
        
        # Reload config
        if 'config' in sys.modules:
            del sys.modules['config']
        
        import config
        
        if config.SERVICE_MODE == 'mock':
            print_success("✓ Environment override to 'mock' works!")
        else:
            print_error(f"✗ Expected 'mock', got '{config.SERVICE_MODE}'")
            return False
        
        # Clean up
        del os.environ['SERVICE_MODE']
        
        return True
        
    except Exception as e:
        print_error(f"Environment override test failed: {e}")
        return False

def generate_recommendations():
    """Generate actionable recommendations"""
    print_header("6. RECOMMENDATIONS")
    
    print(f"{BOLD}If SERVICE_MODE is HARDCODED:{RESET}")
    print("""
1. Open config.py
2. Find the line with SERVICE_MODE = "mock" (around line 50)
3. Replace with:
   SERVICE_MODE = os.getenv("SERVICE_MODE", "mock")
   
4. Ensure os module is imported at the top:
   import os
""")
    
    print(f"\n{BOLD}If .env file is missing SERVICE_MODE:{RESET}")
    print("""
1. Open .env file (or create it)
2. Add this line:
   SERVICE_MODE=mock
   
3. To switch to real services, change to:
   SERVICE_MODE=real
""")
    
    print(f"\n{BOLD}Testing the configuration:{RESET}")
    print("""
# In Python/terminal:
import os
os.environ['SERVICE_MODE'] = 'real'
import config
print(config.SERVICE_MODE)  # Should print: real

# Or in .env:
SERVICE_MODE=real

# Then restart your application
""")

def main():
    """Run all verification checks"""
    print(f"{BOLD}{GREEN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     SERVICE_MODE CONFIGURATION VERIFICATION SCRIPT                 ║")
    print("║     Brutal diagnostic tool for configuration issues                ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}\n")
    
    results = []
    
    # Run checks
    results.append(("Config file exists", check_config_file_exists()))
    results.append(("Config implementation", analyze_config_file()))
    results.append((".env file check", check_env_file()))
    results.append(("Config import test", test_import_config()))
    results.append(("Environment override", test_environment_override()))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"  {check_name:.<50} {status}")
    
    print(f"\n{BOLD}Results: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{BOLD}🎉 ALL CHECKS PASSED - Configuration is correct!{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}⚠️  CONFIGURATION ISSUES DETECTED{RESET}")
        generate_recommendations()
        return 1

if __name__ == "__main__":
    sys.exit(main())