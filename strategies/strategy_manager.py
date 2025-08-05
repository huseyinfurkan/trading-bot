import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from .scalping_strategy import ScalpingStrategy
from .swing_strategy import SwingStrategy

class StrategyManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.strategies = {}
        self.market_conditions = {}
        self._initialize_strategies()
        
    def _initialize_strategies(self):
        """Stratejileri başlatır"""
        self.strategies['scalping'] = ScalpingStrategy(self.config)
        self.strategies['swing'] = SwingStrategy(self.config)
        
        self.logger.info("Stratejiler başlatıldı")
    
    def analyze_market_conditions(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Piyasa koşullarını analiz eder"""
        conditions = {}
        
        # Volatility analysis
        returns = market_data['close'].pct_change().dropna()
        conditions['volatility'] = returns.std()
        
        # Trend analysis
        sma_20 = market_data['close'].rolling(20).mean()
        sma_50 = market_data['close'].rolling(50).mean()
        current_trend = 'bullish' if sma_20.iloc[-1] > sma_50.iloc[-1] else 'bearish'
        conditions['trend'] = current_trend
        
        # Volume analysis
        volume_ma = market_data['volume'].rolling(20).mean()
        current_volume = market_data['volume'].iloc[-1]
        volume_trend = 'high' if current_volume > volume_ma.iloc[-1] * 1.5 else 'normal'
        conditions['volume'] = volume_trend
        
        # Price range analysis
        high_20 = market_data['high'].rolling(20).max()
        low_20 = market_data['low'].rolling(20).min()
        current_price = market_data['close'].iloc[-1]
        price_range = (high_20.iloc[-1] - low_20.iloc[-1]) / low_20.iloc[-1]
        
        if price_range < 0.05:  # %5'ten az range
            conditions['market_type'] = 'ranging'
        elif conditions['volatility'] > 0.03:  # %3'ten fazla volatilite
            conditions['market_type'] = 'volatile'
        elif current_trend == 'bullish' or current_trend == 'bearish':
            conditions['market_type'] = 'trending'
        else:
            conditions['market_type'] = 'stable'
        
        # RSI analysis
        rsi = self._calculate_rsi(market_data['close'])
        conditions['rsi'] = rsi.iloc[-1]
        
        # Market momentum
        momentum = market_data['close'].pct_change(5).iloc[-1]
        conditions['momentum'] = momentum
        
        self.market_conditions = conditions
        return conditions
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesaplar"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def select_strategy(self, market_conditions: Dict[str, Any]) -> str:
        """Piyasa koşullarına göre strateji seçer"""
        market_type = market_conditions.get('market_type', 'stable')
        volatility = market_conditions.get('volatility', 0)
        volume = market_conditions.get('volume', 'normal')
        
        # Strategy selection logic
        if market_type == 'volatile' and volatility > 0.04:
            return 'scalping'
        elif market_type == 'trending' and volume == 'high':
            return 'swing'
        elif market_type == 'ranging':
            return 'scalping'
        elif market_type == 'stable':
            return 'swing'
        else:
            # Default strategy based on time of day
            import datetime
            hour = datetime.datetime.now().hour
            if 9 <= hour <= 17:  # Market hours
                return 'scalping'
            else:
                return 'swing'
    
    def get_strategy_analysis(self, strategy_name: str, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Belirli bir strateji için analiz yapar"""
        if strategy_name not in self.strategies:
            self.logger.error(f"Strateji bulunamadı: {strategy_name}")
            return {}
        
        strategy = self.strategies[strategy_name]
        return strategy.analyze(market_data)
    
    def get_all_strategies_analysis(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Tüm strategiler için analiz yapar"""
        results = {}
        
        for strategy_name, strategy in self.strategies.items():
            if self.config.STRATEGIES[strategy_name]['enabled']:
                results[strategy_name] = strategy.analyze(market_data)
        
        return results
    
    def get_best_signal(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """En iyi sinyali belirler"""
        # Market conditions analizi
        market_conditions = self.analyze_market_conditions(market_data)
        
        # Uygun stratejiyi seç
        selected_strategy = self.select_strategy(market_conditions)
        
        # Seçilen strateji için analiz
        strategy_analysis = self.get_strategy_analysis(selected_strategy, market_data)
        
        # AI confidence ile birleştir
        best_signal = {
            'strategy': selected_strategy,
            'market_conditions': market_conditions,
            'analysis': strategy_analysis,
            'signal': strategy_analysis.get('signal', 'none'),
            'confidence': strategy_analysis.get('confidence', 0.0),
            'should_enter': False,
            'entry_confidence': 0.0
        }
        
        # Entry decision
        if selected_strategy in self.strategies:
            should_enter, entry_confidence = self.strategies[selected_strategy].should_enter(strategy_analysis)
            best_signal['should_enter'] = should_enter
            best_signal['entry_confidence'] = entry_confidence
        
        return best_signal
    
    def should_exit_position(self, strategy_name: str, analysis: Dict[str, Any], 
                           entry_price: float, current_price: float) -> tuple[bool, str]:
        """Pozisyondan çıkılması gerekip gerekmediğini kontrol eder"""
        if strategy_name not in self.strategies:
            return False, "strategy_not_found"
        
        strategy = self.strategies[strategy_name]
        return strategy.should_exit(analysis, entry_price, current_price)
    
    def get_risk_levels(self, strategy_name: str, entry_price: float, 
                       analysis: Dict[str, Any]) -> Dict[str, float]:
        """Risk seviyelerini hesaplar"""
        if strategy_name not in self.strategies:
            return {}
        
        strategy = self.strategies[strategy_name]
        
        return {
            'stop_loss': strategy.get_stop_loss(entry_price, analysis),
            'take_profit': strategy.get_take_profit(entry_price, analysis)
        }
    
    def get_strategy_performance(self, strategy_name: str) -> Dict[str, Any]:
        """Strateji performansını döndürür"""
        # Bu metod gerçek trading verilerinden performans hesaplayabilir
        # Şimdilik temel bilgileri döndürüyor
        return {
            'name': strategy_name,
            'enabled': self.config.STRATEGIES[strategy_name]['enabled'],
            'last_analysis': self.market_conditions
        }