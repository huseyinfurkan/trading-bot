"""
Market Analyzer
Gerçek piyasa verisi analizi - yfinance ve ccxt entegrasyonu
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class MarketAnalyzer:
    """Gerçek market durumu analiz motoru"""
    
    def __init__(self, config, exchange_manager):
        """
        Args:
            config: Market analiz konfigürasyonu
            exchange_manager: Exchange manager
        """
        self.config = config
        self.exchange_manager = exchange_manager
        
        # Major crypto symbols for market analysis (CCXT format)
        self.major_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
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
    
    async def analyze_current_market(self) -> str:
        """
        ENHANCED REAL MARKET ANALYSIS
        Instead of fake analysis, perform comprehensive market assessment
        """
        try:
            logger.info("📊 Comprehensive market regime analysis başlatılıyor...")
            
            # Get market data for multiple symbols
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
            market_data = {}
            
            for symbol in symbols:
                try:
                    # Get 1h data for trend analysis
                    now = datetime.now()
                    data_1h = await self.exchange_manager.get_historical_data(
                        symbol=symbol,
                        timeframe='1h',
                        start_date=now - timedelta(days=3),
                        end_date=now
                    )
                    
                    # Get 15m data for short-term analysis  
                    data_15m = await self.exchange_manager.get_historical_data(
                        symbol=symbol,
                        timeframe='15m',
                        start_date=now - timedelta(days=1),
                        end_date=now
                    )
                    
                    if data_1h is not None and len(data_1h) > 20 and data_15m is not None and len(data_15m) > 50:
                        market_data[symbol] = {
                            'data_1h': data_1h,
                            'data_15m': data_15m
                        }
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not get data for {symbol}: {e}")
                    continue
            
            if not market_data:
                logger.warning("⚠️ No market data available, defaulting to sideways")
                return 'sideways_market'
            
            # Analyze multiple market characteristics
            market_metrics = []
            
            for symbol, data in market_data.items():
                metrics = await self._analyze_symbol_regime(symbol, data['data_1h'], data['data_15m'])
                market_metrics.append(metrics)
                
                logger.info(f"📈 {symbol} Analysis:")
                logger.info(f"   💨 Volatility: {metrics['volatility']:.1%} ({metrics['volatility_regime']})")
                logger.info(f"   📊 Trend: {metrics['trend_strength']:.1%} ({metrics['trend_direction']})")
                logger.info(f"   📉 Range: {metrics['range_pct']:.1%} ({metrics['range_regime']})")
                logger.info(f"   🔄 Regime: {metrics['local_regime']}")
            
            # Aggregate market analysis
            avg_volatility = np.mean([m['volatility'] for m in market_metrics])
            avg_trend_strength = np.mean([abs(m['trend_strength']) for m in market_metrics])
            avg_range = np.mean([m['range_pct'] for m in market_metrics])
            
            # Determine overall market regime
            market_regime = self._determine_market_regime(avg_volatility, avg_trend_strength, avg_range, market_metrics)
            
            logger.info(f"🌍 OVERALL MARKET ANALYSIS:")
            logger.info(f"   📊 Average Volatility: {avg_volatility:.1%}")
            logger.info(f"   📈 Average Trend Strength: {avg_trend_strength:.1%}")
            logger.info(f"   📉 Average Range: {avg_range:.1%}")
            logger.info(f"   🎯 Market Regime: {market_regime}")
            
            logger.success(f"✅ Market analizi tamamlandı: {market_regime}")
            return market_regime
            
        except Exception as e:
            logger.error(f"❌ Market analysis error: {e}")
            return 'sideways_market'
    
    async def analyze_market_condition(self, symbol: str) -> Dict[str, Any]:
        """Belirli bir sembol için market koşulunu analiz et"""
        try:
            # Get general market analysis (returns string regime)
            general_regime = await self.analyze_current_market()
            
            # Get specific symbol data
            symbol_data = await self._fetch_symbol_data(symbol)
            
            if symbol_data is not None:
                # Specific symbol analysis
                symbol_analysis = await self._analyze_symbol_condition(symbol, symbol_data)
                
                # Combine with general market
                return {
                    'symbol': symbol,
                    'condition': symbol_analysis.get('trend', general_regime),
                    'strength': symbol_analysis.get('strength', 0.5),
                    'volatility': symbol_analysis.get('volatility', 'normal'),
                    'recommended_strategies': symbol_analysis.get('strategies', []),
                    'timestamp': datetime.now(),
                    'confidence': symbol_analysis.get('confidence', 0.5)
                }
            else:
                # Use general market analysis
                return {
                    'symbol': symbol,
                    'condition': general_regime,
                    'strength': 0.5,
                    'volatility': 'normal',
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
            
            # Fetch data for major cryptocurrencies using ASYNC CCXT
            for symbol in self.major_symbols:
                try:
                    # Get historical data (last 30 days) from exchange
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    
                    hist = await self.exchange_manager.get_historical_data(
                        symbol=symbol,
                        timeframe='1d',
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if hist is None or len(hist) < 2:
                        logger.warning(f"⚠️ Insufficient data for {symbol}")
                        continue
                    
                    # Calculate technical indicators (CCXT uses lowercase column names)
                    current_price = hist['close'].iloc[-1]
                    prev_price = hist['close'].iloc[-2] if len(hist) > 1 else current_price
                    
                    # Moving averages
                    ma_7 = hist['close'].rolling(7).mean().iloc[-1]
                    ma_20 = hist['close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else current_price
                    
                    # Volatility (30-day)
                    returns = hist['close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(365) if len(returns) > 1 else 0
                    
                    # RSI calculation
                    delta = hist['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    current_rsi = rsi.iloc[-1] if not rsi.empty else 50
                    
                    # Get current market data for 24h change
                    current_market_data = await self.exchange_manager.get_real_time_data(symbol)
                    change_24h = current_market_data.get('change_24h', 0) if current_market_data else 0
                    
                    market_data[symbol] = {
                        'current_price': current_price,
                        'prev_price': prev_price,
                        'change_24h': change_24h,
                        'change_24h_pct': ((current_price - prev_price) / prev_price) * 100,
                        'volume': hist['volume'].iloc[-1],
                        'volume_avg': hist['volume'].rolling(7).mean().iloc[-1],
                        'ma_7': ma_7,
                        'ma_20': ma_20,
                        'volatility': volatility,
                        'rsi': current_rsi,
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
            if '/' in symbol:
                # Format: BTC/USDT -> BTC-USD
                base, quote = symbol.split('/')
                if quote in ['USDT', 'BUSD']:
                    yf_symbol = f"{base}-USD"
                else:
                    yf_symbol = f"{base}-{quote}"
            else:
                # Format: BTCUSDT -> BTC-USD
                if symbol.endswith('USDT'):
                    base = symbol[:-4]
                    yf_symbol = f"{base}-USD"
                elif symbol.endswith('BUSD'):
                    base = symbol[:-4]
                    yf_symbol = f"{base}-USD"
                else:
                    yf_symbol = symbol
            
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

    async def _analyze_symbol_regime(self, symbol: str, data_1h: pd.DataFrame, data_15m: pd.DataFrame) -> Dict[str, Any]:
        """Analyze individual symbol for market regime characteristics"""
        try:
            # Calculate volatility (15m data for precision)
            returns_15m = data_15m['close'].pct_change().dropna()
            volatility = returns_15m.std() * np.sqrt(96)  # Annualized from 15m
            
            # Calculate trend strength (1h data for stability)
            closes_1h = data_1h['close'].values
            sma_20 = pd.Series(closes_1h).rolling(20).mean().iloc[-1]
            current_price = closes_1h[-1]
            trend_strength = (current_price - sma_20) / sma_20
            
            # Calculate recent range
            recent_high = data_1h['high'].tail(24).max()  # Last 24 hours
            recent_low = data_1h['low'].tail(24).min()
            range_pct = (recent_high - recent_low) / current_price
            
            # Calculate momentum
            momentum_3h = (closes_1h[-1] - closes_1h[-4]) / closes_1h[-4] if len(closes_1h) >= 4 else 0
            momentum_12h = (closes_1h[-1] - closes_1h[-13]) / closes_1h[-13] if len(closes_1h) >= 13 else 0
            
            # Volume analysis
            volume_avg = data_1h['volume'].tail(24).mean()
            volume_current = data_1h['volume'].iloc[-1]
            volume_ratio = volume_current / volume_avg if volume_avg > 0 else 1
            
            # Classify regimes
            if volatility > 0.04:  # >4% daily volatility
                volatility_regime = "high"
            elif volatility > 0.02:  # >2% daily volatility
                volatility_regime = "medium"
            else:
                volatility_regime = "low"
            
            if abs(trend_strength) > 0.05:  # >5% from MA
                trend_direction = "bullish" if trend_strength > 0 else "bearish"
            elif abs(trend_strength) > 0.02:  # >2% from MA
                trend_direction = "weak_bullish" if trend_strength > 0 else "weak_bearish"
            else:
                trend_direction = "neutral"
            
            if range_pct > 0.08:  # >8% range
                range_regime = "wide"
            elif range_pct > 0.04:  # >4% range
                range_regime = "normal"
            else:
                range_regime = "tight"
            
            # Determine local regime
            if volatility_regime == "high" and abs(trend_strength) > 0.03:
                local_regime = "breakout_trending"
            elif volatility_regime == "high" and range_regime == "wide":
                local_regime = "high_volatility_ranging"
            elif volatility_regime == "low" and range_regime == "tight":
                local_regime = "low_volatility_consolidation"
            elif abs(trend_strength) > 0.05:
                local_regime = "trending"
            elif range_regime == "wide":
                local_regime = "ranging"
            else:
                local_regime = "sideways"
            
            return {
                'volatility': volatility,
                'volatility_regime': volatility_regime,
                'trend_strength': trend_strength,
                'trend_direction': trend_direction,
                'range_pct': range_pct,
                'range_regime': range_regime,
                'momentum_3h': momentum_3h,
                'momentum_12h': momentum_12h,
                'volume_ratio': volume_ratio,
                'local_regime': local_regime
            }
            
        except Exception as e:
            logger.error(f"❌ Symbol analysis error for {symbol}: {e}")
            return {
                'volatility': 0.02,
                'volatility_regime': 'medium',
                'trend_strength': 0.0,
                'trend_direction': 'neutral',
                'range_pct': 0.05,
                'range_regime': 'normal',
                'momentum_3h': 0.0,
                'momentum_12h': 0.0,
                'volume_ratio': 1.0,
                'local_regime': 'sideways'
            }
    
    def _determine_market_regime(self, avg_volatility: float, avg_trend_strength: float, 
                               avg_range: float, individual_metrics: List[Dict]) -> str:
        """Determine overall market regime from aggregated metrics"""
        try:
            # Count regime types across symbols
            regime_counts = {}
            for metrics in individual_metrics:
                regime = metrics['local_regime']
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            # Get most common regime
            dominant_regime = max(regime_counts.items(), key=lambda x: x[1])[0] if regime_counts else 'sideways'
            
            # Override with market-wide conditions
            if avg_volatility > 0.05:  # Very high volatility across market
                if avg_trend_strength > 0.04:
                    return 'market_breakout'
                else:
                    return 'high_volatility_market'
                    
            elif avg_volatility < 0.015:  # Very low volatility
                if avg_range < 0.03:
                    return 'low_volatility_consolidation'
                else:
                    return 'sideways_market'
                    
            elif avg_trend_strength > 0.06:  # Strong trend across market
                return 'trending_market'
                
            else:
                # Use dominant regime from individual analysis
                regime_mapping = {
                    'breakout_trending': 'breakout_market',
                    'high_volatility_ranging': 'volatile_ranging_market',
                    'low_volatility_consolidation': 'consolidation_market',
                    'trending': 'trending_market',
                    'ranging': 'ranging_market',
                    'sideways': 'sideways_market'
                }
                
                return regime_mapping.get(dominant_regime, 'sideways_market')
                
        except Exception as e:
            logger.error(f"❌ Regime determination error: {e}")
            return 'sideways_market'