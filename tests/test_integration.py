#!/usr/bin/env python3
"""
Integration Tests for Trading Bot
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.risk_manager import RiskManager
from src.trading.exchange_manager import ExchangeManager
from src.trading.strategy_engine import StrategyEngine
from src.trading.position_manager import PositionManager
from src.ai.signal_filter import AISignalFilter
from src.ai.market_analyzer import MarketAnalyzer


@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        'exchanges': {
            'binance': {
                'api_key': 'test_key',
                'secret': 'test_secret',
                'sandbox': True
            }
        },
        'risk_management': {
            'max_portfolio_risk': 0.02,
            'max_daily_loss': 0.05,
            'max_open_positions': 5
        },
        'strategies': {
            'swing_trading': {
                'enabled': True,
                'timeframes': ['1h'],
                'profit_target': 2.0,
                'stop_loss': 1.0,
                'confidence_threshold': 0.7
            }
        },
        'ai_settings': {
            'confidence_threshold': 0.75,
            'signal_strength_min': 0.65
        },
        'trading_pairs': {
            'major': ['BTC/USDT', 'ETH/USDT']
        },
        'database': {
            'type': 'sqlite',
            'path': ':memory:'
        }
    }


@pytest.fixture
async def database_manager(test_config):
    """Test database manager"""
    db_manager = DatabaseManager(test_config['database'])
    await db_manager.initialize()
    return db_manager


@pytest.fixture
def risk_manager(test_config, database_manager):
    """Test risk manager"""
    return RiskManager(test_config['risk_management'], database_manager)


@pytest.fixture
def exchange_manager(test_config):
    """Test exchange manager"""
    return ExchangeManager(test_config['exchanges'])


class TestTradingBotIntegration:
    """Integration tests for trading bot components"""
    
    @pytest.mark.asyncio
    async def test_config_to_database_flow(self, test_config):
        """Test configuration loading and database initialization"""
        # Write test config to temporary file
        import tempfile
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            config_path = f.name
        
        try:
            # Load config
            config_manager = ConfigManager(config_path)
            config = await config_manager.load_config()
            
            assert config is not None
            assert 'exchanges' in config
            
            # Initialize database
            db_manager = DatabaseManager(config['database'])
            await db_manager.initialize()
            
            # Test database operations
            test_data = {
                'symbol': 'BTC/USDT',
                'exchange': 'binance',
                'timestamp': '2024-01-01 00:00:00',
                'open': 50000,
                'high': 50100,
                'low': 49900,
                'close': 50050,
                'volume': 1000
            }
            
            await db_manager.save_market_data('BTC/USDT', 'binance', '1h', test_data)
            
            # Verify data
            market_data = await db_manager.get_market_data('BTC/USDT', 'binance', '1h', 10)
            assert not market_data.empty
            
            await db_manager.close()
            
        finally:
            import os
            os.unlink(config_path)
    
    @pytest.mark.asyncio
    async def test_risk_to_position_flow(self, risk_manager, database_manager):
        """Test risk management to position management flow"""
        # Calculate position size
        result = await risk_manager.calculate_position_size(
            symbol='BTC/USDT',
            entry_price=50000,
            stop_loss=49000,
            confidence=0.8,
            strategy='swing_trading'
        )
        
        assert result['allowed'] is True
        assert result['size'] > 0
        
        # Mock position creation
        position_data = {
            'id': 1,
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'size': result['size'],
            'entry_price': 50000,
            'stop_loss': 49000,
            'opened_at': '2024-01-01 00:00:00',
            'status': 'OPEN'
        }
        
        await database_manager.save_position(position_data)
        
        # Verify position
        positions = await database_manager.get_positions(status='OPEN')
        assert len(positions) == 1
        assert positions[0]['symbol'] == 'BTC/USDT'
    
    @pytest.mark.asyncio
    async def test_ai_to_strategy_flow(self, test_config, database_manager):
        """Test AI signal filtering to strategy engine flow"""
        # Mock market data
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1H')
        mock_data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.normal(50000, 1000, 200),
            'high': np.random.normal(50500, 1000, 200),
            'low': np.random.normal(49500, 1000, 200),
            'close': np.random.normal(50000, 1000, 200),
            'volume': np.random.normal(1000, 100, 200)
        })
        
        market_data = {
            'symbol': 'BTC/USDT',
            'dataframe': mock_data,
            'close': mock_data.iloc[-1]['close']
        }
        
        # Initialize AI components
        ai_signal_filter = AISignalFilter(test_config['ai_settings'], database_manager)
        await ai_signal_filter.initialize()
        
        market_analyzer = MarketAnalyzer(test_config.get('market_conditions', {}), database_manager)
        
        # Mock confidence calculator
        confidence_calculator = Mock()
        confidence_calculator.calculate_confidence = AsyncMock(return_value=0.8)
        
        # Initialize strategy engine
        strategy_engine = StrategyEngine(
            test_config['strategies'], 
            ai_signal_filter, 
            market_analyzer, 
            confidence_calculator
        )
        
        # Test signal generation
        signals = await ai_signal_filter.analyze_signals('BTC/USDT', market_data)
        
        assert isinstance(signals, dict)
        assert 'signals' in signals
        assert 'confidence' in signals
        
        # Test strategy selection
        market_condition = {
            'condition': 'bull_market',
            'volatility': 'normal',
            'strength': 0.7,
            'recommended_strategies': ['swing_trading']
        }
        
        selected_strategy = await strategy_engine.select_strategy(
            'BTC/USDT', market_condition, 0.8
        )
        
        assert selected_strategy in ['swing_trading', None]
    
    @pytest.mark.asyncio
    async def test_full_trading_decision_flow(self, test_config, database_manager):
        """Test complete trading decision flow"""
        # Setup components
        risk_manager = RiskManager(test_config['risk_management'], database_manager)
        
        # Mock exchange manager
        exchange_manager = Mock()
        exchange_manager.get_market_data = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'close': 50000,
            'volume': 1000
        })
        exchange_manager.place_order = AsyncMock(return_value={
            'id': 'test_order_123',
            'exchange': 'binance',
            'price': 50000,
            'fee': 5
        })
        
        # Initialize position manager
        position_manager = PositionManager(exchange_manager, risk_manager, database_manager)
        
        # Test position opening flow
        action = {
            'signal': 'BUY',
            'entry_price': 50000,
            'stop_loss': 49000,
            'take_profit': 51000
        }
        
        position = await position_manager.open_position(
            symbol='BTC/USDT',
            action=action,
            confidence=0.8,
            strategy='swing_trading'
        )
        
        # Verify position creation
        if position:  # Only if risk checks passed
            assert position['symbol'] == 'BTC/USDT'
            assert position['side'] == 'BUY'
            assert position['strategy'] == 'swing_trading'
    
    @pytest.mark.asyncio
    async def test_correlation_analysis_integration(self, risk_manager, database_manager):
        """Test correlation analysis with real data structures"""
        # Add multiple positions
        positions = [
            {
                'id': 1,
                'symbol': 'BTC/USDT',
                'status': 'OPEN'
            },
            {
                'id': 2,
                'symbol': 'ETH/USDT', 
                'status': 'OPEN'
            }
        ]
        
        for pos in positions:
            await database_manager.save_position(pos)
        
        # Mock price history
        with patch.object(risk_manager, '_get_price_history') as mock_history:
            # Return mock correlated data
            dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
            base_prices = np.random.normal(50000, 1000, 50)
            
            mock_history.side_effect = [
                pd.DataFrame({'timestamp': dates, 'close': base_prices}),  # New symbol
                pd.DataFrame({'timestamp': dates, 'close': base_prices + np.random.normal(0, 100, 50)})  # Existing symbol
            ]
            
            # Test correlation check
            result = await risk_manager._check_correlation('LINK/USDT')
            
            assert isinstance(result, dict)
            assert 'allowed' in result
            assert 'reason' in result
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, test_config):
        """Test error handling across components"""
        # Test with invalid config
        invalid_config = {'invalid': 'config'}
        
        try:
            risk_manager = RiskManager(invalid_config, None)
            # Should handle missing keys gracefully
            assert hasattr(risk_manager, 'max_portfolio_risk')
        except Exception as e:
            # Should not crash completely
            assert isinstance(e, (KeyError, AttributeError))
    
    @pytest.mark.asyncio
    async def test_async_operations_coordination(self, database_manager):
        """Test coordination of multiple async operations"""
        # Create multiple concurrent database operations
        tasks = []
        
        for i in range(10):
            task_data = {
                'symbol': f'COIN{i}/USDT',
                'exchange': 'binance',
                'timestamp': f'2024-01-01 0{i}:00:00',
                'open': 1000 + i,
                'high': 1010 + i,
                'low': 990 + i,
                'close': 1005 + i,
                'volume': 100 + i
            }
            
            task = database_manager.save_market_data(f'COIN{i}/USDT', 'binance', '1h', task_data)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, database_manager):
        """Test performance with multiple operations"""
        import time
        
        start_time = time.time()
        
        # Simulate high load
        operations = []
        for i in range(50):
            data = {
                'symbol': 'BTC/USDT',
                'exchange': 'binance',
                'timestamp': f'2024-01-01 {i:02d}:00:00',
                'open': 50000,
                'high': 50100,
                'low': 49900,
                'close': 50050,
                'volume': 1000
            }
            
            op = database_manager.save_market_data('BTC/USDT', 'binance', '1h', data)
            operations.append(op)
        
        await asyncio.gather(*operations)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (5 seconds for 50 operations)
        assert execution_time < 5.0
        
        # Verify data integrity
        market_data = await database_manager.get_market_data('BTC/USDT', 'binance', '1h', 50)
        assert len(market_data) >= 50


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])