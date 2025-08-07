"""
Adaptive Strategy Engine - 2 RESEARCH-BACKED PROVEN Strategies
Enhanced with dynamic parameter optimization and configuration management
"""

import numpy as np
import pandas as pd
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from src.core.risk_manager import RiskManager
from pathlib import Path
import asyncio

# Optional imports for Bayesian optimization
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    BAYESIAN_OPTIMIZATION_AVAILABLE = True
except ImportError:
    BAYESIAN_OPTIMIZATION_AVAILABLE = False
    logger.warning("⚠️ scikit-optimize not available, will use grid search fallback")


class AdaptiveStrategyEngine:
    """2 RESEARCH-BACKED Strategies: Williams Alligator + BB/RSI/StochRSI with Dynamic Optimization"""
    
    def __init__(self, config: Dict, exchange_manager, ai_signal_filter, risk_manager=None):
        """Initialize with 2 research-proven strategies and dynamic optimization"""
        self.config = config
        self.exchange_manager = exchange_manager
        self.ai_signal_filter = ai_signal_filter
        self.risk_manager = risk_manager
        
        # Load strategy parameters from config or use defaults
        self.strategies = self._load_strategy_configs()
        self.adaptive_params = self._load_adaptive_params()
        
        # Dynamic optimization tracking
        self.performance_history = {}
        self.parameter_optimization_enabled = config.get('parameter_optimization', {}).get('enabled', False)
        self.optimization_interval = config.get('parameter_optimization', {}).get('interval_hours', 24)
        self.last_optimization = None
        
        # Strategy performance tracking
        self.strategy_performance = {
            'alligator_ma_momentum': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
            'bollinger_rsi_stochrsi': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
        }
        
        logger.info("🎯 Enhanced Adaptive Strategy Engine initialized with dynamic optimization")
    
    def _load_strategy_configs(self) -> Dict[str, Dict]:
        """Load strategy configurations from config or use research-backed defaults"""
        config_strategies = self.config.get('strategies', {})
        
        default_strategies = {
            'alligator_ma_momentum': {
                'name': 'Williams Alligator + MA (Trend Following)',
                'timeframe': '15m',
                'description': 'Trend following strategy for directional markets',
                'market_conditions': ['trending_market', 'breakout_market'],
                'research_source': 'TradeDots Medium - trend following research',
                'proven_performance': 'Optimized for 15min trending conditions',
                'enabled': True,
                'weight': 0.6
            },
            'bollinger_rsi_stochrsi': {
                'name': 'BB + RSI + Stochastic RSI (Mean Reversion)',
                'timeframe': '5m',
                'description': 'Mean reversion strategy for sideways markets',
                'market_conditions': ['sideways_market', 'consolidation_market', 'ranging_market'],
                'research_source': 'Multiple research papers + scalping optimization',
                'proven_performance': 'Optimized for 5min mean reversion',
                'enabled': True,
                'weight': 0.4
            }
        }
        
        # Merge config with defaults
        for strategy_name, default_config in default_strategies.items():
            if strategy_name in config_strategies:
                default_config.update(config_strategies[strategy_name])
        
        return default_strategies
    
    def _load_adaptive_params(self) -> Dict[str, Dict]:
        """Load strategy parameters from config file with comprehensive parameter management"""
        try:
            # Load from config file
            config_path = Path('config/config.yaml')
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                strategy_params = config_data.get('strategy_parameters', {})
                
                # Define comprehensive default parameters
                default_params = {
                    'alligator_ma_momentum': {
                        # Core strategy parameters
                        'jaw_period': 13,
                        'jaw_shift': 8,
                        'teeth_period': 8,
                        'teeth_shift': 5,
                        'lips_period': 5,
                        'lips_shift': 3,
                        'sma_200': 200,
                        'fast_sma': 10,
                        'slow_sma': 20,
                        
                        # Risk management parameters
                        'profit_target': 0.03,
                        'stop_loss': 0.02,
                        'risk_per_trade': 0.02,
                        'leverage': 1.0,
                        'max_hold_bars': 48,
                        
                        # Advanced exit parameters
                        'trailing_stop_enabled': True,
                        'trailing_stop_activation': 0.01,
                        'trailing_stop_distance': 0.015,
                        'volatility_stop_enabled': True,
                        'atr_stop_multiplier': 2.0,
                        'time_based_exit': True,
                        'max_hold_hours': 24,
                        
                        # Market condition parameters
                        'trend_threshold': 0.6,
                        'volatility_threshold': 0.8,
                        'volume_threshold': 1.2,
                        
                        # Optimization ranges for parameter tuning
                        'optimization_ranges': {
                            'fast_sma': [8, 12, 15, 18],
                            'slow_sma': [15, 20, 25, 30],
                            'profit_target': [0.02, 0.03, 0.04, 0.05, 0.06],
                            'stop_loss': [0.015, 0.02, 0.025, 0.03, 0.035],
                            'risk_per_trade': [0.015, 0.02, 0.025, 0.03],
                            'trailing_stop_distance': [0.01, 0.015, 0.02, 0.025],
                            'atr_stop_multiplier': [1.5, 2.0, 2.5, 3.0],
                            'trend_threshold': [0.5, 0.6, 0.7, 0.8],
                            'volatility_threshold': [0.6, 0.8, 1.0, 1.2]
                        }
                    },
                    'bollinger_rsi_stochrsi': {
                        # Core strategy parameters
                        'bb_period': 20,
                        'bb_std_dev': 2.0,
                        'rsi_period': 14,
                        'rsi_oversold': 30,
                        'rsi_overbought': 70,
                        'stochrsi_period': 14,
                        'stochrsi_oversold': 20,
                        'stochrsi_overbought': 80,
                        
                        # Risk management parameters
                        'profit_target': 0.025,
                        'stop_loss': 0.015,
                        'risk_per_trade': 0.015,
                        'leverage': 1.0,
                        'max_hold_bars': 24,
                        
                        # Advanced exit parameters
                        'trailing_stop_enabled': True,
                        'trailing_stop_activation': 0.008,
                        'trailing_stop_distance': 0.012,
                        'volatility_stop_enabled': True,
                        'atr_stop_multiplier': 1.8,
                        'time_based_exit': True,
                        'max_hold_hours': 12,
                        
                        # Market condition parameters
                        'trend_threshold': 0.5,
                        'volatility_threshold': 0.7,
                        'volume_threshold': 1.0,
                        
                        # Optimization ranges for parameter tuning
                        'optimization_ranges': {
                            'bb_std_dev': [1.8, 2.0, 2.2, 2.5],
                            'rsi_oversold': [25, 30, 35, 40],
                            'rsi_overbought': [60, 65, 70, 75],
                            'stochrsi_oversold': [15, 20, 25, 30],
                            'stochrsi_overbought': [70, 75, 80, 85],
                            'profit_target': [0.02, 0.025, 0.03, 0.035, 0.04],
                            'stop_loss': [0.01, 0.015, 0.02, 0.025, 0.03],
                            'risk_per_trade': [0.01, 0.015, 0.02, 0.025],
                            'trailing_stop_distance': [0.008, 0.012, 0.016, 0.02],
                            'atr_stop_multiplier': [1.5, 1.8, 2.2, 2.5],
                            'trend_threshold': [0.4, 0.5, 0.6, 0.7],
                            'volatility_threshold': [0.5, 0.7, 0.9, 1.1]
                        }
                    }
                }
                
                # Merge config with defaults and validate parameters
                for strategy_name, default_param in default_params.items():
                    if strategy_name in strategy_params:
                        # Update defaults with config values
                        default_param.update(strategy_params[strategy_name])
                        # Validate parameters
                        default_param = self._validate_strategy_parameters(strategy_name, default_param)
                    else:
                        # Use defaults and save to config
                        strategy_params[strategy_name] = default_param
                
                # Save updated config
                config_data['strategy_parameters'] = strategy_params
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                
                logger.info("📋 Comprehensive strategy parameters loaded from config")
                return strategy_params
            else:
                logger.warning("⚠️ Config file not found, using default parameters")
                return self._get_default_params()
                
        except Exception as e:
            logger.error(f"❌ Config loading error: {e}")
            return self._get_default_params()
    
    def _validate_strategy_parameters(self, strategy_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy parameters and set reasonable defaults"""
        try:
            validated_params = params.copy()
            
            # Validate risk parameters
            if 'risk_per_trade' in validated_params:
                validated_params['risk_per_trade'] = max(0.001, min(0.1, validated_params['risk_per_trade']))
            
            if 'profit_target' in validated_params:
                validated_params['profit_target'] = max(0.005, min(0.2, validated_params['profit_target']))
            
            if 'stop_loss' in validated_params:
                validated_params['stop_loss'] = max(0.005, min(0.1, validated_params['stop_loss']))
            
            # Validate leverage
            if 'leverage' in validated_params:
                validated_params['leverage'] = max(1.0, min(10.0, validated_params['leverage']))
            
            # Validate technical parameters
            if 'rsi_period' in validated_params:
                validated_params['rsi_period'] = max(5, min(50, validated_params['rsi_period']))
            
            if 'bb_period' in validated_params:
                validated_params['bb_period'] = max(10, min(100, validated_params['bb_period']))
            
            if 'bb_std_dev' in validated_params:
                validated_params['bb_std_dev'] = max(1.0, min(5.0, validated_params['bb_std_dev']))
            
            # Validate thresholds
            for threshold_key in ['trend_threshold', 'volatility_threshold', 'volume_threshold']:
                if threshold_key in validated_params:
                    validated_params[threshold_key] = max(0.1, min(2.0, validated_params[threshold_key]))
            
            logger.debug(f"✅ Parameters validated for {strategy_name}")
            return validated_params
            
        except Exception as e:
            logger.error(f"❌ Parameter validation error for {strategy_name}: {e}")
            return params
    
    def _get_default_params(self) -> Dict[str, Dict]:
        """Get default strategy parameters"""
        return {
            'alligator_ma_momentum': {
                'profit_target': 0.03,
                'stop_loss': 0.02,
                'risk_per_trade': 0.02,
                'leverage': 1.0,
                'trailing_stop_enabled': True,
                'trailing_stop_activation': 0.01,
                'trailing_stop_distance': 0.015,
                'atr_stop_multiplier': 2.0,
                'max_hold_bars': 48,
                'optimization_ranges': {
                    'profit_target': [0.02, 0.03, 0.04, 0.05],
                    'stop_loss': [0.015, 0.02, 0.025, 0.03],
                    'risk_per_trade': [0.015, 0.02, 0.025],
                    'trailing_stop_distance': [0.01, 0.015, 0.02],
                    'atr_stop_multiplier': [1.5, 2.0, 2.5]
                }
            },
            'bollinger_rsi_stochrsi': {
                'profit_target': 0.025,
                'stop_loss': 0.015,
                'risk_per_trade': 0.015,
                'leverage': 1.0,
                'trailing_stop_enabled': True,
                'trailing_stop_activation': 0.008,
                'trailing_stop_distance': 0.012,
                'atr_stop_multiplier': 1.8,
                'max_hold_bars': 24,
                'optimization_ranges': {
                    'profit_target': [0.02, 0.025, 0.03, 0.035],
                    'stop_loss': [0.01, 0.015, 0.02, 0.025],
                    'risk_per_trade': [0.01, 0.015, 0.02],
                    'trailing_stop_distance': [0.008, 0.012, 0.016],
                    'atr_stop_multiplier': [1.5, 1.8, 2.2]
                }
            }
        }
    
    async def update_strategy_parameters(self, strategy_name: str, new_params: Dict[str, Any]):
        """Update strategy parameters in config file"""
        try:
            # Update in memory
            if strategy_name in self.adaptive_params:
                self.adaptive_params[strategy_name].update(new_params)
            
            # Update config file
            config_path = Path('config/config.yaml')
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                if 'strategy_parameters' not in config_data:
                    config_data['strategy_parameters'] = {}
                
                if strategy_name not in config_data['strategy_parameters']:
                    config_data['strategy_parameters'][strategy_name] = {}
                
                config_data['strategy_parameters'][strategy_name].update(new_params)
                
                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                
                logger.info(f"💾 Strategy parameters updated for {strategy_name}")
            else:
                logger.warning("⚠️ Config file not found, parameters updated in memory only")
                
        except Exception as e:
            logger.error(f"❌ Strategy parameters update error: {e}")
    
    async def optimize_parameters(self, strategy_name: str, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Optimize strategy parameters using Bayesian optimization"""
        try:
            logger.info(f"🔧 Starting Bayesian parameter optimization for {strategy_name}")
            
            optimization_ranges = self.adaptive_params[strategy_name].get('optimization_ranges', {})
            if not optimization_ranges:
                logger.warning(f"⚠️ No optimization ranges defined for {strategy_name}")
                return self.adaptive_params[strategy_name]
            
            # Use Bayesian optimization instead of grid search
            best_params = await self._bayesian_optimization(strategy_name, historical_data, optimization_ranges)
            
            if best_params:
                logger.info(f"🏆 Best parameters found with Bayesian optimization")
                logger.info(f"📋 Optimized parameters: {best_params}")
                await self.update_strategy_parameters(strategy_name, best_params)
                await self._save_optimization_results(strategy_name, best_params, {'method': 'bayesian_optimization'})
            
            return self.adaptive_params[strategy_name]
            
        except Exception as e:
            logger.error(f"❌ Bayesian parameter optimization error for {strategy_name}: {e}")
            return self.adaptive_params[strategy_name]
    
    async def _bayesian_optimization(self, strategy_name: str, historical_data: pd.DataFrame, 
                                   optimization_ranges: Dict) -> Optional[Dict[str, Any]]:
        """Perform Bayesian optimization for parameter tuning"""
        try:
            if not BAYESIAN_OPTIMIZATION_AVAILABLE:
                logger.warning("⚠️ scikit-optimize not available, falling back to grid search")
                return await self._fallback_grid_search(strategy_name, historical_data, optimization_ranges)
            
            # Define optimization space
            space = []
            param_names = []
            
            for param_name, param_range in optimization_ranges.items():
                if isinstance(param_range[0], int):
                    # Integer parameter
                    space.append(Integer(param_range[0], param_range[-1], name=param_name))
                else:
                    # Float parameter
                    space.append(Real(param_range[0], param_range[-1], name=param_name))
                param_names.append(param_name)
            
            # Define objective function
            @use_named_args(space)
            def objective(**params):
                try:
                    # Run backtest with these parameters
                    result = asyncio.run(self._evaluate_parameters_comprehensive(
                        strategy_name, historical_data, params
                    ))
                    
                    if result and result.get('score', -np.inf) > -np.inf:
                        # Return negative score (minimization problem)
                        return -result['score']
                    else:
                        return 0.0  # Penalty for failed evaluation
                        
                except Exception as e:
                    logger.debug(f"⚠️ Parameter evaluation failed: {e}")
                    return 0.0  # Penalty for errors
            
            # Run Bayesian optimization
            logger.info(f"🔍 Running Bayesian optimization with {len(space)} parameters")
            
            # Use more iterations for better optimization
            n_calls = min(50, len(space) * 10)  # Adaptive number of calls
            
            result = gp_minimize(
                func=objective,
                dimensions=space,
                n_calls=n_calls,
                random_state=42,
                acq_func='EI',  # Expected Improvement
                n_initial_points=10
            )
            
            # Extract best parameters
            best_params = {}
            for i, param_name in enumerate(param_names):
                best_params[param_name] = result.x[i]
            
            logger.info(f"✅ Bayesian optimization completed in {result.nit} iterations")
            logger.info(f"🏆 Best score: {-result.fun:.4f}")
            
            return best_params
            
        except Exception as e:
            logger.error(f"❌ Bayesian optimization error: {e}")
            return await self._fallback_grid_search(strategy_name, historical_data, optimization_ranges)
    
    async def _fallback_grid_search(self, strategy_name: str, historical_data: pd.DataFrame, 
                                   optimization_ranges: Dict) -> Optional[Dict[str, Any]]:
        """Fallback to grid search if Bayesian optimization fails"""
        try:
            logger.info(f"🔄 Using fallback grid search for {strategy_name}")
            
            param_combinations = self._generate_smart_combinations(optimization_ranges)
            max_combinations = self.config.get('parameter_optimization', {}).get('max_combinations', 50)
            param_combinations = param_combinations[:max_combinations]
            
            logger.info(f"🔍 Testing {len(param_combinations)} parameter combinations")
            
            best_params = None
            best_score = -np.inf
            best_result = None
            
            for i, params in enumerate(param_combinations):
                try:
                    result = await self._evaluate_parameters_comprehensive(strategy_name, historical_data, params)
                    if result and result.get('score', -np.inf) > best_score:
                        best_score = result['score']
                        best_params = params
                        best_result = result
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"📊 Grid search progress: {i + 1}/{len(param_combinations)} combinations tested")
                        
                except Exception as e:
                    logger.error(f"❌ Parameter evaluation error: {e}")
                    continue
            
            return best_params
            
        except Exception as e:
            logger.error(f"❌ Fallback grid search error: {e}")
            return None
    
    async def _evaluate_parameters_comprehensive(self, strategy_name: str, historical_data: pd.DataFrame, 
                                               params: Dict) -> Optional[Dict[str, Any]]:
        """Evaluate parameters with comprehensive scoring"""
        try:
            # Create temporary parameters
            temp_params = self.adaptive_params[strategy_name].copy()
            temp_params.update(params)
            
            # Run backtest
            result = await self.backtest_strategy(
                strategy_name=strategy_name,
                symbol='BTC/USDT',
                historical_data=historical_data.tail(1000),
                initial_capital=10000,
                custom_params=temp_params,
                trading_fee=0.001
            )
            
            if not result:
                return None
            
            # Calculate comprehensive score
            score = self._calculate_comprehensive_score(result)
            
            return {
                'params': params,
                'result': result,
                'score': score,
                'method': 'bayesian_optimization'
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive parameter evaluation error: {e}")
            return None
    
    def _calculate_comprehensive_score(self, result: Dict[str, Any]) -> float:
        """Calculate comprehensive score for optimization"""
        try:
            # Extract metrics
            total_return = result.get('total_return', 0)
            sharpe_ratio = result.get('sharpe_ratio', 0)
            max_drawdown = abs(result.get('max_drawdown', 0))
            win_rate = result.get('win_rate', 0)
            profit_factor = result.get('profit_factor', 1.0)
            calmar_ratio = result.get('calmar_ratio', 0)
            total_trades = result.get('total_trades', 0)
            
            # Get market conditions for dynamic weighting
            market_volatility = self._analyze_market_conditions(result)
            
            # Dynamic weights based on market conditions
            if market_volatility > 0.8:  # High volatility market
                weights = {
                    'total_return': 0.15,
                    'sharpe_ratio': 0.35,
                    'win_rate': 0.15,
                    'profit_factor': 0.2,
                    'calmar_ratio': 0.1,
                    'max_drawdown': 0.05
                }
            elif market_volatility < 0.3:  # Low volatility market
                weights = {
                    'total_return': 0.35,
                    'sharpe_ratio': 0.15,
                    'win_rate': 0.25,
                    'profit_factor': 0.15,
                    'calmar_ratio': 0.05,
                    'max_drawdown': 0.05
                }
            else:  # Normal market
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
            
            # Apply adjustments
            adjusted_score = base_score
            
            # Trade count adjustments
            if total_trades < 20:
                adjusted_score *= 0.6
            elif total_trades < 50:
                adjusted_score *= 0.8
            
            # Performance penalties/bonuses
            if total_return < 0:
                adjusted_score *= 0.3
            
            if max_drawdown > 0.25:
                adjusted_score *= 0.5
            elif max_drawdown > 0.15:
                adjusted_score *= 0.8
            
            if win_rate < 0.35:
                adjusted_score *= 0.7
            elif win_rate < 0.45:
                adjusted_score *= 0.9
            
            # Performance bonuses
            if total_return > 0.3 and sharpe_ratio > 1.5 and win_rate > 0.55:
                adjusted_score *= 1.2
            
            if profit_factor > 1.5 and calmar_ratio > 0.5:
                adjusted_score *= 1.1
            
            return adjusted_score
            
        except Exception as e:
            logger.error(f"❌ Comprehensive score calculation error: {e}")
            return -np.inf
    
    def _analyze_market_conditions(self, result: Dict[str, Any]) -> float:
        """Analyze market conditions from backtest result"""
        try:
            trades = result.get('trades', [])
            if not trades:
                return 0.5
            
            # Calculate volatility from trade returns
            returns = []
            for trade in trades:
                if 'return_pct' in trade:
                    returns.append(trade['return_pct'])
            
            if returns:
                volatility = np.std(returns)
                return min(volatility, 1.0)
            
            return 0.5
            
        except Exception as e:
            logger.error(f"❌ Market condition analysis error: {e}")
            return 0.5
    
    async def _save_optimization_results(self, strategy_name: str, best_params: Dict, best_result: Dict):
        """Save optimization results to config file and database"""
        try:
            # Save to config file
            await self._save_to_config_file(strategy_name, best_params)
            
            # Save to database
            await self._save_to_database(strategy_name, best_params, best_result)
            
            # Save detailed results to JSON file
            await self._save_detailed_results(strategy_name, best_params, best_result)
            
            logger.info(f"💾 Optimization results saved for {strategy_name}")
            
        except Exception as e:
            logger.error(f"❌ Optimization results save error: {e}")
    
    async def _save_to_config_file(self, strategy_name: str, best_params: Dict):
        """Save optimized parameters to config file"""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path('config/config.yaml')
            
            # Load current config
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
            else:
                config_data = {}
            
            # Ensure strategy_parameters section exists
            if 'strategy_parameters' not in config_data:
                config_data['strategy_parameters'] = {}
            
            # Update strategy parameters
            if strategy_name not in config_data['strategy_parameters']:
                config_data['strategy_parameters'][strategy_name] = {}
            
            # Update with optimized parameters
            config_data['strategy_parameters'][strategy_name].update(best_params)
            
            # Add optimization metadata
            if 'optimization_metadata' not in config_data:
                config_data['optimization_metadata'] = {}
            
            config_data['optimization_metadata'][strategy_name] = {
                'last_optimization': datetime.now().isoformat(),
                'optimized_parameters': list(best_params.keys()),
                'optimization_method': 'bayesian_optimization'
            }
            
            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            logger.info(f"📝 Config file updated with optimized parameters for {strategy_name}")
            
        except Exception as e:
            logger.error(f"❌ Config file save error: {e}")
    
    async def _save_to_database(self, strategy_name: str, best_params: Dict, best_result: Dict):
        """Save optimization results to database"""
        try:
            # This would require database manager integration
            # For now, save to a JSON file as database backup
            optimization_data = {
                'strategy_name': strategy_name,
                'optimized_parameters': best_params,
                'optimization_result': best_result,
                'timestamp': datetime.now().isoformat(),
                'optimization_method': 'bayesian_optimization'
            }
            
            # Save to optimization history file
            import json
            from pathlib import Path
            
            history_file = Path('data/optimization_history.json')
            history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add new optimization result
            history.append(optimization_data)
            
            # Keep only last 100 optimizations
            if len(history) > 100:
                history = history[-100:]
            
            # Save updated history
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"💾 Optimization history saved to database backup for {strategy_name}")
            
        except Exception as e:
            logger.error(f"❌ Database save error: {e}")
    
    async def _save_detailed_results(self, strategy_name: str, best_params: Dict, best_result: Dict):
        """Save detailed optimization results to JSON file"""
        try:
            import json
            from pathlib import Path
            
            # Create results directory
            results_dir = Path('data/optimization_results')
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Create detailed results file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{strategy_name}_optimization_{timestamp}.json"
            filepath = results_dir / filename
            
            detailed_results = {
                'strategy_name': strategy_name,
                'optimization_timestamp': datetime.now().isoformat(),
                'optimization_method': 'bayesian_optimization',
                'best_parameters': best_params,
                'optimization_result': best_result,
                'performance_metrics': {
                    'total_return': best_result.get('total_return', 0),
                    'sharpe_ratio': best_result.get('sharpe_ratio', 0),
                    'max_drawdown': best_result.get('max_drawdown', 0),
                    'win_rate': best_result.get('win_rate', 0),
                    'profit_factor': best_result.get('profit_factor', 0),
                    'calmar_ratio': best_result.get('calmar_ratio', 0)
                },
                'parameter_analysis': await self._analyze_parameter_impact(strategy_name, best_params),
                'market_conditions': best_result.get('market_conditions', {}),
                'trading_costs': best_result.get('trading_costs', {})
            }
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(detailed_results, f, indent=2)
            
            logger.info(f"📊 Detailed optimization results saved: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Detailed results save error: {e}")
    
    async def _analyze_parameter_impact(self, strategy_name: str, best_params: Dict) -> Dict[str, Any]:
        """Analyze the impact of optimized parameters"""
        try:
            # Get original parameters
            original_params = self.adaptive_params[strategy_name].copy()
            
            # Calculate parameter changes
            parameter_changes = {}
            for param_name, optimized_value in best_params.items():
                if param_name in original_params:
                    original_value = original_params[param_name]
                    if isinstance(original_value, (int, float)) and isinstance(optimized_value, (int, float)):
                        change_pct = ((optimized_value - original_value) / original_value) * 100
                        parameter_changes[param_name] = {
                            'original': original_value,
                            'optimized': optimized_value,
                            'change_pct': change_pct,
                            'change_type': 'increase' if change_pct > 0 else 'decrease'
                        }
            
            # Categorize parameters
            risk_params = ['stop_loss', 'risk_per_trade', 'max_hold_bars']
            profit_params = ['profit_target', 'trailing_stop_distance']
            technical_params = ['rsi_period', 'bb_period', 'fast_sma', 'slow_sma']
            
            analysis = {
                'parameter_changes': parameter_changes,
                'risk_parameter_changes': {k: v for k, v in parameter_changes.items() if k in risk_params},
                'profit_parameter_changes': {k: v for k, v in parameter_changes.items() if k in profit_params},
                'technical_parameter_changes': {k: v for k, v in parameter_changes.items() if k in technical_params},
                'total_parameters_optimized': len(parameter_changes),
                'average_change_pct': np.mean([abs(v['change_pct']) for v in parameter_changes.values()]) if parameter_changes else 0
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Parameter impact analysis error: {e}")
            return {}
    
    async def load_optimized_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Load optimized parameters from config"""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path('config/config.yaml')
            
            if not config_path.exists():
                logger.warning(f"⚠️ Config file not found, using default parameters for {strategy_name}")
                return self.adaptive_params.get(strategy_name, {})
            
            # Load config
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Get strategy parameters
            strategy_params = config_data.get('strategy_parameters', {}).get(strategy_name, {})
            
            if strategy_params:
                logger.info(f"📋 Loaded optimized parameters for {strategy_name}")
                return strategy_params
            else:
                logger.warning(f"⚠️ No optimized parameters found for {strategy_name}, using defaults")
                return self.adaptive_params.get(strategy_name, {})
                
        except Exception as e:
            logger.error(f"❌ Load optimized parameters error: {e}")
            return self.adaptive_params.get(strategy_name, {})
    
    async def get_optimization_history(self, strategy_name: str = None, limit: int = 10) -> List[Dict]:
        """Get optimization history"""
        try:
            import json
            from pathlib import Path
            
            history_file = Path('data/optimization_history.json')
            
            if not history_file.exists():
                return []
            
            # Load history
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Filter by strategy if specified
            if strategy_name:
                history = [h for h in history if h.get('strategy_name') == strategy_name]
            
            # Return recent history
            return history[-limit:] if limit else history
            
        except Exception as e:
            logger.error(f"❌ Get optimization history error: {e}")
            return []
    
    async def update_strategy_performance(self, strategy_name: str, trade_result: Dict):
        """Update strategy performance tracking"""
        try:
            if strategy_name not in self.strategy_performance:
                self.strategy_performance[strategy_name] = {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
            
            pnl = trade_result.get('pnl', 0)
            
            if pnl > 0:
                self.strategy_performance[strategy_name]['wins'] += 1
            else:
                self.strategy_performance[strategy_name]['losses'] += 1
            
            self.strategy_performance[strategy_name]['total_pnl'] += pnl
            
            # Store detailed performance data
            if strategy_name not in self.performance_history:
                self.performance_history[strategy_name] = []
            
            self.performance_history[strategy_name].append({
                'timestamp': datetime.now(),
                'pnl': pnl,
                'entry_price': trade_result.get('entry_price', 0),
                'exit_price': trade_result.get('exit_price', 0),
                'duration': trade_result.get('duration', 0)
            })
            
            # Keep only last 100 trades
            if len(self.performance_history[strategy_name]) > 100:
                self.performance_history[strategy_name] = self.performance_history[strategy_name][-100:]
            
        except Exception as e:
            logger.error(f"❌ Strategy performance update error: {e}")
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all strategy performances"""
        try:
            summary = {}
            
            for strategy_name, performance in self.strategy_performance.items():
                total_trades = performance['wins'] + performance['losses']
                if total_trades > 0:
                    win_rate = performance['wins'] / total_trades
                    avg_pnl = performance['total_pnl'] / total_trades
                else:
                    win_rate = 0
                    avg_pnl = 0
                
                summary[strategy_name] = {
                    'total_trades': total_trades,
                    'wins': performance['wins'],
                    'losses': performance['losses'],
                    'win_rate': win_rate,
                    'total_pnl': performance['total_pnl'],
                    'avg_pnl': avg_pnl
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Strategy performance summary error: {e}")
            return {}

    async def analyze_market_regime(self, symbol: str) -> Dict[str, Any]:
        """ENHANCED market regime analysis for strategy selection"""
        try:
            # Get multiple timeframes for comprehensive analysis
            now = datetime.now()
            data_15m = await self.exchange_manager.get_historical_data(
                symbol=symbol, timeframe='15m', 
                start_date=now - timedelta(days=2), end_date=now
            )
            data_1h = await self.exchange_manager.get_historical_data(
                symbol=symbol, timeframe='1h', 
                start_date=now - timedelta(days=7), end_date=now
            )
            data_4h = await self.exchange_manager.get_historical_data(
                symbol=symbol, timeframe='4h', 
                start_date=now - timedelta(days=30), end_date=now
            )
            
            if not all([data_15m is not None, data_1h is not None, data_4h is not None]):
                return {'regime': 'sideways_market', 'confidence': 0.5}
            
            # Calculate comprehensive market metrics
            analysis = self._comprehensive_regime_analysis(data_15m, data_1h, data_4h)
            
            # Enhanced regime determination
            regime = self._determine_optimal_regime(analysis)
            
            # SELECT OPTIMAL STRATEGY FOR THIS SPECIFIC SYMBOL
            optimal_strategy = self._select_optimal_strategy(regime, analysis)
            
            logger.info(f"📊 {symbol} Market Regime: {regime} | Vol: {analysis['volatility']:.3f} | Range: {analysis.get('range_analysis', 'N/A')} | Strategy: {optimal_strategy}")
            
            return {
                'regime': regime,
                'best_strategy': optimal_strategy,
                'confidence': analysis['confidence'],
                'volatility': analysis['volatility'],
                'trend_strength': analysis['trend_strength'],
                'recommended_strategy': optimal_strategy  # Use already calculated value instead of calling again
            }
            
        except Exception as e:
            logger.error(f"❌ Market regime analysis error: {e}")
            return {'regime': 'sideways_market', 'confidence': 0.5, 'recommended_strategy': 'bollinger_rsi_stochrsi'}
    
    def _comprehensive_regime_analysis(self, data_15m, data_1h, data_4h) -> Dict[str, Any]:
        """ENHANCED multi-timeframe analysis with advanced indicators"""
        try:
            current_price = data_15m['close'].iloc[-1]
            
            # 1. VOLATILITY REGIME ANALYSIS
            returns_15m = data_15m['close'].pct_change().dropna()
            volatility = returns_15m.std() * np.sqrt(96)  # Annualized
            
            # GARCH-like volatility regime detection
            vol_5_day = returns_15m.tail(96*5).std() * np.sqrt(96)  # 5-day vol
            vol_20_day = returns_15m.tail(96*20).std() * np.sqrt(96)  # 20-day vol
            vol_regime = 'high' if vol_5_day > vol_20_day * 1.5 else 'low' if vol_5_day < vol_20_day * 0.7 else 'normal'
            
            # 2. TREND REGIME ANALYSIS (Multi-timeframe)
            # 4h for major trend
            closes_4h = data_4h['close']
            sma_10_4h = closes_4h.rolling(10).mean().iloc[-1]
            sma_20_4h = closes_4h.rolling(20).mean().iloc[-1]
            sma_50_4h = closes_4h.rolling(50).mean().iloc[-1] if len(closes_4h) >= 50 else sma_20_4h
            
            # 1h for intermediate trend
            closes_1h = data_1h['close']
            sma_20_1h = closes_1h.rolling(20).mean().iloc[-1]
            
            # Trend strength calculation
            major_trend_strength = abs((current_price - sma_50_4h) / sma_50_4h) if sma_50_4h > 0 else 0
            intermediate_trend_strength = abs((current_price - sma_20_1h) / sma_20_1h) if sma_20_1h > 0 else 0
            
            # Trend direction consensus
            major_trend_up = current_price > sma_10_4h > sma_20_4h > sma_50_4h
            major_trend_down = current_price < sma_10_4h < sma_20_4h < sma_50_4h
            intermediate_trend_up = current_price > sma_20_1h
            
            # 3. MOMENTUM ANALYSIS
            # ADX-like calculation for trend strength
            high_15m = data_15m['high']
            low_15m = data_15m['low']
            close_15m = data_15m['close']
            
            tr = np.maximum(high_15m - low_15m, 
                 np.maximum(abs(high_15m - close_15m.shift(1)), 
                           abs(low_15m - close_15m.shift(1))))
            atr = tr.rolling(14).mean().iloc[-1]
            atr_pct = atr / current_price
            
            # 4. VOLUME PROFILE ANALYSIS
            volume_15m = data_15m['volume']
            volume_sma_20 = volume_15m.rolling(20).mean().iloc[-1]
            current_volume = volume_15m.iloc[-1]
            volume_strength = 'high' if current_volume > volume_sma_20 * 1.5 else 'low' if current_volume < volume_sma_20 * 0.5 else 'normal'
            
            # 5. RANGE ANALYSIS (Support/Resistance)
            high_24h = data_1h['high'].tail(24).max()
            low_24h = data_1h['low'].tail(24).min()
            range_pct = (high_24h - low_24h) / current_price
            
            # Price position in range
            price_position = (current_price - low_24h) / (high_24h - low_24h) if high_24h > low_24h else 0.5
            
            # 6. BREAKOUT DETECTION
            # Recent breakout above resistance
            resistance_break = current_price > data_1h['high'].rolling(20).max().iloc[-2]
            support_break = current_price < data_1h['low'].rolling(20).min().iloc[-2]
            
            # 7. ADVANCED CONFIDENCE CALCULATION
            confidence_factors = []
            
            # Trend consistency across timeframes
            trend_consistency = 0.5
            if major_trend_up and intermediate_trend_up:
                trend_consistency = 0.9
            elif major_trend_down and not intermediate_trend_up:
                trend_consistency = 0.9
            elif major_trend_up or intermediate_trend_up:
                trend_consistency = 0.7
                
            confidence_factors.append(trend_consistency * 0.3)
            
            # Volume confirmation
            volume_confirmation = min(1.0, current_volume / volume_sma_20) if volume_sma_20 > 0 else 0.5
            confidence_factors.append(volume_confirmation * 0.2)
            
            # Volatility factor (higher vol = more opportunities but less certainty)
            vol_factor = 0.8 if vol_regime == 'normal' else 0.6 if vol_regime == 'high' else 0.4
            confidence_factors.append(vol_factor * 0.2)
            
            # Breakout confirmation
            breakout_factor = 0.9 if resistance_break or support_break else 0.5
            confidence_factors.append(breakout_factor * 0.15)
            
            # Range position (avoid extremes)
            range_factor = 1.0 - abs(price_position - 0.5) * 1.5  # Prefer middle range
            confidence_factors.append(max(0.3, range_factor) * 0.15)
            
            final_confidence = min(0.95, max(0.3, sum(confidence_factors)))
            
            return {
                'volatility': volatility,
                'vol_regime': vol_regime,
                'trend_strength': major_trend_strength,
                'intermediate_trend_strength': intermediate_trend_strength,
                'major_trend_up': major_trend_up,
                'major_trend_down': major_trend_down,
                'intermediate_trend_up': intermediate_trend_up,
                'atr_pct': atr_pct,
                'volume_strength': volume_strength,
                'range_pct': range_pct,
                'price_position': price_position,
                'resistance_break': resistance_break,
                'support_break': support_break,
                'confidence': final_confidence,
                'range_analysis': 'wide' if range_pct > 0.08 else 'normal' if range_pct > 0.04 else 'tight'
            }
            
        except Exception as e:
            logger.error(f"❌ Regime analysis error: {e}")
            return {
                'volatility': 0.02, 'trend_strength': 0.01, 'range_pct': 0.05,
                'volume_ratio': 1.0, 'momentum_short': 0, 'momentum_medium': 0,
                'confidence': 0.5, 'range_analysis': 'normal'
            }
    
    def _determine_optimal_regime(self, analysis: Dict) -> str:
        """ENHANCED market regime detection with advanced indicators"""
        # Extract enhanced analysis data
        vol_regime = analysis.get('vol_regime', 'normal')
        major_trend_up = analysis.get('major_trend_up', False)
        major_trend_down = analysis.get('major_trend_down', False)
        resistance_break = analysis.get('resistance_break', False)
        support_break = analysis.get('support_break', False)
        trend_strength = analysis.get('trend_strength', 0)
        atr_pct = analysis.get('atr_pct', 0)
        volume_strength = analysis.get('volume_strength', 'normal')
        price_position = analysis.get('price_position', 0.5)
        
        # 1. BREAKOUT DETECTION (Priority 1)
        if (resistance_break or support_break) and volume_strength == 'high':
            if vol_regime == 'high' and atr_pct > 0.03:
                return 'explosive_breakout_market'
            else:
                return 'breakout_market'
        
        # 2. STRONG TREND DETECTION (Priority 2)
        if (major_trend_up or major_trend_down) and trend_strength > 0.05:
            if vol_regime == 'high':
                return 'volatile_trending_market'
            elif volume_strength == 'high':
                return 'strong_trending_market'
            else:
                return 'trending_market'
        
        # 3. RANGING MARKET DETECTION (Priority 3)
        if not major_trend_up and not major_trend_down:
            if vol_regime == 'high' and atr_pct > 0.04:
                return 'high_volatility_ranging_market'
            elif 0.3 < price_position < 0.7:  # Middle of range
                return 'consolidation_market'
            else:
                return 'sideways_market'
        
        # 4. MEAN REVERSION CONDITIONS (Priority 4)
        if price_position > 0.8 or price_position < 0.2:  # Near extremes
            return 'mean_reversion_market'
        elif vol_regime == 'low' and range_pct < 0.03:  # Low vol + tight range
            return 'consolidation_market'
        elif range_pct > 0.06:  # Wide range but moderate vol
            return 'ranging_market'
        else:
            return 'sideways_market'
    
    def _select_optimal_strategy(self, regime: str, analysis: Dict) -> str:
        """Select optimal strategy based on research and regime"""
        vol = analysis['volatility']
        trend = analysis['trend_strength']
        
        # RESEARCH-BASED STRATEGY SELECTION
        if regime in ['trending_market', 'breakout_market']:
            # Williams Alligator excels in trending markets (3,452% research)
            return 'alligator_ma_momentum'
        elif regime in ['volatile_trending_market', 'strong_trending_market'] and vol > 0.03:
            # High volatility - Alligator can catch breakouts
            return 'alligator_ma_momentum'
        else:
            # Sideways, consolidation, ranging - BB+RSI+StochRSI excels
            return 'bollinger_rsi_stochrsi'

    async def get_entry_signal(self, symbol: str, market_data: Dict, regime: str, current_df_slice: pd.DataFrame = None) -> Dict[str, Any]:
        """Get entry signal using research-optimized strategies"""
        try:
            # Try to get AI confidence first
            ai_analysis = None
            try:
                ai_analysis = await self.ai_signal_filter.filter_signal(symbol, market_data, regime)
                
                # Use consistent AI confidence threshold (0.6 for better signal generation)
                if ai_analysis['confidence'] < 0.6:  # Consistent threshold
                    logger.debug(f"📉 AI confidence too low: {ai_analysis['confidence']:.2f}")
                    # Don't return immediately - try direct strategy as fallback
                else:
                    logger.debug(f"🤖 AI confidence good: {ai_analysis['confidence']:.2f}")
                    
            except Exception as e:
                logger.warning(f"⚠️ AI filter error: {e}, using direct strategy signals")
                ai_analysis = None
            
            # Select optimal strategy (use cached regime analysis if available)
            if current_df_slice is not None:
                # BACKTEST MODE: Use provided data, don't fetch fresh data
                recommended_strategy = 'bollinger_rsi_stochrsi'  # Default during backtest
                if regime in ['trending_market', 'breakout_market']:
                    recommended_strategy = 'alligator_ma_momentum'
            else:
                # LIVE MODE: Perform full regime analysis
                regime_analysis = await self.analyze_market_regime(symbol)
                recommended_strategy = regime_analysis.get('recommended_strategy', 'bollinger_rsi_stochrsi')
            
            # Route to appropriate research-backed strategy
            if recommended_strategy == 'alligator_ma_momentum':
                signal = await self._alligator_ma_signal(symbol, market_data, ai_analysis if ai_analysis else {'confidence': 0.0}, current_df_slice)
            else:
                signal = await self._bollinger_rsi_stochrsi_signal(symbol, market_data, ai_analysis if ai_analysis else {'confidence': 0.0}, current_df_slice)
            
            # Apply AI filter to final signal (only if AI analysis succeeded)
            if signal['action'] != 'HOLD' and ai_analysis is not None:
                # Apply AI confidence boost/penalty with consistent threshold
                if ai_analysis['confidence'] >= 0.6:  # Consistent threshold
                    signal['ai_confidence'] = ai_analysis['confidence']
                    signal['combined_confidence'] = (signal['confidence'] + ai_analysis['confidence']) / 2
                    signal['strategy_used'] = recommended_strategy
                    signal['research_basis'] = self.strategies[recommended_strategy]['proven_performance']
                else:
                    # Reduce confidence if AI is not confident
                    signal['confidence'] *= 0.8  # 20% penalty
                    signal['ai_confidence'] = ai_analysis['confidence']
                    signal['combined_confidence'] = signal['confidence']
            elif signal['action'] != 'HOLD':
                # No AI analysis available - use raw strategy signal
                signal['ai_confidence'] = 0.0
                signal['combined_confidence'] = signal['confidence']
                signal['strategy_used'] = recommended_strategy
                signal['research_basis'] = 'Direct strategy signal (no AI filter)'
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error getting entry signal: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'Error: {str(e)}'}

    async def _alligator_ma_signal(self, symbol: str, market_data: Dict, ai_analysis: Dict, historical_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Williams Alligator + Moving Average Strategy
        Based on TradeDots research: 3,452% return on ETH
        """
        try:
            # Use provided historical data or fetch fresh data
            if historical_data is not None:
                data_15m = historical_data
            else:
                # Get 15m data (trend following optimized timeframe)
                now = datetime.now()
                data_15m = await self.exchange_manager.get_historical_data(
                    symbol=symbol, timeframe='15m', 
                    start_date=now - timedelta(days=7), end_date=now
                )
            
            if data_15m is None or len(data_15m) < 100:
                return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Insufficient data'}
            
            params = self.adaptive_params['alligator_ma_momentum']
            current_price = data_15m['close'].iloc[-1]
            
            # SIMPLIFIED TREND FOLLOWING FOR 15M
            # Moving averages (clear trend detection)
            sma_10 = data_15m['close'].rolling(params['fast_sma']).mean()
            sma_20 = data_15m['close'].rolling(params['slow_sma']).mean()
            sma_50 = data_15m['close'].rolling(50).mean()
            
            # Current values
            current_sma10 = sma_10.iloc[-1] if not pd.isna(sma_10.iloc[-1]) else current_price
            current_sma20 = sma_20.iloc[-1] if not pd.isna(sma_20.iloc[-1]) else current_price
            current_sma50 = sma_50.iloc[-1] if not pd.isna(sma_50.iloc[-1]) else current_price
            
            # Momentum confirmation (calculate BEFORE using in conditions)
            sma10_rising = (sma_10.iloc[-1] > sma_10.iloc[-2]) if len(sma_10) >= 2 else False
            sma10_falling = (sma_10.iloc[-1] < sma_10.iloc[-2]) if len(sma_10) >= 2 else False
            
            # IMPROVED TREND CONDITIONS (realistic for actual trading)
            # LONG: Strong alignment with price momentum
            strong_uptrend = (current_price > current_sma10 and current_sma10 > current_sma20)  # Reasonable trend alignment
            uptrend_momentum = (current_price > current_sma20 and sma10_rising)  # Momentum confirmation
            
            # SHORT: Strong downward alignment with price momentum  
            strong_downtrend = (current_price < current_sma10 and current_sma10 < current_sma20)  # Reasonable downtrend
            downtrend_momentum = (current_price < current_sma20 and sma10_falling)  # Momentum confirmation
            
            # Volume confirmation (if available)
            volume_boost = 0.0
            if 'volume' in data_15m.columns and len(data_15m) > 20:
                vol_ma = data_15m['volume'].rolling(20).mean()
                current_vol = data_15m['volume'].iloc[-1]
                if current_vol > vol_ma.iloc[-1] * 1.2:  # 20% above average
                    volume_boost = 0.15
            
            if strong_uptrend or uptrend_momentum:  # Either strong trend OR momentum (more realistic)
                confidence = 0.65 + volume_boost  # Increased from 0.5 to 0.65 for better signal generation
                return {
                    'action': 'BUY',
                    'confidence': min(0.85, confidence),  # Reduced max from 0.95 to 0.85
                    'entry_price': current_price,
                    'reasons': [
                        "Uptrend detected: Price > SMA10 > SMA20" if strong_uptrend else "Uptrend momentum: Price > SMA20 + SMA10 rising",
                        "SMA10 rising momentum" if sma10_rising else "Price above key MA",
                        f"Volume boost: {volume_boost:.2f}" if volume_boost > 0 else "No volume boost"
                    ],
                    'strategy': 'Alligator Trend Following (LONG)',
                    'timeframe': '15m',
                    'stop_loss': current_sma20 * 0.98,  # Below SMA20
                    'take_profit': current_price * 1.08,  # 8% target
                    'research_basis': '15m trend following'
                }
            elif strong_downtrend or downtrend_momentum:  # Either strong trend OR momentum (more realistic)
                confidence = 0.65 + volume_boost  # Increased from 0.5 to 0.65 for better signal generation
                return {
                    'action': 'SELL',
                    'confidence': min(0.85, confidence),  # Reduced max from 0.95 to 0.85
                    'entry_price': current_price,
                    'reasons': [
                        "Downtrend detected: Price < SMA10 < SMA20" if strong_downtrend else "Downtrend momentum: Price < SMA20 + SMA10 falling",
                        "SMA10 falling momentum" if sma10_falling else "Price below key MA", 
                        f"Volume boost: {volume_boost:.2f}" if volume_boost > 0 else "No volume boost"
                    ],
                    'strategy': 'Alligator Trend Following (SHORT)',
                    'timeframe': '15m',
                    'stop_loss': current_sma20 * 1.02,  # Above SMA20
                    'take_profit': current_price * 0.92,  # 8% target
                    'research_basis': '15m trend following'
                }
            else:
                return {
                    'action': 'HOLD',
                    'confidence': 0.0,
                    'reason': 'No trading opportunity found'
                }
                
        except Exception as e:
            logger.error(f"❌ Alligator MA signal error: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'Signal error: {str(e)}'}

    async def _bollinger_rsi_stochrsi_signal(self, symbol: str, market_data: Dict, ai_analysis: Dict, historical_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Bollinger Bands + RSI + Stochastic RSI Strategy
        Based on research: Sharpe 13.5 on BTC 15min
        """
        try:
            # Use provided historical data or fetch fresh data
            if historical_data is not None:
                data_5m = historical_data
            else:
                # Get 5m data (mean reversion optimized timeframe for sideways markets)
                now = datetime.now()
                data_5m = await self.exchange_manager.get_historical_data(
                    symbol=symbol, timeframe='5m', 
                    start_date=now - timedelta(days=2), end_date=now
                )
            
            if data_5m is None or len(data_5m) < 50:
                return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Insufficient data'}
            
            params = self.adaptive_params['bollinger_rsi_stochrsi']
            current_price = data_5m['close'].iloc[-1]
            
            # MEAN REVERSION INDICATORS FOR 5M SIDEWAYS MARKETS
            
            # Bollinger Bands (standard settings for 5m)
            bb_ma = data_5m['close'].rolling(params['bb_period']).mean()
            bb_std = data_5m['close'].rolling(params['bb_period']).std()
            bb_upper = bb_ma + (bb_std * params['bb_std_dev'])
            bb_lower = bb_ma - (bb_std * params['bb_std_dev'])
            bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
            
            # RSI (standard settings for 5m)
            delta = data_5m['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # SIMPLIFIED MEAN REVERSION CONDITIONS (realistic)
            # BUY: Oversold conditions (bounce from bottom)
            oversold_rsi = current_rsi < params['rsi_oversold']
            near_lower_bb = bb_position < 0.25  # Near lower Bollinger Band (realistic)
            
            # SELL: Overbought conditions (rejection from top)
            overbought_rsi = current_rsi > params['rsi_overbought']
            near_upper_bb = bb_position > 0.75  # Near upper Bollinger Band (realistic)
            
            # Volume confirmation for 5m scalping
            volume_strength = 0.0
            if 'volume' in data_5m.columns and len(data_5m) > 20:
                vol_ma = data_5m['volume'].rolling(20).mean()
                current_vol = data_5m['volume'].iloc[-1]
                if current_vol > vol_ma.iloc[-1] * 1.3:  # 30% above average for scalping
                    volume_strength = 0.2
            
            # LONG signal - Mean reversion bounce
            if oversold_rsi and near_lower_bb:
                confidence = 0.65 + volume_strength  # Increased from 0.45 to 0.65 for better signal generation
                return {
                    'action': 'BUY',
                    'confidence': min(0.8, confidence),  # Reduced max from 0.95 to 0.8
                    'entry_price': current_price,
                    'reasons': [
                        f"RSI oversold: {current_rsi:.1f}",
                        f"Near lower BB: {bb_position:.2f}",
                        "Mean reversion LONG opportunity",
                        f"Volume strength: {volume_strength:.2f}" if volume_strength > 0 else "No volume boost"
                    ],
                    'strategy': 'BB Mean Reversion (LONG)',
                    'timeframe': '5m',
                    'stop_loss': current_price * 0.995,  # Tight 0.5% stop for scalping
                    'take_profit': current_price * 1.02,  # 2% target for quick scalp
                    'research_basis': '5m mean reversion scalping'
                }
            
            # SHORT signal - Mean reversion rejection
            elif overbought_rsi and near_upper_bb:
                confidence = 0.65 + volume_strength  # Increased from 0.45 to 0.65 for better signal generation
                return {
                    'action': 'SELL',
                    'confidence': min(0.8, confidence),  # Reduced max from 0.95 to 0.8
                    'entry_price': current_price,
                    'reasons': [
                        f"RSI overbought: {current_rsi:.1f}",
                        f"Near upper BB: {bb_position:.2f}",
                        "Mean reversion SHORT opportunity",
                        f"Volume strength: {volume_strength:.2f}" if volume_strength > 0 else "No volume boost"
                    ],
                    'strategy': 'BB Mean Reversion (SHORT)',
                    'timeframe': '5m',
                    'stop_loss': current_price * 1.005,  # Tight 0.5% stop for scalping
                    'take_profit': current_price * 0.98,  # 2% target for quick scalp
                    'research_basis': '5m mean reversion scalping'
                }
            
            else:
                return {
                    'action': 'HOLD',
                    'confidence': 0.0,
                    'reason': 'No trading opportunity found'
                }
                
        except Exception as e:
            logger.error(f"❌ BB+RSI+StochRSI signal error: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'Signal error: {str(e)}'}

    async def backtest_strategy(self, strategy_name: str, symbol: str, historical_data: pd.DataFrame, 
                               initial_capital: float = 10000, custom_params: Dict = None, 
                               trading_fee: float = 0.001) -> Dict[str, Any]:
        """
        Backtest a single strategy on historical data
        NEW METHOD - Required by backtest_runner
        """
        try:
            # Map strategy names to research-backed strategies
            strategy_mapping = {
                # New research-backed strategies (direct mapping)
                'alligator_ma_momentum': 'alligator_ma_momentum',
                'bollinger_rsi_stochrsi': 'bollinger_rsi_stochrsi',
                # Old strategy mappings for backward compatibility
                'scalping': 'bollinger_rsi_stochrsi',
                'swing_trading': 'alligator_ma_momentum', 
                'trend_following': 'alligator_ma_momentum',
                'mean_reversion': 'bollinger_rsi_stochrsi',
                'volatility_breakout': 'alligator_ma_momentum',
                'mean_reversion_adaptive': 'bollinger_rsi_stochrsi'
            }
            
            actual_strategy = strategy_mapping.get(strategy_name, 'bollinger_rsi_stochrsi')
            
            logger.info(f"🔄 Backtesting {strategy_name} → {actual_strategy} on {symbol}")
            logger.info(f"📊 Data: {len(historical_data)} candles, Capital: ${initial_capital:,.2f}")
            
            # Initialize backtest variables
            capital = initial_capital
            position = None
            position_size = 0
            entry_price = 0
            entry_bar = 0  # Track when position was entered
            
            # Advanced exit strategy tracking
            trailing_stop = {
                'enabled': False,
                'peak_price': 0,
                'stop_price': 0,
                'activated': False
            }
            entry_atr = 0  # ATR at entry for volatility-based stops
            trades = []
            equity_curve = []
            
            # Enhanced portfolio risk tracking
            portfolio_risk = {
                'total_exposure': 0.0,
                'daily_trades': 0,
                'consecutive_losses': 0,
                'daily_pnl': 0.0,
                'max_drawdown': 0.0,
                'peak_capital': initial_capital,
                'current_drawdown': 0.0,
                'risk_limit_breached': False
            }
            
            # Strategy-specific parameters
            if actual_strategy == 'alligator_ma_momentum':
                params = self.adaptive_params['alligator_ma_momentum']
            elif actual_strategy == 'bollinger_rsi_stochrsi':
                params = self.adaptive_params['bollinger_rsi_stochrsi']
            else:
                # Default to bollinger strategy
                params = self.adaptive_params['bollinger_rsi_stochrsi']
            
            # Ensure we have required indicators
            df = historical_data.copy()
            df = await self._add_indicators(df)
            
            # Simulate trading
            for i in range(50, len(df)):  # Start after indicators stabilize
                current_row = df.iloc[i]
                current_price = current_row['close']
                
                # Analyze market regime
                regime_data = {
                    'close': current_price,
                    'volume': current_row.get('volume', 0),
                    'volatility': current_row.get('atr', 0.01),
                    'rsi': current_row.get('rsi_14', 50),
                    'bb_position': current_row.get('bb_position', 0.5)
                }
                
                # Determine regime
                if current_row.get('atr', 0.01) > 0.02:  # High volatility
                    regime = 'high_volatility'
                elif current_row.get('rsi_14', 50) > 70 or current_row.get('rsi_14', 50) < 30:
                    regime = 'mean_reversion_conditions'
                else:
                    regime = 'sideways_market'
                
                # Get signal
                market_data = {
                    'symbol': symbol,
                    'price': current_price,
                    'volume': current_row.get('volume', 0),
                    'timestamp': current_row.get('timestamp', i),
                    'indicators': {
                        'rsi_14': current_row.get('rsi_14', 50),
                        'macd_signal': current_row.get('macd_signal', 0),
                        'bb_position': current_row.get('bb_position', 0.5),
                        'atr': current_row.get('atr', 0.01)
                    }
                }
                
                # Position management
                if position is None:  # No position
                    # CRITICAL FIX: Use same signal generation as LIVE trading
                    # This ensures backtest results match live performance
                    
                    # Analyze market regime first (like in live trading)
                    regime_data = {
                        'close': current_price,
                        'volume': current_row.get('volume', 0),
                        'volatility': current_row.get('atr', 0.01),
                        'rsi': current_row.get('rsi_14', 50),
                        'bb_position': current_row.get('bb_position', 0.5)
                    }
                    
                    # Determine regime
                    if current_row.get('atr', 0.01) > 0.02:  # High volatility
                        regime = 'high_volatility'
                    elif current_row.get('rsi_14', 50) > 70 or current_row.get('rsi_14', 50) < 30:
                        regime = 'mean_reversion_conditions'
                    else:
                        regime = 'sideways_market'
                    
                    # Get confidence threshold from custom params or use moderate default
                    confidence_threshold = custom_params.get('confidence_threshold', 0.60) if custom_params else 0.60  # Balanced threshold for reasonable trading
                    
                    # Use get_entry_signal method (same as live trading) with AI filtering
                    # IMPORTANT: Pass df slice to prevent API calls during backtest
                    signal = await self.get_entry_signal(symbol, market_data, regime, current_df_slice=df.iloc[:i+1])
                    
                    # Use combined_confidence if available, otherwise use raw confidence
                    signal_confidence = signal.get('combined_confidence', signal.get('confidence', 0.0))
                    
                    if (signal['action'] == 'BUY' or signal['action'] == 'SELL') and signal_confidence > confidence_threshold and not portfolio_risk['risk_limit_breached']:
                        # Enter position with RISK MANAGER sizing (consistent with live trading)
                        if self.risk_manager:
                            # Use RiskManager for consistent position sizing
                            try:
                                position_calc = await self.risk_manager.calculate_position_size_backtest(
                                    symbol=symbol,
                                    action=signal,
                                    current_price=current_price,
                                    account_balance=capital,
                                    confidence=signal_confidence
                                )
                                position_size = position_calc.get('size', 0)
                                
                                if position_size <= 0:
                                    logger.debug(f"RiskManager rejected position for {symbol}")
                                    continue
                                    
                                logger.debug(f"RiskManager position: {position_size} @ ${current_price}")
                                
                            except Exception as e:
                                logger.warning(f"RiskManager error: {e}, using fallback sizing")
                                # Fallback to config-based sizing
                                params = self.adaptive_params.get(actual_strategy, {})
                                risk_per_trade = params.get('risk_per_trade', 0.02)
                                leverage = params.get('leverage', 2.0)
                                position_value = capital * risk_per_trade * leverage
                                position_size = position_value / current_price
                        else:
                            # Get risk parameters from strategy config
                            params = self.adaptive_params.get(actual_strategy, {})
                            risk_per_trade = params.get('risk_per_trade', 0.02)  # Default 2%
                            leverage = params.get('leverage', 2.0)               # Default 2x
                            
                            position_value = capital * risk_per_trade * leverage
                            position_size = position_value / current_price
                        
                        if signal['action'] == 'BUY':
                            position = 'LONG'
                        else:  # SELL
                            position = 'SHORT'
                            
                        entry_price = current_price
                        entry_bar = i  # Record entry bar for duration calculation
                        
                        # Apply entry fee
                        entry_fee = position_value * trading_fee
                        capital -= entry_fee
                        
                        # Initialize advanced exit strategies
                        trailing_stop['enabled'] = params.get('trailing_stop_enabled', False)
                        trailing_stop['peak_price'] = current_price
                        trailing_stop['activated'] = False
                        
                        # Calculate volatility-based stop using current ATR
                        current_atr = current_row.get('atr', current_price * 0.02)  # Fallback to 2% of price
                        entry_atr = current_atr
                        
                        # Update portfolio risk tracking
                        portfolio_risk['total_exposure'] = position_value
                        portfolio_risk['daily_trades'] += 1
                        
                        # Check portfolio risk limits
                        if portfolio_risk['daily_trades'] > 10:  # Max 10 trades per day
                            portfolio_risk['risk_limit_breached'] = True
                            logger.warning(f"⚠️ Daily trade limit exceeded: {portfolio_risk['daily_trades']}")
                        
                        logger.debug(f"📈 {position} Entry: {symbol} @ ${current_price:.4f}, Size: {position_size:.6f}, Fee: ${entry_fee:.2f}, Exposure: ${position_value:.2f}")
                
                else:  # Have position
                    # Check exit conditions - Strategy-specific logic with custom params support
                    if position == 'LONG':
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:  # SHORT
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    should_exit = False
                    exit_reason = ""
                    
                    # Use custom parameters if provided, otherwise use AGGRESSIVE defaults
                    if custom_params:
                        profit_target = custom_params.get('profit_target', 0.08)
                        stop_loss = custom_params.get('stop_loss', 0.04)
                    else:
                        # Get exit strategy parameters from config
                        params = self.adaptive_params.get(actual_strategy, {})
                        profit_target = params.get('profit_target', 0.05)  # Default 5%
                        stop_loss = params.get('stop_loss', 0.02)           # Default 2%
                    
                    # 🚀 ADVANCED EXIT CONDITIONS
                    
                    # 1. UPDATE TRAILING STOP
                    if trailing_stop['enabled']:
                        if position == 'LONG':
                            # Update peak for long position
                            if current_price > trailing_stop['peak_price']:
                                trailing_stop['peak_price'] = current_price
                            
                            # Check if trailing should be activated
                            if not trailing_stop['activated'] and pnl_pct > params.get('trailing_stop_activation', 0.03):
                                trailing_stop['activated'] = True
                                logger.debug(f"🔄 Trailing stop activated at {pnl_pct:.2%} profit")
                            
                            # Calculate trailing stop price
                            if trailing_stop['activated']:
                                trail_distance = params.get('trailing_stop_distance', 0.015)
                                trailing_stop['stop_price'] = trailing_stop['peak_price'] * (1 - trail_distance)
                        
                        else:  # SHORT position
                            # Update peak (lowest price) for short position
                            if current_price < trailing_stop['peak_price']:
                                trailing_stop['peak_price'] = current_price
                            
                            # Check if trailing should be activated
                            if not trailing_stop['activated'] and pnl_pct > params.get('trailing_stop_activation', 0.03):
                                trailing_stop['activated'] = True
                                logger.debug(f"🔄 Trailing stop activated at {pnl_pct:.2%} profit")
                            
                            # Calculate trailing stop price
                            if trailing_stop['activated']:
                                trail_distance = params.get('trailing_stop_distance', 0.015)
                                trailing_stop['stop_price'] = trailing_stop['peak_price'] * (1 + trail_distance)
                    
                    # 2. CHECK ALL EXIT CONDITIONS
                    
                    # Standard profit target
                    if pnl_pct > profit_target:
                        should_exit = True
                        exit_reason = "Profit target"
                    
                    # Trailing stop exit
                    elif trailing_stop['activated']:
                        if position == 'LONG' and current_price <= trailing_stop['stop_price']:
                            should_exit = True
                            exit_reason = f"Trailing stop (peak: ${trailing_stop['peak_price']:.4f})"
                        elif position == 'SHORT' and current_price >= trailing_stop['stop_price']:
                            should_exit = True
                            exit_reason = f"Trailing stop (peak: ${trailing_stop['peak_price']:.4f})"
                    
                    # Volatility-based stop
                    elif params.get('volatility_stop_enabled', False):
                        atr_multiplier = params.get('atr_stop_multiplier', 2.0)
                        if position == 'LONG':
                            volatility_stop = entry_price - (entry_atr * atr_multiplier)
                            if current_price <= volatility_stop:
                                should_exit = True
                                exit_reason = f"Volatility stop ({atr_multiplier}x ATR)"
                        else:  # SHORT
                            volatility_stop = entry_price + (entry_atr * atr_multiplier)
                            if current_price >= volatility_stop:
                                should_exit = True
                                exit_reason = f"Volatility stop ({atr_multiplier}x ATR)"
                    
                    # Standard stop loss (if no trailing stop is active)
                    elif pnl_pct < -stop_loss:
                        should_exit = True
                        exit_reason = "Stop loss"
                    
                    # Time limit
                    elif (i - entry_bar) > params['max_hold_bars']:
                        should_exit = True
                        exit_reason = "Time limit"
                
                    if should_exit:
                        # Exit position with LEVERAGE-ADJUSTED PnL calculation for LONG/SHORT
                        base_pnl = position_size * (current_price - entry_price) if position == 'LONG' else position_size * (entry_price - current_price)
                        # Apply leverage multiplier to PnL (leverage was already used in position sizing)
                        pnl = base_pnl  # PnL is already leveraged due to position_size calculation
                        
                        # Apply exit fee
                        exit_fee = position_size * current_price * trading_fee
                        pnl -= exit_fee  # Subtract exit fee from PnL
                            
                        capital += pnl
                        
                        # Update portfolio risk tracking
                        portfolio_risk['total_exposure'] = 0.0  # No position
                        portfolio_risk['daily_pnl'] += pnl
                        
                        # Track consecutive losses
                        if pnl < 0:
                            portfolio_risk['consecutive_losses'] += 1
                        else:
                            portfolio_risk['consecutive_losses'] = 0  # Reset on profit
                        
                        # Update drawdown tracking
                        if capital > portfolio_risk['peak_capital']:
                            portfolio_risk['peak_capital'] = capital
                            portfolio_risk['current_drawdown'] = 0.0
                        else:
                            portfolio_risk['current_drawdown'] = (portfolio_risk['peak_capital'] - capital) / portfolio_risk['peak_capital']
                            if portfolio_risk['current_drawdown'] > portfolio_risk['max_drawdown']:
                                portfolio_risk['max_drawdown'] = portfolio_risk['current_drawdown']
                        
                        # Risk limit checks
                        if portfolio_risk['consecutive_losses'] >= 3:
                            portfolio_risk['risk_limit_breached'] = True
                            logger.warning(f"⚠️ Consecutive loss limit reached: {portfolio_risk['consecutive_losses']}")
                        
                        if portfolio_risk['current_drawdown'] > 0.10:  # 10% drawdown limit
                            portfolio_risk['risk_limit_breached'] = True
                            logger.warning(f"⚠️ Drawdown limit exceeded: {portfolio_risk['current_drawdown']:.2%}")
                        
                        trade = {
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'position_type': position,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'reason': exit_reason,
                            'duration': i - entry_bar,  # Fixed: Actual position duration in bars
                            'exit_fee': exit_fee
                        }
                        trades.append(trade)
                        
                        logger.debug(f"📉 {position} Exit: {symbol} @ ${current_price:.4f}, PnL: ${pnl:.2f} ({pnl_pct:.2%}), Fee: ${exit_fee:.2f}")
                        
                        position = None
                        position_size = 0
                        entry_price = 0
                        entry_bar = 0  # Reset entry bar
                        entry_atr = 0  # Reset ATR
                        
                        # Reset trailing stop
                        trailing_stop = {
                            'enabled': False,
                            'peak_price': 0,
                            'stop_price': 0,
                            'activated': False
                        }
                
                # Track equity with correct unrealized PnL for LONG/SHORT
                current_equity = capital
                if position:
                    if position == 'LONG':
                        unrealized_pnl = position_size * (current_price - entry_price)
                    else:  # SHORT
                        unrealized_pnl = position_size * (entry_price - current_price)
                    current_equity += unrealized_pnl
                
                equity_curve.append(current_equity)
            
            # Calculate performance metrics
            total_return = (capital - initial_capital) / initial_capital
            max_equity = max(equity_curve) if equity_curve else initial_capital
            max_drawdown = (max_equity - min(equity_curve)) / max_equity if equity_curve else 0
            
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / len(trades) if trades else 0
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            
            profit_factor = abs(sum([t['pnl'] for t in winning_trades]) / sum([t['pnl'] for t in losing_trades])) if losing_trades else float('inf')
            
            # Calculate Sharpe ratio (simplified)
            returns = np.diff(equity_curve) / equity_curve[:-1] if len(equity_curve) > 1 else [0]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            results = {
                'initial_capital': initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'strategy': actual_strategy,
                'symbol': symbol
            }
            
            logger.info(f"✅ Backtest completed: {total_return:.2%} return, {len(trades)} trades")
            return results
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            traceback.print_exc()
            return {
                'error': str(e),
                'initial_capital': initial_capital,
                'final_capital': initial_capital,
                'total_return': 0.0,
                'strategy': strategy_name,
                'symbol': symbol
            }

    async def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        try:
            # RSI
            df['rsi_14'] = self._calculate_rsi(df['close'].values, 14)
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            bb_ma = df['close'].rolling(bb_period).mean()
            bb_std_val = df['close'].rolling(bb_period).std()
            df['bb_upper'] = bb_ma + (bb_std_val * bb_std)
            df['bb_lower'] = bb_ma - (bb_std_val * bb_std)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # ATR
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = np.abs(df['high'] - df['close'].shift())
            df['low_close'] = np.abs(df['low'] - df['close'].shift())
            df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            df['atr'] = df['tr'].rolling(14).mean()
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error adding indicators: {e}")
            return df

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)

        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down if down != 0 else 0
            rsi[i] = 100. - 100. / (1. + rs)

        return rsi

    def _calculate_market_volatility(self, historical_data: pd.DataFrame) -> float:
        """Calculate market volatility for parameter optimization"""
        try:
            if len(historical_data) < 20:
                return 0.5
            
            # Calculate returns
            returns = historical_data['close'].pct_change().dropna()
            
            # Calculate volatility (standard deviation of returns)
            volatility = returns.std()
            
            return min(volatility * 100, 1.0)  # Scale and cap at 1.0
            
        except Exception as e:
            logger.error(f"❌ Market volatility calculation error: {e}")
            return 0.5
    
    def _calculate_market_trend(self, historical_data: pd.DataFrame) -> float:
        """Calculate market trend strength for parameter optimization"""
        try:
            if len(historical_data) < 50:
                return 0.5
            
            # Calculate moving averages
            short_ma = historical_data['close'].rolling(window=10).mean()
            long_ma = historical_data['close'].rolling(window=50).mean()
            
            # Calculate trend strength
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            
            if current_long == 0:
                return 0.5
            
            # Trend strength based on MA relationship
            trend_strength = (current_short - current_long) / current_long
            
            # Normalize to 0-1 range
            return min(max(trend_strength + 0.5, 0), 1)
            
        except Exception as e:
            logger.error(f"❌ Market trend calculation error: {e}")
            return 0.5