# 🤖 Gelişmiş Multi-Coin Trading Bot

Bu proje, yapay zeka destekli, multi-strateji özellikli gelişmiş bir kripto para trading botudur. Bot, piyasa koşullarına göre otomatik olarak strateji seçimi yapar ve AI sinyal filtreleme ile güvenli trading işlemleri gerçekleştirir.

## 🚀 Özellikler

### 📊 Multi-Coin Desteği
- 10 farklı kripto para çiftinde eş zamanlı trading
- BTC/USDT, ETH/USDT, BNB/USDT, ADA/USDT, SOL/USDT, DOT/USDT, LINK/USDT, MATIC/USDT, AVAX/USDT, UNI/USDT

### 🧠 Yapay Zeka Entegrasyonu
- Gradient Boosting Classifier ile fiyat tahmin modeli
- 20+ teknik indikatör ile özellik mühendisliği
- Otomatik model eğitimi ve güncelleme
- Güven faktörü tabanlı sinyal filtreleme

### 📈 Multi-Strateji Sistemi
- **Scalping Stratejisi**: Kısa vadeli, yüksek frekanslı trading
- **Swing Stratejisi**: Orta-uzun vadeli pozisyon trading
- Piyasa koşullarına göre otomatik strateji seçimi
- Trend, volatilite ve hacim analizi

### 🛡️ Risk Yönetimi
- Günlük kayıp limiti kontrolü
- Dinamik pozisyon büyüklüğü hesaplama
- Stop-loss ve take-profit otomasyonu
- Portfolio risk analizi

### 📱 Web Arayüzü
- Real-time dashboard
- Canlı grafik ve analiz
- Bot durumu ve metrikler
- Kolay kontrol ve izleme

## 🛠️ Kurulum

### 1. Gereksinimler
```bash
# Python 3.8+ gerekli
python --version
```

### 2. Projeyi İndirin
```bash
git clone <repository-url>
cd trading-bot
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Environment Dosyasını Ayarlayın
```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
```

### 5. Binance API Anahtarları
1. [Binance](https://www.binance.com) hesabınıza giriş yapın
2. API Management bölümüne gidin
3. Yeni API anahtarı oluşturun
4. Spot trading izinlerini verin
5. API anahtarlarını `.env` dosyasına ekleyin

## 🚀 Kullanım

### Bot Başlatma
```bash
# Terminal üzerinden bot başlatma
python trading_bot.py
```

### Web Arayüzü
```bash
# Web dashboard başlatma
python web_interface.py
```
Tarayıcınızda `http://localhost:8050` adresine gidin.

## 📊 Konfigürasyon

### Trading Parametreleri (`config.py`)
```python
# Risk Yönetimi
MAX_POSITION_SIZE = 0.1      # Portfolio'nun %10'u
MAX_DAILY_LOSS = 0.05        # Günlük maksimum %5 kayıp
MIN_CONFIDENCE_THRESHOLD = 0.7  # Minimum güven eşiği

# Strateji Parametreleri
STRATEGIES = {
    'scalping': {
        'max_hold_time': 300,  # 5 dakika
        'min_profit': 0.002,   # %0.2
        'max_loss': 0.001      # %0.1
    },
    'swing': {
        'max_hold_time': 604800,  # 7 gün
        'min_profit': 0.05,    # %5
        'max_loss': 0.03       # %3
    }
}
```

## 🧠 AI Model Özellikleri

### Teknik İndikatörler
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Moving Averages (SMA, EMA)
- Stochastic Oscillator
- ATR (Average True Range)
- Volume Analysis
- Support/Resistance Levels

### Özellik Mühendisliği
- Fiyat değişim oranları
- Hacim analizi
- Momentum göstergeleri
- Volatilite hesaplamaları
- Zaman bazlı özellikler

## 📈 Strateji Detayları

### Scalping Stratejisi
- **Zaman Aralığı**: 1-5 dakika
- **Hedef**: Küçük ama sık kar
- **Risk**: Düşük pozisyon büyüklüğü
- **Sinyaller**: EMA crossover, RSI, MACD, Bollinger Bands

### Swing Stratejisi
- **Zaman Aralığı**: Saatler-günler
- **Hedef**: Orta vadeli trend takibi
- **Risk**: Normal pozisyon büyüklüğü
- **Sinyaller**: SMA crossover, ADX, Support/Resistance

## 🛡️ Risk Yönetimi

### Pozisyon Büyüklüğü
- Hesap bakiyesine göre dinamik hesaplama
- Güven faktörü ile ayarlama
- Strateji tipine göre farklılaştırma

### Stop-Loss ve Take-Profit
- ATR tabanlı dinamik seviyeler
- Support/Resistance seviyeleri
- Risk/Ödül oranı kontrolü

### Günlük Limitler
- Maksimum günlük kayıp kontrolü
- Ardışık kayıp sayısı takibi
- Otomatik trading durdurma

## 📱 Web Dashboard

### Özellikler
- Real-time bot durumu
- Aktif pozisyonlar
- Risk metrikleri
- Canlı grafikler
- AI model durumu
- Son analizler

### Kontroller
- Bot başlatma/durdurma
- Manuel yenileme
- Trading çifti seçimi

## 🔧 Geliştirme

### Proje Yapısı
```
trading-bot/
├── config.py                 # Konfigürasyon
├── trading_bot.py           # Ana bot sınıfı
├── web_interface.py         # Web dashboard
├── models/
│   └── ai_model.py         # AI model
├── strategies/
│   ├── base_strategy.py    # Temel strateji
│   ├── scalping_strategy.py # Scalping
│   ├── swing_strategy.py   # Swing
│   └── strategy_manager.py # Strateji yöneticisi
├── exchange/
│   └── binance_client.py   # Binance API
├── risk_management/
│   └── risk_manager.py     # Risk yönetimi
└── requirements.txt        # Bağımlılıklar
```

### Yeni Strateji Ekleme
1. `strategies/base_strategy.py`'den türetin
2. `analyze()`, `should_enter()`, `should_exit()` metodlarını implement edin
3. `strategy_manager.py`'e ekleyin
4. `config.py`'de parametreleri tanımlayın

## ⚠️ Uyarılar

### Risk Uyarısı
- Kripto para trading yüksek risk içerir
- Sadece kaybetmeyi göze alabileceğiniz miktarla işlem yapın
- Bu bot eğitim amaçlıdır, gerçek trading için ek testler gerekir

### API Güvenliği
- API anahtarlarınızı güvende tutun
- Sadece gerekli izinleri verin
- IP kısıtlaması kullanın

## 📊 Performans İzleme

### Metrikler
- Günlük P&L
- Kazanma oranı
- Ortalama kar/zarar
- Maksimum drawdown
- Sharpe ratio

### Loglar
- Tüm işlemler loglanır
- Hata durumları kaydedilir
- Performans analizi için veri toplanır

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 📞 Destek

Sorularınız için:
- GitHub Issues
- Email: [your-email@example.com]

---

**Not**: Bu bot eğitim amaçlıdır. Gerçek trading için kendi sorumluluğunuzda kullanın. 
