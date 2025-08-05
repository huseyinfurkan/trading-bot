#!/usr/bin/env python3
"""
Trading Bot Test Scripti
Bu script botun çeşitli bileşenlerini test eder.
"""

import os
import sys
import logging
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Proje dizinini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models.ai_model import AIModel
from strategies.strategy_manager import StrategyManager
from strategies.scalping_strategy import ScalpingStrategy
from strategies.swing_strategy import SwingStrategy
from risk_management.risk_manager import RiskManager

class TestTradingBot(unittest.TestCase):
    """Trading Bot test sınıfı"""
    
    def setUp(self):
        """Test öncesi hazırlık"""
        self.config = Config()
        self.setup_logging()
        
        # Test verisi oluştur
        self.test_data = self.create_test_data()
        
    def setup_logging(self):
        """Test logging ayarları"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_test_data(self):
        """Test için OHLCV verisi oluşturur"""
        np.random.seed(42)
        
        # 100 günlük test verisi
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Başlangıç fiyatı
        base_price = 50000
        
        # Fiyat verisi oluştur
        price_changes = np.random.normal(0, 0.02, 100)  # %2 volatilite
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # OHLCV verisi
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # OHLC hesapla
            volatility = abs(np.random.normal(0, 0.01))
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = price * (1 + np.random.normal(0, 0.005))
            close_price = price
            
            # Volume
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def test_config(self):
        """Config testi"""
        self.assertIsNotNone(self.config.BINANCE_API_KEY)
        self.assertIsNotNone(self.config.TRADING_PAIRS)
        self.assertTrue(len(self.config.TRADING_PAIRS) > 0)
        self.assertGreater(self.config.MIN_CONFIDENCE_THRESHOLD, 0)
        self.assertLess(self.config.MIN_CONFIDENCE_THRESHOLD, 1)
    
    def test_ai_model(self):
        """AI Model testi"""
        ai_model = AIModel(self.config)
        
        # Model eğitimi testi
        success = ai_model.train(self.test_data)
        self.assertTrue(success)
        
        # Tahmin testi
        prediction, confidence = ai_model.predict(self.test_data)
        self.assertIsNotNone(prediction)
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)
        
        # Model kaydetme/yükleme testi
        ai_model.save_model()
        loaded = ai_model.load_model()
        self.assertTrue(loaded)
    
    def test_scalping_strategy(self):
        """Scalping strateji testi"""
        strategy = ScalpingStrategy(self.config)
        
        # Analiz testi
        analysis = strategy.analyze(self.test_data)
        self.assertIsNotNone(analysis)
        self.assertIn('signal', analysis)
        self.assertIn('confidence', analysis)
        
        # Entry testi
        should_enter, confidence = strategy.should_enter(analysis)
        self.assertIsInstance(should_enter, bool)
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)
        
        # Exit testi
        entry_price = 50000
        current_price = 50100
        should_exit, reason = strategy.should_exit(analysis, entry_price, current_price)
        self.assertIsInstance(should_exit, bool)
        self.assertIsInstance(reason, str)
        
        # Risk seviyeleri testi
        stop_loss = strategy.get_stop_loss(entry_price, analysis)
        take_profit = strategy.get_take_profit(entry_price, analysis)
        self.assertGreater(entry_price, stop_loss)
        self.assertLess(entry_price, take_profit)
    
    def test_swing_strategy(self):
        """Swing strateji testi"""
        strategy = SwingStrategy(self.config)
        
        # Analiz testi
        analysis = strategy.analyze(self.test_data)
        self.assertIsNotNone(analysis)
        self.assertIn('signal', analysis)
        self.assertIn('confidence', analysis)
        
        # Entry testi
        should_enter, confidence = strategy.should_enter(analysis)
        self.assertIsInstance(should_enter, bool)
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)
        
        # Exit testi
        entry_price = 50000
        current_price = 50100
        should_exit, reason = strategy.should_exit(analysis, entry_price, current_price)
        self.assertIsInstance(should_exit, bool)
        self.assertIsInstance(reason, str)
        
        # Risk seviyeleri testi
        stop_loss = strategy.get_stop_loss(entry_price, analysis)
        take_profit = strategy.get_take_profit(entry_price, analysis)
        self.assertGreater(entry_price, stop_loss)
        self.assertLess(entry_price, take_profit)
    
    def test_strategy_manager(self):
        """Strateji yöneticisi testi"""
        manager = StrategyManager(self.config)
        
        # Market conditions testi
        conditions = manager.analyze_market_conditions(self.test_data)
        self.assertIsNotNone(conditions)
        self.assertIn('market_type', conditions)
        self.assertIn('volatility', conditions)
        
        # Strateji seçimi testi
        selected_strategy = manager.select_strategy(conditions)
        self.assertIn(selected_strategy, ['scalping', 'swing'])
        
        # Best signal testi
        best_signal = manager.get_best_signal(self.test_data)
        self.assertIsNotNone(best_signal)
        self.assertIn('strategy', best_signal)
        self.assertIn('signal', best_signal)
        self.assertIn('confidence', best_signal)
    
    def test_risk_manager(self):
        """Risk yöneticisi testi"""
        risk_manager = RiskManager(self.config)
        
        # Pozisyon büyüklüğü testi
        balance = 10000
        confidence = 0.8
        strategy_type = 'scalping'
        
        position_size = risk_manager.calculate_position_size(balance, confidence, strategy_type)
        self.assertGreater(position_size, 0)
        self.assertLessEqual(position_size, balance * self.config.MAX_POSITION_SIZE)
        
        # Risk/Ödül oranı testi
        entry_price = 50000
        stop_loss = 49000
        take_profit = 52000
        
        rr_ratio = risk_manager.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
        self.assertGreater(rr_ratio, 0)
        
        # Trade doğrulama testi
        validation = risk_manager.validate_trade_setup(
            entry_price, stop_loss, take_profit, position_size, balance
        )
        self.assertIsInstance(validation, dict)
        self.assertIn('valid', validation)
        self.assertIn('warnings', validation)
        self.assertIn('errors', validation)
        
        # Risk metrikleri testi
        metrics = risk_manager.get_risk_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('daily_loss', metrics)
        self.assertIn('daily_loss_limit', metrics)
    
    def test_data_validation(self):
        """Veri doğrulama testi"""
        # Geçerli veri testi
        strategy = ScalpingStrategy(self.config)
        is_valid = strategy.validate_market_data(self.test_data)
        self.assertTrue(is_valid)
        
        # Geçersiz veri testi
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        is_valid = strategy.validate_market_data(invalid_data)
        self.assertFalse(is_valid)
        
        # Boş veri testi
        empty_data = pd.DataFrame()
        is_valid = strategy.validate_market_data(empty_data)
        self.assertFalse(is_valid)
    
    def test_performance_metrics(self):
        """Performans metrikleri testi"""
        risk_manager = RiskManager(self.config)
        
        # Test trade'leri ekle
        test_trades = [
            {'pnl': 100, 'timestamp': datetime.now()},
            {'pnl': -50, 'timestamp': datetime.now()},
            {'pnl': 200, 'timestamp': datetime.now()},
            {'pnl': -30, 'timestamp': datetime.now()},
            {'pnl': 150, 'timestamp': datetime.now()}
        ]
        
        for trade in test_trades:
            risk_manager.add_trade(trade)
            if trade['pnl'] < 0:
                risk_manager.update_daily_loss(trade['pnl'])
        
        # Metrikleri kontrol et
        metrics = risk_manager.get_risk_metrics()
        self.assertGreater(metrics['daily_trades_count'], 0)
        self.assertGreaterEqual(metrics['daily_win_rate'], 0)
        self.assertLessEqual(metrics['daily_win_rate'], 1)

def run_tests():
    """Testleri çalıştırır"""
    print("🧪 Trading Bot Testleri Başlatılıyor...")
    print("=" * 50)
    
    # Test suite oluştur
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTradingBot)
    
    # Testleri çalıştır
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Sonuçları yazdır
    print("=" * 50)
    print(f"✅ Başarılı Testler: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Başarısız Testler: {len(result.failures)}")
    print(f"⚠️ Hatalı Testler: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Başarısız Testler:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️ Hatalı Testler:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)