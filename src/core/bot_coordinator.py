"""
Bot Coordinator
Ana trading bot koordinasyonu
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger


class BotCoordinator:
    """Bot koordinasyon sistemi"""
    
    def __init__(self, config: Dict[str, Any], exchange_manager, position_manager,
                 risk_manager, monitoring_system, db_manager):
        """
        Args:
            config: Bot konfigürasyonu
            exchange_manager: Exchange yöneticisi
            position_manager: Pozisyon yöneticisi
            risk_manager: Risk yöneticisi
            monitoring_system: Monitoring sistemi
            db_manager: Veritabanı yöneticisi
        """
        self.config = config
        self.exchange_manager = exchange_manager
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.monitoring_system = monitoring_system
        self.db_manager = db_manager
        
        # Coordination state
        self.running = False
        self.main_task = None
        
        # Performance tracking
        self.start_time = datetime.now()
        self.health_checks = 0
        self.risk_checks = 0
        self.maintenance_runs = 0
        self.performance_metrics = {
            'error_counts': [],
            'system_health': [],
            'risk_levels': []
        }
        
        logger.info("🎯 Bot Coordinator initialized")
    
    async def start(self) -> None:
        """Bot koordinasyonunu başlat"""
        try:
            self.running = True
            logger.info("🎯 Bot Coordinator başlatıldı")
            
            # Ana koordinasyon task'ını başlat
            self.main_task = asyncio.create_task(self._coordination_loop())
            
        except Exception as e:
            logger.error(f"❌ Bot Coordinator başlatma hatası: {e}")
            raise
    
    async def stop(self) -> None:
        """Bot koordinasyonunu durdur"""
        try:
            self.running = False
            
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                
                try:
                    await self.main_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("🛑 Bot Coordinator durduruldu")
            
        except Exception as e:
            logger.error(f"❌ Bot Coordinator durdurma hatası: {e}")
    
    async def _coordination_loop(self) -> None:
        """Ana koordinasyon döngüsü"""
        try:
            logger.info("🔄 Bot koordinasyon döngüsü başlatıldı")
            
            while self.running:
                try:
                    # System health check
                    await self._check_system_health()
                    
                    # Risk monitoring
                    await self._monitor_risk_levels()
                    
                    # Performance tracking
                    await self._track_performance()
                    
                    # Regular maintenance
                    await self._perform_maintenance()
                    
                    # Dynamic wait based on system load and error frequency
                    wait_time = await self._get_dynamic_wait_time()
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    logger.error(f"❌ Koordinasyon döngüsü hatası: {e}")
                    # Dynamic error wait time
                    error_wait_time = await self._get_dynamic_error_wait_time()
                    await asyncio.sleep(error_wait_time)
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Koordinasyon döngüsü fatal hatası: {e}")
    
    async def _check_system_health(self) -> None:
        """Sistem sağlık kontrolü"""
        try:
            self.health_checks += 1
            
            # Check exchange connectivity
            if hasattr(self.exchange_manager, 'get_exchange_status'):
                exchange_status = await self.exchange_manager.get_exchange_status()
                if not exchange_status.get('connected', False):
                    logger.warning("⚠️ Exchange bağlantısı kesildi")
            else:
                # Fallback check
                logger.debug("📡 Exchange status check not available")
            
            # Check database connectivity
            if hasattr(self.db_manager, 'check_connection_health'):
                db_status = await self.db_manager.check_connection_health()
                if not db_status:
                    logger.warning("⚠️ Database bağlantısı sorunlu")
            else:
                # Fallback check
                logger.debug("🗄️ Database health check not available")
            
            # Check monitoring system
            if hasattr(self.monitoring_system, 'get_system_health'):
                health_status = await self.monitoring_system.get_system_health()
                if not health_status.get('healthy', True):
                    logger.warning(f"⚠️ Sistem sağlık sorunları: {health_status.get('issues', [])}")
            
            # Log periodic health summary
            if self.health_checks % 20 == 0:  # Every 10 minutes
                logger.info(f"📊 Sistem sağlık kontrolü: {self.health_checks} kez çalıştı")
                
        except Exception as e:
            logger.error(f"❌ Sistem sağlık kontrolü hatası: {e}")
    
    async def _monitor_risk_levels(self) -> None:
        """Risk seviyelerini izle"""
        try:
            self.risk_checks += 1
            
            # Get current risk status
            if hasattr(self.risk_manager, 'get_risk_status'):
                risk_status = await self.risk_manager.get_risk_status()
            else:
                # Fallback to get_current_risk_settings
                risk_status = self.risk_manager.get_current_risk_settings()
            
            # Check portfolio risk
            portfolio_risk = risk_status.get('portfolio_risk', 0)
            if portfolio_risk > 0.8:  # 80% portfolio risk
                logger.warning(f"⚠️ Yüksek portföy riski: {portfolio_risk:.2%}")
            
            # Check daily loss
            daily_loss = risk_status.get('daily_loss', 0)
            if daily_loss > 0.05:  # 5% daily loss
                logger.warning(f"⚠️ Günlük kayıp limiti aşıldı: {daily_loss:.2%}")
            
            # Check open positions
            open_positions = risk_status.get('open_positions', 0)
            max_positions = self.config.get('trading', {}).get('risk_management', {}).get('max_open_positions', 10)
            if open_positions >= max_positions:
                logger.warning(f"⚠️ Maksimum açık pozisyon sayısına ulaşıldı: {open_positions}")
            
        except Exception as e:
            logger.error(f"❌ Risk izleme hatası: {e}")
    
    async def _track_performance(self) -> None:
        """Performans takibi"""
        try:
            # Get trading performance
            if hasattr(self.position_manager, 'get_performance_summary'):
                performance = await self.position_manager.get_performance_summary()
                
                # Log performance metrics
                total_trades = performance.get('total_trades', 0)
                win_rate = performance.get('win_rate', 0)
                total_pnl = performance.get('total_pnl', 0)
                
                if total_trades > 0 and self.risk_checks % 40 == 0:  # Every 20 minutes
                    logger.info(f"📈 Performans: {total_trades} işlem, {win_rate:.1%} kazanma oranı, {total_pnl:.2f} PnL")
            
        except Exception as e:
            logger.error(f"❌ Performans takibi hatası: {e}")
    
    async def _perform_maintenance(self) -> None:
        """Düzenli bakım işlemleri"""
        try:
            self.maintenance_runs += 1
            
            # Clean old data
            if hasattr(self.db_manager, 'cleanup_old_data'):
                await self.db_manager.cleanup_old_data()
            
            # Update trailing stops
            if hasattr(self.position_manager, 'update_trailing_stops'):
                await self.position_manager.update_trailing_stops()
            
            # Log maintenance summary
            if self.maintenance_runs % 60 == 0:  # Every 30 minutes
                uptime = datetime.now() - self.start_time
                logger.info(f"🔧 Bakım: {self.maintenance_runs} kez çalıştı, Uptime: {uptime}")
            
        except Exception as e:
            logger.error(f"❌ Bakım hatası: {e}")
    
    async def _get_dynamic_wait_time(self) -> int:
        """Get dynamic wait time based on system load and performance"""
        try:
            import psutil
            
            # Base wait time
            base_wait = 30
            
            # Get current system load
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Adjust wait time based on system load
            if cpu_percent > 80:
                # High load - increase wait time to reduce overhead
                return min(60, base_wait * 2)
            elif cpu_percent < 30:
                # Low load - decrease wait time for more frequent checks
                return max(15, base_wait // 2)
            elif memory.percent > 80:
                # High memory usage - increase wait time
                return min(45, base_wait + 15)
            else:
                return base_wait
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic wait time: {e}")
            return 30
    
    async def _get_dynamic_error_wait_time(self) -> int:
        """Get dynamic error wait time based on error frequency"""
        try:
            # Base error wait time
            base_error_wait = 5
            
            # Check recent error frequency
            recent_errors = len([e for e in self.performance_metrics.get('error_counts', {}) 
                               if (datetime.now() - e.get('timestamp', datetime.now())).total_seconds() < 300])  # Last 5 minutes
            
            if recent_errors > 5:
                # High error frequency - increase wait time
                return min(15, base_error_wait * 3)
            elif recent_errors < 2:
                # Low error frequency - decrease wait time
                return max(2, base_error_wait // 2)
            else:
                return base_error_wait
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic error wait time: {e}")
            return 5
    
    async def run(self):
        """Bot koordinasyonunu çalıştır"""
        try:
            await self.start()
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Bot koordinasyon çalıştırma hatası: {e}")
        finally:
            await self.stop()