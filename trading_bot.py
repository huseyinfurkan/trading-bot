import pandas as pd
import numpy as np
import logging
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import threading
import asyncio

from config import Config
from models.ai_model import AIModel
from strategies.strategy_manager import StrategyManager
from exchange.binance_client import BinanceClient
from risk_management.risk_manager import RiskManager

class TradingBot:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        
        # Initialize components
        self.ai_model = AIModel(self.config)
        self.strategy_manager = StrategyManager(self.config)
        self.exchange_client = BinanceClient(self.config)
        self.risk_manager = RiskManager(self.config)
        
        # Bot state
        self.is_running = False
        self.active_positions = {}
        self.trading_pairs = self.config.TRADING_PAIRS
        self.last_analysis = {}
        
        # Load AI model
        if not self.ai_model.load_model():
            self.logger.warning("AI model yüklenemedi, yeni model eğitilecek")
        
        self.logger.info("Trading Bot başlatıldı")
    
    def setup_logging(self):
        """Logging ayarlarını yapar"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Botu başlatır"""
        try:
            self.logger.info("Trading Bot başlatılıyor...")
            self.is_running = True
            
            # Schedule tasks
            schedule.every(1).minutes.do(self.analyze_markets)
            schedule.every(5).minutes.do(self.check_positions)
            schedule.every(1).hours.do(self.retrain_ai_model)
            schedule.every().day.at("00:00").do(self.reset_daily_metrics)
            
            # Start trading loop
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Bot durduruluyor...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Bot çalışma hatası: {str(e)}")
            self.stop()
    
    def stop(self):
        """Botu durdurur"""
        self.is_running = False
        self.logger.info("Trading Bot durduruldu")
    
    def analyze_markets(self):
        """Tüm piyasaları analiz eder"""
        try:
            self.logger.info("Piyasa analizi başlıyor...")
            
            for pair in self.trading_pairs:
                try:
                    # Get market data
                    market_data = self.exchange_client.get_ohlcv(pair, '5m', 200)
                    
                    if market_data.empty:
                        self.logger.warning(f"{pair} için veri alınamadı")
                        continue
                    
                    # AI prediction
                    ai_prediction, ai_confidence = self.ai_model.predict(market_data)
                    
                    # Strategy analysis
                    best_signal = self.strategy_manager.get_best_signal(market_data)
                    
                    # Combine AI and strategy signals
                    combined_signal = self.combine_signals(best_signal, ai_prediction, ai_confidence)
                    
                    # Store analysis
                    self.last_analysis[pair] = {
                        'timestamp': datetime.now(),
                        'market_data': market_data,
                        'ai_prediction': ai_prediction,
                        'ai_confidence': ai_confidence,
                        'strategy_signal': best_signal,
                        'combined_signal': combined_signal
                    }
                    
                    # Execute trading logic
                    self.execute_trading_logic(pair, combined_signal)
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"{pair} analiz hatası: {str(e)}")
                    continue
            
            self.logger.info("Piyasa analizi tamamlandı")
            
        except Exception as e:
            self.logger.error(f"Piyasa analizi hatası: {str(e)}")
    
    def combine_signals(self, strategy_signal: Dict[str, Any], 
                       ai_prediction: Optional[int], ai_confidence: float) -> Dict[str, Any]:
        """AI ve strateji sinyallerini birleştirir"""
        try:
            combined = strategy_signal.copy()
            
            # AI confidence weight
            ai_weight = self.config.AI_MODEL_CONFIG['confidence_weight']
            
            # Adjust strategy confidence with AI
            strategy_confidence = strategy_signal.get('confidence', 0.0)
            ai_adjusted_confidence = (strategy_confidence * (1 - ai_weight) + 
                                    ai_confidence * ai_weight)
            
            combined['ai_prediction'] = ai_prediction
            combined['ai_confidence'] = ai_confidence
            combined['combined_confidence'] = ai_adjusted_confidence
            
            # Final decision
            if ai_adjusted_confidence >= self.config.MIN_CONFIDENCE_THRESHOLD:
                combined['should_enter'] = strategy_signal.get('should_enter', False)
            else:
                combined['should_enter'] = False
            
            return combined
            
        except Exception as e:
            self.logger.error(f"Sinyal birleştirme hatası: {str(e)}")
            return strategy_signal
    
    def execute_trading_logic(self, pair: str, signal: Dict[str, Any]):
        """Trading mantığını uygular"""
        try:
            # Check if we should stop trading
            if self.risk_manager.should_stop_trading():
                self.logger.warning("Risk limitleri aşıldı - Trading durduruldu")
                return
            
            # Check if we have an active position
            if pair in self.active_positions:
                self.manage_existing_position(pair, signal)
            else:
                self.check_for_new_position(pair, signal)
                
        except Exception as e:
            self.logger.error(f"{pair} trading mantığı hatası: {str(e)}")
    
    def check_for_new_position(self, pair: str, signal: Dict[str, Any]):
        """Yeni pozisyon için kontrol eder"""
        try:
            if not signal.get('should_enter', False):
                return
            
            # Get account balance
            balance = self.exchange_client.get_balance('USDT')
            if balance < 10:  # Minimum 10 USDT
                self.logger.warning(f"Yetersiz bakiye: {balance} USDT")
                return
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(
                balance, signal['combined_confidence'], signal['strategy']
            )
            
            if position_size <= 0:
                return
            
            # Get current price
            current_price = self.exchange_client.get_current_price(pair)
            if current_price <= 0:
                return
            
            # Calculate coin amount
            coin_amount = self.exchange_client.calculate_order_amount(pair, position_size)
            
            # Get risk levels
            risk_levels = self.strategy_manager.get_risk_levels(
                signal['strategy'], current_price, signal['analysis']
            )
            
            # Validate trade setup
            validation = self.risk_manager.validate_trade_setup(
                current_price, risk_levels.get('stop_loss', 0),
                risk_levels.get('take_profit', 0), position_size, balance
            )
            
            if not validation['valid']:
                self.logger.warning(f"{pair} trade doğrulama hatası: {validation['errors']}")
                return
            
            # Execute buy order
            order = self.exchange_client.place_order(
                pair, 'buy', coin_amount, order_type='market'
            )
            
            if order:
                # Record position
                self.active_positions[pair] = {
                    'entry_price': current_price,
                    'amount': coin_amount,
                    'strategy': signal['strategy'],
                    'stop_loss': risk_levels.get('stop_loss', 0),
                    'take_profit': risk_levels.get('take_profit', 0),
                    'entry_time': datetime.now(),
                    'order_id': order['id'],
                    'confidence': signal['combined_confidence']
                }
                
                self.logger.info(f"Yeni pozisyon açıldı: {pair} @ {current_price}")
                
        except Exception as e:
            self.logger.error(f"{pair} yeni pozisyon hatası: {str(e)}")
    
    def manage_existing_position(self, pair: str, signal: Dict[str, Any]):
        """Mevcut pozisyonu yönetir"""
        try:
            position = self.active_positions[pair]
            current_price = self.exchange_client.get_current_price(pair)
            
            if current_price <= 0:
                return
            
            # Check exit conditions
            should_exit, exit_reason = self.strategy_manager.should_exit_position(
                position['strategy'], signal['analysis'], 
                position['entry_price'], current_price
            )
            
            # Check stop loss and take profit
            if current_price <= position['stop_loss']:
                should_exit = True
                exit_reason = "stop_loss"
            elif current_price >= position['take_profit']:
                should_exit = True
                exit_reason = "take_profit"
            
            if should_exit:
                self.close_position(pair, current_price, exit_reason)
                
        except Exception as e:
            self.logger.error(f"{pair} pozisyon yönetimi hatası: {str(e)}")
    
    def close_position(self, pair: str, current_price: float, reason: str):
        """Pozisyonu kapatır"""
        try:
            position = self.active_positions[pair]
            
            # Calculate P&L
            pnl_percent = (current_price - position['entry_price']) / position['entry_price']
            pnl_usdt = position['amount'] * current_price * pnl_percent
            
            # Execute sell order
            order = self.exchange_client.place_order(
                pair, 'sell', position['amount'], order_type='market'
            )
            
            if order:
                # Record trade
                trade_data = {
                    'pair': pair,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'amount': position['amount'],
                    'pnl': pnl_usdt,
                    'pnl_percent': pnl_percent,
                    'strategy': position['strategy'],
                    'exit_reason': reason,
                    'hold_time': (datetime.now() - position['entry_time']).total_seconds()
                }
                
                self.risk_manager.add_trade(trade_data)
                self.risk_manager.update_daily_loss(pnl_usdt)
                
                # Remove from active positions
                del self.active_positions[pair]
                
                self.logger.info(f"Pozisyon kapatıldı: {pair} - P&L: {pnl_usdt:.2f} USDT ({pnl_percent:.2%})")
                
        except Exception as e:
            self.logger.error(f"{pair} pozisyon kapatma hatası: {str(e)}")
    
    def check_positions(self):
        """Açık pozisyonları kontrol eder"""
        try:
            for pair in list(self.active_positions.keys()):
                current_price = self.exchange_client.get_current_price(pair)
                if current_price > 0:
                    self.manage_existing_position(pair, {})
                    
        except Exception as e:
            self.logger.error(f"Pozisyon kontrolü hatası: {str(e)}")
    
    def retrain_ai_model(self):
        """AI modelini yeniden eğitir"""
        try:
            if self.ai_model.should_retrain():
                self.logger.info("AI model yeniden eğitiliyor...")
                
                # Collect historical data for training
                training_data = pd.DataFrame()
                
                for pair in self.trading_pairs[:3]:  # İlk 3 pair için
                    data = self.exchange_client.get_ohlcv(pair, '1h', 1000)
                    if not data.empty:
                        training_data = pd.concat([training_data, data])
                
                if not training_data.empty:
                    success = self.ai_model.train(training_data)
                    if success:
                        self.logger.info("AI model başarıyla eğitildi")
                    else:
                        self.logger.warning("AI model eğitimi başarısız")
                        
        except Exception as e:
            self.logger.error(f"AI model eğitimi hatası: {str(e)}")
    
    def reset_daily_metrics(self):
        """Günlük metrikleri sıfırlar"""
        try:
            self.risk_manager.reset_daily_metrics()
            self.logger.info("Günlük metrikler sıfırlandı")
        except Exception as e:
            self.logger.error(f"Günlük metrik sıfırlama hatası: {str(e)}")
    
    def get_bot_status(self) -> Dict[str, Any]:
        """Bot durumunu döndürür"""
        try:
            balance = self.exchange_client.get_balance('USDT')
            risk_metrics = self.risk_manager.get_risk_metrics()
            
            status = {
                'is_running': self.is_running,
                'balance': balance,
                'active_positions': len(self.active_positions),
                'trading_pairs': self.trading_pairs,
                'risk_metrics': risk_metrics,
                'last_analysis_count': len(self.last_analysis),
                'ai_model_loaded': self.ai_model.model is not None,
                'last_ai_training': self.ai_model.last_training
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Bot durumu alma hatası: {str(e)}")
            return {}

if __name__ == "__main__":
    bot = TradingBot()
    bot.start()