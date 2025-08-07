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
from pathlib import Path


class AISignalFilter:
    """AI destekli sinyal filtreleme sistemi"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager, exchange_manager=None):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
            exchange_manager: Exchange yöneticisi (opsiyonel)
        """
        self.config = ai_config
        self.db_manager = db_manager
        self.exchange_manager = exchange_manager
        
        # Model storage
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        
        # Dynamic adaptive learning parameters based on performance
        self.adaptive_weights = await self._get_dynamic_adaptive_weights()
        
        self.adaptive_thresholds = await self._get_dynamic_adaptive_thresholds()
        
        # Model versioning
        self.model_versions = {}
        self.current_model_version = 'v1.0'
        self.model_performance_history = {}
        
        # Dynamic learning rate for adaptive adjustments
        self.learning_rate = await self._get_dynamic_learning_rate(ai_config)
        self.performance_window = await self._get_dynamic_performance_window(ai_config)
        
        # Dynamic signal cache
        self.signal_cache = {}
        self.cache_duration = await self._get_dynamic_cache_duration()
        
        logger.info("🤖 AI Signal Filter initialized with adaptive learning")
    
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
        """Enhanced signal analysis with adaptive learning and quality assessment"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{int(datetime.now().timestamp() // 60)}"
            if cache_key in self.signal_cache:
                return self.signal_cache[cache_key]
            
            dataframe = market_data.get('dataframe')
            if dataframe is None or len(dataframe) < 20:
                return self._get_default_signals(symbol)
            
            # 1. Technical signals with enhanced validation
            technical_signals = self._get_technical_signals(dataframe)
            
            # 2. ML signals with improved confidence calculation
            ml_signals = await self._get_ml_signals(dataframe, symbol)
            
            # 3. Volume analysis with anomaly detection
            volume_signals = self._get_volume_signals(dataframe)
            
            # 4. Market regime signals
            regime_signals = self._get_regime_signals(dataframe, symbol)
            
            # 5. Combine all signals with adaptive weighting
            all_signals = []
            
            # Dynamic weighting based on market conditions
            market_volatility = self._calculate_volatility(dataframe, period=20)
            market_trend = self._calculate_trend_strength(dataframe)
            
            # Adjust weights based on market conditions
            if market_volatility > 0.8:  # High volatility
                tech_weight = 0.3
                ml_weight = 0.4
                volume_weight = 0.2
                regime_weight = 0.1
            elif market_trend > 0.7:  # Strong trend
                tech_weight = 0.4
                ml_weight = 0.3
                volume_weight = 0.2
                regime_weight = 0.1
            else:  # Normal conditions
                tech_weight = 0.35
                ml_weight = 0.35
                volume_weight = 0.2
                regime_weight = 0.1
            
            # Apply weights to signals
            for signal in technical_signals:
                signal['weight'] = tech_weight
                signal['source_type'] = 'technical'
                all_signals.append(signal)
            
            for signal in ml_signals:
                signal['weight'] = ml_weight
                signal['source_type'] = 'ml'
                all_signals.append(signal)
            
            for signal in volume_signals:
                signal['weight'] = volume_weight
                signal['source_type'] = 'volume'
                all_signals.append(signal)
            
            for signal in regime_signals:
                signal['weight'] = regime_weight
                signal['source_type'] = 'regime'
                all_signals.append(signal)
            
            # 6. Filter signals by minimum confidence threshold
            min_confidence = self.config.get('confidence_threshold', 0.6)
            filtered_signals = [s for s in all_signals if s.get('confidence', 0) >= min_confidence]
            
            # 7. Calculate weighted overall confidence with signal quality assessment
            if filtered_signals:
                weighted_confidence = sum(s.get('confidence', 0) * s.get('weight', 1.0) for s in filtered_signals)
                total_weight = sum(s.get('weight', 1.0) for s in filtered_signals)
                overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.5
                
                # Signal quality assessment
                signal_quality = self._assess_signal_quality(filtered_signals, dataframe)
                overall_confidence *= signal_quality
            else:
                overall_confidence = 0.5
                signal_quality = 0.5
            
            # 8. Determine final signal type with enhanced logic
            buy_signals = [s for s in filtered_signals if s['type'] == 'BUY']
            sell_signals = [s for s in filtered_signals if s['type'] == 'SELL']
            
            # Enhanced signal decision logic
            if len(buy_signals) > len(sell_signals) and overall_confidence > min_confidence:
                # Check for strong buy consensus
                buy_confidence = np.mean([s.get('confidence', 0) for s in buy_signals])
                if buy_confidence > 0.7:
                    final_signal_type = 'BUY'
                elif buy_confidence > 0.6:
                    final_signal_type = 'BUY'
                else:
                    final_signal_type = 'HOLD'
            elif len(sell_signals) > len(buy_signals) and overall_confidence > min_confidence:
                # Check for strong sell consensus
                sell_confidence = np.mean([s.get('confidence', 0) for s in sell_signals])
                if sell_confidence > 0.7:
                    final_signal_type = 'SELL'
                elif sell_confidence > 0.6:
                    final_signal_type = 'SELL'
                else:
                    final_signal_type = 'HOLD'
            else:
                final_signal_type = 'HOLD'
            
            # 9. Calculate signal strength and reliability
            signal_strength = self._calculate_signal_strength(filtered_signals, final_signal_type)
            signal_reliability = self._calculate_signal_reliability(filtered_signals, dataframe)
            
            result = {
                'symbol': symbol,
                'action': final_signal_type,
                'signals': filtered_signals,
                'confidence': overall_confidence,
                'signal_count': len(filtered_signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'neutral_signals': len([s for s in filtered_signals if s['type'] == 'HOLD']),
                'timestamp': datetime.now(),
                'data_quality_score': self._assess_data_quality(dataframe),
                'signal_quality_score': signal_quality,
                'signal_strength': signal_strength,
                'signal_reliability': signal_reliability,
                'ml_probability': self._get_ml_probability(filtered_signals),
                'technical_score': self._calculate_technical_score(technical_signals),
                'volume_score': self._calculate_volume_score(volume_signals),
                'market_conditions': {
                    'volatility': market_volatility,
                    'trend_strength': market_trend,
                    'regime': self._detect_market_regime(dataframe)
                }
            }
            
            # Cache result with shorter expiry for dynamic markets
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
            if predicted_class == 2 and final_confidence > 0.58:  # BUY - Balanced threshold
                signal_type = "BUY"
            elif predicted_class == 1 and final_confidence > 0.58:  # SELL - Balanced threshold
                signal_type = "SELL"
            else:  # HOLD or low confidence
                signal_type = "HOLD"
            
            result = {
                'action': signal_type,  # FIXED: Use 'action' key for consistency with all modules
                'confidence': final_confidence,
                'ml_probability': signal_prob[predicted_class],  # Fixed: Use actual predicted class probability
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
            'action': 'HOLD',  # FIXED: Use 'action' key for consistency 
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
    
    async def _get_ml_signals(self, df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """Enhanced ML signals with real model predictions and adaptive learning"""
        signals = []
        
        try:
            if len(df) < 50:  # Need sufficient data for ML
                return signals
            
            # Get symbol-specific models
            symbol_key = symbol.replace('/', '_')
            models = self.models.get(symbol_key, {})
            
            # If symbol-specific models not available, try default models
            if not models:
                models = self.models.get('BTC_USDT', {})  # Use BTC as fallback
                if models:
                    logger.debug(f"Using BTC models as fallback for {symbol}")
            
            if not models:
                logger.debug(f"No trained ML models available for {symbol}")
                # Try to load models if not initialized
                await self._try_load_models()
                models = self.models.get(symbol_key, {}) or self.models.get('BTC_USDT', {})
                
            if not models:
                logger.warning(f"⚠️ ML models still not available for {symbol}")
                return signals
            
            # Prepare features for prediction
            features = self._extract_features(df.tail(1))
            if not features:
                return signals
            
            # Get predictions from both models with enhanced confidence calculation
            gb_model = models.get('GradientBoosting')
            rf_model = models.get('RandomForest')
            
            predictions = []
            
            if gb_model:
                try:
                    scaler = self.scalers.get(symbol_key, {}).get('GradientBoosting') or self.scalers.get('BTC_USDT', {}).get('GradientBoosting')
                    if scaler:
                        features_scaled = scaler.transform([list(features.values())])
                        pred_proba = gb_model.predict_proba(features_scaled)[0]
                        pred_class = gb_model.predict(features_scaled)[0]
                        
                        # Enhanced confidence calculation
                        confidence = self._calculate_enhanced_confidence(pred_proba, features, 'GradientBoosting')
                        
                        predictions.append({
                            'model': 'GradientBoosting',
                            'class': pred_class,
                            'probabilities': pred_proba,
                            'confidence': confidence,
                            'features': features
                        })
                except Exception as e:
                    logger.debug(f"GB model prediction error: {e}")
            
            if rf_model:
                try:
                    scaler = self.scalers.get(symbol_key, {}).get('RandomForest') or self.scalers.get('BTC_USDT', {}).get('RandomForest')
                    if scaler:
                        features_scaled = scaler.transform([list(features.values())])
                        pred_proba = rf_model.predict_proba(features_scaled)[0]
                        pred_class = rf_model.predict(features_scaled)[0]
                        
                        # Enhanced confidence calculation
                        confidence = self._calculate_enhanced_confidence(pred_proba, features, 'RandomForest')
                        
                        predictions.append({
                            'model': 'RandomForest',
                            'class': pred_class,
                            'probabilities': pred_proba,
                            'confidence': confidence,
                            'features': features
                        })
                except Exception as e:
                    logger.debug(f"RF model prediction error: {e}")
            
            # Generate signals from predictions with adaptive thresholds
            for pred in predictions:
                # Adaptive confidence threshold based on market conditions
                base_threshold = 0.6
                market_volatility = self._calculate_volatility(df, period=20)
                
                # Adjust threshold based on volatility
                if market_volatility > 0.8:  # High volatility
                    threshold = base_threshold * 1.2  # Higher threshold
                elif market_volatility < 0.3:  # Low volatility
                    threshold = base_threshold * 0.8  # Lower threshold
                else:
                    threshold = base_threshold
                
                if pred['confidence'] > threshold:
                    signal_type = 'HOLD'
                    if pred['class'] == 2:  # BUY class
                        signal_type = 'BUY'
                    elif pred['class'] == 1:  # SELL class
                        signal_type = 'SELL'
                    
                    if signal_type != 'HOLD':
                        # Calculate signal strength based on multiple factors
                        signal_strength = self._calculate_ml_signal_strength(pred, df)
                        
                        signals.append({
                            'type': signal_type,
                            'strength': signal_strength,
                            'source': f"ML_{pred['model']}",
                            'confidence': pred['confidence'],
                            'price': df['close'].iloc[-1],
                            'timestamp': datetime.now(),
                            'details': {
                                'model': pred['model'],
                                'predicted_class': pred['class'],
                                'probabilities': pred['probabilities'].tolist(),
                                'features_count': len(features),
                                'threshold_used': threshold,
                                'market_volatility': market_volatility
                            }
                        })
            
            if signals:
                logger.debug(f"Generated {len(signals)} ML signals from trained models for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ ML signals error: {e}")
        
        return signals
    
    async def _try_load_models(self):
        """Try to load ML models if not already loaded"""
        try:
            if not self.models:
                logger.info("🔄 Attempting to load ML models...")
                
                # Try to load from common model paths
                import os
                import joblib
                
                model_paths = [
                    'models/',
                    'src/ai/models/',
                    '../models/',
                    './models/'
                ]
                
                for model_path in model_paths:
                    if os.path.exists(model_path):
                        logger.debug(f"Checking model directory: {model_path}")
                        
                        # Look for model files
                        for timeframe in ['5m', '15m']:
                            gb_path = os.path.join(model_path, f'gradient_boosting_model_{timeframe}.joblib')
                            rf_path = os.path.join(model_path, f'random_forest_model_{timeframe}.joblib')
                            scaler_gb_path = os.path.join(model_path, f'scaler_gradient_boosting_{timeframe}.joblib')
                            scaler_rf_path = os.path.join(model_path, f'scaler_random_forest_{timeframe}.joblib')
                            
                            if all(os.path.exists(p) for p in [gb_path, rf_path, scaler_gb_path, scaler_rf_path]):
                                try:
                                    # Load models
                                    gb_model = joblib.load(gb_path)
                                    rf_model = joblib.load(rf_path)
                                    gb_scaler = joblib.load(scaler_gb_path)
                                    rf_scaler = joblib.load(scaler_rf_path)
                                    
                                    # Initialize structures if needed
                                    if timeframe not in self.models:
                                        self.models[timeframe] = {}
                                    if timeframe not in self.scalers:
                                        self.scalers[timeframe] = {}
                                    
                                    # Store models
                                    self.models[timeframe]['GradientBoosting'] = gb_model
                                    self.models[timeframe]['RandomForest'] = rf_model
                                    self.scalers[timeframe]['GradientBoosting'] = gb_scaler
                                    self.scalers[timeframe]['RandomForest'] = rf_scaler
                                    
                                    logger.success(f"✅ Loaded {timeframe} models from {model_path}")
                                    
                                except Exception as e:
                                    logger.warning(f"⚠️ Failed to load {timeframe} models: {e}")
                
                if self.models:
                    logger.success(f"✅ Successfully loaded models for timeframes: {list(self.models.keys())}")
                else:
                    logger.warning("⚠️ No models could be loaded from any path")
                    
        except Exception as e:
            logger.error(f"❌ Error trying to load models: {e}")
    
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
        """Get default signals when no real data available"""
        return {
            'symbol': symbol,
            'signals': [],
            'confidence': 0.0,  # No confidence when no real data
            'signal_count': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'neutral_signals': 0,
            'timestamp': datetime.now(),
            'data_quality_score': 0.0,  # No data quality when no real data
            'action': 'HOLD',  # Default to HOLD when no real data
            'reason': 'No real market data available'
        }
    
    async def _load_existing_models(self):
        """Load existing trained models"""
        try:
            logger.info("🤖 Mevcut modeller yükleniyor...")
            
            # Check if models directory exists
            models_dir = Path('models')
            if not models_dir.exists():
                logger.info("📁 Models klasörü bulunamadı, default modeller oluşturulacak")
                await self._create_default_models()
                return
            
            # Try to load models for each symbol
            for symbol in ['BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'ADA_USDT']:
                gb_path = models_dir / f"{symbol}_gradient_boosting_model.pkl"
                rf_path = models_dir / f"{symbol}_random_forest_model.pkl"
                scaler_path = models_dir / f"{symbol}_scaler.pkl"
                
                if gb_path.exists() and rf_path.exists() and scaler_path.exists():
                    try:
                        import joblib
                        
                        # Load models
                        gb_model = joblib.load(gb_path)
                        rf_model = joblib.load(rf_path)
                        scaler = joblib.load(scaler_path)
                        
                        # Store models
                        self.models[symbol] = {
                            'GradientBoosting': gb_model,
                            'RandomForest': rf_model
                        }
                        self.scalers[symbol] = {
                            'GradientBoosting': scaler,
                            'RandomForest': scaler
                        }
                        
                        logger.success(f"✅ {symbol} modelleri yüklendi")
                        
                    except Exception as e:
                        logger.error(f"❌ {symbol} model yükleme hatası: {e}")
                        continue
                else:
                    logger.info(f"📁 {symbol} modelleri bulunamadı")
            
            # If no models loaded, create defaults
            if not self.models:
                logger.info("📁 Hiç model yüklenemedi, default modeller oluşturuluyor")
                await self._create_default_models()
                
        except Exception as e:
            logger.error(f"❌ Model yükleme hatası: {e}")
            await self._create_default_models()
    
    async def _create_default_models(self):
        """Create default ML models using real historical data when available"""
        try:
            from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            import numpy as np
            
            logger.info("🤖 Attempting to create models with real historical data...")
            
            # Try to get real historical data for training
            training_data = await self._get_real_training_data()
            
            if training_data is not None and len(training_data) > 100:
                # Use real data for training
                X_real, y_real = training_data
                
                # Create and train models with real data
                gb_model = GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=4,
                    random_state=42
                )
                
                rf_model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    random_state=42
                )
                
                # Fit models with real data
                gb_model.fit(X_real, y_real)
                rf_model.fit(X_real, y_real)
                
                # Create scaler with real data
                scaler = StandardScaler()
                scaler.fit(X_real)
                
                logger.success("✅ Models created with real historical data")
                
            else:
                # No real data available - create minimal models
                logger.warning("⚠️ No real training data available - creating minimal models")
                
                # Create minimal models that will be updated when real data becomes available
                gb_model = GradientBoostingClassifier(
                    n_estimators=10,
                    learning_rate=0.1,
                    max_depth=2,
                    random_state=42
                )
                
                rf_model = RandomForestClassifier(
                    n_estimators=10,
                    max_depth=3,
                    min_samples_split=10,
                    random_state=42
                )
                
                # Create minimal training data for initialization (only if no real data available)
                logger.warning("⚠️ Creating minimal models with placeholder data - will be updated when real data is available")
                
                # Use simple placeholder data for initialization
                X_minimal = np.zeros((50, 14))  # All zeros instead of random
                y_minimal = np.full(50, 0)  # All HOLD instead of random
                
                # Fit minimal models
                gb_model.fit(X_minimal, y_minimal)
                rf_model.fit(X_minimal, y_minimal)
                
                # Create scaler
                scaler = StandardScaler()
                scaler.fit(X_minimal)
                
                logger.warning("⚠️ Minimal models created - will be updated when real data is available")
            
            # Store models for all symbols
            for symbol in ['BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'ADA_USDT']:
                self.models[symbol] = {
                    'GradientBoosting': gb_model,
                    'RandomForest': rf_model
                }
                self.scalers[symbol] = {
                    'GradientBoosting': scaler,
                    'RandomForest': scaler
                }
            
            # Store feature columns
            self.feature_columns = [
                'price_momentum', 'volume_ratio', 'rsi', 'macd',
                'sma_5', 'sma_20', 'ema_12', 'ema_26',
                'bb_position', 'bb_width', 'atr', 'volatility',
                'price_position', 'trend_strength'
            ]
            
        except Exception as e:
            logger.error(f"❌ Default model creation error: {e}")
            # Set empty models to prevent errors
            self.models = {}
            self.scalers = {}
    
    async def _get_real_training_data(self) -> Optional[tuple]:
        """Get real historical data for model training"""
        try:
            if not self.exchange_manager:
                return None
            
            # Try to get historical data for major symbols
            symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
            all_features = []
            all_labels = []
            
            for symbol in symbols:
                try:
                    # Get historical data
                    hist_data = await self.exchange_manager.get_historical_data(
                        symbol=symbol,
                        timeframe='1h',
                        limit=500
                    )
                    
                    if hist_data is not None and len(hist_data) > 100:
                        # Extract features and create labels
                        features, labels = self._prepare_training_data(hist_data)
                        
                        if features is not None and labels is not None:
                            all_features.extend(features)
                            all_labels.extend(labels)
                            
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get training data for {symbol}: {e}")
                    continue
            
            if len(all_features) > 100:
                # Convert to numpy arrays
                X = np.array(all_features)
                y = np.array(all_labels)
                
                logger.info(f"✅ Collected {len(X)} real training samples")
                return X, y
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Real training data collection error: {e}")
            return None
    
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
        """Get real signal history from database"""
        try:
            if not self.db_manager:
                logger.warning("⚠️ No database manager available for signal history")
                return []
            
            # Get real signal history from database
            query = """
                SELECT * FROM signals 
                WHERE symbol = ? AND timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            """.format(days)
            
            async with self.db_manager.get_connection() as conn:
                cursor = await conn.execute(query, (symbol,))
                rows = await cursor.fetchall()
                
                if rows:
                    signals = []
                    for row in rows:
                        signals.append({
                            'symbol': row[0],
                            'action': row[1],
                            'confidence': row[2],
                            'timestamp': row[3],
                            'strategy': row[4] if len(row) > 4 else 'unknown'
                        })
                    logger.info(f"📊 Retrieved {len(signals)} real signals for {symbol}")
                    return signals
                else:
                    logger.info(f"📊 No signal history found for {symbol}")
                    return []
            
        except Exception as e:
            logger.error(f"❌ Signal history error: {e}")
            return []

    def _get_ml_probability(self, filtered_signals: List[Dict]) -> float:
        """ML sinyallerinden ortalama probability hesapla"""
        ml_signals = [s for s in filtered_signals if s.get('source') == 'ML_ENSEMBLE']
        if ml_signals:
            return sum(s.get('confidence', 0.5) for s in ml_signals) / len(ml_signals)
        return 0.5
    
    def _calculate_technical_score(self, technical_signals: List[Dict]) -> float:
        """Technical sinyallerden ortalama confidence hesapla"""
        if technical_signals:
            return sum(s.get('confidence', 0.5) for s in technical_signals) / len(technical_signals)
        return 0.5
    
    def _calculate_volume_score(self, volume_signals: List[Dict]) -> float:
        """Volume sinyallerinden ortalama confidence hesapla"""
        if volume_signals:
            return sum(s.get('confidence', 0.5) for s in volume_signals) / len(volume_signals)
        return 0.5

    def _get_regime_signals(self, df: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """Generate signals based on market regime analysis"""
        signals = []
        
        try:
            if len(df) < 50:
                return signals
            
            # Detect market regime
            regime = self._detect_market_regime(df)
            
            # Generate regime-specific signals
            if regime == 'trending_market':
                # Trend following signals
                sma_20 = df['close'].rolling(20).mean()
                sma_50 = df['close'].rolling(50).mean()
                current_price = df['close'].iloc[-1]
                
                if current_price > sma_20.iloc[-1] > sma_50.iloc[-1]:
                    signals.append({
                        'type': 'BUY',
                        'source': 'REGIME_TREND',
                        'confidence': 0.7,
                        'value': current_price,
                        'reason': f'Strong uptrend detected in {regime}'
                    })
                elif current_price < sma_20.iloc[-1] < sma_50.iloc[-1]:
                    signals.append({
                        'type': 'SELL',
                        'source': 'REGIME_TREND',
                        'confidence': 0.7,
                        'value': current_price,
                        'reason': f'Strong downtrend detected in {regime}'
                    })
            
            elif regime == 'sideways_market':
                # Mean reversion signals
                bb_upper = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
                bb_lower = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
                current_price = df['close'].iloc[-1]
                
                if current_price <= bb_lower.iloc[-1]:
                    signals.append({
                        'type': 'BUY',
                        'source': 'REGIME_MEAN_REVERSION',
                        'confidence': 0.6,
                        'value': current_price,
                        'reason': f'Oversold in {regime}'
                    })
                elif current_price >= bb_upper.iloc[-1]:
                    signals.append({
                        'type': 'SELL',
                        'source': 'REGIME_MEAN_REVERSION',
                        'confidence': 0.6,
                        'value': current_price,
                        'reason': f'Overbought in {regime}'
                    })
            
            elif regime == 'volatile_market':
                # Volatility breakout signals
                atr = self._calculate_atr(df, period=14)
                current_atr = atr.iloc[-1] if len(atr) > 0 else 0
                avg_atr = atr.rolling(20).mean().iloc[-1] if len(atr) > 20 else 0
                
                if current_atr > avg_atr * 1.5:  # High volatility
                    signals.append({
                        'type': 'HOLD',
                        'source': 'REGIME_VOLATILE',
                        'confidence': 0.8,
                        'value': df['close'].iloc[-1],
                        'reason': f'High volatility detected, wait for stabilization'
                    })
            
        except Exception as e:
            logger.error(f"❌ Regime signals error: {e}")
        
        return signals
    
    def _detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect current market regime"""
        try:
            if len(df) < 50:
                return 'unknown'
            
            # Calculate volatility
            volatility = self._calculate_volatility(df, period=20)
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(df)
            
            # Calculate range
            range_pct = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close'].rolling(20).mean()
            avg_range = range_pct.iloc[-1] if len(range_pct) > 0 else 0
            
            # Regime classification
            if volatility > 0.8:
                return 'volatile_market'
            elif trend_strength > 0.7:
                return 'trending_market'
            elif avg_range < 0.05:  # Low range
                return 'sideways_market'
            else:
                return 'normal_market'
                
        except Exception as e:
            logger.error(f"❌ Market regime detection error: {e}")
            return 'unknown'
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength indicator"""
        try:
            if len(df) < 50:
                return 0.5
            
            # Linear regression slope
            x = np.arange(len(df))
            y = df['close'].values
            
            # Remove NaN values
            mask = ~np.isnan(y)
            if np.sum(mask) < 10:
                return 0.5
            
            x_clean = x[mask]
            y_clean = y[mask]
            
            # Calculate slope
            slope = np.polyfit(x_clean, y_clean, 1)[0]
            
            # Normalize slope to 0-1 range
            max_slope = np.std(y_clean) * 0.1  # Reasonable maximum slope
            trend_strength = min(abs(slope) / max_slope, 1.0) if max_slope > 0 else 0.5
            
            return trend_strength
            
        except Exception as e:
            logger.error(f"❌ Trend strength calculation error: {e}")
            return 0.5
    
    def _assess_signal_quality(self, signals: List[Dict], df: pd.DataFrame) -> float:
        """Assess overall signal quality"""
        try:
            if not signals:
                return 0.5
            
            # Signal consistency
            signal_types = [s['type'] for s in signals]
            consistency = len(set(signal_types)) / len(signal_types)  # Lower is better
            
            # Signal confidence distribution
            confidences = [s.get('confidence', 0) for s in signals]
            avg_confidence = np.mean(confidences)
            confidence_std = np.std(confidences)
            
            # Data quality
            data_quality = self._assess_data_quality(df)
            
            # Market volatility impact
            volatility = self._calculate_volatility(df, period=20)
            volatility_factor = 1.0 - (volatility * 0.3)  # Reduce quality in high volatility
            
            # Composite quality score
            quality_score = (
                (1.0 - consistency) * 0.3 +  # Signal consistency
                avg_confidence * 0.3 +       # Average confidence
                data_quality * 0.2 +         # Data quality
                volatility_factor * 0.2      # Volatility factor
            )
            
            return max(0.1, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"❌ Signal quality assessment error: {e}")
            return 0.5
    
    def _calculate_signal_strength(self, signals: List[Dict], signal_type: str) -> float:
        """Calculate signal strength for specific signal type"""
        try:
            if not signals:
                return 0.0
            
            # Filter signals by type
            type_signals = [s for s in signals if s['type'] == signal_type]
            
            if not type_signals:
                return 0.0
            
            # Calculate weighted strength
            total_strength = 0.0
            total_weight = 0.0
            
            for signal in type_signals:
                confidence = signal.get('confidence', 0)
                weight = signal.get('weight', 1.0)
                total_strength += confidence * weight
                total_weight += weight
            
            return total_strength / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"❌ Signal strength calculation error: {e}")
            return 0.0
    
    def _calculate_signal_reliability(self, signals: List[Dict], df: pd.DataFrame) -> float:
        """Calculate signal reliability based on historical accuracy"""
        try:
            if not signals:
                return 0.5
            
            # Source reliability weights (based on historical performance)
            source_reliability = {
                'technical': 0.7,
                'ml': 0.8,
                'volume': 0.6,
                'regime': 0.65
            }
            
            # Calculate weighted reliability
            total_reliability = 0.0
            total_weight = 0.0
            
            for signal in signals:
                source_type = signal.get('source_type', 'technical')
                weight = signal.get('weight', 1.0)
                reliability = source_reliability.get(source_type, 0.5)
                
                total_reliability += reliability * weight
                total_weight += weight
            
            return total_reliability / total_weight if total_weight > 0 else 0.5
            
        except Exception as e:
            logger.error(f"❌ Signal reliability calculation error: {e}")
            return 0.5
    
    def _calculate_enhanced_confidence(self, probabilities: np.ndarray, features: Dict[str, float], model_name: str) -> float:
        """Calculate enhanced confidence based on probabilities and feature quality"""
        try:
            # Base confidence from model probabilities
            base_confidence = max(probabilities)
            
            # Feature quality adjustment
            feature_quality = self._assess_feature_quality(features)
            
            # Model-specific adjustments
            if model_name == 'GradientBoosting':
                # GB tends to be more confident, so we adjust slightly
                confidence = base_confidence * 0.95
            elif model_name == 'RandomForest':
                # RF is more conservative
                confidence = base_confidence * 1.05
            else:
                confidence = base_confidence
            
            # Apply feature quality adjustment
            confidence *= feature_quality
            
            return min(confidence, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"❌ Enhanced confidence calculation error: {e}")
            return 0.5
    
    def _assess_feature_quality(self, features: Dict[str, float]) -> float:
        """Assess the quality of input features"""
        try:
            quality_score = 1.0
            
            # Check for missing or invalid features
            for key, value in features.items():
                if value is None or np.isnan(value) or np.isinf(value):
                    quality_score *= 0.9  # Reduce quality for invalid features
                elif abs(value) > 100:  # Unusually large values
                    quality_score *= 0.95
            
            # Check feature diversity
            unique_values = len(set(features.values()))
            if unique_values < len(features) * 0.5:  # Low diversity
                quality_score *= 0.8
            
            return quality_score
            
        except Exception as e:
            logger.error(f"❌ Feature quality assessment error: {e}")
            return 0.5
    
    def _calculate_ml_signal_strength(self, prediction: Dict[str, Any], df: pd.DataFrame) -> float:
        """Calculate ML signal strength based on multiple factors"""
        try:
            base_strength = prediction['confidence']
            
            # Market condition adjustment
            market_volatility = self._calculate_volatility(df, period=20)
            trend_strength = self._calculate_trend_strength(df)
            
            # Adjust strength based on market conditions
            if prediction['type'] == 'BUY' and trend_strength > 0.7:
                base_strength *= 1.1  # Stronger buy signal in uptrend
            elif prediction['type'] == 'SELL' and trend_strength < 0.3:
                base_strength *= 1.1  # Stronger sell signal in downtrend
            
            # Volatility adjustment
            if market_volatility > 0.8:
                base_strength *= 0.9  # Reduce strength in high volatility
            
            return min(base_strength, 1.0)
            
        except Exception as e:
            logger.error(f"❌ ML signal strength calculation error: {e}")
            return prediction.get('confidence', 0.5)
    
    async def update_adaptive_parameters(self, performance_metrics: Dict[str, Any]):
        """Update adaptive weights and thresholds based on performance with enhanced logic"""
        try:
            # Extract performance metrics
            win_rate = performance_metrics.get('win_rate', 0.5)
            avg_return = performance_metrics.get('avg_return', 0)
            sharpe_ratio = performance_metrics.get('sharpe_ratio', 0)
            total_trades = performance_metrics.get('total_trades', 0)
            max_drawdown = performance_metrics.get('max_drawdown', 0)
            
            # Calculate comprehensive performance score
            performance_score = self._calculate_comprehensive_performance_score(
                win_rate, avg_return, sharpe_ratio, total_trades, max_drawdown
            )
            
            # Update adaptive weights based on performance
            await self._update_adaptive_weights(performance_score, win_rate, sharpe_ratio)
            
            # Update adaptive thresholds based on performance
            await self._update_adaptive_thresholds(win_rate, sharpe_ratio, max_drawdown)
            
            # Log adaptive parameter updates
            logger.info(f"🔄 Adaptive parameters updated - Performance: {performance_score:.3f}")
            logger.info(f"📊 New weights: {self.adaptive_weights}")
            logger.info(f"🎯 New thresholds: {self.adaptive_thresholds}")
            
        except Exception as e:
            logger.error(f"❌ Adaptive parameters update error: {e}")
    
    def _calculate_comprehensive_performance_score(self, win_rate: float, avg_return: float, 
                                                 sharpe_ratio: float, total_trades: int, 
                                                 max_drawdown: float) -> float:
        """Calculate comprehensive performance score"""
        try:
            # Base score components
            win_rate_score = win_rate * 0.3
            return_score = max(0, avg_return) * 0.25
            sharpe_score = max(0, sharpe_ratio) * 0.25
            drawdown_penalty = max_drawdown * 0.2
            
            # Trade count adjustment
            trade_adjustment = min(1.0, total_trades / 50)  # Normalize to 50 trades
            
            # Calculate base score
            base_score = (win_rate_score + return_score + sharpe_score - drawdown_penalty) * trade_adjustment
            
            # Apply performance bonuses/penalties
            if win_rate > 0.6 and sharpe_ratio > 1.0:
                base_score *= 1.1  # Bonus for excellent performance
            elif win_rate < 0.4 or sharpe_ratio < 0.5:
                base_score *= 0.8  # Penalty for poor performance
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error(f"❌ Performance score calculation error: {e}")
            return 0.5
    
    async def _update_adaptive_weights(self, performance_score: float, win_rate: float, sharpe_ratio: float):
        """Update adaptive weights based on performance"""
        try:
            # Calculate weight adjustments based on performance
            if performance_score > 0.7:  # Excellent performance
                # Increase ML weight, decrease technical
                self.adaptive_weights['ml'] = min(0.7, self.adaptive_weights['ml'] + self.learning_rate * 2)
                self.adaptive_weights['technical'] = max(0.15, self.adaptive_weights['technical'] - self.learning_rate)
                self.adaptive_weights['volume'] = max(0.1, self.adaptive_weights['volume'] - self.learning_rate * 0.5)
                self.adaptive_weights['regime'] = max(0.05, self.adaptive_weights['regime'] - self.learning_rate * 0.5)
                
            elif performance_score > 0.5:  # Good performance
                # Moderate adjustments
                self.adaptive_weights['ml'] = min(0.6, self.adaptive_weights['ml'] + self.learning_rate)
                self.adaptive_weights['technical'] = max(0.2, self.adaptive_weights['technical'] - self.learning_rate * 0.5)
                
            elif performance_score < 0.3:  # Poor performance
                # Increase technical weight, decrease ML
                self.adaptive_weights['technical'] = min(0.6, self.adaptive_weights['technical'] + self.learning_rate * 2)
                self.adaptive_weights['ml'] = max(0.2, self.adaptive_weights['ml'] - self.learning_rate)
                self.adaptive_weights['volume'] = min(0.3, self.adaptive_weights['volume'] + self.learning_rate)
                self.adaptive_weights['regime'] = min(0.2, self.adaptive_weights['regime'] + self.learning_rate)
            
            # Normalize weights to sum to 1.0
            total_weight = sum(self.adaptive_weights.values())
            for key in self.adaptive_weights:
                self.adaptive_weights[key] /= total_weight
                
        except Exception as e:
            logger.error(f"❌ Adaptive weights update error: {e}")
    
    async def _update_adaptive_thresholds(self, win_rate: float, sharpe_ratio: float, max_drawdown: float):
        """Update adaptive thresholds based on performance"""
        try:
            # Update confidence threshold based on win rate
            if win_rate < 0.4:  # Low win rate
                # Increase confidence threshold for more selective trading
                self.adaptive_thresholds['confidence_min'] = min(0.85, 
                    self.adaptive_thresholds['confidence_min'] + self.learning_rate * 2)
            elif win_rate > 0.6:  # High win rate
                # Decrease confidence threshold for more aggressive trading
                self.adaptive_thresholds['confidence_min'] = max(0.45, 
                    self.adaptive_thresholds['confidence_min'] - self.learning_rate)
            
            # Update signal strength threshold based on Sharpe ratio
            if sharpe_ratio < 0.5:  # Low Sharpe ratio
                # Increase signal strength threshold
                self.adaptive_thresholds['signal_strength_min'] = min(0.8, 
                    self.adaptive_thresholds['signal_strength_min'] + self.learning_rate)
            elif sharpe_ratio > 1.5:  # High Sharpe ratio
                # Decrease signal strength threshold
                self.adaptive_thresholds['signal_strength_min'] = max(0.3, 
                    self.adaptive_thresholds['signal_strength_min'] - self.learning_rate)
            
            # Update ML probability threshold based on drawdown
            if max_drawdown > 0.2:  # High drawdown
                # Increase ML probability threshold for more conservative predictions
                self.adaptive_thresholds['ml_probability_min'] = min(0.9, 
                    self.adaptive_thresholds['ml_probability_min'] + self.learning_rate)
            elif max_drawdown < 0.1:  # Low drawdown
                # Decrease ML probability threshold
                self.adaptive_thresholds['ml_probability_min'] = max(0.5, 
                    self.adaptive_thresholds['ml_probability_min'] - self.learning_rate)
                
        except Exception as e:
            logger.error(f"❌ Adaptive thresholds update error: {e}")
    
    async def save_model_version(self, model_name: str, model_data: Dict[str, Any], performance: Dict[str, Any]):
        """Save model version with performance metrics"""
        try:
            version = f"v{len(self.model_versions.get(model_name, [])) + 1}.0"
            
            # Create version directory
            version_dir = Path(f'models/{model_name}/{version}')
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model files
            import joblib
            joblib.dump(model_data['model'], version_dir / 'model.pkl')
            joblib.dump(model_data['scaler'], version_dir / 'scaler.pkl')
            
            # Save performance metrics
            performance_file = version_dir / 'performance.json'
            import json
            with open(performance_file, 'w') as f:
                json.dump(performance, f, indent=2)
            
            # Update version tracking
            if model_name not in self.model_versions:
                self.model_versions[model_name] = []
            self.model_versions[model_name].append({
                'version': version,
                'created_at': datetime.now().isoformat(),
                'performance': performance
            })
            
            logger.info(f"💾 Model version saved: {model_name}/{version}")
            
        except Exception as e:
            logger.error(f"❌ Model version save error: {e}")
    
    async def load_best_model_version(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Load the best performing model version"""
        try:
            if model_name not in self.model_versions:
                return None
            
            # Find best performing version
            best_version = None
            best_score = -np.inf
            
            for version_info in self.model_versions[model_name]:
                performance = version_info['performance']
                score = self._calculate_model_score(performance)
                
                if score > best_score:
                    best_score = score
                    best_version = version_info['version']
            
            if best_version:
                # Load best version
                version_dir = Path(f'models/{model_name}/{best_version}')
                import joblib
                
                model = joblib.load(version_dir / 'model.pkl')
                scaler = joblib.load(version_dir / 'scaler.pkl')
                
                return {
                    'model': model,
                    'scaler': scaler,
                    'version': best_version,
                    'performance': next(v['performance'] for v in self.model_versions[model_name] if v['version'] == best_version)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Best model version load error: {e}")
            return None
    
    async def _get_dynamic_adaptive_weights(self) -> Dict[str, float]:
        """Get dynamic adaptive weights based on performance"""
        try:
            # Base adaptive weights
            base_weights = {
                'technical': 0.3,
                'ml': 0.4,
                'volume': 0.2,
                'regime': 0.1
            }
            
            # This would be adjusted based on performance
            # For now, return base weights
            return base_weights
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic adaptive weights: {e}")
            return {'technical': 0.3, 'ml': 0.4, 'volume': 0.2, 'regime': 0.1}
    
    async def _get_dynamic_adaptive_thresholds(self) -> Dict[str, float]:
        """Get dynamic adaptive thresholds based on performance"""
        try:
            # Base adaptive thresholds
            base_thresholds = {
                'confidence_min': 0.6,
                'signal_strength_min': 0.5,
                'ml_probability_min': 0.7
            }
            
            # This would be adjusted based on performance
            # For now, return base thresholds
            return base_thresholds
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic adaptive thresholds: {e}")
            return {'confidence_min': 0.6, 'signal_strength_min': 0.5, 'ml_probability_min': 0.7}
    
    async def _get_dynamic_learning_rate(self, ai_config: Dict[str, Any]) -> float:
        """Get dynamic learning rate based on performance"""
        try:
            # Base learning rate
            base_rate = ai_config.get('learning_rate', 0.01)
            
            # This would be adjusted based on performance
            # For now, return base rate
            return base_rate
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic learning rate: {e}")
            return ai_config.get('learning_rate', 0.01)
    
    async def _get_dynamic_performance_window(self, ai_config: Dict[str, Any]) -> int:
        """Get dynamic performance window based on performance"""
        try:
            # Base performance window
            base_window = ai_config.get('performance_window', 100)
            
            # This would be adjusted based on performance
            # For now, return base window
            return base_window
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic performance window: {e}")
            return ai_config.get('performance_window', 100)
    
    async def _get_dynamic_cache_duration(self) -> int:
        """Get dynamic cache duration based on market volatility"""
        try:
            # Base cache duration
            base_duration = 300
            
            # This would be adjusted based on market volatility
            # For now, return base duration
            return base_duration
            
        except Exception as e:
            logger.warning(f"⚠️ Could not calculate dynamic cache duration: {e}")
            return 300
    
    def _calculate_model_score(self, performance: Dict[str, Any]) -> float:
        """Calculate model performance score"""
        try:
            accuracy = performance.get('accuracy', 0.5)
            precision = performance.get('precision', 0.5)
            recall = performance.get('recall', 0.5)
            f1_score = performance.get('f1_score', 0.5)
            
            # Weighted score
            score = (accuracy * 0.3 + precision * 0.25 + recall * 0.25 + f1_score * 0.2)
            
            return score
            
        except Exception as e:
            logger.error(f"❌ Model score calculation error: {e}")
            return 0.5