#!/usr/bin/env python3
"""
Unit Tests for RiskManager
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.risk_manager import RiskManager


class MockDatabaseManager:
    """Mock database manager for testing"""
    
    def __init__(self):
        self.positions = []
        self.market_data = pd.DataFrame()
    
    async def get_positions(self, status='OPEN'):
        return [pos for pos in self.positions if pos.get('status') == status]
    
    async def get_market_data(self, symbol, exchange, timeframe, limit):
        if self.market_data.empty:
            # Generate mock data
            dates = pd.date_range(start='2024-01-01', periods=limit, freq='1H')
            return pd.DataFrame({
                'timestamp': dates,
                'close': np.random.normal(50000, 1000, limit)
            })
        return self.market_data
    
    async def get_performance_stats(self, days=1):
        return {'total_pnl': 0, 'win_rate': 0.6}
    
    async def update_position(self, position_id, updates):
        for pos in self.positions:
            if pos['id'] == position_id:
                pos.update(updates)


@pytest.fixture
def mock_db():
    return MockDatabaseManager()


@pytest.fixture
def risk_config():
    return {
        'max_portfolio_risk': 0.02,
        'max_daily_loss': 0.05,
        'max_open_positions': 10,
        'position_sizing_method': 'kelly_criterion',
        'correlation_limit': 0.7,
        'leverage': {
            'max_leverage': 3,
            'default_leverage': 1,
            'high_confidence_leverage': 2
        }
    }


@pytest.fixture
def risk_manager(mock_db, risk_config):
    return RiskManager(risk_config, mock_db)


class TestRiskManager:
    """Test cases for RiskManager"""
    
    @pytest.mark.asyncio
    async def test_position_size_calculation(self, risk_manager):
        """Test position size calculation"""
        result = await risk_manager.calculate_position_size(
            symbol='BTC/USDT',
            entry_price=50000,
            stop_loss=49000,
            confidence=0.8,
            strategy='swing_trading'
        )
        
        assert isinstance(result, dict)
        assert 'size' in result
        assert 'leverage' in result
        assert 'risk_amount' in result
        assert result['size'] >= 0
        assert 1 <= result['leverage'] <= 3
    
    @pytest.mark.asyncio
    async def test_kelly_criterion_sizing(self, risk_manager):
        """Test Kelly Criterion position sizing"""
        size = await risk_manager._kelly_criterion_sizing(
            risk_amount=1000,
            entry_price=50000,
            stop_loss=49000,
            confidence=0.7
        )
        
        assert isinstance(size, float)
        assert size >= 0
    
    @pytest.mark.asyncio
    async def test_risk_checks_max_positions(self, risk_manager, mock_db):
        """Test maximum positions limit"""
        # Add maximum positions
        mock_db.positions = [
            {'id': i, 'symbol': f'COIN{i}/USDT', 'status': 'OPEN'}
            for i in range(15)  # Exceed limit of 10
        ]
        
        risk_checks = await risk_manager._perform_risk_checks('BTC/USDT', 'swing_trading')
        
        assert not risk_checks['allowed']
        assert 'Maximum open positions' in risk_checks['reason']
    
    @pytest.mark.asyncio
    async def test_correlation_check(self, risk_manager, mock_db):
        """Test correlation checking"""
        # Add existing position
        mock_db.positions = [
            {'id': 1, 'symbol': 'ETH/USDT', 'status': 'OPEN'}
        ]
        
        # Mock correlation calculation to return high correlation
        with patch.object(risk_manager, '_calculate_price_correlation') as mock_corr:
            mock_corr.return_value = {'max_correlation': 0.8, 'correlated_symbol': 'ETH/USDT'}
            
            result = await risk_manager._check_correlation('BTC/USDT')
            
            assert not result['allowed']
            assert 'High correlation' in result['reason']
    
    @pytest.mark.asyncio
    async def test_daily_loss_limit(self, risk_manager):
        """Test daily loss limit checking"""
        # Set high daily loss
        risk_manager.daily_pnl = -6000  # 6% loss on 100k portfolio
        
        risk_checks = await risk_manager._perform_risk_checks('BTC/USDT', 'swing_trading')
        
        assert not risk_checks['allowed']
        assert 'Daily loss limit' in risk_checks['reason']
    
    @pytest.mark.asyncio
    async def test_stop_loss_check(self, risk_manager):
        """Test stop loss checking"""
        position = {
            'side': 'BUY',
            'stop_loss': 49000
        }
        
        # Price below stop loss
        result = await risk_manager.check_stop_loss(position, 48000)
        assert result is True
        
        # Price above stop loss
        result = await risk_manager.check_stop_loss(position, 50000)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_take_profit_check(self, risk_manager):
        """Test take profit checking"""
        position = {
            'side': 'BUY',
            'take_profit': 52000
        }
        
        # Price above take profit
        result = await risk_manager.check_take_profit(position, 53000)
        assert result is True
        
        # Price below take profit
        result = await risk_manager.check_take_profit(position, 51000)
        assert result is False
    
    def test_leverage_calculation(self, risk_manager):
        """Test leverage calculation"""
        # High confidence
        leverage = asyncio.run(risk_manager._calculate_leverage(0.9, 'scalping'))
        assert leverage >= 2
        
        # Low confidence
        leverage = asyncio.run(risk_manager._calculate_leverage(0.5, 'mean_reversion'))
        assert leverage >= 1
    
    def test_risk_amount_calculation(self, risk_manager):
        """Test risk amount calculation"""
        risk_amount = asyncio.run(risk_manager._calculate_risk_amount(0.8, 'swing_trading'))
        
        assert isinstance(risk_amount, float)
        assert risk_amount > 0
        assert risk_amount <= risk_manager.max_portfolio_risk * risk_manager.portfolio_value
    
    @pytest.mark.asyncio
    async def test_price_correlation_computation(self, risk_manager):
        """Test price correlation computation"""
        # Create test data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Highly correlated data
        base_prices = np.random.normal(50000, 1000, 100)
        data1 = pd.DataFrame({'timestamp': dates, 'close': base_prices})
        data2 = pd.DataFrame({'timestamp': dates, 'close': base_prices + np.random.normal(0, 100, 100)})
        
        correlation = risk_manager._compute_correlation(data1, data2)
        
        assert isinstance(correlation, float)
        assert -1 <= correlation <= 1
        assert correlation > 0.8  # Should be highly correlated
    
    @pytest.mark.asyncio
    async def test_portfolio_value_update(self, risk_manager, mock_db):
        """Test portfolio value updating"""
        # Add positions with P&L
        mock_db.positions = [
            {'id': 1, 'symbol': 'BTC/USDT', 'status': 'OPEN', 'pnl': 500},
            {'id': 2, 'symbol': 'ETH/USDT', 'status': 'OPEN', 'pnl': -200}
        ]
        
        await risk_manager._update_portfolio_value()
        
        assert risk_manager.open_positions_count == 2
    
    def test_max_daily_loss_getter(self, risk_manager):
        """Test max daily loss calculation"""
        max_loss = risk_manager.get_max_daily_loss()
        expected = risk_manager.max_daily_loss * risk_manager.portfolio_value
        
        assert max_loss == expected
    
    def test_daily_loss_limit_reached(self, risk_manager):
        """Test daily loss limit checking"""
        # Set loss below limit
        risk_manager.daily_pnl = -3000  # 3% loss
        assert not risk_manager.is_daily_loss_limit_reached()
        
        # Set loss above limit
        risk_manager.daily_pnl = -6000  # 6% loss
        assert risk_manager.is_daily_loss_limit_reached()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])