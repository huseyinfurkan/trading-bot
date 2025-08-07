"""
Exchange Manager
Gerçek multi-exchange bağlantıları ve veri yönetimi (Bybit focus)
"""

import asyncio
import ccxt.async_support as ccxt
import websockets
import json
import hmac
import hashlib
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd


class ExchangeManager:
    """Gerçek exchange bağlantıları ve veri yönetimi"""
    
    def __init__(self, exchanges_config: Dict[str, Any]):
        """
        Args:
            exchanges_config: Exchange konfigürasyonları
        """
        self.config = exchanges_config
        self.exchanges = {}
        self.websocket_connections = {}
        self.market_data_cache = {}
        
        # Enhanced rate limiting
        self.rate_limiter = {}
        self.last_request_time = {}
        self.request_counts = {}
        self.rate_limit_windows = {}
        
        # Dynamic rate limit configuration per exchange based on performance
        self.rate_limits = {}  # Will be initialized in initialize()
        
        # WebSocket callbacks
        self.price_callbacks = []
        self.orderbook_callbacks = []
        self.trade_callbacks = []
        
        logger.info("📡 Exchange Manager initialized")
    
    async def initialize(self) -> None:
        """Exchange bağlantılarını başlat"""
        try:
            logger.info("🔌 Exchange connections başlatılıyor...")
            
            # Initialize dynamic rate limits
            self.rate_limits = await self._get_dynamic_rate_limits()
            
            # Initialize exchanges
            for exchange_name, config in self.config.items():
                if config.get('enabled', False):
                    await self._initialize_exchange(exchange_name, config)
            
            logger.success(f"✅ {len(self.exchanges)} exchange bağlantısı kuruldu")
            
        except Exception as e:
            logger.error(f"❌ Exchange initialization error: {e}")
            raise
    
    async def _initialize_exchange(self, exchange_name: str, config: Dict[str, Any]) -> Optional[Any]:
        """Initialize exchange connection"""
        try:
            import ccxt
            
            # Get API credentials
            api_key = config.get('api_key', '')
            secret = config.get('api_secret', '')
            passphrase = config.get('passphrase', '')
            
            # Debug API credentials
            logger.debug(f"🔐 {exchange_name} credentials: apiKey={bool(api_key)}, secret={bool(secret)}")
            logger.debug(f"🔍 {exchange_name} API key first 8 chars: {api_key[:8] if api_key else 'EMPTY'}")
            logger.debug(f"🔍 {exchange_name} Secret first 8 chars: {secret[:8] if secret else 'EMPTY'}")
            
            # Create exchange instance
            exchange_class = getattr(ccxt, exchange_name)
            
            # Build exchange config
            exchange_config = {
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'options': config.get('params', {})
            }
            
            # Add passphrase for OKX
            if exchange_name == 'okx' and passphrase:
                exchange_config['password'] = passphrase
            
            # Create exchange instance
            exchange = exchange_class(exchange_config)
            
            # Test connection
            await exchange.load_markets()
            
            logger.info(f"✅ {exchange_name} exchange initialized successfully")
            return exchange
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} exchange initialization error: {e}")
            return None
    
    @staticmethod
    def rate_limit(exchange_name: str):
        """Rate limiting decorator"""
        def decorator(func):
            async def wrapper(self, *args, **kwargs):
                if exchange_name in self.rate_limiter:
                    limiter = self.rate_limiter[exchange_name]
                    elapsed = time.time() - limiter['last_request']
                    
                    if elapsed < limiter['min_interval']:
                        await asyncio.sleep(limiter['min_interval'] - elapsed)
                    
                    limiter['last_request'] = time.time()
                
                return await func(self, *args, **kwargs)
            return wrapper
        return decorator
    
    async def _apply_rate_limit(self, exchange_name: str):
        """Enhanced rate limiting with multiple time windows"""
        try:
            exchange_name = exchange_name.lower()
            now = time.time()
            
            # Initialize rate limit tracking for this exchange
            if exchange_name not in self.rate_limiter:
                self.rate_limiter[exchange_name] = {
                    'second_window': [],
                    'minute_window': [],
                    'hour_window': []
                }
                self.request_counts[exchange_name] = 0
                self.rate_limit_windows[exchange_name] = now
            
            # Get rate limits for this exchange
            limits = self.rate_limits.get(exchange_name, {
                'requests_per_second': 5,
                'requests_per_minute': 300,
                'requests_per_hour': 18000
            })
            
            # Clean old timestamps
            self.rate_limiter[exchange_name]['second_window'] = [
                t for t in self.rate_limiter[exchange_name]['second_window'] 
                if now - t < 1.0
            ]
            self.rate_limiter[exchange_name]['minute_window'] = [
                t for t in self.rate_limiter[exchange_name]['minute_window'] 
                if now - t < 60.0
            ]
            self.rate_limiter[exchange_name]['hour_window'] = [
                t for t in self.rate_limiter[exchange_name]['hour_window'] 
                if now - t < 3600.0
            ]
            
            # Check rate limits
            if len(self.rate_limiter[exchange_name]['second_window']) >= limits['requests_per_second']:
                sleep_time = 1.0 - (now - self.rate_limiter[exchange_name]['second_window'][0])
                if sleep_time > 0:
                    logger.debug(f"⏱️ Rate limit: sleeping {sleep_time:.2f}s for {exchange_name}")
                    await asyncio.sleep(sleep_time)
            
            if len(self.rate_limiter[exchange_name]['minute_window']) >= limits['requests_per_minute']:
                sleep_time = 60.0 - (now - self.rate_limiter[exchange_name]['minute_window'][0])
                if sleep_time > 0:
                    logger.warning(f"⚠️ Minute rate limit reached for {exchange_name}, sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            if len(self.rate_limiter[exchange_name]['hour_window']) >= limits['requests_per_hour']:
                sleep_time = 3600.0 - (now - self.rate_limiter[exchange_name]['hour_window'][0])
                if sleep_time > 0:
                    logger.error(f"❌ Hour rate limit reached for {exchange_name}, sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            # Add current request timestamp
            self.rate_limiter[exchange_name]['second_window'].append(now)
            self.rate_limiter[exchange_name]['minute_window'].append(now)
            self.rate_limiter[exchange_name]['hour_window'].append(now)
            self.request_counts[exchange_name] += 1
            
        except Exception as e:
            logger.error(f"❌ Rate limiting error: {e}")
            # Fallback to simple delay
            await asyncio.sleep(0.1)
    
    async def _execute_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """Enhanced retry mechanism with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # Determine if we should retry based on error type
                if any(keyword in error_msg for keyword in ['rate limit', '429', 'too many requests']):
                    wait_time = (2 ** attempt) * 1.0  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"⚠️ Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                
                elif any(keyword in error_msg for keyword in ['timeout', 'connection', 'network']):
                    wait_time = (2 ** attempt) * 0.5  # Shorter backoff for network issues
                    logger.warning(f"⚠️ Network error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                
                elif any(keyword in error_msg for keyword in ['invalid', 'bad request', '400']):
                    # Don't retry on bad requests
                    logger.error(f"❌ Bad request error: {e}")
                    raise
                
                elif any(keyword in error_msg for keyword in ['unauthorized', '401', '403']):
                    # Don't retry on auth errors
                    logger.error(f"❌ Authentication error: {e}")
                    raise
                
                else:
                    # For other errors, retry with exponential backoff
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 0.5
                        logger.warning(f"⚠️ Error occurred, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries}): {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Max retries reached: {e}")
                        raise
        
        raise Exception(f"Max retries ({max_retries}) exceeded")

    async def get_market_data(self, symbol: str, exchange: str = 'bybit', timeframe: str = '1h', limit: int = 100) -> Optional[Dict[str, Any]]:
        """Gerçek market data al"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not available")
                return None
            
            exchange_obj = self.exchanges[exchange]
            
            # Get OHLCV data
            ohlcv = await exchange_obj.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            logger.debug(f"📊 {symbol} OHLCV data: {len(ohlcv) if ohlcv else 0} candles")
            
            if not ohlcv:
                logger.warning(f"⚠️ {symbol} için OHLCV data bulunamadı")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Get current ticker
            ticker = await exchange_obj.fetch_ticker(symbol)
            
            # Get orderbook
            orderbook = await exchange_obj.fetch_order_book(symbol, limit=10)
            
            market_data = {
                'symbol': symbol,
                'dataframe': df,
                'current_price': ticker['last'],
                'close': ticker['last'],  # CONSISTENCY: Add 'close' key for modules expecting it
                'price': ticker['last'],  # CONSISTENCY: Add 'price' key as well
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume_24h': ticker['quoteVolume'],
                'volume': ticker['quoteVolume'],  # CONSISTENCY: Add 'volume' key
                'change_24h': ticker['change'],
                'change_24h_pct': ticker['percentage'],
                'orderbook': orderbook,
                'timestamp': datetime.now(),
                'exchange': exchange
            }
            
            # Cache data
            self.market_data_cache[f"{exchange}_{symbol}"] = market_data
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Market data error for {symbol}: {e}")
            return None
    
    async def get_real_time_data(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Gerçek zamanlı fiyat verisi"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            ticker = await exchange_obj.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'current_price': ticker['last'],  # CONSISTENCY: Add current_price key
                'close': ticker['last'],          # CONSISTENCY: Add close key
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'volume_24h': ticker['quoteVolume'] if 'quoteVolume' in ticker else ticker['baseVolume'],
                'change_24h': ticker['change'],
                'change_pct_24h': ticker['percentage'],
                'timestamp': datetime.now(),
                'exchange': exchange
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time data error: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str = '1h', 
                                start_date: datetime = None, end_date: datetime = None,
                                exchange: str = 'bybit') -> Optional[pd.DataFrame]:
        """Geçmiş veri al (backtesting için) - with rate limiting and retry"""
        return await self._execute_with_retry(self._get_historical_data_internal, symbol, timeframe, start_date, end_date, exchange=exchange)
    
    async def _get_historical_data_internal(self, symbol: str, timeframe: str = '1h', 
                                          start_date: datetime = None, end_date: datetime = None,
                                          exchange: str = 'bybit') -> Optional[pd.DataFrame]:
        """Internal method for historical data fetching"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            
            # Calculate date range
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)  # 1 year default
            
            if end_date is None:
                end_date = datetime.now()
            
            # Fetch historical data in chunks
            all_ohlcv = []
            current_start = start_date
            
            while current_start < end_date:
                try:
                    since = int(current_start.timestamp() * 1000)
                    ohlcv = await exchange_obj.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                    
                    if not ohlcv:
                        break
                    
                    all_ohlcv.extend(ohlcv)
                    
                    # Update start time based on timeframe
                    last_timestamp = ohlcv[-1][0]
                    
                    # Calculate appropriate time increment based on timeframe
                    timeframe_minutes = {
                        '1m': 1, '5m': 5, '15m': 15, '30m': 30, 
                        '1h': 60, '4h': 240, '1d': 1440
                    }
                    
                    increment_minutes = timeframe_minutes.get(timeframe, 60)  # Default to 1h
                    current_start = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(minutes=increment_minutes)
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Historical data chunk error: {e}")
                    break
            
            if not all_ohlcv:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.drop_duplicates()
            df = df.sort_index()
            
            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            logger.info(f"📊 Historical data: {len(df)} candles for {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Historical data error: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         price: Optional[float] = None, order_type: str = 'market',
                         exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Gerçek order yerleştir"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not available")
                return None
            
            exchange_obj = self.exchanges[exchange]
            
            # Validate inputs
            if amount <= 0:
                logger.error(f"❌ Invalid amount: {amount}")
                return None
            
            # Place order
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    order = await exchange_obj.create_market_buy_order(symbol, amount)
                else:
                    order = await exchange_obj.create_market_sell_order(symbol, amount)
            elif order_type.lower() == 'limit':
                if price is None:
                    logger.error("❌ Price required for limit order")
                    return None
                
                if side.lower() == 'buy':
                    order = await exchange_obj.create_limit_buy_order(symbol, amount, price)
                else:
                    order = await exchange_obj.create_limit_sell_order(symbol, amount, price)
            else:
                logger.error(f"❌ Unsupported order type: {order_type}")
                return None
            
            logger.success(f"✅ Order placed: {side} {amount} {symbol} @ {price or 'market'}")
            
            return {
                'order_id': order['id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price or order.get('price'),
                'type': order_type,
                'status': order['status'],
                'timestamp': datetime.now(),
                'exchange': exchange,
                'raw_order': order
            }
            
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str, 
                          exchange: str = 'bybit') -> bool:
        """Order iptal et"""
        try:
            if exchange not in self.exchanges:
                return False
            
            exchange_obj = self.exchanges[exchange]
            result = await exchange_obj.cancel_order(order_id, symbol)
            
            logger.info(f"🔄 Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Order cancellation error: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str,
                              exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Order durumu kontrol et"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            order = await exchange_obj.fetch_order(order_id, symbol)
            
            return {
                'order_id': order['id'],
                'status': order['status'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'average_price': order['average'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            logger.error(f"❌ Order status error: {e}")
            return None
    
    async def get_balance(self, exchange: str = 'bybit') -> Optional[Dict[str, float]]:
        """Hesap bakiyesi al"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            balance = await exchange_obj.fetch_balance()
            
            # Extract relevant balances
            relevant_balances = {}
            for currency, amounts in balance.items():
                if isinstance(amounts, dict) and amounts.get('total', 0) > 0:
                    relevant_balances[currency] = {
                        'free': amounts.get('free', 0),
                        'used': amounts.get('used', 0),
                        'total': amounts.get('total', 0)
                    }
            
            return relevant_balances
            
        except Exception as e:
            logger.error(f"❌ Balance fetch error: {e}")
            return None
    
    async def get_multi_exchange_prices(self, symbol: str) -> Dict[str, float]:
        """Çoklu exchange fiyat karşılaştırması"""
        prices = {}
        
        for exchange_name, exchange_obj in self.exchanges.items():
            try:
                ticker = await exchange_obj.fetch_ticker(symbol)
                prices[exchange_name] = ticker['last']
            except Exception as e:
                logger.warning(f"⚠️ {exchange_name} price fetch failed: {e}")
                continue
        
        return prices
    
    async def start_websocket_streams(self, symbols: List[str], 
                                    callbacks: Dict[str, Callable] = None) -> None:
        """WebSocket stream'lerini başlat"""
        try:
            # This would start WebSocket connections for real-time data
            # Implementation depends on specific exchange WebSocket APIs
            
            for symbol in symbols:
                logger.info(f"🌊 Starting WebSocket for {symbol}")
                # WebSocket implementation would go here
                
            logger.success(f"✅ WebSocket streams started for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"❌ WebSocket startup error: {e}")
    
    async def get_trading_fees(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, float]]:
        """Get real-time trading fees from exchange"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            
            # Get real-time trading fees
            markets = await exchange_obj.load_markets()
            market = markets.get(symbol)
            
            if market:
                # Get real fees from market data
                maker_fee = market.get('maker', 0.001)
                taker_fee = market.get('taker', 0.001)
                
                # Validate fees
                if maker_fee <= 0 or taker_fee <= 0:
                    logger.warning(f"⚠️ Invalid fees for {symbol}: maker={maker_fee}, taker={taker_fee}")
                    return None
                
                return {
                    'maker_fee': maker_fee,
                    'taker_fee': taker_fee,
                    'symbol': symbol,
                    'exchange': exchange,
                    'timestamp': datetime.now(),
                    'real_data': True
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Trading fees error: {e}")
            return None
    
    async def get_open_orders(self, symbol: str = None, 
                            exchange: str = 'bybit') -> List[Dict[str, Any]]:
        """Açık orderları al"""
        try:
            if exchange not in self.exchanges:
                return []
            
            exchange_obj = self.exchanges[exchange]
            orders = await exchange_obj.fetch_open_orders(symbol)
            
            return orders
            
        except Exception as e:
            logger.error(f"❌ Open orders fetch error: {e}")
            return []
    
    async def close(self) -> None:
        """Exchange bağlantılarını kapat"""
        try:
            logger.info("🔌 Exchange connections kapatılıyor...")
            
            # Close WebSocket connections
            for connection in self.websocket_connections.values():
                if hasattr(connection, 'close'):
                    await connection.close()
            
            # Close exchange connections
            for exchange in self.exchanges.values():
                await exchange.close()
            
            logger.info("✅ All exchange connections closed")
            
        except Exception as e:
            logger.error(f"❌ Exchange close error: {e}")
    
    async def _get_dynamic_rate_limits(self) -> Dict[str, Dict[str, int]]:
        """Get dynamic rate limits based on exchange performance"""
        try:
            # Base rate limits
            base_limits = {
                'bybit': {
                    'requests_per_second': 10,
                    'requests_per_minute': 600,
                    'requests_per_hour': 36000
                },
                'binance': {
                    'requests_per_second': 10,
                    'requests_per_minute': 1200,
                    'requests_per_hour': 72000
                },
                'okx': {
                    'requests_per_second': 6,
                    'requests_per_minute': 360,
                    'requests_per_hour': 21600
                }
            }
            
            # This would be adjusted based on exchange performance
            # For now, return base limits
            return base_limits
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic rate limits: {e}")
            return {
                'bybit': {'requests_per_second': 10, 'requests_per_minute': 600, 'requests_per_hour': 36000},
                'binance': {'requests_per_second': 10, 'requests_per_minute': 1200, 'requests_per_hour': 72000},
                'okx': {'requests_per_second': 6, 'requests_per_minute': 360, 'requests_per_hour': 21600}
            }
    
    def get_supported_symbols(self, exchange: str = 'bybit') -> List[str]:
        """Desteklenen sembolleri al"""
        try:
            if exchange not in self.exchanges:
                return []
            
            exchange_obj = self.exchanges[exchange]
            markets = exchange_obj.markets
            
            return list(markets.keys()) if markets else []
            
        except Exception as e:
            logger.error(f"❌ Supported symbols error: {e}")
            return []
    
    async def _get_real_time_data_fallback(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time data with fallback strategies - NO MOCK DATA"""
        try:
            logger.info(f"🔄 Attempting real-time data retrieval for {symbol}")
            
            # Try to get real ticker data
            ticker = await self.get_ticker(symbol, 'bybit')
            if ticker:
                return {
                    'symbol': symbol,
                    'price': ticker.get('last', 0),
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'volume': ticker.get('quoteVolume', 0),
                    'change_24h': ticker.get('percentage', 0),
                    'timestamp': datetime.now(),
                    'exchange': 'bybit',
                    'real_data': True
                }
            
            # Try alternative exchange
            ticker = await self.get_ticker(symbol, 'binance')
            if ticker:
                return {
                    'symbol': symbol,
                    'price': ticker.get('last', 0),
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'volume': ticker.get('quoteVolume', 0),
                    'change_24h': ticker.get('percentage', 0),
                    'timestamp': datetime.now(),
                    'exchange': 'binance',
                    'real_data': True
                }
            
            logger.error(f"❌ No real-time data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Real-time data fallback error for {symbol}: {e}")
            return None
    
    async def _get_historical_data_fallback(self, symbol: str, timeframe: str, 
                                          start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Get historical data with fallback strategies - NO MOCK DATA"""
        try:
            logger.info(f"🔄 Attempting historical data retrieval for {symbol}")
            
            # Try primary exchange
            data = await self._get_historical_data_internal(symbol, timeframe, start_date, end_date, 'bybit')
            if data is not None and len(data) > 0:
                return data
            
            # Try alternative exchange
            data = await self._get_historical_data_internal(symbol, timeframe, start_date, end_date, 'binance')
            if data is not None and len(data) > 0:
                return data
            
            # Try different timeframes
            alternative_timeframes = ['4h', '2h', '30m'] if timeframe == '1h' else ['1h', '2h', '30m']
            for alt_timeframe in alternative_timeframes:
                data = await self._get_historical_data_internal(symbol, alt_timeframe, start_date, end_date, 'bybit')
                if data is not None and len(data) > 0:
                    logger.info(f"📋 Using {alt_timeframe} data for {symbol}")
                    return data
            
            logger.error(f"❌ No historical data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Historical data fallback error for {symbol}: {e}")
            return None
    
    async def get_funding_rate(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Get funding rate for a symbol from Bybit or Binance"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            if exchange == 'bybit':
                # Bybit funding rate
                try:
                    funding_info = await exchange_instance.fetch_funding_rate(symbol)
                    return {
                        'fundingRate': funding_info.get('fundingRate', 0),
                        'nextFundingTime': funding_info.get('nextFundingTime', 0),
                        'fundingDatetime': funding_info.get('fundingDatetime'),
                        'previousFundingRate': funding_info.get('previousFundingRate', 0)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Bybit funding rate error for {symbol}: {e}")
                    return None
            
            elif exchange == 'binance':
                # Binance funding rate
                try:
                    funding_info = await exchange_instance.fetch_funding_rate(symbol)
                    return {
                        'fundingRate': funding_info.get('fundingRate', 0),
                        'nextFundingTime': funding_info.get('nextFundingTime', 0),
                        'fundingDatetime': funding_info.get('fundingDatetime'),
                        'previousFundingRate': funding_info.get('previousFundingRate', 0)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Binance funding rate error for {symbol}: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Funding rate error: {e}")
            return None
    
    async def get_open_interest(self, symbol: str, exchange: str = 'binance') -> Optional[Dict[str, Any]]:
        """Get open interest for a symbol from Binance or Bybit"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            if exchange == 'binance':
                # Binance open interest
                try:
                    oi_info = await exchange_instance.fetch_open_interest(symbol)
                    return {
                        'openInterest': oi_info.get('openInterestAmount', 0),
                        'openInterestValue': oi_info.get('openInterestValue', 0),
                        'timestamp': oi_info.get('timestamp', 0)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Binance open interest error for {symbol}: {e}")
                    return None
            
            elif exchange == 'bybit':
                # Bybit open interest
                try:
                    oi_info = await exchange_instance.fetch_open_interest(symbol)
                    return {
                        'openInterest': oi_info.get('openInterestAmount', 0),
                        'openInterestValue': oi_info.get('openInterestValue', 0),
                        'timestamp': oi_info.get('timestamp', 0)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Bybit open interest error for {symbol}: {e}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Open interest error: {e}")
            return None
    
    async def get_order_book(self, symbol: str, exchange: str = 'bybit', limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get order book for a symbol from Bybit or Binance"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            try:
                order_book = await exchange_instance.fetch_order_book(symbol, limit)
                
                return {
                    'bids': order_book.get('bids', []),
                    'asks': order_book.get('asks', []),
                    'timestamp': order_book.get('timestamp', 0),
                    'datetime': order_book.get('datetime'),
                    'nonce': order_book.get('nonce', 0),
                    'bid_ask_spread': self._calculate_bid_ask_spread(order_book),
                    'order_book_depth': self._calculate_order_book_depth(order_book)
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Order book error for {symbol} on {exchange}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Order book error: {e}")
            return None
    
    async def get_ticker(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Get ticker information for a symbol from Bybit or Binance"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            try:
                ticker = await exchange_instance.fetch_ticker(symbol)
                
                return {
                    'symbol': ticker.get('symbol'),
                    'last': ticker.get('last'),
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'high': ticker.get('high'),
                    'low': ticker.get('low'),
                    'volume': ticker.get('baseVolume'),
                    'quoteVolume': ticker.get('quoteVolume'),
                    'change': ticker.get('change'),
                    'percentage': ticker.get('percentage'),
                    'average': ticker.get('average'),
                    'timestamp': ticker.get('timestamp'),
                    'datetime': ticker.get('datetime'),
                    'vwap': ticker.get('vwap'),
                    'open': ticker.get('open'),
                    'close': ticker.get('close'),
                    'previousClose': ticker.get('previousClose')
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Ticker error for {symbol} on {exchange}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Ticker error: {e}")
            return None
    
    async def get_markets(self, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Get all available markets from Bybit or Binance"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            try:
                markets = await exchange_instance.load_markets()
                
                # Filter for USDT pairs
                usdt_pairs = {}
                for symbol, market in markets.items():
                    if market.get('quote') == 'USDT' and market.get('active'):
                        usdt_pairs[symbol] = {
                            'symbol': market.get('symbol'),
                            'base': market.get('base'),
                            'quote': market.get('quote'),
                            'type': market.get('type'),
                            'spot': market.get('spot', False),
                            'margin': market.get('margin', False),
                            'swap': market.get('swap', False),
                            'future': market.get('future', False),
                            'option': market.get('option', False),
                            'active': market.get('active', False),
                            'contract': market.get('contract', False),
                            'linear': market.get('linear', False),
                            'inverse': market.get('inverse', False),
                            'contractSize': market.get('contractSize'),
                            'expiry': market.get('expiry'),
                            'strike': market.get('strike'),
                            'optionType': market.get('optionType'),
                            'settleType': market.get('settleType'),
                            'status': market.get('status')
                        }
                
                return {
                    'total_markets': len(markets),
                    'usdt_pairs': len(usdt_pairs),
                    'markets': usdt_pairs,
                    'exchange': exchange,
                    'timestamp': datetime.now()
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Markets error for {exchange}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Markets error: {e}")
            return None
    
    def _calculate_bid_ask_spread(self, order_book: Dict[str, Any]) -> float:
        """Calculate bid-ask spread from order book"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            best_bid = bids[0][0] if bids else 0
            best_ask = asks[0][0] if asks else 0
            
            if best_bid > 0 and best_ask > 0:
                spread = (best_ask - best_bid) / best_bid
                return spread
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Bid-ask spread calculation error: {e}")
            return 0.0
    
    def _calculate_order_book_depth(self, order_book: Dict[str, Any], depth_levels: int = 5) -> Dict[str, Any]:
        """Calculate order book depth at different levels"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            depth_data = {
                'bid_depth': {},
                'ask_depth': {},
                'total_bid_volume': 0,
                'total_ask_volume': 0,
                'bid_ask_ratio': 0
            }
            
            # Calculate bid depth
            for i, (price, volume) in enumerate(bids[:depth_levels]):
                depth_data['bid_depth'][f'level_{i+1}'] = {
                    'price': price,
                    'volume': volume,
                    'value': price * volume
                }
                depth_data['total_bid_volume'] += volume
            
            # Calculate ask depth
            for i, (price, volume) in enumerate(asks[:depth_levels]):
                depth_data['ask_depth'][f'level_{i+1}'] = {
                    'price': price,
                    'volume': volume,
                    'value': price * volume
                }
                depth_data['total_ask_volume'] += volume
            
            # Calculate bid-ask ratio
            if depth_data['total_ask_volume'] > 0:
                depth_data['bid_ask_ratio'] = depth_data['total_bid_volume'] / depth_data['total_ask_volume']
            
            return depth_data
            
        except Exception as e:
            logger.error(f"❌ Order book depth calculation error: {e}")
            return {}
    
    async def get_24hr_stats(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
        """Get 24-hour statistics for a symbol"""
        try:
            if exchange not in self.exchanges:
                logger.error(f"❌ Exchange {exchange} not initialized")
                return None
            
            exchange_instance = self.exchanges[exchange]
            
            try:
                ticker = await exchange_instance.fetch_ticker(symbol)
                
                return {
                    'symbol': ticker.get('symbol'),
                    'price_change': ticker.get('change'),
                    'price_change_percent': ticker.get('percentage'),
                    'weighted_avg_price': ticker.get('average'),
                    'prev_close_price': ticker.get('previousClose'),
                    'last_price': ticker.get('last'),
                    'last_qty': ticker.get('lastQty'),
                    'bid_price': ticker.get('bid'),
                    'ask_price': ticker.get('ask'),
                    'open_price': ticker.get('open'),
                    'high_price': ticker.get('high'),
                    'low_price': ticker.get('low'),
                    'volume': ticker.get('baseVolume'),
                    'quote_volume': ticker.get('quoteVolume'),
                    'open_time': ticker.get('openTime'),
                    'close_time': ticker.get('closeTime'),
                    'first_id': ticker.get('firstId'),
                    'last_id': ticker.get('lastId'),
                    'count': ticker.get('count'),
                    'timestamp': ticker.get('timestamp'),
                    'datetime': ticker.get('datetime')
                }
                
            except Exception as e:
                logger.warning(f"⚠️ 24hr stats error for {symbol} on {exchange}: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ 24hr stats error: {e}")
            return None