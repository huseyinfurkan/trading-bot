#!/usr/bin/env python3
"""
Trading Bot Başlatma Scripti
Bu script botu güvenli bir şekilde başlatır ve hata durumlarını yönetir.
"""

import os
import sys
import logging
import signal
import time
from datetime import datetime

# Proje dizinini Python path'ine ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import TradingBot
from config import Config

def setup_logging():
    """Logging ayarlarını yapar"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def check_environment():
    """Environment kontrolü yapar"""
    logger = logging.getLogger(__name__)
    
    # .env dosyası kontrolü
    if not os.path.exists('.env'):
        logger.error(".env dosyası bulunamadı!")
        logger.info("Lütfen .env.example dosyasını .env olarak kopyalayın ve API anahtarlarınızı ekleyin.")
        return False
    
    # API anahtarları kontrolü
    config = Config()
    if not config.BINANCE_API_KEY or not config.BINANCE_SECRET_KEY:
        logger.error("Binance API anahtarları eksik!")
        logger.info("Lütfen .env dosyasında BINANCE_API_KEY ve BINANCE_SECRET_KEY değerlerini ayarlayın.")
        return False
    
    # Gerekli dizinler
    required_dirs = ['logs', 'models']
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            logger.info(f"{dir_name} dizini oluşturuldu.")
    
    return True

def signal_handler(signum, frame):
    """Sinyal işleyici"""
    logger = logging.getLogger(__name__)
    logger.info(f"Sinyal {signum} alındı. Bot durduruluyor...")
    if hasattr(signal_handler, 'bot'):
        signal_handler.bot.stop()
    sys.exit(0)

def main():
    """Ana fonksiyon"""
    logger = setup_logging()
    
    logger.info("=" * 50)
    logger.info("🤖 Gelişmiş Trading Bot Başlatılıyor")
    logger.info("=" * 50)
    
    # Environment kontrolü
    if not check_environment():
        logger.error("Environment kontrolü başarısız! Bot başlatılamıyor.")
        sys.exit(1)
    
    # Sinyal işleyicileri
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Bot başlat
        logger.info("Bot başlatılıyor...")
        bot = TradingBot()
        signal_handler.bot = bot  # Sinyal işleyici için referans
        
        # Bot durumunu kontrol et
        status = bot.get_bot_status()
        logger.info(f"Bot durumu: {status}")
        
        # Botu başlat
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.error(f"Bot çalışma hatası: {str(e)}")
        logger.exception("Detaylı hata:")
    finally:
        logger.info("Bot kapatıldı.")
        logger.info("=" * 50)

if __name__ == "__main__":
    main()