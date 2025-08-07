#!/usr/bin/env python3
"""
Model Training Script
Uses Bybit API via CCXT for training ML models
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.trading.exchange_manager import ExchangeManager
from src.ai.signal_filter import AISignalFilter
from loguru import logger


class ModelTrainer:
    """Model trainer using Bybit API via CCXT"""
    
    def __init__(self):
        """Initialize model trainer with Bybit focus"""
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.db_manager = DatabaseManager(self.config['database'])
        self.exchange_manager = ExchangeManager(self.config['exchanges'])
        self.ai_signal_filter = AISignalFilter(self.config['ai'], self.db_manager, self.exchange_manager)
        
        # Bybit-specific training parameters
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        self.timeframes = ['1h', '4h', '1d']
        self.lookback_days = 365  # 1 year of data
        self.min_data_points = 1000
        
        # Model parameters
        self.test_size = 0.2
        self.random_state = 42
        
        # Bybit exchange instance
        self.bybit_exchange = None
        
        logger.info("🤖 Model Trainer initialized with Bybit API")
    
    async def initialize(self):
        """Initialize components and Bybit connection"""
        try:
            await self.db_manager.initialize()
            await self.exchange_manager.initialize()
            await self.ai_signal_filter.initialize()
            
            # Initialize Bybit exchange specifically
            await self._initialize_bybit_exchange()
            
            logger.info("✅ Model Trainer components initialized with Bybit")
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
    
    async def _initialize_bybit_exchange(self):
        """Initialize Bybit exchange connection"""
        try:
            import ccxt
            
            # Get Bybit configuration
            bybit_config = self.config.get('exchanges', {}).get('bybit', {})
            
            # Create Bybit exchange instance
            self.bybit_exchange = ccxt.bybit({
                'apiKey': bybit_config.get('api_key', ''),
                'secret': bybit_config.get('api_secret', ''),
                'sandbox': bybit_config.get('testnet', True),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            })
            
            # Test connection
            await self.bybit_exchange.load_markets()
            logger.info("✅ Bybit exchange connection established")
            
        except Exception as e:
            logger.error(f"❌ Bybit exchange initialization error: {e}")
            raise
    
    async def train_all_models(self):
        """Train models for all symbols using Bybit data"""
        try:
            logger.info("🚀 Starting model training with Bybit API")
            
            for symbol in self.symbols:
                logger.info(f"📊 Training models for {symbol} using Bybit data")
                await self.train_symbol_models(symbol)
            
            logger.info("✅ All models trained successfully with Bybit data")
            
        except Exception as e:
            logger.error(f"❌ Model training error: {e}")
    
    async def train_symbol_models(self, symbol: str):
        """Train models for a specific symbol using Bybit data"""
        try:
            # Get historical data from Bybit
            historical_data = await self._get_bybit_historical_data(symbol)
            
            if historical_data is None or len(historical_data) < self.min_data_points:
                logger.warning(f"⚠️ Insufficient Bybit data for {symbol}: {len(historical_data) if historical_data is not None else 0} points")
                return
            
            logger.info(f"📈 Got {len(historical_data)} Bybit data points for {symbol}")
            
            # Prepare features and labels
            features, labels = await self._prepare_training_data(historical_data, symbol)
            
            if features is None or labels is None:
                logger.error(f"❌ Failed to prepare training data for {symbol}")
                return
            
            logger.info(f"🔧 Prepared {len(features)} training samples for {symbol}")
            
            # Train models
            await self._train_models_for_symbol(symbol, features, labels)
            
            logger.info(f"✅ Models trained successfully for {symbol} with Bybit data")
            
        except Exception as e:
            logger.error(f"❌ Symbol training error for {symbol}: {e}")
    
    async def _get_bybit_historical_data(self, symbol: str) -> pd.DataFrame:
        """Get historical data from Bybit API"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            logger.info(f"📊 Fetching Bybit data for {symbol} from {start_date} to {end_date}")
            
            all_data = []
            
            for timeframe in self.timeframes:
                try:
                    # Calculate limit based on timeframe
                    if timeframe == '1h':
                        limit = min(1000, self.lookback_days * 24)
                    elif timeframe == '4h':
                        limit = min(1000, self.lookback_days * 6)
                    elif timeframe == '1d':
                        limit = min(1000, self.lookback_days)
                    else:
                        limit = 1000
                    
                    # Fetch data from Bybit
                    ohlcv = await self.bybit_exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=limit
                    )
                    
                    if ohlcv and len(ohlcv) > 0:
                        # Convert to DataFrame
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df['timeframe'] = timeframe
                        all_data.append(df)
                        
                        logger.info(f"✅ Got {len(df)} {timeframe} data points for {symbol} from Bybit")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get {timeframe} data for {symbol} from Bybit: {e}")
                    continue
            
            if not all_data:
                logger.error(f"❌ No Bybit data retrieved for {symbol}")
                return None
            
            # Combine all timeframes
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data = combined_data.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
            
            logger.info(f"📊 Combined {len(combined_data)} Bybit data points for {symbol}")
            
            return combined_data
            
        except Exception as e:
            logger.error(f"❌ Bybit historical data fetch error for {symbol}: {e}")
            return None
    
    async def _prepare_training_data(self, data: pd.DataFrame, symbol: str) -> tuple:
        """Prepare features and labels for training"""
        try:
            # Add technical indicators
            data_with_indicators = await self._add_technical_indicators(data)
            
            if data_with_indicators is None or len(data_with_indicators) < 100:
                logger.error(f"❌ Insufficient data after adding indicators for {symbol}")
                return None, None
            
            # Create features
            features = await self._create_features(data_with_indicators)
            
            if features is None or len(features) < 100:
                logger.error(f"❌ Failed to create features for {symbol}")
                return None, None
            
            # Create labels (future price movement)
            labels = await self._create_labels(data_with_indicators)
            
            if labels is None or len(labels) < 100:
                logger.error(f"❌ Failed to create labels for {symbol}")
                return None, None
            
            # Align features and labels
            min_length = min(len(features), len(labels))
            features = features[:min_length]
            labels = labels[:min_length]
            
            # Remove any rows with NaN values
            valid_indices = ~(features.isna().any(axis=1) | labels.isna())
            features = features[valid_indices]
            labels = labels[valid_indices]
            
            logger.info(f"🔧 Prepared {len(features)} training samples for {symbol}")
            
            return features, labels
            
        except Exception as e:
            logger.error(f"❌ Training data preparation error for {symbol}: {e}")
            return None, None
    
    async def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the data"""
        try:
            df = data.copy()
            
            # Ensure we have required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"❌ Missing required column: {col}")
                    return None
            
            # Calculate technical indicators
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'], period=14)
            
            # MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = self._calculate_macd(df['close'])
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
            
            # Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # Stochastic RSI
            df['stoch_rsi'] = self._calculate_stochastic_rsi(df['close'])
            
            # Williams Alligator
            df['alligator_jaw'] = self._calculate_williams_alligator(df['close'], 13, 8)
            df['alligator_teeth'] = self._calculate_williams_alligator(df['close'], 8, 5)
            df['alligator_lips'] = self._calculate_williams_alligator(df['close'], 5, 3)
            
            # ATR (Average True Range)
            df['atr'] = self._calculate_atr(df, period=14)
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price-based features
            df['price_change'] = df['close'].pct_change()
            df['price_change_5'] = df['close'].pct_change(periods=5)
            df['price_change_20'] = df['close'].pct_change(periods=20)
            
            # Volatility
            df['volatility'] = df['price_change'].rolling(window=20).std()
            
            # Remove NaN values
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Technical indicators calculation error: {e}")
            return None
    
    async def _create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create feature matrix for training"""
        try:
            # Select feature columns
            feature_columns = [
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower',
                'sma_20', 'sma_50', 'ema_12', 'ema_26',
                'stoch_rsi', 'alligator_jaw', 'alligator_teeth', 'alligator_lips',
                'atr', 'volume_ratio', 'price_change', 'price_change_5', 'price_change_20',
                'volatility'
            ]
            
            # Check which columns exist
            available_columns = [col for col in feature_columns if col in data.columns]
            
            if len(available_columns) < 10:
                logger.error(f"❌ Insufficient feature columns: {available_columns}")
                return None
            
            features = data[available_columns].copy()
            
            # Normalize features
            features = (features - features.mean()) / features.std()
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature creation error: {e}")
            return None
    
    async def _create_labels(self, data: pd.DataFrame) -> pd.Series:
        """Create labels for training (future price movement)"""
        try:
            # Calculate future price change (next 4 hours)
            future_price_change = data['close'].shift(-4) / data['close'] - 1
            
            # Create 3-class labels
            labels = pd.Series(index=data.index, dtype=int)
            
            # Define thresholds
            buy_threshold = 0.01   # 1% increase
            sell_threshold = -0.01  # 1% decrease
            
            # Assign labels
            labels[future_price_change > buy_threshold] = 2    # BUY
            labels[future_price_change < sell_threshold] = 1   # SELL
            labels[(future_price_change >= sell_threshold) & (future_price_change <= buy_threshold)] = 0  # HOLD
            
            # Remove NaN values
            labels = labels.dropna()
            
            return labels
            
        except Exception as e:
            logger.error(f"❌ Label creation error: {e}")
            return None
    
    async def _train_models_for_symbol(self, symbol: str, features: pd.DataFrame, labels: pd.Series):
        """Train models for a specific symbol"""
        try:
            from sklearn.model_selection import train_test_split
            from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            import joblib
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=self.test_size, random_state=self.random_state, stratify=labels
            )
            
            # Create models directory
            models_dir = Path(f'models/{symbol.replace("/", "_")}')
            models_dir.mkdir(parents=True, exist_ok=True)
            
            # Train Gradient Boosting
            logger.info(f"🤖 Training Gradient Boosting for {symbol}")
            gb_model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=self.random_state
            )
            
            # Scale features
            scaler_gb = StandardScaler()
            X_train_scaled = scaler_gb.fit_transform(X_train)
            X_test_scaled = scaler_gb.transform(X_test)
            
            # Train model
            gb_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            gb_score = gb_model.score(X_test_scaled, y_test)
            logger.info(f"✅ Gradient Boosting accuracy for {symbol}: {gb_score:.4f}")
            
            # Save model
            joblib.dump(gb_model, models_dir / 'gradient_boosting_model.pkl')
            joblib.dump(scaler_gb, models_dir / 'gradient_boosting_scaler.pkl')
            
            # Train Random Forest
            logger.info(f"🤖 Training Random Forest for {symbol}")
            rf_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=self.random_state
            )
            
            # Scale features
            scaler_rf = StandardScaler()
            X_train_scaled_rf = scaler_rf.fit_transform(X_train)
            X_test_scaled_rf = scaler_rf.transform(X_test)
            
            # Train model
            rf_model.fit(X_train_scaled_rf, y_train)
            
            # Evaluate model
            rf_score = rf_model.score(X_test_scaled_rf, y_test)
            logger.info(f"✅ Random Forest accuracy for {symbol}: {rf_score:.4f}")
            
            # Save model
            joblib.dump(rf_model, models_dir / 'random_forest_model.pkl')
            joblib.dump(scaler_rf, models_dir / 'random_forest_scaler.pkl')
            
            # Save training metadata
            metadata = {
                'symbol': symbol,
                'training_date': datetime.now().isoformat(),
                'data_points': len(features),
                'feature_columns': list(features.columns),
                'test_size': self.test_size,
                'random_state': self.random_state,
                'gradient_boosting_accuracy': gb_score,
                'random_forest_accuracy': rf_score,
                'label_distribution': labels.value_counts().to_dict()
            }
            
            import json
            with open(models_dir / 'training_metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"💾 Models saved for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Model training error for {symbol}: {e}")
    
    # Technical indicator calculation methods
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2):
        """Calculate Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    def _calculate_stochastic_rsi(self, prices: pd.Series, period: int = 14):
        """Calculate Stochastic RSI"""
        rsi = self._calculate_rsi(prices, period)
        stoch_rsi = (rsi - rsi.rolling(window=period).min()) / (rsi.rolling(window=period).max() - rsi.rolling(window=period).min())
        return stoch_rsi
    
    def _calculate_williams_alligator(self, prices: pd.Series, period: int, shift: int):
        """Calculate Williams Alligator"""
        sma = prices.rolling(window=period).mean()
        return sma.shift(shift)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14):
        """Calculate Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr


async def main():
    """Main function"""
    try:
        trainer = ModelTrainer()
        await trainer.initialize()
        await trainer.train_all_models()
        logger.info("🎉 Model training completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Main error: {e}")


if __name__ == "__main__":
    asyncio.run(main())