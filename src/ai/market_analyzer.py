"""
Market Analyzer
Piyasa durumunu analiz eder ve uygun stratejileri belirler
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class MarketAnalyzer:
    """Piyasa durumu analizöru"""
    
    def __init__(self, market_config: Dict[str, Any], db_manager):
        """
        Args:
            market_config: Market koşulları konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = market_config
        self.db_manager = db_manager
        
        # Market conditions
        self.bull_config = market_config.get('bull_market', {})
        self.bear_config = market_config.get('bear_market', {})
        self.sideways_config = market_config.get('sideways_market', {})
        
        self.current_market_condition = 'sideways'
        self.market_strength = 0.0
        self.volatility_level = 'normal'
        
    async def analyze_current_market(self) -> Dict[str, Any]:
        """Mevcut market durumunu analiz et"""
        try:
            # Market verilerini topla (major pairs)
            major_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
            market_data = {}
            
            # Her pair için temel analizleri yap
            for pair in major_pairs:
                try:
                    # Historical data al (placeholder - gerçekte exchange'den alınacak)
                    # Bu fonksiyon exchange manager'dan veri alacak
                    pair_analysis = await self._analyze_pair_condition(pair)
                    market_data[pair] = pair_analysis
                except Exception as e:
                    logger.warning(f"⚠️ {pair} analiz hatası: {e}")
                    continue
            
            # Genel market durumunu belirle
            overall_condition = await self._determine_overall_market(market_data)
            
            # Volatilite seviyesini hesapla
            volatility = await self._calculate_market_volatility(market_data)
            
            # Market gücünü hesapla
            strength = await self._calculate_market_strength(market_data)
            
            # Recommended strategies
            recommended_strategies = await self._get_recommended_strategies(
                overall_condition, volatility, strength
            )
            
            result = {
                'condition': overall_condition,
                'strength': strength,
                'volatility': volatility,
                'pair_analysis': market_data,
                'recommended_strategies': recommended_strategies,
                'timestamp': datetime.now(),
                'confidence': await self._calculate_analysis_confidence(market_data)
            }
            
            # Current state'i güncelle
            self.current_market_condition = overall_condition
            self.market_strength = strength
            self.volatility_level = volatility
            
            logger.info(f"📊 Market Durum: {overall_condition}, Güç: {strength:.2f}, Volatilite: {volatility}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Market analiz hatası: {e}")
            return {
                'condition': 'sideways',
                'strength': 0.0,
                'volatility': 'normal',
                'recommended_strategies': ['mean_reversion'],
                'timestamp': datetime.now(),
                'confidence': 0.5
            }
    
    async def _analyze_pair_condition(self, pair: str) -> Dict[str, Any]:
        """Tek bir pair'in market durumunu analiz et"""
        try:
            # Placeholder - gerçekte market verisi alınacak
            # Simulated market analysis
            import random
            
            # Trend direction (-1 to 1)
            trend_direction = random.uniform(-1, 1)
            
            # Trend strength (0 to 1)  
            trend_strength = random.uniform(0, 1)
            
            # RSI simulation
            rsi = random.uniform(20, 80)
            
            # Volume analysis
            volume_ratio = random.uniform(0.5, 2.0)  # vs average
            
            # Volatility (ATR ratio)
            volatility_ratio = random.uniform(0.5, 2.5)
            
            # Determine condition
            if trend_strength > 0.6:
                if trend_direction > 0.3:
                    condition = 'bullish'
                elif trend_direction < -0.3:
                    condition = 'bearish'
                else:
                    condition = 'sideways'
            else:
                condition = 'sideways'
            
            return {
                'pair': pair,
                'condition': condition,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'rsi': rsi,
                'volume_ratio': volume_ratio,
                'volatility_ratio': volatility_ratio,
                'confidence': min(1.0, trend_strength + (volume_ratio - 1) * 0.2)
            }
            
        except Exception as e:
            logger.error(f"❌ {pair} analiz hatası: {e}")
            return {
                'pair': pair,
                'condition': 'sideways',
                'trend_direction': 0,
                'trend_strength': 0.5,
                'confidence': 0.5
            }
    
    async def _determine_overall_market(self, market_data: Dict[str, Any]) -> str:
        """Genel market durumunu belirle"""
        try:
            if not market_data:
                return 'sideways'
            
            # Her pair'in condition'ını al
            conditions = []
            weights = []
            
            for pair, data in market_data.items():
                condition = data.get('condition', 'sideways')
                confidence = data.get('confidence', 0.5)
                
                # BTC daha yüksek ağırlık
                weight = 0.5 if 'BTC' in pair else 0.25
                
                conditions.append(condition)
                weights.append(weight * confidence)
            
            # Ağırlıklı voting
            bullish_weight = sum(w for i, w in enumerate(weights) if conditions[i] == 'bullish')
            bearish_weight = sum(w for i, w in enumerate(weights) if conditions[i] == 'bearish')
            sideways_weight = sum(w for i, w in enumerate(weights) if conditions[i] == 'sideways')
            
            total_weight = bullish_weight + bearish_weight + sideways_weight
            
            if total_weight == 0:
                return 'sideways'
            
            # Normalize
            bullish_ratio = bullish_weight / total_weight
            bearish_ratio = bearish_weight / total_weight
            sideways_ratio = sideways_weight / total_weight
            
            # Threshold ile karar ver
            if bullish_ratio > 0.6:
                return 'bull_market'
            elif bearish_ratio > 0.6:
                return 'bear_market'
            else:
                return 'sideways_market'
                
        except Exception as e:
            logger.error(f"❌ Genel market belirleme hatası: {e}")
            return 'sideways_market'
    
    async def _calculate_market_volatility(self, market_data: Dict[str, Any]) -> str:
        """Market volatilitesini hesapla"""
        try:
            if not market_data:
                return 'normal'
            
            volatility_ratios = []
            for pair, data in market_data.items():
                vol_ratio = data.get('volatility_ratio', 1.0)
                volatility_ratios.append(vol_ratio)
            
            avg_volatility = np.mean(volatility_ratios)
            
            if avg_volatility > 1.5:
                return 'high'
            elif avg_volatility > 1.2:
                return 'elevated'
            elif avg_volatility < 0.8:
                return 'low'
            else:
                return 'normal'
                
        except Exception as e:
            logger.error(f"❌ Volatilite hesaplama hatası: {e}")
            return 'normal'
    
    async def _calculate_market_strength(self, market_data: Dict[str, Any]) -> float:
        """Market gücünü hesapla"""
        try:
            if not market_data:
                return 0.0
            
            strengths = []
            for pair, data in market_data.items():
                trend_strength = data.get('trend_strength', 0.5)
                trend_direction = data.get('trend_direction', 0)
                confidence = data.get('confidence', 0.5)
                
                # Directional strength
                directional_strength = abs(trend_direction) * trend_strength
                weighted_strength = directional_strength * confidence
                
                strengths.append(weighted_strength)
            
            return np.mean(strengths)
            
        except Exception as e:
            logger.error(f"❌ Market güç hesaplama hatası: {e}")
            return 0.0
    
    async def _get_recommended_strategies(self, condition: str, volatility: str, strength: float) -> List[str]:
        """Market koşullarına göre önerilen stratejileri belirle"""
        try:
            strategies = []
            
            # Base strategies by market condition
            if condition == 'bull_market':
                base_strategies = self.bull_config.get('strategies', ['trend_following', 'swing_trading'])
            elif condition == 'bear_market':
                base_strategies = self.bear_config.get('strategies', ['mean_reversion', 'scalping'])
            else:  # sideways
                base_strategies = self.sideways_config.get('strategies', ['mean_reversion', 'scalping'])
            
            strategies.extend(base_strategies)
            
            # Volatility based adjustments
            if volatility == 'high':
                if 'scalping' not in strategies:
                    strategies.append('scalping')
                # Remove long-term strategies in high volatility
                strategies = [s for s in strategies if s != 'trend_following']
            elif volatility == 'low':
                if 'trend_following' not in strategies and strength > 0.6:
                    strategies.append('trend_following')
                # Remove scalping in low volatility
                strategies = [s for s in strategies if s != 'scalping']
            
            # Strength based adjustments
            if strength > 0.8:
                if 'trend_following' not in strategies:
                    strategies.append('trend_following')
            elif strength < 0.3:
                if 'mean_reversion' not in strategies:
                    strategies.append('mean_reversion')
            
            # Ensure at least one strategy
            if not strategies:
                strategies = ['mean_reversion']
            
            return list(set(strategies))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"❌ Strateji önerisi hatası: {e}")
            return ['mean_reversion']
    
    async def _calculate_analysis_confidence(self, market_data: Dict[str, Any]) -> float:
        """Analiz güven seviyesini hesapla"""
        try:
            if not market_data:
                return 0.5
            
            confidences = []
            for pair, data in market_data.items():
                confidence = data.get('confidence', 0.5)
                confidences.append(confidence)
            
            # Average confidence
            avg_confidence = np.mean(confidences)
            
            # Bonus for consistency
            consistency_bonus = 1 - np.std(confidences) if len(confidences) > 1 else 0
            
            final_confidence = min(1.0, avg_confidence + consistency_bonus * 0.1)
            return final_confidence
            
        except Exception as e:
            logger.error(f"❌ Güven hesaplama hatası: {e}")
            return 0.5
    
    def get_current_market_condition(self) -> str:
        """Mevcut market durumunu döndür"""
        return self.current_market_condition
    
    def get_market_strength(self) -> float:
        """Market gücünü döndür"""
        return self.market_strength
    
    def get_volatility_level(self) -> str:
        """Volatilite seviyesini döndür"""
        return self.volatility_level
    
    async def is_good_time_to_trade(self, strategy: str) -> bool:
        """Belirli bir strateji için trading'in uygun olup olmadığını kontrol et"""
        try:
            current_condition = self.get_current_market_condition()
            current_volatility = self.get_volatility_level()
            current_strength = self.get_market_strength()
            
            # Strategy specific rules
            if strategy == 'scalping':
                # Scalping prefers high volatility
                return current_volatility in ['elevated', 'high']
            
            elif strategy == 'trend_following':
                # Trend following needs strong trends
                return current_strength > 0.6 and current_condition in ['bull_market', 'bear_market']
            
            elif strategy == 'swing_trading':
                # Swing trading works in trending markets with moderate volatility
                return current_condition != 'sideways_market' and current_volatility != 'high'
            
            elif strategy == 'mean_reversion':
                # Mean reversion works in sideways markets or high volatility
                return current_condition == 'sideways_market' or current_volatility == 'high'
            
            else:
                # Default: moderate conditions
                return current_volatility in ['normal', 'elevated'] and current_strength > 0.3
                
        except Exception as e:
            logger.error(f"❌ Trading uygunluk kontrolü hatası: {e}")
            return True  # Default to allow trading