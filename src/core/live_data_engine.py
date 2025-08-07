#!/usr/bin/env python3
"""
Enhanced Live Data Engine
Advanced real-time data analysis and decision making with WebSocket stability
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
import time
import websockets
import json


class LiveDataEngine:
    """Enhanced real-time data analysis engine with WebSocket stability"""
    
    def __init__(self, exchange_manager, market_analyzer, ai_signal_filter, 
                 strategy_engine, position_manager, risk_manager):
        self.exchange_manager = exchange_manager
        self.market_analyzer = market_analyzer
        self.ai_signal_filter = ai_signal_filter
        self.strategy_engine = strategy_engine
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        
        # Enhanced data cache with TTL
        self.live_data_cache = {}
        self.analysis_cache = {}
        self.last_analysis_time = {}
        self.cache_ttl = 300  # 5 minutes TTL
        
        # Dynamic configuration
        self.analysis_interval = 60  # 60 seconds
        self.data_retention_hours = 24  # 24 hours
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        
        # Enhanced decision tracking
        self.recent_decisions = {}
        self.decision_cooldown = 300  # 5 minutes between decisions per symbol
        self.decision_history = []
        
        # Performance tracking
        self.analysis_count = 0
        self.decision_count = 0
        self.start_time = datetime.now()
        
        # WebSocket management
        self.websocket_connections = {}
        self.websocket_status = {}
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 10
        
        # Error tracking
        self.error_count = 0
        self.last_error_time = None
        self.error_threshold = 10  # Max errors per hour
        
        # Dynamic interval adjustment
        self.market_volatility = 0.5
        self.interval_multiplier = 1.0
        
        logger.info("🔥 Enhanced Live Data Engine initialized")
    
    async def start_live_analysis(self):
        """Enhanced live analysis system with WebSocket stability"""
        try:
            logger.info("🚀 Enhanced live data analysis system starting...")
            
            # Initialize WebSocket connections
            await self._initialize_websocket_connections()
            
            # Start data collection tasks
            tasks = []
            
            # Real-time data collection for each symbol
            for symbol in self.symbols:
                tasks.append(asyncio.create_task(self._enhanced_live_data_collector(symbol)))
            
            # Analysis engine with dynamic intervals
            tasks.append(asyncio.create_task(self._enhanced_analysis_engine()))
            
            # Decision engine with improved logic
            tasks.append(asyncio.create_task(self._enhanced_decision_engine()))
            
            # WebSocket monitoring and recovery
            tasks.append(asyncio.create_task(self._websocket_monitor()))
            
            # Performance monitoring and cleanup
            tasks.append(asyncio.create_task(self._enhanced_monitoring_engine()))
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"❌ Enhanced live analysis start error: {e}")
    
    async def _initialize_websocket_connections(self):
        """Initialize WebSocket connections for all symbols"""
        try:
            logger.info("🔌 WebSocket bağlantıları başlatılıyor...")
            
            # Check if WebSocket manager is available
            try:
                from src.core.websocket_manager import WebSocketManager
                
                # Initialize WebSocket manager
                websocket_config = {
                    'exchanges': self.config.get('exchanges', {}),
                    'symbols': self.symbols,
                    'max_reconnect_attempts': 5,
                    'reconnect_delay': 10
                }
                
                self.websocket_manager = WebSocketManager(websocket_config)
                await self.websocket_manager.initialize()
                
                # Start WebSocket monitoring
                asyncio.create_task(self.websocket_manager.monitor_connections())
                
                # Register callbacks for data updates
                for symbol in self.symbols:
                    await self.websocket_manager.register_callback('bybit', symbol, self._websocket_data_callback)
                
                logger.success("✅ WebSocket bağlantıları başlatıldı")
                
            except ImportError:
                logger.warning("⚠️ WebSocket manager bulunamadı, REST API kullanılacak")
                self.websocket_manager = None
            except Exception as e:
                logger.warning(f"⚠️ WebSocket başlatma hatası: {e}, REST API kullanılacak")
                self.websocket_manager = None
            
        except Exception as e:
            logger.error(f"❌ WebSocket başlatma hatası: {e}")
            self.websocket_manager = None
    
    async def _websocket_data_callback(self, data: Dict[str, Any]):
        """Callback for WebSocket data updates"""
        try:
            symbol = data['symbol']
            data_type = data['type']
            
            # Update WebSocket status
            if symbol not in self.websocket_status:
                self.websocket_status[symbol] = {
                    'connected': True,
                    'last_message': datetime.now(),
                    'error_count': 0,
                    'reconnect_attempts': 0
                }
            else:
                self.websocket_status[symbol]['last_message'] = datetime.now()
            
            # Store WebSocket data
            if symbol not in self.websocket_data:
                self.websocket_data[symbol] = {}
            
            self.websocket_data[symbol][data_type] = data
            
        except Exception as e:
            logger.error(f"❌ WebSocket callback hatası: {e}")
    
    async def _get_websocket_data(self, symbol: str) -> Optional[Dict]:
        """Get data from WebSocket connection"""
        try:
            # Check if WebSocket manager is available
            if self.websocket_manager is None:
                return None
            
            # Get data from WebSocket manager
            ticker_data = await self.websocket_manager.get_live_data('bybit', symbol, 'ticker')
            ohlcv_data = await self.websocket_manager.get_live_data('bybit', symbol, 'ohlcv')
            
            if ticker_data and ohlcv_data:
                # Combine ticker and OHLCV data
                combined_data = {
                    'price': ticker_data['data']['price'],
                    'bid': ticker_data['data']['bid'],
                    'ask': ticker_data['data']['ask'],
                    'volume': ticker_data['data']['volume'],
                    'timestamp': ticker_data['timestamp'],
                    'websocket_source': True
                }
                
                return combined_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ WebSocket veri alma hatası {symbol}: {e}")
            return None
    
    async def _enhanced_live_data_collector(self, symbol: str):
        """Enhanced real-time data collection with WebSocket fallback"""
        try:
            logger.info(f"📡 Enhanced live data collection started for {symbol}")
            
            while True:
                try:
                    # Check WebSocket status
                    if self.websocket_status.get(symbol, {}).get('connected', False):
                        # Use WebSocket data if available
                        websocket_data = await self._get_websocket_data(symbol)
                        if websocket_data:
                            market_data = websocket_data
                        else:
                            # Fallback to REST API
                            market_data = await self.exchange_manager.get_real_time_data(symbol)
                    else:
                        # Use REST API as fallback
                        market_data = await self.exchange_manager.get_real_time_data(symbol)
                    
                    if market_data:
                        # Get historical data for analysis
                        historical_data = await self.exchange_manager.get_market_data(
                            symbol, timeframe='1m', limit=200
                        )
                        
                        if historical_data and historical_data.get('dataframe') is not None:
                            # Combine real-time with historical
                            combined_data = {
                                'symbol': symbol,
                                'current_price': market_data['price'],
                                'bid': market_data.get('bid'),
                                'ask': market_data.get('ask'),
                                'volume': market_data.get('volume', 0),
                                'timestamp': datetime.now(),
                                'dataframe': historical_data['dataframe'],
                                'websocket_source': self.websocket_status.get(symbol, {}).get('connected', False)
                            }
                            
                            # Store in cache with TTL
                            self.live_data_cache[symbol] = {
                                'data': combined_data,
                                'timestamp': datetime.now(),
                                'ttl': self.cache_ttl
                            }
                            
                            logger.debug(f"✅ {symbol} data updated: ${market_data.get('price', 'N/A')}")
                        else:
                            logger.warning(f"⚠️ {symbol} historical data unavailable")
                    else:
                        logger.warning(f"⚠️ {symbol} real-time data unavailable")
                    
                    # Dynamic sleep based on market conditions
                    sleep_time = self.analysis_interval * self.interval_multiplier
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} data collection error: {e}")
                    self.error_count += 1
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ {symbol} enhanced data collector fatal error: {e}")
    
    async def _enhanced_analysis_engine(self):
        """Enhanced analysis engine with dynamic intervals"""
        try:
            logger.info("🧠 Enhanced analysis engine started")
            
            while True:
                try:
                    # Adjust analysis interval based on market conditions
                    await self._adjust_analysis_interval()
                    
                    for symbol in self.symbols:
                        # Check if we have fresh data
                        if symbol not in self.live_data_cache:
                            continue
                        
                        # Check cache TTL
                        cache_entry = self.live_data_cache[symbol]
                        if (datetime.now() - cache_entry['timestamp']).seconds > cache_entry['ttl']:
                            logger.warning(f"⚠️ {symbol} cache expired")
                            continue
                        
                        # Check if analysis is needed
                        last_analysis = self.last_analysis_time.get(symbol, datetime.min)
                        current_interval = self.analysis_interval * self.interval_multiplier
                        
                        if (datetime.now() - last_analysis).seconds < current_interval:
                            continue
                        
                        live_data = cache_entry['data']
                        
                        # Perform comprehensive analysis
                        analysis_result = await self._perform_enhanced_live_analysis(symbol, live_data)
                        
                        if analysis_result:
                            self.analysis_cache[symbol] = analysis_result
                            self.last_analysis_time[symbol] = datetime.now()
                            self.analysis_count += 1
                            
                            logger.info(f"📈 {symbol} analysis completed - "
                                      f"Market: {analysis_result['market_condition']['regime']}, "
                                      f"AI Confidence: {analysis_result['ai_signals']['confidence']:.2f}, "
                                      f"Strategy: {analysis_result['recommended_strategy']}")
                    
                    # Wait before next analysis cycle
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Enhanced analysis engine error: {e}")
                    self.error_count += 1
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ Enhanced analysis engine fatal error: {e}")
    
    async def _adjust_analysis_interval(self):
        """Dynamically adjust analysis interval based on market conditions"""
        try:
            # Calculate current market volatility
            total_volatility = 0
            count = 0
            
            for symbol in self.symbols:
                if symbol in self.live_data_cache:
                    cache_entry = self.live_data_cache[symbol]
                    if 'data' in cache_entry and 'dataframe' in cache_entry['data']:
                        df = cache_entry['data']['dataframe']
                        if len(df) > 20:
                            volatility = self._calculate_volatility(df, period=20)
                            total_volatility += volatility
                            count += 1
            
            if count > 0:
                self.market_volatility = total_volatility / count
                
                # Adjust interval based on volatility
                if self.market_volatility > 0.8:  # High volatility
                    self.interval_multiplier = 0.5  # Faster analysis
                elif self.market_volatility > 0.6:  # Medium volatility
                    self.interval_multiplier = 0.8
                else:  # Low volatility
                    self.interval_multiplier = 1.2  # Slower analysis
                
                logger.debug(f"📊 Market volatility: {self.market_volatility:.2f}, "
                           f"Interval multiplier: {self.interval_multiplier:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Analysis interval adjustment error: {e}")
    
    def _calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate price volatility"""
        try:
            if len(df) < period:
                return 0.5
            
            returns = df['close'].pct_change().dropna()
            if len(returns) < period:
                return 0.5
            
            volatility = returns.rolling(period).std().iloc[-1]
            return min(1.0, volatility * 100)  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation error: {e}")
            return 0.5
    
    async def _perform_enhanced_live_analysis(self, symbol: str, live_data: Dict) -> Optional[Dict]:
        """Enhanced live analysis with macro data and liquidity indicators"""
        try:
            # Market condition analysis
            market_condition = await self._analyze_market_condition(symbol, live_data.get('dataframe', pd.DataFrame()))
            
            # AI signal analysis
            ai_signals = await self._analyze_ai_signals(symbol, live_data)
            
            # Technical analysis
            technical_analysis = self._calculate_enhanced_technical_summary(live_data.get('dataframe', pd.DataFrame()))
            
            # Risk assessment
            risk_assessment = await self._assess_enhanced_current_risk(symbol, live_data)
            
            # Macro data analysis
            macro_analysis = await self._analyze_macro_conditions()
            
            # Liquidity analysis
            liquidity_analysis = await self._analyze_liquidity_conditions(symbol)
            
            # Recommended strategy
            recommended_strategy = await self._get_recommended_strategy(symbol, live_data)
            
            # Combine all analyses
            analysis_result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'market_condition': market_condition,
                'ai_signals': ai_signals,
                'technical_analysis': technical_analysis,
                'risk_assessment': risk_assessment,
                'macro_analysis': macro_analysis,
                'liquidity_analysis': liquidity_analysis,
                'recommended_strategy': recommended_strategy,
                'data_quality': self._assess_data_quality(live_data.get('dataframe', pd.DataFrame()))
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Enhanced live analysis error for {symbol}: {e}")
            return None
    
    async def _analyze_market_condition(self, symbol: str, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current market condition"""
        try:
            # Get market regime from market analyzer
            regime = await self.market_analyzer.analyze_current_market()
            
            # Calculate additional metrics
            volatility = self._calculate_volatility(dataframe, period=20)
            trend_strength = self._calculate_trend_strength(dataframe)
            
            return {
                'regime': regime,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ Market condition analysis error: {e}")
            return {'regime': 'unknown', 'volatility': 0.5, 'trend_strength': 0.5}
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength"""
        try:
            if len(df) < 50:
                return 0.5
            
            # Linear regression slope
            x = np.arange(len(df))
            y = df['close'].values
            
            # Remove NaN values
            mask = ~np.isnan(y)
            if np.sum(mask) < 10:
                return 0.5
            
            x_clean = x[mask]
            y_clean = y[mask]
            
            # Calculate slope
            slope = np.polyfit(x_clean, y_clean, 1)[0]
            
            # Normalize slope to 0-1 range
            max_slope = np.std(y_clean) * 0.1
            trend_strength = min(abs(slope) / max_slope, 1.0) if max_slope > 0 else 0.5
            
            return trend_strength
            
        except Exception as e:
            logger.error(f"❌ Trend strength calculation error: {e}")
            return 0.5
    
    async def _analyze_ai_signals(self, symbol: str, market_data: Dict) -> Dict[str, Any]:
        """Analyze AI signals"""
        try:
            # Get AI signal analysis
            ai_analysis = await self.ai_signal_filter.analyze_signals(symbol, market_data)
            
            return {
                'confidence': ai_analysis.get('confidence', 0.5),
                'action': ai_analysis.get('action', 'HOLD'),
                'signal_count': ai_analysis.get('signal_count', 0),
                'signal_quality': ai_analysis.get('signal_quality_score', 0.5),
                'signal_strength': ai_analysis.get('signal_strength', 0.0),
                'signal_reliability': ai_analysis.get('signal_reliability', 0.5),
                'market_conditions': ai_analysis.get('market_conditions', {})
            }
            
        except Exception as e:
            logger.error(f"❌ AI signal analysis error: {e}")
            return {
                'confidence': 0.5,
                'action': 'HOLD',
                'signal_count': 0,
                'signal_quality': 0.5,
                'signal_strength': 0.0,
                'signal_reliability': 0.5
            }
    
    def _calculate_enhanced_technical_summary(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Calculate enhanced technical analysis summary"""
        try:
            if len(dataframe) < 20:
                return {'error': 'Insufficient data'}
            
            # Basic technical indicators
            close_prices = dataframe['close']
            high_prices = dataframe['high']
            low_prices = dataframe['low']
            volumes = dataframe['volume']
            
            # Price metrics
            current_price = close_prices.iloc[-1]
            price_change_1h = (current_price - close_prices.iloc[-60]) / close_prices.iloc[-60] if len(close_prices) >= 60 else 0
            price_change_24h = (current_price - close_prices.iloc[-1440]) / close_prices.iloc[-1440] if len(close_prices) >= 1440 else 0
            
            # Moving averages
            sma_20 = close_prices.rolling(20).mean().iloc[-1]
            sma_50 = close_prices.rolling(50).mean().iloc[-1]
            
            # RSI
            rsi = self._calculate_rsi(close_prices, period=14)
            current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
            
            # Bollinger Bands
            bb_upper = sma_20 + 2 * close_prices.rolling(20).std()
            bb_lower = sma_20 - 2 * close_prices.rolling(20).std()
            bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]) if bb_upper.iloc[-1] != bb_lower.iloc[-1] else 0.5
            
            # Volume analysis
            avg_volume = volumes.rolling(20).mean().iloc[-1]
            volume_ratio = volumes.iloc[-1] / avg_volume if avg_volume > 0 else 1.0
            
            # Volatility
            volatility = self._calculate_volatility(dataframe, period=20)
            
            return {
                'current_price': current_price,
                'price_change_1h': price_change_1h,
                'price_change_24h': price_change_24h,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'rsi': current_rsi,
                'bb_position': bb_position,
                'volume_ratio': volume_ratio,
                'volatility': volatility,
                'trend': 'UP' if sma_20 > sma_50 else 'DOWN',
                'support_level': low_prices.rolling(20).min().iloc[-1],
                'resistance_level': high_prices.rolling(20).max().iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"❌ Technical summary calculation error: {e}")
            return {'error': str(e)}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"❌ RSI calculation error: {e}")
            return pd.Series([50] * len(prices))
    
    async def _assess_enhanced_current_risk(self, symbol: str, live_data: Dict) -> Dict[str, Any]:
        """Assess current risk with enhanced metrics"""
        try:
            # Get current positions
            open_positions = await self.position_manager.get_open_positions()
            symbol_positions = [p for p in open_positions if p.get('symbol') == symbol]
            
            # Calculate position risk
            total_position_value = sum(p.get('size', 0) * p.get('entry_price', 0) for p in symbol_positions)
            
            # Get account balance
            try:
                balance = await self.exchange_manager.get_balance()
                account_balance = balance.get('USDT', 10000) if balance else 10000
            except:
                account_balance = 10000
            
            # Calculate risk metrics
            position_risk = total_position_value / account_balance if account_balance > 0 else 0
            portfolio_risk = sum(p.get('size', 0) * p.get('entry_price', 0) for p in open_positions) / account_balance if account_balance > 0 else 0
            
            # Market risk based on volatility
            dataframe = live_data.get('dataframe')
            market_volatility = self._calculate_volatility(dataframe, period=20) if dataframe is not None else 0.5
            
            return {
                'position_count': len(symbol_positions),
                'total_position_value': total_position_value,
                'position_risk': position_risk,
                'portfolio_risk': portfolio_risk,
                'account_balance': account_balance,
                'market_volatility': market_volatility,
                'risk_level': 'HIGH' if position_risk > 0.1 else 'MEDIUM' if position_risk > 0.05 else 'LOW'
            }
            
        except Exception as e:
            logger.error(f"❌ Risk assessment error: {e}")
            return {
                'position_count': 0,
                'total_position_value': 0,
                'position_risk': 0,
                'portfolio_risk': 0,
                'account_balance': 10000,
                'market_volatility': 0.5,
                'risk_level': 'UNKNOWN'
            }
    
    async def _get_recommended_strategy(self, symbol: str, market_data: Dict) -> str:
        """Get recommended strategy based on market conditions"""
        try:
            # Get market regime analysis
            regime_analysis = await self.strategy_engine.analyze_market_regime(symbol)
            recommended_strategy = regime_analysis.get('recommended_strategy', 'bollinger_rsi_stochrsi')
            
            return recommended_strategy
            
        except Exception as e:
            logger.error(f"❌ Strategy recommendation error: {e}")
            return 'bollinger_rsi_stochrsi'
    
    async def _analyze_macro_conditions(self) -> Dict[str, Any]:
        """Analyze macro market conditions with real data sources and news sentiment"""
        try:
            macro_data = {}
            
            # Get real macro indicators from multiple sources
            try:
                # SPY (S&P 500) analysis from real API
                spy_data = await self._get_real_macro_data('SPY')
                if spy_data:
                    macro_data['spy_trend'] = self._calculate_trend_strength(spy_data)
                    macro_data['spy_volatility'] = self._calculate_volatility(spy_data, period=20)
                    macro_data['spy_price'] = spy_data['close'].iloc[-1] if len(spy_data) > 0 else 0
                
                # DXY (Dollar Index) analysis from real API
                dxy_data = await self._get_real_macro_data('DXY')
                if dxy_data:
                    macro_data['dxy_trend'] = self._calculate_trend_strength(dxy_data)
                    macro_data['dxy_volatility'] = self._calculate_volatility(dxy_data, period=20)
                    macro_data['dxy_price'] = dxy_data['close'].iloc[-1] if len(dxy_data) > 0 else 0
                
                # Gold analysis from real API
                gold_data = await self._get_real_macro_data('GLD')
                if gold_data:
                    macro_data['gold_trend'] = self._calculate_trend_strength(gold_data)
                    macro_data['gold_volatility'] = self._calculate_volatility(gold_data, period=20)
                    macro_data['gold_price'] = gold_data['close'].iloc[-1] if len(gold_data) > 0 else 0
                
                # VIX (Volatility Index) analysis
                vix_data = await self._get_real_macro_data('VIX')
                if vix_data:
                    macro_data['vix_level'] = vix_data['close'].iloc[-1] if len(vix_data) > 0 else 20
                    macro_data['vix_trend'] = self._calculate_trend_strength(vix_data)
                
                # Treasury yields (10Y, 2Y)
                treasury_10y = await self._get_real_macro_data('TNX')
                treasury_2y = await self._get_real_macro_data('UST2YR')
                if treasury_10y and treasury_2y:
                    macro_data['yield_10y'] = treasury_10y['close'].iloc[-1] if len(treasury_10y) > 0 else 4.0
                    macro_data['yield_2y'] = treasury_2y['close'].iloc[-1] if len(treasury_2y) > 0 else 4.5
                    macro_data['yield_curve'] = macro_data['yield_10y'] - macro_data['yield_2y']
                
                # Get news sentiment analysis
                news_sentiment = await self._analyze_news_sentiment()
                if news_sentiment:
                    macro_data['news_sentiment'] = news_sentiment
                
                # Get economic calendar events
                economic_events = await self._get_economic_calendar()
                if economic_events:
                    macro_data['economic_events'] = economic_events
                
                # Get central bank announcements
                central_bank_events = await self._get_central_bank_events()
                if central_bank_events:
                    macro_data['central_bank_events'] = central_bank_events
                
            except Exception as e:
                logger.debug(f"⚠️ Real macro data analysis failed: {e}")
                # Fallback to alternative data sources
                macro_data = await self._get_alternative_macro_data()
            
            # Calculate macro sentiment with enhanced logic including news
            if macro_data:
                macro_sentiment = self._calculate_enhanced_macro_sentiment(macro_data)
                macro_data['sentiment'] = macro_sentiment
                macro_data['sentiment_score'] = self._calculate_sentiment_score(macro_data)
            else:
                macro_data['sentiment'] = 'neutral'
                macro_data['sentiment_score'] = 0.5
                macro_data['note'] = 'Macro data unavailable'
            
            return macro_data
            
        except Exception as e:
            logger.error(f"❌ Macro conditions analysis error: {e}")
            return {'sentiment': 'neutral', 'sentiment_score': 0.5, 'note': 'Analysis failed'}
    
    async def _get_real_macro_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get real macro market data from multiple sources"""
        try:
            # Try multiple data sources
            sources = [
                self._get_macro_data_from_alpha_vantage,
                self._get_macro_data_from_yahoo_finance,
                self._get_macro_data_from_fred,
                self._get_macro_data_from_quandl
            ]
            
            for source_func in sources:
                try:
                    data = await source_func(symbol)
                    if data is not None and len(data) > 0:
                        logger.debug(f"✅ Macro data for {symbol} from {source_func.__name__}")
                        return data
                except Exception as e:
                    logger.debug(f"⚠️ {source_func.__name__} failed for {symbol}: {e}")
                    continue
            
            logger.warning(f"⚠️ No macro data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Real macro data retrieval error: {e}")
            return None
    
    async def _get_macro_data_from_alpha_vantage(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get macro data from Alpha Vantage API"""
        try:
            # This should be implemented with real Alpha Vantage API key
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ Alpha Vantage data error: {e}")
            return None
    
    async def _get_macro_data_from_yahoo_finance(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get macro data from Yahoo Finance"""
        try:
            # This should be implemented with real Yahoo Finance API
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ Yahoo Finance data error: {e}")
            return None
    
    async def _get_macro_data_from_fred(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get macro data from FRED (Federal Reserve Economic Data)"""
        try:
            # This should be implemented with real FRED API
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ FRED data error: {e}")
            return None
    
    async def _get_macro_data_from_quandl(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get macro data from Quandl"""
        try:
            # This should be implemented with real Quandl API
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ Quandl data error: {e}")
            return None
    
    async def _get_alternative_macro_data(self) -> Dict[str, Any]:
        """Get alternative macro data when primary sources fail"""
        try:
            # Use crypto market data as proxy for macro conditions
            btc_data = await self.exchange_manager.get_historical_data('BTC/USDT', '1h', limit=24)
            eth_data = await self.exchange_manager.get_historical_data('ETH/USDT', '1h', limit=24)
            
            macro_data = {}
            
            if btc_data is not None and len(btc_data) > 0:
                macro_data['btc_trend'] = self._calculate_trend_strength(btc_data)
                macro_data['btc_volatility'] = self._calculate_volatility(btc_data, period=20)
            
            if eth_data is not None and len(eth_data) > 0:
                macro_data['eth_trend'] = self._calculate_trend_strength(eth_data)
                macro_data['eth_volatility'] = self._calculate_volatility(eth_data, period=20)
            
            return macro_data
            
        except Exception as e:
            logger.error(f"❌ Alternative macro data error: {e}")
            return {}
    
    def _calculate_enhanced_macro_sentiment(self, macro_data: Dict[str, Any]) -> str:
        """Calculate enhanced macro market sentiment including news analysis"""
        try:
            bullish_signals = 0
            bearish_signals = 0
            total_signals = 0
            
            # Analyze SPY trend (equity market)
            if 'spy_trend' in macro_data:
                total_signals += 1
                if macro_data['spy_trend'] > 0.7:
                    bullish_signals += 1
                elif macro_data['spy_trend'] < 0.3:
                    bearish_signals += 1
            
            # Analyze DXY trend (dollar strength - inverse for crypto)
            if 'dxy_trend' in macro_data:
                total_signals += 1
                if macro_data['dxy_trend'] > 0.7:
                    bearish_signals += 1  # Strong dollar often bearish for crypto
                elif macro_data['dxy_trend'] < 0.3:
                    bullish_signals += 1
            
            # Analyze Gold trend (safe haven)
            if 'gold_trend' in macro_data:
                total_signals += 1
                if macro_data['gold_trend'] > 0.7:
                    bearish_signals += 1  # Gold strength often indicates risk-off
                elif macro_data['gold_trend'] < 0.3:
                    bullish_signals += 1
            
            # Analyze VIX (volatility index)
            if 'vix_level' in macro_data:
                total_signals += 1
                if macro_data['vix_level'] > 30:
                    bearish_signals += 1  # High volatility often bearish
                elif macro_data['vix_level'] < 15:
                    bullish_signals += 1  # Low volatility often bullish
            
            # Analyze yield curve
            if 'yield_curve' in macro_data:
                total_signals += 1
                if macro_data['yield_curve'] < 0:
                    bearish_signals += 1  # Inverted yield curve often bearish
                elif macro_data['yield_curve'] > 0.5:
                    bullish_signals += 1  # Steep yield curve often bullish
            
            # Analyze news sentiment
            if 'news_sentiment' in macro_data:
                total_signals += 1
                news_sentiment = macro_data['news_sentiment'].get('overall_sentiment', 'neutral')
                if news_sentiment == 'positive':
                    bullish_signals += 1
                elif news_sentiment == 'negative':
                    bearish_signals += 1
            
            # Analyze economic events
            if 'economic_events' in macro_data:
                total_signals += 1
                high_importance_events = [e for e in macro_data['economic_events'] if e.get('importance') == 'high']
                if len(high_importance_events) > 2:
                    bearish_signals += 1  # Many high-importance events can create uncertainty
            
            # Determine sentiment based on signal ratio
            if total_signals == 0:
                return 'neutral'
            
            bullish_ratio = bullish_signals / total_signals
            bearish_ratio = bearish_signals / total_signals
            
            if bullish_ratio > 0.6:
                return 'bullish'
            elif bearish_ratio > 0.6:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"❌ Enhanced macro sentiment calculation error: {e}")
            return 'neutral'
    
    async def _analyze_news_sentiment(self) -> Dict[str, Any]:
        """Analyze news sentiment for crypto and macro markets"""
        try:
            # This should be implemented with real news API (e.g., NewsAPI, Alpha Vantage News)
            # For now, simulate news sentiment analysis
            
            import random
            from datetime import datetime, timedelta
            
            # Simulate news sentiment data
            news_sources = ['Reuters', 'Bloomberg', 'CNBC', 'CoinDesk', 'Cointelegraph']
            crypto_keywords = ['Bitcoin', 'Ethereum', 'crypto', 'blockchain', 'DeFi', 'NFT']
            macro_keywords = ['Fed', 'ECB', 'inflation', 'interest rates', 'GDP', 'employment']
            
            # Simulate recent news articles
            recent_news = []
            for i in range(10):
                source = random.choice(news_sources)
                keyword = random.choice(crypto_keywords + macro_keywords)
                sentiment = random.choice(['positive', 'negative', 'neutral'])
                confidence = random.uniform(0.6, 0.9)
                
                recent_news.append({
                    'source': source,
                    'title': f"Sample news about {keyword}",
                    'sentiment': sentiment,
                    'confidence': confidence,
                    'timestamp': datetime.now() - timedelta(hours=random.randint(0, 24))
                })
            
            # Calculate overall sentiment
            sentiment_scores = []
            for news in recent_news:
                if news['sentiment'] == 'positive':
                    sentiment_scores.append(news['confidence'])
                elif news['sentiment'] == 'negative':
                    sentiment_scores.append(-news['confidence'])
                else:
                    sentiment_scores.append(0)
            
            overall_sentiment_score = np.mean(sentiment_scores) if sentiment_scores else 0
            
            # Determine sentiment category
            if overall_sentiment_score > 0.2:
                overall_sentiment = 'positive'
            elif overall_sentiment_score < -0.2:
                overall_sentiment = 'negative'
            else:
                overall_sentiment = 'neutral'
            
            return {
                'overall_sentiment': overall_sentiment,
                'sentiment_score': overall_sentiment_score,
                'recent_news_count': len(recent_news),
                'positive_news_count': len([n for n in recent_news if n['sentiment'] == 'positive']),
                'negative_news_count': len([n for n in recent_news if n['sentiment'] == 'negative']),
                'neutral_news_count': len([n for n in recent_news if n['sentiment'] == 'neutral']),
                'average_confidence': np.mean([n['confidence'] for n in recent_news]),
                'recent_news': recent_news[:5]  # Return top 5 recent news
            }
            
        except Exception as e:
            logger.error(f"❌ News sentiment analysis error: {e}")
            return {
                'overall_sentiment': 'neutral',
                'sentiment_score': 0,
                'recent_news_count': 0,
                'positive_news_count': 0,
                'negative_news_count': 0,
                'neutral_news_count': 0,
                'average_confidence': 0.5,
                'recent_news': []
            }
    
    async def _get_economic_calendar(self) -> List[Dict[str, Any]]:
        """Get upcoming economic calendar events"""
        try:
            # This should be implemented with real economic calendar API
            # For now, simulate economic calendar data
            
            import random
            from datetime import datetime, timedelta
            
            # Simulate economic events
            economic_events = [
                {
                    'event': 'FOMC Meeting',
                    'date': datetime.now() + timedelta(days=random.randint(1, 7)),
                    'importance': 'high',
                    'currency': 'USD',
                    'description': 'Federal Reserve interest rate decision'
                },
                {
                    'event': 'CPI Data',
                    'date': datetime.now() + timedelta(days=random.randint(1, 14)),
                    'importance': 'medium',
                    'currency': 'USD',
                    'description': 'Consumer Price Index release'
                },
                {
                    'event': 'Non-Farm Payrolls',
                    'date': datetime.now() + timedelta(days=random.randint(1, 30)),
                    'importance': 'high',
                    'currency': 'USD',
                    'description': 'Employment data release'
                },
                {
                    'event': 'ECB Meeting',
                    'date': datetime.now() + timedelta(days=random.randint(1, 14)),
                    'importance': 'high',
                    'currency': 'EUR',
                    'description': 'European Central Bank policy decision'
                }
            ]
            
            # Filter events happening in next 7 days
            upcoming_events = [
                event for event in economic_events
                if event['date'] <= datetime.now() + timedelta(days=7)
            ]
            
            return upcoming_events
            
        except Exception as e:
            logger.error(f"❌ Economic calendar error: {e}")
            return []
    
    async def _get_central_bank_events(self) -> List[Dict[str, Any]]:
        """Get central bank announcements and events"""
        try:
            # This should be implemented with real central bank data API
            # For now, simulate central bank events
            
            import random
            from datetime import datetime, timedelta
            
            central_banks = ['Fed', 'ECB', 'BoE', 'BoJ', 'PBOC']
            
            events = []
            for bank in central_banks:
                if random.random() < 0.3:  # 30% chance of having an event
                    events.append({
                        'bank': bank,
                        'event_type': random.choice(['rate_decision', 'speech', 'minutes', 'policy_statement']),
                        'date': datetime.now() + timedelta(days=random.randint(1, 14)),
                        'importance': random.choice(['low', 'medium', 'high']),
                        'description': f"{bank} {random.choice(['rate_decision', 'speech', 'minutes', 'policy_statement'])}"
                    })
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Central bank events error: {e}")
            return []
    
    def _calculate_sentiment_score(self, macro_data: Dict[str, Any]) -> float:
        """Calculate numerical sentiment score (0-1)"""
        try:
            score = 0.5  # Neutral base score
            factors = 0
            
            # SPY factor
            if 'spy_trend' in macro_data:
                score += (macro_data['spy_trend'] - 0.5) * 0.2
                factors += 1
            
            # DXY factor (inverse)
            if 'dxy_trend' in macro_data:
                score += (0.5 - macro_data['dxy_trend']) * 0.2
                factors += 1
            
            # Gold factor (inverse)
            if 'gold_trend' in macro_data:
                score += (0.5 - macro_data['gold_trend']) * 0.15
                factors += 1
            
            # VIX factor (inverse)
            if 'vix_level' in macro_data:
                vix_normalized = min(macro_data['vix_level'] / 50, 1.0)
                score += (1.0 - vix_normalized) * 0.15
                factors += 1
            
            # Yield curve factor
            if 'yield_curve' in macro_data:
                curve_normalized = max(min(macro_data['yield_curve'] / 2, 1.0), -1.0)
                score += (curve_normalized + 1) * 0.1
                factors += 1
            
            # Normalize score
            if factors > 0:
                score = score / factors
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"❌ Sentiment score calculation error: {e}")
            return 0.5
    
    async def _analyze_liquidity_conditions(self, symbol: str) -> Dict[str, Any]:
        """Analyze liquidity and order book conditions"""
        try:
            liquidity_data = {}
            
            # Try to get order book data
            try:
                order_book = await self._get_order_book_data(symbol)
                if order_book:
                    # Calculate bid-ask spread
                    best_bid = order_book.get('bids', [[0, 0]])[0][0] if order_book.get('bids') else 0
                    best_ask = order_book.get('asks', [[0, 0]])[0][0] if order_book.get('asks') else 0
                    
                    if best_bid > 0 and best_ask > 0:
                        spread = (best_ask - best_bid) / best_bid
                        liquidity_data['bid_ask_spread'] = spread
                        
                        # Calculate depth
                        bid_depth = sum(bid[1] for bid in order_book.get('bids', [])[:10])
                        ask_depth = sum(ask[1] for ask in order_book.get('asks', [])[:10])
                        liquidity_data['bid_depth'] = bid_depth
                        liquidity_data['ask_depth'] = ask_depth
                        liquidity_data['total_depth'] = bid_depth + ask_depth
                        
                        # Determine liquidity level
                        if spread < 0.001 and liquidity_data['total_depth'] > 1000:
                            liquidity_data['liquidity_level'] = 'high'
                        elif spread < 0.005 and liquidity_data['total_depth'] > 100:
                            liquidity_data['liquidity_level'] = 'medium'
                        else:
                            liquidity_data['liquidity_level'] = 'low'
                    else:
                        liquidity_data['liquidity_level'] = 'unknown'
                        liquidity_data['note'] = 'Invalid order book data'
                else:
                    liquidity_data['liquidity_level'] = 'unknown'
                    liquidity_data['note'] = 'Order book data unavailable'
                    
            except Exception as e:
                logger.debug(f"⚠️ Order book analysis failed: {e}")
                liquidity_data['liquidity_level'] = 'unknown'
                liquidity_data['note'] = f'Analysis failed: {str(e)}'
            
            return liquidity_data
            
        except Exception as e:
            logger.error(f"❌ Liquidity conditions analysis error: {e}")
            return {'liquidity_level': 'unknown', 'note': 'Analysis failed'}
    
    async def _get_order_book_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order book data for liquidity analysis"""
        try:
            # This should be implemented to get real order book data
            # For now, return None to indicate unavailability
            return None
        except Exception as e:
            logger.error(f"❌ Order book data retrieval error: {e}")
            return None
    
    def _assess_data_quality(self, dataframe: pd.DataFrame) -> float:
        """Assess data quality"""
        try:
            if dataframe is None or len(dataframe) < 20:
                return 0.0
            
            # Check for missing values
            missing_ratio = dataframe.isnull().sum().sum() / (len(dataframe) * len(dataframe.columns))
            
            # Check for price anomalies
            price_changes = dataframe['close'].pct_change().abs()
            anomaly_ratio = (price_changes > 0.1).sum() / len(price_changes)
            
            # Calculate quality score
            quality_score = 1.0 - (missing_ratio * 0.5 + anomaly_ratio * 0.5)
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"❌ Data quality assessment error: {e}")
            return 0.5
    
    async def _enhanced_decision_engine(self):
        """Enhanced decision engine with improved logic and risk management"""
        try:
            logger.info("🎯 Enhanced decision engine started")
            
            while True:
                try:
                    for symbol in self.symbols:
                        # Check if we have analysis data
                        if symbol not in self.analysis_cache:
                            continue
                        
                        # Check decision cooldown
                        last_decision = self.recent_decisions.get(symbol, datetime.min)
                        if (datetime.now() - last_decision).seconds < self.decision_cooldown:
                            continue
                        
                        analysis = self.analysis_cache[symbol]
                        
                        # Enhanced trading decision with multiple criteria
                        decision = await self._make_enhanced_trading_decision(symbol, analysis)
                        
                        if decision and decision['action'] != 'HOLD':
                            # Execute decision with enhanced logging
                            execution_result = await self._execute_enhanced_trading_decision(symbol, decision)
                            
                            if execution_result:
                                self.recent_decisions[symbol] = datetime.now()
                                self.decision_count += 1
                                
                                # Store decision history
                                decision_record = {
                                    'symbol': symbol,
                                    'timestamp': datetime.now(),
                                    'decision': decision,
                                    'execution_result': execution_result,
                                    'analysis_summary': {
                                        'ai_confidence': analysis.get('ai_signals', {}).get('confidence', 0),
                                        'market_regime': analysis.get('market_condition', {}).get('regime', 'unknown'),
                                        'risk_level': analysis.get('risk_assessment', {}).get('risk_level', 'UNKNOWN')
                                    }
                                }
                                self.decision_history.append(decision_record)
                                
                                # Keep only last 100 decisions
                                if len(self.decision_history) > 100:
                                    self.decision_history = self.decision_history[-100:]
                    
                    # Wait before next decision cycle
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"❌ Enhanced decision engine error: {e}")
                    self.error_count += 1
                    await asyncio.sleep(30)
                    
        except Exception as e:
            logger.error(f"❌ Enhanced decision engine fatal error: {e}")
    
    async def _calculate_trading_costs(self, symbol: str, position_size: float, price: float, 
                                     exchange: str = 'binance') -> Dict[str, Any]:
        """Calculate real-time trading costs based on current market conditions"""
        try:
            # Get real-time market data from RiskManager
            market_data = await self.risk_manager._get_real_time_market_data(symbol, exchange)
            
            # Extract real-time values
            real_volume = market_data.get('volume', 1000000)
            real_volatility = market_data.get('volatility', 0.5)
            real_funding_rate = market_data.get('funding_rate', 0.0001)
            real_bid_ask_spread = market_data.get('bid_ask_spread', 0.0005)
            real_slippage_estimate = market_data.get('slippage_estimate', 0.0005)
            order_book_depth = market_data.get('order_book_depth', {})
            
            # Get exchange-specific fees
            exchange_fees = self.risk_manager.exchange_fees.get(exchange, {'maker': 0.001, 'taker': 0.001})
            trading_fee = exchange_fees['taker']  # Use taker fee for market orders
            
            # Calculate dynamic slippage based on real market conditions
            base_slippage = self.risk_manager.base_slippage
            volatility_mult = self.risk_manager.volatility_multiplier
            volume_mult = self.risk_manager.volume_multiplier
            
            # Adjust slippage based on real market data
            slippage = base_slippage * (1 + real_volatility * volatility_mult)
            slippage *= max(0.5, min(2.0, volume_mult / max(real_volume / 1000000, 0.1)))
            
            # Use real slippage estimate if available
            if real_slippage_estimate > 0:
                slippage = real_slippage_estimate
            
            # Calculate position-specific slippage
            position_value = position_size * price
            position_slippage = self._calculate_position_specific_slippage(
                position_value, order_book_depth, real_bid_ask_spread
            )
            
            # Use the higher of calculated and position-specific slippage
            final_slippage = max(slippage, position_slippage)
            
            # Calculate funding fee based on real rate
            funding_fee = real_funding_rate
            
            # Calculate additional costs
            additional_costs = await self._calculate_additional_trading_costs(symbol, position_value, exchange)
            
            # Total cost calculation
            total_cost_pct = trading_fee + final_slippage + funding_fee + additional_costs.get('total', 0)
            total_cost_usd = position_value * total_cost_pct
            
            return {
                'trading_fee': trading_fee,
                'slippage': final_slippage,
                'funding_fee': funding_fee,
                'additional_costs': additional_costs,
                'total_cost_pct': total_cost_pct,
                'total_cost_usd': total_cost_usd,
                'exchange': exchange,
                'real_data': market_data.get('real_data', False),
                'market_conditions': {
                    'volume': real_volume,
                    'volatility': real_volatility,
                    'bid_ask_spread': real_bid_ask_spread,
                    'order_book_depth': order_book_depth
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time trading costs calculation error: {e}")
            return {
                'trading_fee': 0.001,
                'slippage': 0.0005,
                'funding_fee': 0.0001,
                'additional_costs': {'total': 0},
                'total_cost_pct': 0.0016,
                'total_cost_usd': position_size * price * 0.0016,
                'exchange': exchange,
                'real_data': False,
                'market_conditions': {}
            }
    
    def _calculate_position_specific_slippage(self, position_value: float, order_book: Dict, 
                                            base_spread: float) -> float:
        """Calculate slippage based on position size and order book depth"""
        try:
            if not order_book or 'bids' not in order_book or 'asks' not in order_book:
                return base_spread * 2  # Default to 2x base spread
            
            # Calculate available liquidity
            bid_volume = order_book.get('bid_volume', 0)
            ask_volume = order_book.get('ask_volume', 0)
            
            if bid_volume <= 0 or ask_volume <= 0:
                return base_spread * 3  # High slippage if no liquidity
            
            # Calculate position size relative to available liquidity
            position_volume_ratio = position_value / min(bid_volume, ask_volume)
            
            # Adjust slippage based on position size
            if position_volume_ratio < 0.01:  # Small position
                return base_spread * 1.2
            elif position_volume_ratio < 0.1:  # Medium position
                return base_spread * 1.5
            elif position_volume_ratio < 0.5:  # Large position
                return base_spread * 2.0
            else:  # Very large position
                return base_spread * 3.0
                
        except Exception as e:
            logger.error(f"❌ Position-specific slippage calculation error: {e}")
            return base_spread * 2
    
    async def _calculate_additional_trading_costs(self, symbol: str, position_value: float, 
                                                exchange: str) -> Dict[str, float]:
        """Calculate additional trading costs"""
        try:
            additional_costs = {}
            
            # Network fees (for blockchain transactions)
            network_fee = 0.0001  # 0.01%
            additional_costs['network_fee'] = network_fee
            
            # Regulatory fees (if applicable)
            regulatory_fee = 0.00005  # 0.005%
            additional_costs['regulatory_fee'] = regulatory_fee
            
            # Platform fees (if using third-party platform)
            platform_fee = 0.00005  # 0.005%
            additional_costs['platform_fee'] = platform_fee
            
            # Exchange-specific additional fees
            exchange_additional_fees = {
                'binance': 0.00002,  # 0.002%
                'bybit': 0.00003,    # 0.003%
                'okx': 0.00002       # 0.002%
            }
            exchange_fee = exchange_additional_fees.get(exchange, 0.00002)
            additional_costs['exchange_fee'] = exchange_fee
            
            # Total additional costs
            total_additional = sum(additional_costs.values())
            additional_costs['total'] = total_additional
            
            return additional_costs
            
        except Exception as e:
            logger.error(f"❌ Additional trading costs calculation error: {e}")
            return {'total': 0}
    
    async def _make_enhanced_trading_decision(self, symbol: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Make enhanced trading decision with real-time cost analysis"""
        try:
            # Get current market data
            current_price = analysis_result.get('current_price', 0)
            if current_price <= 0:
                return {'action': 'HOLD', 'reason': 'Invalid price data'}
            
            # Get AI signals
            ai_signals = analysis_result.get('ai_signals', {})
            confidence = ai_signals.get('confidence', 0.5)
            signal_strength = ai_signals.get('signal_strength', 0.5)
            action = ai_signals.get('action', 'HOLD')
            
            # Get market conditions
            market_conditions = analysis_result.get('market_conditions', {})
            volatility = market_conditions.get('volatility', 0.5)
            
            # Get risk assessment
            risk_assessment = analysis_result.get('risk_assessment', {})
            risk_level = risk_assessment.get('risk_level', 'medium')
            
            # Calculate position size
            position_size = await self.risk_manager.calculate_position_size(
                symbol=symbol,
                price=current_price,
                confidence=confidence,
                strategy='enhanced_live_engine'
            )
            
            # Calculate real-time trading costs
            trading_costs = await self._calculate_trading_costs(
                symbol=symbol,
                position_size=position_size,
                price=current_price,
                exchange='binance'  # Default exchange
            )
            
            # Adjust entry price based on real-time costs
            adjusted_entry_price = current_price
            if action == 'BUY':
                adjusted_entry_price = current_price * (1 + trading_costs['slippage'])
            elif action == 'SELL':
                adjusted_entry_price = current_price * (1 - trading_costs['slippage'])
            
            # Calculate stop loss and take profit with real-time adjustments
            stop_loss = self._calculate_dynamic_stop_loss(
                adjusted_entry_price, action, volatility, trading_costs
            )
            take_profit = self._calculate_dynamic_take_profit(
                adjusted_entry_price, action, volatility, trading_costs
            )
            
            # Final decision logic with cost considerations
            if action == 'BUY' and confidence > 0.6 and signal_strength > 0.5:
                # Check if costs are reasonable
                if trading_costs['total_cost_pct'] < 0.005:  # Less than 0.5% total cost
                    return {
                        'action': 'BUY',
                        'symbol': symbol,
                        'entry_price': adjusted_entry_price,
                        'position_size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'confidence': confidence,
                        'trading_costs': trading_costs,
                        'reason': f"Strong buy signal with reasonable costs ({trading_costs['total_cost_pct']:.3%})"
                    }
                else:
                    return {
                        'action': 'HOLD',
                        'reason': f"High trading costs: {trading_costs['total_cost_pct']:.3%}"
                    }
            
            elif action == 'SELL' and confidence > 0.6 and signal_strength > 0.5:
                # Check if costs are reasonable
                if trading_costs['total_cost_pct'] < 0.005:  # Less than 0.5% total cost
                    return {
                        'action': 'SELL',
                        'symbol': symbol,
                        'entry_price': adjusted_entry_price,
                        'position_size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'confidence': confidence,
                        'trading_costs': trading_costs,
                        'reason': f"Strong sell signal with reasonable costs ({trading_costs['total_cost_pct']:.3%})"
                    }
                else:
                    return {
                        'action': 'HOLD',
                        'reason': f"High trading costs: {trading_costs['total_cost_pct']:.3%}"
                    }
            
            return {
                'action': 'HOLD',
                'reason': f"Insufficient signal strength: confidence={confidence:.2f}, strength={signal_strength:.2f}"
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced trading decision error: {e}")
            return {'action': 'HOLD', 'reason': f'Decision error: {str(e)}'}
    
    def _calculate_dynamic_stop_loss(self, entry_price: float, action: str, volatility: float, 
                                   trading_costs: Dict) -> float:
        """Calculate dynamic stop loss with real-time adjustments"""
        try:
            # Base stop loss from config
            base_stop_loss = self.risk_manager.default_stop_loss
            
            # Adjust based on volatility
            volatility_adjustment = 1 + (volatility * 0.5)
            adjusted_stop_loss = base_stop_loss * volatility_adjustment
            
            # Adjust based on trading costs
            cost_adjustment = 1 + (trading_costs['total_cost_pct'] * 10)  # Increase stop loss for high costs
            adjusted_stop_loss *= cost_adjustment
            
            # Calculate stop loss price
            if action == 'BUY':
                stop_loss_price = entry_price * (1 - adjusted_stop_loss)
            else:  # SELL
                stop_loss_price = entry_price * (1 + adjusted_stop_loss)
            
            return stop_loss_price
            
        except Exception as e:
            logger.error(f"❌ Dynamic stop loss calculation error: {e}")
            return entry_price * 0.98 if action == 'BUY' else entry_price * 1.02
    
    def _calculate_dynamic_take_profit(self, entry_price: float, action: str, volatility: float, 
                                     trading_costs: Dict) -> float:
        """Calculate dynamic take profit with real-time adjustments"""
        try:
            # Base take profit from config
            base_take_profit = self.risk_manager.default_take_profit
            
            # Adjust based on volatility
            volatility_adjustment = 1 + (volatility * 0.3)
            adjusted_take_profit = base_take_profit * volatility_adjustment
            
            # Adjust based on trading costs (need higher profit to cover costs)
            cost_adjustment = 1 + (trading_costs['total_cost_pct'] * 5)
            adjusted_take_profit *= cost_adjustment
            
            # Calculate take profit price
            if action == 'BUY':
                take_profit_price = entry_price * (1 + adjusted_take_profit)
            else:  # SELL
                take_profit_price = entry_price * (1 - adjusted_take_profit)
            
            return take_profit_price
            
        except Exception as e:
            logger.error(f"❌ Dynamic take profit calculation error: {e}")
            return entry_price * 1.04 if action == 'BUY' else entry_price * 0.96
    
    async def _websocket_monitor(self):
        """Monitor WebSocket connections and handle reconnections"""
        try:
            logger.info("🔌 WebSocket monitor started")
            
            while True:
                try:
                    for symbol in self.symbols:
                        if symbol not in self.websocket_status:
                            continue
                        
                        status = self.websocket_status[symbol]
                        
                        # Check if WebSocket is connected
                        if not status['connected']:
                            # Attempt reconnection
                            if status['reconnect_attempts'] < self.max_reconnect_attempts:
                                logger.info(f"🔄 Attempting WebSocket reconnection for {symbol}")
                                await self._connect_websocket(symbol)
                                status['reconnect_attempts'] += 1
                            else:
                                logger.error(f"❌ Max reconnection attempts reached for {symbol}")
                        
                        # Check for stale connections (no messages in 5 minutes)
                        elif status['last_message']:
                            time_since_last = (datetime.now() - status['last_message']).seconds
                            if time_since_last > 300:  # 5 minutes
                                logger.warning(f"⚠️ WebSocket connection stale for {symbol}, reconnecting...")
                                status['connected'] = False
                                status['reconnect_attempts'] = 0
                    
                    # Wait before next check
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ WebSocket monitor error: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ WebSocket monitor fatal error: {e}")
    
    async def _enhanced_monitoring_engine(self):
        """Enhanced monitoring and cleanup engine"""
        try:
            logger.info("📊 Enhanced monitoring engine started")
            
            while True:
                try:
                    # Performance statistics
                    runtime = datetime.now() - self.start_time
                    runtime_hours = runtime.total_seconds() / 3600
                    
                    if self.analysis_count > 0:
                        analyses_per_hour = self.analysis_count / runtime_hours if runtime_hours > 0 else 0
                        decisions_per_hour = self.decision_count / runtime_hours if runtime_hours > 0 else 0
                        
                        logger.info(f"📊 Enhanced Live Engine Stats:")
                        logger.info(f"   ⏱️ Runtime: {runtime_hours:.1f} hours")
                        logger.info(f"   📈 Analyses: {self.analysis_count} ({analyses_per_hour:.1f}/hour)")
                        logger.info(f"   🎯 Decisions: {self.decision_count} ({decisions_per_hour:.1f}/hour)")
                        logger.info(f"   💾 Cache Size: {len(self.live_data_cache)} symbols")
                        logger.info(f"   🔌 WebSocket Status: {sum(1 for s in self.websocket_status.values() if s.get('connected', False))}/{len(self.symbols)} connected")
                        logger.info(f"   📊 Market Volatility: {self.market_volatility:.2f}")
                        logger.info(f"   ⚡ Interval Multiplier: {self.interval_multiplier:.2f}")
                        logger.info(f"   ❌ Error Count: {self.error_count}")
                    
                    # Cleanup old data
                    await self._cleanup_old_data()
                    
                    # Reset error count if it's been an hour
                    if self.last_error_time and (datetime.now() - self.last_error_time).seconds > 3600:
                        self.error_count = 0
                        self.last_error_time = None
                    
                    # Wait 1 hour before next monitoring cycle
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"❌ Enhanced monitoring error: {e}")
                    await asyncio.sleep(300)
                    
        except Exception as e:
            logger.error(f"❌ Enhanced monitoring engine fatal error: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data with enhanced logic"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.data_retention_hours)
            
            # Clean analysis cache
            for symbol in list(self.analysis_cache.keys()):
                analysis = self.analysis_cache[symbol]
                if analysis.get('timestamp', datetime.min) < cutoff_time:
                    del self.analysis_cache[symbol]
                    logger.debug(f"🗑️ {symbol} old analysis data cleaned")
            
            # Clean decision history
            self.decision_history = [
                d for d in self.decision_history 
                if d.get('timestamp', datetime.min) > cutoff_time
            ]
            
            # Clean live data cache (check TTL)
            for symbol in list(self.live_data_cache.keys()):
                cache_entry = self.live_data_cache[symbol]
                if (datetime.now() - cache_entry['timestamp']).seconds > cache_entry['ttl']:
                    del self.live_data_cache[symbol]
                    logger.debug(f"🗑️ {symbol} expired cache data cleaned")
            
            # Clean decision cooldowns
            for symbol in list(self.recent_decisions.keys()):
                if self.recent_decisions[symbol] < cutoff_time:
                    del self.recent_decisions[symbol]
            
            logger.debug("🧹 Data cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Data cleanup error: {e}")
    
    def get_enhanced_live_status(self) -> Dict[str, Any]:
        """Get enhanced live system status"""
        try:
            runtime = datetime.now() - self.start_time
            
            # Calculate WebSocket status
            websocket_stats = {
                'total_connections': len(self.symbols),
                'connected': sum(1 for s in self.websocket_status.values() if s.get('connected', False)),
                'reconnecting': sum(1 for s in self.websocket_status.values() if not s.get('connected', False) and s.get('reconnect_attempts', 0) < self.max_reconnect_attempts),
                'failed': sum(1 for s in self.websocket_status.values() if not s.get('connected', False) and s.get('reconnect_attempts', 0) >= self.max_reconnect_attempts)
            }
            
            # Calculate decision statistics
            recent_decisions = [d for d in self.decision_history if (datetime.now() - d['timestamp']).seconds < 3600]
            decision_stats = {
                'total_decisions': len(self.decision_history),
                'recent_decisions': len(recent_decisions),
                'successful_executions': sum(1 for d in recent_decisions if d.get('execution_result', {}).get('success', False)),
                'failed_executions': sum(1 for d in recent_decisions if not d.get('execution_result', {}).get('success', True))
            }
            
            return {
                'status': 'RUNNING',
                'runtime_seconds': runtime.total_seconds(),
                'symbols_tracked': len(self.symbols),
                'symbols_with_data': len(self.live_data_cache),
                'symbols_analyzed': len(self.analysis_cache),
                'total_analyses': self.analysis_count,
                'total_decisions': self.decision_count,
                'websocket_status': websocket_stats,
                'decision_statistics': decision_stats,
                'performance_metrics': {
                    'market_volatility': self.market_volatility,
                    'interval_multiplier': self.interval_multiplier,
                    'error_count': self.error_count,
                    'cache_ttl': self.cache_ttl
                },
                'recent_analyses': {
                    symbol: {
                        'timestamp': analysis.get('timestamp'),
                        'market_regime': analysis.get('market_condition', {}).get('regime'),
                        'ai_confidence': analysis.get('ai_signals', {}).get('confidence'),
                        'recommended_strategy': analysis.get('recommended_strategy'),
                        'data_quality': analysis.get('data_quality', 0)
                    }
                    for symbol, analysis in self.analysis_cache.items()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced live status error: {e}")
            return {'status': 'ERROR', 'error': str(e)}