#!/usr/bin/env python3
"""
🔍 Signal Generation Debug Script
Traces every step of signal generation to find why no trades occur
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config_manager import ConfigManager
from core.database_manager import DatabaseManager
from trading.exchange_manager import ExchangeManager
from trading.adaptive_strategy_engine import AdaptiveStrategyEngine
from ai.signal_filter import AISignalFilter

async def debug_signal_generation():
    """Debug signal generation step by step"""
    print("🔍 SIGNAL GENERATION DEBUG")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    db_manager = DatabaseManager(config['database'])
    await db_manager.initialize()
    
    exchange_manager = ExchangeManager(config['exchanges'])
    await exchange_manager.initialize()
    
    ai_signal_filter = AISignalFilter(config['ai'], db_manager, exchange_manager)
    await ai_signal_filter.initialize()
    
    strategy_engine = AdaptiveStrategyEngine(config['strategies'], exchange_manager, ai_signal_filter)
    
    # Test parameters
    symbol = 'BTCUSDT'
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)  # Last 24 hours
    
    print(f"\n📊 Testing: {symbol}")
    print(f"⏰ Period: {start_date} to {end_date}")
    
    # STEP 1: Test data fetching
    print("\n🔹 STEP 1: Data Fetching")
    print("-" * 30)
    
    data_15m = await exchange_manager.get_historical_data(symbol, '15m', start_date, end_date)
    data_5m = await exchange_manager.get_historical_data(symbol, '5m', start_date, end_date)
    
    print(f"📊 15m data: {len(data_15m) if data_15m is not None else 'None'} candles")
    print(f"📊 5m data: {len(data_5m) if data_5m is not None else 'None'} candles")
    
    if data_15m is None or len(data_15m) < 100:
        print("❌ Insufficient 15m data!")
        return
    
    if data_5m is None or len(data_5m) < 100:
        print("❌ Insufficient 5m data!")
        return
    
    # STEP 2: Test market regime analysis
    print("\n🔹 STEP 2: Market Regime Analysis")
    print("-" * 30)
    
    try:
        regime_analysis = await strategy_engine.analyze_market_regime(symbol)
        print(f"✅ Regime analysis successful:")
        for key, value in regime_analysis.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Regime analysis failed: {e}")
        return
    
    # STEP 3: Test individual strategy signals 
    print("\n🔹 STEP 3: Individual Strategy Testing")
    print("-" * 30)
    
    # Test last few candles
    test_points = [len(data_15m)-10, len(data_15m)-5, len(data_15m)-1]
    
    for point in test_points:
        print(f"\n🔸 Testing candle {point}:")
        current_price = data_15m.iloc[point]['close']
        print(f"   💰 Price: ${current_price:.2f}")
        
        # Prepare market data
        market_data = {
            'symbol': symbol,
            'price': current_price,
            'volume': data_15m.iloc[point]['volume'],
            'timestamp': datetime.now()
        }
        
        # Test Alligator strategy directly
        print("\n   🐊 Testing Alligator Strategy:")
        try:
            alligator_signal = await strategy_engine._alligator_ma_signal(
                symbol, market_data, {'confidence': 0.0}, data_15m.iloc[:point+1]
            )
            print(f"      Action: {alligator_signal.get('action', 'None')}")
            print(f"      Confidence: {alligator_signal.get('confidence', 0):.3f}")
            print(f"      Reason: {alligator_signal.get('reasons', ['No reason'])[0]}")
        except Exception as e:
            print(f"      ❌ Alligator error: {e}")
        
        # Test Bollinger strategy directly
        print("\n   📊 Testing Bollinger Strategy:")
        try:
            # Use 5m data for bollinger
            point_5m = min(point * 3, len(data_5m)-1)  # Approximate 5m equivalent
            market_data_5m = {
                'symbol': symbol,
                'price': data_5m.iloc[point_5m]['close'],
                'volume': data_5m.iloc[point_5m]['volume'],
                'timestamp': datetime.now()
            }
            
            bollinger_signal = await strategy_engine._bollinger_rsi_stochrsi_signal(
                symbol, market_data_5m, {'confidence': 0.0}, data_5m.iloc[:point_5m+1]
            )
            print(f"      Action: {bollinger_signal.get('action', 'None')}")
            print(f"      Confidence: {bollinger_signal.get('confidence', 0):.3f}")
            print(f"      Reason: {bollinger_signal.get('reasons', ['No reason'])[0]}")
        except Exception as e:
            print(f"      ❌ Bollinger error: {e}")
    
    # STEP 4: Test AI signal filtering
    print("\n🔹 STEP 4: AI Signal Filtering")
    print("-" * 30)
    
    test_regime = regime_analysis.get('regime', 'sideways_market')
    
    try:
        ai_result = await ai_signal_filter.filter_signal(symbol, market_data, test_regime)
        print(f"✅ AI filter successful:")
        print(f"   Signal: {ai_result.get('signal', 'None')}")
        print(f"   Confidence: {ai_result.get('confidence', 0):.3f}")
        print(f"   ML Probability: {ai_result.get('ml_probability', 0):.3f}")
    except Exception as e:
        print(f"❌ AI filter failed: {e}")
    
    # STEP 5: Test complete get_entry_signal flow
    print("\n🔹 STEP 5: Complete Signal Flow")
    print("-" * 30)
    
    try:
        final_signal = await strategy_engine.get_entry_signal(
            symbol, market_data, test_regime, data_15m.iloc[:len(data_15m)-1]
        )
        print(f"✅ Final signal:")
        print(f"   Action: {final_signal.get('action', 'None')}")
        print(f"   Confidence: {final_signal.get('confidence', 0):.3f}")
        print(f"   Combined Confidence: {final_signal.get('combined_confidence', 0):.3f}")
        print(f"   AI Confidence: {final_signal.get('ai_confidence', 0):.3f}")
        print(f"   Strategy: {final_signal.get('strategy_used', 'None')}")
        
        # Test confidence threshold
        confidence_threshold = 0.70
        signal_confidence = final_signal.get('combined_confidence', final_signal.get('confidence', 0.0))
        
        print(f"\n🎯 Confidence Check:")
        print(f"   Signal Confidence: {signal_confidence:.3f}")
        print(f"   Threshold: {confidence_threshold}")
        print(f"   Pass Threshold: {'✅' if signal_confidence > confidence_threshold else '❌'}")
        
        if final_signal.get('action') in ['BUY', 'SELL'] and signal_confidence > confidence_threshold:
            print("✅ SIGNAL WOULD TRIGGER TRADE!")
        else:
            print("❌ Signal would NOT trigger trade")
            if final_signal.get('action') == 'HOLD':
                print("   Reason: Action is HOLD")
            elif signal_confidence <= confidence_threshold:
                print(f"   Reason: Confidence {signal_confidence:.3f} <= {confidence_threshold}")
                
    except Exception as e:
        print(f"❌ Complete signal flow failed: {e}")
        import traceback
        traceback.print_exc()
    
    # STEP 6: Test multiple recent points for signal frequency
    print("\n🔹 STEP 6: Signal Frequency Analysis")
    print("-" * 30)
    
    signal_count = 0
    total_tests = 20
    
    for i in range(total_tests):
        try:
            point = len(data_15m) - total_tests + i
            if point < 100:
                continue
                
            test_price = data_15m.iloc[point]['close']
            test_market_data = {
                'symbol': symbol,
                'price': test_price,
                'volume': data_15m.iloc[point]['volume'],
                'timestamp': datetime.now()
            }
            
            test_signal = await strategy_engine.get_entry_signal(
                symbol, test_market_data, test_regime, data_15m.iloc[:point+1]
            )
            
            test_confidence = test_signal.get('combined_confidence', test_signal.get('confidence', 0.0))
            
            if test_signal.get('action') in ['BUY', 'SELL'] and test_confidence > 0.70:
                signal_count += 1
                print(f"   🎯 Signal {signal_count}: {test_signal.get('action')} @ ${test_price:.2f} (conf: {test_confidence:.3f})")
                
        except Exception as e:
            print(f"   ❌ Error at point {i}: {e}")
    
    print(f"\n📊 Signal Frequency: {signal_count}/{total_tests} ({signal_count/total_tests*100:.1f}%)")
    
    if signal_count == 0:
        print("🚨 NO SIGNALS GENERATED - PROBLEM CONFIRMED!")
        print("\n🔍 SUGGESTED ACTIONS:")
        print("1. Lower confidence threshold (try 0.60)")
        print("2. Check strategy conditions are not too strict")
        print("3. Verify AI filter is not blocking all signals")
        print("4. Test with different market conditions")
    else:
        print(f"✅ Signals are being generated ({signal_count} found)")

if __name__ == "__main__":
    asyncio.run(debug_signal_generation())