import ccxt
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime, timedelta

class BinanceClient:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exchange = None
        self._initialize_exchange()
        
    def _initialize_exchange(self):
        """Exchange bağlantısını başlatır"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.config.BINANCE_API_KEY,
                'secret': self.config.BINANCE_SECRET_KEY,
                'sandbox': False,  # Gerçek trading için False
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Test connection
            self.exchange.load_markets()
            self.logger.info("Binance bağlantısı başarılı")
            
        except Exception as e:
            self.logger.error(f"Binance bağlantı hatası: {str(e)}")
            raise
    
    def get_balance(self, currency: str = 'USDT') -> float:
        """Bakiye sorgular"""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get(currency, {}).get('free', 0.0)
        except Exception as e:
            self.logger.error(f"Bakiye sorgulama hatası: {str(e)}")
            return 0.0
    
    def get_current_price(self, symbol: str) -> float:
        """Güncel fiyat sorgular"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"Fiyat sorgulama hatası: {str(e)}")
            return 0.0
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 500) -> pd.DataFrame:
        """OHLCV verilerini alır"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"OHLCV veri alma hatası: {str(e)}")
            return pd.DataFrame()
    
    def place_order(self, symbol: str, side: str, amount: float, 
                   price: Optional[float] = None, order_type: str = 'market') -> Dict[str, Any]:
        """Sipariş verir"""
        try:
            # Order parameters
            order_params = {
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount
            }
            
            if price and order_type == 'limit':
                order_params['price'] = price
            
            # Place order
            order = self.exchange.create_order(**order_params)
            
            self.logger.info(f"Sipariş verildi: {symbol} {side} {amount} @ {price or 'market'}")
            
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'status': order['status'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            self.logger.error(f"Sipariş verme hatası: {str(e)}")
            return {}
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Siparişi iptal eder"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            self.logger.info(f"Sipariş iptal edildi: {order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Sipariş iptal hatası: {str(e)}")
            return False
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Açık siparişleri getirir"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            self.logger.error(f"Açık sipariş sorgulama hatası: {str(e)}")
            return []
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Sipariş durumunu sorgular"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            self.logger.error(f"Sipariş durumu sorgulama hatası: {str(e)}")
            return {}
    
    def get_trade_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Trade geçmişini getirir"""
        try:
            trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            self.logger.error(f"Trade geçmişi sorgulama hatası: {str(e)}")
            return []
    
    def get_position_size(self, symbol: str) -> float:
        """Pozisyon büyüklüğünü sorgular"""
        try:
            balance = self.exchange.fetch_balance()
            # Spot trading için basit bakiye kontrolü
            base_currency = symbol.split('/')[0]
            return balance.get(base_currency, {}).get('free', 0.0)
        except Exception as e:
            self.logger.error(f"Pozisyon büyüklüğü sorgulama hatası: {str(e)}")
            return 0.0
    
    def calculate_order_amount(self, symbol: str, usdt_amount: float) -> float:
        """USDT miktarına göre coin miktarını hesaplar"""
        try:
            current_price = self.get_current_price(symbol)
            if current_price > 0:
                return usdt_amount / current_price
            return 0.0
        except Exception as e:
            self.logger.error(f"Order amount hesaplama hatası: {str(e)}")
            return 0.0
    
    def get_market_info(self, symbol: str) -> Dict[str, Any]:
        """Market bilgilerini getirir"""
        try:
            market = self.exchange.market(symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'base': market['base'],
                'quote': market['quote'],
                'min_amount': market.get('limits', {}).get('amount', {}).get('min', 0),
                'max_amount': market.get('limits', {}).get('amount', {}).get('max', float('inf')),
                'min_cost': market.get('limits', {}).get('cost', {}).get('min', 0),
                'precision': market.get('precision', {}),
                'current_price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume_24h': ticker['baseVolume'],
                'change_24h': ticker['percentage']
            }
        except Exception as e:
            self.logger.error(f"Market bilgisi alma hatası: {str(e)}")
            return {}
    
    def is_market_open(self, symbol: str) -> bool:
        """Market açık mı kontrol eder"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last'] > 0
        except Exception as e:
            self.logger.error(f"Market durumu kontrol hatası: {str(e)}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Hesap bilgilerini getirir"""
        try:
            balance = self.exchange.fetch_balance()
            account_info = {
                'total_balance': {},
                'free_balance': {},
                'used_balance': {}
            }
            
            for currency, amounts in balance.items():
                if amounts['total'] > 0:
                    account_info['total_balance'][currency] = amounts['total']
                    account_info['free_balance'][currency] = amounts['free']
                    account_info['used_balance'][currency] = amounts['used']
            
            return account_info
        except Exception as e:
            self.logger.error(f"Hesap bilgisi alma hatası: {str(e)}")
            return {}