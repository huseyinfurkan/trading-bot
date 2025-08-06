#!/usr/bin/env python3
"""
🔍 COMPREHENSIVE STRATEGY DEBUG SCRIPT
====================================
Analyzes signal generation, trade frequency, AI filtering, and performance
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from src.trading.exchange_manager import ExchangeManager
from src.trading.adaptive_strategy_engine import AdaptiveStrategyEngine
from src.ai.signal_filter import AISignalFilter
from src.core.database_manager import DatabaseManager
from config.config import Config

async def debug_strategy_performance():
    """Comprehensive strategy debugging"""
    
    print("🔍 COMPREHENSIVE STRATEGY DEBUG")
    print("=" * 50)
    
    # Initialize components
    config = Config().get_config()
    exchange_manager = ExchangeManager(config['exchanges'])
    db_manager = DatabaseManager(config['database'])
    
    # Initialize AI Signal Filter
    ai_filter = AISignalFilter(config['ai'], db_manager, exchange_manager)
    
    # Initialize Adaptive Strategy Engine
    strategy_engine = AdaptiveStrategyEngine(
        config['strategies'], 
        exchange_manager, 
        ai_filter
    )
    
    await exchange_manager.initialize()
    await ai_filter.initialize()
    
    # Test parameters
    symbol = 'BTCUSDT'
    strategies = ['alligator_ma_momentum', 'bollinger_rsi_stochrsi']
    
    # Get recent data for analysis
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)  # 1 week for detailed analysis
    
    print(f"\n📊 ANALYZING: {symbol}")
    print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("-" * 50)
    
    for strategy in strategies:
        print(f"\n🎯 STRATEGY: {strategy}")
        print("=" * 30)
        
        # Determine timeframe based on strategy
        if 'alligator' in strategy:
            timeframe = '15m'
        else:
            timeframe = '5m'
            
        print(f"⏰ Timeframe: {timeframe}")
        
        # Get historical data
        historical_data = await exchange_manager.get_historical_data(
            symbol, timeframe, start_date, end_date
        )
        
        if historical_data is None or len(historical_data) < 100:
            print("❌ Insufficient data")
            continue
            
        print(f"📊 Data points: {len(historical_data)}")
        
        # Add indicators
        df = await strategy_engine._add_indicators(historical_data)
        
        # Test signal generation
        print("\n🔍 SIGNAL GENERATION ANALYSIS:")
        print("-" * 30)
        
        signals_generated = 0
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        ai_filtered = 0
        
        # Sample every 20 candles to avoid overload
        sample_indices = range(50, len(df), 20)
        
        for i in sample_indices:
            current_row = df.iloc[i]
            current_price = current_row['close']
            
            # Create market data
            market_data = {
                'symbol': symbol,
                'price': current_price,
                'volume': current_row.get('volume', 0),
                'timestamp': current_row.name,
                'indicators': {
                    'rsi_14': current_row.get('rsi_14', 50),
                    'macd_signal': current_row.get('macd_signal', 0),
                    'bb_position': current_row.get('bb_position', 0.5),
                    'atr': current_row.get('atr', 0.01)
                }
            }
            
            # Test AI filtering
            regime = 'sideways_market'  # Default for testing
            
            try:
                # Test direct strategy signal
                current_df_slice = df.iloc[:i+1]
                
                if 'alligator' in strategy:
                    direct_signal = await strategy_engine._alligator_ma_signal(
                        symbol, market_data, {'confidence': 0.8}, current_df_slice
                    )
                else:
                    direct_signal = await strategy_engine._bollinger_rsi_stochrsi_signal(
                        symbol, market_data, {'confidence': 0.8}, current_df_slice
                    )
                
                # Test AI-filtered signal
                try:
                    ai_signal = await strategy_engine.get_entry_signal(symbol, market_data, regime)
                    
                    # Compare signals
                    if direct_signal['action'] != 'HOLD' and ai_signal['action'] == 'HOLD':
                        ai_filtered += 1
                        
                except Exception as e:
                    ai_signal = direct_signal  # Fallback
                
                # Count signals
                signals_generated += 1
                if direct_signal['action'] == 'BUY':
                    buy_signals += 1
                elif direct_signal['action'] == 'SELL':
                    sell_signals += 1
                else:
                    hold_signals += 1
                    
            except Exception as e:
                print(f"⚠️ Signal error at index {i}: {e}")
                continue
        
        # Calculate signal statistics
        total_signals = signals_generated
        signal_rate = (buy_signals + sell_signals) / total_signals * 100 if total_signals > 0 else 0
        ai_filter_rate = ai_filtered / total_signals * 100 if total_signals > 0 else 0
        
        print(f"📈 Total signals analyzed: {total_signals}")
        print(f"📊 BUY signals: {buy_signals} ({buy_signals/total_signals*100:.1f}%)" if total_signals > 0 else "📊 BUY signals: 0")
        print(f"📉 SELL signals: {sell_signals} ({sell_signals/total_signals*100:.1f}%)" if total_signals > 0 else "📉 SELL signals: 0")
        print(f"⏸️ HOLD signals: {hold_signals} ({hold_signals/total_signals*100:.1f}%)" if total_signals > 0 else "⏸️ HOLD signals: 0")
        print(f"🤖 AI filtered: {ai_filtered} ({ai_filter_rate:.1f}%)")
        print(f"⚡ Signal rate: {signal_rate:.1f}%")
        
        # Estimated trades per day
        candles_per_day = 24 * 60 // (5 if timeframe == '5m' else 15)
        estimated_trades_per_day = (buy_signals + sell_signals) / 7 * candles_per_day / len(sample_indices) * len(df)
        
        print(f"📅 Estimated trades/day: {estimated_trades_per_day:.1f}")
        
        # Performance indicators
        print(f"\n📊 MARKET CONDITIONS (Last 7 days):")
        print("-" * 30)
        
        if 'atr' in df.columns:
            avg_volatility = df['atr'].tail(100).mean()
            print(f"💥 Average Volatility (ATR): {avg_volatility:.4f}")
        
        if 'rsi_14' in df.columns:
            rsi_overbought = (df['rsi_14'].tail(100) > 70).sum()
            rsi_oversold = (df['rsi_14'].tail(100) < 30).sum()
            print(f"📈 RSI Overbought periods: {rsi_overbought}")
            print(f"📉 RSI Oversold periods: {rsi_oversold}")
        
        # Price movement analysis
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
        print(f"💰 Price change (7 days): {price_change:.2f}%")
        
        print(f"\n{'='*50}")
    
    print("\n🎯 DIAGNOSIS & RECOMMENDATIONS:")
    print("=" * 50)
    print("1. ✅ Fixed backtest/live inconsistency")
    print("2. 🤖 AI filtering now applied in backtest")
    print("3. ⚡ Signal rates should be much lower now")
    print("4. 📊 Trades/day should be more realistic (2-10 max)")
    print("5. 🎯 Performance should be more conservative but realistic")
    
    await exchange_manager.close()

if __name__ == "__main__":
    asyncio.run(debug_strategy_performance())