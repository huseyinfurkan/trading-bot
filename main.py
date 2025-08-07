#!/usr/bin/env python3
"""
Enhanced Trading Bot - Main Entry Point
Integrated with WebSocket, Error Handling, and Performance Monitoring
"""

import asyncio
import signal
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.risk_manager import RiskManager
from src.core.monitoring import MonitoringSystem
from src.core.live_data_engine import LiveDataEngine
from src.core.bot_coordinator import BotCoordinator
from src.core.websocket_manager import WebSocketManager
from src.core.error_handler import ErrorHandler
from src.core.performance_monitor import PerformanceMonitor

from src.trading.exchange_manager import ExchangeManager
from src.trading.position_manager import PositionManager
from src.trading.adaptive_strategy_engine import AdaptiveStrategyEngine

from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.confidence_calculator import ConfidenceCalculator

from src.utils.notifications import NotificationManager
from src.utils.logger_setup import setup_logger


class EnhancedTradingBot:
    """Enhanced Trading Bot with comprehensive monitoring and error handling"""
    
    def __init__(self):
        self.config = None
        self.components = {}
        self.running = False
        
        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🤖 Enhanced Trading Bot initializing...")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def initialize(self):
        """Initialize all bot components"""
        try:
            logger.info("🔧 Initializing bot components...")
            
            # 1. Load configuration
            config_path = Path(__file__).parent / 'config' / 'config.yaml'
            self.config_manager = ConfigManager(str(config_path))
            self.config = await self.config_manager.load_config()
            
            # 2. Setup logging
            setup_logger(self.config.get('logging', {}))
            logger.info("✅ Logging system initialized")
            
            # 3. Initialize error handler
            self.error_handler = ErrorHandler(self.config.get('error_handling', {}))
            logger.info("✅ Error handler initialized")
            
            # 4. Initialize performance monitor
            self.performance_monitor = PerformanceMonitor(self.config.get('performance_monitoring', {}))
            logger.info("✅ Performance monitor initialized")
            
            # 5. Initialize database
            self.db_manager = DatabaseManager(self.config.get('database', {}))
            await self.db_manager.initialize()
            logger.info("✅ Database initialized")
            
            # 6. Initialize exchange manager
            self.exchange_manager = ExchangeManager(self.config.get('exchanges', {}))
            await self.exchange_manager.initialize()
            logger.info("✅ Exchange manager initialized")
            
            # 7. Initialize WebSocket manager
            self.websocket_manager = WebSocketManager(self.config)
            await self.websocket_manager.initialize()
            logger.info("✅ WebSocket manager initialized")
            
            # 8. Initialize AI components
            self.ai_signal_filter = AISignalFilter(self.config.get('ai', {}))
            await self.ai_signal_filter.initialize()
            
            self.market_analyzer = MarketAnalyzer(self.exchange_manager, self.config.get('market_analysis', {}))
            self.confidence_calculator = ConfidenceCalculator()
            
            logger.info("✅ AI components initialized")
            
            # 9. Initialize trading components
            self.risk_manager = RiskManager(self.config.get('trading', {}).get('risk_management', {}))
            self.position_manager = PositionManager(self.exchange_manager, self.db_manager, self.risk_manager)
            
            self.strategy_engine = AdaptiveStrategyEngine(
                self.config, 
                self.exchange_manager, 
                self.ai_signal_filter, 
                self.risk_manager
            )
            
            logger.info("✅ Trading components initialized")
            
            # 10. Initialize monitoring system
            self.monitoring_system = MonitoringSystem(self.config.get('monitoring', {}))
            
            # 11. Initialize live data engine
            self.live_data_engine = LiveDataEngine(
                self.exchange_manager,
                self.market_analyzer,
                self.ai_signal_filter,
                self.strategy_engine,
                self.position_manager,
                self.risk_manager
            )
            
            logger.info("✅ Live data engine initialized")
            
            # 12. Initialize bot coordinator
            self.bot_coordinator = BotCoordinator(
                self.config,
                self.exchange_manager,
                self.position_manager,
                self.risk_manager,
                self.monitoring_system,
                self.db_manager
            )
            
            logger.info("✅ Bot coordinator initialized")
            
            # 13. Initialize notifications
            self.notifications = NotificationManager(self.config.get('notifications', {}))
            
            # Store all components for easy access
            self.components = {
                'config_manager': self.config_manager,
                'error_handler': self.error_handler,
                'performance_monitor': self.performance_monitor,
                'db_manager': self.db_manager,
                'exchange_manager': self.exchange_manager,
                'websocket_manager': self.websocket_manager,
                'ai_signal_filter': self.ai_signal_filter,
                'market_analyzer': self.market_analyzer,
                'confidence_calculator': self.confidence_calculator,
                'risk_manager': self.risk_manager,
                'position_manager': self.position_manager,
                'strategy_engine': self.strategy_engine,
                'monitoring_system': self.monitoring_system,
                'live_data_engine': self.live_data_engine,
                'bot_coordinator': self.bot_coordinator,
                'notifications': self.notifications
            }
            
            logger.success("🎉 All components initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            await self.cleanup()
            raise
    
    async def start(self):
        """Start the trading bot"""
        try:
            logger.info("🚀 Starting Enhanced Trading Bot...")
            self.running = True
            
            # Start performance monitoring
            asyncio.create_task(self.performance_monitor.start_monitoring())
            
            # Start WebSocket monitoring
            asyncio.create_task(self.websocket_manager.monitor_connections())
            
            # Start monitoring system
            asyncio.create_task(self.monitoring_system.start_monitoring())
            
            # Start bot coordinator
            asyncio.create_task(self.bot_coordinator.start())
            
            # Start live data engine
            asyncio.create_task(self.live_data_engine.start_live_analysis())
            
            # Send startup notification
            await self.notifications.send_message(
                f"🤖 Trading Bot Started\nBot started successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "info"
            )
            
            logger.success("✅ Trading bot started successfully!")
            
            # Main loop
            while self.running:
                try:
                    # Check system health
                    health_status = await self.monitoring_system.get_system_health()
                    
                    if not health_status['healthy']:
                        logger.warning(f"⚠️ System health issues: {health_status['issues']}")
                        
                        # Send health alert
                        await self.notifications.send_message(
                            f"⚠️ System Health Alert\nHealth issues detected: {', '.join(health_status['issues'])}",
                            "warning"
                        )
                    
                    # Log periodic status
                    if datetime.now().minute % 10 == 0:  # Every 10 minutes
                        await self._log_status()
                    
                    await asyncio.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"❌ Main loop error: {e}")
                    await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"❌ Bot start failed: {e}")
            await self.cleanup()
            raise
    
    async def _log_status(self):
        """Log periodic status information"""
        try:
            # Get performance summary
            perf_summary = self.performance_monitor.get_performance_summary()
            
            # Get WebSocket status
            ws_status = self.websocket_manager.get_connection_status()
            
            # Get live data status
            live_status = self.live_data_engine.get_enhanced_live_status()
            
            # Get error statistics
            error_stats = self.error_handler.get_error_statistics()
            
            logger.info("📊 Bot Status Summary:")
            logger.info(f"   Performance: CPU {perf_summary.get('system_performance', {}).get('current_cpu_usage', 0):.1f}%, "
                       f"Memory {perf_summary.get('system_performance', {}).get('current_memory_usage', 0):.1f}%")
            logger.info(f"   WebSocket: {ws_status.get('connections', {}).get('bybit', {}).get('connected', False)}")
            logger.info(f"   Live Data: {live_status.get('symbols_with_data', 0)}/{live_status.get('symbols_tracked', 0)} symbols")
            logger.info(f"   Errors: {error_stats.get('total_errors', 0)} total")
            
        except Exception as e:
            logger.error(f"❌ Status logging error: {e}")
    
    async def stop(self):
        """Stop the trading bot gracefully"""
        try:
            logger.info("🛑 Stopping trading bot...")
            self.running = False
            
            # Send shutdown notification
            await self.notifications.send_notification(
                "🛑 Trading Bot Stopped",
                f"Bot stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Wait a bit for graceful shutdown
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ Stop error: {e}")
    
    async def cleanup(self):
        """Cleanup all resources"""
        try:
            logger.info("🧹 Cleaning up resources...")
            
            # Close WebSocket connections
            if hasattr(self, 'websocket_manager'):
                await self.websocket_manager.close()
            
            # Close exchange connections
            if hasattr(self, 'exchange_manager'):
                await self.exchange_manager.close()
            
            # Close database connections
            if hasattr(self, 'db_manager'):
                await self.db_manager.close()
            
            logger.success("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


async def main():
    """Main entry point"""
    bot = None
    
    try:
        # Create and initialize bot
        bot = EnhancedTradingBot()
        await bot.initialize()
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        # Cleanup
        if bot:
            await bot.stop()
            await bot.cleanup()
        
        logger.info("👋 Trading bot shutdown complete")


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())