import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

class RiskManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.daily_loss = 0.0
        self.daily_trades = []
        self.max_daily_loss = config.MAX_DAILY_LOSS
        self.max_position_size = config.MAX_POSITION_SIZE
        
    def calculate_position_size(self, account_balance: float, confidence: float, 
                              strategy_type: str) -> float:
        """Pozisyon büyüklüğünü hesaplar"""
        try:
            # Base position size
            base_size = account_balance * self.max_position_size
            
            # Confidence adjustment
            confidence_multiplier = min(confidence, 1.0)
            
            # Strategy adjustment
            strategy_multiplier = 1.0
            if strategy_type == 'scalping':
                strategy_multiplier = 0.5  # Scalping için daha küçük pozisyon
            elif strategy_type == 'swing':
                strategy_multiplier = 1.0  # Swing için normal pozisyon
            
            # Final position size
            position_size = base_size * confidence_multiplier * strategy_multiplier
            
            # Minimum position check
            min_position = account_balance * 0.01  # %1 minimum
            if position_size < min_position:
                position_size = min_position
            
            self.logger.info(f"Pozisyon büyüklüğü hesaplandı: {position_size:.2f} USDT")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Pozisyon büyüklüğü hesaplama hatası: {str(e)}")
            return 0.0
    
    def check_daily_loss_limit(self, new_loss: float = 0.0) -> bool:
        """Günlük kayıp limitini kontrol eder"""
        try:
            # Reset daily loss if it's a new day
            current_date = datetime.now().date()
            if hasattr(self, 'last_check_date') and self.last_check_date != current_date:
                self.daily_loss = 0.0
                self.daily_trades = []
            
            self.last_check_date = current_date
            
            # Add new loss
            total_daily_loss = self.daily_loss + new_loss
            
            # Check if limit exceeded
            if total_daily_loss >= self.max_daily_loss:
                self.logger.warning(f"Günlük kayıp limiti aşıldı: {total_daily_loss:.4f} >= {self.max_daily_loss}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Günlük kayıp kontrolü hatası: {str(e)}")
            return False
    
    def update_daily_loss(self, trade_result: float):
        """Günlük kaybı günceller"""
        try:
            if trade_result < 0:
                self.daily_loss += abs(trade_result)
                self.logger.info(f"Günlük kayıp güncellendi: {self.daily_loss:.4f}")
        except Exception as e:
            self.logger.error(f"Günlük kayıp güncelleme hatası: {str(e)}")
    
    def add_trade(self, trade_data: Dict[str, Any]):
        """Trade'i kayıt eder"""
        try:
            trade_data['timestamp'] = datetime.now()
            self.daily_trades.append(trade_data)
            
            # Keep only today's trades
            current_date = datetime.now().date()
            self.daily_trades = [
                trade for trade in self.daily_trades 
                if trade['timestamp'].date() == current_date
            ]
            
        except Exception as e:
            self.logger.error(f"Trade kayıt hatası: {str(e)}")
    
    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float, 
                                  take_profit: float) -> float:
        """Risk/Ödül oranını hesaplar"""
        try:
            if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
                return 0.0
            
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            
            if risk == 0:
                return 0.0
            
            ratio = reward / risk
            return ratio
            
        except Exception as e:
            self.logger.error(f"Risk/Ödül oranı hesaplama hatası: {str(e)}")
            return 0.0
    
    def validate_trade_setup(self, entry_price: float, stop_loss: float, 
                           take_profit: float, position_size: float, 
                           account_balance: float) -> Dict[str, Any]:
        """Trade kurulumunu doğrular"""
        try:
            validation = {
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Position size validation
            if position_size > account_balance * self.max_position_size:
                validation['valid'] = False
                validation['errors'].append("Pozisyon büyüklüğü limiti aşıyor")
            
            # Risk/Reward validation
            rr_ratio = self.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
            if rr_ratio < 1.5:
                validation['warnings'].append(f"Risk/Ödül oranı düşük: {rr_ratio:.2f}")
            
            # Stop loss validation
            if stop_loss >= entry_price:
                validation['valid'] = False
                validation['errors'].append("Stop loss geçersiz")
            
            # Take profit validation
            if take_profit <= entry_price:
                validation['valid'] = False
                validation['errors'].append("Take profit geçersiz")
            
            # Daily loss validation
            if not self.check_daily_loss_limit():
                validation['valid'] = False
                validation['errors'].append("Günlük kayıp limiti aşıldı")
            
            return validation
            
        except Exception as e:
            self.logger.error(f"Trade doğrulama hatası: {str(e)}")
            return {'valid': False, 'warnings': [], 'errors': [str(e)]}
    
    def calculate_portfolio_risk(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Portfolio riskini hesaplar"""
        try:
            total_value = 0.0
            total_risk = 0.0
            correlation_risk = 0.0
            
            for position in positions:
                value = position.get('value', 0.0)
                risk = position.get('risk', 0.0)
                
                total_value += value
                total_risk += risk * value
            
            # Portfolio risk metrics
            portfolio_risk = {
                'total_value': total_value,
                'total_risk': total_risk,
                'risk_percentage': (total_risk / total_value * 100) if total_value > 0 else 0,
                'correlation_risk': correlation_risk
            }
            
            return portfolio_risk
            
        except Exception as e:
            self.logger.error(f"Portfolio risk hesaplama hatası: {str(e)}")
            return {}
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Risk metriklerini döndürür"""
        try:
            current_date = datetime.now().date()
            
            # Daily metrics
            daily_trades = [
                trade for trade in self.daily_trades 
                if trade['timestamp'].date() == current_date
            ]
            
            daily_pnl = sum(trade.get('pnl', 0) for trade in daily_trades)
            daily_win_rate = len([t for t in daily_trades if t.get('pnl', 0) > 0]) / len(daily_trades) if daily_trades else 0
            
            metrics = {
                'daily_loss': self.daily_loss,
                'daily_loss_limit': self.max_daily_loss,
                'daily_trades_count': len(daily_trades),
                'daily_pnl': daily_pnl,
                'daily_win_rate': daily_win_rate,
                'remaining_daily_loss': self.max_daily_loss - self.daily_loss,
                'max_position_size': self.max_position_size
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Risk metrikleri alma hatası: {str(e)}")
            return {}
    
    def should_stop_trading(self) -> bool:
        """Trading durdurulmalı mı kontrol eder"""
        try:
            # Daily loss limit check
            if self.daily_loss >= self.max_daily_loss:
                self.logger.warning("Günlük kayıp limiti aşıldı - Trading durduruluyor")
                return True
            
            # Consecutive losses check
            recent_trades = self.daily_trades[-5:]  # Son 5 trade
            if len(recent_trades) >= 5:
                consecutive_losses = 0
                for trade in reversed(recent_trades):
                    if trade.get('pnl', 0) < 0:
                        consecutive_losses += 1
                    else:
                        break
                
                if consecutive_losses >= 3:
                    self.logger.warning("3 ardışık kayıp - Trading durduruluyor")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Trading durdurma kontrolü hatası: {str(e)}")
            return False
    
    def reset_daily_metrics(self):
        """Günlük metrikleri sıfırlar"""
        try:
            self.daily_loss = 0.0
            self.daily_trades = []
            self.logger.info("Günlük metrikler sıfırlandı")
        except Exception as e:
            self.logger.error(f"Günlük metrik sıfırlama hatası: {str(e)}")