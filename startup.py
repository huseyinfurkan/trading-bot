#!/usr/bin/env python3
"""
Startup Debug Script
Bot'u test modunda başlatır ve debug yapar
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from loguru import logger

# Simple logging setup for testing
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")


async def test_imports():
    """Test all imports"""
    try:
        logger.info("🔍 Testing imports...")
        
        # Core imports
        from src.core.config_manager import ConfigManager
        from src.core.database_manager import DatabaseManager
        from src.core.bot_coordinator import BotCoordinator
        from src.core.risk_manager import RiskManager
        from src.core.monitoring import MonitoringSystem
        logger.success("✅ Core modules imported successfully")
        
        # Trading imports
        from src.trading.exchange_manager import ExchangeManager
        from src.trading.strategy_engine import StrategyEngine
        from src.trading.position_manager import PositionManager
        logger.success("✅ Trading modules imported successfully")
        
        # AI imports
        from src.ai.signal_filter import AISignalFilter
        from src.ai.market_analyzer import MarketAnalyzer
        from src.ai.confidence_calculator import ConfidenceCalculator
        logger.success("✅ AI modules imported successfully")
        
        # Utils imports
        from src.utils.logger_setup import setup_logging
        from src.utils.notifications import NotificationManager
        logger.success("✅ Utils modules imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import error: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_config():
    """Test configuration loading"""
    try:
        logger.info("🔍 Testing configuration...")
        
        from src.core.config_manager import ConfigManager
        
        config_manager = ConfigManager("config.yaml")
        config = await config_manager.load_config()
        
        logger.success(f"✅ Configuration loaded with {len(config)} sections")
        
        # Test key sections
        required_sections = ['exchanges', 'trading_pairs', 'ai_settings', 'strategies']
        for section in required_sections:
            if section in config:
                logger.info(f"✓ {section} section present")
            else:
                logger.warning(f"⚠️ {section} section missing")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Config test error: {e}")
        logger.error(traceback.format_exc())
        return None


async def test_database():
    """Test database connection"""
    try:
        logger.info("🔍 Testing database...")
        
        from src.core.database_manager import DatabaseManager
        
        db_config = {
            'type': 'sqlite',
            'path': 'data/test_trading_bot.db'
        }
        
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        logger.success("✅ Database initialized successfully")
        
        # Test basic operations
        test_data = {
            'symbol': 'BTC/USDT',
            'exchange': 'binance',
            'timestamp': '2024-01-01 00:00:00',
            'open': 45000,
            'high': 45100,
            'low': 44900,
            'close': 45050,
            'volume': 1000
        }
        
        await db_manager.save_market_data('BTC/USDT', 'binance', '1h', test_data)
        logger.success("✅ Database write test successful")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test error: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_exchange_connection():
    """Test exchange connection (without API keys)"""
    try:
        logger.info("🔍 Testing exchange connection...")
        
        from src.trading.exchange_manager import ExchangeManager
        
        # Test config without real API keys
        exchanges_config = {
            'binance': {
                'api_key': 'test_key',
                'secret': 'test_secret',
                'sandbox': True,
                'enable_test': True
            }
        }
        
        exchange_manager = ExchangeManager(exchanges_config)
        await exchange_manager.initialize()
        
        logger.success("✅ Exchange manager initialized (test mode)")
        
        await exchange_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Exchange test error: {e}")
        logger.error(traceback.format_exc())
        return False


async def test_ai_components():
    """Test AI components"""
    try:
        logger.info("🔍 Testing AI components...")
        
        from src.ai.signal_filter import AISignalFilter
        from src.ai.market_analyzer import MarketAnalyzer
        from src.ai.confidence_calculator import ConfidenceCalculator
        from src.core.database_manager import DatabaseManager
        
        # Mock database for testing
        db_config = {'type': 'sqlite', 'path': ':memory:'}
        db_manager = DatabaseManager(db_config)
        await db_manager.initialize()
        
        # Test AI components
        ai_config = {
            'confidence_threshold': 0.75,
            'signal_strength_min': 0.65,
            'technical_weight': 0.5,
            'sentiment_weight': 0.3,
            'fundamental_weight': 0.2
        }
        
        signal_filter = AISignalFilter(ai_config, db_manager)
        await signal_filter.initialize()
        logger.success("✅ AI Signal Filter initialized")
        
        market_config = {
            'bull_market': {'strategies': ['trend_following']},
            'bear_market': {'strategies': ['mean_reversion']},
            'sideways_market': {'strategies': ['scalping']}
        }
        
        market_analyzer = MarketAnalyzer(market_config, db_manager)
        logger.success("✅ Market Analyzer initialized")
        
        confidence_calculator = ConfidenceCalculator(ai_config, db_manager)
        logger.success("✅ Confidence Calculator initialized")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ AI components test error: {e}")
        logger.error(traceback.format_exc())
        return False


async def run_full_debug():
    """Run comprehensive debug test"""
    logger.info("🚀 Starting comprehensive debug test...")
    
    tests = [
        ("Import Test", test_imports),
        ("Config Test", test_config),
        ("Database Test", test_database),
        ("Exchange Test", test_exchange_connection),
        ("AI Components Test", test_ai_components)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.success(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} CRASHED: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("DEBUG TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("🎉 All tests passed! Bot is ready to run!")
        return True
    else:
        logger.error(f"💥 {total - passed} tests failed. Please fix issues before running.")
        return False


async def main():
    """Main debug function"""
    try:
        logger.info("🔧 Advanced Trading Bot - Debug Mode")
        logger.info("This script will test all components before running the bot")
        
        success = await run_full_debug()
        
        if success:
            logger.info("\n🚀 Debug completed successfully!")
            logger.info("You can now run: python main.py")
        else:
            logger.error("\n💥 Debug found issues that need to be fixed")
            return 1
            
        return 0
        
    except Exception as e:
        logger.error(f"❌ Debug script crashed: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)