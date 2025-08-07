#!/usr/bin/env python3
"""
Enhanced Backtest Runner
Comprehensive backtesting with parameter optimization and realistic trading costs
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
from pathlib import Path


class BacktestRunner:
    """Enhanced backtesting system with parameter optimization"""
    
    def __init__(self, config: Dict[str, Any], exchange_manager, strategy_engine, 
                 risk_manager, ai_signal_filter=None):
        self.config = config
        self.exchange_manager = exchange_manager
        self.strategy_engine = strategy_engine
        self.risk_manager = risk_manager
        self.ai_signal_filter = ai_signal_filter
        
        # Backtest configuration
        self.backtest_config = config.get('backtesting', {})
        self.initial_capital = self.backtest_config.get('initial_capital', 10000)
        self.trading_fee = self.backtest_config.get('trading_fee', 0.001)
        self.slippage = self.backtest_config.get('slippage', 0.0005)
        
        # Results storage
        self.results = {}
        self.optimization_results = {}
        
        logger.info("📊 Enhanced Backtest Runner initialized")
    
    async def run_comprehensive_backtest(self, symbols: List[str] = None, 
                                       strategies: List[str] = None,
                                       timeframes: List[str] = None,
                                       optimization_enabled: bool = True) -> Dict[str, Any]:
        """Run comprehensive backtest with parameter optimization"""
        try:
            logger.info("🚀 Comprehensive backtest başlatılıyor...")
            
            # Default parameters
            symbols = symbols or ['BTC/USDT', 'ETH/USDT']
            strategies = strategies or ['alligator_ma_momentum', 'bollinger_rsi_stochrsi']
            timeframes = timeframes or ['1h', '4h']
            
            results = {
                'summary': {
                    'total_tests': 0,
                    'successful_tests': 0,
                    'failed_tests': 0,
                    'best_strategy': None,
                    'best_symbol': None,
                    'best_timeframe': None,
                    'best_return': -np.inf
                },
                'detailed_results': {},
                'optimization_results': {},
                'parameter_analysis': {}
            }
            
            # Run backtests for each combination
            for symbol in symbols:
                for strategy in strategies:
                    for timeframe in timeframes:
                        try:
                            logger.info(f"📊 Testing {strategy} on {symbol} ({timeframe})")
                            
                            # Get historical data
                            historical_data = await self._get_historical_data(symbol, timeframe)
                            if historical_data is None or len(historical_data) < 1000:
                                logger.warning(f"⚠️ Insufficient data for {symbol} {timeframe}")
                                continue
                            
                            # Run basic backtest
                            basic_result = await self.run_single_backtest(
                                symbol=symbol,
                                strategy=strategy,
                                historical_data=historical_data,
                                timeframe=timeframe
                            )
                            
                            if basic_result:
                                results['summary']['total_tests'] += 1
                                results['summary']['successful_tests'] += 1
                                
                                # Store detailed result
                                key = f"{symbol}_{strategy}_{timeframe}"
                                results['detailed_results'][key] = basic_result
                                
                                # Track best performance
                                total_return = basic_result.get('total_return', 0)
                                if total_return > results['summary']['best_return']:
                                    results['summary']['best_return'] = total_return
                                    results['summary']['best_strategy'] = strategy
                                    results['summary']['best_symbol'] = symbol
                                    results['summary']['best_timeframe'] = timeframe
                            
                            # Run parameter optimization if enabled
                            if optimization_enabled:
                                optimization_result = await self._run_parameter_optimization(
                                    symbol, strategy, historical_data, timeframe
                                )
                                
                                if optimization_result:
                                    opt_key = f"{symbol}_{strategy}_{timeframe}_optimized"
                                    results['optimization_results'][opt_key] = optimization_result
                            
                        except Exception as e:
                            logger.error(f"❌ Backtest error for {symbol} {strategy} {timeframe}: {e}")
                            results['summary']['failed_tests'] += 1
                            continue
            
            # Generate comprehensive analysis
            results['parameter_analysis'] = await self._analyze_parameters(results)
            
            # Save results
            await self._save_backtest_results(results)
            
            logger.success(f"✅ Comprehensive backtest tamamlandı: {results['summary']['successful_tests']}/{results['summary']['total_tests']} başarılı")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Comprehensive backtest error: {e}")
            return {'error': str(e)}
    
    async def run_single_backtest(self, symbol: str, strategy: str, 
                                historical_data: pd.DataFrame, timeframe: str = '1h',
                                custom_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run single backtest for specific strategy and symbol"""
        try:
            logger.info(f"📊 Running backtest: {strategy} on {symbol}")
            
            # Prepare data
            if len(historical_data) < 100:
                logger.warning(f"⚠️ Insufficient data for {symbol}")
                return None
            
            # Add indicators
            data_with_indicators = await self.strategy_engine._add_indicators(historical_data.copy())
            
            # Initialize backtest variables
            capital = self.initial_capital
            position = None
            trades = []
            equity_curve = []
            
            # Strategy parameters
            strategy_params = self.strategy_engine.adaptive_params[strategy].copy()
            if custom_params:
                strategy_params.update(custom_params)
            
            # Run backtest
            for i in range(len(data_with_indicators)):
                current_data = data_with_indicators.iloc[:i+1]
                current_price = current_data['close'].iloc[-1]
                current_time = current_data.index[-1]
                
                # Update equity curve
                equity_curve.append({
                    'timestamp': current_time,
                    'equity': capital,
                    'price': current_price
                })
                
                # Check for exit signals if position exists
                if position:
                    exit_signal = await self._check_exit_signal(
                        position, current_data, strategy_params
                    )
                    
                    if exit_signal['should_exit']:
                        # Close position
                        exit_price = current_price * (1 + self.slippage) if position['side'] == 'BUY' else current_price * (1 - self.slippage)
                        
                        # Calculate PnL
                        if position['side'] == 'BUY':
                            pnl = (exit_price - position['entry_price']) * position['size']
                        else:
                            pnl = (position['entry_price'] - exit_price) * position['size']
                        
                        # Apply trading fees
                        exit_fee = exit_price * position['size'] * self.trading_fee
                        pnl -= exit_fee
                        
                        # Update capital
                        capital += pnl
                        
                        # Record trade
                        trade = {
                            'entry_time': position['entry_time'],
                            'exit_time': current_time,
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'size': position['size'],
                            'side': position['side'],
                            'pnl': pnl,
                            'return_pct': pnl / (position['entry_price'] * position['size']),
                            'duration': (current_time - position['entry_time']).total_seconds() / 3600,  # hours
                            'exit_reason': exit_signal['reason']
                        }
                        trades.append(trade)
                        
                        position = None
                
                # Check for entry signals if no position
                if not position:
                    entry_signal = await self._check_entry_signal(
                        current_data, strategy, strategy_params
                    )
                    
                    if entry_signal['should_enter']:
                        # Calculate position size
                        risk_amount = capital * strategy_params.get('risk_per_trade', 0.02)
                        stop_loss = entry_signal['stop_loss']
                        position_size = risk_amount / abs(current_price - stop_loss)
                        
                        # Apply trading fees
                        entry_fee = current_price * position_size * self.trading_fee
                        position_size = (risk_amount - entry_fee) / abs(current_price - stop_loss)
                        
                        # Open position
                        position = {
                            'entry_time': current_time,
                            'entry_price': current_price,
                            'size': position_size,
                            'side': entry_signal['side'],
                            'stop_loss': stop_loss,
                            'take_profit': entry_signal['take_profit']
                        }
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(trades, equity_curve)
            
            return {
                'symbol': symbol,
                'strategy': strategy,
                'timeframe': timeframe,
                'initial_capital': self.initial_capital,
                'final_capital': capital,
                'total_return': (capital - self.initial_capital) / self.initial_capital,
                'trades': trades,
                'equity_curve': equity_curve,
                'performance_metrics': performance_metrics,
                'custom_params': custom_params
            }
            
        except Exception as e:
            logger.error(f"❌ Single backtest error: {e}")
            return None
    
    async def _check_entry_signal(self, data: pd.DataFrame, strategy: str, 
                                params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for entry signal based on strategy"""
        try:
            if strategy == 'alligator_ma_momentum':
                return await self._check_alligator_entry(data, params)
            elif strategy == 'bollinger_rsi_stochrsi':
                return await self._check_bollinger_entry(data, params)
            else:
                return {'should_enter': False, 'reason': 'Unknown strategy'}
                
        except Exception as e:
            logger.error(f"❌ Entry signal check error: {e}")
            return {'should_enter': False, 'reason': f'Error: {str(e)}'}
    
    async def _check_exit_signal(self, position: Dict[str, Any], data: pd.DataFrame, 
                               params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for exit signal"""
        try:
            current_price = data['close'].iloc[-1]
            
            # Check stop loss
            if position['side'] == 'BUY' and current_price <= position['stop_loss']:
                return {'should_exit': True, 'reason': 'Stop loss'}
            elif position['side'] == 'SELL' and current_price >= position['stop_loss']:
                return {'should_exit': True, 'reason': 'Stop loss'}
            
            # Check take profit
            if position['side'] == 'BUY' and current_price >= position['take_profit']:
                return {'should_exit': True, 'reason': 'Take profit'}
            elif position['side'] == 'SELL' and current_price <= position['take_profit']:
                return {'should_exit': True, 'reason': 'Take profit'}
            
            return {'should_exit': False, 'reason': 'Hold'}
            
        except Exception as e:
            logger.error(f"❌ Exit signal check error: {e}")
            return {'should_exit': False, 'reason': f'Error: {str(e)}'}
    
    async def _check_alligator_entry(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check Williams Alligator entry conditions"""
        try:
            if len(data) < 50:
                return {'should_enter': False, 'reason': 'Insufficient data'}
            
            # Get Alligator lines
            jaw = data['alligator_jaw'].iloc[-1]
            teeth = data['alligator_teeth'].iloc[-1]
            lips = data['alligator_lips'].iloc[-1]
            current_price = data['close'].iloc[-1]
            
            # Check Alligator alignment
            if jaw < teeth < lips < current_price:  # Bullish alignment
                return {
                    'should_enter': True,
                    'side': 'BUY',
                    'stop_loss': current_price * (1 - params.get('stop_loss', 0.025)),
                    'take_profit': current_price * (1 + params.get('profit_target', 0.08)),
                    'reason': 'Alligator bullish alignment'
                }
            elif current_price < lips < teeth < jaw:  # Bearish alignment
                return {
                    'should_enter': True,
                    'side': 'SELL',
                    'stop_loss': current_price * (1 + params.get('stop_loss', 0.025)),
                    'take_profit': current_price * (1 - params.get('profit_target', 0.08)),
                    'reason': 'Alligator bearish alignment'
                }
            
            return {'should_enter': False, 'reason': 'No Alligator signal'}
            
        except Exception as e:
            logger.error(f"❌ Alligator entry check error: {e}")
            return {'should_enter': False, 'reason': f'Error: {str(e)}'}
    
    async def _check_bollinger_entry(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check Bollinger Bands + RSI + Stochastic RSI entry conditions"""
        try:
            if len(data) < 30:
                return {'should_enter': False, 'reason': 'Insufficient data'}
            
            current_price = data['close'].iloc[-1]
            bb_upper = data['bb_upper'].iloc[-1]
            bb_lower = data['bb_lower'].iloc[-1]
            rsi = data['rsi'].iloc[-1]
            stoch_rsi = data['stoch_rsi'].iloc[-1]
            
            # Oversold condition (BUY)
            if (current_price <= bb_lower and 
                rsi < params.get('rsi_oversold', 30) and 
                stoch_rsi < params.get('stochrsi_oversold', 20)):
                return {
                    'should_enter': True,
                    'side': 'BUY',
                    'stop_loss': current_price * (1 - params.get('stop_loss', 0.012)),
                    'take_profit': current_price * (1 + params.get('profit_target', 0.04)),
                    'reason': 'Bollinger oversold'
                }
            
            # Overbought condition (SELL)
            elif (current_price >= bb_upper and 
                  rsi > params.get('rsi_overbought', 70) and 
                  stoch_rsi > params.get('stochrsi_overbought', 80)):
                return {
                    'should_enter': True,
                    'side': 'SELL',
                    'stop_loss': current_price * (1 + params.get('stop_loss', 0.012)),
                    'take_profit': current_price * (1 - params.get('profit_target', 0.04)),
                    'reason': 'Bollinger overbought'
                }
            
            return {'should_enter': False, 'reason': 'No Bollinger signal'}
            
        except Exception as e:
            logger.error(f"❌ Bollinger entry check error: {e}")
            return {'should_enter': False, 'reason': f'Error: {str(e)}'}
    
    def _calculate_performance_metrics(self, trades: List[Dict], equity_curve: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        try:
            if not trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'profit_factor': 0,
                    'calmar_ratio': 0
                }
            
            # Basic metrics
            total_trades = len(trades)
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] < 0]
            
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            
            # Return metrics
            total_pnl = sum(t['pnl'] for t in trades)
            total_return = total_pnl / self.initial_capital
            
            # Risk metrics
            if equity_curve:
                equity_values = [e['equity'] for e in equity_curve]
                returns = np.diff(equity_values) / equity_values[:-1]
                
                # Sharpe ratio
                if len(returns) > 1:
                    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
                else:
                    sharpe_ratio = 0
                
                # Maximum drawdown
                peak = equity_values[0]
                max_drawdown = 0
                for equity in equity_values:
                    if equity > peak:
                        peak = equity
                    drawdown = (peak - equity) / peak
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                sharpe_ratio = 0
                max_drawdown = 0
            
            # Profit factor
            gross_profit = sum(t['pnl'] for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calmar ratio
            calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_return': total_return,
                'total_pnl': total_pnl,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'profit_factor': profit_factor,
                'calmar_ratio': calmar_ratio,
                'avg_trade_duration': np.mean([t['duration'] for t in trades]) if trades else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Performance metrics calculation error: {e}")
            return {}
    
    async def _get_historical_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get historical data for backtesting"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # 3 months of data
            
            # Get data from exchange
            data = await self.exchange_manager.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if data is None or len(data) < 100:
                logger.warning(f"⚠️ Insufficient historical data for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Historical data retrieval error: {e}")
            return None
    
    async def _run_parameter_optimization(self, symbol: str, strategy: str, 
                                        historical_data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Run parameter optimization for specific strategy"""
        try:
            logger.info(f"🔧 Parameter optimization for {strategy} on {symbol}")
            
            # Get optimization ranges from strategy engine
            optimization_ranges = self.strategy_engine.adaptive_params[strategy].get('optimization_ranges', {})
            
            if not optimization_ranges:
                logger.warning(f"⚠️ No optimization ranges for {strategy}")
                return None
            
            # Generate parameter combinations
            param_combinations = self._generate_optimization_combinations(optimization_ranges)
            
            best_params = None
            best_score = -np.inf
            best_result = None
            
            # Test each parameter combination
            for i, params in enumerate(param_combinations):
                try:
                    # Run backtest with custom parameters
                    result = await self.run_single_backtest(
                        symbol=symbol,
                        strategy=strategy,
                        historical_data=historical_data,
                        timeframe=timeframe,
                        custom_params=params
                    )
                    
                    if result:
                        # Calculate optimization score
                        score = self._calculate_optimization_score(result)
                        
                        if score > best_score:
                            best_score = score
                            best_params = params
                            best_result = result
                    
                    # Log progress
                    if (i + 1) % 10 == 0:
                        logger.info(f"📊 Optimization progress: {i + 1}/{len(param_combinations)}")
                        
                except Exception as e:
                    logger.error(f"❌ Parameter test error: {e}")
                    continue
            
            if best_params and best_result:
                return {
                    'best_params': best_params,
                    'best_score': best_score,
                    'best_result': best_result,
                    'total_combinations_tested': len(param_combinations),
                    'optimization_time': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Parameter optimization error: {e}")
            return None
    
    def _generate_optimization_combinations(self, optimization_ranges: Dict[str, List]) -> List[Dict[str, Any]]:
        """Generate parameter combinations for optimization"""
        import itertools
        
        param_names = list(optimization_ranges.keys())
        param_values = list(optimization_ranges.values())
        
        combinations = []
        for values in itertools.product(*param_values):
            combination = dict(zip(param_names, values))
            combinations.append(combination)
        
        # Limit combinations for performance
        max_combinations = 50
        return combinations[:max_combinations]
    
    def _calculate_optimization_score(self, result: Dict[str, Any]) -> float:
        """Enhanced optimization score calculation with comprehensive metrics"""
        try:
            # Extract performance metrics
            total_return = result.get('total_return', 0)
            sharpe_ratio = result.get('performance_metrics', {}).get('sharpe_ratio', 0)
            max_drawdown = abs(result.get('performance_metrics', {}).get('max_drawdown', 0))
            win_rate = result.get('performance_metrics', {}).get('win_rate', 0)
            profit_factor = result.get('performance_metrics', {}).get('profit_factor', 1.0)
            calmar_ratio = result.get('performance_metrics', {}).get('calmar_ratio', 0)
            total_trades = result.get('performance_metrics', {}).get('total_trades', 0)
            avg_trade_duration = result.get('performance_metrics', {}).get('avg_trade_duration', 24)
            
            # Market condition analysis
            market_volatility = self._analyze_market_conditions(result)
            
            # Dynamic weight adjustment based on market conditions
            if market_volatility > 0.8:  # High volatility market
                weights = {
                    'total_return': 0.2,
                    'sharpe_ratio': 0.3,
                    'win_rate': 0.15,
                    'profit_factor': 0.2,
                    'calmar_ratio': 0.1,
                    'max_drawdown': 0.05
                }
            elif market_volatility < 0.3:  # Low volatility market
                weights = {
                    'total_return': 0.3,
                    'sharpe_ratio': 0.2,
                    'win_rate': 0.25,
                    'profit_factor': 0.15,
                    'calmar_ratio': 0.05,
                    'max_drawdown': 0.05
                }
            else:  # Normal volatility
                weights = {
                    'total_return': 0.25,
                    'sharpe_ratio': 0.25,
                    'win_rate': 0.2,
                    'profit_factor': 0.15,
                    'calmar_ratio': 0.1,
                    'max_drawdown': 0.05
                }
            
            # Calculate base score
            base_score = (
                total_return * weights['total_return'] +
                sharpe_ratio * weights['sharpe_ratio'] +
                win_rate * weights['win_rate'] +
                profit_factor * weights['profit_factor'] +
                calmar_ratio * weights['calmar_ratio'] -
                max_drawdown * weights['max_drawdown']
            )
            
            # Apply additional adjustments
            adjusted_score = base_score
            
            # Penalty for insufficient trades
            if total_trades < 10:
                adjusted_score *= 0.7  # Heavy penalty for too few trades
            elif total_trades < 30:
                adjusted_score *= 0.9  # Light penalty for moderate trades
            
            # Penalty for negative returns
            if total_return < 0:
                adjusted_score *= 0.5  # Heavy penalty for negative returns
            
            # Penalty for high drawdown
            if max_drawdown > 0.2:  # 20% drawdown
                adjusted_score *= 0.7  # Penalty for high drawdown
            elif max_drawdown > 0.1:  # 10% drawdown
                adjusted_score *= 0.9  # Light penalty for moderate drawdown
            
            # Penalty for low win rate
            if win_rate < 0.4:  # Less than 40% win rate
                adjusted_score *= 0.8  # Penalty for low win rate
            elif win_rate < 0.5:  # Less than 50% win rate
                adjusted_score *= 0.9  # Light penalty for moderate win rate
            
            # Bonus for excellent performance
            if total_return > 0.5 and sharpe_ratio > 2.0 and win_rate > 0.6:
                adjusted_score *= 1.1  # Bonus for excellent performance
            
            # Bonus for consistent performance
            if profit_factor > 2.0 and calmar_ratio > 1.0:
                adjusted_score *= 1.05  # Bonus for consistent performance
            
            return adjusted_score
            
        except Exception as e:
            logger.error(f"❌ Optimization score calculation error: {e}")
            return -np.inf
    
    def _analyze_market_conditions(self, result: Dict[str, Any]) -> float:
        """Analyze market conditions from backtest results"""
        try:
            # Extract volatility indicators from the result
            trades = result.get('trades', [])
            if not trades:
                return 0.5  # Default volatility
            
            # Calculate price volatility from trades
            prices = [t.get('entry_price', 0) for t in trades if t.get('entry_price', 0) > 0]
            if len(prices) < 2:
                return 0.5
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(prices)):
                change = abs(prices[i] - prices[i-1]) / prices[i-1]
                price_changes.append(change)
            
            # Calculate volatility as standard deviation of price changes
            if price_changes:
                volatility = np.std(price_changes)
                return min(volatility * 100, 1.0)  # Scale and cap at 1.0
            
            return 0.5
            
        except Exception as e:
            logger.error(f"❌ Market condition analysis error: {e}")
            return 0.5
    
    async def _analyze_parameters(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze parameter performance across all tests"""
        try:
            analysis = {
                'parameter_importance': {},
                'best_parameter_ranges': {},
                'correlation_analysis': {},
                'strategy_comparison': {}
            }
            
            # Analyze parameter importance
            for key, result in results['detailed_results'].items():
                if 'custom_params' in result:
                    params = result['custom_params']
                    performance = result.get('total_return', 0)
                    
                    for param_name, param_value in params.items():
                        if param_name not in analysis['parameter_importance']:
                            analysis['parameter_importance'][param_name] = []
                        
                        analysis['parameter_importance'][param_name].append({
                            'value': param_value,
                            'performance': performance
                        })
            
            # Calculate parameter importance scores
            for param_name, performances in analysis['parameter_importance'].items():
                if len(performances) > 1:
                    # Calculate correlation between parameter values and performance
                    values = [p['value'] for p in performances]
                    perfs = [p['performance'] for p in performances]
                    
                    correlation = np.corrcoef(values, perfs)[0, 1] if len(values) > 1 else 0
                    analysis['correlation_analysis'][param_name] = correlation
            
            # Find best parameter ranges
            for param_name, performances in analysis['parameter_importance'].items():
                if len(performances) > 1:
                    # Sort by performance
                    sorted_perfs = sorted(performances, key=lambda x: x['performance'], reverse=True)
                    top_values = [p['value'] for p in sorted_perfs[:5]]
                    
                    analysis['best_parameter_ranges'][param_name] = {
                        'top_values': top_values,
                        'avg_top_performance': np.mean([p['performance'] for p in sorted_perfs[:5]]),
                        'correlation': analysis['correlation_analysis'].get(param_name, 0)
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Parameter analysis error: {e}")
            return {}
    
    async def _save_backtest_results(self, results: Dict[str, Any]):
        """Save backtest results to file"""
        try:
            # Create results directory
            results_dir = Path('results/backtests')
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Save detailed results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = results_dir / f"comprehensive_backtest_{timestamp}.json"
            
            # Convert numpy types to native Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {key: convert_numpy_types(value) for key, value in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                return obj
            
            serializable_results = convert_numpy_types(results)
            
            import json
            with open(results_file, 'w') as f:
                json.dump(serializable_results, f, indent=2, default=str)
            
            logger.info(f"💾 Backtest results saved to {results_file}")
            
        except Exception as e:
            logger.error(f"❌ Save backtest results error: {e}")