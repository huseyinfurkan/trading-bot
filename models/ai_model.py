import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib
import os
from datetime import datetime, timedelta
import logging

class AIModel:
    def __init__(self, config):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.last_training = None
        self.logger = logging.getLogger(__name__)
        
    def prepare_features(self, df):
        """Teknik indikatörleri hesaplar ve özellik vektörü oluşturur"""
        features = pd.DataFrame()
        
        # Price-based features
        features['price_change'] = df['close'].pct_change()
        features['high_low_ratio'] = df['high'] / df['low']
        features['close_open_ratio'] = df['close'] / df['open']
        
        # Volume features
        features['volume_change'] = df['volume'].pct_change()
        features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Technical indicators
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        features['macd'] = exp1 - exp2
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        bb_middle = df['close'].rolling(window=bb_period).mean()
        bb_upper = bb_middle + (df['close'].rolling(window=bb_period).std() * bb_std)
        bb_lower = bb_middle - (df['close'].rolling(window=bb_period).std() * bb_std)
        features['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # Moving Averages
        features['sma_20'] = df['close'].rolling(20).mean()
        features['sma_50'] = df['close'].rolling(50).mean()
        features['ema_12'] = df['close'].ewm(span=12).mean()
        features['ema_26'] = df['close'].ewm(span=26).mean()
        
        # Price relative to moving averages
        features['price_sma20_ratio'] = df['close'] / features['sma_20']
        features['price_sma50_ratio'] = df['close'] / features['sma_50']
        features['sma20_sma50_ratio'] = features['sma_20'] / features['sma_50']
        
        # Volatility
        features['volatility'] = df['close'].rolling(20).std()
        features['atr'] = self.calculate_atr(df, 14)
        
        # Momentum
        features['momentum'] = df['close'] - df['close'].shift(10)
        features['rate_of_change'] = df['close'].pct_change(10)
        
        # Support/Resistance levels
        features['support_level'] = df['low'].rolling(20).min()
        features['resistance_level'] = df['high'].rolling(20).max()
        features['price_support_ratio'] = df['close'] / features['support_level']
        features['price_resistance_ratio'] = df['close'] / features['resistance_level']
        
        # Market structure
        features['higher_high'] = (df['high'] > df['high'].shift(1)).astype(int)
        features['lower_low'] = (df['low'] < df['low'].shift(1)).astype(int)
        
        # Time-based features
        features['hour'] = pd.to_datetime(df.index).hour
        features['day_of_week'] = pd.to_datetime(df.index).dayofweek
        
        # Remove NaN values
        features = features.dropna()
        
        return features
    
    def calculate_atr(self, df, period=14):
        """Average True Range hesaplar"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def create_labels(self, df, lookforward=5):
        """Gelecek fiyat hareketlerine göre etiketler oluşturur"""
        future_returns = df['close'].shift(-lookforward) / df['close'] - 1
        
        # Binary classification: 1 for profitable trade, 0 for loss
        labels = (future_returns > 0.01).astype(int)  # %1 kar eşiği
        
        return labels
    
    def train(self, historical_data):
        """Modeli eğitir"""
        try:
            self.logger.info("AI model eğitimi başlıyor...")
            
            # Features hazırla
            features = self.prepare_features(historical_data)
            
            # Labels oluştur
            labels = self.create_labels(historical_data)
            
            # Align features and labels
            common_index = features.index.intersection(labels.index)
            features = features.loc[common_index]
            labels = labels.loc[common_index]
            
            if len(features) < self.config.AI_MODEL_CONFIG['min_data_points']:
                self.logger.warning(f"Yetersiz veri: {len(features)} < {self.config.AI_MODEL_CONFIG['min_data_points']}")
                return False
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42, stratify=labels
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Model oluştur ve eğit
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # Model performansını değerlendir
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            
            self.logger.info(f"Model performansı - Accuracy: {accuracy:.3f}, Precision: {precision:.3f}, Recall: {recall:.3f}")
            
            # Feature importance
            feature_importance = pd.DataFrame({
                'feature': features.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            self.logger.info("En önemli özellikler:")
            for _, row in feature_importance.head(10).iterrows():
                self.logger.info(f"  {row['feature']}: {row['importance']:.3f}")
            
            self.feature_columns = features.columns.tolist()
            self.last_training = datetime.now()
            
            # Modeli kaydet
            self.save_model()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Model eğitimi hatası: {str(e)}")
            return False
    
    def predict(self, market_data):
        """Piyasa verilerine göre tahmin yapar"""
        try:
            if self.model is None:
                self.logger.warning("Model henüz eğitilmemiş")
                return None, 0.0
            
            # Features hazırla
            features = self.prepare_features(market_data)
            
            if len(features) == 0:
                return None, 0.0
            
            # Son veriyi al
            latest_features = features.iloc[-1:].copy()
            
            # Scale features
            latest_features_scaled = self.scaler.transform(latest_features)
            
            # Tahmin yap
            prediction = self.model.predict(latest_features_scaled)[0]
            confidence = self.model.predict_proba(latest_features_scaled)[0][1]
            
            return prediction, confidence
            
        except Exception as e:
            self.logger.error(f"Tahmin hatası: {str(e)}")
            return None, 0.0
    
    def should_retrain(self):
        """Modelin yeniden eğitilmesi gerekip gerekmediğini kontrol eder"""
        if self.last_training is None:
            return True
        
        hours_since_training = (datetime.now() - self.last_training).total_seconds() / 3600
        return hours_since_training >= self.config.AI_MODEL_CONFIG['retrain_interval']
    
    def save_model(self):
        """Modeli dosyaya kaydeder"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'last_training': self.last_training
            }
            joblib.dump(model_data, 'models/ai_model.pkl')
            self.logger.info("Model başarıyla kaydedildi")
        except Exception as e:
            self.logger.error(f"Model kaydetme hatası: {str(e)}")
    
    def load_model(self):
        """Kaydedilmiş modeli yükler"""
        try:
            if os.path.exists('models/ai_model.pkl'):
                model_data = joblib.load('models/ai_model.pkl')
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.feature_columns = model_data['feature_columns']
                self.last_training = model_data['last_training']
                self.logger.info("Model başarıyla yüklendi")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Model yükleme hatası: {str(e)}")
            return False