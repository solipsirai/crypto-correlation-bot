# --- AYARLAR (SETTINGS) ---

# Telegram Bot Ayarları
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# Borsa ve Veri Ayarları (ISP engelini aşmak için Türkiye'de engelsiz olan Gate.io kullanıyoruz)
EXCHANGE_ID = 'gateio'   # Veri çekmek için varsayılan borsa
QUOTE_CURRENCY = 'USDT'  # Sadece USDT paritelerini inceliyoruz
MAX_COIN_LIMIT = 200     # Çekilecek maksimum coin paritesi (Çok uzun sürmemesi için ilk 200 pariteyle sınırlandırır)
CANDLE_LIMIT = 100       # Korelasyon analizi için geriye dönük kullanılacak mum sayısı

# Zaman Aralıkları (Hangi aralıklara göre verilerin analiz edileceği)
# Desteklenen formatlar: "5m", "3m", "15m", "30m", "1h", "2h", "4h", "1d" vb.
TIMEFRAMES = ["3m", "5m", "15m", "1h"]

# Kara Liste Ayarları (Havuza dahil edilmeyecek emtialar, stabil coinler ve endeksler)
IGNORE_COINS = [
    'PAXG', 'XAUT', 'KAU', 'KAG', 'SPYX', 'QQQX', 'TQQQX', 
    'USDC', 'TUSD', 'FDUSD', 'DAI', 'USDD', 'USDE', 'EUR', 'GBP'
]
# Dinamik olarak isminin sonu bu eklerle biten kaldıraçlı tokenları engelle (Örn: BTC3L)
LEVERAGE_SUFFIXES = ['3L', '3S', '5L', '5S', '2L', '2S']

# Korelasyon Ayarları
CORRELATION_THRESHOLD = 0.85  # Hangi sonucun üzeri yüksek korelasyon kabul edilecek (0.0 ile 1.0 arası)
LOW_TIMEFRAME_PENALTY = 0.05  # 3m, 5m gibi gürültülü piyasalarda threshold ne kadar artırılsın (Örn: 0.85 + 0.05 = 0.90)

# İstatistiksel Arbitraj (Pairs Trading) ve Filtre Ayarları
MIN_24H_VOLUME = 10000000   # 24 Saatlik minimum USDT işlem hacmi (Örn: 10 Milyon Dolar). Hayalet tahtaları eler.
DIVERGENCE_THRESHOLD = 3.0  # Öncü ve Artçı coin arasındaki getiri (momentum) farkının arbitraj fırsatı vermesi için gereken yüzde sınır

# Kurumsal Risk Yönetimi (Quant) Filtreleri
COINTEGRATION_P_VALUE = 0.05       # Kointegrasyon Testi (Engle-Granger) geçerlilik sınırı (0.05 altı = Piyasayada birlikte hareket ediyorlar)
BTC_CRASH_THRESHOLD = 3.0          # Timeframe içinde BTC fiyatı %X'den fazla düşer/çıkarsa sinyal verme (Piyasa Şoku Filtresi)
ANOMALOUS_VOLUME_MULTIPLIER = 3.0  # Öncü coinin işlem hacmi son N muma göre X katından fazlaysa sinyal verme (Haber/Spekülasyon Filtresi)

# "Hub" Etkisi Filtresi
# Bir coin tek bir zaman diliminde şu sayıdan fazla coin ile korele oluyorsa, 
# bu spesifik bir ilişki değil, genel bir piyasa dalgası kabul edilir ve listeden çıkarılır.
MAX_CORRELATION_PARTNERS = 3 

# Veritabanı ve Hafıza Ayarları
USE_DATABASE_MEMORY = True    # True yaparsanız geçmişte korele olanları sayar ve 500'de özel uyarı atar
DB_NAME = "correlation_memory.sqlite" # SQLite veritabanı dosyasının ismi
SPECIAL_ALERT_COUNT = 500     # Kaçıncı kez korele olduklarında Telegram'dan özel uyarı atılacak
