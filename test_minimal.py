#!/usr/bin/env python3
"""Minimal Test - No external dependencies"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_basic_structure():
    """Test basic file structure"""
    print("Testing basic file structure...")
    
    required_files = [
        'config.yaml',
        'main.py',
        'requirements.txt',
        'src/core/__init__.py',
        'src/core/config_manager.py',
        'src/core/database_manager.py',
        'src/core/risk_manager.py',
        'src/trading/__init__.py',
        'src/trading/exchange_manager.py',
        'src/trading/strategy_engine.py',
        'src/trading/position_manager.py',
        'src/ai/__init__.py',
        'src/ai/signal_filter.py',
        'src/ai/market_analyzer.py',
        'src/ai/confidence_calculator.py',
        'src/utils/__init__.py',
        'src/utils/logger_setup.py',
        'src/utils/notifications.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_python_syntax():
    """Test Python syntax of files"""
    print("\nTesting Python syntax...")
    
    python_files = [
        'main.py',
        'src/core/config_manager.py',
        'src/core/database_manager.py', 
        'src/core/risk_manager.py',
        'src/trading/exchange_manager.py',
        'src/trading/strategy_engine.py',
        'src/trading/position_manager.py',
        'src/ai/signal_filter.py',
        'src/ai/market_analyzer.py',
        'src/ai/confidence_calculator.py',
        'src/utils/logger_setup.py',
        'src/utils/notifications.py'
    ]
    
    syntax_errors = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Compile to check syntax
            compile(code, file_path, 'exec')
            print(f"✅ {file_path} - Syntax OK")
            
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
            print(f"❌ {file_path} - Syntax Error: {e}")
        except Exception as e:
            syntax_errors.append(f"{file_path}: {e}")
            print(f"⚠️ {file_path} - Error: {e}")
    
    if syntax_errors:
        print(f"\n❌ Syntax errors found: {len(syntax_errors)}")
        return False
    else:
        print("\n✅ All Python files have valid syntax")
        return True

def test_config_file():
    """Test config file validity"""
    print("\nTesting config file...")
    
    try:
        # Try to parse YAML without yaml module (basic validation)
        with open('config.yaml', 'r') as f:
            content = f.read()
        
        # Basic YAML checks
        if content.strip() and not content.startswith('---'):
            if 'exchanges:' in content and 'strategies:' in content:
                print("✅ config.yaml appears valid")
                return True
            else:
                print("❌ config.yaml missing required sections")
                return False
        else:
            print("❌ config.yaml appears empty or invalid")
            return False
            
    except Exception as e:
        print(f"❌ config.yaml error: {e}")
        return False

def test_import_structure():
    """Test import structure without executing"""
    print("\nTesting import structure...")
    
    try:
        # Check __init__.py files have proper structure
        init_files = [
            'src/__init__.py',
            'src/core/__init__.py', 
            'src/trading/__init__.py',
            'src/ai/__init__.py',
            'src/utils/__init__.py'
        ]
        
        for init_file in init_files:
            if Path(init_file).exists():
                with open(init_file, 'r') as f:
                    content = f.read()
                if '__all__' in content or 'import' in content:
                    print(f"✅ {init_file} - Import structure OK")
                else:
                    print(f"⚠️ {init_file} - May be empty")
            else:
                print(f"❌ {init_file} - Missing")
                return False
        
        print("✅ Import structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Import structure error: {e}")
        return False

def main():
    """Main test function"""
    print("🔧 Minimal Test - Advanced Trading Bot")
    print("="*50)
    
    tests = [
        ("File Structure", test_basic_structure),
        ("Python Syntax", test_python_syntax),
        ("Config File", test_config_file),
        ("Import Structure", test_import_structure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
    
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Basic structure tests passed!")
        print("\nNext step: Install dependencies and run full tests")
        print("Run: pip install -r requirements.txt")
        print("Then: python startup.py")
    else:
        print("💥 Some basic tests failed. Fix these first.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)