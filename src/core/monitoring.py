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