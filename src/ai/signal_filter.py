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
        
        # Initialize model validator for performance monitoring
        from .model_validator import ModelValidator
        self.model_validator = ModelValidator()
        
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
    
    async def filter_signal(self, symbol: str, market_data: Dict[str, Any], regime: str = None) -> Dict[str, Any]:
        """
        Filter and analyze trading signals using AI models
        
        Args:
            symbol: Trading symbol
            market_data: Current market data
            regime: Current market regime
            
        Returns:
            Dict with signal analysis and filtering results
        """
        try:
            logger.debug(f"🔍 Filtering signal for {symbol} in {regime} regime")
            
            # Get current price and basic data
            current_price = market_data.get('price', 0)
            volume = market_data.get('volume', 0)
            
            # Check if we have trained models for this symbol
            model_key = f"{symbol}_gradient_boosting"
            if model_key not in self.models:
                logger.debug(f"⚠️ No trained model for {symbol}, using default analysis")
                return self._get_default_signal_analysis(symbol, market_data, regime)
            
            # Prepare features for ML prediction
            features = self._prepare_real_time_features(market_data, regime)
            if not features:
                return self._get_default_signal_analysis(symbol, market_data, regime)
            
            # Get ML prediction
            model = self.models[model_key]
            scaler = self.scalers.get(f"{symbol}_scaler")
            
            if scaler:
                features_scaled = scaler.transform([features])
            else:
                features_scaled = [features]
            
            # Predict signal probability and direction (3-class)
            signal_prob = model.predict_proba(features_scaled)[0]
            signal_confidence = max(signal_prob)
            predicted_class = model.predict(features_scaled)[0]  # 0=HOLD, 1=SELL, 2=BUY
            
            # Analyze signal strength based on market regime
            regime_multiplier = self._get_regime_multiplier(regime)
            final_confidence = signal_confidence * regime_multiplier
            
            # Enhanced 3-class signal generation
            if predicted_class == 2 and final_confidence > 0.65:  # BUY - Increased from 0.5 to 0.65
                signal_type = "BUY"
            elif predicted_class == 1 and final_confidence > 0.65:  # SELL - Increased from 0.5 to 0.65
                signal_type = "SELL"
            else:  # HOLD or low confidence
                signal_type = "HOLD"
            
            result = {
                'signal': signal_type,
                'confidence': final_confidence,
                'ml_probability': signal_prob[1],
                'regime': regime,
                'features_used': len(features),
                'model_used': model_key,
                'timestamp': datetime.now().isoformat(),
                'price': current_price,
                'volume': volume
            }
            
            logger.debug(f"✅ Signal filtered: {signal_type} (confidence: {final_confidence:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Signal filtering error for {symbol}: {e}")
            return self._get_default_signal_analysis(symbol, market_data, regime)
    
    def _prepare_real_time_features(self, market_data: Dict[str, Any], regime: str) -> List[float]:
        """Prepare features for real-time ML prediction"""
        try:
            # Basic features that match our training data
            features = [
                market_data.get('rsi_14', 50.0),
                market_data.get('macd_signal', 0.0),
                market_data.get('bb_position', 0.5),
                market_data.get('volume_ratio', 1.0),
                market_data.get('price_change_1h', 0.0),
                market_data.get('volatility', 0.01),
                market_data.get('trend_strength', 0.0),
                0.0,  # support_distance (placeholder)
                0.0,  # resistance_distance (placeholder)
                market_data.get('momentum', 0.0),
                0.0,  # volume_trend (placeholder)
                market_data.get('price_velocity', 0.0),
                0.0   # market_pressure (placeholder)
            ]
            
            # Ensure all features are numeric and finite
            features = [float(f) if not np.isnan(float(f)) and np.isfinite(float(f)) else 0.0 for f in features]
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature preparation error: {e}")
            return []
    
    def _get_regime_multiplier(self, regime: str) -> float:
        """Get confidence multiplier based on market regime"""
        regime_multipliers = {
            'trending_market': 1.2,
            'breakout_market': 1.3,
            'high_volatility': 0.8,
            'sideways_market': 0.9,
            'consolidation_market': 0.85,
            'ranging_market': 0.9,
            'volatile_ranging_market': 0.7
        }
        return regime_multipliers.get(regime, 1.0)
    
    def _get_default_signal_analysis(self, symbol: str, market_data: Dict[str, Any], regime: str) -> Dict[str, Any]:
        """Get default signal analysis when ML models are not available"""
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'ml_probability': 0.5,
            'regime': regime,
            'features_used': 0,
            'model_used': 'default',
            'timestamp': datetime.now().isoformat(),
            'price': market_data.get('price', 0),
            'volume': market_data.get('volume', 0)
        }
    
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
            
            # Get training data from multiple symbols and timeframes
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
            # Updated timeframes to match new strategy configuration
            timeframes = ['5m', '15m']  # Mean reversion (5m) and Trend following (15m)
            all_features = []
            all_labels = []
            
            for symbol in symbols:
                for timeframe in timeframes:
                    try:
                        # Get historical data for training (last 150 days = ~5 months)
                        from datetime import datetime, timedelta
                        end_date = datetime.now()
                        # Adjust days based on timeframe for similar data points
                        if timeframe == '5m':
                            days = 30  # 30 days of 5m = ~8640 candles (sufficient for 5m scalping)
                        elif timeframe == '15m':
                            days = 60  # 60 days of 15m = ~5760 candles (good for trend analysis)
                        else:
                            days = 150  # Fallback
                        start_date = end_date - timedelta(days=days)
                        
                        data = await self.exchange_manager.get_historical_data(
                            symbol, timeframe, start_date, end_date
                        )
                        
                        if data is not None and len(data) > 50:
                            features, labels = self._prepare_training_data(data)
                            if len(features) > 0:
                                all_features.extend(features)
                                all_labels.extend(labels)
                                logger.info(f"📊 {symbol}-{timeframe}: {len(features)} training samples")
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Training data error for {symbol}-{timeframe}: {e}")
            
            if len(all_features) > 100:  # Need minimum samples
                await self._train_and_save_models(all_features, all_labels)
                logger.success(f"🎓 Models trained on {len(all_features)} samples from {len(symbols)} symbols")
            else:
                logger.warning("⚠️ Insufficient training data, using default models")
                self._create_default_models()
                
        except Exception as e:
            logger.error(f"❌ Model training error: {e}")
            self._create_default_models()
    
    def _prepare_training_data(self, df: pd.DataFrame) -> tuple:
        """Prepare training data with TIMEFRAME-ADAPTIVE TARGET DEFINITION"""
        try:
            if df.empty:
                return [], []
            
            # Detect timeframe from data frequency (approximate)
            if len(df) > 1:
                time_diff = (df.index[1] - df.index[0]).total_seconds() / 60  # Minutes
                if time_diff <= 6:
                    timeframe_type = '5m'
                    short_period = 2  # 10 minutes ahead
                    long_period = 6   # 30 minutes ahead  
                    short_target = 0.3  # 0.3% in 10 min (scalping)
                    long_target = 0.15  # 0.15% in 30 min
                elif time_diff <= 20:
                    timeframe_type = '15m'
                    short_period = 2  # 30 minutes ahead
                    long_period = 4   # 1 hour ahead
                    short_target = 0.4  # 0.4% in 30 min (trend)
                    long_target = 0.2   # 0.2% in 1 hour
                else:
                    timeframe_type = 'other'
                    short_period = 1
                    long_period = 2
                    short_target = 0.2
                    long_target = 0.1
            else:
                timeframe_type = 'unknown'
                short_period = 1
                long_period = 2  
                short_target = 0.2
                long_target = 0.1
            
            # DEFINE TRAINING TARGET DYNAMICALLY
            logger.info("🎯 ML Training Target Definition (3-Class):")
            logger.info("   📈 Predicting: BUY/SELL/HOLD signals")
            logger.info(f"   ⏰ Timeframe: {timeframe_type} detected")
            logger.info(f"   💰 BUY: >{short_target:.1%} in {short_period} periods AND >{long_target:.1%} in {long_period} periods (LONG)")
            logger.info(f"   💸 SELL: >{short_target:.1%} in {short_period} periods AND >{long_target:.1%} in {long_period} periods (SHORT)")
            logger.info("   🎯 Label 2: BUY signal (profitable LONG)")
            logger.info("   🎯 Label 1: SELL signal (profitable SHORT)")
            logger.info("   🎯 Label 0: HOLD signal (no clear direction)")
            
            # CALCULATE FUTURE RETURNS FOR BOTH DIRECTIONS
            df = df.copy()  # Work with copy to avoid modifying original
            df['future_return_short'] = df['close'].shift(-short_period) / df['close'] - 1
            df['future_return_long'] = df['close'].shift(-long_period) / df['close'] - 1
            
            # Calculate negative returns for SELL signals (SHORT positions)
            df['future_return_short_sell'] = -(df['future_return_short'])  # Negative return = profit for SHORT
            df['future_return_long_sell'] = -(df['future_return_long'])    # Negative return = profit for SHORT
            
            # Enhanced feature engineering
            feature_columns = [
                'rsi_14', 'macd_signal', 'bb_position', 'volume_ma_ratio',
                'price_change_1h', 'volatility', 'trend_strength',
                'support_distance', 'resistance_distance', 'momentum',
                'volume_trend', 'price_velocity', 'market_pressure'
            ]
            
            # Calculate basic technical indicators
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd = exp1 - exp2
            df['macd_signal'] = macd.ewm(span=9).mean()
            
            # Bollinger Bands position
            bb_ma = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_upper = bb_ma + (2 * bb_std)
            bb_lower = bb_ma - (2 * bb_std)
            df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # Volume ratio
            volume_ma = df['volume'].rolling(20).mean() if 'volume' in df.columns else pd.Series([1.0] * len(df))
            df['volume_ma_ratio'] = df['volume'] / volume_ma if 'volume' in df.columns else 1.0
            
            # Price change and volatility
            df['price_change_1h'] = df['close'].pct_change(1)
            df['volatility'] = df['close'].pct_change().rolling(20).std()
            df['trend_strength'] = abs(df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).mean()
            
            # Simple features for missing ones
            df['support_distance'] = 0  # Placeholder
            df['resistance_distance'] = 0  # Placeholder  
            df['momentum'] = df['close'].pct_change(5)
            df['volume_trend'] = 0  # Placeholder
            df['price_velocity'] = df['close'].pct_change(2)
            df['market_pressure'] = 0  # Placeholder
            
            # Fill NaN values with defaults
            for col in feature_columns:
                if col in df.columns:
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = 0
            
            features = []
            labels = []
            
            for i in range(24, len(df) - long_period):  # Start after indicators stabilize, end before future period
                # Feature extraction
                feature_row = []
                current_row = df.iloc[i]
                
                # Extract features
                for col in feature_columns:
                    val = current_row.get(col, 0)
                    if pd.isna(val) or np.isinf(val):
                        val = 0
                    feature_row.append(val)
                
                # Target: Future returns (MULTI-CLASS: BUY/HOLD/SELL)
                future_short = df.iloc[i]['future_return_short']
                future_long = df.iloc[i]['future_return_long']
                future_short_sell = df.iloc[i]['future_return_short_sell']
                future_long_sell = df.iloc[i]['future_return_long_sell']
                
                # 3-CLASS LABELING: BUY=2, SELL=1, HOLD=0
                # BUY signal: Both long conditions met for upward movement
                buy_signal = (future_short > short_target/100 and future_long > long_target/100)
                
                # SELL signal: Both conditions met for downward movement (profitable SHORT)
                sell_signal = (future_short_sell > short_target/100 and future_long_sell > long_target/100)
                
                if buy_signal:
                    label = 2  # BUY
                elif sell_signal:
                    label = 1  # SELL
                else:
                    label = 0  # HOLD
                
                if not pd.isna(future_short) and not pd.isna(future_long):
                    features.append(feature_row)
                    labels.append(label)
            
            # Log training statistics with 3-class breakdown
            buy_signals = sum(1 for label in labels if label == 2)
            sell_signals = sum(1 for label in labels if label == 1) 
            hold_signals = sum(1 for label in labels if label == 0)
            total_samples = len(labels)
            
            logger.info(f"📊 Training Data Prepared (3-Class):")
            logger.info(f"   📈 Total samples: {total_samples}")
            logger.info(f"   💰 BUY signals: {buy_signals} ({buy_signals/total_samples*100:.1f}%)")
            logger.info(f"   💸 SELL signals: {sell_signals} ({sell_signals/total_samples*100:.1f}%)")
            logger.info(f"   ⏸️ HOLD signals: {hold_signals} ({hold_signals/total_samples*100:.1f}%)")
            logger.info(f"   🔧 Features: {len(feature_columns)} technical indicators")
            
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
            
            # COMPREHENSIVE MODEL VALIDATION
            gb_validation = self.model_validator.validate_model_performance(
                self.gb_model, X_test_scaled, y_test, "GradientBoosting"
            )
            rf_validation = self.model_validator.validate_model_performance(
                self.rf_model, X_test_scaled, y_test, "RandomForest"
            )
            
            # Cross-validation for additional confidence
            gb_cv = self.model_validator.cross_validate_model(self.gb_model, X_train_scaled, y_train, 
                                                            cv_folds=5, model_name="GradientBoosting")
            rf_cv = self.model_validator.cross_validate_model(self.rf_model, X_train_scaled, y_train,
                                                            cv_folds=5, model_name="RandomForest")
            
            # Store validation results
            self.gb_validation = gb_validation
            self.rf_validation = rf_validation
            
            # Save models with validation metadata
            import os
            model_dir = "models"
            os.makedirs(model_dir, exist_ok=True)
            
            joblib.dump(self.gb_model, f"{model_dir}/gradient_boosting_model.joblib")
            joblib.dump(self.rf_model, f"{model_dir}/random_forest_model.joblib")
            joblib.dump(scaler, f"{model_dir}/scaler.joblib")
            joblib.dump(gb_validation, f"{model_dir}/gb_validation.joblib")
            joblib.dump(rf_validation, f"{model_dir}/rf_validation.joblib")
            
            logger.success(f"✅ Models trained and validated!")
            logger.info(f"📊 GB: {gb_score:.3f} (Confidence: {gb_validation['confidence_score']:.3f} - {gb_validation['confidence_level']})")
            logger.info(f"📊 RF: {rf_score:.3f} (Confidence: {rf_validation['confidence_score']:.3f} - {rf_validation['confidence_level']})")
            
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