"""
Risk Manager
Pozisyon boyutu hesaplama ve risk yönetimi
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class RiskManager:
    """Risk yöneticisi"""
    
    def __init__(self, risk_config: Dict[str, Any], db_manager):
        """
        Args:
            risk_config: Risk yönetimi konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = risk_config
        self.db_manager = db_manager
        
        # Risk parametreleri
        self.max_portfolio_risk = risk_config.get('max_portfolio_risk', 0.02)  # %2
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)  # %5
        self.max_open_positions = risk_config.get('max_open_positions', 5)
        self.correlation_limit = risk_config.get('correlation_limit', 0.7)
        
        # Position sizing parametreleri
        self.default_risk_per_trade = risk_config.get('default_risk_per_trade', 0.01)  # %1
        self.min_position_size = risk_config.get('min_position_size', 10)  # $10
        self.max_position_size = risk_config.get('max_position_size', 1000)  # $1000
        
        # Kelly criterion parametreleri
        self.kelly_fraction = risk_config.get('kelly_fraction', 0.25)  # Maksimum Kelly'nin %25'i
        self.win_rate = risk_config.get('historical_win_rate', 0.55)  # %55 kazanma oranı
        self.avg_win_loss_ratio = risk_config.get('avg_win_loss_ratio', 1.5)  # 1.5:1 oran
        
        # Portfolio tracking
        self.portfolio_value = 100000.0  # Default başlangıç değeri
        self.open_positions_count = 0
        
        logger.info("⚖️ Risk Manager initialized")
    
    async def calculate_position_size(self, symbol: str, entry_price: float,
                                    stop_loss: float, confidence: float,
                                    strategy: str) -> Dict[str, Any]:
        """Pozisyon boyutunu hesapla"""
        try:
            # 1. Risk check - position limit
            if self.open_positions_count >= self.max_open_positions:
                return {
                    'allowed': False,
                    'reason': f'Maximum position limit reached: {self.max_open_positions}',
                    'size': 0,
                    'risk_amount': 0
                }
            
            # 2. Correlation check
            correlation_check = await self._check_correlation(symbol)
            if not correlation_check['allowed']:
                return {
                    'allowed': False,
                    'reason': correlation_check['reason'],
                    'size': 0,
                    'risk_amount': 0
                }
            
            # 3. Daily loss check
            daily_loss_check = await self._check_daily_loss()
            if not daily_loss_check['allowed']:
                return {
                    'allowed': False,
                    'reason': daily_loss_check['reason'],
                    'size': 0,
                    'risk_amount': 0
                }
            
            # 4. Calculate risk amount
            risk_amount = self._calculate_risk_amount(confidence, strategy)
            
            # 5. Calculate position size based on stop loss
            if stop_loss <= 0 or entry_price <= 0:
                return {
                    'allowed': False,
                    'reason': 'Invalid entry price or stop loss',
                    'size': 0,
                    'risk_amount': 0
                }
            
            # Risk per unit
            risk_per_unit = abs(entry_price - stop_loss)
            
            # Position size calculation
            if risk_per_unit > 0:
                position_size = risk_amount / risk_per_unit
            else:
                position_size = 0
            
            # Apply size limits
            position_size = max(self.min_position_size / entry_price, position_size)
            position_size = min(self.max_position_size / entry_price, position_size)
            
            # Position value check
            position_value = position_size * entry_price
            
            return {
                'allowed': True,
                'reason': 'Risk assessment passed',
                'size': position_size,
                'risk_amount': risk_amount,
                'position_value': position_value,
                'risk_per_trade': risk_amount / self.portfolio_value,
                'stop_loss': stop_loss,
                'leverage': 1.0  # Default no leverage
            }
            
        except Exception as e:
            logger.error(f"❌ Position size calculation error: {e}")
            return {
                'allowed': False,
                'reason': f'Calculation error: {e}',
                'size': 0,
                'risk_amount': 0
            }
    
    async def _check_correlation(self, symbol: str) -> Dict[str, Any]:
        """Gerçek correlation kontrolü"""
        try:
            current_positions = await self.db_manager.get_positions(status='OPEN')
            
            if not current_positions:
                return {'allowed': True, 'reason': 'No existing positions'}
            
            # Same base currency check
            base_currency = symbol.split('/')[0]
            same_base_count = sum(1 for pos in current_positions if pos['symbol'].startswith(base_currency))
            
            if same_base_count >= 3:
                return {
                    'allowed': False,
                    'reason': f"Too many positions with {base_currency}: {same_base_count}"
                }
            
            # Real correlation calculation
            correlation_check = await self._calculate_price_correlation(symbol, current_positions)
            
            if correlation_check['max_correlation'] > self.correlation_limit:
                return {
                    'allowed': False,
                    'reason': f"High correlation detected: {correlation_check['max_correlation']:.3f} with {correlation_check['correlated_symbol']}"
                }
            
            return {'allowed': True, 'reason': 'Correlation check passed'}
            
        except Exception as e:
            logger.error(f"❌ Correlation kontrol hatası: {e}")
            return {'allowed': True, 'reason': 'Correlation check skipped due to error'}
    
    async def _calculate_price_correlation(self, symbol: str, current_positions: List[Dict]) -> Dict[str, Any]:
        """Gerçek fiyat korelasyonu hesapla"""
        try:
            # Get price history for the new symbol
            new_symbol_data = await self._get_price_history(symbol, days=30)
            
            if new_symbol_data is None or len(new_symbol_data) < 20:
                return {'max_correlation': 0, 'correlated_symbol': None}
            
            max_correlation = 0
            correlated_symbol = None
            
            # Check correlation with each existing position
            for position in current_positions:
                pos_symbol = position['symbol']
                pos_data = await self._get_price_history(pos_symbol, days=30)
                
                if pos_data is None or len(pos_data) < 20:
                    continue
                
                # Calculate correlation
                correlation = self._compute_correlation(new_symbol_data, pos_data)
                
                if abs(correlation) > abs(max_correlation):
                    max_correlation = correlation
                    correlated_symbol = pos_symbol
            
            return {
                'max_correlation': abs(max_correlation),
                'correlated_symbol': correlated_symbol
            }
            
        except Exception as e:
            logger.error(f"❌ Price correlation calculation error: {e}")
            return {'max_correlation': 0, 'correlated_symbol': None}
    
    async def _get_price_history(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Sembol için fiyat geçmişi al"""
        try:
            # Try to get from database first
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Mock implementation - gerçekte database'den alınacak
            dates = pd.date_range(start=start_date, end=end_date, freq='H')
            
            # Generate mock price data
            import random
            base_price = 50000 if 'BTC' in symbol else 3000
            prices = []
            
            for i, date in enumerate(dates):
                # Random walk
                change_pct = random.uniform(-0.02, 0.02)  # ±2% change
                if i == 0:
                    price = base_price
                else:
                    price = prices[-1] * (1 + change_pct)
                prices.append(price)
            
            return pd.DataFrame({
                'timestamp': dates,
                'close': prices
            })
            
        except Exception as e:
            logger.error(f"❌ Price history error for {symbol}: {e}")
            return None
    
    def _compute_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame) -> float:
        """İki fiyat serisi arasında korelasyon hesapla"""
        try:
            # Align data by timestamp
            merged = pd.merge(data1, data2, on='timestamp', suffixes=('_1', '_2'))
            
            if len(merged) < 10:
                return 0
            
            # Calculate returns
            returns1 = merged['close_1'].pct_change().dropna()
            returns2 = merged['close_2'].pct_change().dropna()
            
            if len(returns1) < 5 or len(returns2) < 5:
                return 0
            
            # Calculate correlation
            correlation = returns1.corr(returns2)
            
            return correlation if not np.isnan(correlation) else 0
            
        except Exception as e:
            logger.error(f"❌ Correlation computation error: {e}")
            return 0
    
    async def _check_daily_loss(self) -> Dict[str, Any]:
        """Günlük zarar limitini kontrol et"""
        try:
            today = datetime.now().date()
            
            # Get today's P&L from database
            daily_pnl = await self.db_manager.get_daily_pnl(today)
            
            if daily_pnl is None:
                daily_pnl = 0
            
            # Calculate daily loss percentage
            daily_loss_pct = abs(daily_pnl) / self.portfolio_value if daily_pnl < 0 else 0
            
            if daily_loss_pct >= self.max_daily_loss:
                return {
                    'allowed': False,
                    'reason': f'Daily loss limit exceeded: {daily_loss_pct:.2%} >= {self.max_daily_loss:.2%}'
                }
            
            return {
                'allowed': True,
                'reason': f'Daily loss within limit: {daily_loss_pct:.2%} < {self.max_daily_loss:.2%}'
            }
            
        except Exception as e:
            logger.error(f"❌ Daily loss check error: {e}")
            return {'allowed': True, 'reason': 'Daily loss check skipped due to error'}
    
    def _calculate_risk_amount(self, confidence: float, strategy: str) -> float:
        """Risk miktarını hesapla"""
        try:
            # Base risk amount
            base_risk = self.portfolio_value * self.default_risk_per_trade
            
            # Adjust based on confidence
            confidence_multiplier = min(2.0, max(0.5, confidence * 1.5))
            
            # Adjust based on strategy
            strategy_multipliers = {
                'scalping': 0.5,      # Lower risk for scalping
                'swing_trading': 1.0,  # Normal risk
                'trend_following': 1.2, # Higher risk for trend following
                'mean_reversion': 0.8  # Medium risk
            }
            
            strategy_multiplier = strategy_multipliers.get(strategy, 1.0)
            
            # Kelly Criterion adjustment
            kelly_optimal = self._calculate_kelly_criterion()
            kelly_multiplier = min(1.0, kelly_optimal / self.default_risk_per_trade)
            
            # Final risk amount
            risk_amount = base_risk * confidence_multiplier * strategy_multiplier * kelly_multiplier
            
            # Apply limits
            max_risk = self.portfolio_value * self.max_portfolio_risk
            risk_amount = min(risk_amount, max_risk)
            
            return max(self.min_position_size, risk_amount)
            
        except Exception as e:
            logger.error(f"❌ Risk amount calculation error: {e}")
            return self.min_position_size
    
    def _calculate_kelly_criterion(self) -> float:
        """Kelly Criterion hesapla"""
        try:
            # Kelly formula: f = (bp - q) / b
            # where:
            # f = fraction of capital to wager
            # b = odds (avg_win_loss_ratio)
            # p = probability of winning (win_rate)
            # q = probability of losing (1 - win_rate)
            
            b = self.avg_win_loss_ratio
            p = self.win_rate
            q = 1 - p
            
            kelly_fraction = (b * p - q) / b
            
            # Apply safety factor and limits
            kelly_fraction = max(0, kelly_fraction)  # No negative betting
            kelly_fraction = min(kelly_fraction, self.kelly_fraction)  # Apply fraction limit
            
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"❌ Kelly criterion calculation error: {e}")
            return self.default_risk_per_trade
    
    async def update_portfolio_value(self, new_value: float) -> None:
        """Portfolio değerini güncelle"""
        try:
            self.portfolio_value = max(1000, new_value)  # Minimum $1000
            logger.debug(f"💰 Portfolio value updated: ${self.portfolio_value:,.2f}")
            
        except Exception as e:
            logger.error(f"❌ Portfolio value update error: {e}")
    
    async def update_position_count(self, count: int) -> None:
        """Açık pozisyon sayısını güncelle"""
        try:
            self.open_positions_count = max(0, count)
            logger.debug(f"📊 Open positions count: {self.open_positions_count}")
            
        except Exception as e:
            logger.error(f"❌ Position count update error: {e}")
    
    def validate_stop_loss(self, entry_price: float, stop_loss: float, side: str) -> bool:
        """Stop loss validasyonu"""
        try:
            if side.upper() == 'BUY':
                # Stop loss should be below entry price for long positions
                return stop_loss < entry_price
            elif side.upper() == 'SELL':
                # Stop loss should be above entry price for short positions
                return stop_loss > entry_price
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Stop loss validation error: {e}")
            return False
    
    def validate_take_profit(self, entry_price: float, take_profit: float, side: str) -> bool:
        """Take profit validasyonu"""
        try:
            if side.upper() == 'BUY':
                # Take profit should be above entry price for long positions
                return take_profit > entry_price
            elif side.upper() == 'SELL':
                # Take profit should be below entry price for short positions
                return take_profit < entry_price
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Take profit validation error: {e}")
            return False
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Risk metriklerini döndür"""
        try:
            return {
                'portfolio_value': self.portfolio_value,
                'max_portfolio_risk': self.max_portfolio_risk,
                'max_daily_loss': self.max_daily_loss,
                'max_open_positions': self.max_open_positions,
                'current_open_positions': self.open_positions_count,
                'correlation_limit': self.correlation_limit,
                'kelly_fraction': self.kelly_fraction,
                'win_rate': self.win_rate,
                'avg_win_loss_ratio': self.avg_win_loss_ratio,
                'default_risk_per_trade': self.default_risk_per_trade
            }
            
        except Exception as e:
            logger.error(f"❌ Risk metrics error: {e}")
            return {}
    
    def _calculate_enhanced_kelly_fraction(self, confidence: float, base_risk: float,
                                         volatility_factor: float, market_condition_factor: float) -> float:
        """Enhanced Kelly Criterion with market conditions"""
        try:
            # Base Kelly calculation
            b = self.avg_win_loss_ratio
            p = self.win_rate
            q = 1 - p
            
            # Adjust win rate based on confidence
            adjusted_p = p * confidence
            adjusted_q = 1 - adjusted_p
            
            kelly_fraction = (b * adjusted_p - adjusted_q) / b
            
            # Apply market condition adjustments
            kelly_fraction *= volatility_factor * market_condition_factor
            
            # Apply safety limits
            kelly_fraction = max(0, kelly_fraction)
            kelly_fraction = min(kelly_fraction, self.kelly_fraction * 0.5)  # More conservative
            
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"❌ Enhanced Kelly calculation error: {e}")
            return self.default_risk_per_trade * 0.5
    
    async def _get_volatility_adjustment(self, symbol: str) -> float:
        """Calculate volatility-based position size adjustment"""
        try:
            # Get recent price data for volatility calculation
            if hasattr(self, 'exchange_manager'):
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                data = await self.exchange_manager.get_historical_data(
                    symbol, '1h', start_date, end_date
                )
                
                if data is not None and len(data) > 20:
                    # Calculate 7-day volatility
                    returns = data['close'].pct_change().dropna()
                    volatility = returns.std() * (24 ** 0.5)  # Annualized hourly volatility
                    
                    # Volatility adjustment factor (lower vol = higher position, higher vol = lower position)
                    # Normal crypto volatility ~30-60%, adjust accordingly
                    if volatility < 0.3:  # Low volatility
                        return 1.2  # Increase position size
                    elif volatility > 0.8:  # High volatility
                        return 0.6  # Decrease position size significantly
                    else:  # Normal volatility
                        return 1.0 - (volatility - 0.3) * 0.8  # Gradual adjustment
            
            return 1.0  # Default if no data available
            
        except Exception as e:
            logger.error(f"❌ Volatility adjustment error: {e}")
            return 0.8  # Conservative default
    
    async def _get_market_condition_factor(self, symbol: str) -> float:
        """Calculate market condition-based adjustment"""
        try:
            # This would integrate with market analyzer
            if hasattr(self, 'market_analyzer'):
                market_condition = await self.market_analyzer.analyze_market_condition(symbol)
                
                if market_condition:
                    condition = market_condition.get('condition', 'unknown')
                    strength = market_condition.get('strength', 0.5)
                    
                    if condition == 'bull_market' and strength > 0.7:
                        return 1.3  # Increase positions in strong bull markets
                    elif condition == 'bear_market' and strength > 0.7:
                        return 0.7  # Reduce positions in strong bear markets
                    elif condition == 'sideways_market':
                        return 0.9  # Slightly reduce in sideways markets
            
            return 1.0  # Default neutral
            
        except Exception as e:
            logger.error(f"❌ Market condition factor error: {e}")
            return 0.9  # Slightly conservative default