"""
Position Manager
Pozisyon açma, kapatma ve yönetimi
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import numpy as np


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
        """Enhanced position opening with trading costs and dynamic management"""
        try:
            async with self.position_update_lock:
                logger.info(f"🔓 {symbol} pozisyon açılıyor: {action['action']} - Strateji: {strategy}")
                
                # Entry price validation
                entry_price = action.get('entry_price')
                if not entry_price or entry_price <= 0:
                    market_data = await self.exchange_manager.get_market_data(symbol)
                    if not market_data:
                        logger.error(f"❌ {symbol} market data alınamadı")
                        return None
                    entry_price = market_data.get('current_price', market_data.get('close', 0))
                    if not entry_price or entry_price <= 0:
                        logger.error(f"❌ {symbol} geçerli entry price bulunamadı")
                        return None
                
                # Calculate trading costs
                trading_costs = await self._calculate_trading_costs(symbol, entry_price, action)
                
                # Adjust entry price for slippage
                slippage = trading_costs['slippage']
                if action['action'] == 'BUY':
                    adjusted_entry_price = entry_price * (1 + slippage)
                else:  # SELL
                    adjusted_entry_price = entry_price * (1 - slippage)
                
                # Stop loss validation
                stop_loss = action.get('stop_loss')
                if not stop_loss or stop_loss <= 0:
                    # Calculate default stop loss based on strategy
                    if action['action'] == 'BUY':
                        stop_loss = adjusted_entry_price * 0.97  # 3% stop loss for long
                    else:
                        stop_loss = adjusted_entry_price * 1.03  # 3% stop loss for short
                
                # Validate stop loss direction
                if action['action'] == 'BUY' and stop_loss >= adjusted_entry_price:
                    logger.error(f"❌ {symbol} long pozisyon için stop loss entry price'dan yüksek olamaz")
                    return None
                elif action['action'] == 'SELL' and stop_loss <= adjusted_entry_price:
                    logger.error(f"❌ {symbol} short pozisyon için stop loss entry price'dan düşük olamaz")
                    return None
                
                # Get account balance for position sizing
                try:
                    balance = await self.exchange_manager.get_balance()
                    account_balance = balance.get('USDT', 0) if balance else 10000  # Default fallback
                except Exception as e:
                    logger.warning(f"⚠️ Balance check failed: {e}, using default")
                    account_balance = 10000
                
                # Position size calculation with proper validation
                size_result = await self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    entry_price=adjusted_entry_price,
                    stop_loss=stop_loss,
                    confidence=confidence,
                    strategy=strategy,
                    current_price=adjusted_entry_price,
                    account_balance=account_balance
                )
                
                if not size_result.get('allowed', False):
                    logger.warning(f"⚠️ {symbol} pozisyon reddedildi: {size_result.get('reason')}")
                    return None
                
                position_size = size_result['size']
                
                # Adjust position size for trading costs
                total_costs = trading_costs['total_cost_pct']
                adjusted_position_size = position_size * (1 - total_costs)
                
                # Additional position size validation
                if adjusted_position_size <= 0:
                    logger.error(f"❌ {symbol} pozisyon boyutu sıfır veya negatif")
                    return None
                
                # Calculate take profit
                take_profit = action.get('take_profit')
                if not take_profit or take_profit <= 0:
                    # Calculate default take profit based on risk/reward ratio
                    risk_amount = abs(adjusted_entry_price - stop_loss)
                    if action['action'] == 'BUY':
                        take_profit = adjusted_entry_price + (risk_amount * 2)  # 2:1 reward/risk
                    else:
                        take_profit = adjusted_entry_price - (risk_amount * 2)
                
                # Validate take profit direction
                if action['action'] == 'BUY' and take_profit <= adjusted_entry_price:
                    logger.error(f"❌ {symbol} long pozisyon için take profit entry price'dan düşük olamaz")
                    return None
                elif action['action'] == 'SELL' and take_profit >= adjusted_entry_price:
                    logger.error(f"❌ {symbol} short pozisyon için take profit entry price'dan yüksek olamaz")
                    return None
                
                # Place order with enhanced logging
                order_result = await self._place_order(
                    symbol=symbol,
                    side=action['action'],
                    size=adjusted_position_size,
                    price=adjusted_entry_price,
                    order_type='MARKET'
                )
                
                if not order_result:
                    logger.error(f"❌ {symbol} order placement failed")
                    return None
                
                # Create position record with trading costs
                position_id = await self._create_position_record(
                    symbol=symbol,
                    side=action['action'],
                    size=adjusted_position_size,
                    entry_price=adjusted_entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    strategy=strategy,
                    confidence=confidence,
                    order_id=order_result.get('id', 'unknown'),
                    leverage=size_result.get('leverage_used', 1.0),
                    margin_required=adjusted_position_size / size_result.get('leverage_used', 1.0),
                    trading_costs=trading_costs
                )
                
                if not position_id:
                    logger.error(f"❌ {symbol} position record creation failed")
                    return None
                
                # Initialize trailing stop if enabled
                trailing_enabled = action.get('trailing_stop_enabled', False)
                if trailing_enabled:
                    trailing_distance = action.get('trailing_stop_distance', 0.02)
                    await self.enable_trailing_stop(position_id, trailing_distance)
                
                # Store position in memory
                self.open_positions[position_id] = {
                    'symbol': symbol,
                    'side': action['action'],
                    'size': adjusted_position_size,
                    'entry_price': adjusted_entry_price,
                    'original_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'strategy': strategy,
                    'confidence': confidence,
                    'order_id': order_result.get('id'),
                    'opened_at': datetime.now(),
                    'trading_costs': trading_costs,
                    'leverage': size_result.get('leverage_used', 1.0),
                    'trailing_stop_enabled': trailing_enabled,
                    'trailing_stop_distance': action.get('trailing_stop_distance', 0.02)
                }
                
                logger.success(f"✅ {symbol} pozisyon açıldı: ID {position_id}, Boyut: {adjusted_position_size:.6f}, Fiyat: ${adjusted_entry_price:.4f}")
                
                return {
                    'position_id': position_id,
                    'symbol': symbol,
                    'side': action['action'],
                    'size': adjusted_position_size,
                    'entry_price': adjusted_entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'order_id': order_result.get('id'),
                    'trading_costs': trading_costs,
                    'leverage': size_result.get('leverage_used', 1.0)
                }
                
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
        """Enhanced trailing stop management with dynamic adjustments"""
        try:
            async with self.position_update_lock:
                for position_id, position in self.open_positions.items():
                    if not position.get('trailing_stop_enabled', False):
                        continue
                    
                    try:
                        # Get current price
                        current_price = await self._get_current_price(position['symbol'])
                        if not current_price:
                            continue
                        
                        # Calculate dynamic trailing stop
                        new_stop_loss = await self._calculate_dynamic_trailing_stop(
                            position, current_price
                        )
                        
                        if new_stop_loss:
                            # Update stop loss if it's better
                            old_stop_loss = position['stop_loss']
                            
                            if position['side'] == 'BUY' and new_stop_loss > old_stop_loss:
                                position['stop_loss'] = new_stop_loss
                                await self._update_position_stop_loss(position_id, new_stop_loss)
                                logger.info(f"🔄 {position['symbol']} trailing stop updated: {old_stop_loss:.4f} -> {new_stop_loss:.4f}")
                            
                            elif position['side'] == 'SELL' and new_stop_loss < old_stop_loss:
                                position['stop_loss'] = new_stop_loss
                                await self._update_position_stop_loss(position_id, new_stop_loss)
                                logger.info(f"🔄 {position['symbol']} trailing stop updated: {old_stop_loss:.4f} -> {new_stop_loss:.4f}")
                    
                    except Exception as e:
                        logger.error(f"❌ Trailing stop update error for position {position_id}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"❌ Trailing stops update error: {e}")
    
    async def _calculate_dynamic_trailing_stop(self, position: Dict[str, Any], current_price: float) -> Optional[float]:
        """Calculate dynamic trailing stop based on market conditions"""
        try:
            entry_price = position['entry_price']
            side = position['side']
            trailing_distance = position.get('trailing_stop_distance', 0.02)
            
            # Get market volatility for dynamic adjustment
            volatility = await self._get_market_volatility(position['symbol'])
            
            # Adjust trailing distance based on volatility
            if volatility > 0.8:  # High volatility
                adjusted_distance = trailing_distance * 1.5
            elif volatility < 0.3:  # Low volatility
                adjusted_distance = trailing_distance * 0.7
            else:
                adjusted_distance = trailing_distance
            
            # Calculate profit percentage
            if side == 'BUY':
                profit_pct = (current_price - entry_price) / entry_price
            else:  # SELL
                profit_pct = (entry_price - current_price) / entry_price
            
            # Check if trailing stop should be activated
            activation_threshold = position.get('trailing_stop_activation', 0.01)
            
            if profit_pct < activation_threshold:
                return None  # Don't activate trailing stop yet
            
            # Calculate new stop loss
            if side == 'BUY':
                new_stop_loss = current_price * (1 - adjusted_distance)
                # Ensure stop loss is not below entry price (for long positions)
                new_stop_loss = max(new_stop_loss, entry_price * 0.98)
            else:  # SELL
                new_stop_loss = current_price * (1 + adjusted_distance)
                # Ensure stop loss is not above entry price (for short positions)
                new_stop_loss = min(new_stop_loss, entry_price * 1.02)
            
            return new_stop_loss
            
        except Exception as e:
            logger.error(f"❌ Dynamic trailing stop calculation error: {e}")
            return None
    
    async def _get_market_volatility(self, symbol: str) -> float:
        """Get market volatility for dynamic adjustments"""
        try:
            # Get recent price data
            market_data = await self.exchange_manager.get_market_data(symbol)
            if not market_data or 'dataframe' not in market_data:
                return 0.5  # Default volatility
            
            df = market_data['dataframe']
            if len(df) < 20:
                return 0.5
            
            # Calculate volatility as standard deviation of returns
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Annualized from hourly data
            
            return min(volatility, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"❌ Market volatility calculation error: {e}")
            return 0.5
    
    async def _update_position_stop_loss(self, position_id: int, new_stop_loss: float):
        """Update stop loss in database"""
        try:
            await self.db_manager.update_position_stop_loss(position_id, new_stop_loss)
        except Exception as e:
            logger.error(f"❌ Database stop loss update error: {e}")
    
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
                                    confidence: float, order_id: str,
                                    leverage: float = 1.0, margin_required: float = 0.0,
                                    trading_costs: Optional[Dict] = None) -> Optional[int]:
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
                'order_id': order_id,
                'leverage': leverage,
                'margin_required': margin_required,
                'trading_costs': trading_costs
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
    
    async def _calculate_trading_costs(self, symbol: str, price: float, action: Dict) -> Dict[str, Any]:
        """Calculate trading costs including fees, slippage, and funding"""
        try:
            # Base trading fee (0.1% for spot trading)
            trading_fee = 0.001
            
            # Dynamic slippage based on market conditions
            market_data = await self.exchange_manager.get_market_data(symbol)
            volume = market_data.get('volume', 1000000) if market_data else 1000000
            
            # Slippage decreases with volume
            base_slippage = 0.0005  # 0.05% base slippage
            volume_multiplier = max(0.5, min(1.5, 1000000 / volume))
            slippage = base_slippage * volume_multiplier
            
            # Funding fee (for perpetual futures)
            funding_fee = 0.0001  # 0.01% per 8 hours (simplified)
            
            # Total costs
            total_cost_pct = trading_fee + slippage + funding_fee
            
            return {
                'trading_fee': trading_fee,
                'slippage': slippage,
                'funding_fee': funding_fee,
                'total_cost_pct': total_cost_pct,
                'volume_multiplier': volume_multiplier
            }
            
        except Exception as e:
            logger.error(f"❌ Trading costs calculation error: {e}")
            return {
                'trading_fee': 0.001,
                'slippage': 0.0005,
                'funding_fee': 0.0001,
                'total_cost_pct': 0.0016,
                'volume_multiplier': 1.0
            }
    
    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'MARKET',
                         price: float = None, stop_price: float = None, time_in_force: str = 'GTC') -> Optional[Dict]:
        """Place order with different order types"""
        try:
            # Validate order parameters
            if order_type not in ['MARKET', 'LIMIT', 'STOP_LIMIT', 'STOP_MARKET']:
                logger.error(f"❌ Unsupported order type: {order_type}")
                return None
            
            # Validate price requirements
            if order_type in ['LIMIT', 'STOP_LIMIT'] and price is None:
                logger.error(f"❌ Price required for {order_type} order")
                return None
            
            if order_type in ['STOP_LIMIT', 'STOP_MARKET'] and stop_price is None:
                logger.error(f"❌ Stop price required for {order_type} order")
                return None
            
            # Get current market price for reference
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.error(f"❌ Could not get current price for {symbol}")
                return None
            
            # Calculate order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'amount': size,
                'timeInForce': time_in_force
            }
            
            # Add price parameters based on order type
            if order_type == 'LIMIT':
                order_params['price'] = price
            elif order_type == 'STOP_LIMIT':
                order_params['price'] = price
                order_params['stopPrice'] = stop_price
            elif order_type == 'STOP_MARKET':
                order_params['stopPrice'] = stop_price
            
            # Place order through exchange
            order_result = await self.exchange_manager.place_order(order_params)
            
            if order_result:
                logger.info(f"✅ {order_type} order placed for {symbol}: {side} {size}")
                return order_result
            else:
                logger.error(f"❌ Failed to place {order_type} order for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return None
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel existing order"""
        try:
            result = await self.exchange_manager.cancel_order(order_id, symbol)
            
            if result:
                logger.info(f"✅ Order {order_id} cancelled for {symbol}")
                return True
            else:
                logger.error(f"❌ Failed to cancel order {order_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Order cancellation error: {e}")
            return False
    
    async def get_order_status(self, order_id: str, symbol: str) -> Optional[Dict]:
        """Get order status"""
        try:
            return await self.exchange_manager.get_order_status(order_id, symbol)
        except Exception as e:
            logger.error(f"❌ Order status check error: {e}")
            return None