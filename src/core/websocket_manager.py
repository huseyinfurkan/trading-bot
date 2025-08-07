#!/usr/bin/env python3
"""
WebSocket Manager
Real-time data streaming from exchanges using CCXT WebSocket
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
import websockets
import ccxt.async_support as ccxt


class WebSocketManager:
    """Comprehensive WebSocket manager for real-time trading data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # WebSocket connections
        self.connections = {}
        self.connection_status = {}
        
        # Data storage
        self.live_data = {}
        self.data_callbacks = {}
        
        # Dynamic configuration based on market conditions
        self.exchanges = config.get('exchanges', {})
        self.symbols = await self._get_dynamic_symbols(config)
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = await self._get_dynamic_max_reconnect_attempts(config)
        self.reconnect_delay = await self._get_dynamic_reconnect_delay(config)
        
        # Performance tracking
        self.message_count = 0
        self.error_count = 0
        self.start_time = datetime.now()
        
        # Thread safety
        self.lock = asyncio.Lock()
        
        logger.info("🔌 WebSocket Manager initialized")
    
    async def initialize(self):
        """Initialize WebSocket connections for all exchanges"""
        try:
            logger.info("🚀 Initializing WebSocket connections...")
            
            for exchange_name, exchange_config in self.exchanges.items():
                if exchange_config.get('enabled', False):
                    await self._initialize_exchange_websocket(exchange_name, exchange_config)
            
            logger.success("✅ WebSocket connections initialized")
            
        except Exception as e:
            logger.error(f"❌ WebSocket initialization error: {e}")
            raise
    
    async def _initialize_exchange_websocket(self, exchange_name: str, exchange_config: Dict[str, Any]):
        """Initialize WebSocket connection for specific exchange"""
        try:
            logger.info(f"🔌 Initializing WebSocket for {exchange_name}")
            
            # Initialize exchange
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                'apiKey': exchange_config.get('api_key', ''),
                'secret': exchange_config.get('api_secret', ''),
                'sandbox': False,  # Use live trading
                'enableRateLimit': True,
                'options': exchange_config.get('params', {})
            })
            
            # Initialize connection status
            self.connection_status[exchange_name] = {
                'connected': False,
                'last_message': None,
                'error_count': 0,
                'reconnect_attempts': 0,
                'exchange': exchange
            }
            
            # Start WebSocket connection
            await self._connect_exchange_websocket(exchange_name, exchange)
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} WebSocket initialization error: {e}")
            self.connection_status[exchange_name]['connected'] = False
    
    async def _connect_exchange_websocket(self, exchange_name: str, exchange):
        """Connect to WebSocket for specific exchange"""
        try:
            # Check if exchange supports WebSocket
            if not hasattr(exchange, 'watch_ticker') or not hasattr(exchange, 'watch_ohlcv'):
                logger.warning(f"⚠️ {exchange_name} does not support WebSocket")
                return
            
            # Start WebSocket tasks
            tasks = []
            
            # Ticker data
            for symbol in self.symbols:
                if exchange.market(symbol)['active']:
                    tasks.append(asyncio.create_task(
                        self._watch_ticker(exchange_name, exchange, symbol)
                    ))
                    tasks.append(asyncio.create_task(
                        self._watch_ohlcv(exchange_name, exchange, symbol)
                    ))
            
            # Store tasks
            self.connections[exchange_name] = tasks
            
            # Update status
            self.connection_status[exchange_name]['connected'] = True
            self.connection_status[exchange_name]['last_message'] = datetime.now()
            self.reconnect_attempts[exchange_name] = 0
            
            logger.success(f"✅ WebSocket connected for {exchange_name}")
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} WebSocket connection error: {e}")
            self.connection_status[exchange_name]['connected'] = False
            self.connection_status[exchange_name]['error_count'] += 1
    
    async def _watch_ticker(self, exchange_name: str, exchange, symbol: str):
        """Watch real-time ticker data"""
        try:
            logger.info(f"📊 Watching ticker for {exchange_name}:{symbol}")
            
            while True:
                try:
                    # Get ticker data
                    ticker = await exchange.watch_ticker(symbol)
                    
                    # Process ticker data
                    processed_data = {
                        'exchange': exchange_name,
                        'symbol': symbol,
                        'type': 'ticker',
                        'timestamp': datetime.now(),
                        'data': {
                            'price': ticker['last'],
                            'bid': ticker['bid'],
                            'ask': ticker['ask'],
                            'volume': ticker['baseVolume'],
                            'change_24h': ticker['change'],
                            'change_pct_24h': ticker['percentage'],
                            'high_24h': ticker['high'],
                            'low_24h': ticker['low']
                        }
                    }
                    
                    # Store data
                    await self._store_live_data(processed_data)
                    
                    # Update status
                    self.connection_status[exchange_name]['last_message'] = datetime.now()
                    self.message_count += 1
                    
                    # Call callbacks
                    await self._call_data_callbacks(processed_data)
                    
                except Exception as e:
                    logger.error(f"❌ {exchange_name}:{symbol} ticker error: {e}")
                    self.error_count += 1
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"❌ {exchange_name}:{symbol} ticker watch fatal error: {e}")
    
    async def _watch_ohlcv(self, exchange_name: str, exchange, symbol: str):
        """Watch real-time OHLCV data"""
        try:
            logger.info(f"📈 Watching OHLCV for {exchange_name}:{symbol}")
            
            while True:
                try:
                    # Get OHLCV data (1m timeframe)
                    ohlcv = await exchange.watch_ohlcv(symbol, '1m')
                    
                    if ohlcv and len(ohlcv) > 0:
                        # Get latest candle
                        latest_candle = ohlcv[-1]
                        
                        # Process OHLCV data
                        processed_data = {
                            'exchange': exchange_name,
                            'symbol': symbol,
                            'type': 'ohlcv',
                            'timestamp': datetime.now(),
                            'data': {
                                'timestamp': latest_candle[0],
                                'open': latest_candle[1],
                                'high': latest_candle[2],
                                'low': latest_candle[3],
                                'close': latest_candle[4],
                                'volume': latest_candle[5]
                            }
                        }
                        
                        # Store data
                        await self._store_live_data(processed_data)
                        
                        # Update status
                        self.connection_status[exchange_name]['last_message'] = datetime.now()
                        self.message_count += 1
                        
                        # Call callbacks
                        await self._call_data_callbacks(processed_data)
                    
                except Exception as e:
                    logger.error(f"❌ {exchange_name}:{symbol} OHLCV error: {e}")
                    self.error_count += 1
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"❌ {exchange_name}:{symbol} OHLCV watch fatal error: {e}")
    
    async def _store_live_data(self, data: Dict[str, Any]):
        """Store live data with thread safety"""
        try:
            async with self.lock:
                exchange = data['exchange']
                symbol = data['symbol']
                data_type = data['type']
                
                # Initialize storage if needed
                if exchange not in self.live_data:
                    self.live_data[exchange] = {}
                
                if symbol not in self.live_data[exchange]:
                    self.live_data[exchange][symbol] = {}
                
                # Store data
                self.live_data[exchange][symbol][data_type] = data
                
                # Keep only recent data (last 1000 messages)
                if len(self.live_data[exchange][symbol]) > 1000:
                    # Remove oldest data
                    keys = list(self.live_data[exchange][symbol].keys())
                    for key in keys[:-1000]:
                        del self.live_data[exchange][symbol][key]
                        
        except Exception as e:
            logger.error(f"❌ Data storage error: {e}")
    
    async def _call_data_callbacks(self, data: Dict[str, Any]):
        """Call registered data callbacks"""
        try:
            exchange = data['exchange']
            symbol = data['symbol']
            
            callback_key = f"{exchange}:{symbol}"
            
            if callback_key in self.data_callbacks:
                for callback in self.data_callbacks[callback_key]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"❌ Callback error: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Callback execution error: {e}")
    
    async def get_live_data(self, exchange: str, symbol: str, data_type: str = 'ticker') -> Optional[Dict[str, Any]]:
        """Get live data for specific exchange, symbol and type"""
        try:
            async with self.lock:
                if (exchange in self.live_data and 
                    symbol in self.live_data[exchange] and 
                    data_type in self.live_data[exchange][symbol]):
                    return self.live_data[exchange][symbol][data_type]
                return None
                
        except Exception as e:
            logger.error(f"❌ Get live data error: {e}")
            return None
    
    async def register_callback(self, exchange: str, symbol: str, callback: Callable):
        """Register callback for data updates"""
        try:
            callback_key = f"{exchange}:{symbol}"
            
            if callback_key not in self.data_callbacks:
                self.data_callbacks[callback_key] = []
            
            self.data_callbacks[callback_key].append(callback)
            logger.info(f"✅ Callback registered for {callback_key}")
            
        except Exception as e:
            logger.error(f"❌ Callback registration error: {e}")
    
    async def unregister_callback(self, exchange: str, symbol: str, callback: Callable):
        """Unregister callback"""
        try:
            callback_key = f"{exchange}:{symbol}"
            
            if callback_key in self.data_callbacks:
                if callback in self.data_callbacks[callback_key]:
                    self.data_callbacks[callback_key].remove(callback)
                    logger.info(f"✅ Callback unregistered for {callback_key}")
                    
        except Exception as e:
            logger.error(f"❌ Callback unregistration error: {e}")
    
    async def monitor_connections(self):
        """Monitor WebSocket connections and handle reconnections"""
        try:
            logger.info("🔍 WebSocket connection monitor started")
            
            while True:
                try:
                    for exchange_name, status in self.connection_status.items():
                        # Check if connection is stale (no messages in 5 minutes)
                        if (status['last_message'] and 
                            (datetime.now() - status['last_message']).seconds > 300):
                            logger.warning(f"⚠️ {exchange_name} connection stale, reconnecting...")
                            await self._reconnect_exchange(exchange_name)
                        
                        # Check if connection is down
                        elif not status['connected']:
                            if status['reconnect_attempts'] < self.max_reconnect_attempts:
                                logger.info(f"🔄 Reconnecting {exchange_name}...")
                                await self._reconnect_exchange(exchange_name)
                            else:
                                logger.error(f"❌ Max reconnection attempts reached for {exchange_name}")
                    
                    # Wait before next check
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Connection monitor error: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ Connection monitor fatal error: {e}")
    
    async def _reconnect_exchange(self, exchange_name: str):
        """Reconnect to specific exchange"""
        try:
            status = self.connection_status[exchange_name]
            exchange = status['exchange']
            
            # Close existing connections
            if exchange_name in self.connections:
                for task in self.connections[exchange_name]:
                    if not task.done():
                        task.cancel()
            
            # Reset status
            status['connected'] = False
            status['reconnect_attempts'] += 1
            
            # Wait before reconnection
            await asyncio.sleep(self.reconnect_delay)
            
            # Reconnect
            await self._connect_exchange_websocket(exchange_name, exchange)
            
        except Exception as e:
            logger.error(f"❌ {exchange_name} reconnection error: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get WebSocket connection status"""
        try:
            status_summary = {}
            
            for exchange_name, status in self.connection_status.items():
                status_summary[exchange_name] = {
                    'connected': status['connected'],
                    'last_message': status['last_message'],
                    'error_count': status['error_count'],
                    'reconnect_attempts': status['reconnect_attempts']
                }
            
            return {
                'connections': status_summary,
                'total_messages': self.message_count,
                'total_errors': self.error_count,
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"❌ Status summary error: {e}")
            return {'error': str(e)}
    
    async def _get_dynamic_symbols(self, config: Dict[str, Any]) -> List[str]:
        """Get dynamic symbols based on market conditions"""
        try:
            base_symbols = config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
            
            # This would be adjusted based on real market data
            # For now, return base symbols
            return base_symbols
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic symbols: {e}")
            return config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
    
    async def _get_dynamic_max_reconnect_attempts(self, config: Dict[str, Any]) -> int:
        """Get dynamic max reconnect attempts based on error frequency"""
        try:
            base_attempts = config.get('max_reconnect_attempts', 5)
            
            # Check recent error frequency
            if self.error_count > 10:
                # High error frequency - increase attempts
                return min(10, base_attempts * 2)
            elif self.error_count < 2:
                # Low error frequency - decrease attempts
                return max(3, base_attempts // 2)
            else:
                return base_attempts
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic max reconnect attempts: {e}")
            return config.get('max_reconnect_attempts', 5)
    
    async def _get_dynamic_reconnect_delay(self, config: Dict[str, Any]) -> int:
        """Get dynamic reconnect delay based on connection stability"""
        try:
            base_delay = config.get('reconnect_delay', 10)
            
            # Check connection stability
            stable_connections = sum(1 for status in self.connection_status.values() 
                                   if status.get('connected', False))
            total_connections = len(self.connection_status)
            
            if stable_connections < total_connections * 0.5:
                # Unstable connections - increase delay
                return min(30, base_delay * 2)
            elif stable_connections == total_connections:
                # All connections stable - decrease delay
                return max(5, base_delay // 2)
            else:
                return base_delay
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic reconnect delay: {e}")
            return config.get('reconnect_delay', 10)
    
    async def close(self):
        """Close all WebSocket connections"""
        try:
            logger.info("🛑 Closing WebSocket connections...")
            
            # Close all tasks
            for exchange_name, tasks in self.connections.items():
                for task in tasks:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
            
            # Close exchange connections
            for exchange_name, status in self.connection_status.items():
                if 'exchange' in status:
                    try:
                        await status['exchange'].close()
                    except Exception as e:
                        logger.error(f"❌ {exchange_name} close error: {e}")
            
            logger.success("✅ WebSocket connections closed")
            
        except Exception as e:
            logger.error(f"❌ WebSocket close error: {e}")