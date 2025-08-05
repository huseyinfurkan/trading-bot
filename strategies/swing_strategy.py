import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from typing import Dict, Any, Tuple
import ta

class SwingStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config, "Swing")
        self.sma_short = 20
        self.sma_long = 50
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
    def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Swing trading için piyasa analizi"""
        if not self.validate_market_data(market_data):
            return {'signal': 'none', 'confidence': 0.0}
        
        analysis = {}
        
        # Moving Averages
        analysis['sma_short'] = ta.trend.SMAIndicator(market_data['close'], window=self.sma_short).sma_indicator().iloc[-1]
        analysis['sma_long'] = ta.trend.SMAIndicator(market_data['close'], window=self.sma_long).sma_indicator().iloc[-1]
        analysis['ema_12'] = ta.trend.EMAIndicator(market_data['close'], window=12).ema_indicator().iloc[-1]
        analysis['ema_26'] = ta.trend.EMAIndicator(market_data['close'], window=26).ema_indicator().iloc[-1]
        
        # RSI
        analysis['rsi'] = ta.momentum.RSIIndicator(market_data['close'], window=self.rsi_period).rsi().iloc[-1]
        
        # MACD
        macd = ta.trend.MACD(market_data['close'])
        analysis['macd'] = macd.macd().iloc[-1]
        analysis['macd_signal'] = macd.macd_signal().iloc[-1]
        analysis['macd_histogram'] = macd.macd_diff().iloc[-1]
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(market_data['high'], market_data['low'], market_data['close'])
        analysis['stoch_k'] = stoch.stoch().iloc[-1]
        analysis['stoch_d'] = stoch.stoch_signal().iloc[-1]
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(market_data['close'])
        analysis['bb_upper'] = bb.bollinger_hband().iloc[-1]
        analysis['bb_middle'] = bb.bollinger_mavg().iloc[-1]
        analysis['bb_lower'] = bb.bollinger_lband().iloc[-1]
        analysis['bb_width'] = (analysis['bb_upper'] - analysis['bb_lower']) / analysis['bb_middle']
        
        # Volume analysis
        analysis['volume_ma'] = market_data['volume'].rolling(20).mean().iloc[-1]
        analysis['current_volume'] = market_data['volume'].iloc[-1]
        analysis['volume_ratio'] = analysis['current_volume'] / analysis['volume_ma']
        
        # Price action
        analysis['current_price'] = market_data['close'].iloc[-1]
        analysis['price_change_1d'] = market_data['close'].pct_change().iloc[-1]
        analysis['price_change_5d'] = market_data['close'].pct_change(5).iloc[-1]
        analysis['price_change_20d'] = market_data['close'].pct_change(20).iloc[-1]
        
        # Support and Resistance
        analysis['support_level'] = market_data['low'].rolling(20).min().iloc[-1]
        analysis['resistance_level'] = market_data['high'].rolling(20).max().iloc[-1]
        analysis['price_to_support'] = (analysis['current_price'] - analysis['support_level']) / analysis['current_price']
        analysis['price_to_resistance'] = (analysis['resistance_level'] - analysis['current_price']) / analysis['current_price']
        
        # Trend strength
        analysis['adx'] = ta.trend.ADXIndicator(market_data['high'], market_data['low'], market_data['close']).adx().iloc[-1]
        
        # Volatility
        analysis['atr'] = ta.volatility.AverageTrueRange(market_data['high'], market_data['low'], market_data['close']).average_true_range().iloc[-1]
        
        # Signal generation
        analysis['signal'] = self._generate_signal(analysis)
        analysis['confidence'] = self._calculate_confidence(analysis)
        
        return analysis
    
    def _generate_signal(self, analysis: Dict[str, Any]) -> str:
        """Sinyal üretir"""
        # Trend analysis
        trend_bullish = (analysis['sma_short'] > analysis['sma_long'] and 
                        analysis['ema_12'] > analysis['ema_26'])
        
        trend_bearish = (analysis['sma_short'] < analysis['sma_long'] and 
                        analysis['ema_12'] < analysis['ema_26'])
        
        # RSI conditions
        rsi_oversold = analysis['rsi'] < self.rsi_oversold
        rsi_overbought = analysis['rsi'] > self.rsi_overbought
        
        # MACD conditions
        macd_bullish = analysis['macd'] > analysis['macd_signal']
        macd_histogram_positive = analysis['macd_histogram'] > 0
        
        # Stochastic conditions
        stoch_oversold = analysis['stoch_k'] < 20 and analysis['stoch_d'] < 20
        stoch_overbought = analysis['stoch_k'] > 80 and analysis['stoch_d'] > 80
        
        # Volume confirmation
        volume_confirmed = analysis['volume_ratio'] > 1.0
        
        # Support/Resistance levels
        near_support = analysis['price_to_support'] < 0.02  # %2 yakınlık
        near_resistance = analysis['price_to_resistance'] < 0.02
        
        # Trend strength
        strong_trend = analysis['adx'] > 25
        
        # Buy signal conditions
        if (trend_bullish and rsi_oversold and macd_bullish and 
            macd_histogram_positive and stoch_oversold and 
            volume_confirmed and near_support and strong_trend):
            return 'buy'
        
        # Sell signal conditions
        elif (trend_bearish and rsi_overbought and not macd_bullish and 
              not macd_histogram_positive and stoch_overbought and 
              volume_confirmed and near_resistance and strong_trend):
            return 'sell'
        
        return 'none'
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Sinyal güvenilirliğini hesaplar"""
        confidence = 0.5  # Base confidence
        
        # Trend strength confidence
        if analysis['adx'] > 30:
            confidence += 0.15
        
        # RSI confidence
        if analysis['rsi'] < 25 or analysis['rsi'] > 75:
            confidence += 0.1
        
        # MACD confidence
        if abs(analysis['macd_histogram']) > 0.005:
            confidence += 0.1
        
        # Volume confidence
        if analysis['volume_ratio'] > 1.5:
            confidence += 0.1
        
        # Support/Resistance confidence
        if analysis['price_to_support'] < 0.01 or analysis['price_to_resistance'] < 0.01:
            confidence += 0.1
        
        # Price momentum confidence
        if abs(analysis['price_change_5d']) > 0.05:
            confidence += 0.1
        
        # Bollinger Bands confidence
        if analysis['bb_width'] > 0.1:  # Volatilite yüksek
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def should_enter(self, analysis: Dict[str, Any]) -> Tuple[bool, float]:
        """Pozisyona girilip girilmeyeceğini belirler"""
        signal = analysis.get('signal', 'none')
        confidence = analysis.get('confidence', 0.0)
        
        should_enter = (signal in ['buy', 'sell'] and 
                       confidence >= self.config.MIN_CONFIDENCE_THRESHOLD)
        
        return should_enter, confidence
    
    def should_exit(self, analysis: Dict[str, Any], entry_price: float, current_price: float) -> Tuple[bool, str]:
        """Pozisyondan çıkılıp çıkılmayacağını belirler"""
        # Calculate profit/loss
        if entry_price > 0:
            pnl_percent = (current_price - entry_price) / entry_price
        else:
            pnl_percent = 0
        
        # Exit conditions for swing trading
        exit_reason = ""
        should_exit = False
        
        # Take profit
        if pnl_percent >= self.config.STRATEGIES['swing']['min_profit']:
            should_exit = True
            exit_reason = "take_profit"
        
        # Stop loss
        elif pnl_percent <= -self.config.STRATEGIES['swing']['max_loss']:
            should_exit = True
            exit_reason = "stop_loss"
        
        # Trend reversal
        trend_bullish = (analysis.get('sma_short', 0) > analysis.get('sma_long', 0))
        if not trend_bullish and pnl_percent > 0.02:  # %2 kar varsa trend değişiminde çık
            should_exit = True
            exit_reason = "trend_reversal"
        
        # RSI extreme levels
        rsi = analysis.get('rsi', 50)
        if rsi > 90 or rsi < 10:
            should_exit = True
            exit_reason = "rsi_extreme"
        
        # Support/Resistance break
        price_to_support = analysis.get('price_to_support', 0)
        price_to_resistance = analysis.get('price_to_resistance', 0)
        
        if price_to_support < -0.05 or price_to_resistance < -0.05:  # %5 kırılma
            should_exit = True
            exit_reason = "support_resistance_break"
        
        return should_exit, exit_reason
    
    def get_stop_loss(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Stop loss seviyesini belirler"""
        atr = analysis.get('atr', 0)
        if atr > 0:
            # ATR'nin 2 katı kadar stop loss
            stop_loss = entry_price - (atr * 2)
        else:
            # Sabit %3 stop loss
            stop_loss = entry_price * (1 - self.config.STRATEGIES['swing']['max_loss'])
        
        # Support level kontrolü
        support_level = analysis.get('support_level', 0)
        if support_level > 0 and support_level < stop_loss:
            stop_loss = support_level * 0.98  # Support'un %2 altında
        
        return stop_loss
    
    def get_take_profit(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Take profit seviyesini belirler"""
        atr = analysis.get('atr', 0)
        if atr > 0:
            # ATR'nin 3 katı kadar take profit
            take_profit = entry_price + (atr * 3)
        else:
            # Sabit %5 take profit
            take_profit = entry_price * (1 + self.config.STRATEGIES['swing']['min_profit'])
        
        # Resistance level kontrolü
        resistance_level = analysis.get('resistance_level', 0)
        if resistance_level > 0 and resistance_level < take_profit:
            take_profit = resistance_level * 0.98  # Resistance'un %2 altında
        
        return take_profit