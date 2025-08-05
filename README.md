# 🤖 Advanced Multi-Coin Trading Bot

Gelişmiş yapay zeka destekli çok coinli kripto trading botu. Bu bot multi-exchange desteği, AI sinyal filtreleme, dinamik strateji seçimi ve gelişmiş risk yönetimi ile donatılmıştır.

## ✨ Özellikler

### 🧠 Yapay Zeka & Sinyal Filtreleme
- **Machine Learning Modelleri**: Gradient Boosting, Random Forest ve LSTM modelleri
- **Technical Analysis**: 25+ teknik indikatör ve candlestick pattern analizi
- **Sentiment Analysis**: Fear & Greed Index ve piyasa duygusu analizi
- **Dinamik Güven Faktörü**: Çok faktörlü güven hesaplama sistemi

### 📊 Multi-Strateji Trading
- **Scalping**: Yüksek frekanslı kısa vadeli işlemler
- **Swing Trading**: Orta vadeli trend takip stratejisi  
- **Trend Following**: Güçlü trendlerde pozisyon alma
- **Mean Reversion**: Sideways piyasalarda geri dönüş stratejisi

### 🏪 Multi-Exchange Desteği
- **Binance**: Dünya'nın en büyük kripto borsası
- **Bybit**: Türev işlemler için optimize
- **OKX**: Gelişmiş trading araçları
- **Rate Limiting**: Her exchange için otomatik rate limiting

### ⚖️ Gelişmiş Risk Yönetimi
- **Kelly Criterion**: Optimal pozisyon boyutlandırma
- **Correlation Analysis**: Korelasyonlu pozisyon limitleri
- **Dynamic Stop Loss**: Market koşullarına göre adaptif
- **Maximum Drawdown Protection**: Maksimum kayıp koruma

### 🎯 Akıllı Piyasa Analizi
- **Market Condition Detection**: Bull/Bear/Sideways piyasa tespiti
- **Volatility Analysis**: Dinamik volatilite seviye analizi
- **Volume Confirmation**: Hacim tabanlı sinyal doğrulama
- **Time-based Factors**: Zaman bazlı trading optimizasyonu

## 🚀 Kurulum

### Gereksinimler
```bash
Python 3.9+
pip install -r requirements.txt
```

### Konfigürasyon
1. `config.yaml` dosyasını düzenleyin
2. API anahtarlarınızı ekleyin
3. Trading stratejilerinizi seçin
4. Risk parametrelerini ayarlayın

```yaml
# Exchange API Anahtarları
exchanges:
  binance:
    api_key: "YOUR_BINANCE_API_KEY"
    secret: "YOUR_BINANCE_SECRET"
    
# Trading Çiftleri
trading_pairs:
  major_pairs:
    - "BTC/USDT"
    - "ETH/USDT"
    - "BNB/USDT"
    
# AI Ayarları
ai_settings:
  confidence_threshold: 0.75
  signal_strength_min: 0.65
  ml_model_retrain_hours: 24
```

### Çalıştırma
```bash
python main.py
```

## 📈 Stratejiler

### Scalping Stratejisi
- **Timeframe**: 1m, 5m
- **Profit Target**: %0.5
- **Stop Loss**: %0.3
- **Güven Eşiği**: 0.8

```python
scalping:
  enabled: true
  timeframes: ["1m", "5m"]
  max_position_time: 30  # dakika
  profit_target: 0.5  # %
  stop_loss: 0.3  # %
```

### Swing Trading Stratejisi  
- **Timeframe**: 1h, 4h
- **Profit Target**: %3.0
- **Stop Loss**: %1.5
- **Güven Eşiği**: 0.7

### Trend Following Stratejisi
- **Timeframe**: 4h, 1d
- **Profit Target**: %8.0
- **Stop Loss**: %4.0
- **Güven Eşiği**: 0.75

## 🤖 AI Modelleri

### Teknik Analiz Indikatörleri
```python
# Trend Indikatörleri
- EMA (9, 21, 50, 200)
- MACD
- ADX

# Momentum Indikatörleri  
- RSI
- Stochastic RSI
- MFI
- CCI
- Williams %R

# Volatilite Indikatörleri
- Bollinger Bands
- ATR
- Keltner Channels

# Hacim Indikatörleri
- OBV
- VWAP
- Volume SMA
```

### Machine Learning Pipeline
1. **Feature Engineering**: 35+ teknik feature
2. **Model Training**: Otomatik model eğitimi
3. **Prediction**: Real-time tahminler
4. **Performance Tracking**: Model performans takibi

## ⚡ Hızlı Başlangıç

### 1. Test Modunda Çalıştırma
```python
# config.yaml'da sandbox modunu aktifleştirin
exchanges:
  binance:
    sandbox: true
```

### 2. Paper Trading
```python
# Gerçek para riski olmadan test edin
python main.py --paper-trading
```

### 3. Telegram Bildirimleri
```python
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
```

## 📊 Performans İzleme

### Real-time Dashboard
- **P&L Tracking**: Gerçek zamanlı kar/zarar
- **Win Rate**: Başarı oranları
- **Drawdown**: Maksimum düşüş analizi
- **Sharpe Ratio**: Risk-ayarlı getiri

### Database Analytics
```sql
-- Performans sorguları
SELECT * FROM performance WHERE date >= '2024-01-01';
SELECT * FROM trades WHERE pnl > 0;
SELECT COUNT(*) as total_signals FROM signals;
```

## 🔧 Gelişmiş Özellikler

### Custom Strategy Development
```python
# Kendi stratejinizi ekleyin
class CustomStrategy(BaseStrategy):
    async def get_entry_signal(self, market_data):
        # Custom logic
        return signal
        
    async def get_exit_signal(self, position, market_data):
        # Custom exit logic
        return signal
```

### Webhook Integration
```python
# External sinyalleri entegre edin
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    signal = request.json
    await bot.process_external_signal(signal)
```

### Multi-Timeframe Analysis
```python
# Çoklu timeframe analizi
timeframes = ['1m', '5m', '15m', '1h', '4h']
for tf in timeframes:
    analysis = await analyzer.analyze(symbol, tf)
```

## 🛡️ Güvenlik

### API Güvenliği
- **Read-Only Keys**: Mümkün olduğunda sadece okuma izni
- **IP Whitelisting**: Exchange'lerde IP kısıtlaması
- **Environment Variables**: Hassas bilgileri env dosyasında saklayın

### Risk Yönetimi
```python
risk_management:
  max_portfolio_risk: 0.02  # Portfolyonun %2'si
  max_daily_loss: 0.05      # Günlük %5 kayıp limiti
  max_open_positions: 10    # Maksimum açık pozisyon
```

## 📚 Dokümantasyon

### API Referansı
- [Exchange Manager](docs/exchange_manager.md)
- [Strategy Engine](docs/strategy_engine.md)
- [AI Signal Filter](docs/ai_signal_filter.md)
- [Risk Manager](docs/risk_manager.md)

### Tutorials
- [İlk Kurulum](docs/setup.md)
- [Strateji Geliştirme](docs/strategy_development.md)
- [Performans Optimizasyonu](docs/optimization.md)

## 🤝 Katkıda Bulunma

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## ⚠️ Disclaimer

Bu yazılım eğitim amaçlıdır. Kripto para trading'i yüksek risk içerir. Yatırım kararlarınızı verirken kendi araştırmanızı yapın ve sadece kaybetmeyi göze alabileceğiniz miktarlarla işlem yapın.

## 📄 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 📞 İletişim

- **GitHub**: [GitHub Repository](https://github.com/username/advanced-trading-bot)
- **Issues**: [GitHub Issues](https://github.com/username/advanced-trading-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/advanced-trading-bot/discussions)

---

⭐ **Bu projeyi beğendiyseniz star vermeyi unutmayın!** 
