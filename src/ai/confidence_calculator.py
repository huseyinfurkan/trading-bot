"""
Confidence Calculator
AI sinyalleri için güven faktörü hesaplar ve doğrular
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class ConfidenceCalculator:
    """Güven faktörü hesaplayıcısı"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = ai_config
        self.db_manager = db_manager
        
        # Confidence thresholds
        self.min_confidence = ai_config.get('confidence_threshold', 0.75)
        self.signal_strength_min = ai_config.get('signal_strength_min', 0.65)
        
        # Weights for different factors
        self.technical_weight = ai_config.get('technical_weight', 0.5)
        self.sentiment_weight = ai_config.get('sentiment_weight', 0.3)
        self.fundamental_weight = ai_config.get('fundamental_weight', 0.2)
        
        # Historical performance tracking
        self.performance_history = {}
        self.signal_accuracy = {}
        
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
            volume_confirmation = await self._calculate_volume_confirmation(market_data)
            
            # Historical performance
            historical_performance = await self._get_historical_performance(symbol)
            
            # Time of day factor (some times are better for trading)
            time_factor = await self._calculate_time_factor()
            
            # Volatility adjustment
            volatility_factor = await self._calculate_volatility_factor(market_data)
            
            # Combine all factors
            confidence_factors = {
                'signal_confidence': signal_confidence,
                'market_alignment': market_alignment,
                'technical_confluence': technical_confluence,
                'volume_confirmation': volume_confirmation,
                'historical_performance': historical_performance,
                'time_factor': time_factor,
                'volatility_factor': volatility_factor
            }
            
            # Weighted combination
            final_confidence = await self._combine_confidence_factors(confidence_factors)
            
            # Apply risk adjustments
            adjusted_confidence = await self._apply_risk_adjustments(final_confidence, symbol, market_data)
            
            logger.debug(f"🔍 {symbol} Güven Faktörleri: {confidence_factors}")
            logger.debug(f"🎯 {symbol} Final Confidence: {adjusted_confidence:.3f}")
            
            return min(1.0, max(0.0, adjusted_confidence))
            
        except Exception as e:
            logger.error(f"❌ {symbol} güven hesaplama hatası: {e}")
            return 0.5  # Default moderate confidence
    
    async def _calculate_signal_confidence(self, signals: Dict[str, Any]) -> float:
        """Sinyal bazlı güven hesapla"""
        try:
            signal_list = signals.get('signals', [])
            
            if not signal_list:
                return 0.0
            
            # Signal count and agreement
            buy_signals = [s for s in signal_list if s.get('type') == 'BUY']
            sell_signals = [s for s in signal_list if s.get('type') == 'SELL']
            
            total_signals = len(signal_list)
            dominant_signals = max(len(buy_signals), len(sell_signals))
            
            # Agreement ratio
            agreement_ratio = dominant_signals / total_signals if total_signals > 0 else 0
            
            # Average signal strength
            avg_strength = np.mean([s.get('strength', 0) for s in signal_list])
            
            # Source diversity bonus
            sources = set(s.get('source', '') for s in signal_list)
            diversity_bonus = min(0.2, len(sources) * 0.05)
            
            # ML signal bonus
            ml_signals = [s for s in signal_list if 'ML' in s.get('source', '')]
            ml_bonus = min(0.15, len(ml_signals) * 0.05)
            
            base_confidence = agreement_ratio * avg_strength
            final_confidence = base_confidence + diversity_bonus + ml_bonus
            
            return min(1.0, final_confidence)
            
        except Exception as e:
            logger.error(f"❌ Sinyal güven hesaplama hatası: {e}")
            return 0.5
    
    async def _calculate_market_alignment(self, signals: Dict[str, Any], 
                                        market_condition: Dict[str, Any]) -> float:
        """Market koşulları ile sinyal uyumunu hesapla"""
        try:
            signal_list = signals.get('signals', [])
            market_cond = market_condition.get('condition', 'sideways')
            market_strength = market_condition.get('strength', 0.5)
            
            if not signal_list:
                return 0.5
            
            # Determine dominant signal direction
            buy_signals = [s for s in signal_list if s.get('type') == 'BUY']
            sell_signals = [s for s in signal_list if s.get('type') == 'SELL']
            
            if len(buy_signals) > len(sell_signals):
                signal_direction = 'bullish'
            elif len(sell_signals) > len(buy_signals):
                signal_direction = 'bearish'
            else:
                signal_direction = 'neutral'
            
            # Alignment scoring
            alignment_score = 0.5  # Default neutral
            
            if market_cond == 'bull_market':
                if signal_direction == 'bullish':
                    alignment_score = 0.8 + market_strength * 0.2
                elif signal_direction == 'bearish':
                    alignment_score = 0.2 - market_strength * 0.1
            
            elif market_cond == 'bear_market':
                if signal_direction == 'bearish':
                    alignment_score = 0.8 + market_strength * 0.2
                elif signal_direction == 'bullish':
                    alignment_score = 0.2 - market_strength * 0.1
            
            else:  # sideways market
                if signal_direction == 'neutral':
                    alignment_score = 0.7
                else:
                    # In sideways markets, contrarian signals can be good
                    alignment_score = 0.6
            
            return min(1.0, max(0.0, alignment_score))
            
        except Exception as e:
            logger.error(f"❌ Market alignment hesaplama hatası: {e}")
            return 0.5
    
    async def _calculate_technical_confluence(self, market_data: Dict[str, Any], 
                                           signals: Dict[str, Any]) -> float:
        """Technical indicator confluence hesapla"""
        try:
            df = market_data.get('dataframe')
            
            if df is None or df.empty:
                return 0.5
            
            latest = df.iloc[-1]
            
            # Support/Resistance levels
            support_resistance_score = 0.5
            
            # Trend alignment
            trend_alignment = 0.5
            try:
                # Simple trend check with multiple timeframes
                short_trend = latest['close'] > df['close'].rolling(10).mean().iloc[-1]
                medium_trend = latest['close'] > df['close'].rolling(50).mean().iloc[-1]
                
                if short_trend and medium_trend:
                    trend_alignment = 0.8
                elif not short_trend and not medium_trend:
                    trend_alignment = 0.8
                else:
                    trend_alignment = 0.3
            except:
                pass
            
            # Volume confirmation
            volume_conf = 0.5
            try:
                recent_volume = latest['volume']
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                
                if recent_volume > avg_volume * 1.2:
                    volume_conf = 0.8
                elif recent_volume < avg_volume * 0.8:
                    volume_conf = 0.3
            except:
                pass
            
            # RSI levels
            rsi_conf = 0.5
            try:
                # RSI will be calculated in signal filter
                # This is a placeholder
                import random
                rsi = random.uniform(30, 70)
                
                if 40 <= rsi <= 60:  # Neutral zone
                    rsi_conf = 0.7
                elif rsi < 30 or rsi > 70:  # Extreme zones
                    rsi_conf = 0.8
                else:
                    rsi_conf = 0.6
            except:
                pass
            
            # Combine technical factors
            technical_factors = [support_resistance_score, trend_alignment, volume_conf, rsi_conf]
            confluence_score = np.mean(technical_factors)
            
            return confluence_score
            
        except Exception as e:
            logger.error(f"❌ Technical confluence hesaplama hatası: {e}")
            return 0.5
    
    async def _calculate_volume_confirmation(self, market_data: Dict[str, Any]) -> float:
        """Volume confirmation hesapla"""
        try:
            df = market_data.get('dataframe')
            
            if df is None or df.empty:
                return 0.5
            
            latest = df.iloc[-1]
            
            # Volume trend analysis
            recent_volume = df['volume'].tail(5).mean()
            historical_volume = df['volume'].rolling(50).mean().iloc[-1]
            
            volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1.0
            
            # Price-volume relationship
            price_change = df['close'].pct_change().iloc[-1]
            volume_change = df['volume'].pct_change().iloc[-1]
            
            # Ideal: rising price with rising volume (bullish) or falling price with rising volume (bearish)
            pv_confirmation = 0.5
            
            if price_change > 0 and volume_change > 0:  # Bullish confirmation
                pv_confirmation = 0.8
            elif price_change < 0 and volume_change > 0:  # Bearish confirmation
                pv_confirmation = 0.8
            elif abs(price_change) < 0.01:  # Low price movement
                pv_confirmation = 0.6
            else:  # Divergence
                pv_confirmation = 0.3
            
            # Volume magnitude factor
            if volume_ratio > 1.5:
                magnitude_factor = 0.9
            elif volume_ratio > 1.2:
                magnitude_factor = 0.7
            elif volume_ratio < 0.8:
                magnitude_factor = 0.4
            else:
                magnitude_factor = 0.6
            
            final_volume_conf = (pv_confirmation + magnitude_factor) / 2
            
            return min(1.0, final_volume_conf)
            
        except Exception as e:
            logger.error(f"❌ Volume confirmation hesaplama hatası: {e}")
            return 0.5
    
    async def _get_historical_performance(self, symbol: str) -> float:
        """Historical performance based confidence"""
        try:
            # Bu fonksiyon geçmiş sinyal performansını analiz eder
            # Şimdilik basit bir simülasyon
            
            if symbol not in self.performance_history:
                # Initialize with neutral performance
                self.performance_history[symbol] = {
                    'total_signals': 0,
                    'successful_signals': 0,
                    'average_return': 0.0,
                    'last_updated': datetime.now()
                }
            
            performance = self.performance_history[symbol]
            
            if performance['total_signals'] == 0:
                return 0.6  # Default for new symbols
            
            success_rate = performance['successful_signals'] / performance['total_signals']
            
            # Convert success rate to confidence
            if success_rate > 0.7:
                return 0.9
            elif success_rate > 0.6:
                return 0.8
            elif success_rate > 0.5:
                return 0.7
            elif success_rate > 0.4:
                return 0.6
            else:
                return 0.4
                
        except Exception as e:
            logger.error(f"❌ Historical performance hesaplama hatası: {e}")
            return 0.6
    
    async def _calculate_time_factor(self) -> float:
        """Time of day factor"""
        try:
            now = datetime.now()
            hour = now.hour
            
            # Market hours considerations (crypto trades 24/7 but has patterns)
            # Higher activity during certain hours
            
            if 8 <= hour <= 12:  # Morning hours (high activity)
                return 0.8
            elif 13 <= hour <= 17:  # Afternoon (moderate activity)
                return 0.7
            elif 18 <= hour <= 22:  # Evening (high activity)
                return 0.8
            else:  # Night hours (lower activity)
                return 0.6
                
        except Exception as e:
            logger.error(f"❌ Time factor hesaplama hatası: {e}")
            return 0.7
    
    async def _calculate_volatility_factor(self, market_data: Dict[str, Any]) -> float:
        """Volatility based confidence adjustment"""
        try:
            df = market_data.get('dataframe')
            
            if df is None or df.empty:
                return 0.7
            
            # Calculate recent volatility
            returns = df['close'].pct_change().dropna()
            recent_vol = returns.tail(20).std()
            historical_vol = returns.std()
            
            vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
            
            # Moderate volatility is best for most strategies
            if 0.8 <= vol_ratio <= 1.2:  # Normal volatility
                return 0.8
            elif vol_ratio > 2.0:  # Very high volatility
                return 0.4
            elif vol_ratio < 0.5:  # Very low volatility
                return 0.5
            elif vol_ratio > 1.5:  # High volatility
                return 0.6
            else:  # Low-moderate volatility
                return 0.7
                
        except Exception as e:
            logger.error(f"❌ Volatility factor hesaplama hatası: {e}")
            return 0.7
    
    async def _combine_confidence_factors(self, factors: Dict[str, float]) -> float:
        """Güven faktörlerini birleştir"""
        try:
            # Weighted combination
            weights = {
                'signal_confidence': 0.25,
                'market_alignment': 0.20,
                'technical_confluence': 0.20,
                'volume_confirmation': 0.15,
                'historical_performance': 0.10,
                'time_factor': 0.05,
                'volatility_factor': 0.05
            }
            
            weighted_sum = 0
            total_weight = 0
            
            for factor_name, factor_value in factors.items():
                weight = weights.get(factor_name, 0.1)
                weighted_sum += factor_value * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.5
            
            final_confidence = weighted_sum / total_weight
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"❌ Faktör birleştirme hatası: {e}")
            return 0.5
    
    async def _apply_risk_adjustments(self, confidence: float, symbol: str, 
                                    market_data: Dict[str, Any]) -> float:
        """Risk bazlı güven ayarlamaları"""
        try:
            adjusted_confidence = confidence
            
            # Market cap adjustment (if available)
            # Larger cap coins get slightly higher confidence
            if 'BTC' in symbol or 'ETH' in symbol:
                adjusted_confidence *= 1.05
            
            # Spread adjustment
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            
            if bid > 0 and ask > 0:
                spread_pct = (ask - bid) / bid * 100
                
                if spread_pct > 0.5:  # High spread
                    adjusted_confidence *= 0.9
                elif spread_pct > 0.2:  # Moderate spread
                    adjusted_confidence *= 0.95
            
            # Recent performance penalty
            # If recent signals failed, reduce confidence
            
            return min(1.0, max(0.0, adjusted_confidence))
            
        except Exception as e:
            logger.error(f"❌ Risk ayarlama hatası: {e}")
            return confidence
    
    async def update_signal_performance(self, symbol: str, signal_id: str, 
                                      success: bool, return_pct: float) -> None:
        """Sinyal performansını güncelle"""
        try:
            if symbol not in self.performance_history:
                self.performance_history[symbol] = {
                    'total_signals': 0,
                    'successful_signals': 0,
                    'average_return': 0.0,
                    'last_updated': datetime.now()
                }
            
            performance = self.performance_history[symbol]
            
            # Update stats
            performance['total_signals'] += 1
            
            if success:
                performance['successful_signals'] += 1
            
            # Update average return
            current_avg = performance['average_return']
            total = performance['total_signals']
            
            performance['average_return'] = ((current_avg * (total - 1)) + return_pct) / total
            performance['last_updated'] = datetime.now()
            
            logger.info(f"📊 {symbol} performance güncellendi: {performance['successful_signals']}/{performance['total_signals']} başarılı")
            
        except Exception as e:
            logger.error(f"❌ Performance güncelleme hatası: {e}")
    
    def get_min_confidence_threshold(self) -> float:
        """Minimum güven eşiğini döndür"""
        return self.min_confidence
    
    async def is_confidence_sufficient(self, confidence: float, strategy: str) -> bool:
        """Güven seviyesinin yeterli olup olmadığını kontrol et"""
        try:
            # Strategy-specific thresholds
            strategy_thresholds = {
                'scalping': 0.8,  # Scalping requires high confidence
                'swing_trading': 0.7,
                'trend_following': 0.75,
                'mean_reversion': 0.65
            }
            
            required_confidence = strategy_thresholds.get(strategy, self.min_confidence)
            
            return confidence >= required_confidence
            
        except Exception as e:
            logger.error(f"❌ Güven kontrol hatası: {e}")
            return confidence >= self.min_confidence