"""
Config Manager
Konfigürasyon dosyalarını yönetir ve doğrular
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class ConfigManager:
    """Konfigürasyon yöneticisi"""
    
    def __init__(self, config_path: str):
        """
        Args:
            config_path: Konfigürasyon dosyasının yolu
        """
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
        self._validate_config_exists()
    
    def _validate_config_exists(self):
        """Konfigürasyon dosyasının varlığını kontrol et"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Konfigürasyon dosyası bulunamadı: {self.config_path}")
    
    async def load_config(self) -> Dict[str, Any]:
        """Konfigürasyon dosyasını yükle ve doğrula"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            self._validate_config()
            self._set_environment_variables()
            
            logger.info(f"✅ Konfigürasyon başarıyla yüklendi: {self.config_path}")
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parse hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Konfigürasyon yükleme hatası: {e}")
            raise
    
    def _validate_config(self):
        """Konfigürasyon dosyasını doğrula"""
        if not self.config:
            raise ValueError("Konfigürasyon yüklenemedi")
        
        required_sections = [
            'exchanges', 'trading_pairs', 'ai_settings', 
            'strategies', 'risk_management', 'market_conditions'
        ]
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Gerekli konfigürasyon bölümü eksik: {section}")
        
        # Exchange konfigürasyonlarını doğrula
        for exchange_name, exchange_config in self.config['exchanges'].items():
            if not exchange_config.get('api_key') or not exchange_config.get('secret'):
                logger.warning(f"⚠️ {exchange_name} API anahtarları eksik")
        
        # Strateji konfigürasyonlarını doğrula
        for strategy_name, strategy_config in self.config['strategies'].items():
            if not strategy_config.get('enabled'):
                continue
            
            required_fields = ['timeframes', 'profit_target', 'stop_loss', 'confidence_threshold']
            for field in required_fields:
                if field not in strategy_config:
                    raise ValueError(f"{strategy_name} stratejisinde eksik alan: {field}")
        
        logger.info("✅ Konfigürasyon doğrulaması başarıyla tamamlandı")
    
    def _set_environment_variables(self):
        """Konfigürasyondan environment variable'ları ayarla"""
        # API anahtarları için environment variable'ları kontrol et
        for exchange_name, exchange_config in self.config['exchanges'].items():
            api_key_env = f"{exchange_name.upper()}_API_KEY"
            secret_env = f"{exchange_name.upper()}_SECRET"
            
            if os.getenv(api_key_env):
                exchange_config['api_key'] = os.getenv(api_key_env)
            if os.getenv(secret_env):
                exchange_config['secret'] = os.getenv(secret_env)
            
            # OKX için passphrase
            if exchange_name == 'okx':
                passphrase_env = f"{exchange_name.upper()}_PASSPHRASE"
                if os.getenv(passphrase_env):
                    exchange_config['passphrase'] = os.getenv(passphrase_env)
        
        # Telegram bot token
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if telegram_token:
            self.config['notifications']['telegram']['bot_token'] = telegram_token
        
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if telegram_chat_id:
            self.config['notifications']['telegram']['chat_id'] = telegram_chat_id
    
    def get_config(self) -> Dict[str, Any]:
        """Mevcut konfigürasyonu döndür"""
        if not self.config:
            raise ValueError("Konfigürasyon henüz yüklenmedi")
        return self.config
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """Belirli bir konfigürasyon bölümünü döndür"""
        config = self.get_config()
        if section_name not in config:
            raise KeyError(f"Konfigürasyon bölümü bulunamadı: {section_name}")
        return config[section_name]
    
    def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Belirli bir exchange konfigürasyonunu döndür"""
        exchanges = self.get_section('exchanges')
        if exchange_name not in exchanges:
            raise KeyError(f"Exchange konfigürasyonu bulunamadı: {exchange_name}")
        return exchanges[exchange_name]
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Belirli bir strateji konfigürasyonunu döndür"""
        strategies = self.get_section('strategies')
        if strategy_name not in strategies:
            raise KeyError(f"Strateji konfigürasyonu bulunamadı: {strategy_name}")
        return strategies[strategy_name]
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """Konfigürasyonu güncelle"""
        if not self.config:
            raise ValueError("Konfigürasyon henüz yüklenmedi")
        
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        logger.info(f"🔧 Konfigürasyon güncellendi: {section}.{key} = {value}")
    
    async def save_config(self) -> None:
        """Konfigürasyonu dosyaya kaydet"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"💾 Konfigürasyon kaydedildi: {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Konfigürasyon kaydetme hatası: {e}")
            raise