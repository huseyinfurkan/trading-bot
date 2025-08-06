"""
Position Manager
Pozisyon açma, kapatma ve yönetimi
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class PositionManager:
    """Pozisyon yöneticisi"""
    
    def __init__(self, exchange_manager, risk_manager, db_manager):
        """
        Args:
            exchange_manager: Exchange yöneticisi
            risk_manager: Risk yöneticisi
            db_manager: Veritabanı yöneticisi
        """
        self.exchange_manager = exchange_manager
        self.risk_manager = risk_manager
        self.db_manager = db_manager
        
        # Position tracking
        self.open_positions = {}
        self.position_update_lock = asyncio.Lock()
        
        # Trailing stop tracking
        self.trailing_stops = {}
        
        logger.info("📊 Position Manager initialized")
    
    async def open_position(self, symbol: str, action: Dict[str, Any], 
                          confidence: float, strategy: str) -> Optional[Dict[str, Any]]:
        """Yeni pozisyon aç"""
        try:
            async with self.position_update_lock:
                logger.info(f"🔓 {symbol} pozisyon açılıyor: {action['signal']} - Strateji: {strategy}")
                
                # Entry price
                entry_price = action.get('entry_price')
                if not entry_price:
                    market_data = await self.exchange_manager.get_market_data(symbol)
                    if not market_data:
                        logger.error(f"❌ {symbol} market data alınamadı")
                        return None
                    entry_price = market_data.get('close', 0)
                
                # Position size calculation
                size_result = await self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    entry_price=entry_price,
                    stop_loss=action.get('stop_loss', entry_price * 0.97),
                    confidence=confidence,
                    strategy=strategy
                )
                
                if not size_result.get('allowed', False):
                    logger.warning(f"⚠️ {symbol} pozisyon reddedildi: {size_result.get('reason')}")
                    return None
                
                position_size = size_result['size']
                
                # Create order
                order_result = await self._place_order(
                    symbol=symbol,
                    side=action['signal'],
                    size=position_size,
                    price=entry_price,
                    order_type='MARKET'
                )
                
                if not order_result:
                    logger.error(f"❌ {symbol} order verilemedi")
                    return None
                
                # Create position record
                position_id = await self._create_position_record(
                    symbol=symbol,
                    side=action['signal'],
                    size=position_size,
                    entry_price=entry_price,
                    stop_loss=action.get('stop_loss'),
                    take_profit=action.get('take_profit'),
                    strategy=strategy,
                    confidence=confidence,
                    order_id=order_result.get('order_id')
                )
                
                if position_id:
                    # Track position
                    self.open_positions[position_id] = {
                        'id': position_id,
                        'symbol': symbol,
                        'side': action['signal'],
                        'size': position_size,
                        'entry_price': entry_price,
                        'current_price': entry_price,
                        'stop_loss': action.get('stop_loss'),
                        'take_profit': action.get('take_profit'),
                        'strategy': strategy,
                        'confidence': confidence,
                        'pnl': 0,
                        'opened_at': datetime.now(),
                        'status': 'OPEN'
                    }
                    
                    logger.success(f"✅ {symbol} pozisyon açıldı: {position_id}")
                    
                    return {
                        'id': position_id,
                        'symbol': symbol,
                        'side': action['signal'],
                        'size': position_size,
                        'entry_price': entry_price,
                        'status': 'OPEN'
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"❌ {symbol} pozisyon açma hatası: {e}")
            return None
    
    async def close_position(self, position_id: int, reason: str = "Manual close") -> bool:
        """Pozisyon kapat"""
        try:
            if position_id not in self.open_positions:
                logger.warning(f"⚠️ Pozisyon bulunamadı: {position_id}")
                return False
            
            position = self.open_positions[position_id]
            symbol = position['symbol']
            
            logger.info(f"🔒 {symbol} pozisyon kapatılıyor: {position_id} - {reason}")
            
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.error(f"❌ {symbol} current price alınamadı")
                return False
            
            # Calculate final P&L
            final_pnl = self._calculate_pnl(position, current_price)
            
            # Place close order
            close_result = await self._place_order(
                symbol=symbol,
                side='SELL' if position['side'] == 'BUY' else 'BUY',
                size=position['size'],
                price=current_price,
                order_type='MARKET'
            )
            
            if close_result:
                # Update position record
                await self.db_manager.update_position(position_id, {
                    'status': 'CLOSED',
                    'current_price': current_price,
                    'pnl': final_pnl,
                    'closed_at': datetime.now().isoformat(),
                    'close_reason': reason
                })
                
                # Remove from tracking
                del self.open_positions[position_id]
                
                # Remove trailing stop if exists
                if position_id in self.trailing_stops:
                    del self.trailing_stops[position_id]
                
                logger.success(f"✅ {symbol} pozisyon kapatıldı: {final_pnl:.2f} USDT P&L")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Pozisyon kapatma hatası: {e}")
            return False
    
    async def update_trailing_stops(self) -> None:
        """Trailing stop'ları güncelle"""
        try:
            for position_id, position in self.open_positions.items():
                if position_id not in self.trailing_stops:
                    continue
                
                symbol = position['symbol']
                current_price = await self._get_current_price(symbol)
                
                if not current_price:
                    continue
                
                trailing_config = self.trailing_stops[position_id]
                side = position['side']
                
                # Calculate new trailing stop
                if side == 'BUY':
                    # For long positions
                    new_stop = current_price * (1 - trailing_config['distance'])
                    
                    # Update if price moved favorably
                    if new_stop > position['stop_loss']:
                        position['stop_loss'] = new_stop
                        
                        await self.db_manager.update_position(position_id, {
                            'stop_loss': new_stop
                        })
                        
                        logger.debug(f"📈 {symbol} trailing stop updated: {new_stop:.4f}")
                
                else:  # SELL
                    # For short positions
                    new_stop = current_price * (1 + trailing_config['distance'])
                    
                    # Update if price moved favorably
                    if new_stop < position['stop_loss']:
                        position['stop_loss'] = new_stop
                        
                        await self.db_manager.update_position(position_id, {
                            'stop_loss': new_stop
                        })
                        
                        logger.debug(f"📉 {symbol} trailing stop updated: {new_stop:.4f}")
                
        except Exception as e:
            logger.error(f"❌ Trailing stop update error: {e}")
    
    async def enable_trailing_stop(self, position_id: int, trailing_distance: float = 0.02) -> bool:
        """Pozisyon için trailing stop'u aktifleştir"""
        try:
            if position_id not in self.open_positions:
                return False
            
            self.trailing_stops[position_id] = {
                'distance': trailing_distance,
                'enabled_at': datetime.now()
            }
            
            position = self.open_positions[position_id]
            logger.info(f"🎯 {position['symbol']} trailing stop aktif: %{trailing_distance*100:.1f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Trailing stop enable error: {e}")
            return False
    
    async def disable_trailing_stop(self, position_id: int) -> bool:
        """Pozisyon için trailing stop'u deaktifleştir"""
        try:
            if position_id in self.trailing_stops:
                del self.trailing_stops[position_id]
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Trailing stop disable error: {e}")
            return False
    
    async def check_stop_loss_take_profit(self) -> None:
        """Tüm pozisyonlar için stop loss ve take profit kontrolü"""
        try:
            for position_id, position in list(self.open_positions.items()):
                symbol = position['symbol']
                current_price = await self._get_current_price(symbol)
                
                if not current_price:
                    continue
                
                # Update current price and P&L
                position['current_price'] = current_price
                position['pnl'] = self._calculate_pnl(position, current_price)
                
                side = position['side']
                stop_loss = position.get('stop_loss')
                take_profit = position.get('take_profit')
                
                should_close = False
                close_reason = ""
                
                # Check stop loss
                if stop_loss:
                    if side == 'BUY' and current_price <= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                    elif side == 'SELL' and current_price >= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                
                # Check take profit
                if not should_close and take_profit:
                    if side == 'BUY' and current_price >= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                    elif side == 'SELL' and current_price <= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                
                if should_close:
                    await self.close_position(position_id, close_reason)
                
        except Exception as e:
            logger.error(f"❌ Stop loss/take profit check error: {e}")
    
    async def get_position_performance(self, position_id: int) -> Dict[str, Any]:
        """Pozisyon performans metrikleri"""
        try:
            if position_id not in self.open_positions:
                # Check closed positions in database
                positions = await self.db_manager.get_positions()
                for pos in positions:
                    if pos['id'] == position_id:
                        return self._calculate_position_metrics(pos)
                return {}
            
            position = self.open_positions[position_id]
            current_price = await self._get_current_price(position['symbol'])
            
            if current_price:
                position['current_price'] = current_price
                position['pnl'] = self._calculate_pnl(position, current_price)
            
            return self._calculate_position_metrics(position)
            
        except Exception as e:
            logger.error(f"❌ Position performance error: {e}")
            return {}
    
    def _calculate_position_metrics(self, position: Dict) -> Dict[str, Any]:
        """Pozisyon metriklerini hesapla"""
        try:
            entry_price = position['entry_price']
            current_price = position.get('current_price', entry_price)
            size = position['size']
            pnl = position.get('pnl', 0)
            
            # Duration
            opened_at = position.get('opened_at', datetime.now())
            if isinstance(opened_at, str):
                opened_at = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
            
            duration = datetime.now() - opened_at
            
            # P&L percentage
            position_value = entry_price * size
            pnl_percentage = (pnl / position_value * 100) if position_value > 0 else 0
            
            # Risk-reward ratio
            stop_loss = position.get('stop_loss')
            take_profit = position.get('take_profit')
            
            risk_reward_ratio = None
            if stop_loss and take_profit:
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit - entry_price)
                risk_reward_ratio = reward / risk if risk > 0 else 0
            
            return {
                'position_id': position.get('id'),
                'symbol': position['symbol'],
                'side': position['side'],
                'entry_price': entry_price,
                'current_price': current_price,
                'size': size,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'duration_hours': duration.total_seconds() / 3600,
                'risk_reward_ratio': risk_reward_ratio,
                'status': position.get('status', 'OPEN')
            }
            
        except Exception as e:
            logger.error(f"❌ Position metrics calculation error: {e}")
            return {}
    
    def _calculate_pnl(self, position: Dict, current_price: float) -> float:
        """P&L hesapla"""
        try:
            entry_price = position['entry_price']
            size = position['size']
            side = position['side']
            
            if side == 'BUY':
                return (current_price - entry_price) * size
            else:  # SELL
                return (entry_price - current_price) * size
                
        except Exception as e:
            logger.error(f"❌ P&L calculation error: {e}")
            return 0.0
    
    async def _place_order(self, symbol: str, side: str, size: float, 
                          price: float, order_type: str = 'MARKET') -> Optional[Dict]:
        """Gerçek order placement via exchange manager"""
        try:
            # Use exchange manager for real order placement
            order_result = await self.exchange_manager.place_order(
                symbol=symbol,
                side=side,
                amount=size,
                price=price if order_type == 'LIMIT' else None,
                order_type=order_type.lower()
            )
            
            if order_result:
                logger.success(f"✅ Real order placed: {symbol} {side} {size:.6f} @ {price:.4f}")
                return order_result
            else:
                logger.error(f"❌ Order placement failed: {symbol}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Güncel fiyat al"""
        try:
            # Get real-time price from exchange manager
            market_data = await self.exchange_manager.get_real_time_data(symbol)
            return market_data.get('price') if market_data else None
        except Exception as e:
            logger.error(f"❌ Current price error for {symbol}: {e}")
            return None
    
    async def _create_position_record(self, symbol: str, side: str, size: float,
                                    entry_price: float, stop_loss: Optional[float],
                                    take_profit: Optional[float], strategy: str,
                                    confidence: float, order_id: str) -> Optional[int]:
        """Pozisyon kaydı oluştur"""
        try:
            position_data = {
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'strategy': strategy,
                'confidence': confidence,
                'exchange': 'binance',  # Default
                'order_id': order_id
            }
            
            position_id = await self.db_manager.save_position(position_data)
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Position record creation error: {e}")
            return None
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Açık pozisyonları getir"""
        return list(self.open_positions.values())
    
    async def get_position_count(self) -> int:
        """Açık pozisyon sayısı"""
        return len(self.open_positions)
    
    async def close(self):
        """Position manager'ı kapat"""
        try:
            # Close all open positions
            for position_id in list(self.open_positions.keys()):
                await self.close_position(position_id, "System shutdown")
            
            logger.info("📊 Position Manager closed")
            
        except Exception as e:
            logger.error(f"❌ Position Manager close error: {e}")