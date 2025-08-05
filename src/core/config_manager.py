"""
Config Manager
Konfigürasyon dosyalarını yönetir ve doğrular
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv


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
            logger.info(f"📋 Konfigürasyon yükleniyor: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            if not self.config:
                raise ValueError("Konfigürasyon dosyası boş")
            
            # Environment variables ile override et
            self._set_environment_variables()
            
            # Konfigürasyonu doğrula
            await self._validate_config()
            
            logger.success("✅ Konfigürasyon başarıyla yüklendi")
            return self.config
            
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parse hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Konfigürasyon yükleme hatası: {e}")
            raise
    
    async def _validate_config(self):
        """Konfigürasyonu doğrula"""
        logger.info("🔍 Konfigürasyon doğrulanıyor...")
        
        # Gerekli ana bölümleri kontrol et
        required_sections = ['exchanges', 'strategies', 'risk_management', 'trading_pairs']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Eksik konfigürasyon bölümü: {section}")
        
        # Exchange ayarlarını doğrula (esnek validation)
        for exchange_name, exchange_config in self.config['exchanges'].items():
            # Sadece enabled alanı yoksa otomatik false yap
            if 'enabled' not in exchange_config:
                exchange_config['enabled'] = False
                logger.warning(f"⚠️ {exchange_name} exchange 'enabled' alanı eksik, false olarak ayarlandı")
        
        # Strateji ayarlarını doğrula (esnek validation)
        for strategy_name, strategy_config in self.config['strategies'].items():
            # Enabled alanı yoksa otomatik true yap
            if 'enabled' not in strategy_config:
                strategy_config['enabled'] = True
                logger.warning(f"⚠️ {strategy_name} stratejisi 'enabled' alanı eksik, true olarak ayarlandı")
            
            if not strategy_config.get('enabled'):
                continue
            
            # Required fields için default değerler
            defaults = {
                'weight': 0.25,
                'parameters': {}
            }
            
            for field, default_value in defaults.items():
                if field not in strategy_config:
                    strategy_config[field] = default_value
                    logger.warning(f"⚠️ {strategy_name} stratejisinde '{field}' alanı eksik, default değer ayarlandı")
        
        logger.info("✅ Konfigürasyon doğrulaması başarıyla tamamlandı")
    
    def _set_environment_variables(self):
        """Environment variables ile konfigürasyonu güncelle"""
        try:
            # Load .env file
            load_dotenv()
            
            # Exchange API keys
            exchanges = self.config.get('exchanges', {})
            
            for exchange_name, exchange_config in exchanges.items():
                api_key_env = f"{exchange_name.upper()}_API_KEY"
                secret_env = f"{exchange_name.upper()}_SECRET"
                sandbox_env = f"{exchange_name.upper()}_SANDBOX"
                
                if os.getenv(api_key_env):
                    exchange_config['api_key'] = os.getenv(api_key_env)
                
                if os.getenv(secret_env):
                    exchange_config['secret'] = os.getenv(secret_env)
                
                if os.getenv(sandbox_env):
                    exchange_config['sandbox'] = os.getenv(sandbox_env).lower() == 'true'
                
                # OKX passphrase
                if exchange_name.upper() == 'OKX' and os.getenv('OKX_PASSPHRASE'):
                    exchange_config['passphrase'] = os.getenv('OKX_PASSPHRASE')
            
            # Notification settings
            notifications = self.config.get('notifications', {})
            
            # Telegram
            if os.getenv('TELEGRAM_BOT_TOKEN'):
                notifications.setdefault('telegram', {})['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
            if os.getenv('TELEGRAM_CHAT_ID'):
                notifications.setdefault('telegram', {})['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
            
            # Discord
            if os.getenv('DISCORD_WEBHOOK_URL'):
                notifications.setdefault('discord', {})['webhook_url'] = os.getenv('DISCORD_WEBHOOK_URL')
            
            # Email
            email_config = notifications.setdefault('email', {})
            if os.getenv('EMAIL_SMTP_HOST'):
                email_config['smtp_host'] = os.getenv('EMAIL_SMTP_HOST')
            if os.getenv('EMAIL_SMTP_PORT'):
                email_config['smtp_port'] = int(os.getenv('EMAIL_SMTP_PORT'))
            if os.getenv('EMAIL_FROM'):
                email_config['from_email'] = os.getenv('EMAIL_FROM')
            if os.getenv('EMAIL_PASSWORD'):
                email_config['password'] = os.getenv('EMAIL_PASSWORD')
            if os.getenv('EMAIL_TO'):
                email_config['to_email'] = os.getenv('EMAIL_TO')
            
            # Risk Management
            risk_mgmt = self.config.get('risk_management', {})
            if os.getenv('MAX_PORTFOLIO_RISK'):
                risk_mgmt['max_portfolio_risk'] = float(os.getenv('MAX_PORTFOLIO_RISK'))
            if os.getenv('MAX_DAILY_LOSS'):
                risk_mgmt['max_daily_loss'] = float(os.getenv('MAX_DAILY_LOSS'))
            if os.getenv('MAX_OPEN_POSITIONS'):
                risk_mgmt['max_open_positions'] = int(os.getenv('MAX_OPEN_POSITIONS'))
            
            # AI Settings
            ai_settings = self.config.get('ai_settings', {})
            if os.getenv('AI_CONFIDENCE_THRESHOLD'):
                ai_settings['confidence_threshold'] = float(os.getenv('AI_CONFIDENCE_THRESHOLD'))
            if os.getenv('AI_RETRAIN_FREQUENCY_HOURS'):
                ai_settings['retrain_frequency_hours'] = int(os.getenv('AI_RETRAIN_FREQUENCY_HOURS'))
            
            # Trading Mode
            if os.getenv('TRADING_MODE'):
                self.config['trading_mode'] = os.getenv('TRADING_MODE')
            
            logger.info("✅ Environment variables entegre edildi")
            
        except Exception as e:
            logger.warning(f"⚠️ Environment variable entegrasyon hatası: {e}")
    
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
    
    def update_config(self, section: str, key: str, value: Any) -> None:
        """Konfigürasyonu güncelle"""
        if not self.config:
            raise ValueError("Konfigürasyon henüz yüklenmedi")
        
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        logger.debug(f"📝 Konfigürasyon güncellendi: {section}.{key} = {value}")
    
    async def save_config(self) -> None:
        """Konfigürasyonu dosyaya kaydet"""
        try:
            if not self.config:
                raise ValueError("Kaydedilecek konfigürasyon yok")
            
            # Backup oluştur
            backup_path = self.config_path.with_suffix('.yaml.backup')
            if self.config_path.exists():
                import shutil
                shutil.copy2(self.config_path, backup_path)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"✅ Konfigürasyon kaydedildi: {self.config_path}")
            
        except Exception as e:
            logger.error(f"❌ Konfigürasyon kaydetme hatası: {e}")
            raise
    
    def reload_config(self) -> Dict[str, Any]:
        """Konfigürasyonu yeniden yükle"""
        import asyncio
        return asyncio.run(self.load_config())
    
    def get_exchange_config(self, exchange_name: str) -> Dict[str, Any]:
        """Belirli bir exchange konfigürasyonunu al"""
        exchanges = self.get_section('exchanges')
        if exchange_name not in exchanges:
            raise KeyError(f"Exchange bulunamadı: {exchange_name}")
        return exchanges[exchange_name]
    
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """Belirli bir strateji konfigürasyonunu al"""
        strategies = self.get_section('strategies')
        if strategy_name not in strategies:
            raise KeyError(f"Strateji bulunamadı: {strategy_name}")
        return strategies[strategy_name]