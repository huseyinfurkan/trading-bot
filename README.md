# 🤖 AI-Powered Multi-Crypto Trading Bot

Advanced trading bot with real-time AI signals, comprehensive risk management, and multi-exchange support.

## 🚀 Features

### 🤖 AI & Machine Learning
- **Ensemble ML Models**: Gradient Boosting + Random Forest
- **Real-time Signal Generation**: Technical indicators + ML predictions
- **Dynamic Confidence Scoring**: Adaptive signal filtering
- **Model Training**: Bybit API data for training

### 📊 Trading Strategies
- **Adaptive Strategy Engine**: Market regime detection
- **Multi-Strategy Support**: Alligator + MA, Bollinger + RSI + Stochastic
- **Bayesian Optimization**: Parameter tuning with scikit-optimize
- **Real-time Strategy Selection**: Based on market conditions

### 🛡️ Risk Management
- **Portfolio Risk Control**: Max portfolio/position risk limits
- **Dynamic Correlation Analysis**: High-frequency correlation measurement
- **Real-time Order Book Analysis**: Slippage calculation from order book depth
- **Funding Rate Integration**: Real-time funding rate from exchanges

### 🔄 Real-time Data
- **WebSocket Integration**: Live market data streams
- **Multi-Exchange Support**: Bybit, Binance, OKX
- **Order Book Analysis**: Real-time liquidity assessment
- **Market Regime Detection**: Trending, sideways, volatile markets

### 📈 Performance & Monitoring
- **System Health Monitoring**: CPU, memory, disk usage
- **Performance Metrics**: Sharpe ratio, drawdown, win rate
- **Error Handling**: Circuit breaker pattern with retry logic
- **Comprehensive Logging**: Structured logging with loguru

## 🏗️ Architecture

```
trading-bot/
├── src/
│   ├── core/                 # Core components
│   │   ├── config_manager.py    # Configuration management
│   │   ├── database_manager.py  # SQLite database
│   │   ├── risk_manager.py      # Risk management
│   │   ├── live_data_engine.py  # Real-time data processing
│   │   ├── monitoring.py        # System monitoring
│   │   └── error_handler.py     # Error handling
│   ├── ai/                   # AI components
│   │   ├── signal_filter.py     # ML signal generation
│   │   ├── market_analyzer.py   # Market analysis
│   │   └── confidence_calculator.py # Signal confidence
│   ├── trading/              # Trading components
│   │   ├── exchange_manager.py  # Exchange integration
│   │   ├── position_manager.py  # Position management
│   │   └── adaptive_strategy_engine.py # Strategy engine
│   └── utils/                # Utilities
│       ├── notifications.py     # Telegram/Discord alerts
│       └── logger_setup.py      # Logging configuration
├── config/
│   └── config.yaml           # Main configuration
├── scripts/
│   └── train_models.py       # Model training script
└── main.py                   # Main entry point
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/huseyinfurkan/trading-bot.git
cd trading-bot

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file with your API credentials:

```env
# Bybit API (Primary exchange)
BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET=your_bybit_secret

# Binance API (Optional)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

# OKX API (Optional)
OKX_API_KEY=your_okx_api_key
OKX_SECRET=your_okx_secret
OKX_PASSPHRASE=your_okx_passphrase
```

### 3. Model Training

```bash
# Train ML models with Bybit data
python scripts/train_models.py
```

### 4. Start Trading Bot

```bash
# Start the bot
python main.py
```

## ⚙️ Configuration

### Trading Parameters

```yaml
trading:
  mode: "live"  # paper, live
  symbols:
    - "BTC/USDT"
    - "ETH/USDT"
    - "BNB/USDT"
    - "ADA/USDT"
  
  risk_management:
    max_portfolio_risk: 0.02    # 2% max portfolio risk
    max_position_risk: 0.01     # 1% max position risk
    max_daily_loss: 0.05        # 5% max daily loss
    correlation_threshold: 0.7   # Correlation limit
```

### AI Configuration

```yaml
ai:
  signal_weights:
    technical: 0.3
    ml: 0.4
    volume: 0.2
    regime: 0.1
  
  confidence_threshold: 0.6
  ml_probability_min: 0.55
```

## 📊 Performance Metrics

The bot tracks comprehensive performance metrics:

- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Calmar Ratio**: Annual return / Maximum drawdown

## 🔧 Advanced Features

### Real-time Order Book Analysis
- Dynamic slippage calculation based on order book depth
- Position-specific slippage estimation
- Real-time funding rate integration

### High-frequency Correlation
- 1-minute data for correlation analysis
- Real-time correlation with existing positions
- Dynamic correlation threshold adjustment

### Bayesian Optimization
- Automated parameter tuning
- Performance-based strategy selection
- Config persistence for optimized parameters

## 🛡️ Safety Features

- **Circuit Breaker**: Automatic shutdown on excessive losses
- **Rate Limiting**: Exchange API rate limit compliance
- **Error Recovery**: Automatic retry with exponential backoff
- **Data Validation**: Comprehensive input validation
- **Secure API Handling**: Environment variable configuration

## 📝 Logging

Comprehensive logging with different levels:

```python
# Info level - General operations
logger.info("🚀 Bot started successfully")

# Warning level - Potential issues
logger.warning("⚠️ High correlation detected")

# Error level - Errors that need attention
logger.error("❌ API connection failed")

# Debug level - Detailed debugging info
logger.debug("📊 Processing market data")
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the configuration examples

---

**🚀 Ready to trade with AI-powered precision!** 
