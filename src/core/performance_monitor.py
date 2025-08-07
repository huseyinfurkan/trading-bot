#!/usr/bin/env python3
"""
Performance Monitor
Comprehensive performance monitoring with metrics collection and analysis
"""

import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
import json
import os


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Performance metrics storage
        self.system_metrics = []
        self.trading_metrics = []
        self.error_metrics = []
        
        # Dynamic configuration based on system performance
        self.monitoring_interval = await self._get_dynamic_monitoring_interval(config)
        self.retention_hours = await self._get_dynamic_retention_hours(config)
        self.max_metrics_count = await self._get_dynamic_max_metrics_count(config)
        
        # Dynamic thresholds based on system performance
        self.thresholds = await self._get_dynamic_thresholds(config)
        
        # Performance tracking
        self.start_time = datetime.now()
        self.operation_times = {}
        self.operation_counts = {}
        
        # Dynamic alert tracking
        self.alerts = []
        self.alert_cooldown = await self._get_dynamic_alert_cooldown(config)
        self.last_alert_time = {}
        
        # Thread safety
        self.lock = threading.Lock()
        
        logger.info("📊 Performance Monitor initialized")
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        try:
            logger.info("🚀 Performance monitoring started")
            
            # Start monitoring tasks
            tasks = [
                asyncio.create_task(self._system_monitor()),
                asyncio.create_task(self._trading_performance_monitor()),
                asyncio.create_task(self._metrics_cleanup())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"❌ Performance monitoring start error: {e}")
    
    async def _system_monitor(self):
        """Monitor system performance metrics"""
        try:
            while True:
                try:
                    # Collect system metrics
                    metrics = self._collect_system_metrics()
                    
                    # Store metrics
                    with self.lock:
                        self.system_metrics.append(metrics)
                        
                        # Keep only recent metrics
                        if len(self.system_metrics) > self.max_metrics_count:
                            self.system_metrics = self.system_metrics[-self.max_metrics_count:]
                    
                    # Check thresholds and send alerts
                    await self._check_system_thresholds(metrics)
                    
                    # Log periodic summary
                    if len(self.system_metrics) % 10 == 0:  # Every 10 minutes
                        self._log_system_summary()
                    
                    await asyncio.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"❌ System monitoring error: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ System monitor fatal error: {e}")
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            return {
                'timestamp': datetime.now(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else 0,
                    'process_cpu_percent': process_cpu
                },
                'memory': {
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'used_gb': memory.used / (1024**3),
                    'usage_percent': memory.percent,
                    'swap_total_gb': swap.total / (1024**3),
                    'swap_used_gb': swap.used / (1024**3),
                    'swap_usage_percent': swap.percent,
                    'process_memory_mb': process_memory.rss / (1024**2)
                },
                'disk': {
                    'total_gb': disk.total / (1024**3),
                    'used_gb': disk.used / (1024**3),
                    'free_gb': disk.free / (1024**3),
                    'usage_percent': (disk.used / disk.total) * 100,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"❌ System metrics collection error: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e)
            }
    
    async def _check_system_thresholds(self, metrics: Dict[str, Any]):
        """Check system metrics against thresholds"""
        try:
            alerts = []
            
            # CPU threshold check
            cpu_usage = metrics.get('cpu', {}).get('usage_percent', 0)
            if cpu_usage > self.thresholds['cpu_usage']:
                alerts.append(f"High CPU usage: {cpu_usage:.1f}%")
            
            # Memory threshold check
            memory_usage = metrics.get('memory', {}).get('usage_percent', 0)
            if memory_usage > self.thresholds['memory_usage']:
                alerts.append(f"High memory usage: {memory_usage:.1f}%")
            
            # Disk threshold check
            disk_usage = metrics.get('disk', {}).get('usage_percent', 0)
            if disk_usage > self.thresholds['disk_usage']:
                alerts.append(f"High disk usage: {disk_usage:.1f}%")
            
            # Send alerts
            if alerts:
                await self._send_performance_alert('SYSTEM', alerts, metrics)
                
        except Exception as e:
            logger.error(f"❌ Threshold check error: {e}")
    
    async def _trading_performance_monitor(self):
        """Monitor trading performance metrics"""
        try:
            while True:
                try:
                    # Collect trading metrics
                    metrics = self._collect_trading_metrics()
                    
                    # Store metrics
                    with self.lock:
                        self.trading_metrics.append(metrics)
                        
                        # Keep only recent metrics
                        if len(self.trading_metrics) > self.max_metrics_count:
                            self.trading_metrics = self.trading_metrics[-self.max_metrics_count:]
                    
                    # Check trading thresholds
                    await self._check_trading_thresholds(metrics)
                    
                    await asyncio.sleep(self.monitoring_interval)
                    
                except Exception as e:
                    logger.error(f"❌ Trading performance monitoring error: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ Trading performance monitor fatal error: {e}")
    
    def _collect_trading_metrics(self) -> Dict[str, Any]:
        """Collect trading performance metrics"""
        try:
            # Calculate operation performance
            operation_performance = {}
            for operation, times in self.operation_times.items():
                if times:
                    avg_time = sum(times) / len(times)
                    max_time = max(times)
                    min_time = min(times)
                    count = self.operation_counts.get(operation, 0)
                    
                    operation_performance[operation] = {
                        'avg_time_ms': avg_time * 1000,
                        'max_time_ms': max_time * 1000,
                        'min_time_ms': min_time * 1000,
                        'count': count,
                        'throughput_per_min': count / max(1, (datetime.now() - self.start_time).total_seconds() / 60)
                    }
            
            return {
                'timestamp': datetime.now(),
                'operation_performance': operation_performance,
                'total_operations': sum(self.operation_counts.values()),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"❌ Trading metrics collection error: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e)
            }
    
    async def _check_trading_thresholds(self, metrics: Dict[str, Any]):
        """Check trading metrics against thresholds"""
        try:
            alerts = []
            
            # Check operation response times
            for operation, perf in metrics.get('operation_performance', {}).items():
                avg_time = perf.get('avg_time_ms', 0) / 1000  # Convert to seconds
                if avg_time > self.thresholds['response_time']:
                    alerts.append(f"Slow {operation}: {avg_time:.2f}s")
            
            # Send alerts
            if alerts:
                await self._send_performance_alert('TRADING', alerts, metrics)
                
        except Exception as e:
            logger.error(f"❌ Trading threshold check error: {e}")
    
    async def _send_performance_alert(self, alert_type: str, messages: List[str], metrics: Dict[str, Any]):
        """Send performance alert"""
        try:
            alert_key = f"{alert_type}_{datetime.now().strftime('%Y%m%d_%H')}"
            
            # Check cooldown
            if (alert_key in self.last_alert_time and 
                (datetime.now() - self.last_alert_time[alert_key]).seconds < self.alert_cooldown):
                return
            
            # Create alert
            alert = {
                'timestamp': datetime.now(),
                'type': alert_type,
                'messages': messages,
                'metrics_summary': self._create_metrics_summary(metrics)
            }
            
            # Store alert
            with self.lock:
                self.alerts.append(alert)
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]
            
            # Log alert
            alert_message = f"🚨 {alert_type} PERFORMANCE ALERT:\n"
            for msg in messages:
                alert_message += f"   • {msg}\n"
            
            logger.warning(alert_message)
            
            # Update last alert time
            self.last_alert_time[alert_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Performance alert error: {e}")
    
    def _create_metrics_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of metrics for alert"""
        try:
            summary = {}
            
            # System metrics summary
            if 'cpu' in metrics:
                summary['cpu_usage'] = metrics['cpu'].get('usage_percent', 0)
            
            if 'memory' in metrics:
                summary['memory_usage'] = metrics['memory'].get('usage_percent', 0)
            
            if 'disk' in metrics:
                summary['disk_usage'] = metrics['disk'].get('usage_percent', 0)
            
            # Trading metrics summary
            if 'operation_performance' in metrics:
                summary['total_operations'] = metrics.get('total_operations', 0)
                
                # Find slowest operation
                slowest_operation = None
                slowest_time = 0
                for op, perf in metrics['operation_performance'].items():
                    avg_time = perf.get('avg_time_ms', 0)
                    if avg_time > slowest_time:
                        slowest_time = avg_time
                        slowest_operation = op
                
                if slowest_operation:
                    summary['slowest_operation'] = {
                        'name': slowest_operation,
                        'avg_time_ms': slowest_time
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Metrics summary creation error: {e}")
            return {'error': str(e)}
    
    def record_operation(self, operation: str, duration: float):
        """Record operation performance"""
        try:
            with self.lock:
                # Record operation time
                if operation not in self.operation_times:
                    self.operation_times[operation] = []
                
                self.operation_times[operation].append(duration)
                
                # Keep only last 100 times per operation
                if len(self.operation_times[operation]) > 100:
                    self.operation_times[operation] = self.operation_times[operation][-100:]
                
                # Update operation count
                if operation not in self.operation_counts:
                    self.operation_counts[operation] = 0
                
                self.operation_counts[operation] += 1
                
        except Exception as e:
            logger.error(f"❌ Operation recording error: {e}")
    
    async def _metrics_cleanup(self):
        """Clean up old metrics"""
        try:
            while True:
                try:
                    cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
                    
                    with self.lock:
                        # Clean system metrics
                        self.system_metrics = [
                            m for m in self.system_metrics
                            if m.get('timestamp', datetime.min) > cutoff_time
                        ]
                        
                        # Clean trading metrics
                        self.trading_metrics = [
                            m for m in self.trading_metrics
                            if m.get('timestamp', datetime.min) > cutoff_time
                        ]
                        
                        # Clean alerts
                        self.alerts = [
                            a for a in self.alerts
                            if a.get('timestamp', datetime.min) > cutoff_time
                        ]
                    
                    logger.debug("🧹 Performance metrics cleanup completed")
                    
                    # Wait 1 hour before next cleanup
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"❌ Metrics cleanup error: {e}")
                    await asyncio.sleep(300)
                    
        except Exception as e:
            logger.error(f"❌ Metrics cleanup fatal error: {e}")
    
    def _log_system_summary(self):
        """Log periodic system performance summary"""
        try:
            if not self.system_metrics:
                return
            
            # Get latest metrics
            latest = self.system_metrics[-1]
            
            # Calculate averages over last 10 metrics
            recent_metrics = self.system_metrics[-10:]
            
            avg_cpu = sum(m.get('cpu', {}).get('usage_percent', 0) for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.get('memory', {}).get('usage_percent', 0) for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.get('disk', {}).get('usage_percent', 0) for m in recent_metrics) / len(recent_metrics)
            
            logger.info(f"📊 System Performance Summary:")
            logger.info(f"   CPU: {avg_cpu:.1f}% avg, {latest['cpu']['usage_percent']:.1f}% current")
            logger.info(f"   Memory: {avg_memory:.1f}% avg, {latest['memory']['usage_percent']:.1f}% current")
            logger.info(f"   Disk: {avg_disk:.1f}% avg, {latest['disk']['usage_percent']:.1f}% current")
            logger.info(f"   Uptime: {(datetime.now() - self.start_time).total_seconds() / 3600:.1f} hours")
            
        except Exception as e:
            logger.error(f"❌ System summary logging error: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            with self.lock:
                # System performance
                system_summary = {}
                if self.system_metrics:
                    latest_system = self.system_metrics[-1]
                    system_summary = {
                        'current_cpu_usage': latest_system.get('cpu', {}).get('usage_percent', 0),
                        'current_memory_usage': latest_system.get('memory', {}).get('usage_percent', 0),
                        'current_disk_usage': latest_system.get('disk', {}).get('usage_percent', 0),
                        'uptime_seconds': latest_system.get('uptime_seconds', 0)
                    }
                
                # Trading performance
                trading_summary = {}
                if self.trading_metrics:
                    latest_trading = self.trading_metrics[-1]
                    trading_summary = {
                        'total_operations': latest_trading.get('total_operations', 0),
                        'operation_performance': latest_trading.get('operation_performance', {}),
                        'uptime_seconds': latest_trading.get('uptime_seconds', 0)
                    }
                
                # Alert summary
                alert_summary = {
                    'total_alerts': len(self.alerts),
                    'recent_alerts': self.alerts[-5:] if self.alerts else []
                }
                
                return {
                    'system_performance': system_summary,
                    'trading_performance': trading_summary,
                    'alerts': alert_summary,
                    'metrics_count': {
                        'system_metrics': len(self.system_metrics),
                        'trading_metrics': len(self.trading_metrics),
                        'alerts': len(self.alerts)
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Performance summary error: {e}")
            return {'error': str(e)}
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        try:
            with self.lock:
                export_data = {
                    'export_timestamp': datetime.now().isoformat(),
                    'system_metrics': self.system_metrics,
                    'trading_metrics': self.trading_metrics,
                    'alerts': self.alerts,
                    'operation_counts': self.operation_counts
                }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.success(f"✅ Performance metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Metrics export error: {e}")
    
    async def _get_dynamic_monitoring_interval(self, config: Dict[str, Any]) -> int:
        """Get dynamic monitoring interval based on system load"""
        try:
            base_interval = config.get('monitoring_interval', 60)
            current_cpu = psutil.cpu_percent(interval=1)
            
            # Adjust interval based on CPU load
            if current_cpu > 80:
                # High load - increase interval to reduce overhead
                return min(base_interval * 2, 120)
            elif current_cpu < 30:
                # Low load - decrease interval for better monitoring
                return max(base_interval // 2, 30)
            else:
                return base_interval
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic monitoring interval: {e}")
            return config.get('monitoring_interval', 60)
    
    async def _get_dynamic_retention_hours(self, config: Dict[str, Any]) -> int:
        """Get dynamic retention hours based on disk space"""
        try:
            base_retention = config.get('retention_hours', 24)
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            
            # Adjust retention based on disk usage
            if usage_percent > 85:
                # High disk usage - reduce retention
                return max(6, base_retention // 2)
            elif usage_percent < 50:
                # Low disk usage - increase retention
                return min(72, base_retention * 2)
            else:
                return base_retention
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic retention hours: {e}")
            return config.get('retention_hours', 24)
    
    async def _get_dynamic_max_metrics_count(self, config: Dict[str, Any]) -> int:
        """Get dynamic max metrics count based on memory"""
        try:
            base_count = config.get('max_metrics_count', 1000)
            memory = psutil.virtual_memory()
            
            # Adjust count based on available memory
            if memory.available < memory.total * 0.1:  # Less than 10% available
                return max(500, base_count // 2)
            elif memory.available > memory.total * 0.5:  # More than 50% available
                return min(2000, base_count * 2)
            else:
                return base_count
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic max metrics count: {e}")
            return config.get('max_metrics_count', 1000)
    
    async def _get_dynamic_thresholds(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get dynamic thresholds based on system performance"""
        try:
            base_thresholds = {
                'cpu_usage': config.get('thresholds', {}).get('cpu_usage', 80),
                'memory_usage': config.get('thresholds', {}).get('memory_usage', 80),
                'disk_usage': config.get('thresholds', {}).get('disk_usage', 90),
                'response_time': config.get('thresholds', {}).get('response_time', 5.0),
                'error_rate': config.get('thresholds', {}).get('error_rate', 0.1)
            }
            
            # Adjust thresholds based on current system state
            current_cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # CPU threshold adjustment
            if current_cpu > 70:
                base_thresholds['cpu_usage'] = min(95, base_thresholds['cpu_usage'] + 10)
            elif current_cpu < 30:
                base_thresholds['cpu_usage'] = max(60, base_thresholds['cpu_usage'] - 10)
            
            # Memory threshold adjustment
            if memory.percent > 70:
                base_thresholds['memory_usage'] = min(95, base_thresholds['memory_usage'] + 10)
            elif memory.percent < 30:
                base_thresholds['memory_usage'] = max(60, base_thresholds['memory_usage'] - 10)
            
            # Disk threshold adjustment
            disk_usage_percent = (disk.used / disk.total) * 100
            if disk_usage_percent > 80:
                base_thresholds['disk_usage'] = min(98, base_thresholds['disk_usage'] + 5)
            elif disk_usage_percent > 50:
                base_thresholds['disk_usage'] = max(80, base_thresholds['disk_usage'] - 10)
            
            logger.info(f"📊 Dynamic thresholds - CPU: {base_thresholds['cpu_usage']}%, "
                       f"Memory: {base_thresholds['memory_usage']}%, Disk: {base_thresholds['disk_usage']}%")
            
            return base_thresholds
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic thresholds: {e}")
            return {
                'cpu_usage': config.get('thresholds', {}).get('cpu_usage', 80),
                'memory_usage': config.get('thresholds', {}).get('memory_usage', 80),
                'disk_usage': config.get('thresholds', {}).get('disk_usage', 90),
                'response_time': config.get('thresholds', {}).get('response_time', 5.0),
                'error_rate': config.get('thresholds', {}).get('error_rate', 0.1)
            }
    
    async def _get_dynamic_alert_cooldown(self, config: Dict[str, Any]) -> int:
        """Get dynamic alert cooldown based on alert frequency"""
        try:
            base_cooldown = config.get('alert_cooldown', 300)
            
            # Check recent alert frequency
            recent_alerts = len([a for a in self.alerts 
                               if (datetime.now() - a.get('timestamp', datetime.now())).total_seconds() < 1800])  # Last 30 minutes
            
            if recent_alerts > 10:
                # High alert frequency - increase cooldown
                return min(600, base_cooldown * 2)
            elif recent_alerts < 2:
                # Low alert frequency - decrease cooldown
                return max(60, base_cooldown // 2)
            else:
                return base_cooldown
                
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic alert cooldown: {e}")
            return config.get('alert_cooldown', 300)
    
    def clear_metrics(self):
        """Clear all metrics"""
        try:
            with self.lock:
                self.system_metrics.clear()
                self.trading_metrics.clear()
                self.error_metrics.clear()
                self.alerts.clear()
                self.operation_times.clear()
                self.operation_counts.clear()
            
            logger.info("🧹 All performance metrics cleared")
            
        except Exception as e:
            logger.error(f"❌ Metrics clear error: {e}")