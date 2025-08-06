#!/usr/bin/env python3
"""
Live Data Engine
Canlı veri analizi ve karar verme motoru
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
import time


class LiveDataEngine:
    """Canlı veri analiz motoru"""
    
    def __init__(self, exchange_manager, market_analyzer, ai_signal_filter, 
                 strategy_engine, position_manager, risk_manager):
        self.exchange_manager = exchange_manager
        self.market_analyzer = market_analyzer
        self.ai_signal_filter = ai_signal_filter
        self.strategy_engine = strategy_engine
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        
        # Live data cache
        self.live_data_cache = {}
        self.analysis_cache = {}
        self.last_analysis_time = {}
        
        # Configuration
        self.analysis_interval = 60  # 60 seconds
        self.data_retention_hours = 24  # 24 hours
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        
        # Decision tracking
        self.recent_decisions = {}
        self.decision_cooldown = 300  # 5 minutes between decisions per symbol
        
        # Performance tracking
        self.analysis_count = 0
        self.decision_count = 0
        self.start_time = datetime.now()
        
        logger.info("🔥 Live Data Engine initialized")
    
    async def start_live_analysis(self):
        """Canlı analiz sistemini başlat"""
        try:
            logger.info("🚀 Canlı veri analiz sistemi başlatılıyor...")
            
            # Start data collection tasks
            tasks = []
            
            # Real-time data collection for each symbol
            for symbol in self.symbols:
                tasks.append(asyncio.create_task(self._live_data_collector(symbol)))
            
            # Analysis engine
            tasks.append(asyncio.create_task(self._analysis_engine()))
            
            # Decision engine  
            tasks.append(asyncio.create_task(self._decision_engine()))
            
            # Monitoring and cleanup
            tasks.append(asyncio.create_task(self._monitoring_engine()))
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"❌ Live analysis başlatma hatası: {e}")
    
    async def _live_data_collector(self, symbol: str):
        """Sembol için canlı veri toplama"""
        try:
            logger.info(f"📡 {symbol} canlı veri toplama başlatıldı")
            
            while True:
                try:
                    # Get real-time market data
                    market_data = await self.exchange_manager.get_real_time_data(symbol)
                    
                    if market_data:
                        logger.debug(f"✅ {symbol} real-time data OK: ${market_data.get('price', 'N/A')}")
                        # Get historical data for analysis (last 200 periods)
                        historical_data = await self.exchange_manager.get_market_data(
                            symbol, timeframe='1m', limit=200
                        )
                        
                        logger.debug(f"🕒 {symbol} historical data: {historical_data is not None}, dataframe: {historical_data.get('dataframe') is not None if historical_data else False}")
                        
                        if historical_data and historical_data.get('dataframe') is not None:
                            # Combine real-time with historical
                            combined_data = {
                                'symbol': symbol,
                                'current_price': market_data['price'],
                                'bid': market_data.get('bid'),
                                'ask': market_data.get('ask'),
                                'spread_pct': self._calculate_spread_pct(market_data),
                                'volume_24h': market_data.get('volume', 0),
                                'change_24h': market_data.get('change_24h'),
                                'change_pct_24h': market_data.get('change_pct_24h'),
                                'orderbook': market_data.get('orderbook'),
                                'recent_trades': market_data.get('recent_trades'),
                                'dataframe': historical_data.get('dataframe'),
                                'timestamp': datetime.now(),
                                'exchange': market_data.get('exchange', 'binance')
                            }
                            
                            # Cache the data
                            self.live_data_cache[symbol] = combined_data
                            
                            # Log every 10th update to avoid spam
                            if self.analysis_count % 10 == 0:
                                logger.debug(f"📊 {symbol}: ${market_data['price']:.4f} "
                                           f"(24h: {market_data.get('change_pct_24h', 0):+.2f}%)")
                        else:
                            logger.warning(f"⚠️ {symbol} için historical data bulunamadı veya dataframe eksik")
                            # Fallback: cache real-time data without historical
                            fallback_data = {
                                'symbol': symbol,
                                'current_price': market_data['price'],
                                'bid': market_data.get('bid'),
                                'ask': market_data.get('ask'),
                                'spread_pct': self._calculate_spread_pct(market_data),
                                'volume_24h': market_data.get('volume', 0),
                                'change_24h': market_data.get('change_24h'),
                                'change_pct_24h': market_data.get('change_pct_24h'),
                                'orderbook': market_data.get('orderbook'),
                                'recent_trades': market_data.get('recent_trades'),
                                'dataframe': None,  # No historical data available
                                'timestamp': datetime.now(),
                                'exchange': market_data.get('exchange', 'bybit')
                            }
                            self.live_data_cache[symbol] = fallback_data
                            logger.debug(f"💾 {symbol} fallback data cached (no historical)")
                    else:
                        logger.warning(f"⚠️ {symbol} için real-time data bulunamadı")
                    
                    # Wait before next update (every 10 seconds)
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} veri toplama hatası: {e}")
                    await asyncio.sleep(5)  # Short wait on error
                    
        except Exception as e:
            logger.error(f"❌ {symbol} veri toplama fatal hatası: {e}")
    
    async def _analysis_engine(self):
        """Analiz motoru - verileri analiz eder"""
        try:
            logger.info("🧠 Analiz motoru başlatıldı")
            
            while True:
                try:
                    for symbol in self.symbols:
                        # Check if we have fresh data
                        if symbol not in self.live_data_cache:
                            continue
                        
                        # Check if analysis is needed (based on interval)
                        last_analysis = self.last_analysis_time.get(symbol, datetime.min)
                        if (datetime.now() - last_analysis).seconds < self.analysis_interval:
                            continue
                        
                        live_data = self.live_data_cache.get(symbol)
                        
                        if live_data is None:
                            logger.warning(f"⚠️ {symbol} için cache'de live data bulunamadı")
                            continue
                        
                        # Perform comprehensive analysis
                        analysis_result = await self._perform_live_analysis(symbol, live_data)
                        
                        if analysis_result:
                            self.analysis_cache[symbol] = analysis_result
                            self.last_analysis_time[symbol] = datetime.now()
                            self.analysis_count += 1
                            
                            logger.info(f"📈 {symbol} analiz tamamlandı - "
                                      f"Market: {analysis_result['market_condition']['regime']}, "
                                      f"AI Confidence: {analysis_result['ai_signals']['confidence']:.2f}, "
                                      f"Strategy: {analysis_result['recommended_strategy']}")
                    
                    # Wait before next analysis cycle
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Analiz motoru hatası: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"❌ Analiz motoru fatal hatası: {e}")
    
    async def _decision_engine(self):
        """Karar verme motoru"""
        try:
            logger.info("🎯 Karar verme motoru başlatıldı")
            
            while True:
                try:
                    for symbol in self.symbols:
                        # Check if we have analysis data
                        if symbol not in self.analysis_cache:
                            continue
                        
                        # Check decision cooldown
                        last_decision = self.recent_decisions.get(symbol, datetime.min)
                        if (datetime.now() - last_decision).seconds < self.decision_cooldown:
                            continue
                        
                        analysis = self.analysis_cache[symbol]
                        
                        # Make trading decision
                        decision = await self._make_trading_decision(symbol, analysis)
                        
                        if decision and decision['action'] != 'HOLD':
                            await self._execute_trading_decision(symbol, decision)
                            self.recent_decisions[symbol] = datetime.now()
                            self.decision_count += 1
                    
                    # Wait before next decision cycle
                    await asyncio.sleep(60)
                    
                except Exception as e:
                    logger.error(f"❌ Karar verme motoru hatası: {e}")
                    await asyncio.sleep(30)
                    
        except Exception as e:
            logger.error(f"❌ Karar verme motoru fatal hatası: {e}")
    
    async def _perform_live_analysis(self, symbol: str, live_data: Dict) -> Optional[Dict]:
        """Tek sembol için canlı analiz gerçekleştir"""
        try:
            # Check if live_data is None or empty
            if live_data is None or not live_data:
                logger.warning(f"⚠️ {symbol} için live data bulunamadı")
                return None
                
            dataframe = live_data.get('dataframe')
            if dataframe is None or len(dataframe) < 50:
                logger.warning(f"⚠️ {symbol} için yeterli dataframe yok ({len(dataframe) if dataframe is not None else 0} candles)")
                return None
            
            # Prepare market data for analysis
            market_data = {
                'symbol': symbol,
                'dataframe': dataframe,
                'close': live_data.get('current_price', 0) if live_data else 0,
                'volume': live_data.get('volume_24h', 0) if live_data else 0,
                'timestamp': live_data.get('timestamp', datetime.now()) if live_data else datetime.now()
            }
            
            # 1. Market Condition Analysis
            market_condition = await self.market_analyzer.analyze_market_condition(symbol)
            if market_condition is None:
                market_condition = {'condition': 'unknown', 'strength': 0.5, 'confidence': 0.0}
                logger.warning(f"⚠️ {symbol} market condition None döndü, default değerler kullanılıyor")
            
            # 2. AI Signal Analysis
            ai_signals = await self.ai_signal_filter.analyze_signals(symbol, market_data)
            if ai_signals is None:
                ai_signals = {'confidence': 0.0, 'signals': [], 'strength': 0.0}
                logger.warning(f"⚠️ {symbol} AI signals None döndü, default değerler kullanılıyor")
            
            # 3. NEW: Adaptive Market Regime Analysis & Strategy Selection
            market_regime = await self.strategy_engine.analyze_market_regime(symbol)
            recommended_strategy = market_regime.get('best_strategy', 'mean_reversion_adaptive')
            
            # Get actual trading signal from adaptive strategy
            strategy_signal = await self.strategy_engine.get_entry_signal(
                symbol=symbol, 
                market_data={'symbol': symbol, 'price': 0, 'volume': 0, 'timestamp': datetime.now()}, 
                regime=market_regime.get('regime', 'sideways_market') if isinstance(market_regime, dict) else market_regime
            )
            if strategy_signal.get('action') == 'HOLD':
                logger.debug(f"📊 {symbol} no trading signal from adaptive strategy")
            
            # 4. Risk Assessment
            risk_assessment = await self._assess_current_risk(symbol, live_data)
            if risk_assessment is None:
                risk_assessment = {'overall_risk': 'medium', 'risk_score': 0.5}
                logger.warning(f"⚠️ {symbol} risk assessment None döndü, default değerler kullanılıyor")
            
            # 5. Entry Signal from Adaptive Strategy (already calculated above)
            entry_signal = None
            if strategy_signal:
                entry_signal = {
                    'action': strategy_signal.get('action', 'HOLD'),
                    'confidence': strategy_signal.get('confidence', 0.5),
                    'entry_price': strategy_signal.get('entry_price', strategy_signal.get('price', 0)),
                    'stop_loss': strategy_signal.get('stop_loss'),
                    'take_profit': strategy_signal.get('take_profit'),
                    'reason': strategy_signal.get('reason', 'Adaptive strategy signal')
                }
            
            # 6. Technical Analysis Summary
            technical_summary = self._calculate_technical_summary(dataframe) if dataframe is not None else {}
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'current_price': live_data.get('current_price', 0) if live_data else 0,
                'market_condition': market_regime,  # Now contains real regime analysis
                'ai_signals': ai_signals,
                'recommended_strategy': recommended_strategy,
                'strategy_signal': strategy_signal,  # New: actual trading signal from adaptive engine
                'entry_signal': entry_signal,
                'risk_assessment': risk_assessment,
                'technical_summary': technical_summary,
                'data_quality': {
                    'data_points': len(dataframe) if dataframe is not None else 0,
                    'spread_pct': live_data.get('spread_pct', 0) if live_data else 0,
                    'orderbook_depth': len((live_data.get('orderbook') or {}).get('bids', [])) if live_data else 0,
                    'recent_trades_count': len(live_data.get('recent_trades') or []) if live_data else 0
                }
            }
            
        except Exception as e:
            import traceback
            logger.error(f"❌ {symbol} canlı analiz hatası: {e}")
            logger.error(f"📍 Stack trace: {traceback.format_exc()}")
            return None
    
    async def _make_trading_decision(self, symbol: str, analysis: Dict) -> Optional[Dict]:
        """Trading kararı ver"""
        try:
            market_condition = analysis['market_condition']
            ai_signals = analysis['ai_signals']
            entry_signal = analysis['entry_signal']
            risk_assessment = analysis['risk_assessment']
            
            # Decision criteria
            min_confidence = 0.75
            min_market_strength = 0.6
            
            # Check if conditions are met for trading
            ai_confidence = ai_signals.get('confidence', 0)
            market_strength = market_condition.get('strength', 0)
            
            if ai_confidence < min_confidence:
                return {'action': 'HOLD', 'reason': f'Low AI confidence: {ai_confidence:.2f}'}
            
            if market_strength < min_market_strength:
                return {'action': 'HOLD', 'reason': f'Weak market: {market_strength:.2f}'}
            
            if not risk_assessment['allowed']:
                return {'action': 'HOLD', 'reason': f'Risk check failed: {risk_assessment["reason"]}'}
            
            # Check for entry signal
            if entry_signal and entry_signal.get('signal') in ['BUY', 'SELL']:
                return {
                    'action': entry_signal['signal'],
                    'entry_price': entry_signal['entry_price'],
                    'stop_loss': entry_signal.get('stop_loss'),
                    'take_profit': entry_signal.get('take_profit'),
                    'confidence': entry_signal['confidence'],
                    'strategy': analysis['recommended_strategy'],
                    'reason': f"Strong {entry_signal['signal']} signal",
                    'risk_amount': risk_assessment['risk_amount'],
                    'position_size': risk_assessment['position_size']
                }
            
            return {'action': 'HOLD', 'reason': 'No clear signal'}
            
        except Exception as e:
            logger.error(f"❌ {symbol} karar verme hatası: {e}")
            return None
    
    async def _execute_trading_decision(self, symbol: str, decision: Dict):
        """Trading kararını uygula"""
        try:
            action = decision['action']
            
            if action in ['BUY', 'SELL']:
                logger.info(f"🚀 {symbol} {action} kararı uygulanıyor...")
                logger.info(f"   💰 Price: ${decision['entry_price']:.4f}")
                logger.info(f"   🎯 Strategy: {decision['strategy']}")
                logger.info(f"   📊 Confidence: {decision['confidence']:.2f}")
                logger.info(f"   💼 Position Size: {decision['position_size']:.6f}")
                
                # Execute through position manager
                position_result = await self.position_manager.open_position(
                    symbol=symbol,
                    action={
                        'signal': action,
                        'entry_price': decision['entry_price'],
                        'stop_loss': decision.get('stop_loss'),
                        'take_profit': decision.get('take_profit'),
                        'size': decision['position_size']
                    },
                    confidence=decision['confidence'],
                    strategy=decision['strategy']
                )
                
                if position_result:
                    logger.info(f"✅ {symbol} pozisyon açıldı: {position_result['id']}")
                else:
                    logger.warning(f"⚠️ {symbol} pozisyon açılamadı")
            
        except Exception as e:
            logger.error(f"❌ {symbol} karar uygulama hatası: {e}")
    
    async def _assess_current_risk(self, symbol: str, live_data: Dict) -> Dict[str, Any]:
        """Mevcut risk durumunu değerlendir"""
        try:
            current_price = live_data['current_price']
            
            # Calculate position size based on risk
            result = await self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=current_price,
                stop_loss=current_price * 0.98,  # 2% stop loss
                confidence=0.8,
                strategy='swing_trading'
            )
            
            return {
                'allowed': result.get('allowed', False),
                'reason': result.get('reason', ''),
                'position_size': result.get('size', 0),
                'risk_amount': result.get('risk_amount', 0),
                'leverage': result.get('leverage', 1)
            }
            
        except Exception as e:
            logger.error(f"❌ {symbol} risk değerlendirme hatası: {e}")
            return {'allowed': False, 'reason': f'Risk assessment error: {e}'}
    
    def _calculate_technical_summary(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Teknik analiz özeti"""
        try:
            if dataframe is None or len(dataframe) < 20:
                return {}
            
            close_prices = dataframe['close']
            
            # Simple moving averages
            sma_10 = close_prices.rolling(10).mean().iloc[-1]
            sma_20 = close_prices.rolling(20).mean().iloc[-1]
            
            # Current price
            current_price = close_prices.iloc[-1]
            
            # Price position relative to SMAs
            above_sma10 = current_price > sma_10
            above_sma20 = current_price > sma_20
            
            # Simple RSI calculation
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # Volume trend (last 10 periods)
            volume_trend = dataframe['volume'].rolling(10).mean().iloc[-1]
            
            return {
                'sma_10': sma_10,
                'sma_20': sma_20,
                'above_sma10': above_sma10,
                'above_sma20': above_sma20,
                'rsi': current_rsi,
                'rsi_oversold': current_rsi < 30,
                'rsi_overbought': current_rsi > 70,
                'volume_trend': volume_trend,
                'trend_direction': 'BULLISH' if above_sma10 and above_sma20 else 'BEARISH',
                'momentum': 'STRONG' if abs(current_rsi - 50) > 20 else 'WEAK'
            }
            
        except Exception as e:
            logger.error(f"❌ Teknik analiz özeti hatası: {e}")
            return {}
    
    async def _monitoring_engine(self):
        """Monitoring ve temizlik motoru"""
        try:
            logger.info("📊 Monitoring motoru başlatıldı")
            
            while True:
                try:
                    # Performance statistics
                    runtime = datetime.now() - self.start_time
                    runtime_hours = runtime.total_seconds() / 3600
                    
                    if self.analysis_count > 0:
                        analyses_per_hour = self.analysis_count / runtime_hours if runtime_hours > 0 else 0
                        decisions_per_hour = self.decision_count / runtime_hours if runtime_hours > 0 else 0
                        
                        logger.info(f"📊 Live Engine Stats:")
                        logger.info(f"   ⏱️ Runtime: {runtime_hours:.1f} hours")
                        logger.info(f"   📈 Analyses: {self.analysis_count} ({analyses_per_hour:.1f}/hour)")
                        logger.info(f"   🎯 Decisions: {self.decision_count} ({decisions_per_hour:.1f}/hour)")
                        logger.info(f"   💾 Cache Size: {len(self.live_data_cache)} symbols")
                    
                    # Cleanup old data (every hour)
                    await self._cleanup_old_data()
                    
                    # Wait 1 hour before next monitoring cycle
                    await asyncio.sleep(3600)
                    
                except Exception as e:
                    logger.error(f"❌ Monitoring hatası: {e}")
                    await asyncio.sleep(300)
                    
        except Exception as e:
            logger.error(f"❌ Monitoring motoru fatal hatası: {e}")
    
    async def _cleanup_old_data(self):
        """Eski verileri temizle"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.data_retention_hours)
            
            # Clean analysis cache
            for symbol in list(self.analysis_cache.keys()):
                analysis = self.analysis_cache[symbol]
                if analysis.get('timestamp', datetime.min) < cutoff_time:
                    del self.analysis_cache[symbol]
                    logger.debug(f"🗑️ {symbol} eski analiz verisi temizlendi")
            
            # Clean decision history
            for symbol in list(self.recent_decisions.keys()):
                if self.recent_decisions[symbol] < cutoff_time:
                    del self.recent_decisions[symbol]
            
        except Exception as e:
            logger.error(f"❌ Veri temizleme hatası: {e}")
    
    def get_live_status(self) -> Dict[str, Any]:
        """Canlı sistem durumunu al"""
        try:
            runtime = datetime.now() - self.start_time
            
            return {
                'status': 'RUNNING',
                'runtime_seconds': runtime.total_seconds(),
                'symbols_tracked': len(self.symbols),
                'symbols_with_data': len(self.live_data_cache),
                'symbols_analyzed': len(self.analysis_cache),
                'total_analyses': self.analysis_count,
                'total_decisions': self.decision_count,
                'recent_analyses': {
                    symbol: {
                        'timestamp': analysis.get('timestamp'),
                        'market_condition': analysis.get('market_condition', {}).get('condition'),
                        'ai_confidence': analysis.get('ai_signals', {}).get('confidence'),
                        'recommended_strategy': analysis.get('recommended_strategy')
                    }
                    for symbol, analysis in self.analysis_cache.items()
                },
                'cache_status': {
                    'live_data_cache_size': len(self.live_data_cache),
                    'analysis_cache_size': len(self.analysis_cache),
                    'decision_cooldowns': len(self.recent_decisions)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Live status hatası: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def _calculate_spread_pct(self, market_data: Dict) -> float:
        """Spread yüzdesini hesapla"""
        try:
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            if bid > 0 and ask > 0:
                return ((ask - bid) / bid) * 100
            return 0.0
        except:
            return 0.0