import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # Trading Parameters
    TRADING_PAIRS = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT',
        'DOT/USDT', 'LINK/USDT', 'MATIC/USDT', 'AVAX/USDT', 'UNI/USDT'
    ]
    
    # Risk Management
    MAX_POSITION_SIZE = 0.1  # Total portfolio'nun %10'u
    MAX_DAILY_LOSS = 0.05    # Günlük maksimum kayıp %5
    MIN_CONFIDENCE_THRESHOLD = 0.7  # Minimum güven eşiği
    TAKE_PROFIT_CONFIDENCE = 0.8    # Take profit için güven eşiği
    
    # Timeframes
    TIMEFRAMES = {
        'scalping': '1m',
        'short_term': '5m',
        'medium_term': '15m',
        'long_term': '1h',
        'swing': '4h'
    }
    
    # Strategy Parameters
    STRATEGIES = {
        'scalping': {
            'enabled': True,
            'max_hold_time': 300,  # 5 dakika
            'min_profit': 0.002,   # %0.2
            'max_loss': 0.001      # %0.1
        },
        'swing': {
            'enabled': True,
            'max_hold_time': 86400 * 7,  # 7 gün
            'min_profit': 0.05,    # %5
            'max_loss': 0.03       # %3
        }
    }
    
    # AI Model Parameters
    AI_MODEL_CONFIG = {
        'prediction_threshold': 0.7,
        'retrain_interval': 24,  # saat
        'min_data_points': 1000,
        'confidence_weight': 0.3
    }
    
    # Market Analysis
    MARKET_CONDITIONS = {
        'trending': 'trend_following',
        'ranging': 'mean_reversion',
        'volatile': 'scalping',
        'stable': 'swing'
    }
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'trading_bot.log'
    
    # Web Interface
    WEB_PORT = 8050
    WEB_HOST = '0.0.0.0'