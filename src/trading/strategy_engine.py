"""
Strategy Engine
Multi-strateji trading motoru
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio


class StrategyEngine:
    """Strateji motoru - tüm trading stratejilerini yönetir"""
    
    def __init__(self, strategies_config: Dict[str, Any], signal_filter, market_analyzer, confidence_calculator):
        """
        Args:
            strategies_config: Strateji konfigürasyonları
            signal_filter: AI sinyal filtreleme sistemi
            market_analyzer: Market analizöru
            confidence_calculator: Güven faktörü hesaplayıcısı
        """
        self.config = strategies_config
        self.signal_filter = signal_filter
        self.market_analyzer = market_analyzer
        self.confidence_calculator = confidence_calculator
        
        # Strategy configurations
        self.scalping_config = strategies_config.get('scalping', {})
        self.swing_config = strategies_config.get('swing_trading', {})
        self.trend_config = strategies_config.get('trend_following', {})
        self.mean_reversion_config = strategies_config.get('mean_reversion', {})
        
        # Active strategies
        self.active_strategies = []
        self._load_active_strategies()
        
    def _load_active_strategies(self) -> None:
        """Aktif stratejileri yükle"""
        self.active_strategies = []
        
        for strategy_name, config in self.config.items():
            if config.get('enabled', False):
                self.active_strategies.append(strategy_name)
        
        logger.info(f"🎯 Aktif stratejiler: {self.active_strategies}")
    
    async def select_strategy(self, symbol: str, market_condition: Dict[str, Any], 
                            confidence: float) -> Optional[str]:
        """Piyasa koşullarına göre en uygun stratejiyi seç"""
        try:
            market_cond = market_condition.get('condition', 'sideways_market')
            volatility = market_condition.get('volatility', 'normal')
            strength = market_condition.get('strength', 0.5)
            
            # Market condition'a göre önerilen stratejiler
            recommended_strategies = market_condition.get('recommended_strategies', [])
            
            # Aktif ve önerilen stratejilerin kesişimi
            suitable_strategies = [s for s in self.active_strategies if s in recommended_strategies]
            
            if not suitable_strategies:
                # Fallback: en az bir aktif strateji kullan
                suitable_strategies = self.active_strategies
            
            if not suitable_strategies:
                return None
            
            # Strateji skorlarını hesapla
            strategy_scores = {}
            
            for strategy in suitable_strategies:
                score = await self._calculate_strategy_score(
                    strategy, symbol, market_condition, confidence
                )
                strategy_scores[strategy] = score
            
            # En yüksek skorlu stratejiyi seç
            if strategy_scores:
                best_strategy = max(strategy_scores, key=strategy_scores.get)
                best_score = strategy_scores[best_strategy]
                
                # Minimum skor kontrolü
                if best_score > 0.5:
                    logger.debug(f"🎯 {symbol} için seçilen strateji: {best_strategy} (skor: {best_score:.3f})")
                    return best_strategy
            
            return None
            
        except Exception as e:
            logger.error(f"❌ {symbol} strateji seçim hatası: {e}")
            return None
    
    async def _calculate_strategy_score(self, strategy: str, symbol: str, 
                                      market_condition: Dict[str, Any], confidence: float) -> float:
        """Strateji için uygunluk skoru hesapla"""
        try:
            base_score = 0.5
            
            market_cond = market_condition.get('condition', 'sideways_market')
            volatility = market_condition.get('volatility', 'normal')
            strength = market_condition.get('strength', 0.5)
            
            # Strateji-specific scoring
            if strategy == 'scalping':
                # Scalping yüksek volatilite sever
                if volatility in ['high', 'elevated']:
                    base_score += 0.3
                if confidence > 0.8:
                    base_score += 0.2
                # Düşük volatilitede düşük skor
                if volatility == 'low':
                    base_score -= 0.3
                    
            elif strategy == 'swing_trading':
                # Swing trading trending markets sever
                if market_cond in ['bull_market', 'bear_market']:
                    base_score += 0.3
                if 0.3 < strength < 0.8:  # Moderate strength
                    base_score += 0.2
                if volatility == 'normal':
                    base_score += 0.1
                    
            elif strategy == 'trend_following':
                # Trend following güçlü trendleri sever
                if strength > 0.6:
                    base_score += 0.4
                if market_cond in ['bull_market', 'bear_market']:
                    base_score += 0.2
                if volatility in ['normal', 'elevated']:
                    base_score += 0.1
                    
            elif strategy == 'mean_reversion':
                # Mean reversion sideways markets sever
                if market_cond == 'sideways_market':
                    base_score += 0.3
                if volatility in ['high', 'elevated']:
                    base_score += 0.2
                if strength < 0.4:  # Weak trends
                    base_score += 0.2
            
            # Confidence bonus
            base_score += (confidence - 0.5) * 0.2
            
            # Strategy availability check
            strategy_config = self.config.get(strategy, {})
            if not strategy_config.get('enabled', False):
                base_score = 0
            
            return min(1.0, max(0.0, base_score))
            
        except Exception as e:
            logger.error(f"❌ {strategy} skor hesaplama hatası: {e}")
            return 0.0
    
    async def get_entry_signal(self, symbol: str, market_data: Dict[str, Any], 
                             signals: Dict[str, Any], strategy: str) -> Optional[Dict[str, Any]]:
        """Entry sinyali üret"""
        try:
            strategy_config = self.config.get(strategy, {})
            if not strategy_config.get('enabled', False):
                return None
            
            # Strateji-specific entry logic
            if strategy == 'scalping':
                return await self._scalping_entry(symbol, market_data, signals, strategy_config)
            elif strategy == 'swing_trading':
                return await self._swing_entry(symbol, market_data, signals, strategy_config)
            elif strategy == 'trend_following':
                return await self._trend_entry(symbol, market_data, signals, strategy_config)
            elif strategy == 'mean_reversion':
                return await self._mean_reversion_entry(symbol, market_data, signals, strategy_config)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ {symbol} {strategy} entry signal hatası: {e}")
            return None
    
    async def get_exit_signal(self, symbol: str, market_data: Dict[str, Any], 
                            signals: Dict[str, Any], position: Dict[str, Any], 
                            strategy: str) -> Optional[Dict[str, Any]]:
        """Exit sinyali üret"""
        try:
            strategy_config = self.config.get(strategy, {})
            
            # Temel exit koşulları
            current_price = market_data.get('close', 0)
            entry_price = position.get('entry_price', 0)
            side = position.get('side', 'BUY')
            
            # P&L hesapla
            if side == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            # Stop loss / Take profit kontrolü
            profit_target = strategy_config.get('profit_target', 2.0)
            stop_loss = strategy_config.get('stop_loss', 1.0)
            
            if pnl_pct >= profit_target:
                return {
                    'signal': 'CLOSE',
                    'reason': 'TAKE_PROFIT',
                    'pnl_pct': pnl_pct,
                    'price': current_price
                }
            
            if pnl_pct <= -stop_loss:
                return {
                    'signal': 'CLOSE',
                    'reason': 'STOP_LOSS',
                    'pnl_pct': pnl_pct,
                    'price': current_price
                }
            
            # Zaman bazlı exit
            max_position_time = strategy_config.get('max_position_time', 60)  # minutes
            opened_at = position.get('opened_at')
            if opened_at:
                if isinstance(opened_at, str):
                    opened_at = datetime.fromisoformat(opened_at.replace('Z', '+00:00'))
                
                position_age = (datetime.now() - opened_at).total_seconds() / 60
                
                if position_age > max_position_time:
                    return {
                        'signal': 'CLOSE',
                        'reason': 'TIME_LIMIT',
                        'pnl_pct': pnl_pct,
                        'price': current_price
                    }
            
            # Strateji-specific exit logic
            strategy_exit = await self._get_strategy_exit(
                symbol, market_data, signals, position, strategy, strategy_config
            )
            
            if strategy_exit:
                return strategy_exit
            
            return None
            
        except Exception as e:
            logger.error(f"❌ {symbol} {strategy} exit signal hatası: {e}")
            return None
    
    async def _scalping_entry(self, symbol: str, market_data: Dict[str, Any], 
                            signals: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Scalping entry logic"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 10:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Hızlı RSI check
            try:
                rsi = latest.get('rsi', 50)
                volume_ratio = latest['volume'] / df['volume'].rolling(10).mean().iloc[-1]
                
                # Scalping conditions
                high_volume = volume_ratio > 1.5
                momentum_shift = False
                
                # Simple momentum detection
                if latest['close'] > prev['close'] * 1.002 and high_volume:  # 0.2% move up
                    momentum_shift = True
                    signal_type = 'BUY'
                elif latest['close'] < prev['close'] * 0.998 and high_volume:  # 0.2% move down
                    momentum_shift = True
                    signal_type = 'SELL'
                
                if momentum_shift:
                    return {
                        'signal': signal_type,
                        'entry_price': latest['close'],
                        'stop_loss': latest['close'] * (0.997 if signal_type == 'BUY' else 1.003),
                        'take_profit': latest['close'] * (1.005 if signal_type == 'BUY' else 0.995),
                        'confidence': 0.8 if high_volume else 0.6,
                        'timeframe': '1m'
                    }
                    
            except Exception as e:
                logger.warning(f"⚠️ Scalping hesaplama hatası: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Scalping entry hatası: {e}")
            return None
    
    async def _swing_entry(self, symbol: str, market_data: Dict[str, Any], 
                         signals: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Swing trading entry logic"""
        try:
            # Signal analysis'ten gelen sinyalleri değerlendir
            combined_signals = signals.get('signals', [])
            
            buy_signals = [s for s in combined_signals if s.get('type') == 'BUY']
            sell_signals = [s for s in combined_signals if s.get('type') == 'SELL']
            
            signal_confidence = signals.get('confidence', 0)
            min_confidence = config.get('confidence_threshold', 0.7)
            
            if signal_confidence < min_confidence:
                return None
            
            df = market_data.get('dataframe')
            if df is None or len(df) < 50:
                return None
            
            latest = df.iloc[-1]
            
            # Trend confirmation
            ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
            ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
            
            if len(buy_signals) > len(sell_signals) and latest['close'] > ema_21 > ema_50:
                # Bullish swing setup
                stop_loss_pct = config.get('stop_loss', 1.5) / 100
                profit_target_pct = config.get('profit_target', 3.0) / 100
                
                return {
                    'signal': 'BUY',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 - stop_loss_pct),
                    'take_profit': latest['close'] * (1 + profit_target_pct),
                    'confidence': signal_confidence,
                    'timeframe': '1h'
                }
                
            elif len(sell_signals) > len(buy_signals) and latest['close'] < ema_21 < ema_50:
                # Bearish swing setup
                stop_loss_pct = config.get('stop_loss', 1.5) / 100
                profit_target_pct = config.get('profit_target', 3.0) / 100
                
                return {
                    'signal': 'SELL',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 + stop_loss_pct),
                    'take_profit': latest['close'] * (1 - profit_target_pct),
                    'confidence': signal_confidence,
                    'timeframe': '1h'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Swing entry hatası: {e}")
            return None
    
    async def _trend_entry(self, symbol: str, market_data: Dict[str, Any], 
                         signals: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Trend following entry logic"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 200:
                return None
            
            latest = df.iloc[-1]
            
            # Multi-timeframe trend confirmation
            ema_9 = df['close'].ewm(span=9).mean().iloc[-1]
            ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
            ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
            ema_200 = df['close'].ewm(span=200).mean().iloc[-1]
            
            # Strong uptrend
            if (latest['close'] > ema_9 > ema_21 > ema_50 > ema_200 and
                signals.get('confidence', 0) >= config.get('confidence_threshold', 0.75)):
                
                stop_loss_pct = config.get('stop_loss', 4.0) / 100
                profit_target_pct = config.get('profit_target', 8.0) / 100
                
                return {
                    'signal': 'BUY',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 - stop_loss_pct),
                    'take_profit': latest['close'] * (1 + profit_target_pct),
                    'confidence': signals.get('confidence', 0),
                    'timeframe': '4h'
                }
                
            # Strong downtrend
            elif (latest['close'] < ema_9 < ema_21 < ema_50 < ema_200 and
                  signals.get('confidence', 0) >= config.get('confidence_threshold', 0.75)):
                
                stop_loss_pct = config.get('stop_loss', 4.0) / 100
                profit_target_pct = config.get('profit_target', 8.0) / 100
                
                return {
                    'signal': 'SELL',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 + stop_loss_pct),
                    'take_profit': latest['close'] * (1 - profit_target_pct),
                    'confidence': signals.get('confidence', 0),
                    'timeframe': '4h'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Trend entry hatası: {e}")
            return None
    
    async def _mean_reversion_entry(self, symbol: str, market_data: Dict[str, Any], 
                                  signals: Dict[str, Any], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Mean reversion entry logic"""
        try:
            df = market_data.get('dataframe')
            if df is None or len(df) < 50:
                return None
            
            latest = df.iloc[-1]
            
            # Bollinger Bands mean reversion
            bb_period = 20
            bb_std = 2
            
            sma_20 = df['close'].rolling(bb_period).mean().iloc[-1]
            bb_upper = sma_20 + (df['close'].rolling(bb_period).std().iloc[-1] * bb_std)
            bb_lower = sma_20 - (df['close'].rolling(bb_period).std().iloc[-1] * bb_std)
            
            # RSI oversold/overbought
            rsi_period = 14
            price_changes = df['close'].diff()
            gains = price_changes.where(price_changes > 0, 0).rolling(rsi_period).mean()
            losses = (-price_changes.where(price_changes < 0, 0)).rolling(rsi_period).mean()
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Mean reversion conditions
            oversold = latest['close'] < bb_lower and rsi < 30
            overbought = latest['close'] > bb_upper and rsi > 70
            
            if oversold and signals.get('confidence', 0) >= config.get('confidence_threshold', 0.65):
                stop_loss_pct = config.get('stop_loss', 1.0) / 100
                profit_target_pct = config.get('profit_target', 2.0) / 100
                
                return {
                    'signal': 'BUY',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 - stop_loss_pct),
                    'take_profit': sma_20,  # Target mean
                    'confidence': signals.get('confidence', 0),
                    'timeframe': '15m'
                }
                
            elif overbought and signals.get('confidence', 0) >= config.get('confidence_threshold', 0.65):
                stop_loss_pct = config.get('stop_loss', 1.0) / 100
                profit_target_pct = config.get('profit_target', 2.0) / 100
                
                return {
                    'signal': 'SELL',
                    'entry_price': latest['close'],
                    'stop_loss': latest['close'] * (1 + stop_loss_pct),
                    'take_profit': sma_20,  # Target mean
                    'confidence': signals.get('confidence', 0),
                    'timeframe': '15m'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Mean reversion entry hatası: {e}")
            return None
    
    async def _get_strategy_exit(self, symbol: str, market_data: Dict[str, Any], 
                               signals: Dict[str, Any], position: Dict[str, Any], 
                               strategy: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Strateji-specific exit logic"""
        try:
            # Strategy-specific exit conditions
            if strategy == 'scalping':
                # Scalping: quick exits on signal change
                combined_signals = signals.get('signals', [])
                
                position_side = position.get('side', 'BUY')
                opposing_signals = []
                
                if position_side == 'BUY':
                    opposing_signals = [s for s in combined_signals if s.get('type') == 'SELL']
                else:
                    opposing_signals = [s for s in combined_signals if s.get('type') == 'BUY']
                
                if len(opposing_signals) > 0 and signals.get('confidence', 0) > 0.7:
                    return {
                        'signal': 'CLOSE',
                        'reason': 'SIGNAL_REVERSAL',
                        'confidence': signals.get('confidence', 0),
                        'price': market_data.get('close', 0)
                    }
            
            # Additional strategy-specific exits can be added here
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Strategy exit hatası: {e}")
            return None
    
    def get_active_strategies(self) -> List[str]:
        """Aktif stratejileri döndür"""
        return self.active_strategies.copy()
    
    def is_strategy_enabled(self, strategy: str) -> bool:
        """Strateji aktif mi kontrol et"""
        return strategy in self.active_strategies
    
    async def backtest_strategy(self, strategy: str, symbol: str, 
                               historical_data: pd.DataFrame,
                               start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Strateji backtesting'i"""
        try:
            logger.info(f"🔄 {strategy} stratejisi için {symbol} backtesting başlatılıyor...")
            
            if len(historical_data) < 100:
                return {'error': 'Insufficient data for backtesting'}
            
            # Date filtering
            df = historical_data.copy()
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
            
            if len(df) < 50:
                return {'error': 'Insufficient data after date filtering'}
            
            # Initialize backtesting variables
            positions = []
            trades = []
            balance = 10000  # Starting balance
            current_position = None
            
            strategy_config = self.config.get(strategy, {})
            
            # Process each candle
            for i in range(50, len(df)):  # Start after enough data for indicators
                current_candle = df.iloc[i]
                historical_subset = df.iloc[max(0, i-200):i+1]  # Last 200 candles
                
                market_data = {
                    'dataframe': historical_subset,
                    'close': current_candle['close'],
                    'timestamp': current_candle['timestamp']
                }
                
                # Mock signals for backtesting
                signals = {
                    'signals': [{'type': 'BUY', 'strength': 0.7}] if i % 20 == 0 else [],
                    'confidence': 0.8 if i % 20 == 0 else 0.3
                }
                
                # Check for entry signals
                if current_position is None:
                    entry_signal = await self.get_entry_signal(symbol, market_data, signals, strategy)
                    
                    if entry_signal and entry_signal['confidence'] > 0.7:
                        # Open position
                        entry_price = current_candle['close']
                        position_size = balance * 0.1 / entry_price  # 10% of balance
                        
                        current_position = {
                            'entry_time': current_candle['timestamp'],
                            'entry_price': entry_price,
                            'size': position_size,
                            'side': entry_signal['signal'],
                            'stop_loss': entry_signal.get('stop_loss'),
                            'take_profit': entry_signal.get('take_profit')
                        }
                        
                        positions.append(current_position.copy())
                        logger.debug(f"Opened {entry_signal['signal']} position at {entry_price}")
                
                # Check for exit signals
                elif current_position is not None:
                    current_price = current_candle['close']
                    
                    # Check stop loss
                    if current_position['stop_loss']:
                        if current_position['side'] == 'BUY' and current_price <= current_position['stop_loss']:
                            exit_reason = 'STOP_LOSS'
                        elif current_position['side'] == 'SELL' and current_price >= current_position['stop_loss']:
                            exit_reason = 'STOP_LOSS'
                        else:
                            exit_reason = None
                    else:
                        exit_reason = None
                    
                    # Check take profit
                    if not exit_reason and current_position['take_profit']:
                        if current_position['side'] == 'BUY' and current_price >= current_position['take_profit']:
                            exit_reason = 'TAKE_PROFIT'
                        elif current_position['side'] == 'SELL' and current_price <= current_position['take_profit']:
                            exit_reason = 'TAKE_PROFIT'
                    
                    # Check strategy exit signals
                    if not exit_reason:
                        exit_signal = await self.get_exit_signal(symbol, market_data, signals, current_position, strategy)
                        if exit_signal:
                            exit_reason = exit_signal['reason']
                    
                    # Close position
                    if exit_reason:
                        exit_price = current_candle['close']
                        
                        # Calculate P&L
                        if current_position['side'] == 'BUY':
                            pnl = (exit_price - current_position['entry_price']) * current_position['size']
                        else:
                            pnl = (current_position['entry_price'] - exit_price) * current_position['size']
                        
                        balance += pnl
                        
                        trade = {
                            'entry_time': current_position['entry_time'],
                            'exit_time': current_candle['timestamp'],
                            'entry_price': current_position['entry_price'],
                            'exit_price': exit_price,
                            'side': current_position['side'],
                            'size': current_position['size'],
                            'pnl': pnl,
                            'pnl_pct': (pnl / (current_position['entry_price'] * current_position['size'])) * 100,
                            'exit_reason': exit_reason
                        }
                        
                        trades.append(trade)
                        current_position = None
                        
                        logger.debug(f"Closed position: {exit_reason}, P&L: {pnl:.2f}")
            
            # Calculate metrics
            if trades:
                total_pnl = sum(trade['pnl'] for trade in trades)
                winning_trades = [t for t in trades if t['pnl'] > 0]
                losing_trades = [t for t in trades if t['pnl'] < 0]
                
                win_rate = len(winning_trades) / len(trades) * 100
                avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
                avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
                profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades else float('inf')
                
                roi = (balance - 10000) / 10000 * 100
                
                result = {
                    'strategy': strategy,
                    'symbol': symbol,
                    'start_balance': 10000,
                    'end_balance': balance,
                    'total_pnl': total_pnl,
                    'roi_pct': roi,
                    'total_trades': len(trades),
                    'winning_trades': len(winning_trades),
                    'losing_trades': len(losing_trades),
                    'win_rate_pct': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'trades': trades[-10:],  # Last 10 trades
                    'start_date': df.iloc[0]['timestamp'],
                    'end_date': df.iloc[-1]['timestamp']
                }
                
                logger.info(f"✅ Backtesting tamamlandı: {len(trades)} işlem, %{win_rate:.1f} başarı oranı, ROI: %{roi:.2f}")
                
                return result
            else:
                return {
                    'error': 'No trades generated during backtesting period',
                    'strategy': strategy,
                    'symbol': symbol
                }
                
        except Exception as e:
            logger.error(f"❌ Backtesting hatası: {e}")
            return {'error': str(e)}
    
    def optimize_strategy_parameters(self, strategy: str, symbol: str, 
                                   historical_data: pd.DataFrame,
                                   parameter_ranges: Dict[str, List]) -> Dict[str, Any]:
        """Strateji parametrelerini optimize et"""
        try:
            logger.info(f"🔧 {strategy} parametreleri optimize ediliyor...")
            
            best_roi = -float('inf')
            best_params = {}
            results = []
            
            # Generate parameter combinations
            import itertools
            
            param_names = list(parameter_ranges.keys())
            param_values = list(parameter_ranges.values())
            
            # Limit combinations to prevent excessive computation
            combinations = list(itertools.product(*param_values))[:50]  # Max 50 combinations
            
            for combo in combinations:
                # Create parameter set
                params = dict(zip(param_names, combo))
                
                # Temporarily update strategy config
                original_config = self.config[strategy].copy()
                self.config[strategy].update(params)
                
                try:
                    # Run backtest with these parameters
                    import asyncio
                    result = asyncio.run(self.backtest_strategy(strategy, symbol, historical_data))
                    
                    if 'roi_pct' in result:
                        results.append({
                            'parameters': params,
                            'roi_pct': result['roi_pct'],
                            'win_rate_pct': result['win_rate_pct'],
                            'total_trades': result['total_trades'],
                            'profit_factor': result['profit_factor']
                        })
                        
                        # Track best result
                        if result['roi_pct'] > best_roi:
                            best_roi = result['roi_pct']
                            best_params = params.copy()
                
                except Exception as e:
                    logger.warning(f"⚠️ Parameter combination failed: {params}, error: {e}")
                
                finally:
                    # Restore original config
                    self.config[strategy] = original_config
            
            if results:
                # Sort by ROI
                results.sort(key=lambda x: x['roi_pct'], reverse=True)
                
                logger.info(f"✅ Optimization tamamlandı: En iyi ROI %{best_roi:.2f}")
                
                return {
                    'strategy': strategy,
                    'symbol': symbol,
                    'best_parameters': best_params,
                    'best_roi_pct': best_roi,
                    'optimization_results': results[:10],  # Top 10 results
                    'total_combinations_tested': len(results)
                }
            else:
                return {'error': 'No valid optimization results'}
                
        except Exception as e:
            logger.error(f"❌ Parameter optimization hatası: {e}")
            return {'error': str(e)}
    
    async def get_entry_signal(self, symbol: str, market_data: Dict, signals: Dict, strategy: str) -> Optional[Dict[str, Any]]:
        """Giriş sinyali al"""
        try:
            if strategy not in self.config:
                return None
            
            config = self.config[strategy]
            
            if strategy == 'scalping':
                return await self._scalping_entry(symbol, market_data, signals, config)
            elif strategy == 'swing_trading':
                return await self._swing_trading_entry(symbol, market_data, signals, config)
            elif strategy == 'trend_following':
                return await self._trend_following_entry(symbol, market_data, signals, config)
            elif strategy == 'mean_reversion':
                return await self._mean_reversion_entry(symbol, market_data, signals, config)
            else:
                logger.warning(f"⚠️ Bilinmeyen strateji: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Entry signal hatası: {e}")
            return None
    
    async def get_exit_signal(self, symbol: str, market_data: Dict, signals: Dict, 
                             position: Dict, strategy: str) -> Optional[Dict[str, Any]]:
        """Çıkış sinyali al"""
        try:
            if strategy not in self.config:
                return None
            
            config = self.config[strategy]
            df = market_data.get('dataframe')
            
            if df is None or len(df) < 10:
                return None
            
            current_price = market_data.get('close', df.iloc[-1]['close'])
            entry_price = position['entry_price']
            side = position['side']
            
            # Calculate current P&L
            if side == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            # Check for exit conditions based on strategy
            if strategy == 'scalping':
                # Quick exit for scalping
                if abs(pnl_pct) > 0.5:  # 0.5% target for scalping
                    return {
                        'exit': True,
                        'reason': 'SCALPING_TARGET',
                        'pnl_pct': pnl_pct
                    }
            
            elif strategy == 'swing_trading':
                # Check swing exit signals
                combined_signals = signals.get('signals', [])
                
                if side == 'BUY':
                    sell_signals = [s for s in combined_signals if s.get('type') == 'SELL']
                    if len(sell_signals) >= 2 or pnl_pct > 3.0:  # Strong sell signals or 3% profit
                        return {
                            'exit': True,
                            'reason': 'SWING_EXIT',
                            'pnl_pct': pnl_pct
                        }
                else:
                    buy_signals = [s for s in combined_signals if s.get('type') == 'BUY']
                    if len(buy_signals) >= 2 or pnl_pct > 3.0:  # Strong buy signals or 3% profit
                        return {
                            'exit': True,
                            'reason': 'SWING_EXIT',
                            'pnl_pct': pnl_pct
                        }
            
            elif strategy == 'trend_following':
                # Trend reversal detection
                ema_21 = df['close'].ewm(span=21).mean().iloc[-1]
                ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
                
                if side == 'BUY' and current_price < ema_21:
                    return {
                        'exit': True,
                        'reason': 'TREND_REVERSAL',
                        'pnl_pct': pnl_pct
                    }
                elif side == 'SELL' and current_price > ema_21:
                    return {
                        'exit': True,
                        'reason': 'TREND_REVERSAL',
                        'pnl_pct': pnl_pct
                    }
            
            elif strategy == 'mean_reversion':
                # Mean reversion exit
                sma_20 = df['close'].rolling(20).mean().iloc[-1]
                
                if side == 'BUY' and current_price >= sma_20:
                    return {
                        'exit': True,
                        'reason': 'MEAN_REVERSION',
                        'pnl_pct': pnl_pct
                    }
                elif side == 'SELL' and current_price <= sma_20:
                    return {
                        'exit': True,
                        'reason': 'MEAN_REVERSION',
                        'pnl_pct': pnl_pct
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Exit signal hatası: {e}")
            return None