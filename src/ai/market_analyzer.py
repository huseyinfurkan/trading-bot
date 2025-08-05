"""
Market Analyzer
Gerçek piyasa verilerini analiz eder ve market koşullarını belirler
"""

import numpy as np
import pandas as pd
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import yfinance as yf
from sklearn.preprocessing import StandardScaler


class MarketAnalyzer:
    """Piyasa durumu analizöru - Gerçek verilerle çalışır"""
    
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
        self.volatility_period = 14
        self.rsi_period = 14
        
        # Cache for market data
        self.market_cache = {}
        self.last_update = None
        self.cache_duration = 300  # 5 minutes
        
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
                logger.warning("⚠️ Piyasa verisi alınamadı, fallback analiz kullanılıyor")
                return self._fallback_analysis()
            
            # Analyze each major symbol
            symbol_analyses = {}
            for symbol in self.crypto_symbols:
                analysis = await self._analyze_symbol_condition(symbol, market_data.get(symbol))
                if analysis:
                    symbol_analyses[symbol] = analysis
            
            # Determine overall market condition
            overall_condition = self._determine_overall_market(symbol_analyses)
            
            # Calculate market metrics
            volatility = self._calculate_market_volatility(symbol_analyses)
            strength = self._calculate_market_strength(symbol_analyses)
            
            # Get recommended strategies
            recommended_strategies = self._get_recommended_strategies(
                overall_condition, volatility, strength
            )
            
            # Calculate confidence
            confidence = self._calculate_analysis_confidence(symbol_analyses)
            
            analysis_result = {
                'timestamp': datetime.now(),
                'condition': overall_condition,
                'volatility': volatility,
                'strength': strength,
                'confidence': confidence,
                'recommended_strategies': recommended_strategies,
                'symbol_analyses': symbol_analyses,
                'major_trends': self._get_major_trends(symbol_analyses)
            }
            
            # Update cache
            self.market_cache = {
                'analysis': analysis_result,
                'timestamp': datetime.now()
            }
            
            logger.info(f"✅ Piyasa analizi tamamlandı: {overall_condition} (güven: {confidence:.2f})")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Piyasa analizi hatası: {e}")
            return self._fallback_analysis()
    
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
                    'recommended_strategies': general_analysis.get('recommended_strategies', []),
                    'timestamp': datetime.now(),
                    'confidence': general_analysis.get('confidence', 0.5)
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
    
    async def _fetch_market_data(self) -> Dict[str, pd.DataFrame]:
        """Gerçek piyasa verilerini çek"""
        try:
            market_data = {}
            
            # Use yfinance for crypto data
            for symbol, yf_symbol in zip(self.crypto_symbols, self.major_symbols):
                try:
                    # Get last 100 periods of 1h data
                    ticker = yf.Ticker(yf_symbol)
                    data = ticker.history(period="5d", interval="1h")
                    
                    if not data.empty:
                        # Convert to our format
                        df = pd.DataFrame({
                            'timestamp': data.index,
                            'open': data['Open'].values,
                            'high': data['High'].values,
                            'low': data['Low'].values,
                            'close': data['Close'].values,
                            'volume': data['Volume'].values
                        })
                        
                        market_data[symbol] = df
                        logger.debug(f"✅ {symbol} verisi alındı: {len(df)} kayıt")
                    
                except Exception as e:
                    logger.warning(f"⚠️ {symbol} verisi alınamadı: {e}")
                    continue
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Market data çekme hatası: {e}")
            return {}
    
    async def _analyze_symbol_condition(self, symbol: str, data: Optional[pd.DataFrame]) -> Optional[Dict[str, Any]]:
        """Tek sembol için piyasa durumu analizi"""
        try:
            if data is None or len(data) < 50:
                return None
            
            df = data.copy()
            
            # Technical indicators
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Get latest values
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Trend analysis
            if latest['sma_20'] > latest['sma_50'] and latest['close'] > latest['sma_20']:
                trend = 'bullish'
                trend_strength = min(1.0, (latest['close'] - latest['sma_50']) / latest['sma_50'] * 10)
            elif latest['sma_20'] < latest['sma_50'] and latest['close'] < latest['sma_20']:
                trend = 'bearish'
                trend_strength = min(1.0, (latest['sma_50'] - latest['close']) / latest['sma_50'] * 10)
            else:
                trend = 'sideways'
                trend_strength = 0.3
            
            # Volatility (ATR proxy)
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            atr = df['tr'].rolling(14).mean().iloc[-1]
            volatility_pct = (atr / latest['close']) * 100
            
            if volatility_pct > 3:
                volatility_level = 'high'
            elif volatility_pct > 1.5:
                volatility_level = 'elevated'
            elif volatility_pct > 0.8:
                volatility_level = 'normal'
            else:
                volatility_level = 'low'
            
            # Market condition
            rsi = latest['rsi']
            macd_trend = latest['macd'] > latest['macd_signal']
            price_vs_bb = 'upper' if latest['close'] > latest['bb_upper'] else 'lower' if latest['close'] < latest['bb_lower'] else 'middle'
            
            if trend == 'bullish' and rsi < 70 and macd_trend:
                condition = 'bull_market'
            elif trend == 'bearish' and rsi > 30 and not macd_trend:
                condition = 'bear_market'
            else:
                condition = 'sideways_market'
            
            return {
                'symbol': symbol,
                'condition': condition,
                'trend': trend,
                'trend_strength': trend_strength,
                'volatility_level': volatility_level,
                'volatility_pct': volatility_pct,
                'rsi': rsi,
                'macd_bullish': macd_trend,
                'bb_position': price_vs_bb,
                'price': latest['close'],
                'volume': latest['volume'],
                'timestamp': latest['timestamp']
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} analiz hatası: {e}")
            return None
    
    def _determine_overall_market(self, symbol_analyses: Dict[str, Dict]) -> str:
        """Genel piyasa durumunu belirle"""
        try:
            if not symbol_analyses:
                return 'sideways_market'
            
            # Weight by importance (BTC has highest weight)
            weights = {
                'BTCUSDT': 0.4,
                'ETHUSDT': 0.25,
                'BNBUSDT': 0.15,
                'ADAUSDT': 0.1,
                'SOLUSDT': 0.1
            }
            
            bull_score = 0
            bear_score = 0
            total_weight = 0
            
            for symbol, analysis in symbol_analyses.items():
                weight = weights.get(symbol, 0.1)
                total_weight += weight
                
                if analysis['condition'] == 'bull_market':
                    bull_score += weight * analysis['trend_strength']
                elif analysis['condition'] == 'bear_market':
                    bear_score += weight * analysis['trend_strength']
            
            if total_weight > 0:
                bull_score /= total_weight
                bear_score /= total_weight
            
            if bull_score > 0.6:
                return 'bull_market'
            elif bear_score > 0.6:
                return 'bear_market'
            else:
                return 'sideways_market'
                
        except Exception as e:
            logger.error(f"❌ Genel market analizi hatası: {e}")
            return 'sideways_market'
    
    def _calculate_market_volatility(self, symbol_analyses: Dict[str, Dict]) -> str:
        """Piyasa volatilitesini hesapla"""
        try:
            if not symbol_analyses:
                return 'normal'
            
            volatilities = [analysis['volatility_pct'] for analysis in symbol_analyses.values()]
            avg_volatility = np.mean(volatilities)
            
            if avg_volatility > 3:
                return 'high'
            elif avg_volatility > 1.5:
                return 'elevated'
            elif avg_volatility > 0.8:
                return 'normal'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"❌ Volatilite hesaplama hatası: {e}")
            return 'normal'
    
    def _calculate_market_strength(self, symbol_analyses: Dict[str, Dict]) -> float:
        """Piyasa gücünü hesapla"""
        try:
            if not symbol_analyses:
                return 0.5
            
            strengths = [analysis['trend_strength'] for analysis in symbol_analyses.values()]
            return np.mean(strengths)
            
        except Exception as e:
            logger.error(f"❌ Market strength hesaplama hatası: {e}")
            return 0.5
    
    def _get_recommended_strategies(self, condition: str, volatility: str, strength: float) -> List[str]:
        """Önerilen stratejileri döndür"""
        try:
            strategies = []
            
            if condition == 'bull_market':
                strategies.extend(['trend_following', 'swing_trading'])
                if volatility in ['high', 'elevated']:
                    strategies.append('scalping')
            elif condition == 'bear_market':
                strategies.extend(['mean_reversion', 'swing_trading'])
                if strength > 0.6:
                    strategies.append('trend_following')
            else:  # sideways_market
                strategies.extend(['mean_reversion', 'scalping'])
                if volatility == 'normal':
                    strategies.append('swing_trading')
            
            return strategies
            
        except Exception as e:
            logger.error(f"❌ Strateji önerisi hatası: {e}")
            return ['swing_trading']
    
    def _calculate_analysis_confidence(self, symbol_analyses: Dict[str, Dict]) -> float:
        """Analiz güvenilirliğini hesapla"""
        try:
            if not symbol_analyses:
                return 0.5
            
            # Consensus among major symbols
            conditions = [analysis['condition'] for analysis in symbol_analyses.values()]
            most_common = max(set(conditions), key=conditions.count)
            consensus_ratio = conditions.count(most_common) / len(conditions)
            
            # Average trend strength
            avg_strength = np.mean([analysis['trend_strength'] for analysis in symbol_analyses.values()])
            
            # Data quality (number of analyzed symbols)
            data_quality = min(1.0, len(symbol_analyses) / len(self.crypto_symbols))
            
            confidence = (consensus_ratio * 0.5 + avg_strength * 0.3 + data_quality * 0.2)
            return min(1.0, max(0.1, confidence))
            
        except Exception as e:
            logger.error(f"❌ Güven hesaplama hatası: {e}")
            return 0.5
    
    def _get_major_trends(self, symbol_analyses: Dict[str, Dict]) -> Dict[str, str]:
        """Major trendleri döndür"""
        try:
            trends = {}
            for symbol, analysis in symbol_analyses.items():
                trends[symbol] = analysis['trend']
            return trends
            
        except Exception as e:
            logger.error(f"❌ Trend analizi hatası: {e}")
            return {}
    
    def _is_cache_valid(self) -> bool:
        """Cache geçerliliğini kontrol et"""
        if not self.market_cache or not self.last_update:
            return False
        
        cache_age = (datetime.now() - self.market_cache.get('timestamp', datetime.min)).total_seconds()
        return cache_age < self.cache_duration
    
    def _fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analiz (veri alınamadığında)"""
        return {
            'timestamp': datetime.now(),
            'condition': 'sideways_market',
            'volatility': 'normal',
            'strength': 0.5,
            'confidence': 0.3,
            'recommended_strategies': ['swing_trading', 'mean_reversion'],
            'symbol_analyses': {},
            'major_trends': {},
            'fallback': True
        }
    
    def get_current_market_condition(self) -> str:
        """Mevcut piyasa durumunu döndür"""
        if self.market_cache and self._is_cache_valid():
            return self.market_cache['analysis'].get('condition', 'sideways_market')
        return 'sideways_market'
    
    def get_market_strength(self) -> float:
        """Piyasa gücünü döndür"""
        if self.market_cache and self._is_cache_valid():
            return self.market_cache['analysis'].get('strength', 0.5)
        return 0.5
    
    def get_volatility_level(self) -> str:
        """Volatilite seviyesini döndür"""
        if self.market_cache and self._is_cache_valid():
            return self.market_cache['analysis'].get('volatility', 'normal')
        return 'normal'
    
    def is_good_time_to_trade(self, strategy: str) -> bool:
        """Trading için uygun zaman olup olmadığını kontrol et"""
        try:
            if not self.market_cache or not self._is_cache_valid():
                return False
            
            analysis = self.market_cache['analysis']
            recommended = analysis.get('recommended_strategies', [])
            confidence = analysis.get('confidence', 0)
            
            return strategy in recommended and confidence > 0.6
            
        except Exception as e:
            logger.error(f"❌ Trading time kontrolü hatası: {e}")
            return False