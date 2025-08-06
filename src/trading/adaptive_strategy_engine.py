"""
Adaptive Strategy Engine - 2 Proven Strategies
Replaces the broken 4-strategy approach with 2 solid adaptive ones
"""

import numpy as np
import pandas as pd
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class AdaptiveStrategyEngine:
    """2 Adaptive Strategies that automatically adjust to market conditions"""
    
    def __init__(self, config: Dict, exchange_manager, ai_signal_filter):
        """Initialize with 2 adaptive strategies"""
        self.config = config
        self.exchange_manager = exchange_manager
        self.ai_signal_filter = ai_signal_filter
        
        # Only 2 strategies - proven ones
        self.strategies = {
            'volatility_breakout': {
                'name': 'Volatility Breakout',
                'timeframe': '15m',  # 15-minute for responsiveness
                'description': 'Trades volatility spikes in any direction',
                'market_conditions': ['high_volatility', 'sideways_with_spikes']
            },
            'mean_reversion_adaptive': {
                'name': 'Adaptive Mean Reversion', 
                'timeframe': '1h',   # 1-hour for stability
                'description': 'Mean reversion with dynamic thresholds',
                'market_conditions': ['sideways_market', 'low_volatility', 'ranging']
            }
        }
        
        # Adaptive parameters that change based on market
        self.adaptive_params = {
            'volatility_breakout': {
                'base_threshold': 0.015,     # 1.5% move
                'volume_multiplier': 2.0,    # 2x volume needed
                'atr_factor': 2.5,           # ATR multiplier for stops
                'max_hold_hours': 6          # Max position hold time
            },
            'mean_reversion_adaptive': {
                'bb_std_dev': 2.0,           # Bollinger Band standard deviations
                'rsi_extreme': 25,           # RSI extreme levels
                'reversion_target': 0.5,     # Target reversion (50% of BB)
                'max_hold_hours': 24         # Max position hold time
            }
        }
        
        logger.info("🎯 Adaptive Strategy Engine initialized - 2 proven strategies")
    
    async def analyze_market_regime(self, symbol: str) -> Dict[str, Any]:
        """REAL market regime analysis - not fake"""
        try:
            # Get different timeframes for comprehensive analysis
            data_1h = await self.exchange_manager.get_historical_data(symbol, '1h', 
                                                                     datetime.now() - timedelta(days=7), 
                                                                     datetime.now())
            data_15m = await self.exchange_manager.get_historical_data(symbol, '15m', 
                                                                      datetime.now() - timedelta(days=3), 
                                                                      datetime.now())
            
            if data_1h is None or len(data_1h) < 50:
                return self._default_market_regime()
            
            # Calculate REAL volatility metrics
            returns_1h = data_1h['close'].pct_change().dropna()
            volatility_1h = returns_1h.rolling(24).std().iloc[-1]  # 24-hour rolling volatility
            
            returns_15m = data_15m['close'].pct_change().dropna() if data_15m is not None else returns_1h
            volatility_15m = returns_15m.rolling(96).std().iloc[-1] if len(returns_15m) > 96 else volatility_1h  # 24-hour in 15m periods
            
            # Price movement analysis
            price_range_7d = (data_1h['high'].rolling(168).max().iloc[-1] - data_1h['low'].rolling(168).min().iloc[-1]) / data_1h['close'].iloc[-1]
            current_price = data_1h['close'].iloc[-1]
            sma_20 = data_1h['close'].rolling(20).mean().iloc[-1]
            
            # Volume analysis
            avg_volume = data_1h['volume'].rolling(24).mean().iloc[-1]
            current_volume = data_1h['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Market regime classification
            regime = self._classify_market_regime(volatility_1h, volatility_15m, price_range_7d, 
                                                current_price, sma_20, volume_ratio)
            
            logger.info(f"📊 {symbol} Market Regime: {regime['regime']} | Vol: {volatility_1h:.3f} | Range: {price_range_7d:.3f}")
            
            return regime
            
        except Exception as e:
            logger.error(f"❌ Market regime analysis error: {e}")
            return self._default_market_regime()
    
    def _classify_market_regime(self, vol_1h: float, vol_15m: float, price_range: float, 
                               current_price: float, sma_20: float, volume_ratio: float) -> Dict[str, Any]:
        """Classify market regime based on real metrics"""
        
        # Volatility classification
        if vol_1h > 0.04:  # > 4% daily volatility
            volatility_state = 'high'
        elif vol_1h > 0.02:  # 2-4% daily volatility  
            volatility_state = 'medium'
        else:  # < 2% daily volatility
            volatility_state = 'low'
        
        # Trend analysis
        price_vs_sma = (current_price - sma_20) / sma_20
        if abs(price_vs_sma) < 0.02:  # Within 2% of SMA
            trend_state = 'sideways'
        elif price_vs_sma > 0.05:  # > 5% above SMA
            trend_state = 'uptrend'
        elif price_vs_sma < -0.05:  # > 5% below SMA
            trend_state = 'downtrend'
        else:
            trend_state = 'weak_trend'
        
        # Overall regime
        if volatility_state == 'high' and volume_ratio > 1.5:
            regime = 'breakout_conditions'
            best_strategy = 'volatility_breakout'
        elif volatility_state == 'low' and trend_state == 'sideways':
            regime = 'mean_reversion_conditions'  
            best_strategy = 'mean_reversion_adaptive'
        elif volatility_state == 'medium':
            # Choose based on recent price action
            if vol_15m > vol_1h * 1.2:  # 15m vol higher than 1h - spikes
                regime = 'spike_conditions'
                best_strategy = 'volatility_breakout'
            else:
                regime = 'range_conditions'
                best_strategy = 'mean_reversion_adaptive'
        else:
            regime = 'neutral_conditions'
            best_strategy = 'mean_reversion_adaptive'  # Default to safer strategy
        
        return {
            'regime': regime,
            'best_strategy': best_strategy,
            'volatility_state': volatility_state,
            'trend_state': trend_state, 
            'volatility_score': vol_1h,
            'trend_strength': abs(price_vs_sma),
            'volume_activity': volume_ratio,
            'confidence': min(volume_ratio / 2.0, 1.0)  # Higher volume = higher confidence
        }
    
    def _default_market_regime(self) -> Dict[str, Any]:
        """Default regime when analysis fails"""
        return {
            'regime': 'neutral_conditions',
            'best_strategy': 'mean_reversion_adaptive',
            'volatility_state': 'medium',
            'trend_state': 'sideways',
            'volatility_score': 0.025,
            'trend_strength': 0.02,
            'volume_activity': 1.0,
            'confidence': 0.5
        }
    
    async def get_strategy_signal(self, symbol: str, market_regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get trading signal from the best strategy for current market regime"""
        try:
            strategy = market_regime['best_strategy']
            timeframe = self.strategies[strategy]['timeframe']
            
            # Get data for the specific strategy timeframe
            data = await self.exchange_manager.get_historical_data(
                symbol, timeframe, 
                datetime.now() - timedelta(days=5), 
                datetime.now()
            )
            
            if data is None or len(data) < 50:
                return None
            
            # Get AI signals (if available)
            ai_signals = {}
            if self.ai_signal_filter:
                try:
                    ai_signals = await self.ai_signal_filter.filter_signals(symbol, data)
                except:
                    ai_signals = {'confidence': 0.5, 'signals': []}
            
            # Route to appropriate strategy
            if strategy == 'volatility_breakout':
                return await self._volatility_breakout_signal(symbol, data, market_regime, ai_signals)
            elif strategy == 'mean_reversion_adaptive':
                return await self._mean_reversion_adaptive_signal(symbol, data, market_regime, ai_signals)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Strategy signal error: {e}")
            return None
    
    async def _volatility_breakout_signal(self, symbol: str, data: pd.DataFrame, 
                                        market_regime: Dict[str, Any], ai_signals: Dict) -> Optional[Dict[str, Any]]:
        """Volatility Breakout Strategy - trades spikes in volatile markets"""
        try:
            if len(data) < 50:
                return None
            
            current_price = data['close'].iloc[-1]
            
            # Calculate indicators
            returns = data['close'].pct_change()
            volatility = returns.rolling(20).std().iloc[-1]
            atr = self._calculate_atr(data, 14)
            volume_avg = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            # Adaptive parameters based on market regime
            params = self.adaptive_params['volatility_breakout'].copy()
            vol_factor = market_regime['volatility_score'] / 0.025  # Scale against 2.5% base
            params['base_threshold'] *= vol_factor
            params['volume_multiplier'] *= (2.0 - market_regime['confidence'])  # Lower confidence = higher volume needed
            
            # Signal conditions
            price_move_1 = abs(returns.iloc[-1])
            price_move_3 = abs((data['close'].iloc[-1] - data['close'].iloc[-4]) / data['close'].iloc[-4])
            volume_spike = current_volume / volume_avg if volume_avg > 0 else 1
            
            # Check for breakout conditions
            if (price_move_1 > params['base_threshold'] and 
                price_move_3 > params['base_threshold'] * 1.5 and
                volume_spike > params['volume_multiplier']):
                
                direction = 'BUY' if returns.iloc[-1] > 0 else 'SELL'
                
                # Dynamic stop and target based on ATR
                atr_current = atr.iloc[-1] if len(atr) > 0 else current_price * 0.02
                stop_distance = atr_current * params['atr_factor']
                target_distance = stop_distance * 2  # 2:1 reward/risk
                
                if direction == 'BUY':
                    stop_loss = current_price - stop_distance
                    take_profit = current_price + target_distance
                else:
                    stop_loss = current_price + stop_distance
                    take_profit = current_price - target_distance
                
                # Confidence based on multiple factors
                confidence = min(
                    market_regime['confidence'] + 
                    min(volume_spike / 3.0, 0.3) + 
                    min(price_move_1 / 0.02, 0.2),
                    0.95
                )
                
                return {
                    'signal': direction,
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': confidence,
                    'strategy': 'volatility_breakout',
                    'reason': f'Vol breakout: {price_move_1:.3f}% move, {volume_spike:.1f}x volume',
                    'max_hold_hours': params['max_hold_hours']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Volatility breakout signal error: {e}")
            return None
    
    async def _mean_reversion_adaptive_signal(self, symbol: str, data: pd.DataFrame,
                                            market_regime: Dict[str, Any], ai_signals: Dict) -> Optional[Dict[str, Any]]:
        """Adaptive Mean Reversion Strategy - trades back to mean in ranging markets"""
        try:
            if len(data) < 50:
                return None
            
            current_price = data['close'].iloc[-1]
            
            # Calculate indicators
            bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(data['close'], 20, 2.0)
            rsi = self._calculate_rsi(data['close'], 14)
            
            if len(bb_upper) == 0 or len(rsi) == 0:
                return None
            
            # Adaptive parameters
            params = self.adaptive_params['mean_reversion_adaptive'].copy()
            
            # Adjust RSI levels based on volatility
            vol_adjust = 1 + (market_regime['volatility_score'] - 0.025) * 10  # Scale volatility
            rsi_oversold = max(15, params['rsi_extreme'] - vol_adjust * 5)
            rsi_overbought = min(85, 100 - params['rsi_extreme'] + vol_adjust * 5)
            
            current_rsi = rsi.iloc[-1]
            bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
            
            # Mean reversion signals
            if current_rsi < rsi_oversold and bb_position < 0.2:  # Oversold + near lower BB
                direction = 'BUY'
                target_price = bb_middle.iloc[-1]
                stop_loss = current_price * 0.98  # 2% stop
                confidence = min(0.9, 0.5 + (rsi_oversold - current_rsi) / 20 + (0.2 - bb_position))
                
            elif current_rsi > rsi_overbought and bb_position > 0.8:  # Overbought + near upper BB
                direction = 'SELL'
                target_price = bb_middle.iloc[-1]
                stop_loss = current_price * 1.02  # 2% stop
                confidence = min(0.9, 0.5 + (current_rsi - rsi_overbought) / 20 + (bb_position - 0.8))
                
            else:
                return None
            
            # Add AI signal confirmation if available
            if ai_signals.get('confidence', 0) > 0.6:
                ai_direction = self._get_ai_direction(ai_signals)
                if ai_direction == direction:
                    confidence = min(0.95, confidence + 0.1)
                elif ai_direction and ai_direction != direction:
                    confidence *= 0.8  # Reduce confidence if AI disagrees
            
            return {
                'signal': direction,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': target_price,
                'confidence': confidence,
                'strategy': 'mean_reversion_adaptive',
                'reason': f'Mean reversion: RSI {current_rsi:.1f}, BB pos {bb_position:.2f}',
                'max_hold_hours': params['max_hold_hours']
            }
            
        except Exception as e:
            logger.error(f"❌ Mean reversion signal error: {e}")
            return None
    
    def _get_ai_direction(self, ai_signals: Dict) -> Optional[str]:
        """Extract AI signal direction"""
        signals = ai_signals.get('signals', [])
        if not signals:
            return None
        
        buy_signals = sum(1 for s in signals if s.get('type') == 'BUY')
        sell_signals = sum(1 for s in signals if s.get('type') == 'SELL')
        
        if buy_signals > sell_signals:
            return 'BUY'
        elif sell_signals > buy_signals:
            return 'SELL'
        return None
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower, sma
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    async def get_entry_signal(self, symbol: str, market_data: Dict, regime: str) -> Dict[str, Any]:
        """Get entry signal for given symbol and market regime"""
        try:
            # Get AI confidence first
            ai_analysis = await self.ai_signal_filter.filter_signal(symbol, market_data, regime)
            
            if ai_analysis['confidence'] < 0.6:  # Minimum confidence threshold
                return {'action': 'HOLD', 'confidence': ai_analysis['confidence'], 'reason': 'Low AI confidence'}
            
            # Route to appropriate strategy based on regime
            if regime in ['high_volatility', 'breakout_forming']:
                signal = await self._volatility_breakout_signal(symbol, market_data, ai_analysis)
            elif regime in ['mean_reversion_conditions', 'sideways_market', 'ranging']:
                signal = await self._mean_reversion_adaptive_signal(symbol, market_data, ai_analysis)
            else:
                return {'action': 'HOLD', 'confidence': 0.5, 'reason': f'Unknown regime: {regime}'}
            
            # Apply AI filter to final signal
            if signal['action'] != 'HOLD':
                signal['ai_confidence'] = ai_analysis['confidence']
                signal['combined_confidence'] = (signal['confidence'] + ai_analysis['confidence']) / 2
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error getting entry signal: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': f'Error: {str(e)}'}

    async def backtest_strategy(self, symbol: str, strategy_name: str, historical_data: pd.DataFrame, 
                              initial_capital: float = 10000) -> Dict[str, Any]:
        """
        Backtest a strategy on historical data
        NEW METHOD - Required by backtest_runner
        """
        try:
            # Map old strategy names to new adaptive ones
            strategy_mapping = {
                'scalping': 'volatility_breakout',
                'swing_trading': 'mean_reversion_adaptive', 
                'trend_following': 'volatility_breakout',
                'mean_reversion': 'mean_reversion_adaptive',
                # Direct new names
                'volatility_breakout': 'volatility_breakout',
                'mean_reversion_adaptive': 'mean_reversion_adaptive'
            }
            
            actual_strategy = strategy_mapping.get(strategy_name, 'mean_reversion_adaptive')
            
            logger.info(f"🔄 Backtesting {strategy_name} → {actual_strategy} on {symbol}")
            logger.info(f"📊 Data: {len(historical_data)} candles, Capital: ${initial_capital:,.2f}")
            
            # Initialize backtest variables
            capital = initial_capital
            position = None
            position_size = 0
            entry_price = 0
            trades = []
            equity_curve = []
            
            # Strategy-specific parameters
            if actual_strategy == 'volatility_breakout':
                params = self.adaptive_params['volatility_breakout']
            else:
                params = self.adaptive_params['mean_reversion_adaptive']
            
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
                    # Check for entry signal
                    if actual_strategy == 'volatility_breakout':
                        signal = await self._volatility_breakout_signal(symbol, market_data, {'confidence': 0.8})
                    else:
                        signal = await self._mean_reversion_adaptive_signal(symbol, market_data, {'confidence': 0.8})
                    
                    if signal['action'] == 'BUY' and signal['confidence'] > 0.7:
                        # Enter position
                        risk_per_trade = 0.02  # 2% risk per trade
                        position_value = capital * risk_per_trade * 5  # 5x leverage simulation
                        position_size = position_value / current_price
                        position = 'LONG'
                        entry_price = current_price
                        
                        logger.debug(f"📈 Entry: {symbol} @ ${current_price:.4f}, Size: {position_size:.6f}")
                
                else:  # Have position
                    # Check exit conditions
                    pnl_pct = (current_price - entry_price) / entry_price
                    
                    should_exit = False
                    exit_reason = ""
                    
                    # Profit target
                    if pnl_pct > 0.03:  # 3% profit
                        should_exit = True
                        exit_reason = "Profit target"
                    
                    # Stop loss
                    elif pnl_pct < -0.015:  # 1.5% loss
                        should_exit = True
                        exit_reason = "Stop loss"
                    
                    # Time-based exit
                    elif i - len([t for t in trades if t['exit_price'] == 0]) > params['max_hold_hours']:
                        should_exit = True
                        exit_reason = "Time limit"
                    
                    if should_exit:
                        # Exit position
                        pnl = position_size * (current_price - entry_price)
                        capital += pnl
                        
                        trade = {
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'pnl': pnl,
                            'pnl_pct': pnl_pct,
                            'reason': exit_reason,
                            'duration': i - len([t for t in trades if t['exit_price'] == 0])
                        }
                        trades.append(trade)
                        
                        logger.debug(f"📉 Exit: {symbol} @ ${current_price:.4f}, PnL: ${pnl:.2f} ({pnl_pct:.2%})")
                        
                        position = None
                        position_size = 0
                        entry_price = 0
                
                # Track equity
                current_equity = capital
                if position:
                    unrealized_pnl = position_size * (current_price - entry_price)
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