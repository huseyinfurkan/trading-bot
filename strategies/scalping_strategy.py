import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from typing import Dict, Any, Tuple
import ta

class ScalpingStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config, "Scalping")
        self.min_volume_threshold = 1000000  # Minimum hacim
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ema_fast = 9
        self.ema_slow = 21
        
    def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Scalping için piyasa analizi"""
        if not self.validate_market_data(market_data):
            return {'signal': 'none', 'confidence': 0.0}
        
        analysis = {}
        
        # RSI hesapla
        analysis['rsi'] = ta.momentum.RSIIndicator(market_data['close'], window=14).rsi().iloc[-1]
        
        # EMA hesapla
        analysis['ema_fast'] = ta.trend.EMAIndicator(market_data['close'], window=self.ema_fast).ema_indicator().iloc[-1]
        analysis['ema_slow'] = ta.trend.EMAIndicator(market_data['close'], window=self.ema_slow).ema_indicator().iloc[-1]
        
        # MACD hesapla
        macd = ta.trend.MACD(market_data['close'])
        analysis['macd'] = macd.macd().iloc[-1]
        analysis['macd_signal'] = macd.macd_signal().iloc[-1]
        analysis['macd_histogram'] = macd.macd_diff().iloc[-1]
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(market_data['close'])
        analysis['bb_upper'] = bb.bollinger_hband().iloc[-1]
        analysis['bb_middle'] = bb.bollinger_mavg().iloc[-1]
        analysis['bb_lower'] = bb.bollinger_lband().iloc[-1]
        analysis['bb_position'] = (market_data['close'].iloc[-1] - analysis['bb_lower']) / (analysis['bb_upper'] - analysis['bb_lower'])
        
        # Volume analysis
        analysis['volume_ma'] = market_data['volume'].rolling(20).mean().iloc[-1]
        analysis['current_volume'] = market_data['volume'].iloc[-1]
        analysis['volume_ratio'] = analysis['current_volume'] / analysis['volume_ma']
        
        # Price momentum
        analysis['price_change'] = market_data['close'].pct_change().iloc[-1]
        analysis['price_momentum'] = market_data['close'].pct_change(5).iloc[-1]
        
        # Volatility
        analysis['atr'] = ta.volatility.AverageTrueRange(market_data['high'], market_data['low'], market_data['close']).average_true_range().iloc[-1]
        
        # Current price
        analysis['current_price'] = market_data['close'].iloc[-1]
        
        # Signal generation
        analysis['signal'] = self._generate_signal(analysis)
        analysis['confidence'] = self._calculate_confidence(analysis)
        
        return analysis
    
    def _generate_signal(self, analysis: Dict[str, Any]) -> str:
        """Sinyal üretir"""
        # EMA crossover
        ema_bullish = analysis['ema_fast'] > analysis['ema_slow']
        
        # RSI conditions
        rsi_oversold = analysis['rsi'] < self.rsi_oversold
        rsi_overbought = analysis['rsi'] > self.rsi_overbought
        
        # MACD conditions
        macd_bullish = analysis['macd'] > analysis['macd_signal']
        macd_histogram_positive = analysis['macd_histogram'] > 0
        
        # Bollinger Bands
        bb_squeeze = analysis['bb_position'] < 0.2  # Lower band yakınında
        bb_expansion = analysis['bb_position'] > 0.8  # Upper band yakınında
        
        # Volume confirmation
        volume_confirmed = analysis['volume_ratio'] > 1.2
        
        # Buy signal conditions
        if (ema_bullish and rsi_oversold and macd_bullish and 
            macd_histogram_positive and bb_squeeze and volume_confirmed):
            return 'buy'
        
        # Sell signal conditions
        elif (not ema_bullish and rsi_overbought and not macd_bullish and 
              not macd_histogram_positive and bb_expansion and volume_confirmed):
            return 'sell'
        
        return 'none'
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Sinyal güvenilirliğini hesaplar"""
        confidence = 0.5  # Base confidence
        
        # RSI confidence
        if analysis['rsi'] < 20 or analysis['rsi'] > 80:
            confidence += 0.1
        
        # MACD confidence
        if abs(analysis['macd_histogram']) > 0.001:
            confidence += 0.1
        
        # Volume confidence
        if analysis['volume_ratio'] > 1.5:
            confidence += 0.1
        
        # Bollinger Bands confidence
        if analysis['bb_position'] < 0.1 or analysis['bb_position'] > 0.9:
            confidence += 0.1
        
        # Price momentum confidence
        if abs(analysis['price_momentum']) > 0.02:
            confidence += 0.1
        
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
        
        # Exit conditions for scalping
        exit_reason = ""
        should_exit = False
        
        # Take profit
        if pnl_percent >= self.config.STRATEGIES['scalping']['min_profit']:
            should_exit = True
            exit_reason = "take_profit"
        
        # Stop loss
        elif pnl_percent <= -self.config.STRATEGIES['scalping']['max_loss']:
            should_exit = True
            exit_reason = "stop_loss"
        
        # Signal reversal
        elif analysis.get('signal') == 'none':
            should_exit = True
            exit_reason = "signal_reversal"
        
        # RSI extreme levels
        rsi = analysis.get('rsi', 50)
        if rsi > 85 or rsi < 15:
            should_exit = True
            exit_reason = "rsi_extreme"
        
        return should_exit, exit_reason
    
    def get_stop_loss(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Stop loss seviyesini belirler"""
        atr = analysis.get('atr', 0)
        if atr > 0:
            # ATR'nin 1.5 katı kadar stop loss
            stop_loss = entry_price - (atr * 1.5)
        else:
            # Sabit %0.1 stop loss
            stop_loss = entry_price * (1 - self.config.STRATEGIES['scalping']['max_loss'])
        
        return stop_loss
    
    def get_take_profit(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Take profit seviyesini belirler"""
        atr = analysis.get('atr', 0)
        if atr > 0:
            # ATR'nin 2 katı kadar take profit
            take_profit = entry_price + (atr * 2)
        else:
            # Sabit %0.2 take profit
            take_profit = entry_price * (1 + self.config.STRATEGIES['scalping']['min_profit'])
        
        return take_profit