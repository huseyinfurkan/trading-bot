import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import the strategy components
from rsi_ema_strategy import RSI_EMA_Strategy, run_backtest, print_backtest_results

def generate_synthetic_data(days=180, freq='5min', trend=0.0001, volatility=0.002):
    """
    Generate synthetic OHLCV data for testing
    """
    print("Generating synthetic data for testing...")
    
    # Create date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq=freq)
    
    # Generate price data with trend and random walk
    n_points = len(dates)
    returns = np.random.normal(trend, volatility, n_points)
    price = 2000 * np.exp(np.cumsum(returns))
    
    # Add some realistic price patterns
    # Add daily seasonality
    hour_of_day = np.array([d.hour for d in dates])
    daily_pattern = 0.001 * np.sin(2 * np.pi * hour_of_day / 24)
    price = price * (1 + daily_pattern)
    
    # Generate OHLC from price
    df = pd.DataFrame(index=dates)
    df['Close'] = price
    
    # High and Low with some random variation
    daily_range = price * np.random.uniform(0.002, 0.005, n_points)
    df['High'] = price + daily_range * np.random.uniform(0.5, 1, n_points)
    df['Low'] = price - daily_range * np.random.uniform(0.5, 1, n_points)
    
    # Open is previous close with small gap
    df['Open'] = df['Close'].shift(1)
    df['Open'].iloc[0] = df['Close'].iloc[0] * 0.999
    
    # Add some gaps
    gap_indices = np.random.choice(n_points, size=int(n_points * 0.02), replace=False)
    for idx in gap_indices:
        gap = np.random.uniform(-0.005, 0.005)
        df['Open'].iloc[idx] = df['Close'].iloc[idx-1] * (1 + gap)
    
    # Volume with some patterns
    base_volume = 1000000
    df['Volume'] = base_volume * np.random.lognormal(0, 0.5, n_points)
    
    # Add volume spikes at certain times
    volume_spike_indices = np.random.choice(n_points, size=int(n_points * 0.05), replace=False)
    df['Volume'].iloc[volume_spike_indices] *= np.random.uniform(2, 5, len(volume_spike_indices))
    
    # Ensure OHLC relationships are valid
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    print(f"Generated {len(df)} data points")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Price range: ${df['Low'].min():.2f} - ${df['High'].max():.2f}")
    
    return df

def test_strategy():
    """Test the RSI+EMA strategy with synthetic data"""
    print("="*60)
    print("TESTING RSI + EMA CROSSOVER STRATEGY")
    print("="*60)
    
    # Generate synthetic data
    data = generate_synthetic_data(days=180, freq='5min')
    
    if data is None or len(data) < 1000:
        print("Failed to generate sufficient test data")
        return
    
    print(f"\nData shape: {data.shape}")
    print(f"Data columns: {data.columns.tolist()}")
    
    # Test with default parameters
    print("\n" + "="*60)
    print("1. TESTING WITH DEFAULT PARAMETERS")
    print("="*60)
    
    result, bt = run_backtest(data)
    
    if result is None:
        print("Backtest failed")
        return
    
    # Test with custom parameters
    print("\n" + "="*60)
    print("2. TESTING WITH CUSTOM PARAMETERS")
    print("="*60)
    
    custom_params = {
        'rsi_period': 10,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'ema_fast': 10,
        'ema_slow': 21,
        'ema_signal': 55,
        'use_volume_filter': True,
        'volume_multiplier': 1.2,
        'use_macd_confirmation': False,
        'atr_multiplier': 1.5,
        'risk_reward_ratio': 2.5,
        'use_trailing_stop': True
    }
    
    print("Custom parameters:", custom_params)
    result2, bt2 = run_backtest(data, custom_params)
    
    # Compare results
    if result2 is not None:
        print("\n" + "="*60)
        print("3. PERFORMANCE COMPARISON")
        print("="*60)
        print(f"\n{'Metric':<25} {'Default':<15} {'Custom':<15} {'Difference':<15}")
        print("-" * 70)
        
        metrics = [
            ('Return [%]', 'Return [%]'),
            ('Win Rate [%]', 'Win Rate [%]'),
            ('Max. Drawdown [%]', 'Max. Drawdown [%]'),
            ('Sharpe Ratio', 'Sharpe Ratio'),
            ('# Trades', '# Trades')
        ]
        
        for metric_name, metric_key in metrics:
            default_val = result[metric_key]
            custom_val = result2[metric_key]
            
            if isinstance(default_val, (int, float)) and isinstance(custom_val, (int, float)):
                diff = custom_val - default_val
                print(f"{metric_name:<25} {default_val:<15.2f} {custom_val:<15.2f} {diff:<15.2f}")
            else:
                print(f"{metric_name:<25} {str(default_val):<15} {str(custom_val):<15} -")
    
    # Test different market conditions
    print("\n" + "="*60)
    print("4. TESTING DIFFERENT MARKET CONDITIONS")
    print("="*60)
    
    market_conditions = [
        ("Bull Market", 0.0003, 0.0015),
        ("Bear Market", -0.0002, 0.002),
        ("High Volatility", 0.0001, 0.004),
        ("Low Volatility", 0.00005, 0.001)
    ]
    
    for condition_name, trend, volatility in market_conditions:
        print(f"\n{condition_name} (trend={trend}, volatility={volatility}):")
        test_data = generate_synthetic_data(days=90, freq='5min', trend=trend, volatility=volatility)
        
        if test_data is not None:
            result, _ = run_backtest(test_data, verbose=False)
            if result is not None:
                print(f"  Return: {result['Return [%]']:.2f}%")
                print(f"  Win Rate: {result['Win Rate [%]']:.2f}%")
                print(f"  Max DD: {result['Max. Drawdown [%]']:.2f}%")
                print(f"  Trades: {result['# Trades']}")
    
    print("\n" + "="*60)
    print("STRATEGY TESTING COMPLETED")
    print("="*60)
    print("\nNote: This test used synthetic data.")
    print("For real trading, always test with actual market data.")
    print("The strategy includes fallback calculations for all indicators,")
    print("so it works without TA-Lib, though TA-Lib is recommended for performance.")

if __name__ == "__main__":
    test_strategy()