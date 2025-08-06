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
            self.ai_signal_filter = AISignalFilter(config['ai'], self.db_manager, self.exchange_manager)
            self.confidence_calculator = ConfidenceCalculator(config['ai'], self.db_manager)
            
            # Initialize NEW Adaptive Strategy Engine
            from src.trading.adaptive_strategy_engine import AdaptiveStrategyEngine
            self.strategy_engine = AdaptiveStrategyEngine(
                config.get('strategies', {}),
                self.exchange_manager,
                self.ai_signal_filter
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
            
            # Apply optimized parameters if successful
            if results and 'best_params' in results:
                logger.info("🔧 Applying optimized parameters to strategy")
                self.strategy_engine.apply_optimized_parameters(strategy, results['best_params'])
                
                # Run final backtest with optimized parameters
                logger.info("🧪 Running final backtest with optimized parameters")
                final_results = await self.strategy_engine.backtest_strategy(
                    symbol=symbol,
                    strategy=strategy,
                    historical_data=historical_data
                )
                
                results['final_backtest'] = final_results
                logger.success(f"✅ Final optimized performance: {final_results.get('roi', 0):.2%} ROI")
            
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
    """Main backtest runner"""
    from src.utils.logger_setup import setup_logging
    setup_logging('backtest')
    
    try:
        # Initialize backtest runner
        await initialize()
        
        # NEW: Use adaptive strategies instead of old broken ones
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        strategies = ['volatility_breakout', 'mean_reversion_adaptive']  # Only 2 proven strategies
        
        print("🚀 ADVANCED TRADING BOT - BACKTESTING")
        print("=" * 50)
        print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"📊 Symbols: {', '.join(symbols)}")
        print(f"🎯 Strategies: {', '.join(strategies)}")
        print()
        print("1. Single Symbol Backtest")
        print("2. Multi-Symbol Backtest") 
        print("3. Parameter Optimization")
        print()
        
        choice = input("Select option (1-3): ")
        
        if choice == "1":
            symbol = input(f"Enter symbol ({'/'.join(symbols)}): ").upper()
            if symbol not in symbols:
                symbol = symbols[0]
            
            strategy = input(f"Enter strategy ({'/'.join(strategies)}): ").lower()
            if strategy not in strategies:
                strategy = strategies[0]
                
            result = await backtest_runner.run_backtest(
                symbol=symbol,
                strategy=strategy,
                start_date=start_date,
                end_date=end_date
            )
            
            print_backtest_results(result)
            
        elif choice == "2":
            await backtest_runner.multi_symbol_backtest(symbols, strategies, start_date, end_date)
            
        elif choice == "3":
            await backtest_runner.parameter_optimization(symbols[0], strategies[0], start_date, end_date)
            
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        logger.info("👋 Backtest interrupted by user")
    except Exception as e:
        logger.error(f"❌ Backtest error: {e}")
        traceback.print_exc()

def print_backtest_results(result: Dict[str, Any]):
    """Print formatted backtest results"""
    print("\n" + "=" * 50)
    print("📊 BACKTEST RESULTS")
    print("=" * 50)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"💰 Initial Capital: ${result['initial_capital']:,.2f}")
    print(f"💰 Final Capital: ${result['final_capital']:,.2f}")
    print(f"📈 Total Return: {result['total_return']:.2%}")
    print(f"🎯 Strategy: {result['strategy']}")
    print(f"📊 Symbol: {result['symbol']}")
    print()
    print(f"📈 Total Trades: {result['total_trades']}")
    print(f"✅ Winning Trades: {result['winning_trades']}")
    print(f"❌ Losing Trades: {result['losing_trades']}")
    print(f"🎯 Win Rate: {result['win_rate']:.1%}")
    print()
    print(f"💰 Average Win: ${result['avg_win']:.2f}")
    print(f"💸 Average Loss: ${result['avg_loss']:.2f}")
    print(f"⚖️ Profit Factor: {result['profit_factor']:.2f}")
    print(f"📉 Max Drawdown: {result['max_drawdown']:.2%}")
    print(f"📊 Sharpe Ratio: {result['sharpe_ratio']:.2f}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())