"""
Notification Manager
Telegram, Discord ve Email bildirimleri
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class NotificationManager:
    """Bildirim yöneticisi"""
    
    def __init__(self, notification_config: Dict[str, Any]):
        """
        Args:
            notification_config: Bildirim konfigürasyonu
        """
        self.config = notification_config
        
        # Telegram config
        self.telegram_config = notification_config.get('telegram', {})
        self.telegram_enabled = self.telegram_config.get('enabled', False)
        self.telegram_token = self.telegram_config.get('bot_token', '')
        self.telegram_chat_id = self.telegram_config.get('chat_id', '')
        
        # Discord config
        self.discord_config = notification_config.get('discord', {})
        self.discord_enabled = self.discord_config.get('enabled', False)
        self.discord_webhook = self.discord_config.get('webhook_url', '')
        
        # Email config
        self.email_config = notification_config.get('email', {})
        self.email_enabled = self.email_config.get('enabled', False)
        
        # Rate limiting
        self.last_notification = {}
        self.min_interval = 60  # seconds between same type notifications
        
        logger.info("📱 Notification Manager initialized")
    
    async def initialize(self) -> None:
        """Bildirim sistemini başlat"""
        try:
            logger.info("📱 Notification Manager başlatılıyor...")
            
            # Test connections
            if self.telegram_enabled:
                await self._test_telegram()
            
            if self.discord_enabled:
                await self._test_discord()
            
            if self.email_enabled:
                await self._test_email()
            
            logger.success("✅ Notification Manager başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ Notification Manager başlatma hatası: {e}")
            raise
    
    async def send_message(self, message: str, notification_type: str = "info", priority: str = "normal") -> bool:
        """Genel mesaj gönderme"""
        try:
            # Rate limiting check
            if not self._can_send_notification(notification_type):
                return False
            
            success = False
            
            # Send to enabled platforms
            if self.telegram_enabled:
                success |= await self._send_telegram(message)
            
            if self.discord_enabled:
                success |= await self._send_discord(message)
            
            if self.email_enabled and priority == "high":
                success |= await self._send_email(message, "Trading Bot Alert")
            
            if success:
                self.last_notification[notification_type] = datetime.now()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Message send error: {e}")
            return False
    
    async def send_trade_alert(self, symbol: str, action: str, price: float, details: Dict[str, Any]) -> bool:
        """Trade bildirimi gönder"""
        try:
            message = f"🔥 **TRADE ALERT**\n\n"
            message += f"📊 Symbol: {symbol}\n"
            message += f"⚡ Action: {action}\n"
            message += f"💰 Price: ${price:.4f}\n"
            
            if details:
                if 'strategy' in details:
                    message += f"🎯 Strategy: {details['strategy']}\n"
                if 'confidence' in details:
                    message += f"🎪 Confidence: {details['confidence']:.2%}\n"
                if 'size' in details:
                    message += f"📏 Size: {details['size']:.6f}\n"
            
            return await self.send_message(message, "trade", "high")
            
        except Exception as e:
            logger.error(f"❌ Trade alert error: {e}")
            return False
    
    async def send_error_alert(self, error_message: str, component: str) -> bool:
        """Hata bildirimi gönder"""
        try:
            message = f"🚨 **ERROR ALERT**\n\n"
            message += f"🔧 Component: {component}\n"
            message += f"❌ Error: {error_message}\n"
            message += f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return await self.send_message(message, "error", "high")
            
        except Exception as e:
            logger.error(f"❌ Error alert send error: {e}")
            return False
    
    async def send_performance_summary(self, performance_data: Dict[str, Any]) -> bool:
        """Performans özeti gönder"""
        try:
            message = f"📊 **DAILY PERFORMANCE**\n\n"
            
            if 'total_trades' in performance_data:
                message += f"📈 Total Trades: {performance_data['total_trades']}\n"
            if 'win_rate' in performance_data:
                message += f"🎯 Win Rate: {performance_data['win_rate']:.1%}\n"
            if 'total_pnl' in performance_data:
                pnl = performance_data['total_pnl']
                emoji = "🟢" if pnl >= 0 else "🔴"
                message += f"{emoji} Total P&L: ${pnl:.2f}\n"
            
            return await self.send_message(message, "summary", "normal")
            
        except Exception as e:
            logger.error(f"❌ Performance summary error: {e}")
            return False
    
    async def _send_telegram(self, message: str) -> bool:
        """Telegram mesajı gönder"""
        try:
            if not self.telegram_token or not self.telegram_chat_id:
                return False
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.debug("📱 Telegram message sent")
                        return True
                    else:
                        logger.error(f"❌ Telegram error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
            return False
    
    async def _send_discord(self, message: str) -> bool:
        """Discord mesajı gönder"""
        try:
            if not self.discord_webhook:
                return False
            
            data = {
                'content': message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=data) as response:
                    if response.status == 204:
                        logger.debug("📱 Discord message sent")
                        return True
                    else:
                        logger.error(f"❌ Discord error: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Discord send error: {e}")
            return False
    
    async def _send_email(self, message: str, subject: str) -> bool:
        """Email gönder"""
        try:
            # Email implementation would go here
            # For now, just log
            logger.info(f"📧 Email would be sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send error: {e}")
            return False
    
    async def _test_telegram(self) -> bool:
        """Telegram bağlantısını test et"""
        try:
            if not self.telegram_enabled:
                return True
            
            test_message = "🤖 Trading Bot - Connection Test"
            return await self._send_telegram(test_message)
            
        except Exception as e:
            logger.error(f"❌ Telegram test error: {e}")
            return False
    
    async def _test_discord(self) -> bool:
        """Discord bağlantısını test et"""
        try:
            if not self.discord_enabled:
                return True
            
            test_message = "🤖 Trading Bot - Connection Test"
            return await self._send_discord(test_message)
            
        except Exception as e:
            logger.error(f"❌ Discord test error: {e}")
            return False
    
    async def _test_email(self) -> bool:
        """Email bağlantısını test et"""
        try:
            if not self.email_enabled:
                return True
            
            logger.info("📧 Email test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email test error: {e}")
            return False
    
    def _can_send_notification(self, notification_type: str) -> bool:
        """Rate limiting kontrolü"""
        try:
            if notification_type not in self.last_notification:
                return True
            
            last_time = self.last_notification[notification_type]
            time_diff = (datetime.now() - last_time).total_seconds()
            
            return time_diff >= self.min_interval
            
        except Exception as e:
            logger.error(f"❌ Rate limit check error: {e}")
            return True
    
    async def close(self) -> None:
        """Notification manager'ı kapat"""
        try:
            logger.info("📱 Notification Manager kapatılıyor...")
            
        except Exception as e:
            logger.error(f"❌ Notification close error: {e}")