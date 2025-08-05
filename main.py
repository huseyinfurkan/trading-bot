#!/usr/bin/env python3
"""
Advanced Multi-Coin Trading Bot
AI-powered cryptocurrency trading with live data analysis
"""

import asyncio
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Core modules
from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.risk_manager import RiskManager
from src.core.monitoring import MonitoringSystem
from src.core.live_data_engine import LiveDataEngine

# Trading modules
from src.trading.exchange_manager import ExchangeManager
from src.trading.strategy_engine import StrategyEngine
from src.trading.position_manager import PositionManager

# AI modules
from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.confidence_calculator import ConfidenceCalculator

# Utils
from src.utils.notifications import NotificationManager
from src.utils.logger_setup import setup_logging


class AdvancedTradingBot:
    """Advanced Multi-Coin Trading Bot with Live Data Analysis"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the trading bot"""
        self.config_path = config_path
        self.running = False
        
        # Core components
        self.config_manager = None
        self.config = None
        self.db_manager = None
        self.risk_manager = None
        self.monitoring_system = None
        self.live_data_engine = None
        
        # Trading components
        self.exchange_manager = None
        self.strategy_engine = None
        self.position_manager = None
        
        # AI components
        self.ai_signal_filter = None
        self.market_analyzer = None
        self.confidence_calculator = None
        
        # Utils
        self.notification_manager = None
        
        logger.info("🤖 Advanced Trading Bot initialized")
    
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("🚀 Advanced Trading Bot initializing...")
            
            # Load configuration
            self.config_manager = ConfigManager(self.config_path)
            self.config = await self.config_manager.load_config()
            
            # Setup logging
            setup_logging(self.config.get('logging', {}))
            
            # Initialize database
            self.db_manager = DatabaseManager(self.config.get('database', {}))
            await self.db_manager.initialize()
            
            # Initialize notification system
            self.notification_manager = NotificationManager(
                self.config.get('notifications', {})
            )
            await self.notification_manager.initialize()
            
            # Initialize exchange manager
            self.exchange_manager = ExchangeManager(
                self.config.get('exchanges', {})
            )
            await self.exchange_manager.initialize()
            
            # Initialize risk manager
            self.risk_manager = RiskManager(
                self.config.get('risk_management', {}),
                self.db_manager
            )
            
            # Initialize AI components
            self.ai_signal_filter = AISignalFilter(
                self.config.get('ai_settings', {}),
                self.db_manager
            )
            await self.ai_signal_filter.initialize()
            
            self.market_analyzer = MarketAnalyzer(
                self.config.get('market_conditions', {}),
                self.db_manager
            )
            
            self.confidence_calculator = ConfidenceCalculator(
                self.config.get('ai_settings', {}),
                self.db_manager
            )
            
            # Initialize trading components
            self.strategy_engine = StrategyEngine(
                self.config.get('strategies', {}),
                self.ai_signal_filter,
                self.market_analyzer,
                self.confidence_calculator
            )
            
            self.position_manager = PositionManager(
                self.exchange_manager,
                self.risk_manager,
                self.db_manager
            )
            
            # Initialize live data engine
            self.live_data_engine = LiveDataEngine(
                exchange_manager=self.exchange_manager,
                market_analyzer=self.market_analyzer,
                ai_signal_filter=self.ai_signal_filter,
                strategy_engine=self.strategy_engine,
                position_manager=self.position_manager,
                risk_manager=self.risk_manager
            )
            
            # Initialize monitoring system
            self.monitoring_system = MonitoringSystem(
                self.config.get('performance', {}),
                self.db_manager,
                self.notification_manager
            )
            
            logger.success("✅ All components initialized successfully!")
            
        except Exception as e:
            logger.error(f"❌ Bot initialization error: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def start_trading(self):
        """Start the trading system"""
        try:
            self.running = True
            logger.info("📈 Starting trading system...")
            
            # Get trading pairs
            trading_pairs = self.config.get('trading_pairs', {})
            all_pairs = []
            for category, pairs in trading_pairs.items():
                all_pairs.extend(pairs)
            
            logger.info(f"💎 Monitoring {len(all_pairs)} trading pairs: {all_pairs}")
            
            # Send startup notification
            await self.notification_manager.send_message(
                "🤖 Advanced Trading Bot started!\n"
                f"📊 {len(all_pairs)} coins monitored\n"
                f"🧠 AI filtering active\n"
                f"⚡ Multi-strategy enabled\n"
                f"🔥 Live data analysis running"
            )
            
            # Start live data engine
            live_task = asyncio.create_task(self.live_data_engine.start_live_analysis())
            
            # Main monitoring loop
            while self.running:
                try:
                    # Get live engine status
                    live_status = self.live_data_engine.get_live_status()
                    
                    # Log status every 5 minutes
                    if hasattr(self, '_last_status_log'):
                        time_diff = (datetime.now() - self._last_status_log).seconds
                        if time_diff > 300:  # 5 minutes
                            logger.info(f"🔥 Live Engine Status:")
                            logger.info(f"   📈 Analyses: {live_status['total_analyses']}")
                            logger.info(f"   🎯 Decisions: {live_status['total_decisions']}")
                            logger.info(f"   💾 Symbols tracked: {live_status['symbols_tracked']}")
                            self._last_status_log = datetime.now()
                    else:
                        self._last_status_log = datetime.now()
                    
                    # Update trailing stops
                    await self.position_manager.update_trailing_stops()
                    
                    # Run monitoring checks
                    await self.monitoring_system.check_performance()
                    
                    # Wait before next cycle (live system handles frequency)
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Trading loop error: {e}")
                    await asyncio.sleep(5)
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Trading start error: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the bot"""
        try:
            logger.info("🛑 Shutting down Advanced Trading Bot...")
            self.running = False
            
            # Close components in reverse order
            if self.monitoring_system:
                await self.monitoring_system.close()
            
            if self.position_manager:
                await self.position_manager.close()
            
            if self.exchange_manager:
                await self.exchange_manager.close()
            
            if self.db_manager:
                await self.db_manager.close()
            
            # Send shutdown notification
            if self.notification_manager:
                await self.notification_manager.send_message(
                    "🛑 Advanced Trading Bot safely shut down"
                )
                await self.notification_manager.close()
            
            logger.success("✅ Bot shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")


def signal_handler(signum, frame):
    """Signal handler for graceful shutdown"""
    logger.info(f"📡 Signal {signum} received, shutting down...")
    sys.exit(0)


async def main():
    """Main function"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = None
    try:
        # Create and start bot
        bot = AdvancedTradingBot()
        await bot.initialize()
        await bot.start_trading()
        
    except KeyboardInterrupt:
        logger.info("⌨️ Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        logger.error(traceback.format_exc())
    finally:
        if bot:
            await bot.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Program error: {e}")
        sys.exit(1)