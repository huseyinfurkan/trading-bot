# 🚨 GELİŞTİRME AŞAMASINDA - LÜTFEN KULLANMAYIN / UNDER DEVELOPMENT - PLEASE DO NOT USE

**⚠️ TÜRKÇE:** Bu proje aktif geliştirme aşamasındadır. Gerçek para ile kullanmayın! Test amaçlı dahi olsa kendi sorumluluğunuzdadır.

**⚠️ ENGLISH:** This project is under active development. Do not use with real money! Even for testing purposes, use at your own risk.

---

# 🤖 AI-Powered Crypto Trading Bot

Advanced cryptocurrency trading bot with AI-powered signal filtering and adaptive strategies.

## ⚠️ Important Disclaimers

- **NOT FINANCIAL ADVICE**: This software is for educational and research purposes only
- **USE AT YOUR OWN RISK**: Trading involves substantial risk of loss
- **NO GUARANTEES**: Past performance does not guarantee future results
- **ACTIVE DEVELOPMENT**: Features may change without notice

## 🎯 Features

### 🧠 AI-Powered Signal Analysis
- **Machine Learning Models**: Gradient Boosting & Random Forest classifiers
- **3-Class Prediction**: BUY/SELL/HOLD signal classification
- **Multi-Timeframe Analysis**: 5m and 15m timeframe optimization
- **High Accuracy**: 80%+ model validation accuracy

### 📊 Adaptive Strategy Engine
- **Williams Alligator + MA**: Trend-following strategy (15m timeframe)
- **Bollinger Bands + RSI + Stochastic RSI**: Mean reversion strategy (5m timeframe)
- **Dynamic Strategy Selection**: Automatic regime detection and strategy switching
- **Research-Backed**: Strategies based on proven trading methodologies

### 🔄 Market Regime Detection
- **Trending Markets**: Volatility and momentum analysis
- **Sideways Markets**: Range-bound condition detection
- **Breakout Markets**: Volume and price action confirmation
- **Multi-Timeframe Confirmation**: 15m, 1h, and 4h analysis

### 🛡️ Risk Management
- **Position Sizing**: Dynamic position sizing based on volatility
- **Stop Loss & Take Profit**: Strategy-specific exit conditions
- **Trading Fees**: Comprehensive fee calculation (0.1% per trade)
- **Leverage Control**: Conservative 1.2x-1.5x leverage limits

### 📈 Performance Tracking
- **Comprehensive Backtesting**: Historical performance validation
- **Equity Curve Analysis**: Real-time portfolio tracking
- **Trade Analytics**: Win rate, profit factor, Sharpe ratio
- **Fee Impact Analysis**: Transparent cost calculation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Bybit API credentials (for live trading)

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/your-repo/ai-crypto-trading-bot.git
cd ai-crypto-trading-bot
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys and database credentials
```

4. **Initialize Database**
```bash
python src/core/database_manager.py
```

### Configuration

Edit `config/config.yaml`:

```yaml
database:
  host: localhost
  port: 5432
  name: trading_bot
  user: your_user
  password: your_password

exchanges:
  bybit:
    api_key: your_api_key
    api_secret: your_api_secret
    testnet: true  # Start with testnet!

strategies:
  alligator_ma_momentum:
    timeframe: 15m
    max_hold_hours: 12
  
  bollinger_rsi_stochrsi:
    timeframe: 5m
    max_hold_hours: 6

ai:
  confidence_threshold: 0.70
  retrain_frequency_hours: 24
```

## 📚 Usage

### 🧪 Backtesting
```bash
python backtest_runner.py
```

### 🧠 AI Model Training
```bash
python src/ai/signal_filter.py
```

### 📊 Strategy Analysis
```bash
python debug_strategy.py
```

### 📝 Paper Trading (Recommended)
```bash
python paper_trading.py
```

### 🔴 Live Trading (Use with extreme caution)
```bash
python main.py
```

## 📁 Project Structure

```
src/
├── ai/                     # AI & Machine Learning
│   ├── signal_filter.py    # ML signal filtering
│   ├── market_analyzer.py  # Market analysis
│   └── model_validator.py  # Model validation
├── core/                   # Core components
│   ├── database_manager.py # Database operations
│   ├── risk_manager.py     # Risk management
│   └── live_data_engine.py # Live data processing
├── trading/                # Trading strategies
│   ├── adaptive_strategy_engine.py  # Main strategy engine
│   ├── exchange_manager.py # Exchange integration
│   └── position_manager.py # Position management
└── utils/                  # Utilities
    ├── indicators.py       # Technical indicators
    └── notifications.py    # Alert system
```

## 🎯 Strategy Details

### 📈 Williams Alligator + MA (15m)
- **Market Conditions**: Trending and breakout markets
- **Entry Conditions**: 
  - Price > SMA10 > SMA20 > SMA50 (all MAs aligned)
  - SMA10 rising + momentum confirmation
  - Volume confirmation (>20% above average)
- **Risk/Reward**: 8% profit target, 2.5% stop loss
- **Position Size**: 0.5% risk with 1.5x leverage

### 📊 Bollinger Bands + RSI + Stochastic RSI (5m)
- **Market Conditions**: Sideways and ranging markets
- **Entry Conditions**:
  - RSI < 25 (oversold) + BB position < 0.15 (near lower band)
  - RSI > 75 (overbought) + BB position > 0.85 (near upper band)
  - Volume confirmation (>30% above average)
- **Risk/Reward**: 4% profit target, 1.2% stop loss
- **Position Size**: 0.3% risk with 1.2x leverage

## 🔧 Technical Specifications

### 🧠 AI Models
- **Algorithms**: Gradient Boosting, Random Forest
- **Features**: 13 technical indicators (RSI, MACD, BB, volume, momentum)
- **Training Data**: 56,000+ samples from 4 major cryptocurrencies
- **Validation**: 5-fold cross-validation with 99.7% stability
- **Prediction**: 3-class classification (BUY=2, SELL=1, HOLD=0)

### 📊 Performance Metrics
- **Accuracy**: 80%+ on validation data
- **Precision/Recall**: 0.72+ across all classes
- **F1 Score**: 0.72+ with high stability
- **AUC Score**: 0.71+ indicating good discrimination

### 🛡️ Risk Controls
- **Max Position**: 0.75% of capital per trade
- **Max Leverage**: 1.5x for trends, 1.2x for scalping
- **Confidence Threshold**: 0.70 for signal filtering
- **Trading Fees**: 0.1% entry + 0.1% exit included in calculations

## 📈 Expected Performance

Based on backtesting and optimization:
- **Trade Frequency**: 200-400 trades per 6 months
- **Win Rate**: Target 35-45% (with 3:1 R:R ratios)
- **Maximum Drawdown**: <10% with proper risk management
- **Fee Impact**: 0.6-0.8% of capital (well-controlled)

## ⚠️ Risk Warnings

### 🚨 Market Risks
- **Volatility**: Crypto markets are highly volatile
- **Liquidity**: Low liquidity can cause slippage
- **Market Conditions**: Strategies may underperform in certain conditions

### 🔧 Technical Risks
- **API Failures**: Exchange API issues can affect trading
- **Model Degradation**: AI models may need retraining
- **System Downtime**: Server/internet issues can impact performance

### 💰 Financial Risks
- **Capital Loss**: You can lose all invested capital
- **Leverage Risk**: Leverage amplifies both gains and losses
- **Fee Impact**: High trading frequency increases fee burden

## 🛠️ Development

### 🧪 Testing
```bash
pytest tests/
```

### 📊 Code Quality
```bash
flake8 src/
black src/
```

### 🔍 Debugging
- Enable debug logging in `config.yaml`
- Use `debug_strategy.py` for signal analysis
- Monitor `logs/` directory for detailed output

## 📞 Support

For issues, questions, or contributions:
- **GitHub Issues**: [Create an issue](https://github.com/your-repo/issues)
- **Documentation**: Check `docs/` directory
- **Community**: Join our Discord/Telegram

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Research papers on algorithmic trading strategies
- Open-source technical analysis libraries
- Cryptocurrency exchange APIs
- Machine learning frameworks (scikit-learn, pandas, numpy)

---

**💡 Remember**: This is experimental software. Always test thoroughly on paper trading before considering live trading. Never invest more than you can afford to lose. 
