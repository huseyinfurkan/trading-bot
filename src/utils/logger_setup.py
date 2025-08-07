"""
Logger Setup
Gelişmiş logging sistemi kurulumu
"""

import sys
import os
from pathlib import Path
from loguru import logger
from typing import Dict, Any


def setup_logging(logging_config: Dict[str, Any]) -> None:
    """Logging sistemini kur"""
    try:
        # Mevcut logger'ları temizle
        logger.remove()
        
        # Dynamic config parameters based on system resources
        level = await _get_dynamic_log_level(logging_config)
        file_path = await _get_dynamic_file_path(logging_config)
        max_file_size = await _get_dynamic_max_file_size(logging_config)
        backup_count = await _get_dynamic_backup_count(logging_config)
        console_output = logging_config.get('console_output', True)
        
        # Log directory oluştur
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Console logger
        if console_output:
            logger.add(
                sys.stdout,
                level=level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                       "<level>{level: <8}</level> | "
                       "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                       "<level>{message}</level>",
                colorize=True
            )
        
        # File logger
        logger.add(
            file_path,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation=max_file_size,
            retention=backup_count,
            compression="zip",
            encoding="utf-8"
        )
        
        # Error logger (separate file for errors)
        error_file = str(Path(file_path).parent / "errors.log")
        logger.add(
            error_file,
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
            rotation="1 week",
            retention="1 month",
            compression="zip"
        )
        
        # Performance logger (for trade analysis)
        performance_file = str(Path(file_path).parent / "performance.log")
        logger.add(
            performance_file,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            filter=lambda record: "PERFORMANCE" in record["extra"],
            rotation="1 day",
            retention="3 months"
        )
        
        logger.info(f"✅ Logging sistemi kuruldu - Level: {level}, File: {file_path}")
        
    except Exception as e:
        print(f"❌ Logging kurulum hatası: {e}")
        # Fallback basic console logging
        logger.add(sys.stdout, level="INFO")


def setup_logger(name: str = None, file_path: str = None, level: str = 'INFO'):
    """Setup logger with name and file path for backwards compatibility"""
    if file_path is None:
        file_path = 'logs/trading_bot.log'
    
    config = {
        'level': level,
        'file_path': file_path,
        'console_output': True
    }
    setup_logging(config)
    
    # Return loguru logger
    from loguru import logger
    return logger


async def _get_dynamic_log_level(logging_config: Dict[str, Any]) -> str:
    """Get dynamic log level based on system load"""
    try:
        import psutil
        
        base_level = logging_config.get('level', 'INFO')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Adjust log level based on system load
        if cpu_percent > 80:
            # High load - reduce logging
            return 'WARNING' if base_level == 'INFO' else base_level
        elif cpu_percent < 30:
            # Low load - increase logging
            return 'DEBUG' if base_level == 'INFO' else base_level
        else:
            return base_level
            
    except Exception as e:
        print(f"⚠️ Could not calculate dynamic log level: {e}")
        return logging_config.get('level', 'INFO')

async def _get_dynamic_file_path(logging_config: Dict[str, Any]) -> str:
    """Get dynamic file path based on disk space"""
    try:
        import psutil
        
        base_path = logging_config.get('file_path', 'logs/trading_bot.log')
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        # Adjust path based on disk usage
        if usage_percent > 90:
            # High disk usage - use smaller path
            return 'logs/minimal.log'
        else:
            return base_path
            
    except Exception as e:
        print(f"⚠️ Could not calculate dynamic file path: {e}")
        return logging_config.get('file_path', 'logs/trading_bot.log')

async def _get_dynamic_max_file_size(logging_config: Dict[str, Any]) -> str:
    """Get dynamic max file size based on disk space"""
    try:
        import psutil
        
        base_size = logging_config.get('max_file_size', '100MB')
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        # Adjust size based on disk usage
        if usage_percent > 85:
            # High disk usage - reduce file size
            return '50MB'
        elif usage_percent < 50:
            # Low disk usage - increase file size
            return '200MB'
        else:
            return base_size
            
    except Exception as e:
        print(f"⚠️ Could not calculate dynamic max file size: {e}")
        return logging_config.get('max_file_size', '100MB')

async def _get_dynamic_backup_count(logging_config: Dict[str, Any]) -> int:
    """Get dynamic backup count based on disk space"""
    try:
        import psutil
        
        base_count = logging_config.get('backup_count', 5)
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        # Adjust count based on disk usage
        if usage_percent > 80:
            # High disk usage - reduce backup count
            return max(2, base_count // 2)
        elif usage_percent < 40:
            # Low disk usage - increase backup count
            return min(10, base_count * 2)
        else:
            return base_count
            
    except Exception as e:
        print(f"⚠️ Could not calculate dynamic backup count: {e}")
        return logging_config.get('backup_count', 5)

def get_performance_logger():
    """Performance logging için özel logger"""
    return logger.bind(PERFORMANCE=True)


def log_trade_performance(trade_data: Dict[str, Any]) -> None:
    """Trade performansını logla"""
    try:
        perf_logger = get_performance_logger()
        
        message = (
            f"TRADE | {trade_data.get('symbol', 'UNKNOWN')} | "
            f"{trade_data.get('side', 'UNKNOWN')} | "
            f"PnL: {trade_data.get('pnl', 0):.4f} | "
            f"Duration: {trade_data.get('duration', 0)} min | "
            f"Strategy: {trade_data.get('strategy', 'UNKNOWN')}"
        )
        
        perf_logger.info(message)
        
    except Exception as e:
        logger.error(f"❌ Trade performance log hatası: {e}")


def log_signal_performance(signal_data: Dict[str, Any]) -> None:
    """Sinyal performansını logla"""
    try:
        perf_logger = get_performance_logger()
        
        message = (
            f"SIGNAL | {signal_data.get('symbol', 'UNKNOWN')} | "
            f"Type: {signal_data.get('signal_type', 'UNKNOWN')} | "
            f"Strength: {signal_data.get('strength', 0):.3f} | "
            f"Confidence: {signal_data.get('confidence', 0):.3f} | "
            f"Strategy: {signal_data.get('strategy', 'UNKNOWN')}"
        )
        
        perf_logger.info(message)
        
    except Exception as e:
        logger.error(f"❌ Signal performance log hatası: {e}")


def log_system_metrics(metrics: Dict[str, Any]) -> None:
    """Sistem metriklerini logla"""
    try:
        perf_logger = get_performance_logger()
        
        message = (
            f"SYSTEM | CPU: {metrics.get('cpu_usage', 0):.1f}% | "
            f"Memory: {metrics.get('memory_usage', 0):.1f}MB | "
            f"Active Positions: {metrics.get('active_positions', 0)} | "
            f"Total PnL: {metrics.get('total_pnl', 0):.4f}"
        )
        
        perf_logger.info(message)
        
    except Exception as e:
        logger.error(f"❌ System metrics log hatası: {e}")