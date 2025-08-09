import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA

# TA-Lib import
try:
    import talib
    TALIB_AVAILABLE = True
    print("TA-Lib available - using optimized technical indicators")
except ImportError:
    TALIB_AVAILABLE = False
    print("TA-Lib not available. Install with: pip install TA-Lib")
    print("Note: Strategy will use fallback calculations without TA-Lib")

# Advanced optimization libraries
try:
    from skopt import gp_minimize, forest_minimize, gbrt_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    from skopt.plots import plot_convergence, plot_objective
    from skopt.acquisition import gaussian_ei
    OPTIMIZATION_AVAILABLE = True
    print("Advanced optimization libraries available")
except ImportError:
    print("Advanced optimization not available. Install with: pip install scikit-optimize")
    OPTIMIZATION_AVAILABLE = False

# Plotting for optimization analysis
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Plotting not available. Install with: pip install matplotlib seaborn")

class DataFetcher:
    """Binance'dan veri çeken sınıf"""
    
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': '',  # Public API için boş
            'secret': '',  # Public API için boş
            'sandbox': False,
            'enableRateLimit': True,
        })
    
    def fetch_ohlcv(self, symbol='ETH/USDT', timeframe='5m', months=6):
        """
        Belirtilen süre için OHLCV verilerini çeker
        """
        try:
            # Son 6 ay için timestamp hesapla
            since = int((datetime.now() - timedelta(days=30*months)).timestamp() * 1000)
            
            print(f"Fetching {symbol} data for last {months} months...")
            
            all_data = []
            limit = 1000  # Binance limit
            
            while since < int(datetime.now().timestamp() * 1000):
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
                
                if not ohlcv:
                    break
                    
                all_data.extend(ohlcv)
                since = ohlcv[-1][0] + 1  # Son timestamp + 1ms
                
                print(f"Fetched {len(ohlcv)} candles, total: {len(all_data)}")
                
                if len(ohlcv) < limit:
                    break
            
            # DataFrame'e çevir
            df = pd.DataFrame(all_data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Duplicate'ları temizle
            df = df[~df.index.duplicated(keep='first')]
            df = df.sort_index()
            
            print(f"Total data points: {len(df)}")
            print(f"Date range: {df.index[0]} to {df.index[-1]}")
            
            return df
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

class TechnicalIndicators:
    """Teknik indikatörleri hesaplayan sınıf"""
    
    @staticmethod
    def rsi(close, period=14):
        """RSI hesaplar"""
        if TALIB_AVAILABLE:
            # NumPy array'e çevir
            if hasattr(close, 'values'):
                close = close.values
            close = np.array(close, dtype=float)
            return talib.RSI(close, timeperiod=period)
        else:
            # Fallback RSI calculation
            delta = pd.Series(close).diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.values
    
    @staticmethod
    def ema(close, period=20):
        """EMA hesaplar"""
        if TALIB_AVAILABLE:
            # NumPy array'e çevir
            if hasattr(close, 'values'):
                close = close.values
            close = np.array(close, dtype=float)
            return talib.EMA(close, timeperiod=period)
        else:
            # Fallback EMA calculation
            return pd.Series(close).ewm(span=period, adjust=False).mean().values
    
    @staticmethod
    def sma(close, period=20):
        """SMA hesaplar"""
        if TALIB_AVAILABLE:
            # NumPy array'e çevir
            if hasattr(close, 'values'):
                close = close.values
            close = np.array(close, dtype=float)
            return talib.SMA(close, timeperiod=period)
        else:
            # Fallback SMA calculation
            return pd.Series(close).rolling(window=period).mean().values
    
    @staticmethod
    def atr(high, low, close, period=14):
        """Average True Range hesaplar"""
        if TALIB_AVAILABLE:
            # NumPy array'lere çevir
            if hasattr(high, 'values'):
                high = high.values
            if hasattr(low, 'values'):
                low = low.values
            if hasattr(close, 'values'):
                close = close.values
                
            high = np.array(high, dtype=float)
            low = np.array(low, dtype=float)
            close = np.array(close, dtype=float)
            
            return talib.ATR(high, low, close, timeperiod=period)
        else:
            # Fallback ATR calculation
            high_s = pd.Series(high)
            low_s = pd.Series(low)
            close_s = pd.Series(close)
            
            tr1 = high_s - low_s
            tr2 = abs(high_s - close_s.shift())
            tr3 = abs(low_s - close_s.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            return atr.values
    
    @staticmethod
    def macd(close, fast_period=12, slow_period=26, signal_period=9):
        """MACD hesaplar"""
        if TALIB_AVAILABLE:
            # NumPy array'e çevir
            if hasattr(close, 'values'):
                close = close.values
            close = np.array(close, dtype=float)
            macd, macd_signal, macd_hist = talib.MACD(close, 
                                                      fastperiod=fast_period,
                                                      slowperiod=slow_period,
                                                      signalperiod=signal_period)
            return macd, macd_signal, macd_hist
        else:
            # Fallback MACD calculation
            close_s = pd.Series(close)
            ema_fast = close_s.ewm(span=fast_period, adjust=False).mean()
            ema_slow = close_s.ewm(span=slow_period, adjust=False).mean()
            macd = ema_fast - ema_slow
            macd_signal = macd.ewm(span=signal_period, adjust=False).mean()
            macd_hist = macd - macd_signal
            return macd.values, macd_signal.values, macd_hist.values

class RSI_EMA_Strategy(Strategy):
    """RSI + EMA Crossover Stratejisi"""
    
    # RSI parametreleri
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    rsi_neutral_low = 45
    rsi_neutral_high = 55
    
    # EMA parametreleri
    ema_fast = 12
    ema_slow = 26
    ema_signal = 50  # Trend filtresi için uzun EMA
    
    # Ek filtreler
    use_volume_filter = True
    volume_multiplier = 1.5  # Ortalama volume'un kaç katı
    volume_period = 20
    
    # MACD parametreleri (ek sinyal için)
    use_macd_confirmation = True
    macd_fast = 12
    macd_slow = 26
    macd_signal_period = 9
    
    # Risk yönetimi parametreleri
    atr_period = 14
    atr_multiplier = 2.0
    risk_reward_ratio = 2.0
    max_holding_periods = 50
    trailing_stop_atr_multiplier = 3.0
    use_trailing_stop = True
    
    # Entry parametreleri
    wait_for_pullback = True
    confirm_with_candle = True
    
    def init(self):
        """Strategy initialization"""
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume
        
        # RSI hesapla
        self.rsi = self.I(TechnicalIndicators.rsi, close, self.rsi_period)
        
        # EMA'ları hesapla
        self.ema_fast_line = self.I(TechnicalIndicators.ema, close, self.ema_fast)
        self.ema_slow_line = self.I(TechnicalIndicators.ema, close, self.ema_slow)
        self.ema_signal_line = self.I(TechnicalIndicators.ema, close, self.ema_signal)
        
        # MACD hesapla (opsiyonel confirmation için)
        if self.use_macd_confirmation:
            self.macd, self.macd_signal, self.macd_hist = self.I(TechnicalIndicators.macd,
                                                                 close,
                                                                 self.macd_fast,
                                                                 self.macd_slow,
                                                                 self.macd_signal_period)
        
        # Volume SMA hesapla (filter için)
        if self.use_volume_filter:
            self.volume_sma = self.I(TechnicalIndicators.sma, volume, self.volume_period)
        
        # ATR hesapla (risk yönetimi için)
        self.atr = self.I(TechnicalIndicators.atr, high, low, close, self.atr_period)
        
        # Tracking variables
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.trailing_stop = None
        self.holding_periods = 0
        self.highest_price = None
        self.lowest_price = None
        
    def next(self):
        """Her bar için çalışan ana logic"""
        # Minimum veri kontrolü
        min_periods = max(self.rsi_period, self.ema_signal, self.atr_period)
        if len(self.data) < min_periods + 10:
            return
        
        # Mevcut değerler
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_ema_fast = self.ema_fast_line[-1]
        current_ema_slow = self.ema_slow_line[-1]
        current_ema_signal = self.ema_signal_line[-1]
        current_atr = self.atr[-1]
        current_volume = self.data.Volume[-1]
        
        # Önceki değerler (crossover kontrolü için)
        if len(self.data) >= min_periods + 11:
            prev_ema_fast = self.ema_fast_line[-2]
            prev_ema_slow = self.ema_slow_line[-2]
            prev_rsi = self.rsi[-2]
        else:
            return
        
        # NaN kontrolü
        if (np.isnan(current_rsi) or np.isnan(current_ema_fast) or 
            np.isnan(current_ema_slow) or np.isnan(current_atr)):
            return
        
        # Volume filter
        volume_filter = True
        if self.use_volume_filter and not np.isnan(self.volume_sma[-1]):
            volume_filter = current_volume > self.volume_sma[-1] * self.volume_multiplier
        
        # MACD confirmation
        macd_confirmation = True
        if self.use_macd_confirmation and not np.isnan(self.macd_hist[-1]):
            macd_confirmation_long = self.macd_hist[-1] > 0 and self.macd[-1] > self.macd_signal[-1]
            macd_confirmation_short = self.macd_hist[-1] < 0 and self.macd[-1] < self.macd_signal[-1]
        else:
            macd_confirmation_long = True
            macd_confirmation_short = True
        
        # Trend filter (signal EMA kullanarak)
        trend_up = current_price > current_ema_signal
        trend_down = current_price < current_ema_signal
        
        # Mevcut pozisyon yönetimi
        if self.position:
            self.holding_periods += 1
            
            # Trailing stop güncelleme
            if self.use_trailing_stop:
                if self.position.is_long:
                    if self.highest_price is None or current_price > self.highest_price:
                        self.highest_price = current_price
                        self.trailing_stop = self.highest_price - (current_atr * self.trailing_stop_atr_multiplier)
                    
                    # Exit conditions for long
                    exit_long = (
                        current_price <= self.stop_loss or
                        current_price >= self.take_profit or
                        (self.trailing_stop and current_price <= self.trailing_stop) or
                        self.holding_periods > self.max_holding_periods or
                        (current_rsi > self.rsi_overbought and current_ema_fast < current_ema_slow)  # RSI + EMA exit signal
                    )
                    
                    if exit_long:
                        self.position.close()
                        self.reset_position_tracking()
                        return
                        
                elif self.position.is_short:
                    if self.lowest_price is None or current_price < self.lowest_price:
                        self.lowest_price = current_price
                        self.trailing_stop = self.lowest_price + (current_atr * self.trailing_stop_atr_multiplier)
                    
                    # Exit conditions for short
                    exit_short = (
                        current_price >= self.stop_loss or
                        current_price <= self.take_profit or
                        (self.trailing_stop and current_price >= self.trailing_stop) or
                        self.holding_periods > self.max_holding_periods or
                        (current_rsi < self.rsi_oversold and current_ema_fast > current_ema_slow)  # RSI + EMA exit signal
                    )
                    
                    if exit_short:
                        self.position.close()
                        self.reset_position_tracking()
                        return
        
        # Yeni pozisyon sinyalleri
        if not self.position:
            
            # LONG Sinyali
            long_signal = self.check_long_signal(
                current_rsi, prev_rsi,
                current_ema_fast, current_ema_slow,
                prev_ema_fast, prev_ema_slow,
                trend_up, volume_filter,
                macd_confirmation_long,
                current_price
            )
            
            if long_signal:
                self.entry_price = current_price
                self.stop_loss = current_price - (current_atr * self.atr_multiplier)
                self.take_profit = current_price + (current_atr * self.atr_multiplier * self.risk_reward_ratio)
                self.holding_periods = 0
                self.highest_price = current_price
                self.trailing_stop = None
                self.buy()
            
            # SHORT Sinyali
            short_signal = self.check_short_signal(
                current_rsi, prev_rsi,
                current_ema_fast, current_ema_slow,
                prev_ema_fast, prev_ema_slow,
                trend_down, volume_filter,
                macd_confirmation_short,
                current_price
            )
            
            if short_signal:
                self.entry_price = current_price
                self.stop_loss = current_price + (current_atr * self.atr_multiplier)
                self.take_profit = current_price - (current_atr * self.atr_multiplier * self.risk_reward_ratio)
                self.holding_periods = 0
                self.lowest_price = current_price
                self.trailing_stop = None
                self.sell()
    
    def check_long_signal(self, rsi, prev_rsi, ema_fast, ema_slow, 
                         prev_ema_fast, prev_ema_slow, trend_up, 
                         volume_filter, macd_confirmation, price):
        """Long entry sinyali kontrolü"""
        
        # EMA Golden Cross
        ema_crossover = (prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow)
        
        # RSI koşulları
        rsi_condition = (
            (rsi > self.rsi_oversold and rsi < self.rsi_neutral_high) or  # Oversold'dan çıkış veya nötr bölge
            (prev_rsi <= self.rsi_oversold and rsi > self.rsi_oversold)   # Oversold bounce
        )
        
        # Pullback kontrolü
        if self.wait_for_pullback:
            pullback_condition = price <= ema_fast * 1.01  # EMA'ya yakın
        else:
            pullback_condition = True
        
        # Candle confirmation (bullish candle)
        if self.confirm_with_candle and len(self.data) >= 2:
            candle_confirmation = (
                self.data.Close[-1] > self.data.Open[-1] and  # Bullish candle
                self.data.Close[-1] > self.data.High[-2] * 0.98  # Önceki high'a yakın kapanış
            )
        else:
            candle_confirmation = True
        
        # Tüm koşulları kontrol et
        return (
            (ema_crossover or (ema_fast > ema_slow and rsi_condition)) and
            trend_up and
            volume_filter and
            macd_confirmation and
            pullback_condition and
            candle_confirmation
        )
    
    def check_short_signal(self, rsi, prev_rsi, ema_fast, ema_slow,
                          prev_ema_fast, prev_ema_slow, trend_down,
                          volume_filter, macd_confirmation, price):
        """Short entry sinyali kontrolü"""
        
        # EMA Death Cross
        ema_crossover = (prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow)
        
        # RSI koşulları
        rsi_condition = (
            (rsi < self.rsi_overbought and rsi > self.rsi_neutral_low) or  # Overbought'tan çıkış veya nötr bölge
            (prev_rsi >= self.rsi_overbought and rsi < self.rsi_overbought)  # Overbought rejection
        )
        
        # Pullback kontrolü
        if self.wait_for_pullback:
            pullback_condition = price >= ema_fast * 0.99  # EMA'ya yakın
        else:
            pullback_condition = True
        
        # Candle confirmation (bearish candle)
        if self.confirm_with_candle and len(self.data) >= 2:
            candle_confirmation = (
                self.data.Close[-1] < self.data.Open[-1] and  # Bearish candle
                self.data.Close[-1] < self.data.Low[-2] * 1.02  # Önceki low'a yakın kapanış
            )
        else:
            candle_confirmation = True
        
        # Tüm koşulları kontrol et
        return (
            (ema_crossover or (ema_fast < ema_slow and rsi_condition)) and
            trend_down and
            volume_filter and
            macd_confirmation and
            pullback_condition and
            candle_confirmation
        )
    
    def reset_position_tracking(self):
        """Pozisyon tracking değişkenlerini sıfırla"""
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        self.trailing_stop = None
        self.holding_periods = 0
        self.highest_price = None
        self.lowest_price = None

def run_backtest(data, params=None, verbose=True):
    """Backtest çalıştır"""
    strategy_params = {}
    
    if params:
        strategy_params.update({
            # RSI parameters
            'rsi_period': int(params.get('rsi_period', 14)),
            'rsi_oversold': params.get('rsi_oversold', 30),
            'rsi_overbought': params.get('rsi_overbought', 70),
            'rsi_neutral_low': params.get('rsi_neutral_low', 45),
            'rsi_neutral_high': params.get('rsi_neutral_high', 55),
            
            # EMA parameters
            'ema_fast': int(params.get('ema_fast', 12)),
            'ema_slow': int(params.get('ema_slow', 26)),
            'ema_signal': int(params.get('ema_signal', 50)),
            
            # Volume filter
            'use_volume_filter': bool(params.get('use_volume_filter', True)),
            'volume_multiplier': params.get('volume_multiplier', 1.5),
            'volume_period': int(params.get('volume_period', 20)),
            
            # MACD confirmation
            'use_macd_confirmation': bool(params.get('use_macd_confirmation', True)),
            'macd_fast': int(params.get('macd_fast', 12)),
            'macd_slow': int(params.get('macd_slow', 26)),
            'macd_signal_period': int(params.get('macd_signal_period', 9)),
            
            # Risk management
            'atr_period': int(params.get('atr_period', 14)),
            'atr_multiplier': params.get('atr_multiplier', 2.0),
            'risk_reward_ratio': params.get('risk_reward_ratio', 2.0),
            'max_holding_periods': int(params.get('max_holding_periods', 50)),
            'trailing_stop_atr_multiplier': params.get('trailing_stop_atr_multiplier', 3.0),
            'use_trailing_stop': bool(params.get('use_trailing_stop', True)),
            
            # Entry parameters
            'wait_for_pullback': bool(params.get('wait_for_pullback', True)),
            'confirm_with_candle': bool(params.get('confirm_with_candle', True))
        })
    
    bt = Backtest(data, RSI_EMA_Strategy, cash=10000, commission=.002)
    
    try:
        result = bt.run(**strategy_params)
        
        if verbose:
            print_backtest_results(result)
        
        return result, bt
    except Exception as e:
        print(f"Backtest error: {e}")
        return None, None

def print_backtest_results(result):
    """Backtest sonuçlarını yazdır"""
    if result is None:
        return
    
    print(f"\n=== BACKTEST RESULTS ===")
    print(f"Start: {result['Start']}")
    print(f"End: {result['End']}")
    print(f"Duration: {result['Duration']}")
    print(f"Exposure Time: {result['Exposure Time [%]']:.2f}%")
    print(f"Equity Final: ${result['Equity Final [$]']:.2f}")
    print(f"Equity Peak: ${result['Equity Peak [$]']:.2f}")
    print(f"Return: {result['Return [%]']:.2f}%")
    print(f"Buy & Hold Return: {result['Buy & Hold Return [%]']:.2f}%")
    print(f"Return (Ann.): {result['Return (Ann.) [%]']:.2f}%")
    print(f"Volatility (Ann.): {result['Volatility (Ann.) [%]']:.2f}%")
    print(f"Sharpe Ratio: {result['Sharpe Ratio']:.2f}")
    print(f"Sortino Ratio: {result['Sortino Ratio']:.2f}")
    print(f"Calmar Ratio: {result['Calmar Ratio']:.2f}")
    print(f"Max Drawdown: {result['Max. Drawdown [%]']:.2f}%")
    print(f"Avg. Drawdown: {result['Avg. Drawdown [%]']:.2f}%")
    print(f"Max. Drawdown Duration: {result['Max. Drawdown Duration']}")
    print(f"# Trades: {result['# Trades']}")
    print(f"Win Rate: {result['Win Rate [%]']:.2f}%")
    print(f"Best Trade: {result['Best Trade [%]']:.2f}%")
    print(f"Worst Trade: {result['Worst Trade [%]']:.2f}%")
    print(f"Avg. Trade: {result['Avg. Trade [%]']:.2f}%")
    print(f"Max. Trade Duration: {result['Max. Trade Duration']}")
    print(f"Avg. Trade Duration: {result['Avg. Trade Duration']}")
    print(f"Profit Factor: {result['Profit Factor']:.2f}")
    print(f"Expectancy: {result['Expectancy [%]']:.2f}%")
    print(f"SQN: {result['SQN']:.2f}")

def advanced_optimize_parameters(data, n_calls=100, optimizer='gp'):
    """Gelişmiş Bayesian optimizasyon ile parametre optimizasyonu"""
    if not OPTIMIZATION_AVAILABLE:
        print("Advanced optimization not available. Using default parameters.")
        return None, None
    
    print(f"\n=== STARTING ADVANCED PARAMETER OPTIMIZATION ({n_calls} calls) ===")
    
    # Genişletilmiş parametre alanları
    dimensions = [
        # RSI parameters
        Integer(10, 21, name='rsi_period'),
        Real(25.0, 35.0, name='rsi_oversold'),
        Real(65.0, 75.0, name='rsi_overbought'),
        Real(40.0, 48.0, name='rsi_neutral_low'),
        Real(52.0, 60.0, name='rsi_neutral_high'),
        
        # EMA parameters
        Integer(8, 15, name='ema_fast'),
        Integer(20, 30, name='ema_slow'),
        Integer(40, 60, name='ema_signal'),
        
        # Volume filter
        Categorical([True, False], name='use_volume_filter'),
        Real(1.2, 2.0, name='volume_multiplier'),
        Integer(15, 25, name='volume_period'),
        
        # MACD confirmation
        Categorical([True, False], name='use_macd_confirmation'),
        Integer(9, 15, name='macd_fast'),
        Integer(20, 30, name='macd_slow'),
        Integer(7, 11, name='macd_signal_period'),
        
        # Risk management
        Integer(10, 21, name='atr_period'),
        Real(1.5, 3.0, name='atr_multiplier'),
        Real(1.5, 3.0, name='risk_reward_ratio'),
        Integer(30, 100, name='max_holding_periods'),
        Real(2.5, 4.0, name='trailing_stop_atr_multiplier'),
        Categorical([True, False], name='use_trailing_stop'),
        
        # Entry parameters
        Categorical([True, False], name='wait_for_pullback'),
        Categorical([True, False], name='confirm_with_candle')
    ]
    
    # Optimizasyon metrikleri saklamak için
    optimization_results = []
    
    @use_named_args(dimensions)
    def objective(**params):
        try:
            result, _ = run_backtest(data, params, verbose=False)
            
            if result is None:
                return 1000000  # Penalty for failed runs
            
            # Multi-objective optimization
            equity_final = result['Equity Final [$]']
            max_drawdown = result['Max. Drawdown [%]']
            win_rate = result['Win Rate [%]']
            profit_factor = result['Profit Factor']
            num_trades = result['# Trades']
            sharpe_ratio = result['Sharpe Ratio']
            
            # Minimum trade sayısı kontrolü
            if num_trades < 10:
                penalty = 5000
            else:
                penalty = 0
            
            # Composite score hesapla (maximize edilecek)
            if max_drawdown > 0:
                risk_adjusted_return = equity_final / (max_drawdown / 100)
            else:
                risk_adjusted_return = equity_final
            
            # Sharpe ratio bonus
            sharpe_bonus = max(0, sharpe_ratio) * 1000
            
            # Win rate bonus
            win_rate_bonus = max(0, win_rate - 50) * 10
            
            # Profit factor bonus
            pf_bonus = max(0, profit_factor - 1) * 500
            
            # Final score (maximize edilecek değer)
            score = risk_adjusted_return + sharpe_bonus + win_rate_bonus + pf_bonus - penalty
            
            # Optimization results'a ekle
            result_dict = params.copy()
            result_dict.update({
                'equity_final': equity_final,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'num_trades': num_trades,
                'sharpe_ratio': sharpe_ratio,
                'score': score
            })
            optimization_results.append(result_dict)
            
            print(f"Iteration {len(optimization_results)}: Score={score:.2f}, Equity=${equity_final:.2f}, DD={max_drawdown:.2f}%, WR={win_rate:.2f}%")
            
            return -score  # Minimize edilecek (negatif score)
            
        except Exception as e:
            print(f"Error in optimization: {e}")
            return 1000000  # Penalty for failed runs
    
    # Optimizasyon algoritması seç
    optimizers = {
        'gp': gp_minimize,           # Gaussian Process (default)
        'forest': forest_minimize,   # Random Forest
        'gbrt': gbrt_minimize       # Gradient Boosted Trees
    }
    
    optimize_func = optimizers.get(optimizer, gp_minimize)
    
    print(f"Running {optimizer.upper()} optimization with {n_calls} iterations...")
    
    # Optimizasyonu çalıştır
    result = optimize_func(
        objective, 
        dimensions, 
        n_calls=n_calls, 
        random_state=42,
        acq_func='EI',  # Expected Improvement
        n_initial_points=10
    )
    
    # En iyi parametreler
    best_params = {}
    for i, dim in enumerate(dimensions):
        best_params[dim.name] = result.x[i]
    
    print(f"\n=== OPTIMIZATION COMPLETED ===")
    print(f"Best score: {-result.fun:.2f}")
    print(f"Best parameters: {best_params}")
    
    # Top 5 sonuçları göster
    optimization_df = pd.DataFrame(optimization_results)
    top_5 = optimization_df.nlargest(5, 'score')
    
    print(f"\n=== TOP 5 PARAMETER COMBINATIONS ===")
    for idx, row in top_5.iterrows():
        print(f"\nRank {top_5.index.get_loc(idx) + 1}:")
        print(f"  Score: {row['score']:.2f}")
        print(f"  Equity: ${row['equity_final']:.2f}")
        print(f"  Max DD: {row['max_drawdown']:.2f}%")
        print(f"  Win Rate: {row['win_rate']:.2f}%")
        print(f"  Profit Factor: {row['profit_factor']:.2f}")
        print(f"  Trades: {row['num_trades']}")
        print(f"  Sharpe: {row['sharpe_ratio']:.2f}")
    
    return best_params, optimization_df

def analyze_optimization_results(optimization_df):
    """Optimizasyon sonuçlarını analiz et ve görselleştir"""
    if not PLOTTING_AVAILABLE or optimization_df is None:
        return
    
    print("\n=== OPTIMIZATION ANALYSIS ===")
    
    # Korelasyon analizi
    numeric_cols = optimization_df.select_dtypes(include=[np.number]).columns
    correlation_matrix = optimization_df[numeric_cols].corr()
    
    # En önemli parametreleri bul
    score_correlations = correlation_matrix['score'].abs().sort_values(ascending=False)
    print("\nParameter importance (correlation with score):")
    for param, corr in score_correlations.items():
        if param != 'score':
            print(f"  {param}: {corr:.3f}")
    
    # Grafik çiz
    if PLOTTING_AVAILABLE:
        plt.figure(figsize=(15, 10))
        
        # Subplot 1: Score distribution
        plt.subplot(2, 3, 1)
        plt.hist(optimization_df['score'], bins=30, alpha=0.7)
        plt.xlabel('Score')
        plt.ylabel('Frequency')
        plt.title('Score Distribution')
        
        # Subplot 2: Equity vs Drawdown
        plt.subplot(2, 3, 2)
        plt.scatter(optimization_df['max_drawdown'], optimization_df['equity_final'], 
                   c=optimization_df['score'], cmap='viridis', alpha=0.6)
        plt.xlabel('Max Drawdown (%)')
        plt.ylabel('Final Equity ($)')
        plt.title('Risk vs Return')
        plt.colorbar(label='Score')
        
        # Subplot 3: Win Rate vs Profit Factor
        plt.subplot(2, 3, 3)
        plt.scatter(optimization_df['win_rate'], optimization_df['profit_factor'], 
                   c=optimization_df['score'], cmap='viridis', alpha=0.6)
        plt.xlabel('Win Rate (%)')
        plt.ylabel('Profit Factor')
        plt.title('Win Rate vs Profit Factor')
        plt.colorbar(label='Score')
        
        # Subplot 4: Parameter correlation heatmap
        plt.subplot(2, 3, 4)
        important_params = score_correlations.head(8).index.tolist()
        if 'score' in important_params:
            important_params.remove('score')
        if len(important_params) > 7:
            important_params = important_params[:7]
        
        param_corr = optimization_df[important_params].corr()
        sns.heatmap(param_corr, annot=True, cmap='coolwarm', center=0, 
                   square=True, cbar_kws={'shrink': 0.8})
        plt.title('Parameter Correlations')
        
        # Subplot 5: Trade count vs Performance
        plt.subplot(2, 3, 5)
        plt.scatter(optimization_df['num_trades'], optimization_df['score'], alpha=0.6)
        plt.xlabel('Number of Trades')
        plt.ylabel('Score')
        plt.title('Trade Frequency vs Performance')
        
        # Subplot 6: Sharpe Ratio distribution
        plt.subplot(2, 3, 6)
        plt.hist(optimization_df['sharpe_ratio'], bins=30, alpha=0.7)
        plt.xlabel('Sharpe Ratio')
        plt.ylabel('Frequency')
        plt.title('Sharpe Ratio Distribution')
        
        plt.tight_layout()
        plt.show()

def main():
    """Ana fonksiyon"""
    print("=== RSI + EMA CROSSOVER STRATEGY ===")
    
    # Veri çek
    fetcher = DataFetcher()
    data = fetcher.fetch_ohlcv('ETH/USDT', '5m', 6)
    
    if data is None or len(data) < 1000:
        print("Insufficient data. Please check your connection and try again.")
        return
    
    print(f"Data shape: {data.shape}")
    print(f"Data columns: {data.columns.tolist()}")
    
    # 1. Default parametreler ile backtest
    print("\n" + "="*60)
    print("1. RUNNING BACKTEST WITH DEFAULT PARAMETERS")
    print("="*60)
    
    default_result, default_bt = run_backtest(data)
    
    if default_result is None:
        print("Default backtest failed. Check your data and try again.")
        return
    
    # 2. Hızlı optimizasyon (50 iterations)
    print("\n" + "="*60)
    print("2. QUICK PARAMETER OPTIMIZATION (50 iterations)")
    print("="*60)
    
    quick_params, quick_results = advanced_optimize_parameters(data, n_calls=50, optimizer='gp')
    
    if quick_params is None:
        print("Using default parameters for intermediate backtest.")
        quick_params = {
            'rsi_period': 14, 'rsi_oversold': 30, 'rsi_overbought': 70,
            'rsi_neutral_low': 45, 'rsi_neutral_high': 55,
            'ema_fast': 12, 'ema_slow': 26, 'ema_signal': 50,
            'use_volume_filter': True, 'volume_multiplier': 1.5, 'volume_period': 20,
            'use_macd_confirmation': True, 'macd_fast': 12, 'macd_slow': 26, 'macd_signal_period': 9,
            'atr_period': 14, 'atr_multiplier': 2.0, 'risk_reward_ratio': 2.0,
            'max_holding_periods': 50, 'trailing_stop_atr_multiplier': 3.0, 'use_trailing_stop': True,
            'wait_for_pullback': True, 'confirm_with_candle': True
        }
    
    # 3. Hızlı optimizasyon ile backtest
    print("\n" + "="*60)
    print("3. RUNNING BACKTEST WITH QUICK OPTIMIZED PARAMETERS")
    print("="*60)
    
    print(f"Quick Optimized Parameters: {quick_params}")
    quick_result, quick_bt = run_backtest(data, quick_params)
    
    # 4. Detaylı optimizasyon (kullanıcı seçimi)
    detailed_params = quick_params
    detailed_result = quick_result
    
    if OPTIMIZATION_AVAILABLE:
        user_choice = input("\nDo you want to run detailed optimization (150+ iterations)? This may take 10-20 minutes. (y/n): ").lower().strip()
        
        if user_choice in ['y', 'yes']:
            print("\n" + "="*60)
            print("4. DETAILED PARAMETER OPTIMIZATION (150 iterations)")
            print("="*60)
            
            detailed_params, detailed_results = advanced_optimize_parameters(data, n_calls=150, optimizer='gp')
            
            if detailed_params is not None:
                # 5. Detaylı optimizasyon ile backtest
                print("\n" + "="*60)
                print("5. RUNNING BACKTEST WITH DETAILED OPTIMIZED PARAMETERS")
                print("="*60)
                
                print(f"Detailed Optimized Parameters: {detailed_params}")
                detailed_result, detailed_bt = run_backtest(data, detailed_params)
                
                # 6. Optimizasyon analizi
                print("\n" + "="*60)
                print("6. OPTIMIZATION ANALYSIS")
                print("="*60)
                
                analyze_optimization_results(detailed_results)
            else:
                print("Detailed optimization failed. Using quick optimization results.")
        else:
            print("Skipping detailed optimization.")
    
    # 7. Karşılaştırma ve sonuçlar
    print("\n" + "="*70)
    print("7. FINAL COMPARISON AND RECOMMENDATIONS")
    print("="*70)
    
    # Performans karşılaştırması
    results_comparison = {
        'Default': default_result,
        'Quick Optimized': quick_result,
        'Detailed Optimized': detailed_result
    }
    
    print("\n📊 PERFORMANCE COMPARISON:")
    print("-" * 80)
    print(f"{'Strategy':<20} {'Equity':<12} {'Return':<10} {'Win Rate':<10} {'Max DD':<10} {'Sharpe':<8}")
    print("-" * 80)
    
    for name, result in results_comparison.items():
        if result is not None:
            print(f"{name:<20} ${result['Equity Final [$]']:<11.2f} {result['Return [%]']:<9.2f}% "
                  f"{result['Win Rate [%]']:<9.2f}% {result['Max. Drawdown [%]']:<9.2f}% {result['Sharpe Ratio']:<7.2f}")
    
    # En iyi stratejiyi belirle
    best_strategy = 'Default'
    best_score = default_result['Equity Final [$]'] / max(1, default_result['Max. Drawdown [%]'])
    
    for name, result in results_comparison.items():
        if result is not None:
            score = result['Equity Final [$]'] / max(1, result['Max. Drawdown [%]'])
            if score > best_score:
                best_score = score
                best_strategy = name
    
    print(f"\n🏆 BEST PERFORMING STRATEGY: {best_strategy}")
    
    # Strategi analizi ve öneriler
    best_result = results_comparison[best_strategy]
    print(f"\n📈 STRATEGY ANALYSIS:")
    print("-" * 50)
    
    # Performance kategorileri
    metrics = {
        'Return': (best_result['Return [%]'], [(15, '🔥 Excellent'), (8, '✅ Good'), (3, '⚠️ Fair'), (0, '❌ Poor')]),
        'Win Rate': (best_result['Win Rate [%]'], [(65, '🔥 Excellent'), (55, '✅ Good'), (45, '⚠️ Fair'), (0, '❌ Poor')]),
        'Max Drawdown': (best_result['Max. Drawdown [%]'], [(0, '🔥 Excellent'), (10, '✅ Good'), (20, '⚠️ Fair'), (100, '❌ High Risk')]),
        'Sharpe Ratio': (best_result['Sharpe Ratio'], [(1.5, '🔥 Excellent'), (1.0, '✅ Good'), (0.5, '⚠️ Fair'), (-10, '❌ Poor')]),
        'Profit Factor': (best_result['Profit Factor'], [(2.0, '🔥 Excellent'), (1.5, '✅ Good'), (1.2, '⚠️ Fair'), (0, '❌ Poor')])
    }
    
    for metric_name, (value, thresholds) in metrics.items():
        for threshold, label in thresholds:
            if (metric_name == 'Max Drawdown' and value <= threshold) or (metric_name != 'Max Drawdown' and value >= threshold):
                print(f"{metric_name}: {value:.2f} {label}")
                break
    
    # Detaylı öneriler
    print(f"\n💡 RECOMMENDATIONS:")
    print("-" * 50)
    
    recommendations = []
    
    if best_result['Win Rate [%]'] < 50:
        recommendations.append("• Consider tightening entry criteria or adding more filters")
    
    if best_result['Max. Drawdown [%]'] > 20:
        recommendations.append("• Implement stricter risk management (lower ATR multiplier)")
        recommendations.append("• Consider position sizing based on volatility")
    
    if best_result['# Trades'] < 20:
        recommendations.append("• Strategy may be too selective - consider relaxing some filters")
    elif best_result['# Trades'] > 200:
        recommendations.append("• Strategy may be too aggressive - consider tightening filters")
    
    if best_result['Avg. Trade Duration'] != 'NaT':
        recommendations.append(f"• Average trade duration: {best_result['Avg. Trade Duration']}")
    
    if best_result['Sharpe Ratio'] < 1.0:
        recommendations.append("• Consider improving risk-adjusted returns")
    
    if not recommendations:
        recommendations.append("• Strategy shows good performance across all metrics!")
        recommendations.append("• Consider testing on different timeframes and markets")
        recommendations.append("• Implement live testing with small position sizes")
    
    for rec in recommendations:
        print(rec)
    
    # Parametre önerileri
    if best_strategy != 'Default':
        print(f"\n⚙️ RECOMMENDED PARAMETERS:")
        print("-" * 50)
        
        final_params = detailed_params if best_strategy == 'Detailed Optimized' else quick_params
        
        print("RSI Settings:")
        print(f"  Period: {final_params['rsi_period']}")
        print(f"  Oversold: {final_params['rsi_oversold']}")
        print(f"  Overbought: {final_params['rsi_overbought']}")
        print(f"  Neutral Low: {final_params['rsi_neutral_low']}")
        print(f"  Neutral High: {final_params['rsi_neutral_high']}")
        
        print("\nEMA Settings:")
        print(f"  Fast: {final_params['ema_fast']}")
        print(f"  Slow: {final_params['ema_slow']}")
        print(f"  Signal: {final_params['ema_signal']}")
        
        print("\nVolume Filter:")
        print(f"  Enabled: {final_params['use_volume_filter']}")
        print(f"  Multiplier: {final_params['volume_multiplier']}")
        print(f"  Period: {final_params['volume_period']}")
        
        print("\nMACD Confirmation:")
        print(f"  Enabled: {final_params['use_macd_confirmation']}")
        print(f"  Fast: {final_params['macd_fast']}")
        print(f"  Slow: {final_params['macd_slow']}")
        print(f"  Signal Period: {final_params['macd_signal_period']}")
        
        print("\nRisk Management:")
        print(f"  ATR Period: {final_params['atr_period']}")
        print(f"  ATR Multiplier: {final_params['atr_multiplier']}")
        print(f"  Risk/Reward Ratio: {final_params['risk_reward_ratio']}")
        print(f"  Max Holding Periods: {final_params['max_holding_periods']}")
        print(f"  Trailing Stop ATR Multiplier: {final_params['trailing_stop_atr_multiplier']}")
        print(f"  Use Trailing Stop: {final_params['use_trailing_stop']}")
        
        print("\nEntry Settings:")
        print(f"  Wait for Pullback: {final_params['wait_for_pullback']}")
        print(f"  Confirm with Candle: {final_params['confirm_with_candle']}")
    
    # Risk uyarıları
    print(f"\n⚠️ RISK WARNINGS:")
    print("-" * 50)
    print("• Past performance does not guarantee future results")
    print("• Always test strategies on paper trading first")
    print("• Use proper position sizing (1-2% risk per trade)")
    print("• Monitor strategy performance regularly")
    print("• Consider market regime changes")
    
    # Sonuç özeti
    print(f"\n🎯 SUMMARY:")
    print("-" * 50)
    print(f"Strategy: RSI + EMA Crossover with Advanced Filters")
    print(f"Best Configuration: {best_strategy}")
    print(f"Final Equity: ${best_result['Equity Final [$]']:,.2f}")
    print(f"Total Return: {best_result['Return [%]']:.2f}%")
    print(f"Annual Return: {best_result['Return (Ann.) [%]']:.2f}%")
    print(f"Max Drawdown: {best_result['Max. Drawdown [%]']:.2f}%")
    print(f"Win Rate: {best_result['Win Rate [%]']:.2f}%")
    print(f"Total Trades: {best_result['# Trades']}")
    
    return detailed_result if best_strategy == 'Detailed Optimized' else (
           quick_result if best_strategy == 'Quick Optimized' else default_result
    ), detailed_params if best_strategy == 'Detailed Optimized' else (
       quick_params if best_strategy == 'Quick Optimized' else None
    )

if __name__ == "__main__":
    # Gerekli kütüphaneleri kontrol et
    required_packages = ['ccxt', 'backtesting', 'pandas', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {missing_packages}")
        print("Install with: pip install " + " ".join(missing_packages))
        
    print("\nRequired for this strategy:")
    if not TALIB_AVAILABLE:
        print("⚠️ TA-Lib: pip install TA-Lib (optional but recommended)")
    else:
        print("✅ TA-Lib: Available")
        
    if not OPTIMIZATION_AVAILABLE:
        print("⚠️ Advanced Optimization: pip install scikit-optimize (optional)")
    else:
        print("✅ Advanced Optimization: Available")
        
    if not PLOTTING_AVAILABLE:
        print("⚠️ Plotting: pip install matplotlib seaborn (optional)")
    else:
        print("✅ Plotting: Available")
    
    print("\nNote: This strategy works without TA-Lib using fallback calculations")
    main()