#!/usr/bin/env python3
"""
Final System Check - Dependency Free
Bot'un gerçek durumunu kontrol eder
"""

import ast
import sys
from pathlib import Path
from datetime import datetime


def check_file_syntax(file_path):
    """Check Python file syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        ast.parse(content)
        return True, "Syntax OK"
    except IndentationError as e:
        return False, f"IndentationError: {e}"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_class_methods(file_path, class_name, required_methods):
    """Check if class has required methods"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find the class
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_node = node
                break
        
        if not class_node:
            return False, f"Class {class_name} not found"
        
        # Get methods in the class
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                methods.append(node.name)
        
        missing_methods = [m for m in required_methods if m not in methods]
        
        if missing_methods:
            return False, f"Missing methods: {missing_methods}"
        
        return True, f"Found {len(methods)} methods, all required present"
        
    except Exception as e:
        return False, f"Check error: {e}"


def check_function_implementations(file_path, functions):
    """Check if functions are implemented (not just pass)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        implemented = []
        not_implemented = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in functions:
                    # Check if function body is just 'pass' or empty
                    body_statements = [stmt for stmt in node.body if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Constant)]
                    
                    if len(body_statements) == 1 and isinstance(body_statements[0], ast.Pass):
                        not_implemented.append(node.name)
                    elif len(body_statements) > 1 or (len(body_statements) == 1 and not isinstance(body_statements[0], ast.Pass)):
                        implemented.append(node.name)
        
        return {
            'implemented': implemented,
            'not_implemented': not_implemented,
            'missing': [f for f in functions if f not in implemented + not_implemented]
        }
        
    except Exception as e:
        return {'error': str(e)}


def analyze_live_data_engine():
    """Analyze LiveDataEngine capabilities"""
    file_path = "src/core/live_data_engine.py"
    
    if not Path(file_path).exists():
        return False, "LiveDataEngine file missing"
    
    # Check syntax
    syntax_ok, syntax_msg = check_file_syntax(file_path)
    if not syntax_ok:
        return False, f"Syntax error: {syntax_msg}"
    
    # Check required methods
    required_methods = [
        'start_live_analysis',
        '_live_data_collector',
        '_analysis_engine', 
        '_decision_engine',
        '_make_trading_decision',
        'get_live_status'
    ]
    
    methods_ok, methods_msg = check_class_methods(file_path, 'LiveDataEngine', required_methods)
    if not methods_ok:
        return False, f"Methods error: {methods_msg}"
    
    # Check implementations
    impl_check = check_function_implementations(file_path, required_methods)
    if 'error' in impl_check:
        return False, f"Implementation check error: {impl_check['error']}"
    
    implemented_count = len(impl_check['implemented'])
    total_count = len(required_methods)
    
    if implemented_count < total_count:
        return False, f"Only {implemented_count}/{total_count} methods implemented"
    
    return True, f"All {implemented_count} methods implemented"


def analyze_integration_readiness():
    """Analyze if modules can work together"""
    
    critical_files = {
        'main.py': {'classes': [], 'functions': ['main']},
        'src/core/config_manager.py': {'classes': ['ConfigManager'], 'functions': []},
        'src/core/database_manager.py': {'classes': ['DatabaseManager'], 'functions': []},
        'src/core/risk_manager.py': {'classes': ['RiskManager'], 'functions': []},
        'src/trading/exchange_manager.py': {'classes': ['ExchangeManager'], 'functions': []},
        'src/trading/strategy_engine.py': {'classes': ['StrategyEngine'], 'functions': []},
        'src/trading/position_manager.py': {'classes': ['PositionManager'], 'functions': []},
        'src/ai/signal_filter.py': {'classes': ['AISignalFilter'], 'functions': []},
        'src/ai/market_analyzer.py': {'classes': ['MarketAnalyzer'], 'functions': []},
        'src/core/live_data_engine.py': {'classes': ['LiveDataEngine'], 'functions': []}
    }
    
    results = {}
    total_files = len(critical_files)
    working_files = 0
    
    for file_path, requirements in critical_files.items():
        if not Path(file_path).exists():
            results[file_path] = {'status': 'MISSING', 'details': 'File not found'}
            continue
        
        # Check syntax
        syntax_ok, syntax_msg = check_file_syntax(file_path)
        if not syntax_ok:
            results[file_path] = {'status': 'SYNTAX_ERROR', 'details': syntax_msg}
            continue
        
        # Check classes and functions exist
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            found_classes = []
            found_functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    found_classes.append(node.name)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(node, ast.Module):
                    found_functions.append(node.name)
            
            missing_classes = [cls for cls in requirements['classes'] if cls not in found_classes]
            missing_functions = [func for func in requirements['functions'] if func not in found_functions]
            
            if missing_classes or missing_functions:
                results[file_path] = {
                    'status': 'INCOMPLETE',
                    'details': f"Missing: classes={missing_classes}, functions={missing_functions}"
                }
            else:
                results[file_path] = {'status': 'OK', 'details': 'All required components found'}
                working_files += 1
                
        except Exception as e:
            results[file_path] = {'status': 'ANALYSIS_ERROR', 'details': str(e)}
    
    return results, working_files, total_files


def check_feature_promises():
    """Check if promised features are implemented"""
    
    features = {
        'Live Data Analysis': {
            'file': 'src/core/live_data_engine.py',
            'methods': ['start_live_analysis', '_live_data_collector', '_analysis_engine']
        },
        'AI Signal Filtering': {
            'file': 'src/ai/signal_filter.py', 
            'methods': ['analyze_signals', '_get_ml_signals']
        },
        'Risk Management': {
            'file': 'src/core/risk_manager.py',
            'methods': ['calculate_position_size', '_calculate_price_correlation']
        },
        'Multi-Exchange Support': {
            'file': 'src/trading/exchange_manager.py',
            'methods': ['get_multi_exchange_prices', 'start_websocket_streams']
        },
        'Strategy Backtesting': {
            'file': 'src/trading/strategy_engine.py',
            'methods': ['backtest_strategy', 'optimize_strategy_parameters']
        },
        'Trailing Stops': {
            'file': 'src/trading/position_manager.py',
            'methods': ['update_trailing_stops', 'enable_trailing_stop']
        }
    }
    
    feature_status = {}
    implemented_features = 0
    
    for feature_name, feature_info in features.items():
        file_path = feature_info['file']
        required_methods = feature_info['methods']
        
        if not Path(file_path).exists():
            feature_status[feature_name] = 'FILE_MISSING'
            continue
        
        syntax_ok, _ = check_file_syntax(file_path)
        if not syntax_ok:
            feature_status[feature_name] = 'SYNTAX_ERROR'
            continue
        
        # Check if methods exist and are implemented
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple check - if method name exists in file
            methods_found = 0
            for method in required_methods:
                if f'def {method}(' in content or f'async def {method}(' in content:
                    methods_found += 1
            
            if methods_found == len(required_methods):
                feature_status[feature_name] = 'IMPLEMENTED'
                implemented_features += 1
            elif methods_found > 0:
                feature_status[feature_name] = 'PARTIAL'
            else:
                feature_status[feature_name] = 'MISSING'
                
        except Exception as e:
            feature_status[feature_name] = f'ERROR: {e}'
    
    return feature_status, implemented_features, len(features)


def main():
    """Main system check"""
    print("🔍 ADVANCED TRADING BOT - FINAL SYSTEM CHECK")
    print("=" * 60)
    
    # 1. Syntax Check
    print("\n🧪 1. SYNTAX CHECK")
    print("-" * 30)
    
    critical_files = [
        'main.py',
        'src/core/config_manager.py',
        'src/core/live_data_engine.py',
        'src/trading/exchange_manager.py',
        'src/ai/signal_filter.py'
    ]
    
    syntax_errors = 0
    for file_path in critical_files:
        if Path(file_path).exists():
            syntax_ok, msg = check_file_syntax(file_path)
            status = "✅" if syntax_ok else "❌"
            print(f"{status} {file_path}: {msg}")
            if not syntax_ok:
                syntax_errors += 1
        else:
            print(f"❌ {file_path}: File missing")
            syntax_errors += 1
    
    # 2. Live Data Engine Analysis
    print("\n🔥 2. LIVE DATA ENGINE CHECK")
    print("-" * 30)
    
    live_ok, live_msg = analyze_live_data_engine()
    status = "✅" if live_ok else "❌"
    print(f"{status} Live Data Engine: {live_msg}")
    
    # 3. Integration Readiness
    print("\n🔗 3. INTEGRATION READINESS")
    print("-" * 30)
    
    integration_results, working_files, total_files = analyze_integration_readiness()
    
    for file_path, result in integration_results.items():
        status = "✅" if result['status'] == 'OK' else "❌"
        print(f"{status} {file_path}: {result['status']} - {result['details']}")
    
    # 4. Feature Implementation Check
    print("\n🎯 4. PROMISED FEATURES CHECK")
    print("-" * 30)
    
    feature_status, implemented_count, total_features = check_feature_promises()
    
    for feature, status in feature_status.items():
        if status == 'IMPLEMENTED':
            print(f"✅ {feature}: Implemented")
        elif status == 'PARTIAL':
            print(f"🟡 {feature}: Partially implemented")
        else:
            print(f"❌ {feature}: {status}")
    
    # 5. Final Assessment
    print("\n📊 5. FINAL ASSESSMENT")
    print("-" * 30)
    
    syntax_score = (len(critical_files) - syntax_errors) / len(critical_files) * 100
    integration_score = working_files / total_files * 100
    feature_score = implemented_count / total_features * 100
    live_engine_score = 100 if live_ok else 0
    
    overall_score = (syntax_score + integration_score + feature_score + live_engine_score) / 4
    
    print(f"📝 Syntax Quality: {syntax_score:.0f}%")
    print(f"🔗 Integration Ready: {integration_score:.0f}%")
    print(f"🎯 Features Implemented: {feature_score:.0f}%") 
    print(f"🔥 Live Engine Ready: {live_engine_score:.0f}%")
    print(f"📊 Overall System Score: {overall_score:.0f}%")
    
    # Final verdict
    print("\n🏆 FINAL VERDICT")
    print("-" * 30)
    
    if overall_score >= 90:
        print("🎉 EXCELLENT - Bot is production ready!")
    elif overall_score >= 75:
        print("🟢 GOOD - Bot is mostly ready, minor fixes needed")
    elif overall_score >= 50:
        print("🟡 MODERATE - Bot needs significant work")
    else:
        print("🔴 POOR - Bot needs major fixes")
    
    # Specific recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 30)
    
    if syntax_errors > 0:
        print("🔧 Fix syntax/indentation errors first")
    
    if not live_ok:
        print("🔥 Complete Live Data Engine implementation")
    
    if integration_score < 80:
        print("🔗 Fix module integration issues")
    
    if feature_score < 70:
        print("🎯 Complete promised feature implementations")
    
    return overall_score >= 75


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)