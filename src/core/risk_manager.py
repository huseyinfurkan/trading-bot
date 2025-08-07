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
            risk_config: Risk konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.db_manager = db_manager
        
        # Risk parametreleri - config'den yükleniyor
        self.max_portfolio_risk = risk_config.get('max_portfolio_risk', 0.02)
        self.max_position_risk = risk_config.get('max_position_risk', 0.01)
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)
        self.max_open_positions = risk_config.get('max_open_positions', 5)
        self.correlation_threshold = risk_config.get('correlation_threshold', 0.7)
        self.position_sizing_method = risk_config.get('position_sizing_method', 'kelly')
        
        # Dinamik korelasyon eşiği - piyasa koşullarına göre ayarlanıyor
        self.dynamic_correlation_threshold = self.correlation_threshold
        self.correlation_adjustment_factor = risk_config.get('correlation_adjustment_factor', 0.1)
        
        # Borsa bazlı trading costs - config'den yükleniyor
        self.exchange_fees = risk_config.get('exchange_fees', {
            'binance': {'maker': 0.001, 'taker': 0.001},
            'bybit': {'maker': 0.001, 'taker': 0.001},
            'okx': {'maker': 0.001, 'taker': 0.001}
        })
        
        self.slippage_config = risk_config.get('slippage_config', {
            'base_slippage': 0.0005,
            'volatility_multiplier': 2.0,
            'volume_multiplier': 1.0
        })
        
        self.funding_fee_config = risk_config.get('funding_fee_config', {
            'base_rate': 0.0001,
            'max_rate': 0.001,
            'adjustment_period': 8  # hours
        })
        
        # Position sizing parametreleri
        self.default_risk_per_trade = risk_config.get('default_risk_per_trade', 0.01)  # %1
        self.min_position_size = risk_config.get('min_position_size', 10)  # $10
        self.max_position_size = risk_config.get('max_position_size', 1000)  # $1000
        
        # Kelly criterion parametreleri
        self.kelly_fraction = risk_config.get('kelly_fraction', 0.25)  # Maksimum Kelly'nin %25'i
        self.win_rate = risk_config.get('historical_win_rate', 0.55)  # %55 kazanma oranı
        self.avg_win_loss_ratio = risk_config.get('avg_win_loss_ratio', 1.5)  # 1.5:1 oran
        
        # Portfolio tracking
        self.portfolio_value = risk_config.get('initial_portfolio_value', 10000)
        self.daily_pnl = 0
        self.open_positions_count = 0
        
        # Performance tracking
        self.risk_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
        
        logger.info("🛡️ Risk Manager initialized with dynamic configuration")
    
    async def update_dynamic_correlation_threshold(self, market_volatility: float, market_trend: float):
        """Update correlation threshold based on market conditions"""
        try:
            # Base threshold from config
            base_threshold = self.correlation_threshold
            
            # Adjust based on volatility
            volatility_adjustment = market_volatility * self.correlation_adjustment_factor
            
            # Adjust based on trend strength
            trend_adjustment = (1 - market_trend) * self.correlation_adjustment_factor * 0.5
            
            # Calculate new threshold
            new_threshold = base_threshold + volatility_adjustment - trend_adjustment
            
            # Keep within reasonable bounds
            self.dynamic_correlation_threshold = max(0.3, min(0.9, new_threshold))
            
            logger.debug(f"🔄 Dynamic correlation threshold updated: {self.dynamic_correlation_threshold:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Dynamic correlation threshold update error: {e}")
    
    async def get_exchange_specific_costs(self, exchange: str, symbol: str, order_type: str = 'market') -> Dict[str, Any]:
        """Get exchange-specific trading costs"""
        try:
            # Get exchange fees
            exchange_config = self.exchange_fees.get(exchange, self.exchange_fees['binance'])
            trading_fee = exchange_config['taker'] if order_type == 'market' else exchange_config['maker']
            
            # Get market data for slippage calculation
            market_data = await self._get_market_data_for_costs(symbol)
            volume = market_data.get('volume', 1000000)
            volatility = market_data.get('volatility', 0.5)
            
            # Calculate dynamic slippage
            base_slippage = self.slippage_config['base_slippage']
            volatility_mult = self.slippage_config['volatility_multiplier']
            volume_mult = self.slippage_config['volume_multiplier']
            
            slippage = base_slippage * (1 + volatility * volatility_mult) * (volume_mult / max(volume / 1000000, 0.1))
            
            # Calculate funding fee (for perpetual futures)
            funding_fee = self.funding_fee_config['base_rate']
            if market_data.get('funding_rate'):
                funding_fee = market_data['funding_rate']
            
            return {
                'trading_fee': trading_fee,
                'slippage': slippage,
                'funding_fee': funding_fee,
                'total_cost_pct': trading_fee + slippage + funding_fee,
                'exchange': exchange,
                'order_type': order_type
            }
            
        except Exception as e:
            logger.error(f"❌ Exchange-specific costs calculation error: {e}")
            return {
                'trading_fee': 0.001,
                'slippage': 0.0005,
                'funding_fee': 0.0001,
                'total_cost_pct': 0.0016,
                'exchange': exchange,
                'order_type': order_type
            }
    
    async def _get_market_data_for_costs(self, symbol: str) -> Dict[str, Any]:
        """Get market data for cost calculations"""
        try:
            # This should be implemented to get real market data
            # For now, return default values
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001
            }
        except Exception as e:
            logger.error(f"❌ Market data for costs error: {e}")
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001
            }
    
    async def calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float, 
                                    confidence: float = 0.5, strategy: str = None, 
                                    current_price: float = None, account_balance: float = None) -> Dict[str, Any]:
        """Enhanced position size calculation with dynamic correlation and costs"""
        try:
            # Get current account balance
            if account_balance is None:
                balance_info = await self.get_account_balance()
                account_balance = balance_info.get('total_balance', 10000)
            
            # Get current price if not provided
            if current_price is None:
                current_price = entry_price
            
            # Calculate risk amount
            risk_amount = account_balance * self.max_position_risk
            
            # Calculate position risk (entry to stop loss)
            position_risk_pct = abs(entry_price - stop_loss) / entry_price
            
            # Calculate base position size
            base_position_size = risk_amount / (account_balance * position_risk_pct)
            
            # Apply confidence multiplier
            confidence_multiplier = min(confidence * 1.5, 1.0)  # Max 1.0
            adjusted_position_size = base_position_size * confidence_multiplier
            
            # Apply strategy-specific adjustments
            strategy_multiplier = self._get_strategy_risk_multiplier(strategy)
            adjusted_position_size *= strategy_multiplier
            
            # Check correlation limits
            correlation_check = await self._check_correlation_limits(symbol, adjusted_position_size)
            if not correlation_check['allowed']:
                return {
                    'allowed': False,
                    'reason': f"Correlation limit exceeded: {correlation_check['reason']}",
                    'size': 0,
                    'risk_amount': 0
                }
            
            # Calculate trading costs
            trading_costs = await self._calculate_trading_costs(symbol, adjusted_position_size, entry_price)
            
            # Apply cost adjustment
            cost_adjusted_size = adjusted_position_size * (1 - trading_costs['total_cost_pct'])
            
            # Check position limits
            position_check = await self._check_position_limits(symbol, cost_adjusted_size, entry_price)
            if not position_check['allowed']:
                return {
                    'allowed': False,
                    'reason': position_check['reason'],
                    'size': 0,
                    'risk_amount': 0
                }
            
            # Final position size
            final_position_size = min(cost_adjusted_size, position_check['max_allowed_size'])
            
            return {
                'allowed': True,
                'size': final_position_size,
                'risk_amount': risk_amount,
                'confidence_multiplier': confidence_multiplier,
                'strategy_multiplier': strategy_multiplier,
                'trading_costs': trading_costs,
                'correlation_check': correlation_check,
                'position_check': position_check,
                'leverage_used': 1.0  # Default leverage
            }
            
        except Exception as e:
            logger.error(f"❌ Position size calculation error: {e}")
            return {
                'allowed': False,
                'reason': f"Calculation error: {str(e)}",
                'size': 0,
                'risk_amount': 0
            }
    
    async def calculate_position_size_backtest(self, symbol: str, action: Dict[str, Any],
                                             current_price: float, account_balance: float,
                                             confidence: float) -> Dict[str, Any]:
        """
        Calculate position size for backtest - matches actual call signature
        This method bridges the gap between backtest calls and existing risk logic
        """
        try:
            # Extract stop loss from action or calculate it
            stop_loss = action.get('stop_loss')
            if not stop_loss:
                # Use 2% stop loss as default
                if action.get('action') == 'BUY':
                    stop_loss = current_price * 0.98  # 2% below entry for LONG
                else:  # SELL
                    stop_loss = current_price * 1.02  # 2% above entry for SHORT
            
            # Extract strategy from action
            strategy = action.get('strategy_used', 'unknown')
            
            # Update portfolio value for calculation
            old_portfolio_value = self.portfolio_value
            self.portfolio_value = account_balance
            
            # Call the existing calculate_position_size method
            result = await self.calculate_position_size(
                symbol=symbol,
                entry_price=current_price,
                stop_loss=stop_loss,
                confidence=confidence,
                strategy=strategy
            )
            
            # Restore original portfolio value
            self.portfolio_value = old_portfolio_value
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Backtest position size calculation error: {e}")
            return {
                'allowed': False,
                'reason': f'Calculation error: {str(e)}',
                'size': 0,
                'risk_amount': 0
            }
    

    
    async def _check_correlation_limits(self, symbol: str, position_size: float) -> Dict[str, Any]:
        """Enhanced correlation check with dynamic threshold and market conditions"""
        try:
            # Get current open positions
            open_positions = await self.get_open_positions()
            
            if not open_positions:
                return {'allowed': True, 'reason': 'No existing positions'}
            
            # Get current market conditions for dynamic threshold adjustment
            market_volatility = await self._get_market_volatility(symbol)
            market_trend = await self._get_market_trend(symbol)
            
            # Update dynamic correlation threshold based on market conditions
            await self.update_dynamic_correlation_threshold(market_volatility, market_trend)
            
            # Calculate correlation with existing positions using dynamic threshold
            correlations = []
            total_correlated_exposure = 0
            
            for position in open_positions:
                pos_symbol = position.get('symbol')
                if pos_symbol != symbol:
                    # Calculate correlation between symbols
                    correlation = await self._calculate_symbol_correlation(symbol, pos_symbol)
                    correlations.append(correlation)
                    
                    # If correlation is high, add to correlated exposure
                    if correlation > self.dynamic_correlation_threshold:  # Use dynamic threshold
                        pos_value = position.get('size', 0) * position.get('entry_price', 0)
                        total_correlated_exposure += pos_value
            
            # Check if new position would exceed correlation limits
            new_position_value = position_size * self.get_current_price(symbol)
            total_exposure = total_correlated_exposure + new_position_value
            
            # Calculate portfolio correlation risk with dynamic adjustment
            avg_correlation = np.mean(correlations) if correlations else 0
            correlation_risk = avg_correlation * (total_exposure / self.get_account_balance())
            
            # Adjust risk limit based on market conditions
            adjusted_risk_limit = self.max_portfolio_risk
            if market_volatility > 0.8:  # High volatility
                adjusted_risk_limit *= 0.8  # Reduce risk limit
            elif market_volatility < 0.3:  # Low volatility
                adjusted_risk_limit *= 1.2  # Increase risk limit
            
            if correlation_risk > adjusted_risk_limit:
                return {
                    'allowed': False,
                    'reason': f"Correlation risk too high: {correlation_risk:.2%} > {adjusted_risk_limit:.2%} (market volatility: {market_volatility:.2f})"
                }
            
            return {
                'allowed': True,
                'reason': f"Correlation check passed: {correlation_risk:.2%}",
                'correlation_risk': correlation_risk,
                'avg_correlation': avg_correlation,
                'dynamic_threshold': self.dynamic_correlation_threshold,
                'market_volatility': market_volatility,
                'adjusted_risk_limit': adjusted_risk_limit
            }
            
        except Exception as e:
            logger.error(f"❌ Correlation check error: {e}")
            return {'allowed': True, 'reason': f'Correlation check error: {str(e)}'}
    
    async def _calculate_symbol_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols using historical data"""
        try:
            # Get historical data for both symbols
            data1 = await self.get_historical_data(symbol1, '1h', limit=100)
            data2 = await self.get_historical_data(symbol2, '1h', limit=100)
            
            if not data1 or not data2:
                return 0.5  # Default correlation if no data
            
            # Calculate returns
            returns1 = data1['close'].pct_change().dropna()
            returns2 = data2['close'].pct_change().dropna()
            
            # Align data
            min_length = min(len(returns1), len(returns2))
            returns1 = returns1.tail(min_length)
            returns2 = returns2.tail(min_length)
            
            # Calculate correlation
            correlation = returns1.corr(returns2)
            
            return abs(correlation) if not np.isnan(correlation) else 0.5
            
        except Exception as e:
            logger.error(f"❌ Correlation calculation error: {e}")
            return 0.5  # Default correlation
    
    async def _calculate_trading_costs(self, symbol: str, position_size: float, price: float) -> Dict[str, Any]:
        """Calculate trading costs including fees, slippage, and funding"""
        try:
            position_value = position_size * price
            
            # Get exchange-specific costs
            exchange_specific_costs = await self.get_exchange_specific_costs(symbol.split('/')[0], symbol) # Assuming symbol is like BTC/USDT
            
            # Apply exchange-specific costs
            total_cost = exchange_specific_costs['total_cost_pct'] * position_value
            
            return {
                'trading_fee': exchange_specific_costs['trading_fee'],
                'slippage': exchange_specific_costs['slippage'],
                'funding_fee': exchange_specific_costs['funding_fee'],
                'total_cost': total_cost,
                'total_cost_pct': exchange_specific_costs['total_cost_pct']
            }
            
        except Exception as e:
            logger.error(f"❌ Trading cost calculation error: {e}")
            return {
                'trading_fee': 0,
                'slippage': 0,
                'funding_fee': 0,
                'total_cost': 0,
                'total_cost_pct': 0
            }
    
    def _get_strategy_risk_multiplier(self, strategy: str) -> float:
        """Get risk multiplier based on strategy"""
        strategy_multipliers = {
            'alligator_ma_momentum': 1.0,      # Standard risk
            'bollinger_rsi_stochrsi': 0.8,     # Lower risk for mean reversion
            'scalping': 0.6,                   # Lower risk for scalping
            'swing_trading': 1.2,              # Higher risk for swing
            'trend_following': 1.1,            # Slightly higher risk
            'mean_reversion': 0.9              # Lower risk
        }
        
        return strategy_multipliers.get(strategy, 1.0)
    
    async def _check_position_limits(self, symbol: str, position_size: float, price: float) -> Dict[str, Any]:
        """Check position size limits"""
        try:
            position_value = position_size * price
            account_balance = self.get_account_balance()
            
            # Check minimum position size
            min_position_value = self.config.get('min_position_size', 10)
            if position_value < min_position_value:
                return {
                    'allowed': False,
                    'reason': f"Position too small: ${position_value:.2f} < ${min_position_value}"
                }
            
            # Check maximum position size
            max_position_value = self.config.get('max_position_size', 10000)
            if position_value > max_position_value:
                return {
                    'allowed': True,
                    'max_allowed_size': max_position_value / price,
                    'reason': f"Position capped at ${max_position_value}"
                }
            
            # Check portfolio percentage
            portfolio_pct = position_value / account_balance
            max_portfolio_pct = self.config.get('max_position_risk', 0.01)
            if portfolio_pct > max_portfolio_pct:
                max_allowed_value = account_balance * max_portfolio_pct
                return {
                    'allowed': True,
                    'max_allowed_size': max_allowed_value / price,
                    'reason': f"Position capped at {max_portfolio_pct:.1%} of portfolio"
                }
            
            return {
                'allowed': True,
                'max_allowed_size': position_size,
                'reason': "Position size within limits"
            }
            
        except Exception as e:
            logger.error(f"❌ Position limit check error: {e}")
            return {
                'allowed': False,
                'reason': f"Position limit check error: {str(e)}"
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
                'correlation_limit': self.correlation_threshold, # Use correlation_threshold from config
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
    
    def _calculate_position_size_with_leverage(self, entry_price: float, stop_loss: float, 
                                             risk_amount: float, account_balance: float, 
                                             strategy: str) -> float:
        """Leverage ve margin gereksinimlerini hesaba katarak pozisyon boyutunu hesapla"""
        try:
            # Get strategy-specific leverage
            leverage = self._get_strategy_leverage(strategy)
            
            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)
            
            # Calculate base position size (without leverage)
            base_position_size = risk_amount / risk_per_unit
            
            # Apply leverage
            leveraged_position_size = base_position_size * leverage
            
            # Check margin requirements
            margin_required = leveraged_position_size / leverage
            
            # Ensure we don't exceed account balance
            if account_balance and margin_required > account_balance * 0.95:  # 95% of balance
                max_position_size = account_balance * 0.95 * leverage
                logger.warning(f"⚠️ Position size reduced due to margin requirements")
                return max_position_size
            
            return leveraged_position_size
            
        except Exception as e:
            logger.error(f"❌ Leverage calculation error: {e}")
            return 0.0
    
    def _get_strategy_leverage(self, strategy: str) -> float:
        """Strateji bazında leverage değeri döndür"""
        leverage_map = {
            'alligator_ma_momentum': 2.0,
            'bollinger_rsi_stochrsi': 1.8,
            'scalping': 1.5,
            'swing_trading': 1.2,
            'trend_following': 1.5,
            'mean_reversion': 1.3
        }
        return leverage_map.get(strategy, 1.0)

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions from database"""
        try:
            # This should be implemented to get positions from database
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"❌ Get open positions error: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        try:
            # This should be implemented to get current price
            # For now, return a default price
            return 50000.0  # Default BTC price
        except Exception as e:
            logger.error(f"❌ Get current price error: {e}")
            return 50000.0
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        try:
            # This should be implemented to get actual balance
            # For now, return default balance
            return self.portfolio_value
        except Exception as e:
            logger.error(f"❌ Get account balance error: {e}")
            return 100000.0
    
    async def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get historical data for correlation calculation"""
        try:
            # This should be implemented to get historical data
            # For now, return None to use default correlation
            return None
        except Exception as e:
            logger.error(f"❌ Get historical data error: {e}")
            return None

    async def _get_market_volatility(self, symbol: str) -> float:
        """Get current market volatility for dynamic adjustments"""
        try:
            # Get recent price data
            historical_data = await self.get_historical_data(symbol, '1h', limit=24)
            if historical_data is None or len(historical_data) < 12:
                return 0.5  # Default volatility
            
            # Calculate volatility as standard deviation of returns
            returns = historical_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Annualized from hourly data
            
            return min(volatility, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"❌ Market volatility calculation error: {e}")
            return 0.5
    
    async def _get_market_trend(self, symbol: str) -> float:
        """Get current market trend strength for dynamic adjustments"""
        try:
            # Get recent price data
            historical_data = await self.get_historical_data(symbol, '1h', limit=48)
            if historical_data is None or len(historical_data) < 24:
                return 0.5  # Default trend strength
            
            # Calculate trend strength using moving averages
            short_ma = historical_data['close'].rolling(window=6).mean()
            long_ma = historical_data['close'].rolling(window=24).mean()
            
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            
            if current_long == 0:
                return 0.5
            
            # Calculate trend strength
            trend_strength = (current_short - current_long) / current_long
            
            # Normalize to 0-1 range
            return min(max(trend_strength + 0.5, 0), 1)
            
        except Exception as e:
            logger.error(f"❌ Market trend calculation error: {e}")
            return 0.5
    
    async def get_exchange_specific_costs(self, exchange: str, symbol: str, order_type: str = 'market') -> Dict[str, Any]:
        """Get exchange-specific trading costs with real-time data"""
        try:
            # Get exchange fees from config
            exchange_config = self.exchange_fees.get(exchange, self.exchange_fees['binance'])
            trading_fee = exchange_config['taker'] if order_type == 'market' else exchange_config['maker']
            
            # Get real-time market data for dynamic cost calculation
            market_data = await self._get_real_time_market_data(symbol, exchange)
            volume = market_data.get('volume', 1000000)
            volatility = market_data.get('volatility', 0.5)
            funding_rate = market_data.get('funding_rate', self.funding_fee_config['base_rate'])
            
            # Calculate dynamic slippage based on market conditions
            base_slippage = self.slippage_config['base_slippage']
            volatility_mult = self.slippage_config['volatility_multiplier']
            volume_mult = self.slippage_config['volume_multiplier']
            
            # Adjust slippage based on volatility and volume
            slippage = base_slippage * (1 + volatility * volatility_mult)
            slippage *= max(0.5, min(2.0, volume_mult / max(volume / 1000000, 0.1)))
            
            # Get exchange-specific funding rate
            if exchange in ['bybit', 'binance', 'okx']:
                # These exchanges have perpetual futures with funding rates
                funding_fee = funding_rate
            else:
                # Spot trading
                funding_fee = 0.0
            
            # Calculate total costs
            total_cost_pct = trading_fee + slippage + funding_fee
            
            return {
                'trading_fee': trading_fee,
                'slippage': slippage,
                'funding_fee': funding_fee,
                'total_cost_pct': total_cost_pct,
                'exchange': exchange,
                'order_type': order_type,
                'market_volume': volume,
                'market_volatility': volatility,
                'funding_rate': funding_rate
            }
            
        except Exception as e:
            logger.error(f"❌ Exchange-specific costs calculation error: {e}")
            return {
                'trading_fee': 0.001,
                'slippage': 0.0005,
                'funding_fee': 0.0001,
                'total_cost_pct': 0.0016,
                'exchange': exchange,
                'order_type': order_type,
                'market_volume': 1000000,
                'market_volatility': 0.5,
                'funding_rate': 0.0001
            }
    
    async def _get_real_time_market_data(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get real-time market data for cost calculations"""
        try:
            # This should be implemented to get real market data from exchange
            # For now, return default values
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001,
                'bid_ask_spread': 0.0005
            }
        except Exception as e:
            logger.error(f"❌ Real-time market data error: {e}")
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001,
                'bid_ask_spread': 0.0005
            }