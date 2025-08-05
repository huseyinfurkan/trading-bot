"""
AI Signal Filter
Gerçek makine öğrenmesi modelleri ile sinyal filtreleme ve üretme
"""

import numpy as np
import pandas as pd
import asyncio
import pickle
import joblib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

# ML Libraries
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import yfinance as yf

# Technical Analysis
import talib
import pandas_ta as ta


class AISignalFilter:
    """AI destekli sinyal filtreleme sistemi"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = ai_config
        self.db_manager = db_manager
        
        # Model configuration
        self.confidence_threshold = ai_config.get('confidence_threshold', 0.75)
        self.signal_strength_min = ai_config.get('signal_strength_min', 0.65)
        self.technical_weight = ai_config.get('technical_weight', 0.5)
        self.sentiment_weight = ai_config.get('sentiment_weight', 0.3)
        self.fundamental_weight = ai_config.get('fundamental_weight', 0.2)
        
        # Models
        self.models = {}
        self.scalers = {}
        self.label_encoders = {}
        self.feature_columns = []
        
        # Model paths
        self.model_dir = Path("models")
        self.model_dir.mkdir(exist_ok=True)
        
        # Feature definitions
        self._define_features()
        
        # Training data cache
        self.training_data_cache = {}
        self.last_retrain = None
        self.retrain_frequency = ai_config.get('retrain_frequency_hours', 24)
        
    def _define_features(self) -> None:
        """Feature tanımlarını oluştur"""
        # Technical features
        self.technical_features = [
            'rsi_14', 'rsi_21', 'rsi_30',
            'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26', 'ema_50',
            'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'atr_14', 'atr_ratio',
            'stoch_k', 'stoch_d',
            'williams_r',
            'cci_14',
            'momentum_10',
            'roc_10',
            'mfi_14',
            'obv_ratio',
            'ad_line',
            'price_change_1h', 'price_change_4h', 'price_change_1d',
            'volume_change_1h', 'volume_change_4h',
            'volume_sma_ratio',
            'high_low_ratio',
            'support_resistance_score',
            'trend_strength',
            'volatility_rank'
        ]
        
        # Pattern features
        self.pattern_features = [
            'doji', 'hammer', 'shooting_star', 'engulfing_bull', 'engulfing_bear',
            'morning_star', 'evening_star', 'hanging_man'
        ]
        
        # Market context features
        self.context_features = [
            'hour_of_day', 'day_of_week', 'market_session',
            'btc_correlation', 'market_dominance'
        ]
        
        # All features
        self.feature_columns = (
            self.technical_features + 
            self.pattern_features + 
            self.context_features
        )
        
        logger.info(f"📊 Toplam feature sayısı: {len(self.feature_columns)}")
    
    async def initialize(self) -> None:
        """AI sistemini başlat"""
        try:
            logger.info("🤖 AI Signal Filter başlatılıyor...")
            
            # Load existing models
            await self._load_saved_models()
            
            # Check if retraining is needed
            if self._should_retrain():
                await self.retrain_all_models()
            
            logger.success("✅ AI Signal Filter başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ AI inicializasyon hatası: {e}")
            raise
    
    async def analyze_signals(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ana sinyal analizi fonksiyonu"""
        try:
            logger.debug(f"🔍 {symbol} için sinyal analizi başlatılıyor...")
            
            # Get dataframe
            df = market_data.get('dataframe')
            if df is None or len(df) < 200:
                logger.warning(f"⚠️ {symbol} için yetersiz veri")
                return self._get_empty_signals()
            
            # Calculate features
            features_df = await self._calculate_features(df)
            
            if features_df is None or len(features_df) == 0:
                logger.warning(f"⚠️ {symbol} için feature hesaplanamadı")
                return self._get_empty_signals()
            
            # Get ML signals
            ml_signals = await self._get_ml_signals(features_df, symbol)
            
            # Get technical signals
            technical_signals = await self._get_technical_signals(df)
            
            # Get pattern signals
            pattern_signals = await self._get_pattern_signals(df)
            
            # Get sentiment signals (placeholder for now)
            sentiment_signals = await self._get_sentiment_signals(symbol)
            
            # Combine all signals
            combined_signals = await self._combine_signals(
                ml_signals, technical_signals, pattern_signals, sentiment_signals
            )
            
            # Calculate overall confidence and strength
            confidence = await self._calculate_signal_confidence(combined_signals)
            strength = await self._calculate_signal_strength(combined_signals)
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'signals': combined_signals,
                'confidence': confidence,
                'strength': strength,
                'ml_prediction': ml_signals,
                'technical_score': len(technical_signals),
                'pattern_score': len(pattern_signals),
                'recommendation': self._get_recommendation(combined_signals, confidence)
            }
            
            # Save analysis
            await self._save_signal_analysis(symbol, result)
            
            logger.debug(f"✅ {symbol} sinyal analizi tamamlandı: {len(combined_signals)} sinyal")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ {symbol} sinyal analizi hatası: {e}")
            return self._get_empty_signals()
    
    async def _calculate_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Tüm feature'ları hesapla"""
        try:
            if len(df) < 200:
                return None
            
            features_df = df.copy()
            
            # Technical indicators using talib
            try:
                # RSI
                features_df['rsi_14'] = talib.RSI(df['close'].values, timeperiod=14)
                features_df['rsi_21'] = talib.RSI(df['close'].values, timeperiod=21)
                features_df['rsi_30'] = talib.RSI(df['close'].values, timeperiod=30)
                
                # Moving averages
                features_df['sma_10'] = talib.SMA(df['close'].values, timeperiod=10)
                features_df['sma_20'] = talib.SMA(df['close'].values, timeperiod=20)
                features_df['sma_50'] = talib.SMA(df['close'].values, timeperiod=50)
                features_df['sma_200'] = talib.SMA(df['close'].values, timeperiod=200)
                
                features_df['ema_12'] = talib.EMA(df['close'].values, timeperiod=12)
                features_df['ema_26'] = talib.EMA(df['close'].values, timeperiod=26)
                features_df['ema_50'] = talib.EMA(df['close'].values, timeperiod=50)
                
                # MACD
                macd, macd_signal, macd_hist = talib.MACD(df['close'].values)
                features_df['macd'] = macd
                features_df['macd_signal'] = macd_signal
                features_df['macd_histogram'] = macd_hist
                
                # Bollinger Bands
                bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'].values)
                features_df['bb_upper'] = bb_upper
                features_df['bb_middle'] = bb_middle
                features_df['bb_lower'] = bb_lower
                features_df['bb_width'] = (bb_upper - bb_lower) / bb_middle
                
                # ATR
                features_df['atr_14'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values)
                features_df['atr_ratio'] = features_df['atr_14'] / features_df['close']
                
                # Stochastic
                stoch_k, stoch_d = talib.STOCH(df['high'].values, df['low'].values, df['close'].values)
                features_df['stoch_k'] = stoch_k
                features_df['stoch_d'] = stoch_d
                
                # Williams %R
                features_df['williams_r'] = talib.WILLR(df['high'].values, df['low'].values, df['close'].values)
                
                # CCI
                features_df['cci_14'] = talib.CCI(df['high'].values, df['low'].values, df['close'].values)
                
                # Momentum
                features_df['momentum_10'] = talib.MOM(df['close'].values, timeperiod=10)
                
                # ROC
                features_df['roc_10'] = talib.ROC(df['close'].values, timeperiod=10)
                
                # MFI
                features_df['mfi_14'] = talib.MFI(df['high'].values, df['low'].values, df['close'].values, df['volume'].values)
                
                # OBV
                obv = talib.OBV(df['close'].values, df['volume'].values)
                features_df['obv_ratio'] = obv / obv.rolling(20).mean()
                
                # AD Line
                features_df['ad_line'] = talib.AD(df['high'].values, df['low'].values, df['close'].values, df['volume'].values)
                
            except Exception as e:
                logger.warning(f"⚠️ TALib hesaplama hatası: {e}")
                # Fallback to pandas calculations
                features_df = self._calculate_features_pandas(features_df)
            
            # Price and volume changes
            features_df['price_change_1h'] = features_df['close'].pct_change(1)
            features_df['price_change_4h'] = features_df['close'].pct_change(4)
            features_df['price_change_1d'] = features_df['close'].pct_change(24)
            
            features_df['volume_change_1h'] = features_df['volume'].pct_change(1)
            features_df['volume_change_4h'] = features_df['volume'].pct_change(4)
            
            # Volume ratio
            features_df['volume_sma_ratio'] = features_df['volume'] / features_df['volume'].rolling(20).mean()
            
            # High-Low ratio
            features_df['high_low_ratio'] = (features_df['high'] - features_df['low']) / features_df['close']
            
            # Custom features
            features_df['support_resistance_score'] = self._calculate_support_resistance(features_df)
            features_df['trend_strength'] = self._calculate_trend_strength(features_df)
            features_df['volatility_rank'] = features_df['atr_ratio'].rolling(100).rank(pct=True)
            
            # Candlestick patterns
            patterns = self._calculate_candlestick_patterns(df)
            for pattern_name, pattern_values in patterns.items():
                features_df[pattern_name] = pattern_values
            
            # Market context
            features_df['hour_of_day'] = pd.to_datetime(features_df['timestamp']).dt.hour
            features_df['day_of_week'] = pd.to_datetime(features_df['timestamp']).dt.dayofweek
            features_df['market_session'] = self._get_market_session(features_df['hour_of_day'])
            
            # BTC correlation (placeholder)
            features_df['btc_correlation'] = 0.7
            features_df['market_dominance'] = 0.5
            
            # NaN değerleri temizle
            features_df = features_df.ffill().fillna(0)
            
            # Select only feature columns
            feature_cols = [col for col in self.feature_columns if col in features_df.columns]
            features_df = features_df[feature_cols]
            
            return features_df
            
        except Exception as e:
            logger.error(f"❌ Feature hesaplama hatası: {e}")
            return None
    
    def _calculate_features_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pandas ile temel feature hesaplamaları (TALib fallback)"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
            
            # Moving averages
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # ATR approximation
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['atr_14'] = df['tr'].rolling(14).mean()
            df['atr_ratio'] = df['atr_14'] / df['close']
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Pandas feature hesaplama hatası: {e}")
            return df
    
    def _calculate_candlestick_patterns(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Candlestick pattern'larını hesapla"""
        try:
            patterns = {}
            
            if len(df) < 10:
                return {name: np.zeros(len(df)) for name in self.pattern_features}
            
            try:
                # TALib patterns
                patterns['doji'] = talib.CDLDOJI(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['hammer'] = talib.CDLHAMMER(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['shooting_star'] = talib.CDLSHOOTINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['engulfing_bull'] = talib.CDLENGULFING(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['engulfing_bear'] = -patterns['engulfing_bull']  # Reverse for bearish
                patterns['morning_star'] = talib.CDLMORNINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['evening_star'] = talib.CDLEVENINGSTAR(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                patterns['hanging_man'] = talib.CDLHANGINGMAN(df['open'].values, df['high'].values, df['low'].values, df['close'].values)
                
            except Exception:
                # Fallback: simple pattern detection
                patterns = self._simple_pattern_detection(df)
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Pattern hesaplama hatası: {e}")
            return {name: np.zeros(len(df)) for name in self.pattern_features}
    
    def _simple_pattern_detection(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Basit pattern tanıma (TALib olmadan)"""
        patterns = {}
        length = len(df)
        
        # Doji detection
        body_size = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        doji_condition = body_size / total_range < 0.1
        patterns['doji'] = np.where(doji_condition, 100, 0)
        
        # Simple hammer detection
        lower_shadow = np.where(df['close'] > df['open'], 
                               df['open'] - df['low'], 
                               df['close'] - df['low'])
        upper_shadow = np.where(df['close'] > df['open'],
                               df['high'] - df['close'],
                               df['high'] - df['open'])
        hammer_condition = (lower_shadow > 2 * body_size) & (upper_shadow < body_size)
        patterns['hammer'] = np.where(hammer_condition, 100, 0)
        
        # Fill other patterns with zeros for now
        for pattern_name in self.pattern_features:
            if pattern_name not in patterns:
                patterns[pattern_name] = np.zeros(length)
        
        return patterns
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> pd.Series:
        """Support/Resistance skorunu hesapla"""
        try:
            if len(df) < 50:
                return pd.Series(0.5, index=df.index)
            
            # Rolling min/max for support/resistance levels
            window = 20
            support = df['low'].rolling(window).min()
            resistance = df['high'].rolling(window).max()
            
            # Distance from support/resistance
            dist_support = (df['close'] - support) / df['close']
            dist_resistance = (resistance - df['close']) / df['close']
            
            # Score (0-1, where 0.5 is neutral)
            score = 0.5 + (dist_support - dist_resistance) * 5
            return np.clip(score, 0, 1)
            
        except Exception as e:
            logger.error(f"❌ Support/Resistance hesaplama hatası: {e}")
            return pd.Series(0.5, index=df.index)
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Trend gücünü hesapla"""
        try:
            if len(df) < 50:
                return pd.Series(0.5, index=df.index)
            
            # Price vs moving averages
            sma_20 = df['close'].rolling(20).mean()
            sma_50 = df['close'].rolling(50).mean()
            
            # Price above/below MAs
            above_sma20 = (df['close'] > sma_20).astype(int)
            above_sma50 = (df['close'] > sma_50).astype(int)
            
            # Trend consistency over last 10 periods
            trend_consistency = (above_sma20.rolling(10).sum() / 10)
            
            return trend_consistency
            
        except Exception as e:
            logger.error(f"❌ Trend strength hesaplama hatası: {e}")
            return pd.Series(0.5, index=df.index)
    
    def _get_market_session(self, hour: pd.Series) -> pd.Series:
        """Market session'ı belirle (UTC saatine göre)"""
        try:
            # 0: Asian (22-06 UTC), 1: European (06-14 UTC), 2: US (14-22 UTC)
            conditions = [
                (hour >= 22) | (hour < 6),
                (hour >= 6) & (hour < 14),
                (hour >= 14) & (hour < 22)
            ]
            choices = [0, 1, 2]
            
            return pd.Series(np.select(conditions, choices, default=0), index=hour.index)
            
        except Exception as e:
            logger.error(f"❌ Market session hesaplama hatası: {e}")
            return pd.Series(0, index=hour.index)
    
    async def _get_ml_signals(self, features_df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """ML modellerinden sinyal al"""
        try:
            if len(features_df) == 0 or symbol not in self.models:
                return {'prediction': 'HOLD', 'confidence': 0.5, 'probabilities': [0.33, 0.34, 0.33]}
            
            # Get latest features
            latest_features = features_df.iloc[-1:][self.feature_columns]
            
            # Handle missing columns
            for col in self.feature_columns:
                if col not in latest_features.columns:
                    latest_features[col] = 0
            
            latest_features = latest_features[self.feature_columns]
            
            # Scale features
            if symbol in self.scalers:
                latest_features_scaled = self.scalers[symbol].transform(latest_features)
            else:
                latest_features_scaled = latest_features.values
            
            # Predict
            model = self.models[symbol]
            prediction = model.predict(latest_features_scaled)[0]
            probabilities = model.predict_proba(latest_features_scaled)[0]
            
            # Convert prediction to signal
            signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            signal = signal_map.get(prediction, 'HOLD')
            
            confidence = max(probabilities)
            
            return {
                'prediction': signal,
                'confidence': confidence,
                'probabilities': probabilities.tolist()
            }
            
        except Exception as e:
            logger.error(f"❌ ML sinyal hatası: {e}")
            return {'prediction': 'HOLD', 'confidence': 0.5, 'probabilities': [0.33, 0.34, 0.33]}
    
    async def _get_technical_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Teknik analiz sinyalleri"""
        signals = []
        
        try:
            if len(df) < 50:
                return signals
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # RSI signals
            rsi = self._calculate_rsi(df['close'], 14)
            if len(rsi) > 0:
                current_rsi = rsi.iloc[-1]
                if current_rsi < 30:
                    signals.append({'type': 'BUY', 'reason': 'RSI_OVERSOLD', 'strength': 0.8})
                elif current_rsi > 70:
                    signals.append({'type': 'SELL', 'reason': 'RSI_OVERBOUGHT', 'strength': 0.8})
            
            # MACD signals
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            macd = ema12 - ema26
            signal_line = macd.ewm(span=9).mean()
            
            if len(macd) > 1:
                if macd.iloc[-1] > signal_line.iloc[-1] and macd.iloc[-2] <= signal_line.iloc[-2]:
                    signals.append({'type': 'BUY', 'reason': 'MACD_CROSSOVER', 'strength': 0.7})
                elif macd.iloc[-1] < signal_line.iloc[-1] and macd.iloc[-2] >= signal_line.iloc[-2]:
                    signals.append({'type': 'SELL', 'reason': 'MACD_CROSSUNDER', 'strength': 0.7})
            
            # Moving Average signals
            sma20 = df['close'].rolling(20).mean()
            sma50 = df['close'].rolling(50).mean()
            
            if len(sma20) > 1 and len(sma50) > 1:
                if (sma20.iloc[-1] > sma50.iloc[-1] and sma20.iloc[-2] <= sma50.iloc[-2]):
                    signals.append({'type': 'BUY', 'reason': 'MA_GOLDEN_CROSS', 'strength': 0.9})
                elif (sma20.iloc[-1] < sma50.iloc[-1] and sma20.iloc[-2] >= sma50.iloc[-2]):
                    signals.append({'type': 'SELL', 'reason': 'MA_DEATH_CROSS', 'strength': 0.9})
            
            # Bollinger Bands signals
            bb_period = 20
            sma = df['close'].rolling(bb_period).mean()
            bb_std = df['close'].rolling(bb_period).std()
            bb_upper = sma + (bb_std * 2)
            bb_lower = sma - (bb_std * 2)
            
            if len(bb_upper) > 0 and len(bb_lower) > 0:
                if latest['close'] < bb_lower.iloc[-1]:
                    signals.append({'type': 'BUY', 'reason': 'BB_OVERSOLD', 'strength': 0.6})
                elif latest['close'] > bb_upper.iloc[-1]:
                    signals.append({'type': 'SELL', 'reason': 'BB_OVERBOUGHT', 'strength': 0.6})
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Teknik sinyal hatası: {e}")
            return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesapla"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"❌ RSI hesaplama hatası: {e}")
            return pd.Series()
    
    async def _get_pattern_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Candlestick pattern sinyalleri"""
        signals = []
        
        try:
            if len(df) < 10:
                return signals
            
            patterns = self._calculate_candlestick_patterns(df)
            
            # Check latest patterns
            for pattern_name, pattern_values in patterns.items():
                if len(pattern_values) > 0 and pattern_values[-1] != 0:
                    if pattern_name in ['hammer', 'morning_star', 'engulfing_bull']:
                        signals.append({
                            'type': 'BUY',
                            'reason': f'PATTERN_{pattern_name.upper()}',
                            'strength': 0.6
                        })
                    elif pattern_name in ['shooting_star', 'evening_star', 'engulfing_bear', 'hanging_man']:
                        signals.append({
                            'type': 'SELL',
                            'reason': f'PATTERN_{pattern_name.upper()}',
                            'strength': 0.6
                        })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Pattern sinyal hatası: {e}")
            return signals
    
    async def _get_sentiment_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Sentiment analizi sinyalleri (placeholder)"""
        try:
            # Placeholder - gerçekte fear & greed index, social sentiment vb. kullanılacak
            import random
            
            fear_greed_index = random.randint(0, 100)
            
            signals = []
            
            if fear_greed_index < 25:  # Extreme fear
                signals.append({
                    'type': 'BUY',
                    'reason': 'SENTIMENT_EXTREME_FEAR',
                    'strength': 0.5
                })
            elif fear_greed_index > 75:  # Extreme greed
                signals.append({
                    'type': 'SELL',
                    'reason': 'SENTIMENT_EXTREME_GREED',
                    'strength': 0.5
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Sentiment sinyal hatası: {e}")
            return []
    
    async def _combine_signals(self, ml_signals: Dict, technical_signals: List, 
                             pattern_signals: List, sentiment_signals: List) -> List[Dict[str, Any]]:
        """Tüm sinyalleri birleştir"""
        try:
            combined = []
            
            # Add ML signal
            if ml_signals['prediction'] != 'HOLD':
                combined.append({
                    'type': ml_signals['prediction'],
                    'reason': 'ML_PREDICTION',
                    'strength': ml_signals['confidence'],
                    'source': 'ml'
                })
            
            # Add technical signals
            for signal in technical_signals:
                signal['source'] = 'technical'
                combined.append(signal)
            
            # Add pattern signals
            for signal in pattern_signals:
                signal['source'] = 'pattern'
                combined.append(signal)
            
            # Add sentiment signals
            for signal in sentiment_signals:
                signal['source'] = 'sentiment'
                combined.append(signal)
            
            return combined
            
        except Exception as e:
            logger.error(f"❌ Sinyal birleştirme hatası: {e}")
            return []
    
    async def _calculate_signal_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """Sinyal güvenilirliğini hesapla"""
        try:
            if not signals:
                return 0.0
            
            # Signal agreement
            buy_signals = [s for s in signals if s['type'] == 'BUY']
            sell_signals = [s for s in signals if s['type'] == 'SELL']
            
            if len(buy_signals) == 0 and len(sell_signals) == 0:
                return 0.0
            
            # Consensus strength
            total_strength = sum(s.get('strength', 0.5) for s in signals)
            signal_count = len(signals)
            
            if signal_count == 0:
                return 0.0
            
            # Agreement score
            if len(buy_signals) > len(sell_signals):
                agreement = len(buy_signals) / signal_count
                avg_strength = sum(s.get('strength', 0.5) for s in buy_signals) / len(buy_signals)
            elif len(sell_signals) > len(buy_signals):
                agreement = len(sell_signals) / signal_count
                avg_strength = sum(s.get('strength', 0.5) for s in sell_signals) / len(sell_signals)
            else:
                agreement = 0.5
                avg_strength = 0.5
            
            # Diversity bonus (signals from different sources)
            sources = set(s.get('source', 'unknown') for s in signals)
            diversity_bonus = min(0.2, len(sources) * 0.05)
            
            confidence = (agreement * 0.6 + avg_strength * 0.3 + diversity_bonus)
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"❌ Güven hesaplama hatası: {e}")
            return 0.0
    
    async def _calculate_signal_strength(self, signals: List[Dict[str, Any]]) -> float:
        """Sinyal gücünü hesapla"""
        try:
            if not signals:
                return 0.0
            
            strengths = [s.get('strength', 0.5) for s in signals]
            return np.mean(strengths)
            
        except Exception as e:
            logger.error(f"❌ Sinyal gücü hesaplama hatası: {e}")
            return 0.0
    
    def _get_recommendation(self, signals: List[Dict[str, Any]], confidence: float) -> str:
        """Final öneri oluştur"""
        try:
            if confidence < self.confidence_threshold:
                return 'HOLD'
            
            buy_count = len([s for s in signals if s['type'] == 'BUY'])
            sell_count = len([s for s in signals if s['type'] == 'SELL'])
            
            if buy_count > sell_count:
                return 'BUY'
            elif sell_count > buy_count:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            logger.error(f"❌ Öneri oluşturma hatası: {e}")
            return 'HOLD'
    
    def _get_empty_signals(self) -> Dict[str, Any]:
        """Boş sinyal response'u"""
        return {
            'symbol': '',
            'timestamp': datetime.now(),
            'signals': [],
            'confidence': 0.0,
            'strength': 0.0,
            'ml_prediction': {'prediction': 'HOLD', 'confidence': 0.5},
            'technical_score': 0,
            'pattern_score': 0,
            'recommendation': 'HOLD'
        }
    
    async def _save_signal_analysis(self, symbol: str, analysis: Dict[str, Any]) -> None:
        """Sinyal analizini kaydet"""
        try:
            signal_data = {
                'symbol': symbol,
                'timestamp': analysis['timestamp'].isoformat(),
                'signal_type': analysis['recommendation'],
                'confidence': analysis['confidence'],
                'strength': analysis['strength'],
                'signal_count': len(analysis['signals']),
                'analysis_data': str(analysis)  # JSON as string for SQLite
            }
            
            await self.db_manager.save_signal(signal_data)
            
        except Exception as e:
            logger.error(f"❌ Sinyal kaydetme hatası: {e}")
    
    async def retrain_all_models(self) -> None:
        """Tüm modelleri yeniden eğit"""
        try:
            logger.info("🔄 Model yeniden eğitimi başlatılıyor...")
            
            # Major trading pairs for training
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
            
            for symbol in symbols:
                try:
                    await self._train_model(symbol)
                    logger.info(f"✅ {symbol} modeli eğitildi")
                except Exception as e:
                    logger.error(f"❌ {symbol} model eğitimi hatası: {e}")
            
            self.last_retrain = datetime.now()
            logger.success("✅ Model yeniden eğitimi tamamlandı")
            
        except Exception as e:
            logger.error(f"❌ Model eğitimi genel hatası: {e}")
    
    async def _train_model(self, symbol: str) -> None:
        """Tek sembol için model eğit"""
        try:
            # Get training data
            training_data = await self._prepare_training_data(symbol)
            
            if training_data is None or len(training_data) < 1000:
                logger.warning(f"⚠️ {symbol} için yetersiz eğitim verisi")
                return
            
            # Prepare features and labels
            X = training_data[self.feature_columns]
            y = training_data['target']
            
            # Handle missing columns
            for col in self.feature_columns:
                if col not in X.columns:
                    X[col] = 0
            
            X = X[self.feature_columns]
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)
            
            logger.info(f"📊 {symbol} Model Performance: Train={train_score:.3f}, Test={test_score:.3f}")
            
            # Save model and scaler
            self.models[symbol] = model
            self.scalers[symbol] = scaler
            
            # Save to disk
            model_path = self.model_dir / f"{symbol}_model.pkl"
            scaler_path = self.model_dir / f"{symbol}_scaler.pkl"
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            
        except Exception as e:
            logger.error(f"❌ {symbol} model eğitimi hatası: {e}")
    
    async def _prepare_training_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Model eğitimi için veri hazırla"""
        try:
            # Get historical data from yfinance
            yf_symbol = symbol.replace('USDT', '-USD')
            ticker = yf.Ticker(yf_symbol)
            
            # Get 1 year of 1h data
            data = ticker.history(period="1y", interval="1h")
            
            if data.empty:
                logger.warning(f"⚠️ {symbol} için veri alınamadı")
                return None
            
            # Convert to our format
            df = pd.DataFrame({
                'timestamp': data.index,
                'open': data['Open'].values,
                'high': data['High'].values,
                'low': data['Low'].values,
                'close': data['Close'].values,
                'volume': data['Volume'].values
            })
            
            # Calculate features
            features_df = await self._calculate_features(df)
            
            if features_df is None:
                return None
            
            # Create labels (future price movement)
            # 0: SELL (price decreases > 1%), 1: HOLD (price stable), 2: BUY (price increases > 1%)
            future_returns = df['close'].shift(-4).pct_change()  # 4-hour future return
            
            labels = []
            for ret in future_returns:
                if pd.isna(ret):
                    labels.append(1)  # HOLD
                elif ret > 0.01:  # 1% increase
                    labels.append(2)  # BUY
                elif ret < -0.01:  # 1% decrease
                    labels.append(0)  # SELL
                else:
                    labels.append(1)  # HOLD
            
            features_df['target'] = labels
            
            # Remove last rows (no future data)
            features_df = features_df[:-4]
            
            # Remove NaN rows
            features_df = features_df.dropna()
            
            return features_df
            
        except Exception as e:
            logger.error(f"❌ {symbol} eğitim verisi hazırlama hatası: {e}")
            return None
    
    async def _load_saved_models(self) -> None:
        """Kaydedilmiş modelleri yükle"""
        try:
            model_files = list(self.model_dir.glob("*_model.pkl"))
            
            for model_file in model_files:
                try:
                    symbol = model_file.stem.replace('_model', '')
                    scaler_file = self.model_dir / f"{symbol}_scaler.pkl"
                    
                    if scaler_file.exists():
                        model = joblib.load(model_file)
                        scaler = joblib.load(scaler_file)
                        
                        self.models[symbol] = model
                        self.scalers[symbol] = scaler
                        
                        logger.debug(f"✅ {symbol} modeli yüklendi")
                    
                except Exception as e:
                    logger.warning(f"⚠️ {model_file} yüklenemedi: {e}")
            
            logger.info(f"📂 {len(self.models)} model yüklendi")
            
        except Exception as e:
            logger.error(f"❌ Model yükleme hatası: {e}")
    
    def _should_retrain(self) -> bool:
        """Yeniden eğitim gerekli mi kontrol et"""
        if not self.last_retrain:
            return True
        
        hours_since_retrain = (datetime.now() - self.last_retrain).total_seconds() / 3600
        return hours_since_retrain >= self.retrain_frequency
    
    def get_model_info(self, symbol: str) -> Dict[str, Any]:
        """Model bilgilerini döndür"""
        try:
            if symbol not in self.models:
                return {'trained': False, 'last_retrain': None}
            
            return {
                'trained': True,
                'last_retrain': self.last_retrain.isoformat() if self.last_retrain else None,
                'features_count': len(self.feature_columns),
                'model_type': type(self.models[symbol]).__name__
            }
            
        except Exception as e:
            logger.error(f"❌ Model bilgi hatası: {e}")
            return {'trained': False, 'error': str(e)}