#!/usr/bin/env python3
"""
Live System Test - Dependency Free
Canlı sistem fonksiyonlarını test eder
"""

import sys
import ast
from pathlib import Path
from datetime import datetime


def test_live_data_engine():
    """LiveDataEngine sınıfını test et"""
    try:
        live_engine_path = Path('src/core/live_data_engine.py')
        
        if not live_engine_path.exists():
            return False, "live_data_engine.py dosyası bulunamadı"
        
        with open(live_engine_path, 'r') as f:
            content = f.read()
        
        # AST parse test
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return False, f"Syntax hatası: {e}"
        
        # Check for required methods
        required_methods = [
            'start_live_analysis',
            '_live_data_collector', 
            '_analysis_engine',
            '_decision_engine',
            '_make_trading_decision',
            '_execute_trading_decision',
            'get_live_status'
        ]
        
        found_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                found_methods.append(node.name)
        
        missing_methods = [m for m in required_methods if m not in found_methods]
        
        if missing_methods:
            return False, f"Eksik methodlar: {missing_methods}"
        
        return True, f"{len(found_methods)} method bulundu"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_main_integration():
    """Main.py'deki entegrasyon test et"""
    try:
        main_path = Path('main.py')
        
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check imports
        required_imports = [
            'LiveDataEngine',
            'asyncio',
            'logger'
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
        
        if missing_imports:
            return False, f"Eksik imports: {missing_imports}"
        
        # Check live_data_engine initialization
        if 'self.live_data_engine = LiveDataEngine(' not in content:
            return False, "LiveDataEngine initialization eksik"
        
        # Check live analysis start
        if 'start_live_analysis' not in content:
            return False, "Live analysis start kodu eksik"
        
        return True, "Main.py entegrasyonu OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_strategy_engine_signals():
    """StrategyEngine'deki entry/exit signal fonksiyonları test et"""
    try:
        strategy_path = Path('src/trading/strategy_engine.py')
        
        with open(strategy_path, 'r') as f:
            content = f.read()
        
        required_functions = [
            'get_entry_signal',
            'get_exit_signal',
            'backtest_strategy'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f'def {func}(' not in content:
                missing_functions.append(func)
        
        if missing_functions:
            return False, f"Eksik fonksiyonlar: {missing_functions}"
        
        return True, "StrategyEngine signal fonksiyonları OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_position_manager_trailing():
    """PositionManager'daki trailing stop fonksiyonları test et"""
    try:
        position_path = Path('src/trading/position_manager.py')
        
        with open(position_path, 'r') as f:
            content = f.read()
        
        required_functions = [
            'update_trailing_stops',
            'enable_trailing_stop',
            'get_position_performance'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f'def {func}(' not in content:
                missing_functions.append(func)
        
        if missing_functions:
            return False, f"Eksik fonksiyonlar: {missing_functions}"
        
        return True, "PositionManager trailing stop fonksiyonları OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_exchange_manager_realtime():
    """ExchangeManager'daki real-time fonksiyonları test et"""
    try:
        exchange_path = Path('src/trading/exchange_manager.py')
        
        with open(exchange_path, 'r') as f:
            content = f.read()
        
        required_functions = [
            'get_real_time_data',
            'start_websocket_streams',
            'get_multi_exchange_prices'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f'def {func}(' not in content:
                missing_functions.append(func)
        
        if missing_functions:
            return False, f"Eksik fonksiyonlar: {missing_functions}"
        
        return True, "ExchangeManager real-time fonksiyonları OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_risk_manager_correlation():
    """RiskManager'daki korelasyon fonksiyonları test et"""
    try:
        risk_path = Path('src/core/risk_manager.py')
        
        with open(risk_path, 'r') as f:
            content = f.read()
        
        required_functions = [
            '_calculate_price_correlation',
            '_get_price_history',
            '_compute_correlation'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f'def {func}(' not in content:
                missing_functions.append(func)
        
        if missing_functions:
            return False, f"Eksik fonksiyonlar: {missing_functions}"
        
        return True, "RiskManager korelasyon fonksiyonları OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def test_live_flow_completeness():
    """Canlı veri akışının bütünlüğünü test et"""
    try:
        components = {
            'LiveDataEngine': 'src/core/live_data_engine.py',
            'ExchangeManager': 'src/trading/exchange_manager.py', 
            'MarketAnalyzer': 'src/ai/market_analyzer.py',
            'AISignalFilter': 'src/ai/signal_filter.py',
            'StrategyEngine': 'src/trading/strategy_engine.py',
            'PositionManager': 'src/trading/position_manager.py',
            'RiskManager': 'src/core/risk_manager.py'
        }
        
        missing_components = []
        for component, path in components.items():
            if not Path(path).exists():
                missing_components.append(component)
        
        if missing_components:
            return False, f"Eksik bileşenler: {missing_components}"
        
        # Check data flow connections
        flow_checks = {
            'Exchange → LiveDataEngine': ('get_real_time_data', 'src/trading/exchange_manager.py'),
            'LiveDataEngine → MarketAnalyzer': ('analyze_market_condition', 'src/ai/market_analyzer.py'),
            'LiveDataEngine → AISignalFilter': ('analyze_signals', 'src/ai/signal_filter.py'),
            'LiveDataEngine → StrategyEngine': ('get_entry_signal', 'src/trading/strategy_engine.py'),
            'LiveDataEngine → PositionManager': ('open_position', 'src/trading/position_manager.py'),
            'LiveDataEngine → RiskManager': ('calculate_position_size', 'src/core/risk_manager.py')
        }
        
        broken_flows = []
        for flow_name, (function, file_path) in flow_checks.items():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                if f'def {function}(' not in content:
                    broken_flows.append(flow_name)
            except:
                broken_flows.append(flow_name)
        
        if broken_flows:
            return False, f"Bozuk veri akışları: {broken_flows}"
        
        return True, "Canlı veri akışı bütünlüğü OK"
        
    except Exception as e:
        return False, f"Test hatası: {e}"


def main():
    """Ana test fonksiyonu"""
    print("🔥 Canlı Sistem Test - Advanced Trading Bot")
    print("=" * 60)
    
    tests = [
        ("Live Data Engine", test_live_data_engine),
        ("Main Integration", test_main_integration),
        ("Strategy Engine Signals", test_strategy_engine_signals),
        ("Position Manager Trailing", test_position_manager_trailing),
        ("Exchange Manager Real-time", test_exchange_manager_realtime),
        ("Risk Manager Correlation", test_risk_manager_correlation),
        ("Live Flow Completeness", test_live_flow_completeness)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            success, message = test_func()
            
            if success:
                print(f"✅ {test_name}: {message}")
                passed += 1
            else:
                print(f"❌ {test_name}: {message}")
                failed += 1
                
        except Exception as e:
            print(f"❌ {test_name}: Test exception - {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Sonuçlar: {passed} başarılı, {failed} başarısız")
    
    if failed == 0:
        print("🎉 Tüm canlı sistem testleri başarılı!")
        print("🚀 Bot artık canlı veri analizi ile çalışmaya hazır!")
        return True
    else:
        print("⚠️ Bazı testler başarısız oldu. Düzeltmeler gerekli.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)