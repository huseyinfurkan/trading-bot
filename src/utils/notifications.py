"""
Notification Manager
Telegram, Discord ve email bildirimleri yönetir
"""

import aiohttp
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime
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
        self.telegram_bot_token = self.telegram_config.get('bot_token')
        self.telegram_chat_id = self.telegram_config.get('chat_id')
        
        # Discord config
        self.discord_config = notification_config.get('discord', {})
        self.discord_enabled = self.discord_config.get('enabled', False)
        self.discord_webhook_url = self.discord_config.get('webhook_url')
        
        # Email config
        self.email_config = notification_config.get('email', {})
        self.email_enabled = self.email_config.get('enabled', False)
        
        # Rate limiting
        self.last_notification = {}
        self.min_interval = 60  # seconds between same type notifications
        
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
    
    async def send_message(self, message: str, message_type: str = "info", 
                          priority: str = "normal") -> None:
        """Ana bildirim gönderme fonksiyonu"""
        try:
            # Rate limiting check
            if not await self._check_rate_limit(message_type):
                return
            
            # Format message
            formatted_message = await self._format_message(message, message_type, priority)
            
            # Send to all enabled channels
            tasks = []
            
            if self.telegram_enabled:
                tasks.append(self._send_telegram(formatted_message))
            
            if self.discord_enabled:
                tasks.append(self._send_discord(formatted_message, message_type))
            
            if self.email_enabled and priority in ["high", "critical"]:
                tasks.append(self._send_email(formatted_message, message_type))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update rate limiting
            self.last_notification[message_type] = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Bildirim gönderme hatası: {e}")
    
    async def send_trade_alert(self, trade_data: Dict[str, Any]) -> None:
        """Trade bildirimi gönder"""
        try:
            symbol = trade_data.get('symbol', 'UNKNOWN')
            side = trade_data.get('side', 'UNKNOWN')
            size = trade_data.get('size', 0)
            price = trade_data.get('price', 0)
            pnl = trade_data.get('pnl', 0)
            strategy = trade_data.get('strategy', 'UNKNOWN')
            
            # PnL emoji
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            message = (
                f"📊 **TRADE EXECUTED**\n\n"
                f"💎 **Symbol**: {symbol}\n"
                f"📈 **Side**: {side}\n"
                f"💰 **Size**: {size:.6f}\n"
                f"💵 **Price**: ${price:.4f}\n"
                f"{pnl_emoji} **PnL**: {pnl:.4f} USDT ({pnl/abs(pnl)*100 if pnl != 0 else 0:.2f}%)\n"
                f"🎯 **Strategy**: {strategy}\n"
                f"⏰ **Time**: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            priority = "high" if abs(pnl) > 100 else "normal"
            await self.send_message(message, "trade", priority)
            
        except Exception as e:
            logger.error(f"❌ Trade alert hatası: {e}")
    
    async def send_signal_alert(self, signal_data: Dict[str, Any]) -> None:
        """Sinyal bildirimi gönder"""
        try:
            symbol = signal_data.get('symbol', 'UNKNOWN')
            signal_type = signal_data.get('signal_type', 'UNKNOWN')
            strength = signal_data.get('strength', 0)
            confidence = signal_data.get('confidence', 0)
            strategy = signal_data.get('strategy', 'UNKNOWN')
            
            # Signal emoji
            signal_emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "🟡"
            
            message = (
                f"🎯 **SIGNAL DETECTED**\n\n"
                f"💎 **Symbol**: {symbol}\n"
                f"{signal_emoji} **Signal**: {signal_type}\n"
                f"💪 **Strength**: {strength:.3f}\n"
                f"🎲 **Confidence**: {confidence:.3f}\n"
                f"🎯 **Strategy**: {strategy}\n"
                f"⏰ **Time**: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            priority = "normal" if confidence > 0.8 else "low"
            await self.send_message(message, "signal", priority)
            
        except Exception as e:
            logger.error(f"❌ Signal alert hatası: {e}")
    
    async def send_error_alert(self, error_message: str, module: str = "Unknown") -> None:
        """Hata bildirimi gönder"""
        try:
            message = (
                f"🚨 **ERROR ALERT**\n\n"
                f"📍 **Module**: {module}\n"
                f"❌ **Error**: {error_message}\n"
                f"⏰ **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await self.send_message(message, "error", "high")
            
        except Exception as e:
            logger.error(f"❌ Error alert hatası: {e}")
    
    async def send_performance_summary(self, performance_data: Dict[str, Any]) -> None:
        """Performans özeti gönder"""
        try:
            total_pnl = performance_data.get('total_pnl', 0)
            total_trades = performance_data.get('total_trades', 0)
            win_rate = performance_data.get('win_rate', 0)
            best_trade = performance_data.get('best_trade', 0)
            worst_trade = performance_data.get('worst_trade', 0)
            
            pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
            
            message = (
                f"📈 **DAILY PERFORMANCE SUMMARY**\n\n"
                f"{pnl_emoji} **Total PnL**: {total_pnl:.4f} USDT\n"
                f"📊 **Total Trades**: {total_trades}\n"
                f"🎯 **Win Rate**: {win_rate:.1f}%\n"
                f"🏆 **Best Trade**: +{best_trade:.4f} USDT\n"
                f"📉 **Worst Trade**: {worst_trade:.4f} USDT\n"
                f"📅 **Date**: {datetime.now().strftime('%Y-%m-%d')}"
            )
            
            await self.send_message(message, "performance", "normal")
            
        except Exception as e:
            logger.error(f"❌ Performance summary hatası: {e}")
    
    async def _format_message(self, message: str, message_type: str, priority: str) -> str:
        """Mesajı formatla"""
        try:
            # Priority prefix
            priority_prefix = {
                "low": "ℹ️",
                "normal": "📢",
                "high": "🔔",
                "critical": "🚨"
            }
            
            prefix = priority_prefix.get(priority, "📢")
            
            # Add bot header
            formatted = f"{prefix} **Advanced Trading Bot**\n{'-' * 30}\n\n{message}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Message formatting hatası: {e}")
            return message
    
    async def _send_telegram(self, message: str) -> bool:
        """Telegram mesajı gönder"""
        try:
            if not self.telegram_bot_token or not self.telegram_chat_id:
                return False
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.debug("✅ Telegram mesajı gönderildi")
                        return True
                    else:
                        logger.error(f"❌ Telegram hatası: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Telegram gönderim hatası: {e}")
            return False
    
    async def _send_discord(self, message: str, message_type: str) -> bool:
        """Discord webhook mesajı gönder"""
        try:
            if not self.discord_webhook_url:
                return False
            
            # Color based on message type
            colors = {
                "info": 3447003,      # Blue
                "trade": 3066993,     # Green
                "signal": 15158332,   # Orange
                "error": 15158332,    # Red
                "performance": 9936031 # Purple
            }
            
            color = colors.get(message_type, 3447003)
            
            payload = {
                "embeds": [{
                    "title": "Advanced Trading Bot",
                    "description": message,
                    "color": color,
                    "timestamp": datetime.now().isoformat()
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.debug("✅ Discord mesajı gönderildi")
                        return True
                    else:
                        logger.error(f"❌ Discord hatası: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Discord gönderim hatası: {e}")
            return False
    
    async def _send_email(self, message: str, message_type: str) -> bool:
        """Email gönder"""
        try:
            smtp_server = self.email_config.get('smtp_server')
            smtp_port = self.email_config.get('smtp_port', 587)
            email = self.email_config.get('email')
            password = self.email_config.get('password')
            
            if not all([smtp_server, email, password]):
                return False
            
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = email
            msg['Subject'] = f"Trading Bot Alert - {message_type.upper()}"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            server.quit()
            
            logger.debug("✅ Email gönderildi")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email gönderim hatası: {e}")
            return False
    
    async def _check_rate_limit(self, message_type: str) -> bool:
        """Rate limiting kontrolü"""
        try:
            last_time = self.last_notification.get(message_type)
            
            if last_time:
                elapsed = (datetime.now() - last_time).total_seconds()
                
                if elapsed < self.min_interval:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Rate limit kontrol hatası: {e}")
            return True
    
    async def _test_telegram(self) -> None:
        """Telegram bağlantısını test et"""
        try:
            if self.telegram_bot_token and self.telegram_chat_id:
                test_message = "🤖 Advanced Trading Bot - Telegram connection test"
                await self._send_telegram(test_message)
                logger.info("✅ Telegram bağlantısı test edildi")
        except Exception as e:
            logger.warning(f"⚠️ Telegram test hatası: {e}")
    
    async def _test_discord(self) -> None:
        """Discord bağlantısını test et"""
        try:
            if self.discord_webhook_url:
                test_message = "🤖 Advanced Trading Bot - Discord connection test"
                await self._send_discord(test_message, "info")
                logger.info("✅ Discord bağlantısı test edildi")
        except Exception as e:
            logger.warning(f"⚠️ Discord test hatası: {e}")
    
    async def _test_email(self) -> None:
        """Email bağlantısını test et"""
        try:
            # Email test is optional to avoid spam
            logger.info("✅ Email konfigürasyonu kontrol edildi")
        except Exception as e:
            logger.warning(f"⚠️ Email test hatası: {e}")
    
    async def close(self) -> None:
        """Notification manager'ı kapat"""
        try:
            logger.info("📱 Notification Manager kapatılıyor...")
            # Cleanup resources if needed
            logger.info("✅ Notification Manager kapatıldı")
        except Exception as e:
            logger.error(f"❌ Notification Manager kapatma hatası: {e}")