"""
Strategy Engine
Multi-strateji trading motoru
"""

import numpy as np
import pandas as pd
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class StrategyEngine:
    """Strateji motoru - tüm trading stratejilerini yönetir"""
    
    def __init__(self, strategy_config: Dict, ai_signal_filter, market_analyzer, confidence_calculator):
        """Strategy Engine başlatıcısı"""
        self.config = strategy_config
        self.ai_signal_filter = ai_signal_filter
        self.market_analyzer = market_analyzer
        self.confidence_calculator = confidence_calculator
        
        # Strategy-specific timeframes (CRITICAL FIX)
        self.strategy_timeframes = {
            'scalping': '5m',        # Scalping: 5-minute timeframe
            'swing_trading': '1h',   # Swing: 1-hour timeframe  
            'trend_following': '4h', # Trend: 4-hour timeframe
            'mean_reversion': '15m'  # Mean reversion: 15-minute timeframe
        }
        
        # Strategy-specific parameters (will be optimized)
        self.strategy_params = {
            'scalping': {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'volume_threshold': 1.5,
                'min_signals': 3,
                'min_strength': 0.7
            },
            'swing_trading': {
                'sma_short': 20,
                'sma_long': 50,
                'rsi_threshold': 35,
                'volume_confirmation': 1.3,
                'trend_confirmation': True
            },
            'trend_following': {
                'ema_fast': 12,
                'ema_slow': 26,
                'trend_strength': 0.7,
                'volume_filter': 1.2,
                'macd_confirmation': True
            },
            'mean_reversion': {
                'bb_period': 20,
                'bb_std': 2.0,
                'rsi_extreme': 25,
                'reversion_target': 0.6,
                'oversold_threshold': 25,
                'overbought_threshold': 75
            }
        }
        
        # Load active strategies
        self.active_strategies = self._load_active_strategies()
        
        logger.info("🎯 Strategy Engine initialized")
    
    def _load_active_strategies(self) -> List[str]:
        """Aktif stratejileri yükle"""
        active_strategies = []
        
        # If config is None or empty, use all strategies as default
        if not self.config:
            active_strategies = ['scalping', 'swing_trading', 'trend_following', 'mean_reversion']
        else:
            for strategy_name, config in self.config.items():
                if config.get('enabled', False):
                    active_strategies.append(strategy_name)
        
        # If no strategies enabled, enable all as fallback
        if not active_strategies:
            active_strategies = ['scalping', 'swing_trading', 'trend_following', 'mean_reversion']
        
        logger.info(f"🎯 Aktif stratejiler: {active_strategies}")
        return active_strategies
    
    async def select_strategy(self, symbol: str, market_condition: Dict[str, Any], 
                             confidence: float) -> Optional[str]:
        """Enhanced strategy selection based on REAL market analysis"""
        try:
            # Get real market metrics
            market_cond = market_condition.get('condition', 'sideways_market')
            volatility = market_condition.get('volatility_score', 0.5)  # 0-1 scale
            trend_strength = market_condition.get('trend_strength', 0.5)  # 0-1 scale
            volume_profile = market_condition.get('volume_profile', 'normal')
            
            # Calculate strategy scores based on real conditions
            strategy_scores = {}
            
            # Scalping: Best in high volatility, sideways markets
            scalping_score = 0.3  # Base score
            if volatility > 0.6:  # High volatility
                scalping_score += 0.4
            if market_cond == 'sideways_market':
                scalping_score += 0.3
            if volume_profile == 'high':
                scalping_score += 0.2
            if confidence > 0.8:  # High AI confidence
                scalping_score += 0.1
            strategy_scores['scalping'] = scalping_score
            
            # Trend Following: Best in strong trending markets
            trend_score = 0.2
            if trend_strength > 0.7:  # Strong trend
                trend_score += 0.5
            if market_cond in ['bull_market', 'bear_market']:
                trend_score += 0.3
            if volatility < 0.4:  # Low volatility = stable trend
                trend_score += 0.2
            strategy_scores['trend_following'] = trend_score
            
            # Swing Trading: Balanced approach for medium volatility
            swing_score = 0.4  # Higher base score (safer)
            if 0.3 < volatility < 0.7:  # Medium volatility
                swing_score += 0.3
            if 0.4 < trend_strength < 0.8:  # Medium trend strength
                swing_score += 0.2
            if market_cond == 'sideways_market':
                swing_score += 0.1
            strategy_scores['swing_trading'] = swing_score
            
            # Mean Reversion: Best when price deviates from norm
            reversion_score = 0.2
            if market_cond == 'sideways_market':
                reversion_score += 0.3
            if volatility > 0.5:  # Higher volatility for reversions
                reversion_score += 0.3
            if trend_strength < 0.3:  # Weak trend = good for reversion
                reversion_score += 0.4
            strategy_scores['mean_reversion'] = reversion_score
            
            # Select best strategy from active ones
            best_strategy = None
            best_score = 0
            
            # Safety check for active_strategies
            if not self.active_strategies:
                logger.warning("⚠️ No active strategies found, using default")
                self.active_strategies = ['scalping', 'swing_trading', 'trend_following', 'mean_reversion']
            
            for strategy in self.active_strategies:
                if strategy in strategy_scores:
                    score = strategy_scores[strategy]
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy
            
            logger.info(f"📊 Strategy scores: {strategy_scores}")
            logger.info(f"🎯 Selected: {best_strategy} (score: {best_score:.2f})")
            
            return best_strategy or 'swing_trading'  # Safe fallback
                
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
        """Enhanced Scalping Strategy - Multi-factor confirmation"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 50:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Calculate enhanced technical indicators
            indicators = self._calculate_enhanced_indicators(df)
            
            # Multi-factor confirmation system
            buy_signals = 0
            sell_signals = 0
            signal_strength = 0
            
            # Get strategy parameters (MUCH MORE CONSERVATIVE)
            params = self.strategy_params.get('scalping', {})
            rsi_oversold = params.get('rsi_oversold', 20)  # More extreme
            rsi_overbought = params.get('rsi_overbought', 80)  # More extreme
            volume_threshold = params.get('volume_threshold', 2.5)  # Much higher volume needed
            min_signals = params.get('min_signals', 5)  # MORE confirmation needed
            min_strength = params.get('min_strength', 0.85)  # MUCH higher strength needed
            
            # 1. RSI Mean Reversion (Scalping favors quick reversals)
            rsi = indicators['rsi'].iloc[-1]
            if rsi < rsi_oversold:  # Oversold (optimized)
                buy_signals += 2
                signal_strength += 0.3
            elif rsi > rsi_overbought:  # Overbought (optimized)
                sell_signals += 2
                signal_strength += 0.3
            
            # 2. Volume Spike Confirmation
            volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
            if volume_ratio > volume_threshold:  # Volume spike (optimized)
                signal_strength += 0.2
                if buy_signals > sell_signals:
                    buy_signals += 1
                elif sell_signals > buy_signals:
                    sell_signals += 1
            
            # 3. Price Action - Quick momentum
            price_momentum_1 = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            price_momentum_5 = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            
            if price_momentum_1 > 0.002 and price_momentum_5 > 0.003:  # Strong short-term momentum
                buy_signals += 1
                signal_strength += 0.15
            elif price_momentum_1 < -0.002 and price_momentum_5 < -0.003:
                sell_signals += 1
                signal_strength += 0.15
            
            # 4. Bollinger Band position
            bb_position = (current_price - indicators['bb_lower'].iloc[-1]) / (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1])
            if bb_position < 0.2:  # Near lower band
                buy_signals += 1
                signal_strength += 0.1
            elif bb_position > 0.8:  # Near upper band
                sell_signals += 1
                signal_strength += 0.1
            
            # 5. AI Signal confirmation
            ai_confidence = signals.get('confidence', 0)
            if ai_confidence > 0.6:
                signal_strength += 0.25
                ai_signals = signals.get('signals', [])
                buy_ai = sum(1 for s in ai_signals if s.get('type') == 'BUY')
                sell_ai = sum(1 for s in ai_signals if s.get('type') == 'SELL')
                
                if buy_ai > sell_ai:
                    buy_signals += 1
                elif sell_ai > buy_ai:
                    sell_signals += 1
            
            # Decision logic - require strong multi-factor confirmation (optimized)
            
            if buy_signals >= min_signals and signal_strength >= min_strength and buy_signals > (sell_signals + 2):
                # Dynamic stop loss based on volatility
                atr = indicators['atr'].iloc[-1]
                volatility_factor = min(atr / current_price, 0.01)  # Cap at 1%
                
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price * (1 - max(0.003, volatility_factor * 2)),
                    'take_profit': current_price * (1 + max(0.005, volatility_factor * 2.5)),
                    'confidence': signal_strength,
                    'reason': f'Scalping: {buy_signals} buy signals, strength {signal_strength:.2f}',
                    'signals_count': buy_signals
                }
            elif sell_signals >= min_signals and signal_strength >= min_strength and sell_signals > (buy_signals + 2):
                atr = indicators['atr'].iloc[-1]
                volatility_factor = min(atr / current_price, 0.01)
                
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price * (1 + max(0.003, volatility_factor * 2)),
                    'take_profit': current_price * (1 - max(0.005, volatility_factor * 2.5)),
                    'confidence': signal_strength,
                    'reason': f'Scalping: {sell_signals} sell signals, strength {signal_strength:.2f}',
                    'signals_count': sell_signals
                }
            
            return None  # No strong signal
            
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
        """Enhanced backtesting with realistic market conditions"""
        try:
            if historical_data.empty or len(historical_data) < 100:
                return {'error': 'Insufficient data for backtesting'}
            
            # Enhanced backtest parameters
            trades = []
            capital = initial_capital
            position = None
            max_drawdown = 0
            peak_capital = initial_capital
            
            # Trading costs (realistic for crypto)
            maker_fee = 0.001  # 0.1% maker fee
            taker_fee = 0.0015  # 0.15% taker fee
            slippage_factor = 0.0005  # 0.05% average slippage
            
            # Track metrics
            winning_trades = 0
            losing_trades = 0
            total_fees_paid = 0
            
            for i in range(50, len(historical_data)):
                current_data = historical_data.iloc[:i+1]
                market_data = {'dataframe': current_data}
                
                # Enhanced signal generation with AI mock
                signals = await self._generate_mock_ai_signals(current_data)
                
                if position is None:
                    # Look for entry
                    entry_signal = await self.get_entry_signal(symbol, market_data, signals, strategy)
                    
                    if entry_signal and capital > initial_capital * 0.1:  # Stop if capital too low
                        entry_price = entry_signal['entry_price']
                        
                        # Apply slippage to entry price
                        if entry_signal['signal'] == 'BUY':
                            actual_entry_price = entry_price * (1 + slippage_factor)
                        else:
                            actual_entry_price = entry_price * (1 - slippage_factor)
                        
                        # Dynamic position sizing based on volatility
                        volatility = self._calculate_recent_volatility(current_data)
                        base_position_pct = 0.1  # 10% base
                        volatility_adjusted_pct = base_position_pct * (1 - min(volatility * 2, 0.5))  # Reduce in high vol
                        
                        position_value = capital * volatility_adjusted_pct
                        position_size = position_value / actual_entry_price
                        
                        # Calculate entry fees
                        entry_fee = position_value * taker_fee
                        
                        position = {
                            'entry_price': actual_entry_price,
                            'side': entry_signal['signal'],
                            'size': position_size,
                            'entry_index': i,
                            'entry_fee': entry_fee,
                            'stop_loss': entry_signal.get('stop_loss'),
                            'take_profit': entry_signal.get('take_profit'),
                            'entry_time': current_data.index[i]
                        }
                        
                        capital -= entry_fee
                        total_fees_paid += entry_fee
                        
                else:
                    # Look for exit
                    current_price = current_data['close'].iloc[-1]
                    current_high = current_data['high'].iloc[-1]
                    current_low = current_data['low'].iloc[-1]
                    
                    exit_triggered = False
                    exit_reason = ""
                    exit_price = current_price
                    
                    # Check stop loss / take profit with realistic price movement
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
                    'rsi_oversold': [15, 20, 25],  # More extreme
                    'rsi_overbought': [75, 80, 85],  # More extreme  
                    'volume_threshold': [2.0, 2.5, 3.0],  # Higher volume
                    'min_signals': [4, 5, 6]  # More confirmation
                },
                'swing_trading': {
                    'sma_short': [15, 20, 25],
                    'sma_long': [40, 50, 60],
                    'rsi_threshold': [30, 35, 40],
                    'volume_confirmation': [1.2, 1.5, 1.8]
                },
                'trend_following': {
                    'ema_fast': [12, 15, 18],
                    'ema_slow': [26, 30, 35],
                    'trend_strength': [0.6, 0.7, 0.8],
                    'volume_filter': [1.1, 1.3, 1.5]
                },
                'mean_reversion': {
                    'bb_period': [18, 20, 22],
                    'bb_std': [1.8, 2.0, 2.2],
                    'rsi_extreme': [20, 25, 30],
                    'reversion_target': [0.5, 0.6, 0.7]
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
    
    def apply_optimized_parameters(self, strategy: str, optimized_params: Dict[str, Any]) -> None:
        """Apply optimized parameters to strategy"""
        try:
            if strategy in self.strategy_params and optimized_params:
                logger.info(f"🔧 Applying optimized parameters for {strategy}")
                logger.info(f"📊 Old params: {self.strategy_params[strategy]}")
                
                # Update strategy parameters
                self.strategy_params[strategy].update(optimized_params)
                
                logger.success(f"✅ New params applied: {self.strategy_params[strategy]}")
                
        except Exception as e:
            logger.error(f"❌ Failed to apply optimized parameters: {e}")
    
    def get_strategy_timeframe(self, strategy: str) -> str:
        """Get appropriate timeframe for strategy"""
        return self.strategy_timeframes.get(strategy, '1h')  # Default to 1h
    
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
    
    def _calculate_enhanced_indicators(self, df):
        """Calculate comprehensive technical indicators"""
        try:
            import pandas as pd
            import numpy as np
            
            indicators = {}
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs))
            
            # Moving Averages
            indicators['sma_10'] = df['close'].rolling(10).mean()
            indicators['sma_20'] = df['close'].rolling(20).mean()
            indicators['sma_50'] = df['close'].rolling(50).mean()
            indicators['ema_12'] = df['close'].ewm(span=12).mean()
            indicators['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
            indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            sma = df['close'].rolling(window=bb_period).mean()
            std = df['close'].rolling(window=bb_period).std()
            indicators['bb_upper'] = sma + (std * bb_std)
            indicators['bb_lower'] = sma - (std * bb_std)
            indicators['bb_middle'] = sma
            
            # ATR (Average True Range)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            indicators['atr'] = true_range.rolling(14).mean()
            
            # Stochastic Oscillator
            lowest_low = df['low'].rolling(14).min()
            highest_high = df['high'].rolling(14).max()
            indicators['stoch_k'] = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
            indicators['stoch_d'] = indicators['stoch_k'].rolling(3).mean()
            
            # Volume indicators
            indicators['volume_sma'] = df['volume'].rolling(20).mean()
            indicators['volume_ratio'] = df['volume'] / indicators['volume_sma']
            
            return indicators
            
        except Exception as e:
            logger.error(f"❌ Enhanced indicators calculation error: {e}")
            return {}
    
    def _calculate_recent_volatility(self, data, period=20):
        """Calculate recent volatility for position sizing"""
        try:
            if len(data) < period:
                return 0.02  # Default 2% volatility
            
            returns = data['close'].pct_change().dropna()
            recent_returns = returns.tail(period)
            volatility = recent_returns.std()
            
            return max(0.01, min(volatility, 0.1))  # Cap between 1% and 10%
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation error: {e}")
            return 0.02
    
    async def _generate_mock_ai_signals(self, data):
        """Generate mock AI signals for backtesting"""
        try:
            # Simple mock implementation
            if len(data) < 20:
                return {'confidence': 0.5, 'signals': []}
            
            # Calculate simple indicators for mock signals
            rsi = self._calculate_enhanced_indicators(data).get('rsi')
            if rsi is not None and len(rsi) > 0:
                current_rsi = rsi.iloc[-1]
                
                confidence = 0.6 + abs(50 - current_rsi) / 100  # Higher confidence away from 50
                signals = []
                
                if current_rsi < 35:
                    signals.append({'type': 'BUY', 'strength': 0.7})
                elif current_rsi > 65:
                    signals.append({'type': 'SELL', 'strength': 0.7})
                
                return {'confidence': min(confidence, 0.9), 'signals': signals}
            
            return {'confidence': 0.5, 'signals': []}
            
        except Exception as e:
            logger.error(f"❌ Mock AI signals error: {e}")
            return {'confidence': 0.5, 'signals': []}