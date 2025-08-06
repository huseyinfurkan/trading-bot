#!/usr/bin/env python3
"""
Backtesting Runner
Gerçek historical data ile backtesting ve optimizasyon
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.trading.exchange_manager import ExchangeManager
from src.trading.strategy_engine import StrategyEngine
from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.confidence_calculator import ConfidenceCalculator
from src.utils.logger_setup import setup_logger

# Setup logger
logger = setup_logger('backtest_runner', 'logs/backtest.log')


class BacktestRunner:
    """Gerçek data ile backtesting runner"""
    
    def __init__(self):
        self.config_manager = None
        self.db_manager = None
        self.exchange_manager = None
        self.strategy_engine = None
        self.ai_signal_filter = None
        self.market_analyzer = None
        self.confidence_calculator = None
        
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("🚀 Backtesting Runner başlatılıyor...")
            
            # Load configuration
            self.config_manager = ConfigManager('config/config.yaml')
            await self.config_manager.load_config()
            config = self.config_manager.config
            
            # Initialize database
            self.db_manager = DatabaseManager(config['database'])
            await self.db_manager.initialize()
            
            # Initialize exchange manager
            self.exchange_manager = ExchangeManager(config['exchanges'])
            await self.exchange_manager.initialize()
            
            # Initialize AI components
            self.market_analyzer = MarketAnalyzer(config['market_analysis'], self.db_manager)
            self.ai_signal_filter = AISignalFilter(config['ai'], self.db_manager)
            self.confidence_calculator = ConfidenceCalculator(config['ai'], self.db_manager)
            
            # Initialize strategy engine
            self.strategy_engine = StrategyEngine(
                config['strategies'],
                self.ai_signal_filter,
                self.market_analyzer,
                self.confidence_calculator
            )
            
            logger.success("✅ Backtesting components initialized")
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
    
    async def run_backtest(self, symbol: str, strategy: str, 
                          start_date: datetime, end_date: datetime,
                          initial_capital: float = 10000) -> Dict[str, Any]:
        """Single backtest execution"""
        try:
            logger.info(f"📊 Backtesting {strategy} on {symbol}")
            logger.info(f"📅 Period: {start_date.date()} to {end_date.date()}")
            logger.info(f"💰 Initial capital: ${initial_capital:,.2f}")
            
            # Get historical data
            logger.info("📡 Fetching historical data...")
            historical_data = await self.exchange_manager.get_historical_data(
                symbol=symbol,
                timeframe='1h',
                start_date=start_date,
                end_date=end_date
            )
            
            if historical_data is None or historical_data.empty:
                logger.error(f"❌ No historical data for {symbol}")
                return {'error': 'No historical data available'}
            
            logger.success(f"✅ Historical data: {len(historical_data)} candles")
            
            # Run backtest
            results = await self.strategy_engine.backtest_strategy(
                symbol=symbol,
                strategy=strategy,
                historical_data=historical_data,
                initial_capital=initial_capital
            )
            
            # Add metadata
            results.update({
                'symbol': symbol,
                'strategy': strategy,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'initial_capital': initial_capital,
                'data_points': len(historical_data),
                'backtest_timestamp': datetime.now().isoformat()
            })
            
            # Save results
            await self._save_backtest_results(results)
            
            logger.success(f"✅ Backtest completed: {results.get('roi', 0):.2f}% ROI")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            return {'error': str(e)}
    
    async def run_optimization(self, symbol: str, strategy: str,
                             start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Parameter optimization"""
        try:
            logger.info(f"🔧 Optimizing {strategy} parameters for {symbol}")
            
            # Get historical data
            historical_data = await self.exchange_manager.get_historical_data(
                symbol=symbol,
                timeframe='1h',
                start_date=start_date,
                end_date=end_date
            )
            
            if historical_data is None or historical_data.empty:
                return {'error': 'No historical data available'}
            
            # Run optimization
            results = await self.strategy_engine.optimize_strategy_parameters(
                symbol=symbol,
                strategy=strategy,
                historical_data=historical_data
            )
            
            logger.success(f"✅ Optimization completed")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Optimization error: {e}")
            return {'error': str(e)}
    
    async def multi_symbol_backtest(self, symbols: List[str], strategies: List[str],
                                  start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Multiple symbols and strategies backtest"""
        try:
            logger.info(f"🔄 Multi-symbol backtest: {len(symbols)} symbols, {len(strategies)} strategies")
            
            all_results = {}
            
            for symbol in symbols:
                symbol_results = {}
                
                for strategy in strategies:
                    logger.info(f"📊 Testing {strategy} on {symbol}")
                    
                    result = await self.run_backtest(
                        symbol=symbol,
                        strategy=strategy,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    symbol_results[strategy] = result
                    
                    # Brief pause to avoid overwhelming the system
                    await asyncio.sleep(0.5)
                
                all_results[symbol] = symbol_results
            
            # Generate summary
            summary = self._generate_summary(all_results)
            
            logger.success(f"✅ Multi-symbol backtest completed")
            
            return {
                'individual_results': all_results,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"❌ Multi-symbol backtest error: {e}")
            return {'error': str(e)}
    
    def _generate_summary(self, results: Dict) -> Dict[str, Any]:
        """Generate summary statistics"""
        try:
            total_tests = 0
            profitable_tests = 0
            total_roi = 0
            best_roi = -float('inf')
            worst_roi = float('inf')
            best_combo = None
            worst_combo = None
            
            for symbol, strategies in results.items():
                for strategy, result in strategies.items():
                    if 'error' not in result:
                        total_tests += 1
                        roi = result.get('roi', 0)
                        total_roi += roi
                        
                        if roi > 0:
                            profitable_tests += 1
                        
                        if roi > best_roi:
                            best_roi = roi
                            best_combo = f"{symbol} - {strategy}"
                        
                        if roi < worst_roi:
                            worst_roi = roi
                            worst_combo = f"{symbol} - {strategy}"
            
            return {
                'total_tests': total_tests,
                'profitable_tests': profitable_tests,
                'win_rate': (profitable_tests / total_tests * 100) if total_tests > 0 else 0,
                'average_roi': total_roi / total_tests if total_tests > 0 else 0,
                'best_roi': best_roi,
                'worst_roi': worst_roi,
                'best_combination': best_combo,
                'worst_combination': worst_combo
            }
            
        except Exception as e:
            logger.error(f"❌ Summary generation error: {e}")
            return {}
    
    async def _save_backtest_results(self, results: Dict[str, Any]):
        """Save backtest results to database"""
        try:
            # This would save to a backtest_results table
            # For now, just log the key metrics
            logger.info("💾 Saving backtest results...")
            logger.info(f"📈 ROI: {results.get('roi', 0):.2f}%")
            logger.info(f"🎯 Win Rate: {results.get('win_rate', 0):.1f}%")
            logger.info(f"💰 Final Capital: ${results.get('final_capital', 0):,.2f}")
            logger.info(f"📊 Total Trades: {results.get('total_trades', 0)}")
            
        except Exception as e:
            logger.error(f"❌ Save results error: {e}")
    
    async def close(self):
        """Close all connections"""
        try:
            if self.exchange_manager:
                await self.exchange_manager.close()
            if self.db_manager:
                await self.db_manager.close()
            logger.info("✅ Backtesting runner closed")
            
        except Exception as e:
            logger.error(f"❌ Close error: {e}")


async def main():
    """Main backtesting function"""
    runner = BacktestRunner()
    
    try:
        await runner.initialize()
        
        # Define test parameters
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        strategies = ['scalping', 'swing_trading', 'trend_following', 'mean_reversion']
        
        # Date range (last 6 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        
        print("🚀 ADVANCED TRADING BOT - BACKTESTING")
        print("=" * 50)
        print(f"📅 Period: {start_date.date()} to {end_date.date()}")
        print(f"📊 Symbols: {', '.join(symbols)}")
        print(f"🎯 Strategies: {', '.join(strategies)}")
        print()
        
        # Option 1: Single backtest
        print("1. Single Symbol Backtest")
        print("2. Multi-Symbol Backtest")
        print("3. Parameter Optimization")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            symbol = input("Enter symbol (e.g., BTCUSDT): ").strip().upper()
            strategy = input("Enter strategy (scalping/swing_trading/trend_following/mean_reversion): ").strip()
            
            if symbol and strategy in strategies:
                results = await runner.run_backtest(symbol, strategy, start_date, end_date)
                
                print(f"\n📊 BACKTEST RESULTS - {symbol} {strategy}")
                print("=" * 40)
                print(f"ROI: {results.get('roi', 0):.2f}%")
                print(f"Win Rate: {results.get('win_rate', 0):.1f}%")
                print(f"Total Trades: {results.get('total_trades', 0)}")
                print(f"Final Capital: ${results.get('final_capital', 0):,.2f}")
        
        elif choice == '2':
            results = await runner.multi_symbol_backtest(symbols, strategies, start_date, end_date)
            
            summary = results.get('summary', {})
            print(f"\n📊 MULTI-SYMBOL BACKTEST SUMMARY")
            print("=" * 40)
            print(f"Total Tests: {summary.get('total_tests', 0)}")
            print(f"Profitable: {summary.get('profitable_tests', 0)}")
            print(f"Win Rate: {summary.get('win_rate', 0):.1f}%")
            print(f"Average ROI: {summary.get('average_roi', 0):.2f}%")
            print(f"Best: {summary.get('best_combination', 'N/A')} ({summary.get('best_roi', 0):.2f}%)")
            print(f"Worst: {summary.get('worst_combination', 'N/A')} ({summary.get('worst_roi', 0):.2f}%)")
        
        elif choice == '3':
            symbol = input("Enter symbol for optimization (e.g., BTCUSDT): ").strip().upper()
            strategy = input("Enter strategy to optimize: ").strip()
            
            if symbol and strategy in strategies:
                results = await runner.run_optimization(symbol, strategy, start_date, end_date)
                
                print(f"\n🔧 OPTIMIZATION RESULTS - {symbol} {strategy}")
                print("=" * 40)
                print(f"Best ROI: {results.get('roi', 0):.2f}%")
                print(f"Tested Combinations: {results.get('tested_combinations', 0)}")
        
        else:
            print("❌ Invalid choice")
        
    except KeyboardInterrupt:
        print("\n🛑 Backtesting interrupted by user")
    except Exception as e:
        print(f"\n❌ Backtesting error: {e}")
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())