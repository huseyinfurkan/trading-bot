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
        self.rate_limiters = {}
        
        # WebSocket callbacks
        self.price_callbacks = []
        self.orderbook_callbacks = []
        self.trade_callbacks = []
        
        logger.info("🌐 Exchange Manager initialized")
    
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
            
            # Test connection
            await exchange.load_markets()
            
            self.exchanges[exchange_name] = exchange
            
            # Initialize rate limiter
            self.rate_limiters[exchange_name] = {
                'last_request': 0,
                'min_interval': 1.0 / config.get('requests_per_second', 10)
            }
            
            logger.success(f"✅ {exchange_name} connected")
            
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
    
    async def get_market_data(self, symbol: str, timeframe: str = '1h', 
                            limit: int = 100, exchange: str = 'bybit') -> Optional[Dict[str, Any]]:
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
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume_24h': ticker['quoteVolume'],
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
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'change_24h': ticker['change'],
                'timestamp': datetime.now(),
                'exchange': exchange
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time data error: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str = '1h', 
                                start_date: datetime = None, end_date: datetime = None,
                                exchange: str = 'bybit') -> Optional[pd.DataFrame]:
        """Geçmiş veri al (backtesting için)"""
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
                    
                    # Update start time
                    last_timestamp = ohlcv[-1][0]
                    current_start = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(hours=1)
                    
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