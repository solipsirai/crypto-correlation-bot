import ccxt
import pandas as pd
import time
from config import EXCHANGE_ID, QUOTE_CURRENCY, CANDLE_LIMIT, MAX_COIN_LIMIT, IGNORE_COINS, LEVERAGE_SUFFIXES, MIN_24H_VOLUME

# Seçilen borsayı ccxt üzerinden ayağa kaldır (ISP bloklarını aşmak ve kopmaları önlemek için özel ayarlar)
exchange_class = getattr(ccxt, EXCHANGE_ID)
exchange = exchange_class({
    'enableRateLimit': True,
    'timeout': 30000,
    'options': {
        'defaultType': 'future'  # Vadeli işlemler paritelerini listelemek için 
    }
})

def is_valid_altcoin(symbol):
    """Sembolün kara listede veya kaldıraçlı ETF (3L, 5S vb) formatında olup olmadığını kontrol eder."""
    base_coin = symbol.split('/')[0] # Örn: 'BTC/USDT:USDT' -> 'BTC'
    
    # Tam eşleşme olan gümüş, altın stabil coin kontrolü
    if base_coin in IGNORE_COINS:
        return False
        
    # Sonu 3L, 5S vb. ile biten tokenlar kontrolü
    for suffix in LEVERAGE_SUFFIXES:
        if base_coin.endswith(suffix):
            return False
            
    return True

def get_active_usdt_futures():
    """Borsadaki tüm aktif ve çalışır durumdaki USDT vadeli paritelerini hacim filtresiyle getirir."""
    try:
        exchange.load_markets()
        print("[Veri İndirme] 24 saatlik hacim verileri (Tickers) kontrol ediliyor...")
        
        # Hacimleri almak için tekil bir borsa API isteği yap
        tickers = exchange.fetch_tickers()
        
        active_symbols = []
        for symbol, market in exchange.markets.items():
            # Vadeli ve aktif olan USDT pariteleri (Örn: BTC/USDT:USDT)
            # Gate.io USDT-M Swap'leri genelde 'linear': True ile ve QUOTE_CURRENCY ile tutulur.
            if market.get('active', True) and market.get('quote') == QUOTE_CURRENCY and market.get('linear', True):
                if is_valid_altcoin(symbol):
                    ticker = tickers.get(symbol, {})
                    
                    # ccxt verisinden 24 saatlik alıntı (USDT) hacmini çıkar
                    quote_volume = ticker.get('quoteVolume', 0)
                    if quote_volume is None:
                        quote_volume = 0
                        
                    # Hacim filtresine takılmayan "sağlıklı" altcoinleri listeye dahil et
                    if quote_volume >= MIN_24H_VOLUME:
                        active_symbols.append(symbol)
                
        print(f"[Filtre Sonucu] Hacim ({MIN_24H_VOLUME}) ve Blacklist onayından geçen parite sayısı: {len(active_symbols)}")
        return active_symbols[:MAX_COIN_LIMIT]
    except Exception as e:
        print(f"[Veri Hatası] Market pariteleri çekilirken hata oluştu: {e}")
        return []

def fetch_ohlcv(symbol, timeframe, limit=CANDLE_LIMIT, max_retries=3):
    """Verilen sembol ve süre için kapanış fiyatlarını döndürür. (Hata korumalı)"""
    for attempt in range(max_retries):
        try:
            # Mum bilgilerini al [timestamp, open, high, low, close, volume]
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not candles:
                return None
                
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df['close']
        except Exception as e:
            if attempt == max_retries - 1:
                # Son denemede pas geç
                print(f"[Uyarı] {symbol} mum verisi alınamadı: {e}")
                return None
            time.sleep(1) # Hata aldıysan kısa bir bekleme yap (Rate limit, SSL vb. geçici kopukluklara karşı)

def get_all_closes(symbols, timeframe):
    """
    Tüm coinlerin kapanış fiyatlarını alıp tek bir DataFrame tablosunda birleştirir.
    Sütunlar: Coinler, Satırlar: Zaman dilimleri
    """
    closes = {}
    total_symbols = len(symbols)
    print(f"\n[Veri İndirme] {timeframe} zaman aralığı için {total_symbols} coinin mum verileri çekiliyor...")
    
    cnt = 0
    for sym in symbols:
        close_data = fetch_ohlcv(sym, timeframe)
        if close_data is not None and not close_data.empty:
            closes[sym] = close_data
            
        cnt += 1
        # İlerlemeyi belirli aralıklarla consol'da göster
        if cnt % 50 == 0:
            print(f"... İlerleme: {cnt}/{total_symbols} coin tamamlandı.")
            
    # Hepsini tek bir veri tablosunda hizala
    df_closes = pd.DataFrame(closes)
    
    # Eksik satır veya sütunlara sahip kirli verileri devre dışı bırak.
    df_closes.dropna(axis=1, inplace=True) 
    
    return df_closes

def get_all_volumes(symbols, timeframe):
    """
    Anormal Hacim (Haber Etkisi) filtrelemesi için verileri çeker.
    Tüm coinlerin Hacim (Volume) verilerini alıp DataFrame tablosunda birleştirir.
    Sütunlar: Coinler, Satırlar: Zaman dilimleri
    """
    volumes = {}
    print(f"[Veri İndirme] {timeframe} zaman aralığı Hacim serileri kontrol ediliyor...")
    
    for sym in symbols:
        try:
            candles = exchange.fetch_ohlcv(sym, timeframe, limit=CANDLE_LIMIT)
            if candles:
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                volumes[sym] = df['volume']
        except Exception as e:
            continue
            
    df_volumes = pd.DataFrame(volumes)
    df_volumes.dropna(axis=1, inplace=True) 
    
    return df_volumes
