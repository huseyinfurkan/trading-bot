"""
Market Analyzer
Piyasa durumu analizi ve trend tespiti
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class MarketAnalyzer:
    """Market durumu analiz motoru"""
    
    def __init__(self, market_config: Dict[str, Any], db_manager):
        """
        Args:
            market_config: Market analiz konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = market_config
        self.db_manager = db_manager
        
        # Major crypto symbols for market analysis
        self.major_symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD']
        self.crypto_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # Analysis parameters
        self.trend_period = 20
        self.volatility_window = 14
        self.dominance_threshold = 0.45
        self.fear_greed_levels = {'extreme_fear': 25, 'fear': 45, 'greed': 75, 'extreme_greed': 90}
        self.rsi_period = 14
        
        # Cache for market data
        self.market_cache = {}
        self.last_update = None
        self.cache_duration = 300  # 5 minutes
        
        logger.info("📊 Market Analyzer initialized")
    
    async def analyze_current_market(self) -> Dict[str, Any]:
        """Mevcut piyasa koşullarını analiz et"""
        try:
            logger.info("📊 Piyasa durumu analizi başlatılıyor...")
            
            # Check cache
            if self._is_cache_valid():
                logger.debug("📋 Cache'den piyasa verisi kullanılıyor")
                return self.market_cache.get('analysis', {})
            
            # Get real market data
            market_data = await self._fetch_market_data()
            
            if not market_data:
                logger.warning("⚠️ Market data alınamadı, varsayılan analiz döndürülüyor")
                return self._get_default_analysis()
            
            # Analyze market conditions
            analysis = await self._perform_comprehensive_analysis(market_data)
            
            # Cache the results
            self.market_cache['analysis'] = analysis
            self.market_cache['timestamp'] = datetime.now()
            self.last_update = datetime.now()
            
            logger.success(f"✅ Market analizi tamamlandı: {analysis['condition']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Market analiz hatası: {e}")
            return self._get_default_analysis()
    
    async def analyze_market_condition(self, symbol: str) -> Dict[str, Any]:
        """Belirli bir sembol için market koşulunu analiz et"""
        try:
            # Get general market analysis
            general_analysis = await self.analyze_current_market()
            
            # Get specific symbol data
            market_data = await self._fetch_market_data()
            symbol_data = market_data.get(symbol) if market_data else None
            
            if symbol_data is not None:
                # Specific symbol analysis
                symbol_analysis = await self._analyze_symbol_condition(symbol, symbol_data)
                
                # Combine with general market
                return {
                    'symbol': symbol,
                    'condition': symbol_analysis.get('trend', general_analysis.get('condition', 'unknown')),
                    'strength': symbol_analysis.get('strength', general_analysis.get('strength', 0.5)),
                    'volatility': symbol_analysis.get('volatility', general_analysis.get('volatility', 'normal')),
                    'recommended_strategies': symbol_analysis.get('strategies', general_analysis.get('recommended_strategies', [])),
                    'timestamp': datetime.now(),
                    'confidence': symbol_analysis.get('confidence', general_analysis.get('confidence', 0.5))
                }
            else:
                # Use general market analysis
                return {
                    'symbol': symbol,
                    'condition': general_analysis.get('condition', 'unknown'),
                    'strength': general_analysis.get('strength', 0.5),
                    'volatility': general_analysis.get('volatility', 'normal'),
                    'recommended_strategies': [],
                    'timestamp': datetime.now(),
                    'confidence': 0.5
                }
                
        except Exception as e:
            logger.error(f"❌ {symbol} market condition analiz hatası: {e}")
            return {
                'symbol': symbol,
                'condition': 'unknown',
                'strength': 0.5,
                'volatility': 'normal',
                'recommended_strategies': ['swing_trading'],
                'timestamp': datetime.now(),
                'confidence': 0.3
            }
    
    async def _fetch_market_data(self) -> Optional[Dict[str, Any]]:
        """Market verilerini çek"""
        try:
            # Mock implementation - gerçekte yfinance, ccxt vb. kullanılacak
            import random
            
            # Simulate market data for major symbols
            market_data = {}
            
            for symbol in self.crypto_symbols:
                base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 500
                
                # Generate mock OHLCV data
                current_price = base_price * (1 + random.uniform(-0.05, 0.05))
                
                market_data[symbol] = {
                    'close': current_price,
                    'open': current_price * (1 + random.uniform(-0.02, 0.02)),
                    'high': current_price * (1 + random.uniform(0, 0.03)),
                    'low': current_price * (1 + random.uniform(-0.03, 0)),
                    'volume': random.uniform(1000000, 10000000),
                    'timestamp': datetime.now(),
                    'change_24h': random.uniform(-10, 10),
                    'change_pct_24h': random.uniform(-15, 15)
                }
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Market data fetch error: {e}")
            return None
    
    async def _perform_comprehensive_analysis(self, market_data: Dict) -> Dict[str, Any]:
        """Kapsamlı market analizi gerçekleştir"""
        try:
            # Analyze major cryptos
            btc_data = market_data.get('BTCUSDT', {})
            eth_data = market_data.get('ETHUSDT', {})
            
            # Calculate overall market sentiment
            total_change = 0
            positive_coins = 0
            total_coins = 0
            
            for symbol, data in market_data.items():
                change_pct = data.get('change_pct_24h', 0)
                total_change += change_pct
                total_coins += 1
                
                if change_pct > 0:
                    positive_coins += 1
            
            avg_change = total_change / total_coins if total_coins > 0 else 0
            positive_ratio = positive_coins / total_coins if total_coins > 0 else 0.5
            
            # Determine market condition
            if avg_change > 5 and positive_ratio > 0.7:
                condition = 'bull_market'
                strength = min(0.9, avg_change / 10 + positive_ratio)
            elif avg_change < -5 and positive_ratio < 0.3:
                condition = 'bear_market'
                strength = min(0.9, abs(avg_change) / 10 + (1 - positive_ratio))
            else:
                condition = 'sideways_market'
                strength = 0.5
            
            # Volatility analysis
            volatility_sum = 0
            for symbol, data in market_data.items():
                vol = abs(data.get('change_pct_24h', 0))
                volatility_sum += vol
            
            avg_volatility = volatility_sum / len(market_data) if market_data else 5
            
            if avg_volatility > 10:
                volatility = 'high'
            elif avg_volatility > 5:
                volatility = 'elevated'
            elif avg_volatility > 2:
                volatility = 'normal'
            else:
                volatility = 'low'
            
            # Recommended strategies based on conditions
            strategies = []
            if condition == 'bull_market':
                strategies = ['trend_following', 'swing_trading']
            elif condition == 'bear_market':
                strategies = ['mean_reversion', 'swing_trading']
            else:
                strategies = ['scalping', 'swing_trading', 'mean_reversion']
            
            # Fear & Greed simulation
            fear_greed_score = 50 + avg_change * 2  # Simple simulation
            fear_greed_score = max(0, min(100, fear_greed_score))
            
            if fear_greed_score < 25:
                fear_greed = 'extreme_fear'
            elif fear_greed_score < 45:
                fear_greed = 'fear'
            elif fear_greed_score < 75:
                fear_greed = 'neutral'
            elif fear_greed_score < 90:
                fear_greed = 'greed'
            else:
                fear_greed = 'extreme_greed'
            
            return {
                'condition': condition,
                'strength': strength,
                'volatility': volatility,
                'avg_change_24h': avg_change,
                'positive_ratio': positive_ratio,
                'fear_greed_index': fear_greed_score,
                'fear_greed_label': fear_greed,
                'recommended_strategies': strategies,
                'btc_dominance': 0.45,  # Mock BTC dominance
                'total_market_cap': 2500000000000,  # Mock total market cap
                'confidence': min(0.9, strength),
                'analysis_time': datetime.now(),
                'data_quality': 'good' if len(market_data) >= 5 else 'limited'
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis error: {e}")
            return self._get_default_analysis()
    
    async def _analyze_symbol_condition(self, symbol: str, data: Dict) -> Dict[str, Any]:
        """Tek sembol için koşul analizi"""
        try:
            change_pct = data.get('change_pct_24h', 0)
            volume = data.get('volume', 0)
            
            # Trend analysis
            if change_pct > 3:
                trend = 'bull_market'
                strength = min(0.9, change_pct / 10)
            elif change_pct < -3:
                trend = 'bear_market'
                strength = min(0.9, abs(change_pct) / 10)
            else:
                trend = 'sideways_market'
                strength = 0.5
            
            # Volatility
            vol_level = abs(change_pct)
            if vol_level > 8:
                volatility = 'high'
            elif vol_level > 4:
                volatility = 'elevated'
            else:
                volatility = 'normal'
            
            # Strategy recommendations
            if trend == 'bull_market' and volatility == 'normal':
                strategies = ['trend_following', 'swing_trading']
            elif trend == 'bear_market':
                strategies = ['mean_reversion']
            elif volatility == 'high':
                strategies = ['scalping']
            else:
                strategies = ['swing_trading']
            
            return {
                'trend': trend,
                'strength': strength,
                'volatility': volatility,
                'strategies': strategies,
                'confidence': 0.7,
                'volume_indicator': 'high' if volume > 5000000 else 'normal'
            }
            
        except Exception as e:
            logger.error(f"❌ Symbol analysis error for {symbol}: {e}")
            return {
                'trend': 'sideways_market',
                'strength': 0.5,
                'volatility': 'normal',
                'strategies': ['swing_trading'],
                'confidence': 0.3
            }
    
    def _is_cache_valid(self) -> bool:
        """Cache geçerliliğini kontrol et"""
        if not self.last_update or 'timestamp' not in self.market_cache:
            return False
        
        cache_age = (datetime.now() - self.last_update).total_seconds()
        return cache_age < self.cache_duration
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Varsayılan market analizi"""
        return {
            'condition': 'sideways_market',
            'strength': 0.5,
            'volatility': 'normal',
            'avg_change_24h': 0,
            'positive_ratio': 0.5,
            'fear_greed_index': 50,
            'fear_greed_label': 'neutral',
            'recommended_strategies': ['swing_trading', 'mean_reversion'],
            'btc_dominance': 0.45,
            'total_market_cap': 2500000000000,
            'confidence': 0.3,
            'analysis_time': datetime.now(),
            'data_quality': 'limited'
        }
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Market özeti al"""
        try:
            analysis = await self.analyze_current_market()
            
            return {
                'overall_condition': analysis['condition'],
                'market_strength': analysis['strength'],
                'volatility_level': analysis['volatility'],
                'fear_greed': analysis['fear_greed_label'],
                'recommended_strategies': analysis['recommended_strategies'][:3],
                'last_update': analysis['analysis_time']
            }
            
        except Exception as e:
            logger.error(f"❌ Market summary error: {e}")
            return {
                'overall_condition': 'unknown',
                'market_strength': 0.5,
                'volatility_level': 'normal',
                'fear_greed': 'neutral',
                'recommended_strategies': ['swing_trading'],
                'last_update': datetime.now()
            }