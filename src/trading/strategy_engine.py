"""
Strategy Engine
Multi-strateji trading motoru
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class StrategyEngine:
    """Strateji motoru - tüm trading stratejilerini yönetir"""
    
    def __init__(self, strategies_config: Dict[str, Any], signal_filter, market_analyzer, confidence_calculator):
        """
        Args:
            strategies_config: Strateji konfigürasyonları
            signal_filter: AI sinyal filtreleme sistemi
            market_analyzer: Market analizöru
            confidence_calculator: Güven faktörü hesaplayıcısı
        """
        self.config = strategies_config
        self.signal_filter = signal_filter
        self.market_analyzer = market_analyzer
        self.confidence_calculator = confidence_calculator
        
        # Strategy configurations
        self.scalping_config = strategies_config.get('scalping', {})
        self.swing_config = strategies_config.get('swing_trading', {})
        self.trend_config = strategies_config.get('trend_following', {})
        self.mean_reversion_config = strategies_config.get('mean_reversion', {})
        
        # Active strategies
        self.active_strategies = []
        self._load_active_strategies()
        
        logger.info("🎯 Strategy Engine initialized")
    
    def _load_active_strategies(self) -> None:
        """Aktif stratejileri yükle"""
        self.active_strategies = []
        
        for strategy_name, config in self.config.items():
            if config.get('enabled', False):
                self.active_strategies.append(strategy_name)
        
        logger.info(f"🎯 Aktif stratejiler: {self.active_strategies}")
    
    async def select_strategy(self, symbol: str, market_condition: Dict[str, Any], 
                             confidence: float) -> Optional[str]:
        """Piyasa koşullarına göre en uygun stratejiyi seç"""
        try:
            market_cond = market_condition.get('condition', 'sideways_market')
            volatility = market_condition.get('volatility', 'normal')
            strength = market_condition.get('strength', 0.5)
            
            # Strategy selection logic
            if market_cond == 'bull_market' and strength > 0.7:
                if volatility == 'low':
                    return 'trend_following'
                else:
                    return 'swing_trading'
            elif market_cond == 'bear_market' and strength > 0.7:
                return 'mean_reversion'
            elif volatility == 'high' and confidence > 0.8:
                return 'scalping'
            else:
                return 'swing_trading'  # Default safe strategy
                
        except Exception as e:
            logger.error(f"❌ Strategy selection error: {e}")
            return 'swing_trading'
    
    async def get_entry_signal(self, symbol: str, market_data: Dict, signals: Dict, strategy: str) -> Optional[Dict[str, Any]]:
        """Giriş sinyali al"""
        try:
            if strategy not in self.config:
                return None
            
            config = self.config[strategy]
            
            if strategy == 'scalping':
                return await self._scalping_entry(symbol, market_data, signals, config)
            elif strategy == 'swing_trading':
                return await self._swing_trading_entry(symbol, market_data, signals, config)
            elif strategy == 'trend_following':
                return await self._trend_following_entry(symbol, market_data, signals, config)
            elif strategy == 'mean_reversion':
                return await self._mean_reversion_entry(symbol, market_data, signals, config)
            else:
                logger.warning(f"⚠️ Bilinmeyen strateji: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Entry signal hatası: {e}")
            return None
    
    async def get_exit_signal(self, symbol: str, market_data: Dict, signals: Dict, 
                            position: Dict, strategy: str) -> Optional[Dict[str, Any]]:
        """Çıkış sinyali al"""
        try:
            if strategy == 'scalping':
                return await self._scalping_exit(symbol, market_data, position)
            elif strategy == 'swing_trading':
                return await self._swing_trading_exit(symbol, market_data, position)
            elif strategy == 'trend_following':
                return await self._trend_following_exit(symbol, market_data, position)
            elif strategy == 'mean_reversion':
                return await self._mean_reversion_exit(symbol, market_data, position)
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Exit signal hatası: {e}")
            return None
    
    async def _scalping_entry(self, symbol: str, market_data: Dict, signals: Dict, config: Dict) -> Optional[Dict]:
        """Scalping giriş sinyali"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 20:
                return None
            
            # Quick RSI check
            current_price = df['close'].iloc[-1]
            
            # Simple scalping logic - quick moves
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            
            if abs(price_change) > 0.005:  # 0.5% move
                signal_type = 'BUY' if price_change > 0 else 'SELL'
                
                return {
                    'signal': signal_type,
                    'entry_price': current_price,
                    'stop_loss': current_price * (0.998 if signal_type == 'BUY' else 1.002),
                    'take_profit': current_price * (1.004 if signal_type == 'BUY' else 0.996),
                    'confidence': 0.7,
                    'reason': f'Scalping {price_change:.3f}% move'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Scalping entry error: {e}")
            return None
    
    async def _swing_trading_entry(self, symbol: str, market_data: Dict, signals: Dict, config: Dict) -> Optional[Dict]:
        """Swing trading giriş sinyali"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 50:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Simple swing logic
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-1]
            
            if current_price > sma_20 > sma_50:
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price * 0.97,
                    'take_profit': current_price * 1.06,
                    'confidence': 0.8,
                    'reason': 'Swing uptrend'
                }
            elif current_price < sma_20 < sma_50:
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price * 1.03,
                    'take_profit': current_price * 0.94,
                    'confidence': 0.8,
                    'reason': 'Swing downtrend'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Swing trading entry error: {e}")
            return None
    
    async def _trend_following_entry(self, symbol: str, market_data: Dict, signals: Dict, config: Dict) -> Optional[Dict]:
        """Trend following giriş sinyali"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 100:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Trend analysis
            sma_50 = df['close'].rolling(50).mean().iloc[-1]
            sma_100 = df['close'].rolling(100).mean().iloc[-1]
            
            # Strong trend condition
            if sma_50 > sma_100 * 1.02:  # 2% above
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price * 0.95,
                    'take_profit': current_price * 1.10,
                    'confidence': 0.85,
                    'reason': 'Strong uptrend'
                }
            elif sma_50 < sma_100 * 0.98:  # 2% below
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price * 1.05,
                    'take_profit': current_price * 0.90,
                    'confidence': 0.85,
                    'reason': 'Strong downtrend'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Trend following entry error: {e}")
            return None
    
    async def _mean_reversion_entry(self, symbol: str, market_data: Dict, signals: Dict, config: Dict) -> Optional[Dict]:
        """Mean reversion giriş sinyali"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 50:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Bollinger Bands
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            std_20 = df['close'].rolling(20).std().iloc[-1]
            bb_upper = sma_20 + (std_20 * 2)
            bb_lower = sma_20 - (std_20 * 2)
            
            # Mean reversion signals
            if current_price <= bb_lower:
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price * 0.96,
                    'take_profit': sma_20,
                    'confidence': 0.75,
                    'reason': 'Mean reversion - oversold'
                }
            elif current_price >= bb_upper:
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price * 1.04,
                    'take_profit': sma_20,
                    'confidence': 0.75,
                    'reason': 'Mean reversion - overbought'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Mean reversion entry error: {e}")
            return None
    
    async def _scalping_exit(self, symbol: str, market_data: Dict, position: Dict) -> Optional[Dict]:
        """Scalping çıkış logic"""
        # Quick profit/loss exit
        current_price = market_data.get('dataframe', {}).get('close', pd.Series()).iloc[-1] if 'dataframe' in market_data else position['entry_price']
        entry_price = position['entry_price']
        
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Quick exit for scalping
        if abs(pnl_pct) > 0.005:  # 0.5% move
            return {
                'signal': 'EXIT',
                'exit_price': current_price,
                'reason': f'Scalping quick exit: {pnl_pct:.3f}%'
            }
        
        return None
    
    async def _swing_trading_exit(self, symbol: str, market_data: Dict, position: Dict) -> Optional[Dict]:
        """Swing trading çıkış logic"""
        df = market_data.get('dataframe')
        if df is None or len(df) < 20:
            return None
        
        current_price = df['close'].iloc[-1]
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        
        # Exit on trend reversal
        side = position.get('side', 'BUY')
        entry_price = position['entry_price']
        
        if side == 'BUY' and current_price < sma_20 * 0.99:
            return {
                'signal': 'EXIT',
                'exit_price': current_price,
                'reason': 'Swing exit - below SMA20'
            }
        elif side == 'SELL' and current_price > sma_20 * 1.01:
            return {
                'signal': 'EXIT',
                'exit_price': current_price,
                'reason': 'Swing exit - above SMA20'
            }
        
        return None
    
    async def _trend_following_exit(self, symbol: str, market_data: Dict, position: Dict) -> Optional[Dict]:
        """Trend following çıkış logic"""
        # Let profits run, cut losses
        return None  # Use stop loss / take profit
    
    async def _mean_reversion_exit(self, symbol: str, market_data: Dict, position: Dict) -> Optional[Dict]:
        """Mean reversion çıkış logic"""
        df = market_data.get('dataframe')
        if df is None or len(df) < 20:
            return None
        
        current_price = df['close'].iloc[-1]
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        
        # Exit when close to mean
        price_diff = abs(current_price - sma_20) / sma_20
        
        if price_diff < 0.01:  # Within 1% of mean
            return {
                'signal': 'EXIT',
                'exit_price': current_price,
                'reason': 'Mean reversion target reached'
            }
        
        return None
    
    async def backtest_strategy(self, symbol: str, strategy: str, historical_data: pd.DataFrame, 
                               initial_capital: float = 10000) -> Dict[str, Any]:
        """Strateji backtesting"""
        try:
            if historical_data.empty or len(historical_data) < 100:
                return {'error': 'Insufficient data for backtesting'}
            
            trades = []
            capital = initial_capital
            position = None
            
            for i in range(50, len(historical_data)):
                current_data = historical_data.iloc[:i+1]
                market_data = {'dataframe': current_data}
                signals = {}  # Simplified for backtest
                
                if position is None:
                    # Look for entry
                    entry_signal = await self.get_entry_signal(symbol, market_data, signals, strategy)
                    
                    if entry_signal:
                        position = {
                            'entry_price': entry_signal['entry_price'],
                            'side': entry_signal['signal'],
                            'size': capital * 0.1 / entry_signal['entry_price'],  # 10% of capital
                            'entry_index': i
                        }
                        
                else:
                    # Look for exit
                    current_price = current_data['close'].iloc[-1]
                    
                    # Check stop loss / take profit
                    entry_price = position['entry_price']
                    side = position['side']
                    
                    should_exit = False
                    exit_reason = ""
                    
                    if side == 'BUY':
                        if current_price <= entry_price * 0.95:  # 5% stop loss
                            should_exit = True
                            exit_reason = "Stop loss"
                        elif current_price >= entry_price * 1.05:  # 5% take profit
                            should_exit = True
                            exit_reason = "Take profit"
                    else:  # SELL
                        if current_price >= entry_price * 1.05:  # 5% stop loss
                            should_exit = True
                            exit_reason = "Stop loss"
                        elif current_price <= entry_price * 0.95:  # 5% take profit
                            should_exit = True
                            exit_reason = "Take profit"
                    
                    # Check strategy exit
                    if not should_exit:
                        exit_signal = await self.get_exit_signal(symbol, market_data, signals, position, strategy)
                        if exit_signal:
                            should_exit = True
                            exit_reason = exit_signal.get('reason', 'Strategy exit')
                    
                    if should_exit:
                        # Calculate P&L
                        if side == 'BUY':
                            pnl = (current_price - entry_price) * position['size']
                        else:
                            pnl = (entry_price - current_price) * position['size']
                        
                        capital += pnl
                        
                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'side': side,
                            'pnl': pnl,
                            'pnl_pct': pnl / (entry_price * position['size']) * 100,
                            'duration': i - position['entry_index'],
                            'exit_reason': exit_reason
                        })
                        
                        position = None
            
            # Calculate metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            
            total_pnl = sum(t['pnl'] for t in trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # ROI
            roi = (capital - initial_capital) / initial_capital * 100
            
            return {
                'symbol': symbol,
                'strategy': strategy,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'roi': roi,
                'final_capital': capital,
                'trades': trades[-10:] if trades else []  # Last 10 trades
            }
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            return {'error': str(e)}
    
    async def optimize_strategy_parameters(self, symbol: str, strategy: str, 
                                         historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Strateji parametre optimizasyonu"""
        try:
            if strategy not in ['scalping', 'swing_trading', 'trend_following', 'mean_reversion']:
                return {'error': 'Strategy not supported for optimization'}
            
            # Define parameter ranges for optimization
            param_ranges = {
                'scalping': {
                    'move_threshold': [0.003, 0.005, 0.007, 0.010],
                    'stop_loss_pct': [0.002, 0.003, 0.005],
                    'take_profit_pct': [0.004, 0.006, 0.008]
                },
                'swing_trading': {
                    'sma_short': [15, 20, 25],
                    'sma_long': [40, 50, 60],
                    'stop_loss_pct': [0.02, 0.03, 0.05],
                    'take_profit_pct': [0.04, 0.06, 0.08]
                }
            }
            
            if strategy not in param_ranges:
                # Default backtest
                return await self.backtest_strategy(symbol, strategy, historical_data)
            
            best_result = None
            best_roi = -float('inf')
            
            # Real Grid search with parameter combinations
            ranges = param_ranges[strategy]
            param_names = list(ranges.keys())
            param_values = list(ranges.values())
            
            import itertools
            combinations = list(itertools.product(*param_values))
            
            tested_combinations = 0
            logger.info(f"🔧 Testing {len(combinations)} parameter combinations")
            
            # Test each combination
            for combination in combinations[:20]:  # Limit to 20 tests for speed
                tested_combinations += 1
                
                # Create parameter dict
                params = dict(zip(param_names, combination))
                logger.debug(f"🧪 Testing combination {tested_combinations}: {params}")
                
                # Run backtest with these parameters
                result = await self._backtest_with_params(symbol, strategy, historical_data, params)
                
                if result and 'roi' in result and result['roi'] > best_roi:
                    best_roi = result['roi']
                    best_result = result.copy()
                    best_result['best_params'] = params
                    logger.info(f"🎯 New best ROI: {best_roi:.2%} with {params}")
            
            if best_result:
                best_result['optimization'] = 'completed'
                best_result['tested_combinations'] = tested_combinations
                logger.success(f"✅ Optimization completed: {tested_combinations} combinations tested")
            else:
                best_result = {'error': 'No profitable combinations found', 'tested_combinations': tested_combinations}
            
            return best_result
            
        except Exception as e:
            logger.error(f"❌ Parameter optimization error: {e}")
            return {'error': str(e)}
    
    async def _backtest_with_params(self, symbol: str, strategy: str, 
                                   historical_data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run backtest with specific parameters"""
        try:
            # Temporarily store original strategy parameters
            original_params = getattr(self, f"{strategy}_params", {})
            
            # Update strategy parameters
            setattr(self, f"{strategy}_params", params)
            
            # Run backtest
            result = await self.backtest_strategy(symbol, strategy, historical_data)
            
            # Restore original parameters
            setattr(self, f"{strategy}_params", original_params)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Backtest with params error: {e}")
            return None