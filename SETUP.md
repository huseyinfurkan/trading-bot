# Advanced Multi-Coin Trading Bot - Kurulum Rehberi

## 🚀 Hızlı Başlangıç

Bu gelişmiş kripto trading bot'u, yapay zeka destekli sinyal filtreleme, multi-strateji trading ve risk yönetimi ile donatılmış bir sistemdir.

## ✅ Sistem Gereksinimleri

- **Python**: 3.9 veya daha yeni sürüm
- **RAM**: En az 4GB (8GB önerilir)
- **Disk**: En az 2GB boş alan
- **İnternet**: Sürekli internet bağlantısı

## 📦 Kurulum Adımları

### 1. Repository'yi İndir
```bash
# Git kullanıyorsanız
git clone <repository-url>
cd advanced-trading-bot

# Veya dosyaları manuel olarak indirip klasöre açın
```

### 2. Python Virtual Environment Oluştur (Önerilir)
```bash
# Virtual environment oluştur
python3 -m venv venv

# Aktifleştir (Linux/Mac)
source venv/bin/activate

# Aktifleştir (Windows)
venv\Scripts\activate
```

### 3. Gerekli Paketleri Kur
```bash
# Ana paketleri kur
pip install -r requirements.txt

# TA-Lib için ekstra kurulum (eğer hata alırsanız)
# Linux/Ubuntu:
sudo apt-get install build-essential
pip install TA-Lib

# Mac:
brew install ta-lib
pip install TA-Lib

# Windows:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib adresinden wheel dosyasını indirin
pip install TA_Lib-0.4.xx-cp3x-cp3x-win_amd64.whl
```

### 4. Konfigürasyon Ayarları

#### API Anahtarları Ekle
`config.yaml` dosyasını düzenleyin:

```yaml
exchanges:
  binance:
    api_key: "YOUR_BINANCE_API_KEY"
    secret: "YOUR_BINANCE_SECRET_KEY"
    sandbox: false  # Test için true yapın
    
  bybit:
    api_key: "YOUR_BYBIT_API_KEY"
    secret: "YOUR_BYBIT_SECRET_KEY"
    sandbox: false
```

#### Bildirim Ayarları (Opsiyonel)
```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_TELEGRAM_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
    
  discord:
    enabled: true
    webhook_url: "YOUR_DISCORD_WEBHOOK_URL"
    
  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    from_email: "your-email@gmail.com"
    password: "your-app-password"
    to_email: "notifications@yourdomain.com"
```

### 5. Testleri Çalıştır

#### Temel Yapı Testi (Bağımlılık gerektirmez)
```bash
python3 test_minimal.py
```

#### Kapsamlı Test
```bash
python3 startup.py
```

#### Hızlı Test
```bash
python3 quick_test.py
```

## 🔧 Çalıştırma

### Test Modunda Çalıştırma
```bash
# Test modunda (gerçek emir vermez)
python3 main.py --test-mode

# Veya config.yaml'da sandbox: true yapın
```

### Üretim Modunda Çalıştırma
```bash
# Canlı trading (DİKKAT: Gerçek para kullanır!)
python3 main.py
```

## ⚙️ Konfigürasyon Seçenekleri

### Risk Yönetimi
```yaml
risk_management:
  max_portfolio_risk: 0.02        # Toplam portföy riski (%2)
  max_daily_loss: 0.05           # Günlük maksimum kayıp (%5)
  max_open_positions: 10         # Maksimum açık pozisyon sayısı
  position_sizing_method: "kelly_criterion"  # kelly_criterion, fixed_risk
```

### AI Ayarları
```yaml
ai_settings:
  confidence_threshold: 0.75      # Sinyal güven eşiği
  signal_strength_min: 0.65      # Minimum sinyal gücü
  retrain_frequency_hours: 24    # Model yeniden eğitim sıklığı
```

### Strateji Ayarları
```yaml
strategies:
  scalping:
    enabled: true
    timeframes: ["1m", "5m"]
    profit_target: 0.5            # %0.5 kar hedefi
    stop_loss: 0.3               # %0.3 stop loss
    
  swing_trading:
    enabled: true
    timeframes: ["1h", "4h"]
    profit_target: 3.0           # %3 kar hedefi
    stop_loss: 1.5              # %1.5 stop loss
```

## 📊 Monitoring ve Logs

### Log Dosyaları
- `logs/trading_bot.log` - Ana log dosyası
- `logs/errors.log` - Hata logları
- `logs/performance.log` - Performans metrikleri

### Database
- `data/trading_bot.db` - SQLite veritabanı
- Market data, pozisyonlar, trades, performans

### Monitoring
Bot çalışırken şu bilgileri izleyebilirsiniz:
- Aktif pozisyonlar
- Günlük P&L
- AI sinyal güveni
- Risk seviyesi

## 🛠️ Troubleshooting

### Yaygın Hatalar

#### 1. ModuleNotFoundError
```bash
# Eksik paket hatası için
pip install <package-name>

# Veya tüm gereksinimleri yeniden kur
pip install -r requirements.txt --upgrade
```

#### 2. API Bağlantı Hatası
- API anahtarlarınızı kontrol edin
- IP adresinizin whitelist'te olduğundan emin olun
- Sandbox modunda test edin

#### 3. Insufficient Balance
- Hesabınızda yeterli bakiye olduğundan emin olun
- Trading izinlerinin aktif olduğunu kontrol edin

#### 4. TA-Lib Kurulum Hatası
```bash
# Linux/Ubuntu için
sudo apt-get install build-essential
sudo apt-get install python3-dev
pip install TA-Lib

# Mac için
brew install ta-lib
pip install TA-Lib
```

### Log Kontrolü
```bash
# Son 100 satır log
tail -100 logs/trading_bot.log

# Hata logları
tail -50 logs/errors.log

# Real-time log takibi
tail -f logs/trading_bot.log
```

## 🔒 Güvenlik

### API Güvenliği
- API anahtarlarınızı asla paylaşmayın
- Sadece gerekli izinleri verin (trading, reading)
- IP whitelist kullanın
- Düzenli olarak API anahtarlarını yenileyin

### Risk Yönetimi
- Her zaman test modunda başlayın
- Küçük miktarlarla başlayın
- Stop loss'ları mutlaka kullanın
- Günlük kayıp limitlerini ayarlayın

## 📈 Performans İyileştirme

### Sistem Optimizasyonu
```yaml
performance:
  max_cpu_usage: 80              # Maksimum CPU kullanımı
  max_memory_usage: 4            # Maksimum RAM (GB)
  data_retention_days: 90        # Veri saklama süresi
  cleanup_frequency: 24          # Temizlik sıklığı (saat)
```

### Model Performansı
- Model eğitimi için yeterli veri biriktirin
- Düzenli olarak model performansını kontrol edin
- Gerektiğinde hiperparametreleri ayarlayın

## 🔄 Güncelleme

```bash
# Bot'u durdur
Ctrl+C

# Kod güncellemelerini çek
git pull

# Paketleri güncelle
pip install -r requirements.txt --upgrade

# Yeniden başlat
python3 main.py
```

## 📞 Destek

### Problem Çözme Sırası
1. Log dosyalarını kontrol edin
2. Test modunda çalıştırın
3. Konfigürasyon ayarlarını kontrol edin
4. Minimal test'i çalıştırın

### Performans Raporları
Bot otomatik olarak performans raporları oluşturur:
- Günlük özet
- Haftalık performans
- Model başarı oranları

## ⚡ Hızlı Başlatma Komutları

```bash
# Kurulum kontrolü
python3 test_minimal.py

# Tam test
python3 startup.py

# Test modunda başlat
python3 main.py --test-mode

# Canlı modda başlat (DİKKAT!)
python3 main.py
```

---

**⚠️ DİKKAT: Bu bot gerçek para ile işlem yapar. Mutlaka önce test modunda çalıştırın ve risk yönetimi ayarlarınızı dikkatlice yapın!**