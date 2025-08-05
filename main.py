#!/usr/bin/env python3
"""
Advanced Multi-Coin Trading Bot
Gelişmiş Çok Coinli Trading Botu

Bu bot şu özellikleri içerir:
- Multi-coin trading desteği
- AI sinyal filtreleme
- Dinamik strateji seçimi
- Piyasa durumu analizi
- Risk yönetimi
- Scalping ve uzun vadeli trading
"""

import asyncio
import signal
import sys
import traceback
from pathlib import Path
from loguru import logger
from typing import Dict, List, Optional

# Add src to Python path for proper imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Core modules
from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.bot_coordinator import BotCoordinator
from src.core.risk_manager import RiskManager
from src.core.monitoring import MonitoringSystem

# Trading modules
from src.trading.exchange_manager import ExchangeManager
from src.trading.strategy_engine import StrategyEngine
from src.trading.position_manager import PositionManager

# AI modules
from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.confidence_calculator import ConfidenceCalculator

# Utils
from src.utils.logger_setup import setup_logging
from src.utils.notifications import NotificationManager


class AdvancedTradingBot:
    """Ana trading bot sınıfı"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Bot'u başlat"""
        self.config_path = config_path
        self.config = None
        self.running = False
        
        # Core components
        self.config_manager = None
        self.db_manager = None
        self.bot_coordinator = None
        self.risk_manager = None
        self.monitoring = None
        
        # Trading components
        self.exchange_manager = None
        self.strategy_engine = None
        self.position_manager = None
        
        # AI components
        self.signal_filter = None
        self.market_analyzer = None
        self.confidence_calculator = None
        
        # Utils
        self.notification_manager = None
        
    async def initialize(self):
        """Tüm bileşenleri başlat"""
        try:
            logger.info("🚀 Advanced Trading Bot başlatılıyor...")
            
            # Config yükle
            self.config_manager = ConfigManager(self.config_path)
            self.config = await self.config_manager.load_config()
            
            # Logging'i kur
            setup_logging(self.config.get('logging', {}))
            
            # Database bağlantısı
            self.db_manager = DatabaseManager(self.config.get('database', {}))
            await self.db_manager.initialize()
            
            # Notification sistemi
            self.notification_manager = NotificationManager(
                self.config.get('notifications', {})
            )
            await self.notification_manager.initialize()
            
            # Exchange manager
            self.exchange_manager = ExchangeManager(
                self.config.get('exchanges', {})
            )
            await self.exchange_manager.initialize()
            
            # Risk manager
            self.risk_manager = RiskManager(
                self.config.get('risk_management', {}),
                self.db_manager
            )
            
            # AI components
            self.signal_filter = AISignalFilter(
                self.config.get('ai_settings', {}),
                self.db_manager
            )
            await self.signal_filter.initialize()
            
            self.market_analyzer = MarketAnalyzer(
                self.config.get('market_conditions', {}),
                self.db_manager
            )
            
            self.confidence_calculator = ConfidenceCalculator(
                self.config.get('ai_settings', {}),
                self.db_manager
            )
            
            # Trading components
            self.strategy_engine = StrategyEngine(
                self.config.get('strategies', {}),
                self.signal_filter,
                self.market_analyzer,
                self.confidence_calculator
            )
            
            self.position_manager = PositionManager(
                self.exchange_manager,
                self.risk_manager,
                self.db_manager
            )
            
            # Bot coordinator
            self.bot_coordinator = BotCoordinator(
                self.strategy_engine,
                self.position_manager,
                self.market_analyzer,
                self.notification_manager
            )
            
            # Monitoring sistemi
            self.monitoring = MonitoringSystem(
                self.config.get('performance', {}),
                self.db_manager,
                self.notification_manager
            )
            
            logger.success("✅ Tüm bileşenler başarıyla başlatıldı!")
            
        except Exception as e:
            logger.error(f"❌ Bot başlatma hatası: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def start_trading(self):
        """Trading başlat"""
        try:
            self.running = True
            logger.info("📈 Trading başlatılıyor...")
            
            # Ana trading loop'u başlat
            await self.bot_coordinator.start()
            
            # Monitoring'i başlat
            await self.monitoring.start()
            
            # Trading pairs'leri yükle
            trading_pairs = self.config.get('trading_pairs', {})
            all_pairs = []
            for category, pairs in trading_pairs.items():
                all_pairs.extend(pairs)
            
            logger.info(f"💎 {len(all_pairs)} trading pair izleniyor: {all_pairs}")
            
            # Bildirim gönder
            await self.notification_manager.send_message(
                "🤖 Advanced Trading Bot başlatıldı!\n"
                f"📊 {len(all_pairs)} coin izleniyor\n"
                f"🧠 AI filtreleme aktif\n"
                f"⚡ Multi-strateji çalışıyor"
            )
            
            # Ana döngü
            while self.running:
                try:
                    # Market durumunu analiz et
                    market_condition = await self.market_analyzer.analyze_current_market()
                    
                    # Her trading pair için işlem yap
                    for pair in all_pairs:
                        await self.process_trading_pair(pair, market_condition)
                    
                    # Monitoring kontrolleri
                    await self.monitoring.check_performance()
                    
                    # Kısa bekleme
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ Trading loop hatası: {e}")
                    await asyncio.sleep(5)
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Trading başlatma hatası: {e}")
            raise
    
    async def process_trading_pair(self, pair: str, market_condition: Dict):
        """Tek bir trading pair'i işle"""
        try:
            # Mevcut pozisyonları kontrol et
            positions = await self.position_manager.get_positions(pair)
            
            # Piyasa verilerini al
            market_data = await self.exchange_manager.get_market_data(pair)
            if not market_data:
                return
            
            # AI sinyal analizi
            signals = await self.signal_filter.analyze_signals(pair, market_data)
            
            # Güven faktörü hesapla
            confidence = await self.confidence_calculator.calculate_confidence(
                pair, market_data, signals, market_condition
            )
            
            # Strateji seç
            selected_strategy = await self.strategy_engine.select_strategy(
                pair, market_condition, confidence
            )
            
            if not selected_strategy:
                return
            
            # Güven eşiğini kontrol et
            strategy_config = self.config['strategies'][selected_strategy]
            required_confidence = strategy_config.get('confidence_threshold', 0.7)
            
            if confidence < required_confidence:
                logger.debug(f"🔍 {pair}: Güven faktörü yetersiz ({confidence:.3f} < {required_confidence:.3f})")
                return
            
            # Pozisyon aç/kapat kararı ver
            if not positions:
                # Yeni pozisyon açma kontrolü
                action = await self.strategy_engine.get_entry_signal(
                    pair, market_data, signals, selected_strategy
                )
                
                if action and action['signal'] in ['BUY', 'SELL']:
                    await self.position_manager.open_position(
                        pair, action, confidence, selected_strategy
                    )
            else:
                # Mevcut pozisyonları yönet
                for position in positions:
                    action = await self.strategy_engine.get_exit_signal(
                        pair, market_data, signals, position, selected_strategy
                    )
                    
                    if action and action['signal'] == 'CLOSE':
                        await self.position_manager.close_position(
                            position, action['reason']
                        )
                        
        except Exception as e:
            logger.error(f"❌ {pair} işlem hatası: {e}")
    
    async def shutdown(self):
        """Bot'u güvenli şekilde kapat"""
        logger.info("🛑 Bot kapatılıyor...")
        self.running = False
        
        try:
            # Tüm pozisyonları kapat
            if self.position_manager:
                await self.position_manager.close_all_positions("Bot shutdown")
            
            # Bileşenleri kapat
            if self.monitoring:
                await self.monitoring.stop()
            
            if self.bot_coordinator:
                await self.bot_coordinator.stop()
            
            if self.exchange_manager:
                await self.exchange_manager.close()
            
            if self.db_manager:
                await self.db_manager.close()
            
            # Son bildirim
            if self.notification_manager:
                await self.notification_manager.send_message(
                    "🛑 Advanced Trading Bot güvenli şekilde kapatıldı"
                )
                await self.notification_manager.close()
            
            logger.success("✅ Bot başarıyla kapatıldı")
            
        except Exception as e:
            logger.error(f"❌ Kapatma hatası: {e}")


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info(f"📡 Signal {signum} alındı, bot kapatılıyor...")
    sys.exit(0)


async def main():
    """Ana fonksiyon"""
    # Signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = None
    try:
        # Bot'u oluştur ve başlat
        bot = AdvancedTradingBot()
        await bot.initialize()
        await bot.start_trading()
        
    except KeyboardInterrupt:
        logger.info("⌨️ Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"❌ Kritik hata: {e}")
        logger.error(traceback.format_exc())
    finally:
        if bot:
            await bot.shutdown()


if __name__ == "__main__":
    # Event loop'u çalıştır
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Program hatası: {e}")
        sys.exit(1)