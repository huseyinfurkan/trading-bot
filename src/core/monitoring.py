"""
Enhanced Monitoring System
Comprehensive system health monitoring and alerting
"""

import asyncio
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json


class MonitoringSystem:
    """Enhanced monitoring system with health checks and alerting"""
    
    def __init__(self, config: Dict[str, Any], db_manager, notification_manager):
        """
        Args:
            config: Monitoring konfigürasyonu
            db_manager: Veritabanı yöneticisi
            notification_manager: Bildirim yöneticisi
        """
        self.config = config
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
        # Dynamic system thresholds based on system performance
        self.cpu_threshold = await self._get_dynamic_cpu_threshold(config)
        self.memory_threshold = await self._get_dynamic_memory_threshold(config)
        self.disk_threshold = await self._get_dynamic_disk_threshold(config)
        
        # Performance tracking
        self.performance_metrics = {
            'system_health': [],
            'trading_performance': [],
            'error_counts': {},
            'last_alert_time': {}
        }
        
        # Dynamic alert cooldown based on error frequency
        self.alert_cooldown = await self._get_dynamic_alert_cooldown(config)
        
        # Dynamic health check intervals based on system load
        self.system_check_interval = await self._get_dynamic_check_interval(config, 'system')
        self.performance_check_interval = await self._get_dynamic_check_interval(config, 'performance')
        self.error_check_interval = await self._get_dynamic_check_interval(config, 'error')
        
        logger.info("🔍 Enhanced Monitoring System initialized")
    
    async def start_monitoring(self):
        """Monitoring sistemini başlat"""
        try:
            logger.info("🚀 Starting comprehensive monitoring system...")
            
            # Start monitoring tasks
            tasks = [
                asyncio.create_task(self._system_health_monitor()),
                asyncio.create_task(self._trading_performance_monitor()),
                asyncio.create_task(self._error_monitor()),
                asyncio.create_task(self._database_health_monitor()),
                asyncio.create_task(self._api_health_monitor())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"❌ Monitoring start error: {e}")
    
    async def _system_health_monitor(self):
        """Sistem sağlığı izleme"""
        while True:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                
                # Network I/O
                network = psutil.net_io_counters()
                
                # System load (Linux only)
                try:
                    load_avg = psutil.getloadavg()
                except:
                    load_avg = (0, 0, 0)
                
                # Check thresholds and alert
                alerts = []
                
                if cpu_percent > self.cpu_threshold:
                    alerts.append(f"🚨 High CPU usage: {cpu_percent:.1f}%")
                
                if memory_percent > self.memory_threshold:
                    alerts.append(f"🚨 High memory usage: {memory_percent:.1f}%")
                
                if disk_percent > self.disk_threshold:
                    alerts.append(f"🚨 High disk usage: {disk_percent:.1f}%")
                
                # Store metrics
                self.performance_metrics['system_health'].append({
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'load_avg': load_avg,
                    'network_bytes_sent': network.bytes_sent,
                    'network_bytes_recv': network.bytes_recv
                })
                
                # Keep only last 100 entries
                if len(self.performance_metrics['system_health']) > 100:
                    self.performance_metrics['system_health'] = self.performance_metrics['system_health'][-100:]
                
                # Send alerts if any
                if alerts:
                    await self._send_alert("System Health Alert", "\n".join(alerts))
                
                # Log metrics every 5 minutes
                if len(self.performance_metrics['system_health']) % 5 == 0:
                    logger.info(f"📊 System Health: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%, Disk {disk_percent:.1f}%")
                
                await asyncio.sleep(self.system_check_interval)
                
            except Exception as e:
                logger.error(f"❌ System health monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _trading_performance_monitor(self):
        """Trading performans izleme"""
        while True:
            try:
                # Get recent trades
                recent_trades = await self.db_manager.get_trades(limit=50)
                
                if recent_trades:
                    # Calculate performance metrics
                    total_trades = len(recent_trades)
                    winning_trades = len([t for t in recent_trades if t.get('pnl', 0) > 0])
                    losing_trades = len([t for t in recent_trades if t.get('pnl', 0) < 0])
                    
                    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
                    
                    total_pnl = sum(t.get('pnl', 0) for t in recent_trades)
                    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
                    
                    # Calculate drawdown
                    cumulative_pnl = []
                    running_total = 0
                    for trade in recent_trades:
                        running_total += trade.get('pnl', 0)
                        cumulative_pnl.append(running_total)
                    
                    if cumulative_pnl:
                        max_drawdown = min(cumulative_pnl) - max(cumulative_pnl)
                    else:
                        max_drawdown = 0
                    
                    # Store metrics
                    self.performance_metrics['trading_performance'].append({
                        'timestamp': datetime.now(),
                        'total_trades': total_trades,
                        'winning_trades': winning_trades,
                        'losing_trades': losing_trades,
                        'win_rate': win_rate,
                        'total_pnl': total_pnl,
                        'avg_pnl': avg_pnl,
                        'max_drawdown': max_drawdown
                    })
                    
                    # Keep only last 50 entries
                    if len(self.performance_metrics['trading_performance']) > 50:
                        self.performance_metrics['trading_performance'] = self.performance_metrics['trading_performance'][-50:]
                    
                    # Check for performance alerts
                    alerts = []
                    
                    if win_rate < 40:  # Low win rate
                        alerts.append(f"📉 Low win rate: {win_rate:.1f}%")
                    
                    if total_pnl < -100:  # Significant losses
                        alerts.append(f"📉 Significant losses: ${total_pnl:.2f}")
                    
                    if max_drawdown < -50:  # High drawdown
                        alerts.append(f"📉 High drawdown: ${max_drawdown:.2f}")
                    
                    # Send alerts if any
                    if alerts:
                        await self._send_alert("Trading Performance Alert", "\n".join(alerts))
                    
                    # Log performance every 10 minutes
                    if len(self.performance_metrics['trading_performance']) % 2 == 0:
                        logger.info(f"📈 Trading Performance: Win Rate {win_rate:.1f}%, PnL ${total_pnl:.2f}, Drawdown ${max_drawdown:.2f}")
                
                await asyncio.sleep(self.performance_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Trading performance monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _error_monitor(self):
        """Hata izleme"""
        while True:
            try:
                # Get recent system logs
                recent_logs = await self.db_manager.execute_with_retry(
                    "SELECT level, message, timestamp FROM system_logs WHERE timestamp > datetime('now', '-1 hour') ORDER BY timestamp DESC LIMIT 100"
                )
                
                if recent_logs:
                    # Count errors by type
                    error_counts = {}
                    for log in recent_logs:
                        level = log[0]
                        if level in ['ERROR', 'CRITICAL']:
                            # Extract error type from message
                            message = log[1]
                            error_type = self._extract_error_type(message)
                            error_counts[error_type] = error_counts.get(error_type, 0) + 1
                    
                    # Check for error thresholds
                    alerts = []
                    for error_type, count in error_counts.items():
                        if count > 5:  # More than 5 errors of same type in 1 hour
                            alerts.append(f"🚨 High {error_type} errors: {count} in last hour")
                    
                    # Send alerts if any
                    if alerts:
                        await self._send_alert("Error Alert", "\n".join(alerts))
                
                await asyncio.sleep(self.error_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _database_health_monitor(self):
        """Veritabanı sağlığı izleme"""
        while True:
            try:
                # Check database connection
                is_healthy = await self.db_manager.check_connection_health()
                
                if not is_healthy:
                    await self._send_alert("Database Health Alert", "🚨 Database connection issues detected")
                
                # Check database size
                try:
                    db_size = await self.db_manager.execute_with_retry(
                        "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
                    )
                    if db_size and db_size[0][0] > 100 * 1024 * 1024:  # 100MB
                        await self._send_alert("Database Size Alert", "📊 Database size exceeds 100MB")
                except:
                    pass
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ Database health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _api_health_monitor(self):
        """API sağlığı izleme"""
        while True:
            try:
                # This would check exchange API health
                # For now, just log that it's running
                logger.debug("🔍 API health check running")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"❌ API health monitor error: {e}")
                await asyncio.sleep(60)
    
    def _extract_error_type(self, message: str) -> str:
        """Hata mesajından hata tipini çıkar"""
        message_lower = message.lower()
        
        if 'rate limit' in message_lower:
            return 'Rate Limit'
        elif 'network' in message_lower or 'connection' in message_lower:
            return 'Network'
        elif 'database' in message_lower or 'sql' in message_lower:
            return 'Database'
        elif 'api' in message_lower:
            return 'API'
        elif 'authentication' in message_lower or 'auth' in message_lower:
            return 'Authentication'
        else:
            return 'General'
    
    async def _send_alert(self, title: str, message: str):
        """Alert gönder"""
        try:
            # Check cooldown
            alert_key = f"{title}_{message[:50]}"
            now = time.time()
            
            if alert_key in self.performance_metrics['last_alert_time']:
                time_since_last = now - self.performance_metrics['last_alert_time'][alert_key]
                if time_since_last < self.alert_cooldown:
                    return  # Still in cooldown
            
            # Update last alert time
            self.performance_metrics['last_alert_time'][alert_key] = now
            
            # Send notification
            full_message = f"🚨 {title}\n\n{message}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if self.notification_manager:
                await self.notification_manager.send_message(full_message)
            
            logger.warning(f"🚨 Alert sent: {title}")
            
        except Exception as e:
            logger.error(f"❌ Alert sending error: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumunu döndür"""
        try:
            # Current system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Recent performance
            recent_performance = self.performance_metrics['trading_performance'][-1] if self.performance_metrics['trading_performance'] else {}
            
            # Error counts
            error_summary = {}
            for error_type, count in self.performance_metrics['error_counts'].items():
                error_summary[error_type] = count
            
            return {
                'system_health': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': (disk.used / disk.total) * 100,
                    'status': 'healthy' if cpu_percent < self.cpu_threshold and memory.percent < self.memory_threshold else 'warning'
                },
                'trading_performance': recent_performance,
                'error_summary': error_summary,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ System status error: {e}")
            return {'error': str(e)}
    
    async def _get_dynamic_cpu_threshold(self, config: Dict[str, Any]) -> int:
        """Get dynamic CPU threshold based on system performance"""
        try:
            # Get current CPU usage to adjust threshold
            current_cpu = psutil.cpu_percent(interval=1)
            base_threshold = config.get('cpu_threshold', 80)
            
            # Adjust threshold based on current load
            if current_cpu > 70:
                # High load - increase threshold to avoid false alarms
                return min(95, base_threshold + 10)
            elif current_cpu < 30:
                # Low load - decrease threshold for better monitoring
                return max(60, base_threshold - 10)
            else:
                return base_threshold
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic CPU threshold: {e}")
            return config.get('cpu_threshold', 80)
    
    async def _get_dynamic_memory_threshold(self, config: Dict[str, Any]) -> int:
        """Get dynamic memory threshold based on system memory"""
        try:
            memory = psutil.virtual_memory()
            base_threshold = config.get('memory_threshold', 80)
            
            # Adjust based on available memory
            if memory.available < memory.total * 0.1:  # Less than 10% available
                return min(95, base_threshold + 10)
            elif memory.available > memory.total * 0.5:  # More than 50% available
                return max(60, base_threshold - 10)
            else:
                return base_threshold
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic memory threshold: {e}")
            return config.get('memory_threshold', 80)
    
    async def _get_dynamic_disk_threshold(self, config: Dict[str, Any]) -> int:
        """Get dynamic disk threshold based on disk usage"""
        try:
            disk = psutil.disk_usage('/')
            base_threshold = config.get('disk_threshold', 90)
            
            # Adjust based on disk usage
            usage_percent = (disk.used / disk.total) * 100
            if usage_percent > 85:
                return min(98, base_threshold + 5)
            elif usage_percent < 50:
                return max(80, base_threshold - 10)
            else:
                return base_threshold
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic disk threshold: {e}")
            return config.get('disk_threshold', 90)
    
    async def _get_dynamic_alert_cooldown(self, config: Dict[str, Any]) -> int:
        """Get dynamic alert cooldown based on error frequency"""
        try:
            base_cooldown = config.get('alert_cooldown', 300)
            
            # Check recent error frequency
            recent_errors = len([e for e in self.performance_metrics.get('error_counts', {}) 
                               if time.time() - e.get('timestamp', 0) < 3600])  # Last hour
            
            if recent_errors > 10:
                # High error frequency - increase cooldown
                return min(600, base_cooldown * 2)
            elif recent_errors < 2:
                # Low error frequency - decrease cooldown
                return max(60, base_cooldown // 2)
            else:
                return base_cooldown
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic alert cooldown: {e}")
            return config.get('alert_cooldown', 300)
    
    async def _get_dynamic_check_interval(self, config: Dict[str, Any], check_type: str) -> int:
        """Get dynamic check interval based on system load"""
        try:
            current_cpu = psutil.cpu_percent(interval=1)
            
            if check_type == 'system':
                base_interval = config.get('system_check_interval', 60)
            elif check_type == 'performance':
                base_interval = config.get('performance_check_interval', 300)
            elif check_type == 'error':
                base_interval = config.get('error_check_interval', 30)
            else:
                base_interval = 60
            
            # Adjust interval based on CPU load
            if current_cpu > 80:
                # High load - increase interval to reduce overhead
                return min(base_interval * 2, 600)
            elif current_cpu < 30:
                # Low load - decrease interval for better monitoring
                return max(base_interval // 2, 15)
            else:
                return base_interval
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic check interval: {e}")
            if check_type == 'system':
                return config.get('system_check_interval', 60)
            elif check_type == 'performance':
                return config.get('performance_check_interval', 300)
            elif check_type == 'error':
                return config.get('error_check_interval', 30)
            else:
                return 60
    
    async def close(self):
        """Monitoring sistemini kapat"""
        try:
            logger.info("🛑 Closing monitoring system...")
            # Cleanup tasks
            self.performance_metrics.clear()
            logger.success("✅ Monitoring system closed")
            
        except Exception as e:
            logger.error(f"❌ Monitoring close error: {e}")