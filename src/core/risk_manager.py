"""
Risk Manager
Gelişmiş risk yönetimi ve pozisyon boyutlandırma
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import asyncio


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
self.max_open_positions = risk_config.get('max_open_positions', 10)
self.position_sizing_method = risk_config.get('position_sizing_method', 'kelly_criterion')
self.correlation_limit = risk_config.get('correlation_limit', 0.7)

# Leverage settings
self.leverage_config = risk_config.get('leverage', {})
self.max_leverage = self.leverage_config.get('max_leverage', 3)
self.default_leverage = self.leverage_config.get('default_leverage', 1)
self.high_confidence_leverage = self.leverage_config.get('high_confidence_leverage', 2)

# Internal state
self.daily_pnl = 0.0
self.portfolio_value = 100000.0  # Default başlangıç değeri
self.open_positions_count = 0

async def calculate_position_size(self, symbol: str, entry_price: float,
stop_loss: float, confidence: float,
strategy: str) -> Dict[str, Any]:
"""Pozisyon boyutunu hesapla"""
try:
# Portfolio değerini güncelle
await self._update_portfolio_value()

# Risk kontrollerini yap
risk_checks = await self._perform_risk_checks(symbol, strategy)

if not risk_checks['allowed']:
return {
'size': 0,
'leverage': 1,
'risk_amount': 0,
'reason': risk_checks['reason']
}

# Risk miktarını hesapla
risk_amount = await self._calculate_risk_amount(confidence, strategy)

# Pozisyon boyutunu hesapla
position_size = await self._calculate_size_by_method(
risk_amount, entry_price, stop_loss, confidence
)

# Leverage hesapla
leverage = await self._calculate_leverage(confidence, strategy)

# Final size with leverage
final_size = position_size * leverage

# Minimum/Maximum size kontrolü
final_size = await self._apply_size_limits(symbol, final_size)

result = {
'size': final_size,
'leverage': leverage,
'risk_amount': risk_amount,
'position_value': final_size * entry_price,
'risk_percentage': (risk_amount / self.portfolio_value) * 100,
'allowed': True,
'method': self.position_sizing_method
}

logger.info(f"💰 {symbol} Pozisyon boyutu: {final_size:.6f}, Risk: {risk_amount:.2f} USDT")

return result

except Exception as e:
logger.error(f"❌ {symbol} pozisyon boyutu hesaplama hatası: {e}")
return {
'size': 0,
'leverage': 1,
'risk_amount': 0,
'allowed': False,
'reason': f"Calculation error: {e}"
}

async def _perform_risk_checks(self, symbol: str, strategy: str) -> Dict[str, Any]:
"""Risk kontrollerini gerçekleştir"""
try:
# Günlük kayıp kontrolü
if abs(self.daily_pnl) >= self.max_daily_loss * self.portfolio_value:
return {
'allowed': False,
'reason': f"Daily loss limit exceeded: {abs(self.daily_pnl):.2f}"
}

# Maksimum pozisyon sayısı kontrolü
if self.open_positions_count >= self.max_open_positions:
return {
'allowed': False,
'reason': f"Maximum open positions limit reached: {self.open_positions_count}"
}

# Correlation kontrolü
correlation_check = await self._check_correlation(symbol)
if not correlation_check['allowed']:
return correlation_check

# Market hours kontrolü (opsiyonel)
market_hours_check = await self._check_market_conditions()
if not market_hours_check['allowed']:
return market_hours_check

return {'allowed': True, 'reason': 'All checks passed'}

except Exception as e:
logger.error(f"❌ Risk kontrol hatası: {e}")
return {'allowed': False, 'reason': f"Risk check error: {e}"}

async def _calculate_risk_amount(self, confidence: float, strategy: str) -> float:
"""Risk miktarını hesapla"""
try:
# Base risk amount
base_risk = self.max_portfolio_risk * self.portfolio_value

# Confidence adjustment
confidence_multiplier = min(2.0, max(0.5, confidence * 1.5))

# Strategy-specific adjustment
strategy_multipliers = {
'scalping': 0.5,      # Lower risk for high frequency
'swing_trading': 1.0,  # Normal risk
'trend_following': 1.2, # Slightly higher for long-term
'mean_reversion': 0.8   # Conservative
}

strategy_multiplier = strategy_multipliers.get(strategy, 1.0)

# Final risk amount
risk_amount = base_risk * confidence_multiplier * strategy_multiplier

# Ensure we don't exceed maximum
max_risk = self.max_portfolio_risk * self.portfolio_value
risk_amount = min(risk_amount, max_risk)

return risk_amount

except Exception as e:
logger.error(f"❌ Risk miktarı hesaplama hatası: {e}")
return self.max_portfolio_risk * self.portfolio_value * 0.5

async def _calculate_size_by_method(self, risk_amount: float, entry_price: float,
stop_loss: float, confidence: float) -> float:
"""Seçilen metoda göre pozisyon boyutunu hesapla"""
try:
if self.position_sizing_method == 'kelly_criterion':
return await self._kelly_criterion_sizing(risk_amount, entry_price, stop_loss, confidence)
elif self.position_sizing_method == 'fixed_risk':
return await self._fixed_risk_sizing(risk_amount, entry_price, stop_loss)
elif self.position_sizing_method == 'volatility_adjusted':
return await self._volatility_adjusted_sizing(risk_amount, entry_price, stop_loss)
else:
# Default to fixed risk
return await self._fixed_risk_sizing(risk_amount, entry_price, stop_loss)

except Exception as e:
logger.error(f"❌ Pozisyon boyutu hesaplama hatası: {e}")
return 0.0

async def _kelly_criterion_sizing(self, risk_amount: float, entry_price: float,
stop_loss: float, confidence: float) -> float:
"""Kelly Criterion ile pozisyon boyutlandırma"""
try:
# Kelly formula: f = (bp - q) / b
# f = fraction of capital to wager
# b = odds received on the wager (reward/risk ratio)
# p = probability of winning
# q = probability of losing (1 - p)

# Risk per unit
risk_per_unit = abs(entry_price - stop_loss)

if risk_per_unit == 0:
return 0.0

# Expected reward/risk ratio (assumed based on strategy)
reward_risk_ratio = 2.0  # Default 2:1 RR

# Win probability based on confidence
win_probability = confidence
lose_probability = 1 - win_probability

# Kelly percentage
kelly_percentage = (reward_risk_ratio * win_probability - lose_probability) / reward_risk_ratio

# Apply Kelly fraction (usually use 25% of Kelly to be conservative)
kelly_fraction = max(0, min(0.25, kelly_percentage * 0.25))

# Calculate position size
position_value = self.portfolio_value * kelly_fraction
position_size = position_value / entry_price

# Ensure we don't exceed risk limit
max_size_by_risk = risk_amount / risk_per_unit
position_size = min(position_size, max_size_by_risk)

return position_size

except Exception as e:
logger.error(f"❌ Kelly Criterion hesaplama hatası: {e}")
return 0.0

async def _fixed_risk_sizing(self, risk_amount: float, entry_price: float, stop_loss: float) -> float:
"""Sabit risk ile pozisyon boyutlandırma"""
try:
risk_per_unit = abs(entry_price - stop_loss)

if risk_per_unit == 0:
return 0.0

position_size = risk_amount / risk_per_unit
return position_size

except Exception as e:
logger.error(f"❌ Fixed risk hesaplama hatası: {e}")
return 0.0

async def _volatility_adjusted_sizing(self, risk_amount: float, entry_price: float, stop_loss: float) -> float:
"""Volatilite ayarlı pozisyon boyutlandırma"""
try:
# Bu implementasyon historical volatility gerektirir
# Şimdilik fixed risk kullanıyoruz
return await self._fixed_risk_sizing(risk_amount, entry_price, stop_loss)

except Exception as e:
logger.error(f"❌ Volatility adjusted hesaplama hatası: {e}")
return 0.0

async def _calculate_leverage(self, confidence: float, strategy: str) -> int:
"""Leverage hesapla"""
try:
# Base leverage
base_leverage = self.default_leverage

# High confidence bonus
if confidence > 0.8:
base_leverage = self.high_confidence_leverage

# Strategy-specific adjustments
strategy_leverage = {
'scalping': min(self.max_leverage, base_leverage + 1),  # Higher for scalping
'swing_trading': base_leverage,
'trend_following': base_leverage,
'mean_reversion': max(1, base_leverage - 1)  # Lower for mean reversion
}

leverage = strategy_leverage.get(strategy, base_leverage)

# Ensure within limits
leverage = max(1, min(self.max_leverage, leverage))

return int(leverage)

except Exception as e:
logger.error(f"❌ Leverage hesaplama hatası: {e}")
return 1

async def _check_correlation(self, symbol: str) -> Dict[str, Any]:
"""Gerçek correlation kontrolü"""
try:
current_positions = await self.db_manager.get_positions(status='OPEN')

if not current_positions:
return {'allowed': True, 'reason': 'No existing positions'}

# Aynı base currency kontrolü
base_currency = symbol.split('/')[0]
same_base_count = sum(1 for pos in current_positions if pos['symbol'].startswith(base_currency))

if same_base_count >= 3:
return {
'allowed': False,
'reason': f"Too many positions with {base_currency}: {same_base_count}"
}

# Gerçek correlation hesaplama
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
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Get historical data for the new symbol
new_symbol_data = await self._get_price_history(symbol, days=30)

if new_symbol_data is None or len(new_symbol_data) < 20:
return {'max_correlation': 0.0, 'correlated_symbol': None}

max_correlation = 0.0
correlated_symbol = None

# Check correlation with each existing position
for position in current_positions:
existing_symbol = position['symbol']
existing_data = await self._get_price_history(existing_symbol, days=30)

if existing_data is None or len(existing_data) < 20:
continue

# Align data by timestamp
correlation = self._compute_correlation(new_symbol_data, existing_data)

if abs(correlation) > abs(max_correlation):
max_correlation = correlation
correlated_symbol = existing_symbol

return {
'max_correlation': abs(max_correlation),
'correlated_symbol': correlated_symbol
}

except Exception as e:
logger.error(f"❌ Price correlation hesaplama hatası: {e}")
return {'max_correlation': 0.0, 'correlated_symbol': None}

async def _get_price_history(self, symbol: str, days: int = 30) -> Optional[pd.DataFrame]:
"""Sembol için fiyat geçmişi al"""
try:
# Try database first
market_data = await self.db_manager.get_market_data(
symbol=symbol,
exchange='binance',  # Default exchange
timeframe='1h',
limit=days * 24
)

if not market_data.empty and len(market_data) >= 20:
return market_data[['timestamp', 'close']].copy()

# Fallback to yfinance for crypto data
import yfinance as yf

# Convert symbol format
yf_symbol = symbol.replace('USDT', '-USD').replace('/', '-')

ticker = yf.Ticker(yf_symbol)
data = ticker.history(period=f"{days}d", interval="1h")

if data.empty:
return None

df = pd.DataFrame({
'timestamp': data.index,
'close': data['Close'].values
})

return df

except Exception as e:
logger.error(f"❌ {symbol} fiyat geçmişi alınamadı: {e}")
return None

def _compute_correlation(self, data1: pd.DataFrame, data2: pd.DataFrame) -> float:
"""İki fiyat serisi arasında korelasyon hesapla"""
try:
# Merge on timestamp
merged = pd.merge(data1, data2, on='timestamp', suffixes=('_1', '_2'))

if len(merged) < 10:
return 0.0

# Calculate returns
merged['return_1'] = merged['close_1'].pct_change()
merged['return_2'] = merged['close_2'].pct_change()

# Remove NaN values
merged = merged.dropna()

if len(merged) < 10:
return 0.0

# Calculate correlation
correlation = merged['return_1'].corr(merged['return_2'])

return correlation if not pd.isna(correlation) else 0.0

except Exception as e:
logger.error(f"❌ Korelasyon hesaplama hatası: {e}")
return 0.0

async def _check_market_conditions(self) -> Dict[str, Any]:
"""Market koşulları kontrolü"""
try:
# Basit market hours kontrolü
# Crypto 24/7 olduğu için şimdilik her zaman allowed

return {'allowed': True, 'reason': 'Market conditions OK'}

except Exception as e:
logger.error(f"❌ Market koşulları kontrol hatası: {e}")
return {'allowed': True, 'reason': 'Market check skipped due to error'}

async def _apply_size_limits(self, symbol: str, size: float) -> float:
"""Boyut limitlerini uygula"""
try:
# Minimum ve maximum size kontrolü
min_size = 0.001  # Minimum position size
max_size = self.portfolio_value * 0.1 / 50000  # Assume average price 50k for max calc

size = max(min_size, min(size, max_size))

return size

except Exception as e:
logger.error(f"❌ Size limit uygulama hatası: {e}")
return size

async def _update_portfolio_value(self) -> None:
"""Portfolio değerini güncelle"""
try:
# Bu gerçek implementasyonda exchange'lerden balance alınacak
# Şimdilik static value kullanıyoruz

# Get current positions P&L
positions = await self.db_manager.get_positions(status='OPEN')
total_pnl = sum(pos.get('pnl', 0) for pos in positions)

# Update daily P&L
today = datetime.now().date()
daily_stats = await self.db_manager.get_performance_stats(days=1)
self.daily_pnl = daily_stats.get('total_pnl', 0)

# Update position count
self.open_positions_count = len(positions)

logger.debug(f"💼 Portfolio: {self.portfolio_value:.2f}, Daily PnL: {self.daily_pnl:.2f}, Positions: {self.open_positions_count}")

except Exception as e:
logger.error(f"❌ Portfolio güncelleme hatası: {e}")

async def update_position_pnl(self, position_id: int, current_pnl: float) -> None:
"""Pozisyon P&L'ini güncelle"""
try:
await self.db_manager.update_position(position_id, {
'pnl': current_pnl,
'pnl_percentage': (current_pnl / self.portfolio_value) * 100
})

except Exception as e:
logger.error(f"❌ Position PnL güncelleme hatası: {e}")

async def check_stop_loss(self, position: Dict[str, Any], current_price: float) -> bool:
"""Stop loss kontrolü"""
try:
stop_loss = position.get('stop_loss')
if not stop_loss:
return False

side = position.get('side', 'BUY')

if side == 'BUY' and current_price <= stop_loss:
return True
elif side == 'SELL' and current_price >= stop_loss:
return True

return False

except Exception as e:
logger.error(f"❌ Stop loss kontrol hatası: {e}")
return False

async def check_take_profit(self, position: Dict[str, Any], current_price: float) -> bool:
"""Take profit kontrolü"""
try:
take_profit = position.get('take_profit')
if not take_profit:
return False

side = position.get('side', 'BUY')

if side == 'BUY' and current_price >= take_profit:
return True
elif side == 'SELL' and current_price <= take_profit:
return True

return False

except Exception as e:
logger.error(f"❌ Take profit kontrol hatası: {e}")
return False

def get_max_daily_loss(self) -> float:
"""Maksimum günlük kayıp limitini döndür"""
return self.max_daily_loss * self.portfolio_value

def get_current_daily_pnl(self) -> float:
"""Mevcut günlük P&L'i döndür"""
return self.daily_pnl

def is_daily_loss_limit_reached(self) -> bool:
"""Günlük kayıp limitine ulaşılıp ulaşılmadığını kontrol et"""
return abs(self.daily_pnl) >= self.get_max_daily_loss()