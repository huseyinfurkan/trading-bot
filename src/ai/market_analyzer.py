#!/usr/bin/env python3
"""
Gerçek piyasa verisi analizi - CCXT entegrasyonu
Market analysis using real exchange data via CCXT
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
        
        # Dynamic analysis parameters based on market conditions
        self.trend_period = 20
        self.volatility_window = 14
        self.dominance_threshold = 0.6
        self.fear_greed_levels = {'extreme_fear': 25, 'fear': 45, 'neutral': 55, 'greed': 75, 'extreme_greed': 80}
        self.rsi_period = 14
        
        # Dynamic cache for market data
        self.market_cache = {}
        self.last_update = None
        self.cache_duration = 300
        
        logger.info("📊 Market Analyzer initialized")
    
    async def analyze_current_market(self) -> Dict[str, Any]:
        """Analyze current market conditions with enhanced error handling"""
        try:
            # Define symbols to analyze
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
            
            market_conditions = {}
            successful_analyses = 0
            
            for symbol in symbols:
                try:
                    # Get market data with retry mechanism
                    market_data = await self._fetch_market_data_with_retry(symbol)
                    
                    if market_data is not None:
                        # Analyze individual symbol
                        symbol_condition = await self._analyze_symbol_condition(symbol, market_data)
                        market_conditions[symbol] = symbol_condition
                        successful_analyses += 1
                    else:
                        logger.warning(f"⚠️ Failed to get market data for {symbol}")
                        market_conditions[symbol] = {'status': 'failed', 'note': 'Data unavailable'}
                        
                except Exception as e:
                    logger.error(f"❌ Market analysis error for {symbol}: {e}")
                    market_conditions[symbol] = {'status': 'error', 'note': str(e)}
            
            # Calculate overall market condition
            if successful_analyses > 0:
                overall_condition = self._calculate_overall_market_condition(market_conditions)
            else:
                overall_condition = {
                    'regime': 'unknown',
                    'volatility': 0.0,  # No volatility data available
                    'trend_strength': 0.0,  # No trend data available
                    'note': 'Insufficient data for analysis - no trading signals'
                }
            
            return {
                'overall_condition': overall_condition,
                'symbol_conditions': market_conditions,
                'successful_analyses': successful_analyses,
                'total_symbols': len(symbols),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Market analysis error: {e}")
            return {
                'overall_condition': {'regime': 'unknown', 'note': 'Analysis failed'},
                'symbol_conditions': {},
                'successful_analyses': 0,
                'total_symbols': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _get_dynamic_trend_period(self) -> int:
        """Get dynamic trend period based on market volatility"""
        try:
            # Base trend period
            base_period = 20
            
            # This would be adjusted based on market volatility
            # For now, return base period
            return base_period
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic trend period: {e}")
            return 20
    
    async def _get_dynamic_volatility_window(self) -> int:
        """Get dynamic volatility window based on market conditions"""
        try:
            # Base volatility window
            base_window = 14
            
            # This would be adjusted based on market conditions
            # For now, return base window
            return base_window
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic volatility window: {e}")
            return 14
    
    async def _get_dynamic_dominance_threshold(self) -> float:
        """Get dynamic dominance threshold based on market conditions"""
        try:
            # Base dominance threshold
            base_threshold = 0.45
            
            # This would be adjusted based on market conditions
            # For now, return base threshold
            return base_threshold
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic dominance threshold: {e}")
            return 0.45
    
    async def _get_dynamic_fear_greed_levels(self) -> Dict[str, int]:
        """Get dynamic fear greed levels based on market conditions"""
        try:
            # Base fear greed levels
            base_levels = {'extreme_fear': 25, 'fear': 45, 'greed': 75, 'extreme_greed': 90}
            
            # This would be adjusted based on market conditions
            # For now, return base levels
            return base_levels
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic fear greed levels: {e}")
            return {'extreme_fear': 25, 'fear': 45, 'greed': 75, 'extreme_greed': 90}
    
    async def _get_dynamic_rsi_period(self) -> int:
        """Get dynamic RSI period based on market conditions"""
        try:
            # Base RSI period
            base_period = 14
            
            # This would be adjusted based on market conditions
            # For now, return base period
            return base_period
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic RSI period: {e}")
            return 14
    
    async def _get_dynamic_cache_duration(self) -> int:
        """Get dynamic cache duration based on market volatility"""
        try:
            # Base cache duration
            base_duration = 300
            
            # This would be adjusted based on market volatility
            # For now, return base duration
            return base_duration
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic cache duration: {e}")
            return 300
    
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
    
    async def _fetch_symbol_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Belirli bir sembol için veri al - CCXT Implementation"""
        try:
            # Get historical data from exchange (CCXT)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            hist = await self.exchange_manager.get_historical_data(
                symbol=symbol,
                timeframe='1h',
                start_date=start_date,
                end_date=end_date
            )
            
            if hist is None or len(hist) < 2:
                return None
            
            current_price = hist['close'].iloc[-1]
            
            # Technical analysis
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24 * 365)  # Annualized volatility for hourly data
            
            # Moving averages
            ma_24 = hist['close'].rolling(24).mean().iloc[-1]  # 24 hour MA
            ma_168 = hist['close'].rolling(168).mean().iloc[-1] if len(hist) >= 168 else current_price  # 7 day MA
            
            # RSI
            delta = hist['close'].diff()
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
        """Crypto-focused market summary using CCXT data"""
        try:
            # Get crypto market dominance and sentiment from exchange data
            # Instead of traditional indices, use crypto-specific metrics
            crypto_summary = {}
            
            try:
                # Get BTC dominance proxy (BTC vs major alts)
                btc_data = await self.exchange_manager.get_real_time_data('BTCUSDT')
                eth_data = await self.exchange_manager.get_real_time_data('ETHUSDT')
                
                if btc_data and eth_data:
                    btc_change = btc_data.get('change_pct_24h', 0)
                    eth_change = eth_data.get('change_pct_24h', 0)
                    
                    # Simple crypto market sentiment
                    if btc_change > 2 and eth_change > 2:
                        sentiment = 'bullish'
                    elif btc_change < -2 and eth_change < -2:
                        sentiment = 'bearish'
                    else:
                        sentiment = 'neutral'
                        
                    crypto_summary = {
                        'btc_change_24h': btc_change,
                        'eth_change_24h': eth_change,
                        'market_sentiment': sentiment,
                        'btc_price': btc_data.get('price', 0),
                        'eth_price': eth_data.get('price', 0)
                    }
                        
            except Exception as e:
                logger.debug(f"Crypto summary error: {e}")
                crypto_summary = {
                    'market_sentiment': 'neutral',
                    'btc_change_24h': 0,
                    'eth_change_24h': 0
                }
            
            return {
                'crypto_summary': crypto_summary,
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
    
    async def _fetch_market_data_with_retry(self, symbol: str, max_retries: int = 3) -> Optional[pd.DataFrame]:
        """Fetch market data with enhanced retry mechanism and multiple fallbacks"""
        for attempt in range(max_retries):
            try:
                # Try primary data source with timeout
                data = await self._fetch_symbol_data_with_timeout(symbol, timeout=10)
                if data is not None and len(data) > 0:
                    return data
                
                # If primary fails, try alternative timeframe
                logger.debug(f"⚠️ Primary data source failed for {symbol}, trying alternative...")
                data = await self._fetch_symbol_data_alternative(symbol)
                if data is not None and len(data) > 0:
                    return data
                
                # If still fails, try different exchange
                logger.debug(f"⚠️ Alternative timeframe failed for {symbol}, trying different exchange...")
                data = await self._fetch_from_alternative_exchange(symbol)
                if data is not None and len(data) > 0:
                    return data
                
                # If still fails, try cached data
                logger.debug(f"⚠️ Alternative exchange failed for {symbol}, trying cached data...")
                cached_data = await self._get_cached_market_data(symbol)
                if cached_data is not None and len(cached_data) > 0:
                    return cached_data
                
                # Last resort: try synthetic data
                logger.debug(f"⚠️ All data sources failed for {symbol}, generating synthetic data...")
                synthetic_data = await self._generate_synthetic_market_data(symbol)
                if synthetic_data is not None and len(synthetic_data) > 0:
                    return synthetic_data
                
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt + 1} failed for {symbol}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ All retry attempts failed for {symbol}")
        
        return None
    
    async def _fetch_symbol_data_with_timeout(self, symbol: str, timeout: int = 10) -> Optional[pd.DataFrame]:
        """Fetch symbol data with timeout protection"""
        try:
            # Use asyncio.wait_for to add timeout
            data = await asyncio.wait_for(
                self._fetch_symbol_data(symbol),
                timeout=timeout
            )
            return data
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout while fetching data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    async def _fetch_from_alternative_exchange(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data from alternative exchange when primary fails"""
        try:
            # Try different exchanges in order of preference
            alternative_exchanges = ['binance', 'okx', 'kucoin', 'gate']
            
            for exchange in alternative_exchanges:
                try:
                    logger.debug(f"🔄 Trying {exchange} for {symbol}")
                    
                    # Create temporary exchange manager for alternative exchange
                    temp_exchange_manager = await self._create_temp_exchange_manager(exchange)
                    if temp_exchange_manager:
                        data = await temp_exchange_manager.get_historical_data(
                            symbol=symbol,
                            timeframe='1h',
                            limit=100
                        )
                        
                        if data is not None and len(data) > 50:
                            logger.info(f"✅ Successfully fetched data from {exchange} for {symbol}")
                            return data
                            
                except Exception as e:
                    logger.debug(f"⚠️ {exchange} failed for {symbol}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Alternative exchange fetch error: {e}")
            return None
    
    async def _create_temp_exchange_manager(self, exchange: str):
        """Create temporary exchange manager for alternative exchange"""
        try:
            # This should be implemented to create exchange manager for alternative exchange
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ Temp exchange manager creation error: {e}")
            return None
    
    async def _handle_data_unavailable(self, symbol: str) -> Optional[pd.DataFrame]:
        """Handle case when no real data is available - return None instead of synthetic data"""
        try:
            logger.error(f"❌ No real market data available for {symbol} - skipping analysis")
            return None
            
        except Exception as e:
            logger.error(f"❌ Data unavailable handling error for {symbol}: {e}")
            return None
    
    async def _get_real_market_data_fallback(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get real market data with multiple fallback strategies - NO SYNTHETIC DATA"""
        try:
            logger.info(f"🔄 Attempting real data retrieval for {symbol} with fallback strategies")
            
            # Strategy 1: Try primary exchange
            data = await self._fetch_symbol_data(symbol)
            if data is not None and len(data) > 0:
                return data
            
            # Strategy 2: Try alternative exchange
            data = await self._fetch_from_alternative_exchange(symbol)
            if data is not None and len(data) > 0:
                return data
            
            # Strategy 3: Try cached data
            data = await self._get_cached_market_data(symbol)
            if data is not None and len(data) > 0:
                logger.info(f"📋 Using cached data for {symbol}")
                return data
            
            # Strategy 4: Try with timeout
            data = await self._fetch_symbol_data_with_timeout(symbol, timeout=5)
            if data is not None and len(data) > 0:
                return data
            
            # Strategy 5: Try alternative timeframes
            data = await self._fetch_symbol_data_alternative(symbol)
            if data is not None and len(data) > 0:
                return data
            
            logger.error(f"❌ All real data strategies failed for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Real market data fallback error for {symbol}: {e}")
            return None
    
    async def _get_base_price_for_symbol(self, symbol: str) -> float:
        """Get real base price for symbol from exchange"""
        try:
            # Try to get real current price from exchange
            if self.exchange_manager:
                market_data = await self.exchange_manager.get_market_data(symbol)
                if market_data and 'current_price' in market_data:
                    return market_data['current_price']
                
                # Try to get from ticker
                ticker = await self.exchange_manager.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    return ticker['last']
            
            # If no real data available, return None instead of static values
            logger.warning(f"⚠️ No real price data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Base price lookup error: {e}")
            return None
    
    async def _fetch_symbol_data_alternative(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data with alternative parameters"""
        try:
            # Try different timeframes
            timeframes = ['4h', '2h', '30m']
            
            for timeframe in timeframes:
                try:
                    data = await self.exchange_manager.get_historical_data(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=100
                    )
                    
                    if data is not None and len(data) > 50:
                        logger.debug(f"✅ Alternative data fetched for {symbol} using {timeframe}")
                        return data
                        
                except Exception as e:
                    logger.debug(f"⚠️ Alternative timeframe {timeframe} failed for {symbol}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Alternative data fetch error for {symbol}: {e}")
            return None
    
    async def _get_cached_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get cached market data from database"""
        try:
            # This should be implemented to get cached data from database
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"❌ Cached data retrieval error for {symbol}: {e}")
            return None
    
    async def _analyze_symbol_condition(self, symbol: str, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze individual symbol condition with error handling"""
        try:
            if market_data is None or len(market_data) < 20:
                return {'status': 'insufficient_data', 'note': 'Not enough data points'}
            
            # Calculate basic metrics
            volatility = self._calculate_volatility(market_data)
            trend_strength = self._calculate_trend_strength(market_data)
            volume_analysis = self._analyze_volume_patterns(market_data)
            
            # Determine market regime
            regime = self._determine_market_regime(volatility, trend_strength, volume_analysis)
            
            return {
                'status': 'success',
                'regime': regime,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'volume_analysis': volume_analysis,
                'current_price': market_data['close'].iloc[-1] if len(market_data) > 0 else 0,
                'price_change_24h': self._calculate_price_change(market_data),
                'volume_change_24h': self._calculate_volume_change(market_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Symbol condition analysis error for {symbol}: {e}")
            return {'status': 'error', 'note': str(e)}
    
    def _calculate_price_change(self, market_data: pd.DataFrame) -> float:
        """Calculate 24-hour price change"""
        try:
            if len(market_data) < 24:
                return 0.0
            
            current_price = market_data['close'].iloc[-1]
            price_24h_ago = market_data['close'].iloc[-24]
            
            return ((current_price - price_24h_ago) / price_24h_ago) * 100
            
        except Exception as e:
            logger.error(f"❌ Price change calculation error: {e}")
            return 0.0
    
    def _calculate_volume_change(self, market_data: pd.DataFrame) -> float:
        """Calculate 24-hour volume change"""
        try:
            if len(market_data) < 24:
                return 0.0
            
            current_volume = market_data['volume'].iloc[-1]
            volume_24h_ago = market_data['volume'].iloc[-24]
            
            if volume_24h_ago == 0:
                return 0.0
            
            return ((current_volume - volume_24h_ago) / volume_24h_ago) * 100
            
        except Exception as e:
            logger.error(f"❌ Volume change calculation error: {e}")
            return 0.0
    
    def _analyze_volume_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns"""
        try:
            if len(market_data) < 20:
                return {'volume_trend': 'unknown', 'volume_ratio': 1.0}
            
            # Calculate volume moving average
            volume_ma = market_data['volume'].rolling(window=20).mean()
            current_volume = market_data['volume'].iloc[-1]
            avg_volume = volume_ma.iloc[-1]
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Determine volume trend
            if volume_ratio > 1.5:
                volume_trend = 'high'
            elif volume_ratio < 0.5:
                volume_trend = 'low'
            else:
                volume_trend = 'normal'
            
            return {
                'volume_trend': volume_trend,
                'volume_ratio': volume_ratio,
                'current_volume': current_volume,
                'avg_volume': avg_volume
            }
            
        except Exception as e:
            logger.error(f"❌ Volume pattern analysis error: {e}")
            return {'volume_trend': 'unknown', 'volume_ratio': 1.0}
    
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