#!/usr/bin/env python3
"""
Paper Trading Runner
Sandbox environment ile gerçek zamanlı paper trading
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.risk_manager import RiskManager
from src.trading.exchange_manager import ExchangeManager
from src.trading.strategy_engine import StrategyEngine
from src.trading.position_manager import PositionManager
from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer
from src.ai.confidence_calculator import ConfidenceCalculator
from src.core.live_data_engine import LiveDataEngine
from src.core.monitoring import MonitoringSystem
from src.utils.notifications import NotificationManager
from src.utils.logger_setup import setup_logger

# Setup logger
logger = setup_logger('paper_trading', 'logs/paper_trading.log')


class PaperTradingBot:
    """Paper trading bot with sandbox environment"""
    
    def __init__(self):
        self.config_manager = None
        self.db_manager = None
        self.risk_manager = None
        self.exchange_manager = None
        self.strategy_engine = None
        self.position_manager = None
        self.ai_signal_filter = None
        self.market_analyzer = None
        self.confidence_calculator = None
        self.live_data_engine = None
        self.monitoring_system = None
        self.notification_manager = None
        
        # Paper trading specific
        self.paper_balance = {}
        self.paper_positions = {}
        self.start_time = datetime.now()
        self.initial_balance = 10000  # $10,000 starting capital
        
    async def initialize(self):
        """Initialize paper trading environment"""
        try:
            logger.info("🚀 Paper Trading Bot başlatılıyor...")
            
            # Load configuration
            self.config_manager = ConfigManager('config/config.yaml')
            await self.config_manager.load_config()
            config = self.config_manager.config
            
            # Force sandbox mode for paper trading
            for exchange_name, exchange_config in config['exchanges'].items():
                exchange_config['sandbox'] = True
                logger.info(f"🧪 {exchange_name} sandbox mode enabled")
            
            # Initialize database
            self.db_manager = DatabaseManager(config['database'])
            await self.db_manager.initialize()
            
            # Initialize components
            self.risk_manager = RiskManager(config['risk_management'], self.db_manager)
            
            self.exchange_manager = ExchangeManager(config['exchanges'])
            await self.exchange_manager.initialize()
            
            # Initialize AI components
            self.market_analyzer = MarketAnalyzer(config['market_analysis'], self.db_manager)
            self.ai_signal_filter = AISignalFilter(config['ai'], self.db_manager, self.exchange_manager)
            self.confidence_calculator = ConfidenceCalculator(config['ai'], self.db_manager)
            
            # Initialize trading components
            self.strategy_engine = StrategyEngine(
                config['strategies'],
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
                config['live_data'],
                self.exchange_manager,
                self.market_analyzer,
                self.ai_signal_filter,
                self.strategy_engine,
                self.position_manager,
                self.risk_manager
            )
            
            # Initialize monitoring and notifications
            self.monitoring_system = MonitoringSystem(
                config['monitoring'],
                self.db_manager,
                None  # notifications will be initialized separately
            )
            
            self.notification_manager = NotificationManager(config['notifications'])
            await self.notification_manager.initialize()
            
            # Setup paper trading balance
            self._setup_paper_balance()
            
            logger.success("✅ Paper Trading Bot initialized")
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
    
    def _setup_paper_balance(self):
        """Setup initial paper trading balance"""
        self.paper_balance = {
            'USDT': {
                'free': self.initial_balance,
                'used': 0,
                'total': self.initial_balance
            }
        }
        
        logger.info(f"💰 Paper trading balance: ${self.initial_balance:,.2f} USDT")
    
    async def start_paper_trading(self, symbols: List[str]):
        """Start paper trading session"""
        try:
            logger.info(f"📈 Paper trading başlatılıyor: {', '.join(symbols)}")
            
            # Send startup notification
            await self.notification_manager.send_message(
                f"🤖 **PAPER TRADING STARTED**\n\n"
                f"💰 Initial Balance: ${self.initial_balance:,.2f}\n"
                f"📊 Symbols: {', '.join(symbols)}\n"
                f"🕐 Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                "info", "high"
            )
            
            # Start live data engine
            await self.live_data_engine.start_live_analysis()
            
            # Start monitoring
            await self.monitoring_system.start()
            
            # Main paper trading loop
            await self._paper_trading_loop(symbols)
            
        except Exception as e:
            logger.error(f"❌ Paper trading error: {e}")
            await self.notification_manager.send_error_alert(str(e), "PaperTradingBot")
    
    async def _paper_trading_loop(self, symbols: List[str]):
        """Main paper trading monitoring loop"""
        try:
            logger.info("🔄 Paper trading monitoring loop started")
            
            while True:
                try:
                    # Monitor positions
                    await self._update_paper_positions()
                    
                    # Check performance
                    await self._check_performance()
                    
                    # Generate periodic reports
                    if datetime.now().minute % 15 == 0:  # Every 15 minutes
                        await self._send_status_update()
                    
                    # Sleep for 1 minute
                    await asyncio.sleep(60)
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Paper trading stopped by user")
                    break
                except Exception as e:
                    logger.error(f"❌ Paper trading loop error: {e}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            logger.error(f"❌ Paper trading loop fatal error: {e}")
    
    async def _update_paper_positions(self):
        """Update paper trading positions"""
        try:
            # Get current positions
            current_positions = await self.position_manager.get_open_positions()
            
            for position in current_positions:
                symbol = position['symbol']
                current_price = await self.exchange_manager.get_real_time_data(symbol)
                
                if current_price:
                    # Update position with current price
                    position['current_price'] = current_price['price']
                    position['pnl'] = self._calculate_paper_pnl(position, current_price['price'])
                    
                    # Update paper balance
                    self._update_paper_balance(position)
                    
        except Exception as e:
            logger.error(f"❌ Paper position update error: {e}")
    
    def _calculate_paper_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate paper trading P&L"""
        try:
            entry_price = position['entry_price']
            size = position['size']
            side = position['side']
            
            if side == 'BUY':
                return (current_price - entry_price) * size
            else:  # SELL
                return (entry_price - current_price) * size
                
        except Exception as e:
            logger.error(f"❌ Paper P&L calculation error: {e}")
            return 0.0
    
    def _update_paper_balance(self, position: Dict):
        """Update paper trading balance"""
        try:
            # This would update the virtual balance based on position changes
            pass
            
        except Exception as e:
            logger.error(f"❌ Paper balance update error: {e}")
    
    async def _check_performance(self):
        """Check paper trading performance"""
        try:
            # Get all positions
            positions = await self.position_manager.get_open_positions()
            
            total_pnl = 0
            for position in positions:
                total_pnl += position.get('pnl', 0)
            
            current_balance = self.initial_balance + total_pnl
            performance_pct = (total_pnl / self.initial_balance) * 100
            
            # Log performance
            if abs(performance_pct) > 5:  # Significant change
                logger.info(f"📊 Paper Trading Performance: {performance_pct:+.2f}% (${total_pnl:+,.2f})")
                
        except Exception as e:
            logger.error(f"❌ Performance check error: {e}")
    
    async def _send_status_update(self):
        """Send periodic status update"""
        try:
            # Get current statistics
            positions = await self.position_manager.get_open_positions()
            total_pnl = sum(pos.get('pnl', 0) for pos in positions)
            current_balance = self.initial_balance + total_pnl
            performance_pct = (total_pnl / self.initial_balance) * 100
            
            runtime = datetime.now() - self.start_time
            hours_running = runtime.total_seconds() / 3600
            
            message = (
                f"📊 **PAPER TRADING UPDATE**\n\n"
                f"⏱️ Runtime: {hours_running:.1f} hours\n"
                f"💰 Current Balance: ${current_balance:,.2f}\n"
                f"📈 P&L: ${total_pnl:+,.2f} ({performance_pct:+.2f}%)\n"
                f"📊 Open Positions: {len(positions)}\n"
                f"🕐 Update Time: {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await self.notification_manager.send_message(message, "summary", "normal")
            
        except Exception as e:
            logger.error(f"❌ Status update error: {e}")
    
    async def stop_paper_trading(self):
        """Stop paper trading and generate final report"""
        try:
            logger.info("🛑 Paper trading stopping...")
            
            # Stop live data engine
            if self.live_data_engine:
                await self.live_data_engine.stop()
            
            # Stop monitoring
            if self.monitoring_system:
                await self.monitoring_system.stop()
            
            # Generate final report
            await self._generate_final_report()
            
            logger.success("✅ Paper trading stopped")
            
        except Exception as e:
            logger.error(f"❌ Stop paper trading error: {e}")
    
    async def _generate_final_report(self):
        """Generate final paper trading report"""
        try:
            # Calculate final statistics
            positions = await self.position_manager.get_open_positions()
            total_pnl = sum(pos.get('pnl', 0) for pos in positions)
            final_balance = self.initial_balance + total_pnl
            performance_pct = (total_pnl / self.initial_balance) * 100
            
            runtime = datetime.now() - self.start_time
            days_running = runtime.days
            hours_running = runtime.total_seconds() / 3600
            
            # Get all completed trades from database
            # This would fetch actual trade history
            
            report = (
                f"📋 **PAPER TRADING FINAL REPORT**\n\n"
                f"📅 Duration: {days_running} days, {hours_running:.1f} hours\n"
                f"💰 Initial Balance: ${self.initial_balance:,.2f}\n"
                f"💰 Final Balance: ${final_balance:,.2f}\n"
                f"📈 Total P&L: ${total_pnl:+,.2f}\n"
                f"📊 Performance: {performance_pct:+.2f}%\n"
                f"📊 Open Positions: {len(positions)}\n"
                f"🕐 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await self.notification_manager.send_message(report, "summary", "high")
            
            logger.info("📋 Final report generated")
            
        except Exception as e:
            logger.error(f"❌ Final report error: {e}")
    
    async def close(self):
        """Close all connections"""
        try:
            if self.live_data_engine:
                await self.live_data_engine.stop()
            if self.monitoring_system:
                await self.monitoring_system.stop()
            if self.exchange_manager:
                await self.exchange_manager.close()
            if self.db_manager:
                await self.db_manager.close()
            if self.notification_manager:
                await self.notification_manager.close()
                
            logger.info("✅ Paper trading bot closed")
            
        except Exception as e:
            logger.error(f"❌ Close error: {e}")


async def main():
    """Main paper trading function"""
    bot = PaperTradingBot()
    
    try:
        await bot.initialize()
        
        # Default symbols for paper trading
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']
        
        print("🤖 ADVANCED TRADING BOT - PAPER TRADING")
        print("=" * 50)
        print(f"💰 Initial Balance: ${bot.initial_balance:,.2f}")
        print(f"📊 Symbols: {', '.join(symbols)}")
        print(f"🧪 Mode: SANDBOX (Paper Trading)")
        print()
        
        input("Press Enter to start paper trading (Ctrl+C to stop)...")
        
        # Start paper trading
        await bot.start_paper_trading(symbols)
        
    except KeyboardInterrupt:
        print("\n🛑 Paper trading interrupted by user")
    except Exception as e:
        print(f"\n❌ Paper trading error: {e}")
    finally:
        await bot.stop_paper_trading()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())