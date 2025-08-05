#!/usr/bin/env python3
"""Quick Test - Basic functionality test"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_imports():
    """Test basic imports"""
    try:
        print("Testing imports...")
        
        # Basic imports
        from src.core.config_manager import ConfigManager
        from src.core.database_manager import DatabaseManager
        print("✅ Core imports OK")
        
        from src.trading.exchange_manager import ExchangeManager  
        print("✅ Trading imports OK")
        
        from src.ai.signal_filter import AISignalFilter
        print("✅ AI imports OK")
        
        from src.utils.notifications import NotificationManager
        print("✅ Utils imports OK")
        
        print("🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test config loading"""
    try:
        print("\nTesting config...")
        
        # Check if config file exists
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("⚠️ config.yaml not found")
            return False
            
        print("✅ config.yaml found")
        print("🎉 Config test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔧 Quick Test - Advanced Trading Bot")
    print("="*50)
    
    tests = [
        ("Import Test", test_imports),
        ("Config Test", test_config)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Basic tests passed! Try running: python startup.py")
    else:
        print("💥 Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)