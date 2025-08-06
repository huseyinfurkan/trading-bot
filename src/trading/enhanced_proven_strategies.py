"""
Enhanced Proven Trading Strategies
Based on research and quantitative analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


class EnhancedProvenStrategies:
    """Enhanced proven strategies based on research and quantitative analysis"""
    
    def __init__(self):
        """Initialize with research-backed strategies"""
        
        # Williams Alligator + Moving Average Strategy (3,452% return research)
        self.williams_ma_strategy = {
            'name': 'Williams Alligator + Moving Average',
            'timeframe': '4h',  # Proven on 4h and daily timeframes
            'description': 'Based on TradeDots research showing 3,452% return on ETH',
            'parameters': {
                # Williams Alligator (SMMA)
                'jaw_length': 13,      # 13-period SMMA
                'teeth_length': 8,     # 8-period SMMA  
                'lips_length': 5,      # 5-period SMMA
                
                # Moving Averages for momentum
                'fast_ma': 4,          # 4 SMA for ETH (4 and 10 for BTC)
                'slow_ma': 7,          # 7 SMA for ETH
                'trend_ma': 200,       # 200 SMA for trend filter
                
                # Offsets
                'jaw_offset': 8,
                'teeth_offset': 5,
                'lips_offset': 3
            }
        }
        
        # Bollinger Bands + RSI + Stochastic RSI Strategy (Research-backed)
        self.bb_rsi_stoch_strategy = {
            'name': 'Bollinger Bands + RSI + Stochastic RSI',
            'timeframe': '1h',  # Proven on 1h timeframe
            'description': 'Multi-indicator volatility and momentum strategy',
            'parameters': {
                # Bollinger Bands
                'bb_length': 20,
                'bb_std_dev': 3.0,     # 3 std dev for extreme conditions
                
                # RSI
                'rsi_length': 14,
                'rsi_oversold': 34,    # Research shows 34 better than 30
                'rsi_overbought': 66,  # Research shows 66 better than 70
                
                # Stochastic RSI
                'stoch_rsi_length': 14,
                'stoch_oversold': 20,
                'stoch_overbought': 80,
                
                # Risk Management
                'take_profit': 0.006,  # 0.60% take profit
                'stop_loss': 0.0025,   # 0.25% stop loss
                'max_trades_per_day': 1
            }
        }
        
        # ML-Enhanced Bollinger + MACD + RSI (8787% ROI research)
        self.ml_enhanced_strategy = {
            'name': 'ML-Enhanced BB + MACD + RSI',
            'timeframe': '1h',
            'description': 'Based on 8787% ROI research with ML optimization',
            'parameters': {
                # Bollinger Bands
                'bb_length': 20,
                'bb_std_dev': 2.0,
                
                # MACD
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                
                # RSI
                'rsi_length': 14,
                'rsi_long_min': 30,
                'rsi_long_max': 70,
                'rsi_short_min': 30,
                'rsi_short_max': 70,
                
                # ADX for trend strength
                'adx_length': 14,
                'adx_long_min': 20,
                'adx_long_max': 50,
                
                # EMA
                'ema_length': 21,
                
                # ATR for dynamic stops
                'atr_length': 14,
                'atr_multiplier': 2.5
            }
        }
        
        # 15-minute BTC ML Strategy (Flawless Victory - Sharpe 13.5)
        self.btc_ml_strategy = {
            'name': 'BTC ML Strategy (15min)',
            'timeframe': '15m',
            'description': 'Machine Learning optimized for Bitcoin 15-min timeframe',
            'parameters': {
                # Bollinger Bands (ML optimized)
                'bb_length': 20,
                'bb_std_dev': 1.0,     # 1 std dev for more sensitive signals
                
                # RSI (ML optimized thresholds)
                'rsi_length': 14,
                'rsi_buy_threshold': 35,    # ML found optimal levels
                'rsi_sell_threshold': 65,
                
                # Volume confirmation
                'volume_factor': 1.2,  # 20% above average volume
                
                # Risk Management
                'risk_reward_ratio': 2.0,  # 2:1 reward to risk
                'max_drawdown': 0.02      # 2% max drawdown per trade
            }
        }
        
        logger.info("🎯 Enhanced Proven Strategies initialized - 4 research-backed strategies")
    
    def get_williams_alligator_signal(self, data: pd.DataFrame, market_regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Williams Alligator + Moving Average Strategy (3,452% return)"""
        try:
            if len(data) < 200:  # Need enough data for 200 SMA
                return None
            
            params = self.williams_ma_strategy['parameters']
            
            # Calculate Williams Alligator (SMMA)
            jaw = self._calculate_smma(data['close'], params['jaw_length'])
            teeth = self._calculate_smma(data['close'], params['teeth_length'])  
            lips = self._calculate_smma(data['close'], params['lips_length'])
            
            # Calculate Moving Averages
            fast_ma = data['close'].rolling(params['fast_ma']).mean()
            slow_ma = data['close'].rolling(params['slow_ma']).mean()
            trend_ma = data['close'].rolling(params['trend_ma']).mean()
            
            current_price = data['close'].iloc[-1]
            
            # Entry Conditions (Research-based)
            above_trend = current_price > trend_ma.iloc[-1]
            
            # Long condition: Stacked alignment from top to bottom
            # fastMA > slowMA > lips > teeth > jaw
            long_alignment = (fast_ma.iloc[-1] > slow_ma.iloc[-1] and 
                            slow_ma.iloc[-1] > lips.iloc[-1] and
                            lips.iloc[-1] > teeth.iloc[-1] and 
                            teeth.iloc[-1] > jaw.iloc[-1])
            
            # Exit Conditions
            # 1. MA crossover + price below teeth
            ma_crossover = fast_ma.iloc[-1] < slow_ma.iloc[-1]
            below_teeth = current_price < teeth.iloc[-1]
            exit_signal_1 = ma_crossover and below_teeth
            
            # 2. Price below 200 SMA
            exit_signal_2 = current_price < trend_ma.iloc[-1]
            
            # 3. Reverse alignment: jaw > teeth > lips > slowMA > fastMA
            short_alignment = (jaw.iloc[-1] > teeth.iloc[-1] and
                             teeth.iloc[-1] > lips.iloc[-1] and
                             lips.iloc[-1] > slow_ma.iloc[-1] and
                             slow_ma.iloc[-1] > fast_ma.iloc[-1])
            
            # Generate signals
            if above_trend and long_alignment:
                # Calculate dynamic stop loss based on recent volatility
                atr = self._calculate_atr(data, 14)
                atr_current = atr.iloc[-1] if len(atr) > 0 else current_price * 0.02
                
                stop_distance = atr_current * 2.0
                target_distance = stop_distance * 2.5  # 2.5:1 reward/risk from research
                
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price - stop_distance,
                    'take_profit': current_price + target_distance,
                    'confidence': min(0.9, 0.7 + market_regime.get('confidence', 0) * 0.2),
                    'strategy': 'williams_alligator_ma',
                    'reason': 'Williams Alligator bullish alignment + trend confirmation',
                    'max_hold_hours': 24  # Research shows daily timeframe works best
                }
            
            elif exit_signal_1 or exit_signal_2 or short_alignment:
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price * 1.02,
                    'take_profit': current_price * 0.98,
                    'confidence': 0.8,
                    'strategy': 'williams_alligator_ma',
                    'reason': 'Williams Alligator exit conditions met',
                    'max_hold_hours': 24
                }
                
            return None
            
        except Exception as e:
            logger.error(f"❌ Williams Alligator strategy error: {e}")
            return None
    
    def get_bb_rsi_stoch_signal(self, data: pd.DataFrame, market_regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Bollinger Bands + RSI + Stochastic RSI Strategy"""
        try:
            if len(data) < 50:
                return None
            
            params = self.bb_rsi_stoch_strategy['parameters']
            
            # Calculate indicators
            bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(
                data['close'], params['bb_length'], params['bb_std_dev']
            )
            rsi = self._calculate_rsi(data['close'], params['rsi_length'])
            stoch_rsi = self._calculate_stochastic_rsi(data['close'], params['stoch_rsi_length'])
            
            current_price = data['close'].iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_stoch = stoch_rsi.iloc[-1]
            
            # Long signal: RSI < 34, Stoch RSI < 20, price <= lower BB
            long_condition = (current_rsi < params['rsi_oversold'] and 
                            current_stoch < params['stoch_oversold'] and
                            current_price <= bb_lower.iloc[-1])
            
            # Short signal: RSI > 66, Stoch RSI > 80, price >= upper BB  
            short_condition = (current_rsi > params['rsi_overbought'] and
                             current_stoch > params['stoch_overbought'] and
                             current_price >= bb_upper.iloc[-1])
            
            if long_condition:
                stop_loss = current_price * (1 - params['stop_loss'])
                take_profit = current_price * (1 + params['take_profit'])
                
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': 0.85,
                    'strategy': 'bb_rsi_stochastic',
                    'reason': f'Oversold: RSI {current_rsi:.1f}, StochRSI {current_stoch:.1f}, BB position',
                    'max_trades_per_day': params['max_trades_per_day']
                }
            
            elif short_condition:
                stop_loss = current_price * (1 + params['stop_loss'])
                take_profit = current_price * (1 - params['take_profit'])
                
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': 0.85,
                    'strategy': 'bb_rsi_stochastic',
                    'reason': f'Overbought: RSI {current_rsi:.1f}, StochRSI {current_stoch:.1f}, BB position',
                    'max_trades_per_day': params['max_trades_per_day']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ BB RSI Stochastic strategy error: {e}")
            return None
    
    def get_ml_enhanced_signal(self, data: pd.DataFrame, market_regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """ML-Enhanced BB + MACD + RSI Strategy (8787% ROI)"""
        try:
            if len(data) < 50:
                return None
            
            params = self.ml_enhanced_strategy['parameters']
            
            # Calculate indicators
            bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(
                data['close'], params['bb_length'], params['bb_std_dev']
            )
            macd_line, macd_signal, _ = self._calculate_macd(data['close'])
            rsi = self._calculate_rsi(data['close'], params['rsi_length'])
            adx = self._calculate_adx(data, params['adx_length'])
            ema = data['close'].ewm(span=params['ema_length']).mean()
            atr = self._calculate_atr(data, params['atr_length'])
            
            current_price = data['close'].iloc[-1]
            volume_mean = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            # ML-optimized conditions from 8787% ROI research
            
            # Long conditions
            rsi_long_ok = params['rsi_long_min'] < rsi.iloc[-1] < params['rsi_long_max']
            above_lower_bb = current_price > bb_lower.iloc[-1]
            macd_bullish = macd_line.iloc[-1] > macd_signal.iloc[-1]
            adx_strength = params['adx_long_min'] < adx.iloc[-1] < params['adx_long_max']
            volume_confirmation = current_volume > volume_mean
            
            long_condition = (rsi_long_ok and above_lower_bb and macd_bullish and 
                            adx_strength and volume_confirmation)
            
            # Short conditions  
            rsi_short_ok = params['rsi_short_min'] < rsi.iloc[-1] < params['rsi_short_max']
            below_upper_bb = current_price < bb_upper.iloc[-1]
            macd_bearish = macd_line.iloc[-1] < macd_signal.iloc[-1]
            adx_strength_short = params['adx_long_min'] < adx.iloc[-1] < params['adx_long_max']
            volume_confirmation_short = current_volume > volume_mean
            
            short_condition = (rsi_short_ok and below_upper_bb and macd_bearish and
                             adx_strength_short and volume_confirmation_short)
            
            if long_condition:
                # Dynamic stop based on ATR (research-backed)
                atr_current = atr.iloc[-1] if len(atr) > 0 else current_price * 0.02
                stop_distance = atr_current * params['atr_multiplier']
                
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': ema.iloc[-1] - stop_distance,  # EMA-based stop
                    'take_profit': current_price + (stop_distance * 2),  # 2:1 R/R
                    'confidence': 0.9,
                    'strategy': 'ml_enhanced_bb_macd_rsi',
                    'reason': 'ML-optimized multi-indicator bullish confluence',
                    'max_hold_hours': 24
                }
            
            elif short_condition:
                atr_current = atr.iloc[-1] if len(atr) > 0 else current_price * 0.02
                stop_distance = atr_current * params['atr_multiplier']
                
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': ema.iloc[-1] + stop_distance,
                    'take_profit': current_price - (stop_distance * 2),
                    'confidence': 0.9,
                    'strategy': 'ml_enhanced_bb_macd_rsi',
                    'reason': 'ML-optimized multi-indicator bearish confluence',
                    'max_hold_hours': 24
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ ML Enhanced strategy error: {e}")
            return None
    
    def get_btc_ml_15m_signal(self, data: pd.DataFrame, market_regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """15-minute BTC ML Strategy (Sharpe 13.5)"""
        try:
            if len(data) < 50:
                return None
            
            params = self.btc_ml_strategy['parameters']
            
            # Calculate indicators (ML optimized for 15m BTC)
            bb_upper, bb_lower, bb_middle = self._calculate_bollinger_bands(
                data['close'], params['bb_length'], params['bb_std_dev']
            )
            rsi = self._calculate_rsi(data['close'], params['rsi_length'])
            
            current_price = data['close'].iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            # Volume confirmation (ML found this crucial for BTC 15m)
            volume_mean = data['volume'].rolling(20).mean().iloc[-1]
            volume_ok = data['volume'].iloc[-1] > volume_mean * params['volume_factor']
            
            # ML-optimized entry conditions for BTC 15m
            # Buy: RSI > 35, close < lower BB (1 std dev), volume confirmation
            buy_condition = (current_rsi > params['rsi_buy_threshold'] and
                           current_price <= bb_lower.iloc[-1] and
                           volume_ok)
            
            # Sell: RSI < 65, close > upper BB (1 std dev), volume confirmation
            sell_condition = (current_rsi < params['rsi_sell_threshold'] and
                            current_price >= bb_upper.iloc[-1] and
                            volume_ok)
            
            if buy_condition:
                # ML-optimized risk management for 15m timeframe
                risk_amount = current_price * params['max_drawdown']
                take_profit = current_price + (risk_amount * params['risk_reward_ratio'])
                
                return {
                    'signal': 'BUY',
                    'entry_price': current_price,
                    'stop_loss': current_price - risk_amount,
                    'take_profit': take_profit,
                    'confidence': 0.95,  # High confidence from ML optimization
                    'strategy': 'btc_ml_15m',
                    'reason': f'BTC 15m ML signal: RSI {current_rsi:.1f}, BB breakout, volume {volume_ok}',
                    'max_hold_hours': 4  # 15m strategy - shorter holds
                }
            
            elif sell_condition:
                risk_amount = current_price * params['max_drawdown']
                take_profit = current_price - (risk_amount * params['risk_reward_ratio'])
                
                return {
                    'signal': 'SELL',
                    'entry_price': current_price,
                    'stop_loss': current_price + risk_amount,
                    'take_profit': take_profit,
                    'confidence': 0.95,
                    'strategy': 'btc_ml_15m',
                    'reason': f'BTC 15m ML signal: RSI {current_rsi:.1f}, BB breakout, volume {volume_ok}',
                    'max_hold_hours': 4
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ BTC ML 15m strategy error: {e}")
            return None
    
    def select_best_strategy(self, symbol: str, timeframe: str, market_regime: Dict[str, Any]) -> str:
        """Select the best strategy based on symbol, timeframe, and market conditions"""
        
        volatility_score = market_regime.get('volatility_score', 0.025)
        trend_strength = market_regime.get('trend_strength', 0.02)
        
        # Strategy selection logic based on research
        if symbol == 'BTCUSDT' and timeframe == '15m':
            return 'btc_ml_15m'  # Optimized specifically for BTC 15m
        
        elif timeframe in ['4h', '1d']:
            return 'williams_alligator_ma'  # Research shows best on 4h+ timeframes
        
        elif volatility_score > 0.04:  # High volatility
            return 'bb_rsi_stochastic'  # Good for volatile conditions
        
        elif trend_strength > 0.05:  # Strong trending
            return 'ml_enhanced_bb_macd_rsi'  # Best for trending markets
        
        else:
            return 'bb_rsi_stochastic'  # Default safe choice
    
    # Helper methods for technical indicators
    def _calculate_smma(self, prices: pd.Series, length: int) -> pd.Series:
        """Calculate Smoothed Moving Average (SMMA) for Williams Alligator"""
        smma = pd.Series(index=prices.index, dtype=float)
        sma_initial = prices.rolling(length).mean()
        
        for i in range(len(prices)):
            if i < length:
                smma.iloc[i] = sma_initial.iloc[i]
            else:
                smma.iloc[i] = (smma.iloc[i-1] * (length - 1) + prices.iloc[i]) / length
        
        return smma
    
    def _calculate_stochastic_rsi(self, prices: pd.Series, length: int) -> pd.Series:
        """Calculate Stochastic RSI"""
        rsi = self._calculate_rsi(prices, length)
        stoch_rsi = pd.Series(index=prices.index, dtype=float)
        
        for i in range(length, len(rsi)):
            rsi_slice = rsi.iloc[i-length+1:i+1]
            min_rsi = rsi_slice.min()
            max_rsi = rsi_slice.max()
            
            if max_rsi != min_rsi:
                stoch_rsi.iloc[i] = (rsi.iloc[i] - min_rsi) / (max_rsi - min_rsi) * 100
            else:
                stoch_rsi.iloc[i] = 50
        
        return stoch_rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - macd_signal
        
        return macd_line, macd_signal, macd_histogram
    
    def _calculate_adx(self, data: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = pd.Series(np.where((high - high.shift()) > (low.shift() - low), 
                                   np.maximum(high - high.shift(), 0), 0), index=data.index)
        dm_minus = pd.Series(np.where((low.shift() - low) > (high - high.shift()), 
                                    np.maximum(low.shift() - low, 0), 0), index=data.index)
        
        # Smoothed values
        tr_smooth = tr.rolling(length).mean()
        dm_plus_smooth = dm_plus.rolling(length).mean()
        dm_minus_smooth = dm_minus.rolling(length).mean()
        
        # DI+ and DI-
        di_plus = 100 * dm_plus_smooth / tr_smooth
        di_minus = 100 * dm_minus_smooth / tr_smooth
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(length).mean()
        
        return adx
    
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