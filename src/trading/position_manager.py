"""
Position Manager
Pozisyon açma, kapatma ve yönetimi
"""

import asyncio
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
        
        # Active positions cache
        self.active_positions: Dict[str, List[Dict]] = {}
        self.position_update_lock = asyncio.Lock()
        
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
                    entry_price = market_data['close']
                
                # Stop loss hesapla
                stop_loss = action.get('stop_loss')
            if not stop_loss:
                    stop_loss_pct = 0.02 if strategy == 'scalping' else 0.03  # Default %2-3
                if action['signal'] == 'BUY':
                        stop_loss = entry_price * (1 - stop_loss_pct)
                else:
                        stop_loss = entry_price * (1 + stop_loss_pct)
                
                # Position size hesapla
                size_info = await self.risk_manager.calculate_position_size(
                    symbol, entry_price, stop_loss, confidence, strategy
                )
                
            if not size_info.get('allowed', False) or size_info['size'] <= 0:
                    logger.warning(f"⚠️ {symbol} pozisyon açılamadı: {size_info.get('reason', 'Risk kontrolü başarısız')}")
                    return None
                
                position_size = size_info['size']
                leverage = size_info.get('leverage', 1)
                
                # Exchange'de emir ver
                order_result = await self.exchange_manager.place_order(
                    symbol=symbol,
                    side=action['signal'].lower(),  # BUY -> buy, SELL -> sell
                    amount=position_size,
                    order_type='market'
                )
                
            if not order_result:
                    logger.error(f"❌ {symbol} emir verilemedi")
                    return None
                
                # Pozisyon verisini hazırla
                position_data = {
                    'symbol': symbol,
                    'exchange': order_result['exchange'],
                    'side': action['signal'],
                    'size': position_size,
                    'entry_price': order_result.get('price', entry_price),
                    'strategy': strategy,
                    'confidence': confidence,
                    'stop_loss': stop_loss,
                    'take_profit': action.get('take_profit'),
                    'opened_at': datetime.now()
                }
                
                # Veritabanına kaydet
                position_id = await self.db_manager.save_position(position_data)
                position_data['id'] = position_id
                
                # Trade kaydı oluştur
                trade_data = {
                    'position_id': position_id,
                    'symbol': symbol,
                    'exchange': order_result['exchange'],
                    'side': action['signal'],
                    'size': position_size,
                    'price': order_result.get('price', entry_price),
                    'fee': order_result.get('fee', 0),
                    'trade_type': 'ENTRY',
                    'order_id': order_result['id'],
                    'executed_at': datetime.now()
                }
                
                await self.db_manager.save_trade(trade_data)
                
                # Cache'e ekle
            if symbol not in self.active_positions:
                    self.active_positions[symbol] = []
                self.active_positions[symbol].append(position_data)
                
                logger.success(f"✅ {symbol} pozisyon açıldı: {action['signal']} {position_size:.6f} @ {entry_price:.4f}")
                
                return position_data
                
    except Exception as e:
            logger.error(f"❌ {symbol} pozisyon açma hatası: {e}")
            return None
    
async def close_position(self, position: Dict[str, Any], reason: str) -> bool:
        """Pozisyon kapat"""
    try:
            async with self.position_update_lock:
                position_id = position['id']
                symbol = position['symbol']
                side = position['side']
                size = position['size']
                
                logger.info(f"🔒 {symbol} pozisyon kapatılıyor: {reason}")
                
                # Ters emir ver (BUY pozisyonu SELL ile kapat)
                close_side = 'sell' if side == 'BUY' else 'buy'
                
                order_result = await self.exchange_manager.place_order(
                    symbol=symbol,
                    side=close_side,
                    amount=size,
                    order_type='market'
                )
                
            if not order_result:
                    logger.error(f"❌ {symbol} pozisyon kapatılamadı")
                    return False
                
                close_price = order_result.get('price', 0)
                
                # P&L hesapla
                entry_price = position['entry_price']
            if side == 'BUY':
                    pnl = (close_price - entry_price) * size
                    pnl_pct = (close_price - entry_price) / entry_price * 100
            else:
                    pnl = (entry_price - close_price) * size
                    pnl_pct = (entry_price - close_price) / entry_price * 100
                
                # Pozisyonu güncelle
                position_updates = {
                    'current_price': close_price,
                    'pnl': pnl,
                    'pnl_percentage': pnl_pct,
                    'status': 'CLOSED',
                    'closed_at': datetime.now(),
                    'close_reason': reason
                }
                
                await self.db_manager.update_position(position_id, position_updates)
                
                # Kapatma trade'i kaydet
                trade_data = {
                    'position_id': position_id,
                    'symbol': symbol,
                    'exchange': order_result['exchange'],
                    'side': close_side.upper(),
                    'size': size,
                    'price': close_price,
                    'fee': order_result.get('fee', 0),
                    'trade_type': 'EXIT',
                    'order_id': order_result['id'],
                    'executed_at': datetime.now()
                }
                
                await self.db_manager.save_trade(trade_data)
                
                # Cache'den kaldır
            if symbol in self.active_positions:
                    self.active_positions[symbol] = [
                        p for p in self.active_positions[symbol] 
                    if p['id'] != position_id
                    ]
                    
                if not self.active_positions[symbol]:
                        del self.active_positions[symbol]
                
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                logger.success(f"✅ {symbol} pozisyon kapatıldı: {pnl_emoji} PnL: {pnl:.4f} USDT ({pnl_pct:.2f}%)")
                
                return True
                
    except Exception as e:
            logger.error(f"❌ {position.get('symbol', 'UNKNOWN')} pozisyon kapatma hatası: {e}")
            return False
    
async def close_all_positions(self, reason: str = "Manual close") -> None:
        """Tüm pozisyonları kapat"""
    try:
            logger.info(f"🔒 Tüm pozisyonlar kapatılıyor: {reason}")
            
            # Database'den aktif pozisyonları al
            positions = await self.db_manager.get_positions(status='OPEN')
            
        if not positions:
                logger.info("ℹ️ Kapatılacak aktif pozisyon yok")
                return
            
            # Paralel kapatma
            close_tasks = []
        for position in positions:
                task = asyncio.create_task(self.close_position(position, reason))
                close_tasks.append(task)
            
            # Tüm kapatma işlemlerini bekle
            results = await asyncio.gather(*close_tasks, return_exceptions=True)
            
            successful_closes = sum(1 for result in results if result is True)
            total_positions = len(positions)
            
            logger.info(f"✅ {successful_closes}/{total_positions} pozisyon başarıyla kapatıldı")
            
    except Exception as e:
            logger.error(f"❌ Toplu pozisyon kapatma hatası: {e}")
    
async def update_position_prices(self) -> None:
        """Aktif pozisyonların güncel fiyatlarını güncelle"""
    try:
            positions = await self.db_manager.get_positions(status='OPEN')
            
        if not positions:
                return
            
        for position in positions:
            try:
                    symbol = position['symbol']
                    position_id = position['id']
                    
                    # Güncel market data al
                    market_data = await self.exchange_manager.get_market_data(symbol)
                if not market_data:
                        continue
                    
                    current_price = market_data['close']
                    entry_price = position['entry_price']
                    side = position['side']
                    size = position['size']
                    
                    # P&L hesapla
                if side == 'BUY':
                        pnl = (current_price - entry_price) * size
                        pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                        pnl = (entry_price - current_price) * size
                        pnl_pct = (entry_price - current_price) / entry_price * 100
                    
                    # Pozisyonu güncelle
                    await self.db_manager.update_position(position_id, {
                        'current_price': current_price,
                        'pnl': pnl,
                        'pnl_percentage': pnl_pct
                    })
                    
                    # Risk manager'a bildir
                    await self.risk_manager.update_position_pnl(position_id, pnl)
                    
                    # Stop loss / Take profit kontrolü
                if await self.risk_manager.check_stop_loss(position, current_price):
                        await self.close_position(position, "STOP_LOSS")
                elif await self.risk_manager.check_take_profit(position, current_price):
                        await self.close_position(position, "TAKE_PROFIT")
                    
            except Exception as e:
                    logger.error(f"❌ Pozisyon güncelleme hatası: {e}")
                    continue
                    
    except Exception as e:
            logger.error(f"❌ Pozisyon fiyat güncelleme hatası: {e}")
    
async def get_positions(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Pozisyonları getir"""
    try:
            return await self.db_manager.get_positions(symbol=symbol, status='OPEN')
    except Exception as e:
            logger.error(f"❌ Pozisyon getirme hatası: {e}")
            return []
    
async def get_position_summary(self) -> Dict[str, Any]:
        """Pozisyon özetini döndür"""
    try:
            positions = await self.get_positions()
            
        if not positions:
                return {
                    'total_positions': 0,
                    'total_pnl': 0,
                    'best_position': None,
                    'worst_position': None
                }
            
            total_pnl = sum(pos.get('pnl', 0) for pos in positions)
            best_position = max(positions, key=lambda p: p.get('pnl', 0))
            worst_position = min(positions, key=lambda p: p.get('pnl', 0))
            
            return {
                'total_positions': len(positions),
                'total_pnl': total_pnl,
                'best_position': {
                    'symbol': best_position['symbol'],
                    'pnl': best_position.get('pnl', 0),
                    'pnl_percentage': best_position.get('pnl_percentage', 0)
                },
                'worst_position': {
                    'symbol': worst_position['symbol'],
                    'pnl': worst_position.get('pnl', 0),
                    'pnl_percentage': worst_position.get('pnl_percentage', 0)
                }
            }
            
    except Exception as e:
            logger.error(f"❌ Pozisyon özeti hatası: {e}")
            return {'total_positions': 0, 'total_pnl': 0}
    
async def cleanup_expired_positions(self) -> None:
        """Süresi dolmuş pozisyonları temizle"""
    try:
            positions = await self.get_positions()
            
        for position in positions:
            try:
                    opened_at = position.get('opened_at')
                if not opened_at:
                        continue
                    
                if isinstance(opened_at, str):
                        opened_at = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                    
                    # 24 saatten eski pozisyonları kapat
                    position_age = datetime.now() - opened_at
                if position_age > timedelta(hours=24):
                        await self.close_position(position, "EXPIRED_TIME_LIMIT")
                        
            except Exception as e:
                    logger.error(f"❌ Pozisyon cleanup hatası: {e}")
                    continue
                    
    except Exception as e:
            logger.error(f"❌ Pozisyon cleanup genel hatası: {e}")
    
def get_active_positions_count(self) -> int:
        """Aktif pozisyon sayısını döndür"""
        return sum(len(positions) for positions in self.active_positions.values())
    
async def is_position_size_valid(self, symbol: str, size: float) -> bool:
        """Pozisyon boyutunun geçerli olup olmadığını kontrol et"""
    try:
            # Minimum size kontrolü
        if size < 0.001:  # Minimum 0.001
                return False
            
            # Exchange limits kontrolü
            # Bu gerçek implementasyonda exchange'den market info alınacak
            
            return True
            
    except Exception as e:
            logger.error(f"❌ Position size validasyon hatası: {e}")
            return False
    
async def update_trailing_stops(self) -> None:
        """Trailing stop'ları güncelle"""
    try:
            positions = await self.db_manager.get_positions(status='OPEN')
            
        for position in positions:
            try:
                if not position.get('trailing_stop_enabled'):
                        continue
                    
                    symbol = position['symbol']
                    position_id = position['id']
                    side = position['side']
                    entry_price = position['entry_price']
                    current_stop = position.get('stop_loss')
                    
                    # Get current price
                    market_data = await self.exchange_manager.get_market_data(symbol)
                if not market_data:
                        continue
                    
                    current_price = market_data['close']
                    
                    # Calculate trailing distance (default 2%)
                    trailing_distance = position.get('trailing_distance', 0.02)
                    
                    # Calculate new stop level
                if side == 'BUY':
                        # For long positions, trail stop up
                        new_stop = current_price * (1 - trailing_distance)
                        
                        # Only update if new stop is higher than current
                    if not current_stop or new_stop > current_stop:
                            await self.db_manager.update_position(position_id, {
                                'stop_loss': new_stop,
                                'last_trailing_update': datetime.now()
                            })
                            
                            logger.info(f"📈 {symbol} trailing stop güncellendi: {current_stop} → {new_stop:.4f}")
                    
                else:  # SELL position
                        # For short positions, trail stop down
                        new_stop = current_price * (1 + trailing_distance)
                        
                        # Only update if new stop is lower than current
                    if not current_stop or new_stop < current_stop:
                            await self.db_manager.update_position(position_id, {
                                'stop_loss': new_stop,
                                'last_trailing_update': datetime.now()
                            })
                            
                            logger.info(f"📉 {symbol} trailing stop güncellendi: {current_stop} → {new_stop:.4f}")
                
            except Exception as e:
                    logger.error(f"❌ {position.get('symbol', 'UNKNOWN')} trailing stop hatası: {e}")
                    continue
                    
    except Exception as e:
            logger.error(f"❌ Trailing stop güncelleme genel hatası: {e}")
    
async def enable_trailing_stop(self, position_id: int, trailing_distance: float = 0.02) -> bool:
        """Pozisyon için trailing stop'u aktifleştir"""
    try:
            await self.db_manager.update_position(position_id, {
                'trailing_stop_enabled': True,
                'trailing_distance': trailing_distance,
                'trailing_enabled_at': datetime.now()
            })
            
            logger.info(f"✅ Pozisyon {position_id} için trailing stop aktifleştirildi (%{trailing_distance*100:.1f})")
            return True
            
    except Exception as e:
            logger.error(f"❌ Trailing stop aktifleştirme hatası: {e}")
            return False
    
async def disable_trailing_stop(self, position_id: int) -> bool:
        """Pozisyon için trailing stop'u deaktifleştir"""
    try:
            await self.db_manager.update_position(position_id, {
                'trailing_stop_enabled': False,
                'trailing_disabled_at': datetime.now()
            })
            
            logger.info(f"🔴 Pozisyon {position_id} için trailing stop deaktifleştirildi")
            return True
            
    except Exception as e:
            logger.error(f"❌ Trailing stop deaktifleştirme hatası: {e}")
            return False
    
async def get_position_performance(self, position_id: int) -> Dict[str, Any]:
        """Pozisyon performans metrikleri"""
    try:
            positions = await self.db_manager.get_positions()
            position = next((p for p in positions if p['id'] == position_id), None)
            
        if not position:
                return {'error': 'Position not found'}
            
            # Get current price
            market_data = await self.exchange_manager.get_market_data(position['symbol'])
            current_price = market_data['close'] if market_data else position.get('current_price', position['entry_price'])
            
            # Calculate metrics
            entry_price = position['entry_price']
            side = position['side']
            size = position['size']
            
        if side == 'BUY':
                unrealized_pnl = (current_price - entry_price) * size
                pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
                unrealized_pnl = (entry_price - current_price) * size
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            # Time metrics
            opened_at = position['opened_at']
        if isinstance(opened_at, str):
                opened_at = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
            
            duration = datetime.now() - opened_at
            duration_hours = duration.total_seconds() / 3600
            
            # Risk metrics
            position_value = entry_price * size
            risk_amount = position_value * 0.02  # Assumed 2% risk
            
            risk_reward_ratio = abs(unrealized_pnl / risk_amount) if risk_amount > 0 else 0
            
            return {
                'position_id': position_id,
                'symbol': position['symbol'],
                'side': side,
                'entry_price': entry_price,
                'current_price': current_price,
                'size': size,
                'unrealized_pnl': unrealized_pnl,
                'pnl_percentage': pnl_pct,
                'position_value': position_value,
                'duration_hours': duration_hours,
                'risk_reward_ratio': risk_reward_ratio,
                'stop_loss': position.get('stop_loss'),
                'take_profit': position.get('take_profit'),
                'trailing_stop_enabled': position.get('trailing_stop_enabled', False),
                'strategy': position.get('strategy'),
                'confidence': position.get('confidence')
            }
            
    except Exception as e:
            logger.error(f"❌ Position performance hatası: {e}")
            return {'error': str(e)}