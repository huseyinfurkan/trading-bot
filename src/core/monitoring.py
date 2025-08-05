"""
System Monitoring
Performans ve sistem durumu izleme
"""

import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger


class MonitoringSystem:
    """Sistem ve performans monitoring"""
    
    def __init__(self, monitoring_config: Dict[str, Any], db_manager, notification_manager):
        """
        Args:
            monitoring_config: Monitoring konfigürasyonu
            db_manager: Veritabanı yöneticisi
            notification_manager: Bildirim yöneticisi
        """
        self.config = monitoring_config
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
        # Monitoring parameters
        self.check_interval = monitoring_config.get('check_interval', 60)
        self.cpu_threshold = monitoring_config.get('cpu_threshold', 80)
        self.memory_threshold = monitoring_config.get('memory_threshold', 80)
        self.disk_threshold = monitoring_config.get('disk_threshold', 90)
        
        # System state
        self.running = False
        self.monitoring_task = None
        self.last_cleanup = datetime.now()
        
        logger.info("📊 Monitoring System initialized")
    
    async def start(self) -> None:
        """Monitoring'i başlat"""
        try:
            self.running = True
            logger.info("📊 Monitoring System başlatıldı")
            
            # Monitoring task'ını başlat
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
        except Exception as e:
            logger.error(f"❌ Monitoring başlatma hatası: {e}")
            raise
    
    async def stop(self) -> None:
        """Monitoring'i durdur"""
        try:
            self.running = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("📊 Monitoring System durduruldu")
            
        except Exception as e:
            logger.error(f"❌ Monitoring durdurma hatası: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Ana monitoring döngüsü"""
        try:
            while self.running:
                try:
                    # System health check
                    await self._check_system_health()
                    
                    # Performance metrics
                    await self.check_performance()
                    
                    # Sleep for check interval
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"❌ Monitoring loop hatası: {e}")
                    await asyncio.sleep(30)  # Error recovery sleep
                    
        except Exception as e:
            logger.error(f"❌ Monitoring loop fatal hatası: {e}")
    
    async def _check_system_health(self) -> None:
        """Sistem sağlığını kontrol et"""
        try:
            # CPU usage check
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage > self.cpu_threshold:
                await self._send_alert(f"⚠️ High CPU usage: {cpu_usage:.1f}%")
            
            # Memory usage check
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            if memory_usage > self.memory_threshold:
                await self._send_alert(f"⚠️ High memory usage: {memory_usage:.1f}%")
            
            # Disk usage check
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            if disk_usage > self.disk_threshold:
                await self._send_alert(f"⚠️ High disk usage: {disk_usage:.1f}%")
            
            logger.debug(f"💻 System: CPU {cpu_usage:.1f}% | Memory {memory_usage:.1f}% | Disk {disk_usage:.1f}%")
            
        except Exception as e:
            logger.error(f"❌ System health check hatası: {e}")
    
    async def check_performance(self) -> Dict[str, Any]:
        """Performance metriklerini kontrol et"""
        try:
            # Get system metrics
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get trading metrics from database
            trading_metrics = await self._get_trading_metrics()
            
            performance = {
                'timestamp': datetime.now(),
                'system': {
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory.percent,
                    'memory_total': memory.total,
                    'disk_usage': (disk.used / disk.total) * 100,
                    'disk_free': disk.free
                },
                'trading': trading_metrics
            }
            
            # Log to performance logger if available
            try:
                from src.utils.logger_setup import log_system_metrics
                log_system_metrics({
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory.percent,
                    'active_positions': trading_metrics.get('active_positions', 0),
                    'total_pnl': trading_metrics.get('total_pnl', 0)
                })
            except ImportError:
                pass
            
            return performance
            
        except Exception as e:
            logger.error(f"❌ Performance check hatası: {e}")
            return {}
    
    async def _get_trading_metrics(self) -> Dict[str, Any]:
        """Trading metriklerini al"""
        try:
            metrics = {
                'active_positions': 0,
                'total_pnl': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            }
            
            if self.db_manager:
                # Get active positions count
                positions = await self.db_manager.get_positions()
                active_positions = [p for p in positions if p.get('status') == 'open']
                metrics['active_positions'] = len(active_positions)
                
                # Calculate total PnL
                total_pnl = sum(p.get('pnl', 0) for p in active_positions)
                metrics['total_pnl'] = total_pnl
                
                # Get trade statistics
                trades = await self.db_manager.get_trades()
                metrics['total_trades'] = len(trades)
                
                if trades:
                    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
                    metrics['win_rate'] = len(winning_trades) / len(trades) * 100
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Trading metrics hatası: {e}")
            return {
                'active_positions': 0,
                'total_pnl': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            }
    
    async def _send_alert(self, message: str) -> None:
        """Alert gönder"""
        try:
            if self.notification_manager:
                await self.notification_manager.send_message(message, "alert", "high")
            
            logger.warning(message)
            
        except Exception as e:
            logger.error(f"❌ Alert gönderme hatası: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumunu al"""
        try:
            status = {
                'running': self.running,
                'uptime': datetime.now() - self.last_cleanup,
                'last_check': datetime.now(),
                'health': 'healthy'
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ System status hatası: {e}")
            return {'running': False, 'health': 'error'}