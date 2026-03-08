import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

def compute_partial_correlation(df_closes):
    """
    BTC ve ETH'nin yarattığı genel piyasa dalgalanma etkisini (market effect) 
    İstatiksel olarak (Linear Regression / Beta Neutralization) arındırır.
    Sadece coinlerin kendi aralarındaki 'özel' Pearson korelasyonlarını döndürür.
    """
    
    # Fiyatlardan yüzdelik getiri (returns) hesapla ki korelasyon anlamlı olsun
    returns = df_closes.pct_change().dropna()
    coins = returns.columns.tolist()
    
    # CCXT sembol verilerinde BTC ve ETH isimlerini dinamik olarak ara (Örn: 'BTC/USDT:USDT' vd.)
    btc_symbol = next((s for s in coins if s.startswith('BTC/USDT')), None)
    eth_symbol = next((s for s in coins if s.startswith('ETH/USDT')), None)
    
    if not btc_symbol or not eth_symbol:
        print("[Uyarı] BTC veya ETH sembolü parite tablosunda bulunamadı. Arındırma işlemi yapılamıyor, normal korelasyon veriliyor! (Lütfen borsa paritelerini kontrol edin)")
        return returns.corr()
    
    # Bağımsız değişken matrisi Z (1 Sabiti ile, BTC ve ETH getirileri)
    Z = pd.DataFrame({
        'const': 1,
        'BTC': returns[btc_symbol],
        'ETH': returns[eth_symbol]
    })
    
    Z_mat = Z.values
    
    # Çoklu Lineer Regresyon Çözümü (Pseudo-Inverse ile)
    try:
        # Z matrisi için ters (pseudo-inverse) işlemi
        Z_pinv = np.linalg.pinv(Z_mat.T @ Z_mat) @ Z_mat.T
    except np.linalg.LinAlgError:
        print("[Uyarı] Matris hesaplama hatası oluştu, arındırılmamış direkt korelasyon döndürülüyor.")
        return returns.corr()
    
    # Bağımlı (Açıklanan) Matris: Tüm coinlerin getirileri
    Y = returns.values
    
    # Beta katsayılarını (Regresyon Ağırlıklarını) bul
    B = Z_pinv @ Y
    
    # Modellenen getiri (Piyasanın o coindeki tahmini etkisi)
    Y_pred = Z_mat @ B
    
    # Artıklar (Residuals): Coinin toplam getirisinden, pazar etkisini (BTC+ETH) çıkartıyoruz.
    # Elde kalan şey, coinin sadece kendisine ait, arındırılmış hareketleridir.
    residuals = Y - Y_pred
    
    # Artık getirileri baz alıp normal aralarında korelasyon hesapla
    df_residuals = pd.DataFrame(residuals, columns=coins)
    partial_corr_matrix = df_residuals.corr()
    
    return partial_corr_matrix

def check_btc_crash(df_closes, threshold=3.0, btc_symbol='BTC/USDT:USDT'):
    """
    BTC'nin ilgili timeframe içerisindeki hareketini kontrol eder.
    Eğer düşüş veya yükseliş belirlenen % threshold'dan fazlaysa True (Crash/Shock var) döndürür.
    """
    if btc_symbol not in df_closes.columns:
        return False, 0.0
        
    btc_series = df_closes[btc_symbol]
    if len(btc_series) < 2:
        return False, 0.0
        
    # İlk muma göre son mumdaki değişim (Timeframe içi komple hareket)
    btc_return = ((btc_series.iloc[-1] / btc_series.iloc[0]) - 1) * 100
    
    if abs(btc_return) >= threshold:
        return True, btc_return
    return False, btc_return

def calculate_lead_lag_divergence_and_coint(series_a, series_b, lookback=3, coint_p_value_threshold=0.05):
    """
    İki coinin anlık getiri (momentum) farkını hesaplar ve Cointegration uygular.
    Cointegration (Engle-Granger) testi ile iki fiyat serisinin tarihsel süreçte 'mean-reverting' 
    (birbirine dönen/kavuşan) bir yapıya sahip olup olmadığını doğrular.
    """
    if len(series_a) < lookback + 1 or len(series_b) < lookback + 1:
        return 0.0, None, None, 0.0, 0.0, False
        
    # 1. Cointegration Testi (İki fiyat serisi arasında uzun vadeli bir denge var mı?)
    # Null Hypothesis: Seriler ko-entegre (cointegrated) DEĞİLDİR.
    # p-value < 0.05 ise null hypothesis reddedilir, yani seriler %95 güvenle KO-ENTEGRE'dir diyebiliriz.
    try:
        # İkinci dönüş olarak p-value gelir
        score, p_value, _ = coint(series_a.values, series_b.values)
        is_cointegrated = p_value < coint_p_value_threshold
    except Exception as e:
        is_cointegrated = False # Hata varsa temkinli davranıp testi başarısız say
        
    # 2. Öncü - Artçı Momentum (Spread) Hesaplaması
    # Son 'lookback' muma göre yüzde kaç değişim (Return) yaşanmış?
    return_a = ((series_a.iloc[-1] / series_a.iloc[-(lookback + 1)]) - 1) * 100
    return_b = ((series_b.iloc[-1] / series_b.iloc[-(lookback + 1)]) - 1) * 100
    
    spread = abs(return_a - return_b)
    
    if return_a > return_b:
        lead_return, lag_return = return_a, return_b
        lead_series, lag_series = 'A', 'B'
    else:
        lead_return, lag_return = return_b, return_a
        lead_series, lag_series = 'B', 'A'
        
    return spread, lead_series, lag_series, lead_return, lag_return, is_cointegrated

