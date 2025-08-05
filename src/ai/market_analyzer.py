"""
Market Analyzer
Gerçek piyasa verisi analizi - yfinance ve ccxt entegrasyonu
"""

import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class MarketAnalyzer:
    """Gerçek market durumu analiz motoru"""
    
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
            market_data = await self._fetch_real_market_data()
            
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
            symbol_data = await self._fetch_symbol_data(symbol)
            
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
    
    async def _fetch_real_market_data(self) -> Optional[Dict[str, Any]]:
        """Gerçek market verilerini çek"""
        try:
            logger.debug("📡 Gerçek market data alınıyor...")
            
            market_data = {}
            
            # Fetch data for major cryptocurrencies using yfinance
            for symbol in self.major_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    
                    # Get historical data (last 30 days)
                    hist = ticker.history(period="30d", interval="1d")
                    
                    if hist.empty:
                        continue
                    
                    # Get current info
                    info = ticker.info
                    
                    # Calculate technical indicators
                    current_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    
                    # Moving averages
                    ma_7 = hist['Close'].rolling(7).mean().iloc[-1]
                    ma_20 = hist['Close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else current_price
                    
                    # Volatility
                    returns = hist['Close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252)  # Annualized volatility
                    
                    # RSI calculation
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    current_rsi = rsi.iloc[-1] if not rsi.empty else 50
                    
                    market_data[symbol] = {
                        'current_price': current_price,
                        'prev_price': prev_price,
                        'change_24h': current_price - prev_price,
                        'change_24h_pct': ((current_price - prev_price) / prev_price) * 100,
                        'volume': hist['Volume'].iloc[-1],
                        'volume_avg': hist['Volume'].rolling(7).mean().iloc[-1],
                        'ma_7': ma_7,
                        'ma_20': ma_20,
                        'volatility': volatility,
                        'rsi': current_rsi,
                        'market_cap': info.get('marketCap', 0),
                        'dataframe': hist,
                        'timestamp': datetime.now()
                    }
                    
                except Exception as e:
                    logger.warning(f"⚠️ {symbol} data fetch failed: {e}")
                    continue
            
            # Fetch additional market indicators
            market_data['market_summary'] = await self._get_market_summary()
            
            return market_data if market_data else None
                
        except Exception as e:
            logger.error(f"❌ Real market data fetch error: {e}")
            return None
    
    async def _fetch_symbol_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Belirli bir sembol için veri al"""
        try:
            # Convert crypto symbol to yfinance format
            yf_symbol = symbol.replace('USDT', '-USD').replace('BUSD', '-USD')
            
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="30d", interval="1h")
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            
            # Technical analysis
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24 * 365)  # Annualized volatility for hourly data
            
            # Moving averages
            ma_24 = hist['Close'].rolling(24).mean().iloc[-1]  # 24 hour MA
            ma_168 = hist['Close'].rolling(168).mean().iloc[-1] if len(hist) >= 168 else current_price  # 7 day MA
            
            # RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            return {
                'current_price': current_price,
                'ma_24': ma_24,
                'ma_168': ma_168,
                'volatility': volatility,
                'rsi': current_rsi,
                'volume': hist['Volume'].iloc[-1],
                'dataframe': hist
            }
            
        except Exception as e:
            logger.error(f"❌ Symbol data fetch error for {symbol}: {e}")
            return None
    
    async def _get_market_summary(self) -> Dict[str, Any]:
        """Genel piyasa özeti"""
        try:
            # Fetch major indices for market sentiment
            indices = {
                'SPY': '^GSPC',  # S&P 500
                'QQQ': '^IXIC',  # NASDAQ
                'DXY': 'DX-Y.NYB'  # Dollar Index
            }
            
            index_data = {}
            
            for name, symbol in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d", interval="1d")
                    
                    if not hist.empty:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                        change_pct = ((current - prev) / prev) * 100
                        
                        index_data[name] = {
                            'current': current,
                            'change_pct': change_pct
                        }
                        
                except Exception as e:
                    logger.warning(f"⚠️ Index {name} fetch failed: {e}")
                    continue
            
            return {
                'indices': index_data,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Market summary error: {e}")
            return {}
    
    async def _perform_comprehensive_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Kapsamlı piyasa analizi"""
        try:
            analysis_results = []
            total_market_cap = 0
            total_volume = 0
            bullish_count = 0
            bearish_count = 0
            
            # Analyze each major cryptocurrency
            for symbol, data in market_data.items():
                if symbol == 'market_summary':
                    continue
                
                change_pct = data.get('change_24h_pct', 0)
                rsi = data.get('rsi', 50)
                current_price = data.get('current_price', 0)
                ma_7 = data.get('ma_7', current_price)
                ma_20 = data.get('ma_20', current_price)
                volume_ratio = data.get('volume', 1) / max(data.get('volume_avg', 1), 1)
                
                # Individual analysis
                symbol_analysis = {
                    'symbol': symbol,
                    'trend': 'neutral',
                    'strength': 0.5,
                    'sentiment': 'neutral'
                }
                
                # Trend analysis
                if current_price > ma_7 > ma_20 and change_pct > 2:
                    symbol_analysis['trend'] = 'bullish'
                    symbol_analysis['strength'] = min(0.9, 0.6 + abs(change_pct) / 20)
                    bullish_count += 1
                elif current_price < ma_7 < ma_20 and change_pct < -2:
                    symbol_analysis['trend'] = 'bearish'
                    symbol_analysis['strength'] = min(0.9, 0.6 + abs(change_pct) / 20)
                    bearish_count += 1
                
                # RSI sentiment
                if rsi > 70:
                    symbol_analysis['sentiment'] = 'overbought'
                elif rsi < 30:
                    symbol_analysis['sentiment'] = 'oversold'
                
                analysis_results.append(symbol_analysis)
                total_market_cap += data.get('market_cap', 0)
                total_volume += data.get('volume', 0)
            
            # Overall market condition
            bullish_ratio = bullish_count / len(analysis_results) if analysis_results else 0
            bearish_ratio = bearish_count / len(analysis_results) if analysis_results else 0
            
            if bullish_ratio > 0.6:
                market_condition = 'bull_market'
                market_strength = 0.7 + (bullish_ratio - 0.6) * 0.75
            elif bearish_ratio > 0.6:
                market_condition = 'bear_market'
                market_strength = 0.7 + (bearish_ratio - 0.6) * 0.75
            else:
                market_condition = 'sideways_market'
                market_strength = 0.5
            
            # Volatility assessment
            avg_volatility = np.mean([data.get('volatility', 0.5) for symbol, data in market_data.items() if symbol != 'market_summary'])
            
            if avg_volatility > 0.8:
                volatility_level = 'high'
            elif avg_volatility < 0.3:
                volatility_level = 'low'
            else:
                volatility_level = 'normal'
            
            # Strategy recommendations
            recommended_strategies = []
            
            if market_condition == 'bull_market':
                if volatility_level == 'low':
                    recommended_strategies = ['trend_following', 'swing_trading']
                else:
                    recommended_strategies = ['scalping', 'momentum']
            elif market_condition == 'bear_market':
                recommended_strategies = ['mean_reversion', 'short_selling']
            else:
                recommended_strategies = ['swing_trading', 'range_trading']
            
            return {
                'condition': market_condition,
                'strength': market_strength,
                'volatility': volatility_level,
                'bullish_ratio': bullish_ratio,
                'bearish_ratio': bearish_ratio,
                'total_market_cap': total_market_cap,
                'total_volume': total_volume,
                'recommended_strategies': recommended_strategies,
                'individual_analysis': analysis_results,
                'confidence': 0.8 if len(analysis_results) >= 3 else 0.6,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive analysis error: {e}")
            return self._get_default_analysis()
    
    async def _analyze_symbol_condition(self, symbol: str, symbol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tek sembol için detaylı analiz"""
        try:
            current_price = symbol_data.get('current_price', 0)
            ma_24 = symbol_data.get('ma_24', current_price)
            ma_168 = symbol_data.get('ma_168', current_price)
            rsi = symbol_data.get('rsi', 50)
            volatility = symbol_data.get('volatility', 0.5)
            
            # Trend determination
            if current_price > ma_24 > ma_168:
                trend = 'bull_market'
                strength = 0.7
            elif current_price < ma_24 < ma_168:
                trend = 'bear_market'
                strength = 0.7
            else:
                trend = 'sideways_market'
                strength = 0.5
            
            # Volatility classification
            if volatility > 1.0:
                vol_level = 'high'
            elif volatility < 0.3:
                vol_level = 'low'
            else:
                vol_level = 'normal'
            
            # Strategy suggestions
            if trend == 'bull_market' and vol_level == 'low':
                strategies = ['trend_following', 'swing_trading']
            elif trend == 'bull_market' and vol_level == 'high':
                strategies = ['scalping']
            elif trend == 'bear_market':
                strategies = ['mean_reversion']
            else:
                strategies = ['swing_trading']
            
            # Confidence based on data quality
            confidence = 0.8 if symbol_data.get('dataframe') is not None else 0.6
            
            return {
                'trend': trend,
                'strength': strength,
                'volatility': vol_level,
                'rsi': rsi,
                'strategies': strategies,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"❌ Symbol condition analysis error: {e}")
            return {
                'trend': 'sideways_market',
                'strength': 0.5,
                'volatility': 'normal',
                'strategies': ['swing_trading'],
                'confidence': 0.3
            }
    
    def _is_cache_valid(self) -> bool:
        """Cache geçerliliğini kontrol et"""
        if self.last_update is None:
            return False
        
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed < self.cache_duration
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Varsayılan analiz sonucu"""
        return {
            'condition': 'sideways_market',
            'strength': 0.5,
            'volatility': 'normal',
            'bullish_ratio': 0.5,
            'bearish_ratio': 0.5,
            'recommended_strategies': ['swing_trading'],
            'confidence': 0.3,
            'timestamp': datetime.now()
        }
    
    async def get_fear_greed_index(self) -> int:
        """Fear & Greed Index'i al (basitleştirilmiş)"""
        try:
            # Bu gerçek bir API entegrasyonu olabilir
            # Şimdilik RSI bazlı basit hesaplama
            market_data = await self._fetch_real_market_data()
            
            if not market_data:
                return 50  # Neutral
            
            # Average RSI from major cryptocurrencies
            rsi_values = []
            for symbol, data in market_data.items():
                if symbol != 'market_summary' and 'rsi' in data:
                    rsi_values.append(data['rsi'])
            
            if not rsi_values:
                return 50
            
            avg_rsi = np.mean(rsi_values)
            
            # Convert RSI to Fear & Greed scale (0-100)
            # RSI 30 = Fear (25), RSI 70 = Greed (75)
            if avg_rsi <= 30:
                return 25  # Extreme Fear
            elif avg_rsi <= 45:
                return 40  # Fear
            elif avg_rsi <= 55:
                return 50  # Neutral
            elif avg_rsi <= 70:
                return 65  # Greed
            else:
                return 80  # Extreme Greed
                
        except Exception as e:
            logger.error(f"❌ Fear & Greed index error: {e}")
            return 50
    
    async def get_market_dominance(self) -> Dict[str, float]:
        """Market dominance hesapla"""
        try:
            market_data = await self._fetch_real_market_data()
            
            if not market_data:
                return {'BTC': 45.0, 'ETH': 20.0, 'Others': 35.0}
            
            total_cap = 0
            individual_caps = {}
            
            for symbol, data in market_data.items():
                if symbol != 'market_summary':
                    market_cap = data.get('market_cap', 0)
                    if market_cap > 0:
                        individual_caps[symbol] = market_cap
                        total_cap += market_cap
            
            if total_cap == 0:
                return {'BTC': 45.0, 'ETH': 20.0, 'Others': 35.0}
            
            # Calculate dominance percentages
            dominance = {}
            for symbol, cap in individual_caps.items():
                dominance[symbol] = (cap / total_cap) * 100
            
            return dominance
            
        except Exception as e:
            logger.error(f"❌ Market dominance error: {e}")
            return {'BTC': 45.0, 'ETH': 20.0, 'Others': 35.0}