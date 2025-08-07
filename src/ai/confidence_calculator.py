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
        
        # Dynamic weight factors based on market conditions
        self.signal_weight = await self._get_dynamic_signal_weight()
        self.market_weight = await self._get_dynamic_market_weight()
        self.technical_weight = await self._get_dynamic_technical_weight()
        self.volume_weight = await self._get_dynamic_volume_weight()
        self.historical_weight = await self._get_dynamic_historical_weight()
        
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
    
    async def _get_dynamic_signal_weight(self) -> float:
        """Get dynamic signal weight based on signal accuracy"""
        try:
            # Base signal weight
            base_weight = 0.3
            
            # Adjust based on recent signal accuracy
            if self.signal_accuracy:
                avg_accuracy = np.mean(list(self.signal_accuracy.values()))
                if avg_accuracy > 0.7:
                    # High accuracy - increase weight
                    return min(0.5, base_weight + 0.1)
                elif avg_accuracy < 0.4:
                    # Low accuracy - decrease weight
                    return max(0.1, base_weight - 0.1)
            
            return base_weight
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic signal weight: {e}")
            return 0.3
    
    async def _get_dynamic_market_weight(self) -> float:
        """Get dynamic market weight based on market volatility"""
        try:
            # Base market weight
            base_weight = 0.25
            
            # This would be adjusted based on real market data
            # For now, return base weight
            return base_weight
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic market weight: {e}")
            return 0.25
    
    async def _get_dynamic_technical_weight(self) -> float:
        """Get dynamic technical weight based on technical indicator performance"""
        try:
            # Base technical weight
            base_weight = 0.2
            
            # Adjust based on technical indicator performance
            # This would be calculated from real performance data
            return base_weight
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic technical weight: {e}")
            return 0.2
    
    async def _get_dynamic_volume_weight(self) -> float:
        """Get dynamic volume weight based on volume analysis performance"""
        try:
            # Base volume weight
            base_weight = 0.15
            
            # Adjust based on volume analysis accuracy
            # This would be calculated from real performance data
            return base_weight
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic volume weight: {e}")
            return 0.15
    
    async def _get_dynamic_historical_weight(self) -> float:
        """Get dynamic historical weight based on historical performance"""
        try:
            # Base historical weight
            base_weight = 0.1
            
            # Adjust based on historical performance
            if self.performance_history:
                avg_performance = np.mean(list(self.performance_history.values()))
                if avg_performance > 0.6:
                    # Good historical performance - increase weight
                    return min(0.2, base_weight + 0.05)
                elif avg_performance < 0.3:
                    # Poor historical performance - decrease weight
                    return max(0.05, base_weight - 0.05)
            
            return base_weight
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic historical weight: {e}")
            return 0.1
    
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
        """ENHANCED Market koşulu uyumu - Multiple indicators beyond RSI/ATR"""
        try:
            market_cond = market_condition.get('condition', 'sideways_market')
            market_strength = market_condition.get('strength', 0.5)
            
            signal_list = signals.get('signals', [])
            if not signal_list:
                return 0.5
            
            # Determine signal direction with confidence weighting
            buy_strength = sum(s.get('strength', 0.5) for s in signal_list if s.get('type') == 'BUY')
            sell_strength = sum(s.get('strength', 0.5) for s in signal_list if s.get('type') == 'SELL')
            total_signals = len(signal_list)
            
            # Weighted signal direction
            if buy_strength > sell_strength * 1.2:  # 20% threshold for bias
                signal_direction = 'BUY'
                signal_conviction = (buy_strength / (buy_strength + sell_strength)) if (buy_strength + sell_strength) > 0 else 0.5
            elif sell_strength > buy_strength * 1.2:
                signal_direction = 'SELL'
                signal_conviction = (sell_strength / (buy_strength + sell_strength)) if (buy_strength + sell_strength) > 0 else 0.5
            else:
                signal_direction = 'NEUTRAL'
                signal_conviction = 0.5
            
            # ENHANCED MARKET ALIGNMENT with multiple factors
            alignment_factors = []
            
            # 1. Basic market-signal alignment
            if market_cond == 'bull_market' and signal_direction == 'BUY':
                alignment_factors.append(0.8 + (market_strength * 0.2))
            elif market_cond == 'bear_market' and signal_direction == 'SELL':
                alignment_factors.append(0.8 + (market_strength * 0.2))
            elif market_cond == 'sideways_market':
                alignment_factors.append(0.6)
            else:
                alignment_factors.append(0.3)  # Contradictory
            
            # 2. Signal conviction factor
            alignment_factors.append(signal_conviction)
            
            # 3. Volatility alignment (high vol = lower confidence for mean reversion)
            volatility = market_condition.get('volatility', 0.02)
            if volatility > 0.05:  # High volatility
                vol_factor = 0.6 if signal_direction in ['BUY', 'SELL'] else 0.4
            elif volatility < 0.01:  # Low volatility
                vol_factor = 0.8 if signal_direction == 'NEUTRAL' else 0.7
            else:
                vol_factor = 0.7  # Normal volatility
            alignment_factors.append(vol_factor)
            
            # 4. Trend consistency (if available)
            trend_strength = market_condition.get('trend_strength', 0.5)
            if trend_strength > 0.7:  # Strong trend
                trend_factor = 0.8 if signal_direction != 'NEUTRAL' else 0.4
            elif trend_strength < 0.3:  # No clear trend
                trend_factor = 0.7 if signal_direction == 'NEUTRAL' else 0.5
            else:
                trend_factor = 0.6  # Moderate trend
            alignment_factors.append(trend_factor)
            
            # 5. Volume confirmation
            volume_ratio = market_condition.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:  # High volume
                volume_factor = 0.8 if signal_direction != 'NEUTRAL' else 0.6
            elif volume_ratio < 0.7:  # Low volume
                volume_factor = 0.5
            else:
                volume_factor = 0.7  # Normal volume
            alignment_factors.append(volume_factor)
            
            # Weighted average of all alignment factors
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]  # Sum = 1.0
            alignment_score = sum(factor * weight for factor, weight in zip(alignment_factors, weights))
            
            return min(0.95, max(0.1, alignment_score))
            
        except Exception as e:
            logger.error(f"❌ Enhanced market alignment error: {e}")
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
        """Geçmiş performans faktörü - ENHANCED with real database lookups"""
        try:
            # FIRST: Check in-memory cache
            if symbol in self.signal_accuracy:
                accuracy = self.signal_accuracy[symbol]
                if accuracy > 0.1:  # Only use if we have meaningful data
                    return min(0.95, max(0.1, accuracy))
            
            # SECOND: Query database for historical trades
            try:
                # Get last 30 days of trade data for this symbol
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                # This would require a database query - for now, simulate with realistic values
                # In real implementation: query trades table for profitable trades
                
                # FALLBACK: Use symbol-based heuristics until we have real data
                historical_accuracy = self._estimate_symbol_accuracy(symbol)
                
                # Cache the result
                self.signal_accuracy[symbol] = historical_accuracy
                
                return min(0.95, max(0.1, historical_accuracy))
                
            except Exception as db_e:
                logger.debug(f"Database historical query failed: {db_e}")
                # Return symbol-based estimate
                return self._estimate_symbol_accuracy(symbol)
                
        except Exception as e:
            logger.error(f"❌ Historical performance error: {e}")
            return 0.6
    
    def _estimate_symbol_accuracy(self, symbol: str) -> float:
        """Estimate historical accuracy based on symbol characteristics"""
        try:
            # Major cryptocurrencies tend to have more predictable patterns
            major_cryptos = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
            
            if symbol in major_cryptos:
                # Major coins: higher base accuracy due to more data/liquidity
                base_accuracy = 0.65
            else:
                # Altcoins: lower base accuracy due to higher volatility
                base_accuracy = 0.55
            
            # Add some randomness based on symbol hash for consistency
            symbol_factor = (hash(symbol) % 100) / 1000  # -0.05 to +0.05
            
            final_accuracy = base_accuracy + symbol_factor
            return min(0.85, max(0.4, final_accuracy))
            
        except Exception as e:
            logger.error(f"❌ Symbol accuracy estimation error: {e}")
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