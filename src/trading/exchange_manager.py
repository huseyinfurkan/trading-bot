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
        
        # Rate limit configuration per exchange
        self.rate_limits = {
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
        
        # WebSocket callbacks
        self.price_callbacks = []
        self.orderbook_callbacks = []
        self.trade_callbacks = []
        
        logger.info("📡 Exchange Manager initialized")
    
    async def initialize(self) -> None:
        """Exchange bağlantılarını başlat"""
        try:
            logger.info("🔌 Exchange connections başlatılıyor...")
            
            # Initialize exchanges
            for exchange_name, config in self.config.items():
                if config.get('enabled', False):
                    await self._initialize_exchange(exchange_name, config)
            
            logger.success(f"✅ {len(self.exchanges)} exchange bağlantısı kuruldu")
            
        except Exception as e:
            logger.error(f"❌ Exchange initialization error: {e}")
            raise
    
    async def _initialize_exchange(self, exchange_name: str, config: Dict[str, Any]) -> None:
        """Tek exchange'i başlat"""
        try:
            if exchange_name.lower() == 'bybit':
                exchange_class = ccxt.bybit
            elif exchange_name.lower() == 'binance':
                exchange_class = ccxt.binance
            elif exchange_name.lower() == 'okx':
                exchange_class = ccxt.okx
            else:
                logger.warning(f"⚠️ Unsupported exchange: {exchange_name}")
                return
            
            # Debug API credentials
            api_key = config.get('api_key', '')
            secret = config.get('secret', '')
            logger.debug(f"🔐 {exchange_name} credentials: apiKey={bool(api_key)}, secret={bool(secret)}")
            logger.debug(f"🔍 {exchange_name} API key first 8 chars: {api_key[:8] if api_key else 'EMPTY'}")
            logger.debug(f"🔍 {exchange_name} Secret first 8 chars: {secret[:8] if secret else 'EMPTY'}")
            
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': secret,
                'password': config.get('passphrase', ''),  # OKX için
                'sandbox': config.get('sandbox', True),  # Paper trading için
                'enableRateLimit': True,
                'options': {
                    'defaultType': config.get('default_type', 'spot'),  # spot, future, option
                }
            })
            
            # Test connection - PUBLIC FIRST, then private if needed
            try:
                # Use public ticker endpoint for initial test (no API key needed)
                ticker = await exchange.fetch_ticker('BTC/USDT')
                logger.success(f"✅ {exchange_name} public connection verified")
                
                # Now test private API with balance check
                try:
                    balance = await exchange.fetch_balance()
                    logger.success(f"✅ {exchange_name} private API verified")
                    # Load markets AFTER API verification
                    await exchange.load_markets()
                    logger.success(f"✅ {exchange_name} markets loaded")
                except Exception as private_error:
                    if "10003" in str(private_error) or "invalid" in str(private_error).lower():
                        logger.error(f"❌ {exchange_name} API credentials invalid: {private_error}")
                        logger.error(f"🔑 Please check your API keys in .env file")
                        raise
                    else:
                        logger.warning(f"⚠️ {exchange_name} private API issue: {private_error}")
                        logger.info(f"📊 Continuing with public data only...")
                        # Load markets with public access only
                        exchange.apiKey = ''
                        exchange.secret = ''
                        await exchange.load_markets()
                        exchange._public_only = True
                        
            except Exception as e:
                logger.error(f"❌ {exchange_name} connection failed: {e}")
                logger.error(f"🌐 Check your internet connection and API credentials")
                raise
            
            self.exchanges[exchange_name] = exchange
            
            # Initialize rate limiter
            self.rate_limiter[exchange_name] = {
                'last_request': 0,
                'min_interval': 1.0 / config.get('requests_per_second', 10)
            }
            
            if hasattr(exchange, '_public_only') and exchange._public_only:
                logger.success(f"✅ {exchange_name} connected (public data only)")
            else:
                logger.success(f"✅ {exchange_name} connected successfully")
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} connection failed: {e}")
            raise
    
    @staticmethod
    def rate_limit(exchange_name: str):
        """Rate limiting decorator"""
        def decorator(func):
            async def wrapper(self, *args, **kwargs):
                if exchange_name in self.rate_limiters:
                    limiter = self.rate_limiters[exchange_name]
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

    async def get_market_data(self, symbol: str, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
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
        """Trading ücretleri al"""
        try:
            if exchange not in self.exchanges:
                return None
            
            exchange_obj = self.exchanges[exchange]
            
            # Get trading fees
            markets = await exchange_obj.load_markets()
            market = markets.get(symbol)
            
            if market:
                return {
                    'maker_fee': market.get('maker', 0.001),
                    'taker_fee': market.get('taker', 0.001)
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
    
    def _generate_mock_real_time_data(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic mock data for demo"""
        import random
        
        # Base prices for major coins
        base_prices = {
            'BTCUSDT': 110000, 'ETHUSDT': 3500, 'BNBUSDT': 790, 'ADAUSDT': 0.75,
            'SOLUSDT': 170, 'MATICUSDT': 1.1, 'DOTUSDT': 8.5, 'LINKUSDT': 22,
            'AVAXUSDT': 55, 'ATOMUSDT': 12, 'UNIUSDT': 8, 'AAVEUSDT': 180,
            'COMPUSDT': 95, 'SUSHIUSDT': 2.5
        }
        
        base_price = base_prices.get(symbol, 100)
        # Add realistic price fluctuation (±0.5%)
        price_variation = random.uniform(-0.005, 0.005)
        current_price = base_price * (1 + price_variation)
        
        # Generate bid/ask spread (0.01-0.05%)
        spread = random.uniform(0.0001, 0.0005)
        bid = current_price * (1 - spread)
        ask = current_price * (1 + spread)
        
        return {
            'symbol': symbol,
            'price': round(current_price, 6),
            'bid': round(bid, 6),
            'ask': round(ask, 6),
            'volume': round(random.uniform(1000, 10000), 2),
            'change_24h': round(random.uniform(-5, 5), 2),
            'timestamp': datetime.now(),
            'exchange': 'bybit_mock'
        }
    
    def _generate_mock_historical_data(self, symbol: str, timeframe: str, 
                                     start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate realistic mock historical data for demo"""
        import random
        import pandas as pd
        from datetime import timedelta
        
        # Base prices for major coins
        base_prices = {
            'BTCUSDT': 110000, 'ETHUSDT': 3500, 'BNBUSDT': 790, 'ADAUSDT': 0.75,
            'SOLUSDT': 170, 'MATICUSDT': 1.1, 'DOTUSDT': 8.5, 'LINKUSDT': 22,
            'AVAXUSDT': 55, 'ATOMUSDT': 12, 'UNIUSDT': 8, 'AAVEUSDT': 180,
            'COMPUSDT': 95, 'SUSHIUSDT': 2.5
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generate time series
        if timeframe == '1h':
            delta = timedelta(hours=1)
        elif timeframe == '4h':
            delta = timedelta(hours=4)
        elif timeframe == '1d':
            delta = timedelta(days=1)
        else:
            delta = timedelta(hours=1)
        
        timestamps = []
        current = start_date or (datetime.now() - timedelta(days=30))
        end = end_date or datetime.now()
        
        while current < end:
            timestamps.append(current)
            current += delta
        
        # Generate realistic OHLCV data
        data = []
        current_price = base_price
        
        for i, timestamp in enumerate(timestamps):
            # Add some trend and random walk
            trend = random.uniform(-0.002, 0.002)  # ±0.2% trend
            volatility = random.uniform(-0.01, 0.01)  # ±1% volatility
            
            # Calculate OHLC
            open_price = current_price
            close_price = current_price * (1 + trend + volatility)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
            volume = random.uniform(1000, 50000)
            
            data.append({
                'timestamp': timestamp,
                'open': round(open_price, 6),
                'high': round(high_price, 6),
                'low': round(low_price, 6),
                'close': round(close_price, 6),
                'volume': round(volume, 2)
            })
            
            current_price = close_price
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df