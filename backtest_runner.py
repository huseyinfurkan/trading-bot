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
            self.config_manager = ConfigManager('config/config.yaml')
            self.config = await self.config_manager.load_config()
            
            # Initialize core components
            self.db_manager = DatabaseManager(self.config.get('database', {}))
            await self.db_manager.initialize()
            
            # Initialize exchange manager with proper config dict
            exchanges_config = self.config.get('exchanges', {
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
                self.config.get('ai_settings', {}), 
                self.db_manager, 
                self.exchange_manager
            )
            self.confidence_calculator = ConfidenceCalculator(
                self.config.get('ai_settings', {}), 
                self.db_manager
            )
            
            # Initialize RiskManager for consistent position sizing
            from src.core.risk_manager import RiskManager
            self.risk_manager = RiskManager(
                self.config.get('risk_management', {}),
                self.db_manager,
                self.market_analyzer
            )
            
            # Initialize strategy engine WITH RiskManager
            self.strategy_engine = AdaptiveStrategyEngine(
                self.config, 
                self.exchange_manager, 
                self.signal_filter,
                self.risk_manager  # ADDED: For consistent position sizing with live trading
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
            
            # CRITICAL: Train AI models before backtesting (if not already trained)
            logger.info("🤖 Initializing AI models for backtesting...")
            try:
                await self.signal_filter.initialize()
                logger.success("✅ AI models ready for backtesting")
            except Exception as e:
                logger.warning(f"⚠️ AI model initialization failed: {e}, continuing without AI filtering")
            
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
        """ADVANCED parameter optimization with grid search and cross-validation"""
        try:
            logger.info(f"🔧 ADVANCED Parameter optimization for {strategy} on {symbol}")
            
            # 1. SPLIT DATA FOR CROSS-VALIDATION
            total_days = (end_date - start_date).days
            train_days = int(total_days * 0.7)  # 70% for training
            
            train_end = start_date + timedelta(days=train_days)
            validation_start = train_end
            
            logger.info(f"📊 Train period: {start_date.strftime('%Y-%m-%d')} to {train_end.strftime('%Y-%m-%d')}")
            logger.info(f"📊 Validation period: {validation_start.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # 2. DEFINE COMPREHENSIVE PARAMETER GRIDS
            if 'alligator' in strategy:
                param_grid = {
                    'profit_target': [0.04, 0.06, 0.08, 0.10, 0.12],
                    'stop_loss': [0.015, 0.020, 0.025, 0.030, 0.035],
                    'confidence_threshold': [0.45, 0.50, 0.55, 0.60, 0.65],
                    'trailing_stop_activation': [0.02, 0.025, 0.03, 0.035],
                    'trailing_stop_distance': [0.010, 0.015, 0.020]
                }
            elif 'bollinger' in strategy:
                param_grid = {
                    'profit_target': [0.02, 0.03, 0.04, 0.05, 0.06],
                    'stop_loss': [0.008, 0.010, 0.012, 0.015, 0.018],
                    'confidence_threshold': [0.45, 0.50, 0.55, 0.60, 0.65],
                    'trailing_stop_activation': [0.015, 0.020, 0.025],
                    'trailing_stop_distance': [0.006, 0.008, 0.010]
                }
            else:
                param_grid = {}
            
            # 3. GENERATE PARAMETER COMBINATIONS (Grid Search)
            from itertools import product
            
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())
            
            # Limit combinations to avoid excessive testing
            max_combinations = 50
            all_combinations = list(product(*param_values))
            
            if len(all_combinations) > max_combinations:
                # Sample random combinations
                import random
                combinations = random.sample(all_combinations, max_combinations)
            else:
                combinations = all_combinations
            
            logger.info(f"🔍 Testing {len(combinations)} parameter combinations (grid search)")
            
            # 4. RUN TRAINING PHASE
            results = []
            best_train_return = -float('inf')
            best_params = {}
            
            for i, combo in enumerate(combinations):
                params = dict(zip(param_names, combo))
                
                logger.info(f"📊 Training {i+1}/{len(combinations)}: {params}")
                
                # Train on training data
                train_result = await self.run_backtest(symbol, strategy, start_date, train_end, 10000, params)
                train_return = train_result.get('total_return', 0)
                train_trades = train_result.get('total_trades', 0)
                
                # Filter out configurations with too few trades
                if train_trades < 5:
                    logger.info(f"   ❌ Skipping: Only {train_trades} trades")
                    continue
                
                logger.info(f"   Train result: {train_return:.2%} return ({train_trades} trades)")
                
                results.append({
                    'params': params,
                    'train_return': train_return,
                    'train_trades': train_trades
                })
                
                if train_return > best_train_return:
                    best_train_return = train_return
                    best_params = params
            
            # 5. SELECT TOP CANDIDATES FOR VALIDATION
            results.sort(key=lambda x: x['train_return'], reverse=True)
            top_candidates = results[:10]  # Top 10 performers
            
            logger.info(f"🎯 Top {len(top_candidates)} candidates selected for validation")
            
            # 6. VALIDATION PHASE
            best_val_return = -float('inf')
            best_validated_params = {}
            validation_results = []
            
            for candidate in top_candidates:
                params = candidate['params']
                
                logger.info(f"📊 Validating: {params}")
                
                # Test on validation data
                val_result = await self.run_backtest(symbol, strategy, validation_start, end_date, 10000, params)
                val_return = val_result.get('total_return', 0)
                val_trades = val_result.get('total_trades', 0)
                
                logger.info(f"   Validation result: {val_return:.2%} return ({val_trades} trades)")
                
                validation_results.append({
                    'params': params,
                    'train_return': candidate['train_return'],
                    'val_return': val_return,
                    'combined_score': (candidate['train_return'] + val_return) / 2
                })
                
                if val_return > best_val_return:
                    best_val_return = val_return
                    best_validated_params = params
            
            # 7. SELECT FINAL PARAMETERS BASED ON COMBINED SCORE
            validation_results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            if validation_results:
                final_params = validation_results[0]['params']
                final_score = validation_results[0]['combined_score']
                
                logger.info(f"🎯 FINAL OPTIMAL PARAMETERS: {final_params}")
                logger.info(f"🎯 Combined score: {final_score:.2%}")
            else:
                final_params = {}
                final_score = 0
            
# Parameter optimization complete - results will be logged in final step
            
            # 8. FINAL FULL-PERIOD TEST
            if final_params:
                full_result = await self.run_backtest(symbol, strategy, start_date, end_date, 10000, final_params)
                full_return = full_result.get('total_return', 0)
            else:
                full_return = 0
            
            logger.info(f"✅ ADVANCED OPTIMIZATION COMPLETE:")
            logger.info(f"   🎯 Final parameters: {final_params}")
            logger.info(f"   📊 Full-period return: {full_return:.2%}")
            logger.info(f"   📊 Combined score: {final_score:.2%}")
            
            return {
                'symbol': symbol,
                'strategy': strategy,
                'optimal_params': final_params,
                'full_period_return': full_return,
                'combined_score': final_score,
                'validation_results': validation_results[:5] if validation_results else [],
                'total_combinations_tested': len(combinations) if 'combinations' in locals() else 0
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