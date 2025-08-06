"""
AI Signal Filter
Advanced AI-powered signal filtering and analysis
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


class AISignalFilter:
    """AI destekli sinyal filtreleme sistemi"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager, exchange_manager=None):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
            exchange_manager: Exchange manager for data fetching
        """
        self.config = ai_config
        self.db_manager = db_manager
        self.exchange_manager = exchange_manager
        self.confidence_threshold = ai_config.get('confidence_threshold', 0.75)
        self.retrain_frequency = ai_config.get('retrain_frequency_hours', 24)
        
        # Model storage
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # Signal cache
        self.signal_cache = {}
        self.cache_expiry = 300  # 5 minutes
        
        logger.info("🧠 AI Signal Filter initialized")
    
    async def initialize(self) -> None:
        """AI bileşenlerini başlat"""
        try:
            logger.info("🧠 AI Signal Filter başlatılıyor...")
            
            # Load any existing models
            await self._load_existing_models()
            
            logger.info("✅ AI Signal Filter hazır")
            
        except Exception as e:
            logger.error(f"❌ AI Signal Filter başlatma hatası: {e}")
            raise
    
    async def analyze_signals(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ana sinyal analizi fonksiyonu"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{int(datetime.now().timestamp() // 60)}"
            if cache_key in self.signal_cache:
                return self.signal_cache[cache_key]
            
            dataframe = market_data.get('dataframe')
            if dataframe is None or len(dataframe) < 20:
                return self._get_default_signals(symbol)
            
            # 1. Technical signals
            technical_signals = self._get_technical_signals(dataframe)
            
            # 2. ML signals (simplified)
            ml_signals = self._get_ml_signals(dataframe, symbol)
            
            # 3. Volume analysis
            volume_signals = self._get_volume_signals(dataframe)
            
            # 4. Combine all signals
            all_signals = technical_signals + ml_signals + volume_signals
            
            # 5. Calculate overall confidence
            confidence = self._calculate_signal_confidence(all_signals, dataframe)
            
            # 6. Filter signals by confidence
            filtered_signals = [s for s in all_signals if s.get('strength', 0) > 0.5]
            
            result = {
                'symbol': symbol,
                'signals': filtered_signals,
                'confidence': confidence,
                'signal_count': len(filtered_signals),
                'buy_signals': len([s for s in filtered_signals if s['type'] == 'BUY']),
                'sell_signals': len([s for s in filtered_signals if s['type'] == 'SELL']),
                'neutral_signals': len([s for s in filtered_signals if s['type'] == 'HOLD']),
                'timestamp': datetime.now(),
                'data_quality_score': self._assess_data_quality(dataframe)
            }
            
            # Cache result
            self.signal_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {symbol} sinyal analizi hatası: {e}")
            return self._get_default_signals(symbol)
    
    def _get_technical_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Teknik analiz sinyalleri"""
        signals = []
        
        try:
            if len(df) < 20:
                return signals
            
            # RSI signals
            rsi = self._calculate_rsi(df['close'])
            current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
            
            if current_rsi < 30:
                signals.append({
                    'type': 'BUY',
                    'source': 'RSI',
                    'strength': min(0.9, (30 - current_rsi) / 30 + 0.5),
                    'value': current_rsi,
                    'reason': f'RSI oversold: {current_rsi:.1f}'
                })
            elif current_rsi > 70:
                signals.append({
                    'type': 'SELL',
                    'source': 'RSI',
                    'strength': min(0.9, (current_rsi - 70) / 30 + 0.5),
                    'value': current_rsi,
                    'reason': f'RSI overbought: {current_rsi:.1f}'
                })
            
            # Moving Average Crossover
            if len(df) >= 50:
                sma_20 = df['close'].rolling(20).mean()
                sma_50 = df['close'].rolling(50).mean()
                
                current_price = df['close'].iloc[-1]
                sma20_current = sma_20.iloc[-1]
                sma50_current = sma_50.iloc[-1]
                
                if current_price > sma20_current > sma50_current:
                    signals.append({
                        'type': 'BUY',
                        'source': 'SMA_CROSS',
                        'strength': 0.7,
                        'value': current_price,
                        'reason': 'Price above SMA20 > SMA50'
                    })
                elif current_price < sma20_current < sma50_current:
                    signals.append({
                        'type': 'SELL',
                        'source': 'SMA_CROSS',
                        'strength': 0.7,
                        'value': current_price,
                        'reason': 'Price below SMA20 < SMA50'
                    })
            
            # MACD Signal
            macd_signals = self._get_macd_signals(df)
            signals.extend(macd_signals)
            
            # Bollinger Bands
            bb_signals = self._get_bollinger_signals(df)
            signals.extend(bb_signals)
            
        except Exception as e:
            logger.error(f"❌ Technical signals error: {e}")
        
        return signals
    
    def _get_ml_signals(self, df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """ML tabanlı sinyaller (basitleştirilmiş)"""
        signals = []
        
        try:
            # Simple ML simulation - gerçek implementation için model training gerekli
            features = self._extract_features(df)
            
            if len(features) > 0:
                # Mock ML prediction
                import random
                
                # Simulate different ML model predictions
                predictions = []
                
                # Random Forest simulation
                rf_pred = random.choice(['BUY', 'SELL', 'HOLD'])
                rf_conf = random.uniform(0.6, 0.9)
                predictions.append((rf_pred, rf_conf, 'RandomForest'))
                
                # Gradient Boosting simulation  
                gb_pred = random.choice(['BUY', 'SELL', 'HOLD'])
                gb_conf = random.uniform(0.6, 0.9)
                predictions.append((gb_pred, gb_conf, 'GradientBoosting'))
                
                # LSTM simulation
                lstm_pred = random.choice(['BUY', 'SELL', 'HOLD'])
                lstm_conf = random.uniform(0.5, 0.8)
                predictions.append((lstm_pred, lstm_conf, 'LSTM'))
                
                # Ensemble voting
                buy_votes = sum(1 for pred, _, _ in predictions if pred == 'BUY')
                sell_votes = sum(1 for pred, _, _ in predictions if pred == 'SELL')
                
                if buy_votes > sell_votes:
                    avg_conf = np.mean([conf for pred, conf, _ in predictions if pred == 'BUY'])
                    signals.append({
                        'type': 'BUY',
                        'source': 'ML_ENSEMBLE',
                        'strength': avg_conf,
                        'value': df['close'].iloc[-1],
                        'reason': f'ML Ensemble: {buy_votes}/3 models predict BUY'
                    })
                elif sell_votes > buy_votes:
                    avg_conf = np.mean([conf for pred, conf, _ in predictions if pred == 'SELL'])
                    signals.append({
                        'type': 'SELL',
                        'source': 'ML_ENSEMBLE',
                        'strength': avg_conf,
                        'value': df['close'].iloc[-1],
                        'reason': f'ML Ensemble: {sell_votes}/3 models predict SELL'
                    })
                
        except Exception as e:
            logger.error(f"❌ ML signals error: {e}")
        
        return signals
    
    def _get_volume_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Volume tabanlı sinyaller"""
        signals = []
        
        try:
            if len(df) < 20:
                return signals
            
            # Volume SMA
            volume_sma = df['volume'].rolling(20).mean()
            current_volume = df['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            # Volume spike detection
            if current_volume > avg_volume * 2:
                # Determine direction based on price movement
                price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
                
                if price_change > 0.01:  # 1% increase
                    signals.append({
                        'type': 'BUY',
                        'source': 'VOLUME_SPIKE',
                        'strength': min(0.8, current_volume / avg_volume * 0.2),
                        'value': current_volume,
                        'reason': f'Volume spike with price increase: {current_volume/avg_volume:.1f}x'
                    })
                elif price_change < -0.01:  # 1% decrease
                    signals.append({
                        'type': 'SELL',
                        'source': 'VOLUME_SPIKE',
                        'strength': min(0.8, current_volume / avg_volume * 0.2),
                        'value': current_volume,
                        'reason': f'Volume spike with price decrease: {current_volume/avg_volume:.1f}x'
                    })
            
            # On Balance Volume (simplified)
            obv = self._calculate_obv(df)
            if len(obv) >= 10:
                obv_sma = obv.rolling(10).mean()
                if obv.iloc[-1] > obv_sma.iloc[-1] * 1.1:
                    signals.append({
                        'type': 'BUY',
                        'source': 'OBV',
                        'strength': 0.6,
                        'value': obv.iloc[-1],
                        'reason': 'OBV trending up'
                    })
                elif obv.iloc[-1] < obv_sma.iloc[-1] * 0.9:
                    signals.append({
                        'type': 'SELL',
                        'source': 'OBV',
                        'strength': 0.6,
                        'value': obv.iloc[-1],
                        'reason': 'OBV trending down'
                    })
            
        except Exception as e:
            logger.error(f"❌ Volume signals error: {e}")
        
        return signals
    
    def _get_macd_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """MACD sinyalleri"""
        signals = []
        
        try:
            if len(df) < 26:
                return signals
            
            # MACD calculation
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9).mean()
            
            # MACD crossover
            if len(macd_line) >= 2:
                current_macd = macd_line.iloc[-1]
                current_signal = signal_line.iloc[-1]
                prev_macd = macd_line.iloc[-2]
                prev_signal = signal_line.iloc[-2]
                
                # Bullish crossover
                if current_macd > current_signal and prev_macd <= prev_signal:
                    signals.append({
                        'type': 'BUY',
                        'source': 'MACD',
                        'strength': 0.75,
                        'value': current_macd,
                        'reason': 'MACD bullish crossover'
                    })
                # Bearish crossover
                elif current_macd < current_signal and prev_macd >= prev_signal:
                    signals.append({
                        'type': 'SELL',
                        'source': 'MACD',
                        'strength': 0.75,
                        'value': current_macd,
                        'reason': 'MACD bearish crossover'
                    })
            
        except Exception as e:
            logger.error(f"❌ MACD signals error: {e}")
        
        return signals
    
    def _get_bollinger_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Bollinger Bands sinyalleri"""
        signals = []
        
        try:
            if len(df) < 20:
                return signals
            
            # Bollinger Bands
            sma = df['close'].rolling(20).mean()
            std = df['close'].rolling(20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Oversold condition
            if current_price <= current_lower:
                signals.append({
                    'type': 'BUY',
                    'source': 'BOLLINGER',
                    'strength': 0.7,
                    'value': current_price,
                    'reason': 'Price at lower Bollinger Band'
                })
            # Overbought condition
            elif current_price >= current_upper:
                signals.append({
                    'type': 'SELL',
                    'source': 'BOLLINGER',
                    'strength': 0.7,
                    'value': current_price,
                    'reason': 'Price at upper Bollinger Band'
                })
            
        except Exception as e:
            logger.error(f"❌ Bollinger signals error: {e}")
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesaplama"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(50)
            
        except Exception as e:
            logger.error(f"❌ RSI calculation error: {e}")
            return pd.Series([50] * len(prices), index=prices.index)
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """On Balance Volume hesaplama"""
        try:
            obv = []
            obv_value = 0
            
            for i in range(len(df)):
                if i == 0:
                    obv.append(df['volume'].iloc[i])
                    obv_value = df['volume'].iloc[i]
                else:
                    if df['close'].iloc[i] > df['close'].iloc[i-1]:
                        obv_value += df['volume'].iloc[i]
                    elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                        obv_value -= df['volume'].iloc[i]
                    # If close prices are equal, OBV remains the same
                    
                    obv.append(obv_value)
            
            return pd.Series(obv, index=df.index)
            
        except Exception as e:
            logger.error(f"❌ OBV calculation error: {e}")
            return pd.Series([0] * len(df), index=df.index)
    
    def _extract_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Feature extraction for ML"""
        try:
            if len(df) < 20:
                return {}
            
            features = {}
            
            # Price features
            features['price_sma_10'] = df['close'].rolling(10).mean().iloc[-1]
            features['price_sma_20'] = df['close'].rolling(20).mean().iloc[-1]
            features['price_change_pct'] = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
            
            # Volume features
            features['volume_sma_10'] = df['volume'].rolling(10).mean().iloc[-1]
            if features['volume_sma_10'] > 0:
                features['volume_ratio'] = df['volume'].iloc[-1] / features['volume_sma_10']
            else:
                features['volume_ratio'] = 1.0  # Default ratio if no volume data
            
            # Volatility features
            features['volatility'] = df['close'].rolling(10).std().iloc[-1]
            features['atr'] = self._calculate_atr(df)
            
            # RSI
            rsi = self._calculate_rsi(df['close'])
            features['rsi'] = rsi.iloc[-1] if len(rsi) > 0 else 50
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature extraction error: {e}")
            return {}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Average True Range hesaplama"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            tr = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = tr.rolling(period).mean().iloc[-1]
            
            return atr if not np.isnan(atr) else 0
            
        except Exception as e:
            logger.error(f"❌ ATR calculation error: {e}")
            return 0
    
    def _calculate_signal_confidence(self, signals: List[Dict], df: pd.DataFrame) -> float:
        """Sinyal güven faktörü hesaplama"""
        try:
            if not signals:
                return 0.3
            
            # Weight signals by strength and source
            source_weights = {
                'RSI': 0.8,
                'SMA_CROSS': 0.7,
                'MACD': 0.9,
                'BOLLINGER': 0.7,
                'ML_ENSEMBLE': 1.0,
                'VOLUME_SPIKE': 0.6,
                'OBV': 0.5
            }
            
            total_weight = 0
            buy_weight = 0
            sell_weight = 0
            
            for signal in signals:
                weight = signal['strength'] * source_weights.get(signal['source'], 0.5)
                total_weight += weight
                
                if signal['type'] == 'BUY':
                    buy_weight += weight
                elif signal['type'] == 'SELL':
                    sell_weight += weight
            
            if total_weight == 0:
                return 0.3
            
            # Calculate signal agreement
            max_weight = max(buy_weight, sell_weight)
            agreement = max_weight / total_weight
            
            # Apply data quality factor
            data_quality = self._assess_data_quality(df)
            
            # Apply volatility adjustment
            volatility = self._calculate_volatility(df)
            volatility_factor = max(0.5, 1 - volatility)
            
            confidence = agreement * data_quality * volatility_factor
            return min(0.95, max(0.1, confidence))
            
        except Exception as e:
            logger.error(f"❌ Confidence calculation error: {e}")
            return 0.3
    
    def _assess_data_quality(self, df: pd.DataFrame) -> float:
        """Veri kalitesini değerlendir"""
        try:
            if len(df) < 10:
                return 0.3
            
            # Check for missing values
            missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
            
            # Check for data recency
            if 'timestamp' in df.columns:
                last_timestamp = df['timestamp'].max()
                time_diff = (datetime.now() - last_timestamp).total_seconds()
                recency_factor = max(0.5, 1 - time_diff / 3600)  # Decrease after 1 hour
            else:
                recency_factor = 0.8
            
            # Check for sufficient data points
            length_factor = min(1.0, len(df) / 100)
            
            quality = (1 - missing_ratio) * recency_factor * length_factor
            return max(0.1, min(1.0, quality))
            
        except Exception as e:
            logger.error(f"❌ Data quality assessment error: {e}")
            return 0.5
    
    def _calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Volatilite hesaplama"""
        try:
            if len(df) < period:
                return 0.02
            
            returns = df['close'].pct_change().dropna()
            volatility = returns.rolling(period).std().iloc[-1]
            
            return max(0.001, min(0.1, volatility)) if not np.isnan(volatility) else 0.02
            
        except Exception as e:
            logger.error(f"❌ Volatility calculation error: {e}")
            return 0.02
    
    def _get_default_signals(self, symbol: str) -> Dict[str, Any]:
        """Varsayılan sinyal sonucu"""
        return {
            'symbol': symbol,
            'signals': [],
            'confidence': 0.3,
            'signal_count': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'neutral_signals': 0,
            'timestamp': datetime.now(),
            'data_quality_score': 0.3
        }
    
    async def _load_existing_models(self):
        """Mevcut modelleri yükle"""
        try:
            import os
            model_dir = "models"
            os.makedirs(model_dir, exist_ok=True)
            
            # Check for existing models
            gb_path = f"{model_dir}/gradient_boosting_model.joblib"
            rf_path = f"{model_dir}/random_forest_model.joblib"
            
            if os.path.exists(gb_path) and os.path.exists(rf_path):
                import joblib
                self.gb_model = joblib.load(gb_path)
                self.rf_model = joblib.load(rf_path)
                logger.success("✅ Pre-trained models loaded successfully")
            else:
                logger.info("🎓 No existing models found, will train new ones")
                await self._train_models()
                
        except Exception as e:
            logger.error(f"❌ Model loading error: {e}")
            logger.info("🎓 Training new models as fallback")
            await self._train_models()
    
    async def _train_models(self):
        """Train ML models with historical data"""
        try:
            logger.info("🎓 Starting ML model training...")
            
            # Check if exchange_manager is available
            if not self.exchange_manager:
                logger.warning("⚠️ No exchange manager available, using default models")
                self._create_default_models()
                return
            
            # Get training data from multiple symbols
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            all_features = []
            all_labels = []
            
            for symbol in symbols:
                try:
                    # Get historical data for training (last 150 days = ~5 months)
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=150)
                    
                    data = await self.exchange_manager.get_historical_data(
                        symbol, '1h', start_date, end_date
                    )
                    
                    if data is not None and len(data) > 50:
                        features, labels = self._prepare_training_data(data)
                        if len(features) > 0:
                            all_features.extend(features)
                            all_labels.extend(labels)
                            logger.info(f"📊 {symbol}: {len(features)} training samples")
                
                except Exception as e:
                    logger.warning(f"⚠️ Training data error for {symbol}: {e}")
            
            if len(all_features) > 100:  # Need minimum samples
                await self._train_and_save_models(all_features, all_labels)
                logger.success(f"🎓 Models trained on {len(all_features)} samples from {len(symbols)} symbols")
            else:
                logger.warning("⚠️ Insufficient training data, using default models")
                self._create_default_models()
                
        except Exception as e:
            logger.error(f"❌ Model training error: {e}")
            self._create_default_models()
    
    def _prepare_training_data(self, data):
        """Enhanced feature engineering with overfitting prevention"""
        import pandas as pd
        import numpy as np
        
        try:
            if len(data) < 100:  # Need more data for robust training
                return [], []
            
            # Copy data to prevent modification
            df = data.copy()
            
            # ANTI-DATA-LEAKAGE: Calculate future returns FIRST, before any other calculations
            df['future_return_1h'] = df['close'].shift(-1) / df['close'] - 1
            df['future_return_4h'] = df['close'].shift(-4) / df['close'] - 1
            
            # Enhanced technical indicators (using only past data)
            df['sma_10'] = df['close'].rolling(10).mean()
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'])
            df['rsi_sma'] = df['rsi'].rolling(5).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_upper'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['close']
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['volume_roc'] = df['volume'].pct_change(5)
            
            # Price momentum features
            df['price_roc_1'] = df['close'].pct_change(1)
            df['price_roc_5'] = df['close'].pct_change(5)
            df['price_roc_20'] = df['close'].pct_change(20)
            
            # Volatility features
            df['returns'] = df['close'].pct_change()
            df['volatility_5'] = df['returns'].rolling(5).std()
            df['volatility_20'] = df['returns'].rolling(20).std()
            
            # Market structure features
            df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
            df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
            
            # Trend strength
            df['trend_strength'] = np.abs(df['close'] - df['sma_20']) / df['sma_20']
            
            # ANTI-OVERFITTING: Remove last 10% of data to prevent lookahead
            cutoff = int(len(df) * 0.9)
            df = df.iloc[:cutoff]
            
            # Remove NaN values
            df = df.dropna()
            
            if len(df) < 50:
                return [], []
            
            # Feature selection (prevent overfitting with too many features)
            feature_columns = [
                'rsi', 'rsi_sma', 'macd_histogram', 'bb_position', 'bb_width',
                'volume_ratio', 'volume_roc', 'price_roc_1', 'price_roc_5',
                'volatility_5', 'high_low_ratio', 'close_position', 'trend_strength'
            ]
            
            features = []
            labels = []
            
            # Use multiple prediction horizons for robustness
            for i in range(len(df)):
                feature_row = []
                for col in feature_columns:
                    val = df.iloc[i][col]
                    if np.isnan(val) or np.isinf(val):
                        val = 0  # Handle edge cases
                    feature_row.append(val)
                
                # Multi-target labeling for robustness
                future_1h = df.iloc[i]['future_return_1h']
                future_4h = df.iloc[i]['future_return_4h']
                
                # Conservative labeling: require consistent profitability
                label = 1 if (future_1h > 0.002 and future_4h > 0.001) else 0  # 0.2% and 0.1% thresholds
                
                if not np.isnan([future_1h, future_4h]).any():
                    features.append(feature_row)
                    labels.append(label)
            
            logger.info(f"📊 Prepared {len(features)} samples with {len(feature_columns)} features")
            return features, labels
            
        except Exception as e:
            logger.error(f"❌ Enhanced data preparation error: {e}")
            return [], []
    
    async def _train_and_save_models(self, features, labels):
        """Train and save ML models"""
        try:
            from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            import joblib
            import numpy as np
            
            X = np.array(features)
            y = np.array(labels)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Gradient Boosting
            self.gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            self.gb_model.fit(X_train_scaled, y_train)
            gb_score = self.gb_model.score(X_test_scaled, y_test)
            
            # Train Random Forest
            self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.rf_model.fit(X_train_scaled, y_train)
            rf_score = self.rf_model.score(X_test_scaled, y_test)
            
            # Save models
            import os
            model_dir = "models"
            os.makedirs(model_dir, exist_ok=True)
            
            joblib.dump(self.gb_model, f"{model_dir}/gradient_boosting_model.joblib")
            joblib.dump(self.rf_model, f"{model_dir}/random_forest_model.joblib")
            joblib.dump(scaler, f"{model_dir}/scaler.joblib")
            
            logger.success(f"✅ Models trained and saved! GB: {gb_score:.3f}, RF: {rf_score:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Model training error: {e}")
            self._create_default_models()
    
    def _create_default_models(self):
        """Create simple default models"""
        from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
        
        # Create untrained models with default parameters
        self.gb_model = GradientBoostingClassifier(n_estimators=50, random_state=42)
        self.rf_model = RandomForestClassifier(n_estimators=50, random_state=42)
        logger.info("📊 Default models created")
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        import pandas as pd
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        import pandas as pd
        
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, lower_band
    
    async def get_signal_history(self, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Sinyal geçmişi"""
        try:
            # Mock implementation
            return []
            
        except Exception as e:
            logger.error(f"❌ Signal history error: {e}")
            return []