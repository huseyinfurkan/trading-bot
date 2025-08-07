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
        """Kapsamlı konfigürasyon doğrulaması - tip kontrolü ve tutarlılık"""
        logger.info("🔍 Kapsamlı konfigürasyon doğrulaması başlatılıyor...")
        
        # Type validation schema
        validation_schema = {
            'exchanges': {
                'type': dict,
                'required_keys': ['api_key', 'secret'],
                'optional_keys': ['sandbox', 'passphrase']
            },
            'strategies': {
                'type': dict,
                'required_strategies': ['alligator_ma_momentum', 'bollinger_rsi_stochrsi'],
                'strategy_params': {
                    'alligator_ma_momentum': {
                        'risk_per_trade': {'type': float, 'min': 0.001, 'max': 0.05},
                        'leverage': {'type': float, 'min': 1.0, 'max': 5.0},
                        'profit_target': {'type': float, 'min': 0.02, 'max': 0.20},
                        'stop_loss': {'type': float, 'min': 0.01, 'max': 0.10},
                        'max_hold_bars': {'type': int, 'min': 1, 'max': 100}
                    },
                    'bollinger_rsi_stochrsi': {
                        'risk_per_trade': {'type': float, 'min': 0.001, 'max': 0.05},
                        'leverage': {'type': float, 'min': 1.0, 'max': 5.0},
                        'profit_target': {'type': float, 'min': 0.01, 'max': 0.15},
                        'stop_loss': {'type': float, 'min': 0.005, 'max': 0.08},
                        'max_hold_bars': {'type': int, 'min': 1, 'max': 100},
                        'rsi_oversold': {'type': int, 'min': 10, 'max': 40},
                        'rsi_overbought': {'type': int, 'min': 60, 'max': 90}
                    }
                }
            },
            'risk_management': {
                'type': dict,
                'required_params': {
                    'max_daily_loss': {'type': float, 'min': 0.01, 'max': 0.20},
                    'max_portfolio_risk': {'type': float, 'min': 0.01, 'max': 0.30},
                    'max_positions': {'type': int, 'min': 1, 'max': 20}
                }
            },
            'ai': {
                'type': dict,
                'required_params': {
                    'confidence_threshold': {'type': float, 'min': 0.3, 'max': 0.9}
                }
            }
        }
        
        # Validate top-level structure
        for section, schema in validation_schema.items():
            if section not in self.config:
                logger.error(f"❌ Eksik konfigürasyon bölümü: {section}")
                raise ValueError(f"Required config section missing: {section}")
            
            if not isinstance(self.config[section], schema['type']):
                logger.error(f"❌ Hatalı tip: {section} should be {schema['type'].__name__}")
                raise TypeError(f"Config section {section} must be {schema['type'].__name__}")
        
        # Validate strategies in detail
        await self._validate_strategies(validation_schema['strategies'])
        
        # Validate risk management parameters
        await self._validate_risk_parameters(validation_schema['risk_management'])
        
        # Validate AI parameters
        await self._validate_ai_parameters(validation_schema['ai'])
        
        # Check parameter name consistency
        await self._check_parameter_consistency()
        
        logger.success("✅ Kapsamlı konfigürasyon doğrulaması tamamlandı")
    
    async def _validate_strategies(self, schema):
        """Strateji parametrelerini detaylı doğrula"""
        strategies = self.config['strategies']
        
        # Check required strategies exist
        for required_strategy in schema['required_strategies']:
            if required_strategy not in strategies:
                logger.error(f"❌ Gerekli strateji eksik: {required_strategy}")
                raise ValueError(f"Required strategy missing: {required_strategy}")
        
        # Validate each strategy's parameters
        for strategy_name, strategy_config in strategies.items():
            if strategy_name in schema['strategy_params']:
                param_schema = schema['strategy_params'][strategy_name]
                
                for param_name, param_rules in param_schema.items():
                    if param_name in strategy_config:
                        value = strategy_config[param_name]
                        
                        # Type check
                        if not isinstance(value, param_rules['type']):
                            logger.error(f"❌ {strategy_name}.{param_name}: Expected {param_rules['type'].__name__}, got {type(value).__name__}")
                            raise TypeError(f"Parameter {strategy_name}.{param_name} must be {param_rules['type'].__name__}")
                        
                        # Range check
                        if 'min' in param_rules and value < param_rules['min']:
                            logger.error(f"❌ {strategy_name}.{param_name}: {value} < {param_rules['min']}")
                            raise ValueError(f"Parameter {strategy_name}.{param_name} must be >= {param_rules['min']}")
                        
                        if 'max' in param_rules and value > param_rules['max']:
                            logger.error(f"❌ {strategy_name}.{param_name}: {value} > {param_rules['max']}")
                            raise ValueError(f"Parameter {strategy_name}.{param_name} must be <= {param_rules['max']}")
                        
                        logger.debug(f"✅ {strategy_name}.{param_name}: {value} valid")
    
    async def _validate_risk_parameters(self, schema):
        """Risk yönetimi parametrelerini doğrula"""
        risk_config = self.config['risk_management']
        
        for param_name, param_rules in schema['required_params'].items():
            if param_name not in risk_config:
                logger.error(f"❌ Risk parametresi eksik: {param_name}")
                raise ValueError(f"Required risk parameter missing: {param_name}")
            
            value = risk_config[param_name]
            
            # Type and range validation
            if not isinstance(value, param_rules['type']):
                raise TypeError(f"Risk parameter {param_name} must be {param_rules['type'].__name__}")
            
            if 'min' in param_rules and value < param_rules['min']:
                raise ValueError(f"Risk parameter {param_name} must be >= {param_rules['min']}")
            
            if 'max' in param_rules and value > param_rules['max']:
                raise ValueError(f"Risk parameter {param_name} must be <= {param_rules['max']}")
    
    async def _validate_ai_parameters(self, schema):
        """AI parametrelerini doğrula"""
        ai_config = self.config['ai']
        
        for param_name, param_rules in schema['required_params'].items():
            if param_name in ai_config:
                value = ai_config[param_name]
                
                if not isinstance(value, param_rules['type']):
                    raise TypeError(f"AI parameter {param_name} must be {param_rules['type'].__name__}")
                
                if 'min' in param_rules and value < param_rules['min']:
                    raise ValueError(f"AI parameter {param_name} must be >= {param_rules['min']}")
                
                if 'max' in param_rules and value > param_rules['max']:
                    raise ValueError(f"AI parameter {param_name} must be <= {param_rules['max']}")
    
    async def _check_parameter_consistency(self):
        """Parametre isim tutarlılığını kontrol et"""
        strategies = self.config.get('strategies', {})
        
        # Expected strategy names (must match AdaptiveStrategyEngine)
        expected_strategies = ['alligator_ma_momentum', 'bollinger_rsi_stochrsi']
        
        for strategy_name in strategies.keys():
            if strategy_name not in expected_strategies:
                logger.warning(f"⚠️ Bilinmeyen strateji ismi: {strategy_name}")
                logger.warning(f"   Beklenen isimler: {expected_strategies}")
        
        # Check for old parameter names
        deprecated_params = {
            'max_hold_hours': 'max_hold_bars',
            'mean_reversion_adaptive': 'bollinger_rsi_stochrsi',
            'trend_following_adaptive': 'alligator_ma_momentum'
        }
        
        for strategy_config in strategies.values():
            for old_param, new_param in deprecated_params.items():
                if old_param in strategy_config:
                    logger.warning(f"⚠️ Deprecated parameter: {old_param} → use {new_param}")
        
        logger.info("✅ Parametre tutarlılık kontrolü tamamlandı")
    
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
                
                # Debug API key loading
                api_key_value = os.getenv(api_key_env)
                secret_value = os.getenv(secret_env)
                logger.debug(f"🔍 {exchange_name}: {api_key_env}={bool(api_key_value)}, {secret_env}={bool(secret_value)}")
                
                if api_key_value:
                    exchange_config['api_key'] = api_key_value
                    logger.debug(f"✅ {exchange_name} API key loaded")
                
                if secret_value:
                    exchange_config['secret'] = secret_value
                    logger.debug(f"✅ {exchange_name} secret loaded")
                
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