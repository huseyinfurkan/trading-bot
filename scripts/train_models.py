#!/usr/bin/env python3
"""
AI Model Training Script
ML modellerini eğitir ve kaydeder
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.ai.signal_filter import AISignalFilter
from src.core.database_manager import DatabaseManager


class ModelTrainer:
    """Model eğitim yöneticisi"""
    
    def __init__(self):
        self.symbols = [
            'BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 
            'SOL-USD', 'DOT-USD', 'MATIC-USD', 'LINK-USD'
        ]
        
        self.crypto_mapping = {
            'BTC-USD': 'BTC/USDT',
            'ETH-USD': 'ETH/USDT', 
            'BNB-USD': 'BNB/USDT',
            'ADA-USD': 'ADA/USDT',
            'SOL-USD': 'SOL/USDT',
            'DOT-USD': 'DOT/USDT',
            'MATIC-USD': 'MATIC/USDT',
            'LINK-USD': 'LINK/USDT'
        }
        
        self.model_dir = Path('models')
        self.model_dir.mkdir(exist_ok=True)
        
        self.data_dir = Path('data/training')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def download_training_data(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        """Eğitim verilerini indir"""
        try:
            logger.info(f"📥 {symbol} için eğitim verisi indiriliyor...")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval="1h")
            
            if data.empty:
                logger.warning(f"⚠️ {symbol} için veri bulunamadı")
                return pd.DataFrame()
            
            # Clean and format data
            df = pd.DataFrame({
                'timestamp': data.index,
                'open': data['Open'].values,
                'high': data['High'].values,
                'low': data['Low'].values,
                'close': data['Close'].values,
                'volume': data['Volume'].values
            })
            
            # Remove NaN values
            df = df.dropna()
            
            # Save raw data
            output_file = self.data_dir / f"{symbol.replace('-', '_')}_raw.csv"
            df.to_csv(output_file, index=False)
            
            logger.info(f"✅ {symbol}: {len(df)} kayıt indirildi ve kaydedildi")
            return df
            
        except Exception as e:
            logger.error(f"❌ {symbol} veri indirme hatası: {e}")
            return pd.DataFrame()
    
    async def prepare_features(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Özellikleri hazırla"""
        try:
            logger.info(f"🔧 {symbol} için özellik mühendisliği...")
            
            if len(df) < 200:
                logger.warning(f"⚠️ {symbol} için yetersiz veri")
                return pd.DataFrame()
            
            # Use a subset of features for faster training
            features_df = df.copy()
            
            # Price-based features
            features_df['returns'] = features_df['close'].pct_change()
            features_df['log_returns'] = np.log(features_df['close'] / features_df['close'].shift(1))
            
            # Moving averages
            for window in [5, 10, 20, 50]:
                features_df[f'sma_{window}'] = features_df['close'].rolling(window).mean()
                features_df[f'ema_{window}'] = features_df['close'].ewm(span=window).mean()
            
            # Volatility
            features_df['volatility_10'] = features_df['returns'].rolling(10).std()
            features_df['volatility_20'] = features_df['returns'].rolling(20).std()
            
            # Volume features
            features_df['volume_sma_10'] = features_df['volume'].rolling(10).mean()
            features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma_10']
            
            # Price position features  
            features_df['price_position_20'] = (features_df['close'] - features_df['close'].rolling(20).min()) / (features_df['close'].rolling(20).max() - features_df['close'].rolling(20).min())
            
            # RSI approximation
            delta = features_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features_df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            bb_period = 20
            bb_std = features_df['close'].rolling(bb_period).std()
            features_df['bb_upper'] = features_df[f'sma_{bb_period}'] + (2 * bb_std)
            features_df['bb_lower'] = features_df[f'sma_{bb_period}'] - (2 * bb_std)
            features_df['bb_position'] = (features_df['close'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
            
            # Create labels (future price movement)
            # Predict price movement 4 hours ahead
            future_returns = features_df['close'].shift(-4).pct_change(4)
            
            # Convert to classification labels
            # 0: SELL (< -1%), 1: HOLD (-1% to 1%), 2: BUY (> 1%)
            conditions = [
                future_returns < -0.01,
                (future_returns >= -0.01) & (future_returns <= 0.01),
                future_returns > 0.01
            ]
            choices = [0, 1, 2]
            features_df['target'] = np.select(conditions, choices, default=1)
            
            # Remove NaN values
            features_df = features_df.dropna()
            
            if len(features_df) < 1000:
                logger.warning(f"⚠️ {symbol} için eğitim sonrası yetersiz veri: {len(features_df)}")
                return pd.DataFrame()
            
            # Save processed data
            output_file = self.data_dir / f"{symbol.replace('-', '_')}_features.csv"
            features_df.to_csv(output_file, index=False)
            
            logger.info(f"✅ {symbol}: {len(features_df)} özellik hazırlandı")
            return features_df
            
        except Exception as e:
            logger.error(f"❌ {symbol} özellik hazırlama hatası: {e}")
            return pd.DataFrame()
    
    async def train_symbol_models(self, symbol: str, features_df: pd.DataFrame) -> Dict[str, Any]:
        """Sembol için modelleri eğit"""
        try:
            from sklearn.model_selection import train_test_split, GridSearchCV
            from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import classification_report, accuracy_score, f1_score
            import joblib
            
            logger.info(f"🤖 {symbol} için model eğitimi başlıyor...")
            
            # Feature columns (exclude target and non-numeric)
            exclude_cols = ['timestamp', 'target']
            feature_cols = [col for col in features_df.columns if col not in exclude_cols]
            
            X = features_df[feature_cols]
            y = features_df['target']
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            results = {}
            
            # Train Gradient Boosting
            logger.info(f"📊 {symbol} GradientBoosting eğitiliyor...")
            gb_params = {
                'n_estimators': [50, 100],
                'learning_rate': [0.1, 0.2],
                'max_depth': [4, 6]
            }
            
            gb_model = GradientBoostingClassifier(random_state=42)
            gb_grid = GridSearchCV(gb_model, gb_params, cv=3, scoring='f1_macro', n_jobs=-1)
            gb_grid.fit(X_train_scaled, y_train)
            
            gb_predictions = gb_grid.predict(X_test_scaled)
            gb_accuracy = accuracy_score(y_test, gb_predictions)
            gb_f1 = f1_score(y_test, gb_predictions, average='macro')
            
            results['gradient_boosting'] = {
                'model': gb_grid.best_estimator_,
                'accuracy': gb_accuracy,
                'f1_score': gb_f1,
                'best_params': gb_grid.best_params_
            }
            
            # Train Random Forest
            logger.info(f"🌲 {symbol} RandomForest eğitiliyor...")
            rf_params = {
                'n_estimators': [50, 100],
                'max_depth': [None, 10, 20],
                'min_samples_split': [2, 5]
            }
            
            rf_model = RandomForestClassifier(random_state=42)
            rf_grid = GridSearchCV(rf_model, rf_params, cv=3, scoring='f1_macro', n_jobs=-1)
            rf_grid.fit(X_train, y_train)  # RF doesn't need scaling
            
            rf_predictions = rf_grid.predict(X_test)
            rf_accuracy = accuracy_score(y_test, rf_predictions)
            rf_f1 = f1_score(y_test, rf_predictions, average='macro')
            
            results['random_forest'] = {
                'model': rf_grid.best_estimator_,
                'accuracy': rf_accuracy,
                'f1_score': rf_f1,
                'best_params': rf_grid.best_params_
            }
            
            # Select best model
            best_model_type = 'gradient_boosting' if gb_f1 > rf_f1 else 'random_forest'
            best_model = results[best_model_type]['model']
            best_score = results[best_model_type]['f1_score']
            
            # Save models and scaler
            crypto_symbol = self.crypto_mapping.get(symbol, symbol.replace('-', '/'))
            
            model_file = self.model_dir / f"{crypto_symbol.replace('/', '_')}_model.pkl"
            scaler_file = self.model_dir / f"{crypto_symbol.replace('/', '_')}_scaler.pkl"
            
            joblib.dump(best_model, model_file)
            joblib.dump(scaler, scaler_file)
            
            # Save feature columns
            feature_file = self.model_dir / f"{crypto_symbol.replace('/', '_')}_features.txt"
            with open(feature_file, 'w') as f:
                f.write('\n'.join(feature_cols))
            
            logger.info(f"✅ {symbol}: En iyi model ({best_model_type}) F1={best_score:.3f} kaydedildi")
            
            return {
                'symbol': symbol,
                'crypto_symbol': crypto_symbol,
                'best_model_type': best_model_type,
                'best_f1_score': best_score,
                'gradient_boosting': results['gradient_boosting'],
                'random_forest': results['random_forest'],
                'feature_count': len(feature_cols),
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} model eğitimi hatası: {e}")
            return {'error': str(e)}
    
    async def train_all_models(self) -> Dict[str, Any]:
        """Tüm semboller için modelleri eğit"""
        try:
            logger.info(f"🚀 {len(self.symbols)} sembol için toplu model eğitimi başlıyor...")
            
            results = {}
            summary = {
                'total_symbols': len(self.symbols),
                'successful_trainings': 0,
                'failed_trainings': 0,
                'average_f1_score': 0,
                'best_performing_symbol': None,
                'best_f1_score': 0
            }
            
            for symbol in self.symbols:
                try:
                    logger.info(f"📈 {symbol} işleniyor...")
                    
                    # Download data
                    raw_data = await self.download_training_data(symbol)
                    if raw_data.empty:
                        continue
                    
                    # Prepare features
                    features_data = await self.prepare_features(raw_data, symbol)
                    if features_data.empty:
                        continue
                    
                    # Train models
                    training_result = await self.train_symbol_models(symbol, features_data)
                    if 'error' not in training_result:
                        results[symbol] = training_result
                        summary['successful_trainings'] += 1
                        
                        # Track best performance
                        f1_score = training_result['best_f1_score']
                        if f1_score > summary['best_f1_score']:
                            summary['best_f1_score'] = f1_score
                            summary['best_performing_symbol'] = symbol
                    else:
                        logger.error(f"❌ {symbol} eğitimi başarısız: {training_result['error']}")
                        summary['failed_trainings'] += 1
                    
                    # Small delay between symbols
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} genel hatası: {e}")
                    summary['failed_trainings'] += 1
                    continue
            
            # Calculate average F1 score
            if results:
                f1_scores = [r['best_f1_score'] for r in results.values()]
                summary['average_f1_score'] = sum(f1_scores) / len(f1_scores)
            
            # Save training summary
            summary_file = self.model_dir / 'training_summary.json'
            import json
            with open(summary_file, 'w') as f:
                json.dump({
                    'summary': summary,
                    'results': {k: {**v, 'model': None} for k, v in results.items()},  # Remove model objects for JSON
                    'training_date': datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"🎉 Model eğitimi tamamlandı!")
            logger.info(f"✅ Başarılı: {summary['successful_trainings']}/{summary['total_symbols']}")
            logger.info(f"📊 Ortalama F1 Score: {summary['average_f1_score']:.3f}")
            logger.info(f"🏆 En iyi performans: {summary['best_performing_symbol']} (F1: {summary['best_f1_score']:.3f})")
            
            return {
                'summary': summary,
                'detailed_results': results
            }
            
        except Exception as e:
            logger.error(f"❌ Toplu eğitim hatası: {e}")
            return {'error': str(e)}


async def main():
    """Ana eğitim fonksiyonu"""
    logger.info("🤖 AI Model Training Script")
    logger.info("=" * 50)
    
    trainer = ModelTrainer()
    results = await trainer.train_all_models()
    
    if 'error' not in results:
        summary = results['summary']
        logger.info("\n🎯 EĞİTİM ÖZET:")
        logger.info(f"Toplam Sembol: {summary['total_symbols']}")
        logger.info(f"Başarılı Eğitim: {summary['successful_trainings']}")
        logger.info(f"Başarısız Eğitim: {summary['failed_trainings']}")
        logger.info(f"Ortalama F1 Score: {summary['average_f1_score']:.3f}")
        logger.info(f"En İyi Sembol: {summary['best_performing_symbol']} (F1: {summary['best_f1_score']:.3f})")
        logger.info("\n✅ Modeller 'models/' klasörüne kaydedildi")
        logger.info("🚀 Artık bot'u çalıştırabilirsiniz!")
    else:
        logger.error(f"❌ Eğitim başarısız: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())