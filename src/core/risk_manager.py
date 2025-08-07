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
import math
import os # Added for os.getenv


class RiskManager:
    """Risk yöneticisi"""
    
    def __init__(self, config: Dict[str, Any], exchange_manager=None):
        """Initialize RiskManager with config"""
        self.config = config
        self.exchange_manager = exchange_manager
        
        # Load risk parameters from config
        risk_config = config.get('trading', {}).get('risk_management', {})
        
        # Core risk parameters
        self.max_portfolio_risk = risk_config.get('max_portfolio_risk', 0.02)
        self.max_position_risk = risk_config.get('max_position_risk', 0.01)
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)
        self.max_open_positions = risk_config.get('max_open_positions', 10)
        self.correlation_threshold = risk_config.get('correlation_threshold', 0.7)
        self.correlation_adjustment_factor = risk_config.get('correlation_adjustment_factor', 0.1)
        self.min_position_size = risk_config.get('min_position_size', 10)
        self.max_position_size = risk_config.get('max_position_size', 10000)
        
        # Position sizing configuration
        position_sizing_config = risk_config.get('position_sizing', {})
        self.position_sizing_method = position_sizing_config.get('method', 'kelly')
        self.kelly_fraction = position_sizing_config.get('kelly_fraction', 0.25)
        self.fixed_amount = position_sizing_config.get('fixed_amount', 100)
        self.percentage_amount = position_sizing_config.get('percentage', 0.02)
        
        # Stop loss and take profit configuration
        stop_loss_config = risk_config.get('stop_loss', {})
        self.default_stop_loss = stop_loss_config.get('default_percentage', 0.02)
        self.trailing_stop_enabled = stop_loss_config.get('trailing_enabled', True)
        self.trailing_stop_distance = stop_loss_config.get('trailing_distance', 0.01)
        
        take_profit_config = risk_config.get('take_profit', {})
        self.default_take_profit = take_profit_config.get('default_percentage', 0.04)
        self.trailing_take_profit_enabled = take_profit_config.get('trailing_enabled', True)
        self.trailing_take_profit_distance = take_profit_config.get('trailing_distance', 0.005)
        
        # Exchange-specific trading costs
        exchange_fees_config = risk_config.get('exchange_fees', {})
        self.exchange_fees = {
            'binance': exchange_fees_config.get('binance', {'maker': 0.001, 'taker': 0.001}),
            'bybit': exchange_fees_config.get('bybit', {'maker': 0.001, 'taker': 0.001}),
            'okx': exchange_fees_config.get('okx', {'maker': 0.0008, 'taker': 0.001})
        }
        
        # Slippage configuration
        slippage_config = risk_config.get('slippage_config', {})
        self.base_slippage = slippage_config.get('base_slippage', 0.0005)
        self.volatility_multiplier = slippage_config.get('volatility_multiplier', 2.0)
        self.volume_multiplier = slippage_config.get('volume_multiplier', 1.0)
        
        # Funding fee configuration
        funding_config = risk_config.get('funding_fee_config', {})
        self.base_funding_rate = funding_config.get('base_rate', 0.0001)
        self.max_funding_rate = funding_config.get('max_rate', 0.001)
        self.funding_adjustment_period = funding_config.get('adjustment_period', 8)
        
        # Dynamic correlation threshold
        self.dynamic_correlation_threshold = self.correlation_threshold
        
        # Account balance (will be updated)
        self.account_balance = 10000  # Default
        
        # Performance tracking
        self.daily_pnl = 0
        self.total_trades = 0
        self.winning_trades = 0
        
        logger.info("🔒 RiskManager initialized with config parameters")
        logger.info(f"📊 Risk settings: Portfolio={self.max_portfolio_risk:.1%}, Position={self.max_position_risk:.1%}, Daily Loss={self.max_daily_loss:.1%}")
    
    async def calculate_position_size(self, symbol: str = None, entry_price: float = None,
                                    stop_loss: float = None, leverage: float = 1.0,
                                    confidence: float = 0.5, strategy: str = "default") -> Dict[str, Any]:
        """Calculate position size based on risk parameters and market conditions"""
        try:
            # Validate inputs
            if not entry_price or entry_price <= 0:
                return {'allowed': False, 'size': 0, 'leverage_used': 1.0, 'reason': 'Invalid entry price'}
            
            if not stop_loss or stop_loss <= 0:
                return {'allowed': False, 'size': 0, 'leverage_used': 1.0, 'reason': 'Invalid stop loss'}
            
            # Calculate risk amount based on confidence and strategy
            risk_amount = self._calculate_risk_amount(confidence, strategy)
            
            # Get account balance
            account_balance = self.account_balance
            
            # Calculate position size with leverage
            position_size = self._calculate_position_size_with_leverage(
                entry_price, stop_loss, risk_amount, account_balance, strategy
            )
            
            # Apply leverage
            leverage_used = min(leverage, self._get_strategy_leverage(strategy))
            position_size *= leverage_used
            
            # Check position limits
            limits_check = await self._check_position_limits(symbol, position_size, entry_price)
            if not limits_check.get('allowed', True):
                return {
                    'allowed': False,
                    'size': 0,
                    'leverage_used': leverage_used,
                    'reason': limits_check.get('reason', 'Position limits exceeded')
                }
            
            # Check correlation
            correlation_check = await self._check_correlation(symbol)
            if not correlation_check.get('allowed', True):
                return {
                    'allowed': False,
                    'size': 0,
                    'leverage_used': leverage_used,
                    'reason': correlation_check.get('reason', 'Correlation limit exceeded')
                }
            
            return {
                'allowed': True,
                'size': position_size,
                'leverage_used': leverage_used,
                'risk_amount': risk_amount,
                'account_balance': account_balance
            }
            
        except Exception as e:
            logger.error(f"❌ Position size calculation error: {e}")
            return {'allowed': False, 'size': 0, 'leverage_used': 1.0, 'reason': f'Calculation error: {e}'}
    
    async def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status for monitoring"""
        try:
            # Get current portfolio risk
            portfolio_risk = self.daily_pnl / self.account_balance if self.account_balance > 0 else 0
            
            # Get open positions count
            open_positions = len(await self.get_open_positions())
            
            # Get daily loss
            daily_loss = abs(self.daily_pnl) / self.account_balance if self.account_balance > 0 else 0
            
            return {
                'portfolio_risk': portfolio_risk,
                'open_positions': open_positions,
                'daily_loss': daily_loss,
                'account_balance': self.account_balance,
                'max_open_positions': self.max_open_positions,
                'max_daily_loss': self.max_daily_loss,
                'max_portfolio_risk': self.max_portfolio_risk
            }
            
        except Exception as e:
            logger.error(f"❌ Risk status error: {e}")
            return {
                'portfolio_risk': 0,
                'open_positions': 0,
                'daily_loss': 0,
                'account_balance': self.account_balance,
                'max_open_positions': self.max_open_positions,
                'max_daily_loss': self.max_daily_loss,
                'max_portfolio_risk': self.max_portfolio_risk
            }
    
    async def update_config_parameters(self, new_config: Dict[str, Any]):
        """Update risk parameters from new config"""
        try:
            risk_config = new_config.get('trading', {}).get('risk_management', {})
            
            # Update core risk parameters
            self.max_portfolio_risk = risk_config.get('max_portfolio_risk', self.max_portfolio_risk)
            self.max_position_risk = risk_config.get('max_position_risk', self.max_position_risk)
            self.max_daily_loss = risk_config.get('max_daily_loss', self.max_daily_loss)
            self.max_open_positions = risk_config.get('max_open_positions', self.max_open_positions)
            self.correlation_threshold = risk_config.get('correlation_threshold', self.correlation_threshold)
            self.correlation_adjustment_factor = risk_config.get('correlation_adjustment_factor', self.correlation_adjustment_factor)
            self.min_position_size = risk_config.get('min_position_size', self.min_position_size)
            self.max_position_size = risk_config.get('max_position_size', self.max_position_size)
            
            # Update position sizing
            position_sizing_config = risk_config.get('position_sizing', {})
            self.position_sizing_method = position_sizing_config.get('method', self.position_sizing_method)
            self.kelly_fraction = position_sizing_config.get('kelly_fraction', self.kelly_fraction)
            self.fixed_amount = position_sizing_config.get('fixed_amount', self.fixed_amount)
            self.percentage_amount = position_sizing_config.get('percentage', self.percentage_amount)
            
            # Update stop loss and take profit
            stop_loss_config = risk_config.get('stop_loss', {})
            self.default_stop_loss = stop_loss_config.get('default_percentage', self.default_stop_loss)
            self.trailing_stop_enabled = stop_loss_config.get('trailing_enabled', self.trailing_stop_enabled)
            self.trailing_stop_distance = stop_loss_config.get('trailing_distance', self.trailing_stop_distance)
            
            take_profit_config = risk_config.get('take_profit', {})
            self.default_take_profit = take_profit_config.get('default_percentage', self.default_take_profit)
            self.trailing_take_profit_enabled = take_profit_config.get('trailing_enabled', self.trailing_take_profit_enabled)
            self.trailing_take_profit_distance = take_profit_config.get('trailing_distance', self.trailing_take_profit_distance)
            
            # Update exchange fees
            exchange_fees_config = risk_config.get('exchange_fees', {})
            for exchange in ['binance', 'bybit', 'okx']:
                if exchange in exchange_fees_config:
                    self.exchange_fees[exchange].update(exchange_fees_config[exchange])
            
            # Update slippage and funding config
            slippage_config = risk_config.get('slippage_config', {})
            self.base_slippage = slippage_config.get('base_slippage', self.base_slippage)
            self.volatility_multiplier = slippage_config.get('volatility_multiplier', self.volatility_multiplier)
            self.volume_multiplier = slippage_config.get('volume_multiplier', self.volume_multiplier)
            
            funding_config = risk_config.get('funding_fee_config', {})
            self.base_funding_rate = funding_config.get('base_rate', self.base_funding_rate)
            self.max_funding_rate = funding_config.get('max_rate', self.max_funding_rate)
            self.funding_adjustment_period = funding_config.get('adjustment_period', self.funding_adjustment_period)
            
            logger.info("🔄 RiskManager config parameters updated")
            logger.info(f"📊 Updated risk settings: Portfolio={self.max_portfolio_risk:.1%}, Position={self.max_position_risk:.1%}")
            
        except Exception as e:
            logger.error(f"❌ Config update error: {e}")
    
    def get_current_risk_settings(self) -> Dict[str, Any]:
        """Get current risk settings for monitoring"""
        return {
            'max_portfolio_risk': self.max_portfolio_risk,
            'max_position_risk': self.max_position_risk,
            'max_daily_loss': self.max_daily_loss,
            'max_open_positions': self.max_open_positions,
            'correlation_threshold': self.correlation_threshold,
            'dynamic_correlation_threshold': self.dynamic_correlation_threshold,
            'min_position_size': self.min_position_size,
            'max_position_size': self.max_position_size,
            'position_sizing_method': self.position_sizing_method,
            'default_stop_loss': self.default_stop_loss,
            'default_take_profit': self.default_take_profit,
            'trailing_stop_enabled': self.trailing_stop_enabled,
            'trailing_take_profit_enabled': self.trailing_take_profit_enabled,
            'account_balance': self.account_balance,
            'daily_pnl': self.daily_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades
        }
    
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
            market_data = await self._get_market_data_for_costs(symbol, exchange)
            volume = market_data.get('volume', 1000000)
            volatility = market_data.get('volatility', 0.5)
            
            # Calculate dynamic slippage
            base_slippage = self.base_slippage
            volatility_mult = self.volatility_multiplier
            volume_mult = self.volume_multiplier
            
            slippage = base_slippage * (1 + volatility * volatility_mult) * (volume_mult / max(volume / 1000000, 0.1))
            
            # Calculate funding fee (for perpetual futures)
            funding_fee = self.base_funding_rate
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
    
    async def _get_market_data_for_costs(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get real market data for cost calculations from exchange APIs"""
        try:
            # Get real exchange instance
            exchange_instance = await self._get_exchange_instance(exchange)
            if not exchange_instance:
                return await self._get_fallback_market_data(symbol, exchange)
            
            # Fetch real-time order book
            order_book = await self._fetch_real_order_book(exchange_instance, symbol)
            
            # Fetch real-time funding rate
            funding_rate = await self._fetch_real_funding_rate(exchange_instance, symbol)
            
            # Fetch real-time ticker data
            ticker = await self._fetch_real_ticker(exchange_instance, symbol)
            
            # Calculate real-time slippage from order book
            slippage = await self._calculate_real_slippage(order_book, ticker)
            
            # Calculate real-time volatility
            volatility = await self._calculate_real_volatility(exchange_instance, symbol)
            
            return {
                'volume': ticker.get('quoteVolume', 1000000),
                'volatility': volatility,
                'funding_rate': funding_rate,
                'bid_ask_spread': slippage['bid_ask_spread'],
                'order_book_depth': order_book,
                'last_price': ticker.get('last', 50000),
                'timestamp': datetime.now(),
                'real_data': True,
                'slippage_estimate': slippage['slippage_estimate']
            }
            
        except Exception as e:
            logger.error(f"❌ Real market data fetch error: {e}")
            return await self._get_fallback_market_data(symbol, exchange)
    
    async def _get_fallback_market_data(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get fallback market data when real API is unavailable - NO SIMULATION"""
        try:
            # Try to get historical data for fallback calculation
            if self.exchange_manager:
                historical_data = await self.exchange_manager.get_historical_data(symbol, '1h', limit=24)
                
                if historical_data is not None and len(historical_data) > 0:
                    # Calculate volatility from historical data
                    returns = historical_data['close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(24) if len(returns) > 0 else 0.5
                    
                    # Get volume from historical data
                    volume = historical_data['volume'].iloc[-1] if 'volume' in historical_data.columns else 1000000
                    
                                # Calculate bid-ask spread estimate from high-low range
            high_low_spread = (historical_data['high'].iloc[-1] - historical_data['low'].iloc[-1]) / historical_data['close'].iloc[-1]
            bid_ask_spread = high_low_spread * 0.1  # Estimate 10% of high-low range
            
            # Get real funding rate from exchange
            funding_rate = 0.0001  # Default, will be updated by real API
            try:
                funding_info = await self.exchange_manager.get_funding_rate(symbol, exchange)
                if funding_info:
                    funding_rate = funding_info.get('fundingRate', 0.0001)
            except Exception as e:
                logger.warning(f"⚠️ Failed to get funding rate for {symbol}: {e}")
                    
                    return {
                        'volume': volume,
                        'volatility': min(volatility, 1.0),
                        'funding_rate': funding_rate,
                        'bid_ask_spread': max(bid_ask_spread, 0.0001),
                        'order_book_depth': {},
                        'last_price': historical_data['close'].iloc[-1],
                        'timestamp': datetime.now(),
                        'real_data': False,
                        'note': 'Using historical data fallback'
                    }
            
            # Ultimate fallback - minimal data only
            logger.warning(f"⚠️ No historical data available for {symbol}, using minimal fallback")
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001,
                'bid_ask_spread': 0.0005,
                'order_book_depth': {},
                'last_price': 50000,
                'timestamp': datetime.now(),
                'real_data': False,
                'note': 'Minimal fallback - no real data available'
            }
                
        except Exception as e:
            logger.error(f"❌ Fallback market data calculation error: {e}")
            return {
                'volume': 1000000,
                'volatility': 0.5,
                'funding_rate': 0.0001,
                'bid_ask_spread': 0.0005,
                'order_book_depth': {},
                'last_price': 50000,
                'timestamp': datetime.now(),
                'real_data': False,
                'note': 'Error in fallback calculation'
            }
    
    async def _get_high_frequency_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get high-frequency price data for correlation calculation"""
        try:
            # Try to get 1-minute data for high-frequency correlation
            if self.exchange_manager:
                # Get 1-minute OHLCV data
                data = await self.exchange_manager.get_historical_data(
                    symbol=symbol,
                    timeframe='1m',
                    limit=limit
                )
                
                if data is not None and len(data) > 0:
                    # Calculate returns
                    data['returns'] = data['close'].pct_change().dropna()
                    return data
            
            # Fallback to 5-minute data if 1-minute not available
            if self.exchange_manager:
                data = await self.exchange_manager.get_historical_data(
                    symbol=symbol,
                    timeframe='5m',
                    limit=limit
                )
                
                if data is not None and len(data) > 0:
                    data['returns'] = data['close'].pct_change().dropna()
                    return data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ High-frequency data fetch error for {symbol}: {e}")
            return None
    
    def _align_time_series(self, data1: pd.DataFrame, data2: pd.DataFrame) -> pd.DataFrame:
        """Align two time series for correlation calculation"""
        try:
            # Create a combined dataframe with aligned timestamps
            df1 = data1[['timestamp', 'returns']].copy()
            df2 = data2[['timestamp', 'returns']].copy()
            
            # Rename columns to avoid conflicts
            df1.columns = ['timestamp', 'returns_1']
            df2.columns = ['timestamp', 'returns_2']
            
            # Merge on timestamp with inner join
            aligned = pd.merge(df1, df2, on='timestamp', how='inner')
            
            # Remove rows with NaN values
            aligned = aligned.dropna()
            
            return aligned
            
        except Exception as e:
            logger.error(f"❌ Time series alignment error: {e}")
            return pd.DataFrame()
    
    async def _calculate_symbol_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate high-frequency correlation between two symbols"""
        try:
            # Get high-frequency data (1-minute intervals for better correlation)
            data1 = await self._get_high_frequency_data(symbol1, limit=100)
            data2 = await self._get_high_frequency_data(symbol2, limit=100)
            
            if data1 is None or data2 is None or len(data1) < 50 or len(data2) < 50:
                logger.warning(f"⚠️ Insufficient data for correlation: {symbol1} vs {symbol2}")
                return 0.0
            
            # Align timestamps
            aligned_data = self._align_time_series(data1, data2)
            
            if len(aligned_data) < 30:
                logger.warning(f"⚠️ Insufficient aligned data for correlation: {symbol1} vs {symbol2}")
                return 0.0
            
            # Calculate returns
            returns1 = aligned_data[f'{symbol1}_returns']
            returns2 = aligned_data[f'{symbol2}_returns']
            
            # Calculate correlation
            correlation = returns1.corr(returns2)
            
            # Handle NaN values
            if pd.isna(correlation):
                return 0.0
            
            return abs(correlation)  # Return absolute correlation
            
        except Exception as e:
            logger.error(f"❌ Symbol correlation calculation error: {e}")
            return 0.0
    
    async def _calculate_real_time_correlation(self, symbol: str, existing_positions: List[Dict]) -> Dict[str, Any]:
        """Calculate real-time correlation with existing positions"""
        try:
            correlations = []
            max_correlation = 0.0
            most_correlated_symbol = None
            
            for position in existing_positions:
                position_symbol = position.get('symbol', '')
                if position_symbol and position_symbol != symbol:
                    correlation = await self._calculate_symbol_correlation(symbol, position_symbol)
                    correlations.append(correlation)
                    
                    if correlation > max_correlation:
                        max_correlation = correlation
                        most_correlated_symbol = position_symbol
            
            # Calculate average correlation
            avg_correlation = np.mean(correlations) if correlations else 0.0
            
            # Calculate correlation-weighted exposure
            total_correlated_exposure = 0.0
            for i, position in enumerate(existing_positions):
                if i < len(correlations):
                    position_value = position.get('size', 0) * position.get('entry_price', 0)
                    total_correlated_exposure += position_value * correlations[i]
            
            return {
                'max_correlation': max_correlation,
                'avg_correlation': avg_correlation,
                'correlated_symbol': most_correlated_symbol,
                'total_correlated_exposure': total_correlated_exposure,
                'correlation_count': len(correlations)
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time correlation calculation error: {e}")
            return {
                'max_correlation': 0.0,
                'avg_correlation': 0.0,
                'correlated_symbol': None,
                'total_correlated_exposure': 0.0,
                'correlation_count': 0
            }
    
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
            min_position_value = self.min_position_size
            if position_value < min_position_value:
                return {
                    'allowed': False,
                    'reason': f"Position too small: ${position_value:.2f} < ${min_position_value}"
                }
            
            # Check maximum position size
            max_position_value = self.max_position_size
            if position_value > max_position_value:
                return {
                    'allowed': True,
                    'max_allowed_size': max_position_value / price,
                    'reason': f"Position capped at ${max_position_value}"
                }
            
            # Check portfolio percentage
            portfolio_pct = position_value / account_balance
            max_portfolio_pct = self.max_position_risk
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
            
            if correlation_check['max_correlation'] > self.correlation_threshold: # Changed from self.correlation_limit
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
        """Get real price history for symbol"""
        try:
            # Try to get from exchange manager first
            if self.exchange_manager:
                data = await self.exchange_manager.get_historical_data(
                    symbol=symbol,
                    timeframe='1h',
                    limit=days * 24  # 24 hours per day
                )
                
                if data is not None and len(data) > 0:
                    return data
            
            # Try to get from database as fallback
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # If no real data available, return None instead of mock data
            logger.warning(f"⚠️ No real price history available for {symbol}")
            return None
            
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
            daily_loss_pct = abs(daily_pnl) / self.account_balance if daily_pnl < 0 else 0 # Changed from self.portfolio_value
            
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
            base_risk = self.account_balance * self.percentage_amount # Changed from self.portfolio_value
            
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
            kelly_multiplier = min(1.0, kelly_optimal / self.percentage_amount) # Changed from self.default_risk_per_trade
            
            # Final risk amount
            risk_amount = base_risk * confidence_multiplier * strategy_multiplier * kelly_multiplier
            
            # Apply limits
            max_risk = self.account_balance * self.max_portfolio_risk
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
            return self.percentage_amount # Changed from self.default_risk_per_trade
    
    async def update_portfolio_value(self, new_value: float) -> None:
        """Portfolio değerini güncelle"""
        try:
            self.account_balance = max(1000, new_value)  # Minimum $1000 # Changed from self.portfolio_value
            logger.debug(f"💰 Portfolio value updated: ${self.account_balance:,.2f}") # Changed from self.portfolio_value
            
        except Exception as e:
            logger.error(f"❌ Portfolio value update error: {e}")
    
    async def update_position_count(self, count: int) -> None:
        """Açık pozisyon sayısını güncelle"""
        try:
            # This method is not directly related to position_size calculation,
            # but keeping it for consistency if it's used elsewhere.
            # self.open_positions_count = max(0, count) # This line was removed from __init__
            logger.debug(f"📊 Open positions count: {count}") # This line was removed from __init__
            
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
                'portfolio_value': self.account_balance, # Changed from self.portfolio_value
                'max_portfolio_risk': self.max_portfolio_risk,
                'max_daily_loss': self.max_daily_loss,
                'max_open_positions': self.max_open_positions,
                'current_open_positions': 0, # This line was removed from __init__
                'correlation_limit': self.correlation_threshold, # Use correlation_threshold from config
                'kelly_fraction': self.kelly_fraction,
                'win_rate': self.win_rate,
                'avg_win_loss_ratio': self.avg_win_loss_ratio,
                'default_risk_per_trade': self.percentage_amount # Changed from self.default_risk_per_trade
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
            return self.percentage_amount * 0.5 # Changed from self.default_risk_per_trade
    
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
            return self.account_balance
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
            funding_rate = market_data.get('funding_rate', self.base_funding_rate)
            
            # Calculate dynamic slippage based on market conditions
            base_slippage = self.base_slippage
            volatility_mult = self.volatility_multiplier
            volume_mult = self.volume_multiplier
            
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
        """Get real-time market data for cost calculations from exchange APIs"""
        try:
            # Get real-time data from exchange
            real_data = await self._fetch_real_time_exchange_data(symbol, exchange)
            
            if real_data:
                return {
                    'volume': real_data.get('volume', 1000000),
                    'volatility': real_data.get('volatility', 0.5),
                    'funding_rate': real_data.get('funding_rate', 0.0001),
                    'bid_ask_spread': real_data.get('bid_ask_spread', 0.0005),
                    'order_book_depth': real_data.get('order_book_depth', {}),
                    'last_price': real_data.get('last_price', 0),
                    'timestamp': real_data.get('timestamp', datetime.now())
                }
            else:
                # Fallback to calculated values
                return await self._calculate_fallback_market_data(symbol, exchange)
                
        except Exception as e:
            logger.error(f"❌ Real-time market data error: {e}")
            return await self._calculate_fallback_market_data(symbol, exchange)
    
    async def _fetch_real_time_exchange_data(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time data from exchange APIs with actual order book and funding data"""
        try:
            # Get real exchange instance
            exchange_instance = await self._get_exchange_instance(exchange)
            if not exchange_instance:
                return await self._get_simulated_real_time_data(symbol, exchange)
            
            # Fetch real-time order book
            order_book = await self._fetch_real_order_book(exchange_instance, symbol)
            
            # Fetch real-time funding rate
            funding_rate = await self._fetch_real_funding_rate(exchange_instance, symbol)
            
            # Fetch real-time ticker data
            ticker = await self._fetch_real_ticker(exchange_instance, symbol)
            
            # Calculate real-time slippage from order book
            slippage = await self._calculate_real_slippage(order_book, ticker)
            
            # Calculate real-time volatility
            volatility = await self._calculate_real_volatility(exchange_instance, symbol)
            
            return {
                'volume': ticker.get('quoteVolume', 1000000),
                'volatility': volatility,
                'funding_rate': funding_rate,
                'bid_ask_spread': slippage['bid_ask_spread'],
                'order_book_depth': order_book,
                'last_price': ticker.get('last', 50000),
                'timestamp': datetime.now(),
                'real_data': True,
                'slippage_estimate': slippage['slippage_estimate']
            }
            
        except Exception as e:
            logger.error(f"❌ Real-time exchange data fetch error: {e}")
            return await self._get_simulated_real_time_data(symbol, exchange)
    
    async def _get_exchange_instance(self, exchange_name: str):
        """Get CCXT exchange instance"""
        try:
            import ccxt
            
            # Exchange configuration
            exchange_configs = {
                'binance': {
                    'apiKey': os.getenv('BINANCE_API_KEY', ''),
                    'secret': os.getenv('BINANCE_SECRET', ''),
                    'sandbox': False,  # Use live trading
                    'enableRateLimit': True
                },
                'bybit': {
                    'apiKey': os.getenv('BYBIT_API_KEY', ''),
                    'secret': os.getenv('BYBIT_SECRET', ''),
                    'sandbox': False,  # Use live trading
                    'enableRateLimit': True
                },
                'okx': {
                    'apiKey': os.getenv('OKX_API_KEY', ''),
                    'secret': os.getenv('OKX_SECRET', ''),
                    'password': os.getenv('OKX_PASSPHRASE', ''),
                    'sandbox': False,  # Use live trading
                    'enableRateLimit': True
                }
            }
            
            config = exchange_configs.get(exchange_name, {})
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class(config)
            
            # Test connection
            await exchange.load_markets()
            return exchange
            
        except Exception as e:
            logger.error(f"❌ Exchange instance creation error: {e}")
            return None
    
    async def _fetch_real_order_book(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch real order book data"""
        try:
            order_book = await exchange.fetch_order_book(symbol, limit=20)
            
            return {
                'bids': order_book['bids'][:10],  # Top 10 bids
                'asks': order_book['asks'][:10],  # Top 10 asks
                'bid_volume': sum(bid[1] for bid in order_book['bids'][:10]),
                'ask_volume': sum(ask[1] for ask in order_book['asks'][:10]),
                'spread': order_book['asks'][0][0] - order_book['bids'][0][0] if order_book['asks'] and order_book['bids'] else 0,
                'timestamp': order_book.get('timestamp', datetime.now().timestamp())
            }
            
        except Exception as e:
            logger.error(f"❌ Order book fetch error: {e}")
            return {
                'bids': [],
                'asks': [],
                'bid_volume': 0,
                'ask_volume': 0,
                'spread': 0,
                'timestamp': datetime.now().timestamp()
            }
    
    async def _fetch_real_funding_rate(self, exchange, symbol: str) -> float:
        """Fetch real funding rate"""
        try:
            # Try to get funding rate for perpetual futures
            if hasattr(exchange, 'fetch_funding_rate'):
                funding_info = await exchange.fetch_funding_rate(symbol)
                return funding_info.get('fundingRate', 0.0001)
            else:
                # For spot exchanges, return default
                return 0.0001
                
        except Exception as e:
            logger.error(f"❌ Funding rate fetch error: {e}")
            return 0.0001
    
    async def _fetch_real_ticker(self, exchange, symbol: str) -> Dict[str, Any]:
        """Fetch real ticker data"""
        try:
            ticker = await exchange.fetch_ticker(symbol)
            
            return {
                'last': ticker.get('last', 0),
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'volume': ticker.get('baseVolume', 0),
                'quoteVolume': ticker.get('quoteVolume', 0),
                'change': ticker.get('change', 0),
                'percentage': ticker.get('percentage', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Ticker fetch error: {e}")
            return {
                'last': 50000,
                'bid': 49900,
                'ask': 50100,
                'volume': 1000000,
                'quoteVolume': 1000000,
                'change': 0,
                'percentage': 0
            }
    
    async def _calculate_real_slippage(self, order_book: Dict[str, Any], ticker: Dict[str, Any]) -> Dict[str, float]:
        """Calculate real slippage from order book"""
        try:
            if not order_book['bids'] or not order_book['asks']:
                return {'bid_ask_spread': 0.0005, 'slippage_estimate': 0.0005}
            
            # Calculate bid-ask spread
            best_bid = order_book['bids'][0][0]
            best_ask = order_book['asks'][0][0]
            mid_price = (best_bid + best_ask) / 2
            bid_ask_spread = (best_ask - best_bid) / mid_price
            
            # Calculate slippage for different order sizes
            slippage_estimates = {}
            
            # Small order (0.1% of total volume)
            small_order_size = min(order_book['bid_volume'], order_book['ask_volume']) * 0.001
            small_slippage = self._calculate_slippage_for_size(order_book, small_order_size, mid_price)
            slippage_estimates['small'] = small_slippage
            
            # Medium order (1% of total volume)
            medium_order_size = min(order_book['bid_volume'], order_book['ask_volume']) * 0.01
            medium_slippage = self._calculate_slippage_for_size(order_book, medium_order_size, mid_price)
            slippage_estimates['medium'] = medium_slippage
            
            # Large order (5% of total volume)
            large_order_size = min(order_book['bid_volume'], order_book['ask_volume']) * 0.05
            large_slippage = self._calculate_slippage_for_size(order_book, large_order_size, mid_price)
            slippage_estimates['large'] = large_slippage
            
            return {
                'bid_ask_spread': bid_ask_spread,
                'slippage_estimate': slippage_estimates['medium'],  # Default to medium
                'slippage_by_size': slippage_estimates
            }
            
        except Exception as e:
            logger.error(f"❌ Real slippage calculation error: {e}")
            return {'bid_ask_spread': 0.0005, 'slippage_estimate': 0.0005}
    
    def _calculate_slippage_for_size(self, order_book: Dict[str, Any], order_size: float, mid_price: float) -> float:
        """Calculate slippage for specific order size"""
        try:
            if order_size <= 0 or mid_price <= 0:
                return 0.0005
            
            # Calculate weighted average price for buy order
            total_cost = 0
            remaining_size = order_size
            
            for ask_price, ask_size in order_book['asks']:
                if remaining_size <= 0:
                    break
                fill_size = min(remaining_size, ask_size)
                total_cost += fill_size * ask_price
                remaining_size -= fill_size
            
            if remaining_size > 0:
                # Not enough liquidity, estimate higher slippage
                return 0.01  # 1% slippage
            
            weighted_avg_price = total_cost / order_size
            slippage = (weighted_avg_price - mid_price) / mid_price
            
            return max(slippage, 0.0001)  # Minimum 0.01% slippage
            
        except Exception as e:
            logger.error(f"❌ Slippage calculation error: {e}")
            return 0.0005
    
    async def _calculate_real_volatility(self, exchange, symbol: str) -> float:
        """Calculate real volatility from recent price data"""
        try:
            # Fetch recent OHLCV data
            ohlcv = await exchange.fetch_ohlcv(symbol, '1h', limit=24)
            
            if not ohlcv or len(ohlcv) < 12:
                return 0.5
            
            # Calculate returns
            closes = [candle[4] for candle in ohlcv]
            returns = []
            for i in range(1, len(closes)):
                if closes[i-1] > 0:
                    returns.append((closes[i] - closes[i-1]) / closes[i-1])
            
            if not returns:
                return 0.5
            
            # Calculate volatility (annualized)
            volatility = np.std(returns) * np.sqrt(24 * 365)
            return min(volatility, 1.0)
            
        except Exception as e:
            logger.error(f"❌ Real volatility calculation error: {e}")
            return 0.5
    
    async def _get_real_time_market_data(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Get real-time market data from exchange APIs - NO SIMULATION"""
        try:
            # Try to get real exchange data first
            exchange_instance = await self._get_exchange_instance(exchange)
            if exchange_instance:
                # Get real order book
                order_book = await self._fetch_real_order_book(exchange_instance, symbol)
                
                # Get real funding rate
                funding_rate = await self._fetch_real_funding_rate(exchange_instance, symbol)
                
                # Get real ticker data
                ticker = await self._fetch_real_ticker(exchange_instance, symbol)
                
                # Calculate real slippage
                slippage = await self._calculate_real_slippage(order_book, ticker)
                
                # Calculate real volatility
                volatility = await self._calculate_real_volatility(exchange_instance, symbol)
                
                return {
                    'volume': ticker.get('quoteVolume', 1000000),
                    'volatility': volatility,
                    'funding_rate': funding_rate,
                    'bid_ask_spread': slippage['bid_ask_spread'],
                    'order_book_depth': order_book,
                    'last_price': ticker.get('last', 50000),
                    'timestamp': datetime.now(),
                    'real_data': True,
                    'slippage_estimate': slippage['slippage_estimate']
                }
            
            # If exchange instance not available, use fallback
            return await self._get_fallback_market_data(symbol, exchange)
            
        except Exception as e:
            logger.error(f"❌ Real-time market data error: {e}")
            return await self._get_fallback_market_data(symbol, exchange)