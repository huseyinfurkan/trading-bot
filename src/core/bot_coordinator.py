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
    
    def __init__(self, exchange_manager, strategy_engine, position_manager,
                 risk_manager, market_analyzer, ai_signal_filter, db_manager):
        """
        Args:
            exchange_manager: Exchange yöneticisi
            strategy_engine: Strateji motoru
            position_manager: Pozisyon yöneticisi
            risk_manager: Risk yöneticisi
            market_analyzer: Market analizöru
            ai_signal_filter: AI sinyal filtreleme
            db_manager: Veritabanı yöneticisi
        """
        self.exchange_manager = exchange_manager
        self.strategy_engine = strategy_engine
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.market_analyzer = market_analyzer
        self.ai_signal_filter = ai_signal_filter
        self.db_manager = db_manager
        
        # Coordination state
        self.running = False
        self.main_task = None
        
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
                    
                    # Wait before next cycle
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Koordinasyon döngüsü hatası: {e}")
                    await asyncio.sleep(5)
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Koordinasyon döngüsü fatal hatası: {e}")
    
    async def _check_system_health(self) -> None:
        """Sistem sağlığını kontrol et"""
        try:
            # Check active components
            components = {
                'exchange_manager': self.exchange_manager,
                'strategy_engine': self.strategy_engine,
                'position_manager': self.position_manager,
                'risk_manager': self.risk_manager,
                'market_analyzer': self.market_analyzer,
                'ai_signal_filter': self.ai_signal_filter,
                'db_manager': self.db_manager
            }
            
            for name, component in components.items():
                if component is None:
                    logger.warning(f"⚠️ {name} is None")
                    
        except Exception as e:
            logger.error(f"❌ System health check error: {e}")
    
    async def _monitor_risk_levels(self) -> None:
        """Risk seviyelerini izle"""
        try:
            # Get current risk metrics
            risk_metrics = self.risk_manager.get_risk_metrics()
            
            # Check portfolio risk
            portfolio_risk = risk_metrics.get('current_portfolio_risk', 0)
            max_risk = risk_metrics.get('max_portfolio_risk', 0.02)
            
            if portfolio_risk > max_risk * 0.8:  # 80% of max risk
                logger.warning(f"⚠️ High portfolio risk: {portfolio_risk:.2%}")
                
        except Exception as e:
            logger.error(f"❌ Risk monitoring error: {e}")
    
    async def _track_performance(self) -> None:
        """Performans takibi"""
        try:
            # Get open positions
            open_positions = await self.position_manager.get_open_positions()
            position_count = len(open_positions)
            
            if position_count > 0:
                logger.debug(f"📊 Active positions: {position_count}")
                
        except Exception as e:
            logger.error(f"❌ Performance tracking error: {e}")
    
    async def _perform_maintenance(self) -> None:
        """Düzenli bakım işlemleri"""
        try:
            # Clean old data periodically
            current_time = datetime.now()
            
            # Daily cleanup
            if hasattr(self, '_last_cleanup'):
                time_diff = current_time - self._last_cleanup
                if time_diff > timedelta(hours=24):
                    await self.db_manager.cleanup_old_data()
                    self._last_cleanup = current_time
            else:
                self._last_cleanup = current_time
                
        except Exception as e:
            logger.error(f"❌ Maintenance error: {e}")
    
    async def run(self):
        """Run the coordinator"""
        await self.start()