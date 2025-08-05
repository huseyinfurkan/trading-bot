"""
Exchange Manager
Çoklu exchange bağlantılarını yönetir ve API çağrılarını koordine eder
"""

import ccxt.async_support as ccxt
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from loguru import logger
import time
from functools import wraps


def rate_limit(max_calls_per_second: int = 10):
    """Rate limiting decorator"""
    def decorator(func):
        calls = []
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls older than 1 second
            while calls and calls[0] <= now - 1:
                calls.pop(0)
            
            if len(calls) >= max_calls_per_second:
                sleep_time = 1 - (now - calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            calls.append(time.time())
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class ExchangeManager:
    """Exchange yöneticisi - Çoklu exchange bağlantılarını yönetir"""
    
    def __init__(self, exchanges_config: Dict[str, Any]):
        """
        Args:
            exchanges_config: Exchange konfigürasyonları
        """
        self.config = exchanges_config
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self.active_exchanges: List[str] = []
        self.rate_limits: Dict[str, int] = {}
        self.last_requests: Dict[str, float] = {}
        
    async def initialize(self) -> None:
        """Tüm exchange'leri başlat"""
        try:
            for exchange_name, exchange_config in self.config.items():
                if exchange_config.get('enable_test', True):
                    await self._initialize_exchange(exchange_name, exchange_config)
            
            logger.info(f"✅ {len(self.active_exchanges)} exchange başlatıldı: {self.active_exchanges}")
            
        except Exception as e:
            logger.error(f"❌ Exchange başlatma hatası: {e}")
            raise
    
    async def _initialize_exchange(self, name: str, config: Dict[str, Any]) -> None:
        """Tek bir exchange'i başlat"""
        try:
            # Exchange class'ını al
            exchange_class = getattr(ccxt, name)
            
            # Konfigürasyon hazırla
            exchange_config = {
                'apiKey': config.get('api_key'),
                'secret': config.get('secret'),
                'sandbox': config.get('sandbox', False),
                'enableRateLimit': True,
                'timeout': 30000,
            }
            
            # OKX için passphrase ekle
            if name == 'okx' and config.get('passphrase'):
                exchange_config['password'] = config.get('passphrase')
            
            # Exchange'i oluştur
            exchange = exchange_class(exchange_config)
            
            # Test bağlantısı
            await self._test_connection(exchange, name)
            
            self.exchanges[name] = exchange
            self.active_exchanges.append(name)
            self.rate_limits[name] = config.get('rate_limit', 10)
            self.last_requests[name] = 0
            
            logger.info(f"✅ {name} exchange başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ {name} exchange başlatma hatası: {e}")
            if config.get('required', False):
                raise
    
    async def _test_connection(self, exchange: ccxt.Exchange, name: str) -> None:
        """Exchange bağlantısını test et"""
        try:
            # Test API çağrısı
            if hasattr(exchange, 'fetch_status'):
                try:
                    status = await exchange.fetch_status()
                    if status and status.get('status') != 'ok':
                        logger.warning(f"⚠️ {name} exchange durumu: {status}")
                except Exception as e:
                    logger.warning(f"⚠️ {name} status kontrolü başarısız: {e}")
            
            # Balance çağrısı ile API anahtarlarını test et (eğer API keys varsa)
            if exchange.apiKey and exchange.secret:
                try:
                    await exchange.fetch_balance()
                    logger.info(f"✅ {name} API anahtarları doğrulandı")
                except Exception as e:
                    logger.warning(f"⚠️ {name} API anahtarları test edilemedi: {e}")
            else:
                logger.info(f"ℹ️ {name} için API anahtarları ayarlanmamış (sadece okuma modu)")
            
        except Exception as e:
            logger.warning(f"⚠️ {name} bağlantı testi başarısız: {e}")
    
    @rate_limit(max_calls_per_second=10)
    async def get_market_data(self, symbol: str, timeframe: str = '1m', 
                             limit: int = 100, exchange_name: str = None) -> Optional[Dict]:
        """Market verilerini al"""
        try:
            # En uygun exchange'i seç
            if not exchange_name:
                exchange_name = await self._select_best_exchange(symbol)
            
            if not exchange_name or exchange_name not in self.exchanges:
                logger.warning(f"⚠️ {symbol} için uygun exchange bulunamadı")
                return None
            
            exchange = self.exchanges[exchange_name]
            
            # Rate limiting kontrol
            await self._check_rate_limit(exchange_name)
            
            # OHLCV verilerini al
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                return None
            
            # DataFrame'e dönüştür
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Ticker bilgilerini al
            ticker = await exchange.fetch_ticker(symbol)
            
            # Son veriyi döndür
            latest = df.iloc[-1]
            
            return {
                'symbol': symbol,
                'exchange': exchange_name,
                'timestamp': latest['timestamp'],
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'close': latest['close'],
                'volume': latest['volume'],
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'change': ticker.get('change'),
                'percentage': ticker.get('percentage'),
                'dataframe': df
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} market data hatası: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, timeframe: str = '1h', 
                                 days: int = 30, exchange_name: str = None) -> pd.DataFrame:
        """Geçmiş verileri al"""
        try:
            if not exchange_name:
                exchange_name = await self._select_best_exchange(symbol)
            
            if not exchange_name or exchange_name not in self.exchanges:
                return pd.DataFrame()
            
            exchange = self.exchanges[exchange_name]
            
            # Zaman aralığını hesapla
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            # Veri limitini hesapla
            timeframe_minutes = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440
            }
            
            minutes = timeframe_minutes.get(timeframe, 60)
            limit = min(1000, days * 24 * 60 // minutes)
            
            await self._check_rate_limit(exchange_name)
            
            # Verileri al
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            
            if not ohlcv:
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"📊 {symbol} için {len(df)} adet {timeframe} verisi alındı")
            return df
            
        except Exception as e:
            logger.error(f"❌ {symbol} geçmiş veri hatası: {e}")
            return pd.DataFrame()
    
    async def get_orderbook(self, symbol: str, exchange_name: str = None) -> Optional[Dict]:
        """Order book bilgilerini al"""
        try:
            if not exchange_name:
                exchange_name = await self._select_best_exchange(symbol)
            
            if not exchange_name or exchange_name not in self.exchanges:
                return None
            
            exchange = self.exchanges[exchange_name]
            await self._check_rate_limit(exchange_name)
            
            orderbook = await exchange.fetch_order_book(symbol)
            
            return {
                'symbol': symbol,
                'exchange': exchange_name,
                'bids': orderbook['bids'][:10],  # En iyi 10 bid
                'asks': orderbook['asks'][:10],  # En iyi 10 ask
                'timestamp': orderbook['timestamp'],
                'spread': orderbook['asks'][0][0] - orderbook['bids'][0][0] if orderbook['bids'] and orderbook['asks'] else 0
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} orderbook hatası: {e}")
            return None
    
    async def get_account_balance(self, exchange_name: str) -> Optional[Dict]:
        """Hesap bakiyesini al"""
        try:
            if exchange_name not in self.exchanges:
                logger.warning(f"⚠️ Exchange bulunamadı: {exchange_name}")
                return None
            
            exchange = self.exchanges[exchange_name]
            await self._check_rate_limit(exchange_name)
            
            balance = await exchange.fetch_balance()
            
            # Sadece sıfırdan büyük bakiyeleri döndür
            filtered_balance = {}
            for currency, amounts in balance.items():
                if currency in ['info', 'free', 'used', 'total']:
                    continue
                
                if isinstance(amounts, dict) and amounts.get('total', 0) > 0:
                    filtered_balance[currency] = amounts
            
            return {
                'exchange': exchange_name,
                'balances': filtered_balance,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} bakiye hatası: {e}")
            return None
    
    async def place_order(self, symbol: str, side: str, amount: float, 
                         price: float = None, order_type: str = 'market',
                         exchange_name: str = None) -> Optional[Dict]:
        """Emir ver"""
        try:
            if not exchange_name:
                exchange_name = await self._select_best_exchange(symbol)
            
            if not exchange_name or exchange_name not in self.exchanges:
                logger.error(f"❌ {symbol} için uygun exchange bulunamadı")
                return None
            
            exchange = self.exchanges[exchange_name]
            await self._check_rate_limit(exchange_name)
            
            # Emir ver
            if order_type == 'market':
                order = await exchange.create_market_order(symbol, side, amount)
            elif order_type == 'limit':
                if not price:
                    raise ValueError("Limit emir için fiyat gerekli")
                order = await exchange.create_limit_order(symbol, side, amount, price)
            else:
                raise ValueError(f"Desteklenmeyen emir türü: {order_type}")
            
            logger.info(f"✅ Emir verildi: {symbol} {side} {amount} @ {price or 'market'}")
            
            return {
                'id': order['id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'type': order_type,
                'exchange': exchange_name,
                'timestamp': order.get('timestamp'),
                'status': order.get('status'),
                'filled': order.get('filled', 0),
                'remaining': order.get('remaining', amount),
                'info': order
            }
            
        except Exception as e:
            logger.error(f"❌ Emir verme hatası: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str, 
                          exchange_name: str) -> bool:
        """Emir iptal et"""
        try:
            if exchange_name not in self.exchanges:
                return False
            
            exchange = self.exchanges[exchange_name]
            await self._check_rate_limit(exchange_name)
            
            await exchange.cancel_order(order_id, symbol)
            logger.info(f"✅ Emir iptal edildi: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Emir iptal hatası: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str, 
                              exchange_name: str) -> Optional[Dict]:
        """Emir durumunu kontrol et"""
        try:
            if exchange_name not in self.exchanges:
                return None
            
            exchange = self.exchanges[exchange_name]
            await self._check_rate_limit(exchange_name)
            
            order = await exchange.fetch_order(order_id, symbol)
            
            return {
                'id': order['id'],
                'status': order['status'],
                'filled': order.get('filled', 0),
                'remaining': order.get('remaining', 0),
                'average': order.get('average'),
                'fee': order.get('fee'),
                'trades': order.get('trades', [])
            }
            
        except Exception as e:
            logger.error(f"❌ Emir durumu hatası: {e}")
            return None
    
    async def _select_best_exchange(self, symbol: str) -> Optional[str]:
        """Sembol için en uygun exchange'i seç"""
        try:
            best_exchange = None
            best_volume = 0
            
            for exchange_name in self.active_exchanges:
                try:
                    exchange = self.exchanges[exchange_name]
                    
                    # Sembolün desteklendiğini kontrol et
                    markets = await exchange.load_markets()
                    if symbol not in markets:
                        continue
                    
                    # Ticker al ve volume kontrol et
                    ticker = await exchange.fetch_ticker(symbol)
                    volume = ticker.get('quoteVolume', 0)
                    
                    if volume > best_volume:
                        best_volume = volume
                        best_exchange = exchange_name
                        
                except Exception:
                    continue
            
            return best_exchange
            
        except Exception as e:
            logger.error(f"❌ Exchange seçim hatası: {e}")
            return self.active_exchanges[0] if self.active_exchanges else None
    
    async def _check_rate_limit(self, exchange_name: str) -> None:
        """Rate limit kontrolü"""
        if exchange_name not in self.rate_limits:
            return
        
        now = time.time()
        last_request = self.last_requests.get(exchange_name, 0)
        min_interval = 1.0 / self.rate_limits[exchange_name]
        
        time_since_last = now - last_request
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_requests[exchange_name] = time.time()
    
    async def get_supported_symbols(self, exchange_name: str = None) -> List[str]:
        """Desteklenen sembolleri getir"""
        try:
            symbols = set()
            
            exchanges_to_check = [exchange_name] if exchange_name else self.active_exchanges
            
            for exchange_name in exchanges_to_check:
                if exchange_name not in self.exchanges:
                    continue
                
                exchange = self.exchanges[exchange_name]
                markets = await exchange.load_markets()
                symbols.update(markets.keys())
            
            return sorted(list(symbols))
            
        except Exception as e:
            logger.error(f"❌ Sembol listesi hatası: {e}")
            return []
    
    async def close(self) -> None:
        """Tüm exchange bağlantılarını kapat"""
        for exchange_name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"✅ {exchange_name} bağlantısı kapatıldı")
            except Exception as e:
                logger.error(f"❌ {exchange_name} kapatma hatası: {e}")
        
        self.exchanges.clear()
        self.active_exchanges.clear()
        logger.info("✅ Tüm exchange bağlantıları kapatıldı")