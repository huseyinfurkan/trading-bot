"""
Monitoring System
Sistem performansı ve sağlığını izler
"""

import psutil
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class MonitoringSystem:
    """Sistem izleme ve monitoring"""
    
def __init__(self, performance_config: Dict[str, Any], db_manager, notification_manager):
        """
        Args:
            performance_config: Performans konfigürasyonu
            db_manager: Veritabanı yöneticisi
            notification_manager: Bildirim yöneticisi
        """
        self.config = performance_config
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
        # Performance thresholds
        self.max_cpu_usage = performance_config.get('max_cpu_usage', 80)
        self.max_memory_usage = performance_config.get('max_memory_usage', 4) * 1024  # MB
        self.data_retention_days = performance_config.get('data_retention_days', 90)
        self.cleanup_frequency = performance_config.get('cleanup_frequency', 24)
        
        # Internal state
        self.running = False
        self.monitoring_task = None
        self.last_cleanup = datetime.now()
        
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
            
            logger.info("🛑 Monitoring System durduruldu")
            
    except Exception as e:
            logger.error(f"❌ Monitoring durdurma hatası: {e}")
    
async def check_performance(self) -> Dict[str, Any]:
        """Sistem performansını kontrol et"""
    try:
            # CPU kullanımı
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory kullanımı
            memory_info = psutil.virtual_memory()
            memory_usage_mb = memory_info.used / (1024 * 1024)
            memory_percentage = memory_info.percent
            
            # Disk kullanımı
            disk_info = psutil.disk_usage('/')
            disk_usage_percentage = (disk_info.used / disk_info.total) * 100
            
            # Trading bot specific metrics
            trading_metrics = await self._get_trading_metrics()
            
            metrics = {
                'timestamp': datetime.now(),
                'cpu_usage': cpu_usage,
                'memory_usage_mb': memory_usage_mb,
                'memory_percentage': memory_percentage,
                'disk_usage_percentage': disk_usage_percentage,
                'active_positions': trading_metrics.get('active_positions', 0),
                'total_pnl': trading_metrics.get('total_pnl', 0),
                'daily_pnl': trading_metrics.get('daily_pnl', 0),
                'win_rate': trading_metrics.get('win_rate', 0)
            }
            
            # Performance warnings kontrolü
            await self._check_performance_warnings(metrics)
            
            # Metrics'i logla
        from src.utils.logger_setup import log_system_metrics
            log_system_metrics(metrics)
            
            return metrics
            
    except Exception as e:
            logger.error(f"❌ Performance kontrol hatası: {e}")
            return {}
    
async def _monitoring_loop(self) -> None:
        """Ana monitoring döngüsü"""
    try:
        while self.running:
            try:
                    # Performance kontrolü
                    await self.check_performance()
                    
                    # Cleanup kontrolü
                    await self._check_cleanup_schedule()
                    
                    # Health check
                    await self._health_check()
                    
                    # 60 saniye bekle
                    await asyncio.sleep(60)
                    
            except Exception as e:
                    logger.error(f"❌ Monitoring loop hatası: {e}")
                    await asyncio.sleep(30)
                    
    except asyncio.CancelledError:
            logger.info("🔄 Monitoring loop iptal edildi")
    except Exception as e:
            logger.error(f"❌ Kritik monitoring hatası: {e}")
    
async def _get_trading_metrics(self) -> Dict[str, Any]:
        """Trading metrikleri al"""
    try:
            # Aktif pozisyonlar
            positions = await self.db_manager.get_positions(status='OPEN')
            active_positions = len(positions)
            
            # Total PnL
            total_pnl = sum(pos.get('pnl', 0) for pos in positions)
            
            # Daily performance
            daily_stats = await self.db_manager.get_performance_stats(days=1)
            daily_pnl = daily_stats.get('total_pnl', 0)
            win_rate = daily_stats.get('win_rate', 0)
            
            return {
                'active_positions': active_positions,
                'total_pnl': total_pnl,
                'daily_pnl': daily_pnl,
                'win_rate': win_rate
            }
            
    except Exception as e:
            logger.error(f"❌ Trading metrics hatası: {e}")
            return {}
    
async def _check_performance_warnings(self, metrics: Dict[str, Any]) -> None:
        """Performance uyarılarını kontrol et"""
    try:
            warnings = []
            
            # CPU warning
        if metrics.get('cpu_usage', 0) > self.max_cpu_usage:
                warnings.append(f"High CPU usage: {metrics['cpu_usage']:.1f}%")
            
            # Memory warning
        if metrics.get('memory_usage_mb', 0) > self.max_memory_usage:
                warnings.append(f"High memory usage: {metrics['memory_usage_mb']:.1f}MB")
            
            # Disk warning
        if metrics.get('disk_usage_percentage', 0) > 90:
                warnings.append(f"High disk usage: {metrics['disk_usage_percentage']:.1f}%")
            
            # Trading warnings
        if metrics.get('daily_pnl', 0) < -1000:  # Large daily loss
                warnings.append(f"Large daily loss: {metrics['daily_pnl']:.2f} USDT")
            
            # Send warnings
        if warnings:
                warning_message = "🚨 **PERFORMANCE WARNINGS**\n\n" + "\n".join(f"⚠️ {w}" for w in warnings)
                await self.notification_manager.send_message(warning_message, "warning", "high")
                
    except Exception as e:
            logger.error(f"❌ Performance warning kontrol hatası: {e}")
    
async def _check_cleanup_schedule(self) -> None:
        """Cleanup zamanlamasını kontrol et"""
    try:
            now = datetime.now()
            hours_since_cleanup = (now - self.last_cleanup).total_seconds() / 3600
            
        if hours_since_cleanup >= self.cleanup_frequency:
                await self._perform_cleanup()
                self.last_cleanup = now
                
    except Exception as e:
            logger.error(f"❌ Cleanup schedule kontrol hatası: {e}")
    
async def _perform_cleanup(self) -> None:
        """Temizlik işlemlerini gerçekleştir"""
    try:
            logger.info("🧹 Cleanup işlemi başlatılıyor...")
            
            # Database cleanup
            await self.db_manager.cleanup_old_data()
            
            # Log rotation (loguru handles this automatically)
            
            logger.info("✅ Cleanup işlemi tamamlandı")
            
    except Exception as e:
            logger.error(f"❌ Cleanup işlemi hatası: {e}")
    
async def _health_check(self) -> None:
        """Sistem sağlık kontrolü"""
    try:
            # Database connectivity
        try:
                await self.db_manager.get_performance_stats(days=1)
                db_healthy = True
        except:
                db_healthy = False
            
            # Basic system health
            cpu_ok = psutil.cpu_percent() < 95
            memory_ok = psutil.virtual_memory().percent < 95
            
        if not (db_healthy and cpu_ok and memory_ok):
                health_issues = []
            if not db_healthy:
                    health_issues.append("Database connectivity issue")
            if not cpu_ok:
                    health_issues.append("Critical CPU usage")
            if not memory_ok:
                    health_issues.append("Critical memory usage")
                
                error_message = "🚨 **HEALTH CHECK FAILED**\n\n" + "\n".join(f"❌ {issue}" for issue in health_issues)
                await self.notification_manager.send_error_alert(error_message, "MonitoringSystem")
            
    except Exception as e:
            logger.error(f"❌ Health check hatası: {e}")
    
async def generate_daily_report(self) -> Dict[str, Any]:
        """Günlük rapor oluştur"""
    try:
            # Performance stats
            daily_stats = await self.db_manager.get_performance_stats(days=1)
            
            # System metrics
            current_metrics = await self.check_performance()
            
            # Position summary
            positions = await self.db_manager.get_positions(status='OPEN')
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'trading_performance': daily_stats,
                'system_metrics': current_metrics,
                'active_positions': len(positions),
                'positions_summary': [
                    {
                        'symbol': pos['symbol'],
                        'side': pos['side'],
                        'pnl': pos.get('pnl', 0)
                    } for pos in positions
                ]
            }
            
            return report
            
    except Exception as e:
            logger.error(f"❌ Daily report oluşturma hatası: {e}")
            return {}
    
async def send_daily_summary(self) -> None:
        """Günlük özet gönder"""
    try:
            report = await self.generate_daily_report()
            
        if report:
                await self.notification_manager.send_performance_summary(
                    report.get('trading_performance', {})
                )
                
    except Exception as e:
            logger.error(f"❌ Daily summary gönderme hatası: {e}")
    
def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumunu döndür"""
    try:
            return {
                'monitoring_active': self.running,
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'uptime': datetime.now() - self.last_cleanup if hasattr(self, 'last_cleanup') else timedelta(0)
            }
            
    except Exception as e:
            logger.error(f"❌ System status hatası: {e}")
            return {'monitoring_active': False}