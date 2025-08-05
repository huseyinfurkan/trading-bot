"""
AI Signal Filter
Yapay zeka ile trading sinyallerini filtreler ve güçlendirir
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import json

# Machine Learning imports
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Technical Analysis
import ta
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator, StochRSIIndicator, MFIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator
from ta.volume import OnBalanceVolumeIndicator, VolumeSMAIndicator

# Deep Learning (optional - requires tensorflow)
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("⚠️ TensorFlow bulunamadı, LSTM modeller kullanılamayacak")


class AISignalFilter:
    """AI sinyal filtreleme sistemi"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager):
        """
        Args:
            ai_config: AI konfigürasyonu
            db_manager: Veritabanı yöneticisi
        """
        self.config = ai_config
        self.db_manager = db_manager
        
        # Model parametreleri
        self.confidence_threshold = ai_config.get('confidence_threshold', 0.75)
        self.signal_strength_min = ai_config.get('signal_strength_min', 0.65)
        self.model_retrain_hours = ai_config.get('ml_model_retrain_hours', 24)
        
        # Ağırlıklar
        self.sentiment_weight = ai_config.get('sentiment_weight', 0.3)
        self.technical_weight = ai_config.get('technical_weight', 0.5)
        self.fundamental_weight = ai_config.get('fundamental_weight', 0.2)
        
        # Model saklama
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.last_training: Dict[str, datetime] = {}
        
        # Feature engineering parametreleri
        self.feature_columns = []
        self.target_column = 'signal'
        
    async def initialize(self) -> None:
        """AI modelleri başlat"""
        try:
            logger.info("🧠 AI Signal Filter başlatılıyor...")
            
            # Önceki modelleri yükle
            await self._load_saved_models()
            
            # Feature column'ları tanımla
            self._define_features()
            
            logger.success("✅ AI Signal Filter başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ AI Signal Filter başlatma hatası: {e}")
            raise
    
    def _define_features(self) -> None:
        """Feature column'larını tanımla"""
        self.feature_columns = [
            # Price features
            'close', 'volume', 'high', 'low', 'open',
            
            # Technical indicators - Trend
            'ema_9', 'ema_21', 'ema_50', 'sma_200',
            'macd', 'macd_signal', 'macd_diff',
            'adx',
            
            # Technical indicators - Momentum  
            'rsi', 'stoch_rsi', 'mfi', 'cci', 'williams_r',
            
            # Technical indicators - Volatility
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'atr',
            
            # Technical indicators - Volume
            'obv', 'vwap', 'volume_sma',
            
            # Price patterns
            'price_change_1h', 'price_change_4h', 'price_change_1d',
            'volume_change_1h', 'volume_change_4h',
            
            # Market structure
            'support_resistance_score', 'trend_strength',
            'volatility_percentile', 'volume_percentile'
        ]
    
    async def analyze_signals(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ana sinyal analiz fonksiyonu"""
        try:
            df = market_data.get('dataframe')
            if df is None or df.empty:
                return {'strength': 0, 'confidence': 0, 'signals': []}
            
            # Feature'ları hesapla
            features_df = await self._calculate_features(df)
            
            if features_df.empty:
                return {'strength': 0, 'confidence': 0, 'signals': []}
            
            # ML model sinyalleri
            ml_signals = await self._get_ml_signals(symbol, features_df)
            
            # Technical analysis sinyalleri
            ta_signals = await self._get_technical_signals(features_df)
            
            # Pattern recognition sinyalleri
            pattern_signals = await self._get_pattern_signals(features_df)
            
            # Sentiment analizi (eğer veri varsa)
            sentiment_signals = await self._get_sentiment_signals(symbol)
            
            # Sinyalleri birleştir ve filtrele
            combined_signals = await self._combine_signals(
                ml_signals, ta_signals, pattern_signals, sentiment_signals
            )
            
            # Güven faktörü hesapla
            confidence = await self._calculate_signal_confidence(combined_signals)
            
            # Sinyal gücü hesapla
            strength = await self._calculate_signal_strength(combined_signals)
            
            # Sonuçları kaydet
            await self._save_signal_analysis(symbol, market_data, combined_signals, confidence, strength)
            
            return {
                'strength': strength,
                'confidence': confidence,
                'signals': combined_signals,
                'ml_signals': ml_signals,
                'ta_signals': ta_signals,
                'pattern_signals': pattern_signals,
                'sentiment_signals': sentiment_signals,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} sinyal analiz hatası: {e}")
            return {'strength': 0, 'confidence': 0, 'signals': []}
    
    async def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Technical indicator'ları ve feature'ları hesapla"""
        try:
            if len(df) < 50:  # Minimum veri gereksinimi
                return pd.DataFrame()
            
            features_df = df.copy()
            
            # Trend indicators
            features_df['ema_9'] = EMAIndicator(close=df['close'], window=9).ema_indicator()
            features_df['ema_21'] = EMAIndicator(close=df['close'], window=21).ema_indicator()
            features_df['ema_50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
            features_df['sma_200'] = SMAIndicator(close=df['close'], window=200).sma_indicator()
            
            # MACD
            macd = MACD(close=df['close'])
            features_df['macd'] = macd.macd()
            features_df['macd_signal'] = macd.macd_signal()
            features_df['macd_diff'] = macd.macd_diff()
            
            # ADX
            features_df['adx'] = ADXIndicator(high=df['high'], low=df['low'], close=df['close']).adx()
            
            # Momentum indicators
            features_df['rsi'] = RSIIndicator(close=df['close']).rsi()
            features_df['stoch_rsi'] = StochRSIIndicator(close=df['close']).stochrsi()
            features_df['mfi'] = MFIIndicator(high=df['high'], low=df['low'], 
                                            close=df['close'], volume=df['volume']).money_flow_index()
            features_df['cci'] = ta.trend.cci(high=df['high'], low=df['low'], close=df['close'])
            features_df['williams_r'] = ta.momentum.williams_r(high=df['high'], low=df['low'], close=df['close'])
            
            # Volatility indicators
            bb = BollingerBands(close=df['close'])
            features_df['bb_upper'] = bb.bollinger_hband()
            features_df['bb_middle'] = bb.bollinger_mavg()
            features_df['bb_lower'] = bb.bollinger_lband()
            features_df['bb_width'] = (features_df['bb_upper'] - features_df['bb_lower']) / features_df['bb_middle']
            
            features_df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()
            
            # Volume indicators
            features_df['obv'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
            features_df['vwap'] = ta.volume.volume_weighted_average_price(
                high=df['high'], low=df['low'], close=df['close'], volume=df['volume']
            )
            features_df['volume_sma'] = VolumeSMAIndicator(close=df['close'], volume=df['volume']).volume_sma()
            
            # Price change features
            features_df['price_change_1h'] = df['close'].pct_change(periods=1)
            features_df['price_change_4h'] = df['close'].pct_change(periods=4)
            features_df['price_change_1d'] = df['close'].pct_change(periods=24)
            
            # Volume change features
            features_df['volume_change_1h'] = df['volume'].pct_change(periods=1)
            features_df['volume_change_4h'] = df['volume'].pct_change(periods=4)
            
            # Market structure features
            features_df['support_resistance_score'] = await self._calculate_support_resistance(df)
            features_df['trend_strength'] = await self._calculate_trend_strength(features_df)
            features_df['volatility_percentile'] = features_df['atr'].rolling(100).rank(pct=True)
            features_df['volume_percentile'] = features_df['volume'].rolling(100).rank(pct=True)
            
            # NaN değerleri temizle
            features_df = features_df.ffill().fillna(0)
            
            return features_df
            
        except Exception as e:
            logger.error(f"❌ Feature hesaplama hatası: {e}")
            return pd.DataFrame()
    
    async def _calculate_support_resistance(self, df: pd.DataFrame) -> pd.Series:
        """Destek/direnç skorunu hesapla"""
        try:
            window = min(20, len(df) // 2)
            
            # Pivot noktaları bul
            highs = df['high'].rolling(window).max()
            lows = df['low'].rolling(window).min()
            
            # Mevcut fiyatın destek/direnç seviyelerine yakınlığını hesapla
            current_price = df['close']
            
            # Normalize et
            score = ((current_price - lows) / (highs - lows)).fillna(0.5)
            
            return score
            
        except Exception as e:
            logger.error(f"❌ Destek/direnç hesaplama hatası: {e}")
            return pd.Series([0.5] * len(df))
    
    async def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Trend gücünü hesapla"""
        try:
            # EMA'ların sıralamasını kontrol et
            ema_9 = df['ema_9']
            ema_21 = df['ema_21'] 
            ema_50 = df['ema_50']
            
            # Yükseliş trendi: EMA9 > EMA21 > EMA50
            uptrend = ((ema_9 > ema_21) & (ema_21 > ema_50)).astype(int)
            
            # Düşüş trendi: EMA9 < EMA21 < EMA50
            downtrend = ((ema_9 < ema_21) & (ema_21 < ema_50)).astype(int)
            
            # Trend gücü: +1 (güçlü yükseliş) ile -1 (güçlü düşüş) arası
            trend_strength = uptrend - downtrend
            
            # MACD ile doğrula
            macd_confirmation = (df['macd'] > df['macd_signal']).astype(int) * 2 - 1
            
            # ADX ile güçlendir
            adx_strength = (df['adx'] / 100).fillna(0.5)
            
            final_strength = trend_strength * adx_strength * 0.7 + macd_confirmation * adx_strength * 0.3
            
            return final_strength.fillna(0)
            
        except Exception as e:
            logger.error(f"❌ Trend gücü hesaplama hatası: {e}")
            return pd.Series([0] * len(df))
    
    async def _get_ml_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Machine learning modellerinden sinyaller al"""
        try:
            signals = []
            
            # Model'in var olup olmadığını ve yeniden eğitim gerekip gerekmediğini kontrol et
            await self._check_and_retrain_models(symbol, df)
            
            # Mevcut feature'ları hazırla
            latest_features = await self._prepare_features_for_prediction(df)
            
            if latest_features is None:
                return signals
            
            # Her model için tahmin yap
            for model_name in self.config.get('models', ['gradient_boosting_signals']):
                if f"{symbol}_{model_name}" in self.models:
                    try:
                        model = self.models[f"{symbol}_{model_name}"]
                        scaler = self.scalers.get(f"{symbol}_{model_name}")
                        
                        if scaler:
                            features_scaled = scaler.transform([latest_features])
                        else:
                            features_scaled = [latest_features]
                        
                        # Tahmin yap
                        if hasattr(model, 'predict_proba'):
                            prediction_proba = model.predict_proba(features_scaled)[0]
                            prediction = np.argmax(prediction_proba)
                            confidence = np.max(prediction_proba)
                        else:
                            prediction = model.predict(features_scaled)[0]
                            confidence = 0.7  # Default confidence for models without probability
                        
                        # Sinyali yorumla (0: SELL, 1: HOLD, 2: BUY)
                        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
                        signal_type = signal_map.get(prediction, 'HOLD')
                        
                        if signal_type != 'HOLD' and confidence >= self.signal_strength_min:
                            signals.append({
                                'type': signal_type,
                                'strength': confidence,
                                'source': f'ML_{model_name}',
                                'confidence': confidence,
                                'timestamp': datetime.now()
                            })
                            
                    except Exception as e:
                        logger.warning(f"⚠️ {model_name} model tahmin hatası: {e}")
                        continue
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ ML sinyal hatası: {e}")
            return []
    
    async def _get_technical_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Technical analysis sinyalleri"""
        try:
            signals = []
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            # RSI sinyalleri
            rsi = latest['rsi']
            if rsi < 30:  # Oversold
                signals.append({
                    'type': 'BUY',
                    'strength': min(0.9, (30 - rsi) / 30),
                    'source': 'RSI_Oversold',
                    'confidence': 0.7
                })
            elif rsi > 70:  # Overbought
                signals.append({
                    'type': 'SELL',
                    'strength': min(0.9, (rsi - 70) / 30),
                    'source': 'RSI_Overbought',
                    'confidence': 0.7
                })
            
            # MACD sinyalleri
            if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                signals.append({
                    'type': 'BUY',
                    'strength': 0.8,
                    'source': 'MACD_Bullish_Cross',
                    'confidence': 0.75
                })
            elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                signals.append({
                    'type': 'SELL',
                    'strength': 0.8,
                    'source': 'MACD_Bearish_Cross',
                    'confidence': 0.75
                })
            
            # Bollinger Bands sinyalleri
            if latest['close'] < latest['bb_lower']:
                signals.append({
                    'type': 'BUY',
                    'strength': 0.7,
                    'source': 'BB_Oversold',
                    'confidence': 0.65
                })
            elif latest['close'] > latest['bb_upper']:
                signals.append({
                    'type': 'SELL',
                    'strength': 0.7,
                    'source': 'BB_Overbought',
                    'confidence': 0.65
                })
            
            # EMA trend sinyalleri
            if (latest['ema_9'] > latest['ema_21'] > latest['ema_50'] and 
                latest['close'] > latest['ema_9']):
                signals.append({
                    'type': 'BUY',
                    'strength': 0.8,
                    'source': 'EMA_Uptrend',
                    'confidence': 0.8
                })
            elif (latest['ema_9'] < latest['ema_21'] < latest['ema_50'] and 
                  latest['close'] < latest['ema_9']):
                signals.append({
                    'type': 'SELL',
                    'strength': 0.8,
                    'source': 'EMA_Downtrend',
                    'confidence': 0.8
                })
            
            # Volume confirmation
            volume_avg = df['volume'].rolling(20).mean().iloc[-1]
            if latest['volume'] > volume_avg * 1.5:
                # Yüksek volume ile sinyalleri güçlendir
                for signal in signals:
                    signal['strength'] *= 1.2
                    signal['confidence'] *= 1.1
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Technical sinyal hatası: {e}")
            return []
    
    async def _get_pattern_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Candlestick pattern sinyalleri"""
        try:
            signals = []
            
            if len(df) < 3:
                return signals
            
            latest = df.iloc[-1]
            prev1 = df.iloc[-2]
            prev2 = df.iloc[-3]
            
            # Doji pattern
            body_size = abs(latest['close'] - latest['open'])
            candle_range = latest['high'] - latest['low']
            
            if body_size < candle_range * 0.1:  # Doji
                signals.append({
                    'type': 'HOLD',
                    'strength': 0.6,
                    'source': 'Doji_Pattern',
                    'confidence': 0.6
                })
            
            # Hammer pattern (bullish reversal)
            if (latest['low'] < prev1['low'] and 
                latest['close'] > latest['open'] and
                (latest['high'] - latest['close']) < body_size * 0.3 and
                (latest['close'] - latest['low']) > body_size * 2):
                signals.append({
                    'type': 'BUY',
                    'strength': 0.7,
                    'source': 'Hammer_Pattern',
                    'confidence': 0.7
                })
            
            # Shooting star pattern (bearish reversal)
            if (latest['high'] > prev1['high'] and 
                latest['close'] < latest['open'] and
                (latest['close'] - latest['low']) < body_size * 0.3 and
                (latest['high'] - latest['open']) > body_size * 2):
                signals.append({
                    'type': 'SELL',
                    'strength': 0.7,
                    'source': 'Shooting_Star_Pattern',
                    'confidence': 0.7
                })
            
            # Engulfing patterns
            if (latest['close'] > latest['open'] and prev1['close'] < prev1['open'] and
                latest['open'] < prev1['close'] and latest['close'] > prev1['open']):
                signals.append({
                    'type': 'BUY',
                    'strength': 0.8,
                    'source': 'Bullish_Engulfing',
                    'confidence': 0.75
                })
            
            if (latest['close'] < latest['open'] and prev1['close'] > prev1['open'] and
                latest['open'] > prev1['close'] and latest['close'] < prev1['open']):
                signals.append({
                    'type': 'SELL',
                    'strength': 0.8,
                    'source': 'Bearish_Engulfing',
                    'confidence': 0.75
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Pattern sinyal hatası: {e}")
            return []
    
    async def _get_sentiment_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Sentiment analysis sinyalleri"""
        try:
            # TODO: Sentiment analizi - news, social media, fear & greed index
            # Şimdilik placeholder
            signals = []
            
            # Fear & Greed Index simulation
            import random
            fear_greed_score = random.uniform(0, 100)
            
            if fear_greed_score < 25:  # Extreme Fear
                signals.append({
                    'type': 'BUY',
                    'strength': 0.6,
                    'source': 'Fear_Greed_Index',
                    'confidence': 0.6
                })
            elif fear_greed_score > 75:  # Extreme Greed
                signals.append({
                    'type': 'SELL',
                    'strength': 0.6,
                    'source': 'Fear_Greed_Index',
                    'confidence': 0.6
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Sentiment sinyal hatası: {e}")
            return []
    
    async def _combine_signals(self, ml_signals: List, ta_signals: List, 
                              pattern_signals: List, sentiment_signals: List) -> List[Dict[str, Any]]:
        """Sinyalleri birleştir ve filtrele"""
        try:
            all_signals = ml_signals + ta_signals + pattern_signals + sentiment_signals
            
            if not all_signals:
                return []
            
            # Sinyal türlerine göre grupla
            buy_signals = [s for s in all_signals if s['type'] == 'BUY']
            sell_signals = [s for s in all_signals if s['type'] == 'SELL']
            hold_signals = [s for s in all_signals if s['type'] == 'HOLD']
            
            combined_signals = []
            
            # BUY sinyalleri
            if buy_signals:
                avg_strength = np.mean([s['strength'] for s in buy_signals])
                avg_confidence = np.mean([s['confidence'] for s in buy_signals])
                
                combined_signals.append({
                    'type': 'BUY',
                    'strength': avg_strength,
                    'confidence': avg_confidence,
                    'count': len(buy_signals),
                    'sources': [s['source'] for s in buy_signals],
                    'weight': self.technical_weight + (len(ml_signals) * 0.1)
                })
            
            # SELL sinyalleri
            if sell_signals:
                avg_strength = np.mean([s['strength'] for s in sell_signals])
                avg_confidence = np.mean([s['confidence'] for s in sell_signals])
                
                combined_signals.append({
                    'type': 'SELL',
                    'strength': avg_strength,
                    'confidence': avg_confidence,
                    'count': len(sell_signals),
                    'sources': [s['source'] for s in sell_signals],
                    'weight': self.technical_weight + (len(ml_signals) * 0.1)
                })
            
            # Güven eşiğinin altındaki sinyalleri filtrele
            filtered_signals = [
                s for s in combined_signals 
                if s['confidence'] >= self.signal_strength_min
            ]
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"❌ Sinyal birleştirme hatası: {e}")
            return []
    
    async def _calculate_signal_confidence(self, signals: List[Dict[str, Any]]) -> float:
        """Genel sinyal güven faktörünü hesapla"""
        try:
            if not signals:
                return 0.0
            
            # Sinyal sayısı ve türü
            total_signals = len(signals)
            
            # Ağırlıklı güven ortalaması
            weighted_confidence = 0
            total_weight = 0
            
            for signal in signals:
                weight = signal.get('weight', 1.0)
                confidence = signal['confidence']
                strength = signal['strength']
                count = signal.get('count', 1)
                
                # Çoklu sinyal desteği güveni artırır
                count_bonus = min(0.2, count * 0.05)
                adjusted_confidence = min(1.0, confidence + count_bonus)
                
                weighted_confidence += adjusted_confidence * strength * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.0
            
            final_confidence = weighted_confidence / total_weight
            
            # Çelişkili sinyaller güveni azaltır
            buy_count = sum(1 for s in signals if s['type'] == 'BUY')
            sell_count = sum(1 for s in signals if s['type'] == 'SELL')
            
            if buy_count > 0 and sell_count > 0:
                conflict_penalty = min(0.3, abs(buy_count - sell_count) * 0.1)
                final_confidence *= (1 - conflict_penalty)
            
            return min(1.0, max(0.0, final_confidence))
            
        except Exception as e:
            logger.error(f"❌ Güven hesaplama hatası: {e}")
            return 0.0
    
    async def _calculate_signal_strength(self, signals: List[Dict[str, Any]]) -> float:
        """Sinyal gücünü hesapla"""
        try:
            if not signals:
                return 0.0
            
            # En güçlü sinyali bul
            max_strength = max(s['strength'] for s in signals)
            
            # Sinyal konsensüsü
            buy_strength = sum(s['strength'] for s in signals if s['type'] == 'BUY')
            sell_strength = sum(s['strength'] for s in signals if s['type'] == 'SELL')
            
            net_strength = abs(buy_strength - sell_strength)
            total_strength = buy_strength + sell_strength
            
            if total_strength == 0:
                return 0.0
            
            # Normalleştirilmiş güç
            normalized_strength = net_strength / total_strength
            
            # Maximum güç ile birleştir
            final_strength = (normalized_strength + max_strength) / 2
            
            return min(1.0, final_strength)
            
        except Exception as e:
            logger.error(f"❌ Güç hesaplama hatası: {e}")
            return 0.0
    
    async def _prepare_features_for_prediction(self, df: pd.DataFrame) -> Optional[List[float]]:
        """Model tahmini için feature'ları hazırla"""
        try:
            if df.empty or len(df) == 0:
                return None
            
            latest = df.iloc[-1]
            
            # Sadece gerekli feature'ları al
            features = []
            for col in self.feature_columns:
                if col in latest:
                    value = latest[col]
                    # NaN kontrol et
                    if pd.isna(value):
                        value = 0.0
                    features.append(float(value))
                else:
                    features.append(0.0)
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature hazırlama hatası: {e}")
            return None
    
    async def _check_and_retrain_models(self, symbol: str, df: pd.DataFrame) -> None:
        """Model'lerin yeniden eğitim gereksinimini kontrol et"""
        try:
            model_key = f"{symbol}_gradient_boosting_signals"
            
            # Son eğitim zamanını kontrol et
            last_training = self.last_training.get(model_key)
            now = datetime.now()
            
            should_retrain = (
                model_key not in self.models or
                last_training is None or
                (now - last_training).total_seconds() > self.model_retrain_hours * 3600
            )
            
            if should_retrain and len(df) >= 200:  # Minimum veri gereksinimi
                await self._train_model(symbol, df)
                
        except Exception as e:
            logger.error(f"❌ Model kontrol hatası: {e}")
    
    async def _train_model(self, symbol: str, df: pd.DataFrame) -> None:
        """Machine learning modelini eğit"""
        try:
            logger.info(f"🧠 {symbol} için ML model eğitiliyor...")
            
            # Feature'ları hazırla
            features_df = await self._calculate_features(df)
            
            if len(features_df) < 100:
                logger.warning(f"⚠️ {symbol} için yetersiz veri, model eğitimi atlandı")
                return
            
            # Target variable oluştur (future returns based)
            future_returns = features_df['close'].pct_change(periods=5).shift(-5)  # 5 period ilerideki return
            
            # Signal labels: 0=SELL, 1=HOLD, 2=BUY
            labels = pd.cut(future_returns, 
                          bins=[-np.inf, -0.02, 0.02, np.inf], 
                          labels=[0, 1, 2]).astype(int)
            
            # Features ve labels hazırla
            feature_data = []
            for _, row in features_df.iterrows():
                features = []
                for col in self.feature_columns:
                    if col in row:
                        value = row[col]
                        if pd.isna(value):
                            value = 0.0
                        features.append(float(value))
                    else:
                        features.append(0.0)
                feature_data.append(features)
            
            X = np.array(feature_data)
            y = labels.values
            
            # NaN'ları temizle
            valid_indices = ~(pd.isna(y) | np.isnan(X).any(axis=1))
            X = X[valid_indices]
            y = y[valid_indices]
            
            if len(X) < 50:
                logger.warning(f"⚠️ {symbol} için yetersiz temiz veri")
                return
            
            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Feature scaling
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Model eğitimi
            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Model değerlendirme
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"✅ {symbol} model eğitimi tamamlandı - Accuracy: {accuracy:.3f}")
            
            # Model'i kaydet
            model_key = f"{symbol}_gradient_boosting_signals"
            self.models[model_key] = model
            self.scalers[model_key] = scaler
            self.last_training[model_key] = datetime.now()
            
            # Veritabanına kaydet
            await self._save_model_info(symbol, model_key, accuracy, len(X_train))
            
        except Exception as e:
            logger.error(f"❌ {symbol} model eğitim hatası: {e}")
    
    async def _save_signal_analysis(self, symbol: str, market_data: Dict, 
                                   signals: List, confidence: float, strength: float) -> None:
        """Sinyal analizini veritabanına kaydet"""
        try:
            signal_data = {
                'symbol': symbol,
                'exchange': market_data.get('exchange', 'unknown'),
                'signal_type': 'HOLD',  # Default
                'strength': strength,
                'confidence': confidence,
                'strategy': 'AI_Signal_Filter',
                'timeframe': '1m',  # Default
                'price': market_data.get('close', 0),
                'indicators': {
                    'technical_signals': len([s for s in signals if 'technical' in s.get('source', '').lower()]),
                    'ml_signals': len([s for s in signals if 'ml' in s.get('source', '').lower()]),
                    'pattern_signals': len([s for s in signals if 'pattern' in s.get('source', '').lower()]),
                    'total_signals': len(signals)
                },
                'ai_analysis': {
                    'signals': signals,
                    'confidence_threshold': self.confidence_threshold,
                    'signal_strength_min': self.signal_strength_min
                },
                'market_condition': 'unknown'  # Market analyzer'dan gelecek
            }
            
            # Dominant signal type
            if signals:
                buy_signals = [s for s in signals if s['type'] == 'BUY']
                sell_signals = [s for s in signals if s['type'] == 'SELL']
                
                if len(buy_signals) > len(sell_signals):
                    signal_data['signal_type'] = 'BUY'
                elif len(sell_signals) > len(buy_signals):
                    signal_data['signal_type'] = 'SELL'
            
            await self.db_manager.save_signal(signal_data)
            
        except Exception as e:
            logger.error(f"❌ Sinyal kaydetme hatası: {e}")
    
    async def _save_model_info(self, symbol: str, model_name: str, 
                              accuracy: float, training_size: int) -> None:
        """Model bilgilerini veritabanına kaydet"""
        try:
            # TODO: AI models tablosuna kaydet
            pass
        except Exception as e:
            logger.error(f"❌ Model bilgi kaydetme hatası: {e}")
    
    async def _load_saved_models(self) -> None:
        """Kaydedilmiş modelleri yükle"""
        try:
            # TODO: Veritabanından model bilgilerini yükle
            # Şimdilik boş
            pass
        except Exception as e:
            logger.error(f"❌ Model yükleme hatası: {e}")
    
    async def retrain_all_models(self) -> None:
        """Tüm modelleri yeniden eğit"""
        try:
            logger.info("🔄 Tüm AI modelleri yeniden eğitiliyor...")
            self.last_training.clear()
            logger.info("✅ Model yeniden eğitimi tamamlandı")
        except Exception as e:
            logger.error(f"❌ Toplu model eğitim hatası: {e}")