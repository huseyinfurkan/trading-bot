"""
Advanced Trading Bot - Backtest Runner
Research-backed strategy backtesting
"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any
from loguru import logger

from src.utils.logger_setup import setup_logging
from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.trading.exchange_manager import ExchangeManager
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.signal_filter import AISignalFilter
from src.ai.confidence_calculator import ConfidenceCalculator
from src.trading.adaptive_strategy_engine import AdaptiveStrategyEngine


class BacktestRunner:
    """Comprehensive backtesting system for research-backed strategies"""
    
    def __init__(self):
        self.config = None
        self.db_manager = None
        self.exchange_manager = None
        self.market_analyzer = None
        self.signal_filter = None
        self.confidence_calculator = None
        self.strategy_engine = None
        
    async def initialize(self):
        """Initialize all components for backtesting"""
        try:
            logger.info("🚀 Backtesting Runner başlatılıyor...")
            
            # Load configuration
            self.config = ConfigManager('config/config.yaml')
            await self.config.load_config()
            
            # Initialize core components
            self.db_manager = DatabaseManager(self.config.config.get('database', {}))
            await self.db_manager.initialize()
            
            # Initialize exchange manager with proper config dict
            exchanges_config = self.config.config.get('exchanges', {
                'bybit': {
                    'enabled': True,
                    'testnet': False,
                    'api_key': '',
                    'secret': ''
                }
            })
            logger.info(f"🔧 Exchange config type: {type(exchanges_config)}")
            self.exchange_manager = ExchangeManager(exchanges_config)
            await self.exchange_manager.initialize()
            
            # Initialize AI components
            self.market_analyzer = MarketAnalyzer(self.config, self.exchange_manager)
            self.signal_filter = AISignalFilter(
                self.config.config.get('ai_settings', {}), 
                self.db_manager, 
                self.exchange_manager
            )
            self.confidence_calculator = ConfidenceCalculator(
                self.config.config.get('ai_settings', {}), 
                self.db_manager
            )
            
            # Initialize strategy engine
            self.strategy_engine = AdaptiveStrategyEngine(
                self.config.config, 
                self.exchange_manager, 
                self.signal_filter
            )
            
            logger.success("✅ Backtesting components initialized")
            
        except Exception as e:
            logger.error(f"❌ Backtest initialization error: {e}")
            raise
    
    async def run_backtest(self, symbol: str, strategy: str, start_date: datetime, 
                          end_date: datetime, initial_capital: float = 10000, custom_params: Dict = None) -> Dict[str, Any]:
        """Run single strategy backtest"""
        try:
            logger.info(f"📊 Backtesting {strategy} on {symbol}")
            logger.info(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"💰 Initial capital: ${initial_capital:,.2f}")
            
            # Fetch historical data
            logger.info("📡 Fetching historical data...")
            
            # Use strategy-specific timeframes optimized for market conditions
            if 'alligator' in strategy:
                timeframe = '15m'  # Trend following optimized for 15m
            elif 'bollinger' in strategy:
                timeframe = '5m'   # Mean reversion optimized for 5m (sideways markets)
            else:
                timeframe = '15m'  # Default fallback
            
            logger.info(f"📊 Using {timeframe} timeframe for {strategy}")
            
            historical_data = await self.exchange_manager.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if historical_data is None or len(historical_data) < 100:
                return {
                    'error': 'Insufficient historical data',
                    'symbol': symbol,
                    'strategy': strategy,
                    'initial_capital': initial_capital,
                    'final_capital': initial_capital,
                    'total_return': 0.0
                }
            
            logger.success(f"✅ Historical data: {len(historical_data)} candles")
            
            # Run backtest using strategy engine with custom params
            results = await self.strategy_engine.backtest_strategy(
                strategy_name=strategy,
                symbol=symbol,
                historical_data=historical_data,
                initial_capital=initial_capital,
                custom_params=custom_params
            )
            
            logger.info(f"✅ Backtest completed: {results.get('total_return', 0):.2%} return, {results.get('total_trades', 0)} trades")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            return {
                'error': str(e),
                'symbol': symbol,
                'strategy': strategy,
                'initial_capital': initial_capital,
                'final_capital': initial_capital,
                'total_return': 0.0
            }
    
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
                
                all_results[symbol] = symbol_results
            
            # Print summary
            self._print_multi_backtest_summary(all_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Multi-symbol backtest error: {e}")
            return {}
    
    async def parameter_optimization(self, symbol: str, strategy: str, 
                                   start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Parameter optimization for strategies"""
        try:
            logger.info(f"🔧 Parameter optimization for {strategy} on {symbol}")
            
            # Run base strategy
            base_result = await self.run_backtest(symbol, strategy, start_date, end_date)
            base_return = base_result.get('total_return', 0)
            
            logger.info(f"📊 Base strategy return: {base_return:.2%}")
            
            # Define AGGRESSIVE parameter variations for HIGH RETURNS
            if 'alligator' in strategy:
                param_variations = [
                    {'profit_target': 0.08, 'stop_loss': 0.03, 'confidence_threshold': 0.5},   # Aggressive
                    {'profit_target': 0.12, 'stop_loss': 0.04, 'confidence_threshold': 0.6},   # Very aggressive  
                    {'profit_target': 0.15, 'stop_loss': 0.05, 'confidence_threshold': 0.4},   # Ultra aggressive
                    {'profit_target': 0.10, 'stop_loss': 0.035, 'confidence_threshold': 0.55}  # Balanced aggressive
                ]
            elif 'bollinger' in strategy:
                param_variations = [
                    {'profit_target': 0.05, 'stop_loss': 0.02, 'confidence_threshold': 0.5},   # Aggressive
                    {'profit_target': 0.08, 'stop_loss': 0.025, 'confidence_threshold': 0.6},  # Very aggressive
                    {'profit_target': 0.10, 'stop_loss': 0.03, 'confidence_threshold': 0.45},  # Ultra aggressive 
                    {'profit_target': 0.07, 'stop_loss': 0.022, 'confidence_threshold': 0.55}  # Balanced aggressive
                ]
            else:
                param_variations = []
            
            best_return = base_return
            best_params = "Base parameters"
            
            logger.info(f"🔍 Testing {len(param_variations)} parameter variations...")
            
            # Test each parameter variation
            for i, params in enumerate(param_variations):
                logger.info(f"📊 Testing variation {i+1}/{len(param_variations)}: {params}")
                
                # Run backtest with custom parameters
                result = await self.run_backtest(symbol, strategy, start_date, end_date, 10000, params)
                current_return = result.get('total_return', 0)
                
                logger.info(f"   Result: {current_return:.2%} return")
                
                if current_return > best_return:
                    best_return = current_return
                    best_params = params
                    logger.info(f"   🎯 New best parameters found!")
            
            improvement = ((best_return - base_return) / base_return * 100) if base_return != 0 else 0
            
            logger.info(f"✅ Optimization complete:")
            logger.info(f"   Base return: {base_return:.2%}")
            logger.info(f"   Best return: {best_return:.2%}")
            logger.info(f"   Improvement: {improvement:.1f}%")
            
            return {
                'symbol': symbol,
                'strategy': strategy,
                'base_return': base_return,
                'best_return': best_return,
                'improvement': improvement,
                'best_params': best_params,
                'variations_tested': len(param_variations)
            }
            
        except Exception as e:
            logger.error(f"❌ Parameter optimization error: {e}")
            return {}
    
    def _print_multi_backtest_summary(self, results: Dict[str, Any]):
        """Print summary of multi-symbol backtest"""
        try:
            print("\n" + "=" * 60)
            print("📊 MULTI-SYMBOL BACKTEST SUMMARY")
            print("=" * 60)
            
            total_tests = 0
            profitable_tests = 0
            total_return = 0
            best_combo = ""
            best_return = -999
            
            for symbol, strategies in results.items():
                print(f"\n📈 {symbol}:")
                for strategy, result in strategies.items():
                    if 'error' not in result:
                        ret = result.get('total_return', 0)
                        total_return += ret
                        total_tests += 1
                        
                        if ret > 0:
                            profitable_tests += 1
                        
                        if ret > best_return:
                            best_return = ret
                            best_combo = f"{symbol}-{strategy}"
                        
                        print(f"   {strategy}: {ret:.2%} return, {result.get('total_trades', 0)} trades")
                    else:
                        print(f"   {strategy}: ❌ {result['error']}")
            
            print(f"\n📊 OVERALL SUMMARY:")
            print(f"   Total tests: {total_tests}")
            print(f"   Profitable: {profitable_tests}")
            print(f"   Win rate: {profitable_tests/total_tests:.1%}" if total_tests > 0 else "   Win rate: 0%")
            print(f"   Average return: {total_return/total_tests:.2%}" if total_tests > 0 else "   Average return: 0%")
            print(f"   Best combination: {best_combo} ({best_return:.2%})")
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Summary print error: {e}")
    
    async def close(self):
        """Close all connections"""
        try:
            if self.exchange_manager:
                await self.exchange_manager.close()
            if self.db_manager:
                await self.db_manager.close()
        except Exception as e:
            logger.error(f"❌ Close error: {e}")


# Global variables for main function
backtest_runner = None
start_date = datetime.now() - timedelta(days=180)  # 6 months ago
end_date = datetime.now()


async def initialize():
    """Initialize global backtest runner"""
    global backtest_runner
    backtest_runner = BacktestRunner()
    await backtest_runner.initialize()


async def main():
    """Main backtest runner"""
    setup_logging({
        'level': 'INFO',
        'file_path': 'logs/backtest.log',
        'console_output': True
    })
    
    try:
        # Initialize backtest runner
        await initialize()
        
        # NEW: Use research-backed strategies
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        strategies = ['alligator_ma_momentum', 'bollinger_rsi_stochrsi']  # Research-backed strategies
        
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