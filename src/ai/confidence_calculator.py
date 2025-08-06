"""
Confidence Calculator
AI güven faktörü hesaplama sistemi
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class ConfidenceCalculator:
    """Güven faktörü hesaplama sistemi"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = ai_config
        self.db_manager = db_manager
        
        # Confidence parameters
        self.base_confidence = ai_config.get('base_confidence', 0.5)
        self.max_confidence = ai_config.get('max_confidence', 0.95)
        self.min_confidence = ai_config.get('min_confidence', 0.1)
        
        # Weight factors
        self.signal_weight = 0.3
        self.market_weight = 0.25
        self.technical_weight = 0.2
        self.volume_weight = 0.15
        self.historical_weight = 0.1
        
        # Historical performance tracking
        self.performance_history = {}
        self.signal_accuracy = {}
        
        logger.info("🎯 Confidence Calculator initialized")
        
    async def calculate_confidence(self, symbol: str, market_data: Dict[str, Any], 
                                 signals: Dict[str, Any], market_condition: Dict[str, Any]) -> float:
        """Ana güven faktörü hesaplama fonksiyonu"""
        try:
            # Base confidence from signal analysis
            signal_confidence = await self._calculate_signal_confidence(signals)
            
            # Market condition alignment
            market_alignment = await self._calculate_market_alignment(signals, market_condition)
            
            # Technical confluence
            technical_confluence = await self._calculate_technical_confluence(market_data, signals)
            
            # Volume confirmation
            volume_confirmation = await self._calculate_volume_confirmation(market_data, signals)
            
            # Historical performance
            historical_performance = await self._calculate_historical_performance(symbol)
            
            # Combined confidence
            total_confidence = (
                signal_confidence * self.signal_weight +
                market_alignment * self.market_weight +
                technical_confluence * self.technical_weight +
                volume_confirmation * self.volume_weight +
                historical_performance * self.historical_weight
            )
            
            # Apply bounds
            total_confidence = max(self.min_confidence, min(self.max_confidence, total_confidence))
            
            return total_confidence
            
        except Exception as e:
            logger.error(f"❌ Confidence calculation error: {e}")
            return self.base_confidence
    
    async def _calculate_signal_confidence(self, signals: Dict[str, Any]) -> float:
        """Sinyal güven faktörü"""
        try:
            signal_list = signals.get('signals', [])
            signal_confidence = signals.get('confidence', 0.5)
            signal_count = len(signal_list)
            
            if signal_count == 0:
                return 0.3
            
            # Signal strength average
            avg_strength = np.mean([s.get('strength', 0.5) for s in signal_list])
            
            # Signal agreement (same direction)
            buy_signals = sum(1 for s in signal_list if s.get('type') == 'BUY')
            sell_signals = sum(1 for s in signal_list if s.get('type') == 'SELL')
            
            agreement = max(buy_signals, sell_signals) / signal_count if signal_count > 0 else 0.5
            
            # Combine factors
            confidence = (signal_confidence * 0.4 + avg_strength * 0.4 + agreement * 0.2)
            
            return min(0.95, max(0.1, confidence))
            
        except Exception as e:
            logger.error(f"❌ Signal confidence error: {e}")
            return 0.5
    
    async def _calculate_market_alignment(self, signals: Dict[str, Any], market_condition: Dict[str, Any]) -> float:
        """Market koşulu uyumu"""
        try:
            market_cond = market_condition.get('condition', 'sideways_market')
            market_strength = market_condition.get('strength', 0.5)
            
            signal_list = signals.get('signals', [])
            if not signal_list:
                return 0.5
            
            # Determine signal direction
            buy_signals = sum(1 for s in signal_list if s.get('type') == 'BUY')
            sell_signals = sum(1 for s in signal_list if s.get('type') == 'SELL')
            
            signal_direction = 'BUY' if buy_signals > sell_signals else 'SELL' if sell_signals > buy_signals else 'NEUTRAL'
            
            # Market alignment scoring
            alignment_score = 0.5
            
            if market_cond == 'bull_market' and signal_direction == 'BUY':
                alignment_score = 0.8 + (market_strength * 0.2)
            elif market_cond == 'bear_market' and signal_direction == 'SELL':
                alignment_score = 0.8 + (market_strength * 0.2)
            elif market_cond == 'sideways_market':
                alignment_score = 0.6
            else:
                alignment_score = 0.3  # Contradictory signals
            
            return min(0.95, max(0.1, alignment_score))
            
        except Exception as e:
            logger.error(f"❌ Market alignment error: {e}")
            return 0.5
    
    async def _calculate_technical_confluence(self, market_data: Dict[str, Any], signals: Dict[str, Any]) -> float:
        """Teknik analiz uyumu"""
        try:
            dataframe = market_data.get('dataframe')
            if dataframe is None or len(dataframe) < 20:
                return 0.5
            
            # Simple technical confluence
            df = dataframe.copy()
            current_price = df['close'].iloc[-1]
            
            # Moving averages
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            sma_50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else sma_20
            
            # Price position relative to MAs
            above_sma20 = current_price > sma_20
            above_sma50 = current_price > sma_50
            sma_trend = sma_20 > sma_50
            
            # Technical confluence score
            confluence_factors = []
            
            # Trend alignment
            if above_sma20 and above_sma50 and sma_trend:
                confluence_factors.append(0.8)  # Strong bullish confluence
            elif not above_sma20 and not above_sma50 and not sma_trend:
                confluence_factors.append(0.8)  # Strong bearish confluence
            else:
                confluence_factors.append(0.5)  # Mixed signals
            
            # Volume confluence
            if 'volume' in df.columns:
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                current_volume = df['volume'].iloc[-1]
                volume_factor = min(1.0, current_volume / avg_volume) * 0.7 + 0.3
                confluence_factors.append(volume_factor)
            
            confluence_score = np.mean(confluence_factors)
            
            return min(0.95, max(0.1, confluence_score))
            
        except Exception as e:
            logger.error(f"❌ Technical confluence error: {e}")
            return 0.5
    
    async def _calculate_volume_confirmation(self, market_data: Dict[str, Any], signals: Dict[str, Any]) -> float:
        """Volume onayı"""
        try:
            dataframe = market_data.get('dataframe')
            if dataframe is None or 'volume' not in dataframe.columns or len(dataframe) < 10:
                return 0.5
            
            # Volume analysis
            df = dataframe.copy()
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(10).mean().iloc[-1]
            
            # Volume ratio
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Volume confirmation score
            if volume_ratio > 1.5:  # High volume
                volume_score = 0.8
            elif volume_ratio > 1.2:  # Above average volume
                volume_score = 0.7
            elif volume_ratio > 0.8:  # Normal volume
                volume_score = 0.6
            else:  # Low volume
                volume_score = 0.4
            
            return min(0.95, max(0.1, volume_score))
            
        except Exception as e:
            logger.error(f"❌ Volume confirmation error: {e}")
            return 0.5
    
    async def _calculate_historical_performance(self, symbol: str) -> float:
        """Geçmiş performans faktörü"""
        try:
            # Get historical accuracy for this symbol
            if symbol in self.signal_accuracy:
                accuracy = self.signal_accuracy[symbol]
                return min(0.95, max(0.1, accuracy))
            else:
                # Default for new symbols
                return 0.6
                
        except Exception as e:
            logger.error(f"❌ Historical performance error: {e}")
            return 0.6
    
    async def update_signal_accuracy(self, symbol: str, was_correct: bool) -> None:
        """Sinyal doğruluğunu güncelle"""
        try:
            if symbol not in self.signal_accuracy:
                self.signal_accuracy[symbol] = 0.5
            
            # Simple moving average update
            current_accuracy = self.signal_accuracy[symbol]
            new_accuracy = (current_accuracy * 0.9) + (1.0 if was_correct else 0.0) * 0.1
            
            self.signal_accuracy[symbol] = min(0.95, max(0.1, new_accuracy))
            
        except Exception as e:
            logger.error(f"❌ Signal accuracy update error: {e}")
    
    def get_confidence_breakdown(self, symbol: str, market_data: Dict[str, Any], 
                               signals: Dict[str, Any], market_condition: Dict[str, Any]) -> Dict[str, float]:
        """Güven faktörü detayları"""
        try:
            return {
                'signal_confidence': 0.7,  # Simplified
                'market_alignment': 0.6,
                'technical_confluence': 0.8,
                'volume_confirmation': 0.5,
                'historical_performance': self.signal_accuracy.get(symbol, 0.6)
            }
            
        except Exception as e:
            logger.error(f"❌ Confidence breakdown error: {e}")
            return {}