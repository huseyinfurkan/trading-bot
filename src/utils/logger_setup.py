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
        
        # Config parametreleri
        level = logging_config.get('level', 'INFO')
        file_path = logging_config.get('file_path', 'logs/trading_bot.log')
        max_file_size = logging_config.get('max_file_size', '100MB')
        backup_count = logging_config.get('backup_count', 5)
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
            retention=f"{backup_count} files",
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


def setup_logger(config: Dict[str, Any] = None) -> None:
    """Alias for setup_logging function"""
    if config is None:
        config = {
            'level': 'INFO',
            'file_path': 'logs/trading_bot.log',
            'console_output': True
        }
    setup_logging(config)


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