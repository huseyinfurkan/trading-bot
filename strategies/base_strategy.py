from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Tuple, Optional

class BaseStrategy(ABC):
    def __init__(self, config, name: str):
        self.config = config
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Piyasa verilerini analiz eder ve sinyal üretir"""
        pass
    
    @abstractmethod
    def should_enter(self, analysis: Dict[str, Any]) -> Tuple[bool, float]:
        """Pozisyona girilip girilmeyeceğini belirler"""
        pass
    
    @abstractmethod
    def should_exit(self, analysis: Dict[str, Any], entry_price: float, current_price: float) -> Tuple[bool, str]:
        """Pozisyondan çıkılıp çıkılmayacağını belirler"""
        pass
    
    @abstractmethod
    def get_stop_loss(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Stop loss seviyesini belirler"""
        pass
    
    @abstractmethod
    def get_take_profit(self, entry_price: float, analysis: Dict[str, Any]) -> float:
        """Take profit seviyesini belirler"""
        pass
    
    def calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Sinyal güvenilirliğini hesaplar"""
        # Base implementation - can be overridden by subclasses
        return analysis.get('confidence', 0.5)
    
    def validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Market verilerinin geçerliliğini kontrol eder"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        if not all(col in market_data.columns for col in required_columns):
            self.logger.error(f"Eksik sütunlar: {required_columns}")
            return False
        
        if len(market_data) < 50:
            self.logger.warning(f"Yetersiz veri: {len(market_data)} satır")
            return False
        
        if market_data.isnull().any().any():
            self.logger.warning("NaN değerler bulundu")
            return False
        
        return True