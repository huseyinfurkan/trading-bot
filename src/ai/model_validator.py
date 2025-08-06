"""
ML Model Performance Validation System
Evaluates model quality and provides confidence scores
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
import joblib
from loguru import logger
from datetime import datetime, timedelta


class ModelValidator:
    """Validates ML model performance and provides confidence metrics"""
    
    def __init__(self, models_dir: str = "models/"):
        """Initialize model validator"""
        self.models_dir = models_dir
        self.performance_history = {}
        self.confidence_thresholds = {
            'high': 0.75,      # High confidence threshold
            'medium': 0.60,    # Medium confidence threshold
            'low': 0.45        # Low confidence threshold
        }
        
    def validate_model_performance(self, model, X_test: np.ndarray, y_test: np.ndarray, 
                                 model_name: str = "unknown") -> Dict[str, Any]:
        """Comprehensive model performance validation"""
        try:
            # Get predictions
            y_pred = model.predict(X_test)
            y_proba = None
            
            # Get probabilities if available
            if hasattr(model, 'predict_proba'):
                y_proba = model.predict_proba(X_test)
            elif hasattr(model, 'decision_function'):
                y_proba = model.decision_function(X_test)
            
            # Calculate basic metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
            recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
            
            # Calculate AUC if probabilities available
            auc_score = None
            if y_proba is not None:
                try:
                    if len(np.unique(y_test)) == 2:  # Binary classification
                        if y_proba.ndim > 1:
                            auc_score = roc_auc_score(y_test, y_proba[:, 1])
                        else:
                            auc_score = roc_auc_score(y_test, y_proba)
                    else:  # Multi-class
                        auc_score = roc_auc_score(y_test, y_proba, multi_class='ovr', average='weighted')
                except Exception as e:
                    logger.warning(f"⚠️ AUC calculation failed: {e}")
            
            # Calculate prediction consistency
            pred_consistency = self._calculate_prediction_consistency(y_pred, y_proba)
            
            # Calculate temporal stability (if applicable)
            temporal_stability = self._calculate_temporal_stability(y_pred)
            
            # Overall confidence score
            confidence_score = self._calculate_confidence_score(
                accuracy, precision, recall, f1, auc_score, pred_consistency, temporal_stability
            )
            
            # Confidence level
            confidence_level = self._get_confidence_level(confidence_score)
            
            performance_metrics = {
                'model_name': model_name,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'auc_score': auc_score,
                'prediction_consistency': pred_consistency,
                'temporal_stability': temporal_stability,
                'confidence_score': confidence_score,
                'confidence_level': confidence_level,
                'sample_size': len(y_test),
                'validation_timestamp': datetime.now().isoformat(),
                'recommendations': self._generate_recommendations(confidence_score, accuracy, precision, recall)
            }
            
            # Store performance history
            self.performance_history[model_name] = performance_metrics
            
            # Log results
            logger.info(f"🎓 {model_name} Model Validation:")
            logger.info(f"   📊 Accuracy: {accuracy:.3f}")
            logger.info(f"   🎯 Precision: {precision:.3f}")
            logger.info(f"   🔍 Recall: {recall:.3f}")
            logger.info(f"   📈 F1 Score: {f1:.3f}")
            if auc_score:
                logger.info(f"   🌟 AUC Score: {auc_score:.3f}")
            logger.info(f"   💪 Confidence: {confidence_score:.3f} ({confidence_level})")
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"❌ Model validation error: {e}")
            return self._default_performance_metrics(model_name)
    
    def cross_validate_model(self, model, X: np.ndarray, y: np.ndarray, 
                           cv_folds: int = 5, model_name: str = "unknown") -> Dict[str, Any]:
        """Perform cross-validation for more robust performance assessment"""
        try:
            # Use TimeSeriesSplit for time-based data
            tscv = TimeSeriesSplit(n_splits=cv_folds)
            
            # Perform cross-validation
            cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='accuracy')
            cv_precision = cross_val_score(model, X, y, cv=tscv, scoring='precision_weighted')
            cv_recall = cross_val_score(model, X, y, cv=tscv, scoring='recall_weighted')
            cv_f1 = cross_val_score(model, X, y, cv=tscv, scoring='f1_weighted')
            
            cv_results = {
                'model_name': model_name,
                'cv_accuracy_mean': cv_scores.mean(),
                'cv_accuracy_std': cv_scores.std(),
                'cv_precision_mean': cv_precision.mean(),
                'cv_precision_std': cv_precision.std(),
                'cv_recall_mean': cv_recall.mean(),
                'cv_recall_std': cv_recall.std(),
                'cv_f1_mean': cv_f1.mean(),
                'cv_f1_std': cv_f1.std(),
                'cv_folds': cv_folds,
                'stability_score': 1 - cv_scores.std(),  # Lower std = higher stability
                'validation_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🔄 {model_name} Cross-Validation Results:")
            logger.info(f"   📊 CV Accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
            logger.info(f"   🎯 CV Precision: {cv_precision.mean():.3f} ± {cv_precision.std():.3f}")
            logger.info(f"   🔍 CV Recall: {cv_recall.mean():.3f} ± {cv_recall.std():.3f}")
            logger.info(f"   📈 CV F1: {cv_f1.mean():.3f} ± {cv_f1.std():.3f}")
            logger.info(f"   🏗️ Stability: {cv_results['stability_score']:.3f}")
            
            return cv_results
            
        except Exception as e:
            logger.error(f"❌ Cross-validation error: {e}")
            return {'model_name': model_name, 'error': str(e)}
    
    def _calculate_prediction_consistency(self, y_pred: np.ndarray, y_proba: np.ndarray = None) -> float:
        """Calculate how consistent the model's predictions are"""
        try:
            if y_proba is None:
                return 0.5  # Default consistency
            
            if y_proba.ndim == 1:
                # For binary with single probability
                confidence_values = np.abs(y_proba - 0.5) * 2  # Convert to 0-1 scale
            else:
                # For multi-class, use max probability as confidence
                confidence_values = np.max(y_proba, axis=1)
            
            # Consistency = average confidence in predictions
            consistency = np.mean(confidence_values)
            return min(max(consistency, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception:
            return 0.5
    
    def _calculate_temporal_stability(self, y_pred: np.ndarray, window_size: int = 50) -> float:
        """Calculate temporal stability of predictions"""
        try:
            if len(y_pred) < window_size * 2:
                return 0.5  # Default stability
            
            # Split into windows and calculate prediction distribution stability
            n_windows = len(y_pred) // window_size
            window_distributions = []
            
            for i in range(n_windows):
                start_idx = i * window_size
                end_idx = start_idx + window_size
                window_pred = y_pred[start_idx:end_idx]
                
                # Calculate class distribution in this window
                unique, counts = np.unique(window_pred, return_counts=True)
                distribution = counts / len(window_pred)
                window_distributions.append(distribution)
            
            if len(window_distributions) < 2:
                return 0.5
            
            # Calculate stability as inverse of variance in distributions
            stabilities = []
            for i in range(1, len(window_distributions)):
                # Compare adjacent windows
                prev_dist = window_distributions[i-1]
                curr_dist = window_distributions[i]
                
                # Align distributions to same length
                max_len = max(len(prev_dist), len(curr_dist))
                prev_aligned = np.zeros(max_len)
                curr_aligned = np.zeros(max_len)
                
                prev_aligned[:len(prev_dist)] = prev_dist
                curr_aligned[:len(curr_dist)] = curr_dist
                
                # Calculate similarity (1 - difference)
                similarity = 1 - np.mean(np.abs(prev_aligned - curr_aligned))
                stabilities.append(similarity)
            
            return np.mean(stabilities)
            
        except Exception:
            return 0.5
    
    def _calculate_confidence_score(self, accuracy: float, precision: float, recall: float, 
                                  f1: float, auc: float = None, consistency: float = 0.5, 
                                  temporal_stability: float = 0.5) -> float:
        """Calculate overall confidence score"""
        try:
            # Base score from classification metrics
            base_score = (accuracy * 0.3 + precision * 0.25 + recall * 0.25 + f1 * 0.2)
            
            # Add AUC if available
            if auc is not None:
                base_score = base_score * 0.8 + auc * 0.2
            
            # Add consistency and stability
            final_score = base_score * 0.7 + consistency * 0.15 + temporal_stability * 0.15
            
            return min(max(final_score, 0.0), 1.0)  # Clamp to [0, 1]
            
        except Exception:
            return 0.5
    
    def _get_confidence_level(self, confidence_score: float) -> str:
        """Convert confidence score to categorical level"""
        if confidence_score >= self.confidence_thresholds['high']:
            return 'HIGH'
        elif confidence_score >= self.confidence_thresholds['medium']:
            return 'MEDIUM'
        elif confidence_score >= self.confidence_thresholds['low']:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def _generate_recommendations(self, confidence_score: float, accuracy: float, 
                                precision: float, recall: float) -> List[str]:
        """Generate recommendations based on model performance"""
        recommendations = []
        
        if confidence_score < self.confidence_thresholds['low']:
            recommendations.append("Consider retraining model with more data")
            recommendations.append("Review feature engineering process")
        
        if accuracy < 0.6:
            recommendations.append("Model accuracy is low - consider different algorithms")
        
        if precision < 0.6:
            recommendations.append("High false positive rate - adjust decision threshold")
        
        if recall < 0.6:
            recommendations.append("High false negative rate - consider class balancing")
        
        if abs(precision - recall) > 0.2:
            recommendations.append("Significant precision-recall imbalance detected")
        
        if confidence_score >= self.confidence_thresholds['high']:
            recommendations.append("Model performance is excellent - safe for production use")
        elif confidence_score >= self.confidence_thresholds['medium']:
            recommendations.append("Model performance is acceptable - monitor closely")
        
        return recommendations
    
    def _default_performance_metrics(self, model_name: str) -> Dict[str, Any]:
        """Default metrics when validation fails"""
        return {
            'model_name': model_name,
            'accuracy': 0.5,
            'precision': 0.5,
            'recall': 0.5,
            'f1_score': 0.5,
            'auc_score': None,
            'prediction_consistency': 0.5,
            'temporal_stability': 0.5,
            'confidence_score': 0.3,
            'confidence_level': 'VERY_LOW',
            'sample_size': 0,
            'validation_timestamp': datetime.now().isoformat(),
            'recommendations': ["Model validation failed - retrain model"],
            'error': True
        }
    
    def get_model_confidence(self, model_name: str) -> float:
        """Get current confidence score for a model"""
        if model_name in self.performance_history:
            return self.performance_history[model_name]['confidence_score']
        return 0.3  # Default low confidence
    
    def should_use_model(self, model_name: str, min_confidence: float = 0.5) -> bool:
        """Determine if model should be used based on confidence"""
        confidence = self.get_model_confidence(model_name)
        return confidence >= min_confidence
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all model performances"""
        if not self.performance_history:
            return {"message": "No models validated yet"}
        
        summary = {
            "total_models": len(self.performance_history),
            "models": {}
        }
        
        for model_name, metrics in self.performance_history.items():
            summary["models"][model_name] = {
                "confidence_score": metrics["confidence_score"],
                "confidence_level": metrics["confidence_level"],
                "accuracy": metrics["accuracy"],
                "last_validation": metrics["validation_timestamp"]
            }
        
        return summary