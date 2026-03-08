import time
import schedule
from config import (
    TIMEFRAMES, CORRELATION_THRESHOLD, MAX_CORRELATION_PARTNERS, LOW_TIMEFRAME_PENALTY,
    DIVERGENCE_THRESHOLD, BTC_CRASH_THRESHOLD, ANOMALOUS_VOLUME_MULTIPLIER, COINTEGRATION_P_VALUE
)
from data_fetcher import get_active_usdt_futures, get_all_closes, get_all_volumes
from correlation_engine import compute_partial_correlation, calculate_lead_lag_divergence_and_coint, check_btc_crash
from telegram_notifier import send_message, get_chat_id
from database import init_db, record_correlation


def analyze_market_for_timeframe(timeframe):
    """Belirli bir zaman dilimi için tüm sürecin baştan sona çalıştırılması."""
    print(f"\n============================================\n[Görev Başlatıldı] Süreç: {timeframe}")
    
    symbols = get_active_usdt_futures()
    if not symbols:
        print("Market aktif verileri çekilemedi.")
        return
        
    df_closes = get_all_closes(symbols, timeframe)
    if df_closes.empty:
        print("Mum verileri yetersiz.")
        return
        
    # --- PİYASA ŞOKU / KIYAMET FİLTRESİ ---
    is_btc_crashing, btc_return = check_btc_crash(df_closes, threshold=BTC_CRASH_THRESHOLD)
    if is_btc_crashing:
        print(f"[!] DİKKAT: BTC çok sert hareket etti ({btc_return:.2f}%). İstatistiksel Arbitraj sinyalleri geçici olarak durduruldu.")
        # İsteğe bağlı olarak kullanıcıya bir kez bilgi mesajı da atılabilir:
        # send_message(f"🚨 PİYASA ŞOKU: BTC {timeframe} içinde %{btc_return:.2f} hareket etti. Sinyaller beklemeye alındı.")
        return
        
    print("[Hesaplama] BTC ve ETH etkisi arındırılıyor... Saf (Partial) Korelasyonlar hesaplanıyor...")
    corr_matrix = compute_partial_correlation(df_closes)
    
    # Haber / Anormal hacim filtresi için o timeframe'deki hacim DataFrame'ini hazırla 
    # (Sadece arbitraj fırsatı bulduğumuzda kullanacağız, önden çekelim)
    df_volumes = get_all_volumes(symbols, timeframe)
    
    # 3m ve 5m gibi düşük zaman dilimlerindeki algoritmik gürültüleri (noise) filtrelemek için eşiği zorlaştırıyoruz
    current_threshold = CORRELATION_THRESHOLD
    if timeframe in ['1m', '3m', '5m']:
        current_threshold += LOW_TIMEFRAME_PENALTY
        print(f"[{timeframe}] Gürültü filtresi devrede. Hedef korelasyon eşiği artırıldı: {current_threshold:.2f}")
    
    candidate_pairs = []
    seen_pairs = set() # A-B veya B-A kopyalarını önlemek için iz bıraktığımız hafıza kümesi
    partner_counts = {} # "Hub" etkisini saptamak için her coinin o an kaç partnerle eşleştiğini sayan sözlük
    
    columns_len = len(corr_matrix.columns)
    
    # Sadece üst üçgen matrisini dönüyoruz (A-A gibi 1.0 korelasyonları veya çift sayımları önlemek için)
    for i in range(columns_len):
        for j in range(i + 1, columns_len):
            coin1 = corr_matrix.columns[i]
            coin2 = corr_matrix.columns[j]
            corr_value = corr_matrix.iloc[i, j]
            
            # Ana coinlerimiz üzerinden arındırma yaptığımız için onları sonuçlarda göstermeye gerek yok
            if 'BTC/USDT' in coin1 or 'ETH/USDT' in coin1 or \
               'BTC/USDT' in coin2 or 'ETH/USDT' in coin2:
                continue
                
            # Eşik Kontrolü (Negatif veya Pozitif yönde güçlü korelasyon aranır)
            if abs(corr_value) >= current_threshold:
                
                # A-B ile B-A aynıdır. Alfabetik sıralayarak kopyasını yakalamak üzere tekil kimlik (ID) oluştur
                pair_id = tuple(sorted([coin1, coin2]))
                if pair_id in seen_pairs:
                    continue
                seen_pairs.add(pair_id)

                # İstatistiksel Arbitraj için Momentum (Öncü-Artçı) makasının hesaplanması (Son 3 mum)
                # ve Cointegration testi doğrulamasının yapılması
                spread, lead_series, lag_series, lead_ret, lag_ret, is_coint = calculate_lead_lag_divergence_and_coint(
                    df_closes[coin1], df_closes[coin2], lookback=3, coint_p_value_threshold=COINTEGRATION_P_VALUE
                )
                
                has_divergence = spread >= DIVERGENCE_THRESHOLD
                
                # --- ANORMAL HACİM / HABER FİLTRESİ ---
                # Eğer makas açılmışsa (Arbitraj fırsatı varsa), Öncü Coinde aşırı hacim var mı diye bak
                anomalous_volume_detected = False
                if has_divergence and not df_volumes.empty:
                    lead_ticker = coin1 if lead_series == 'A' else coin2
                    if lead_ticker in df_volumes.columns:
                        lead_vol_series = df_volumes[lead_ticker]
                        
                        if len(lead_vol_series) > 3:
                            # Son mumdaki hacim
                            recent_vol = lead_vol_series.iloc[-1]
                            # Önceki mumların ortalama hacmi
                            avg_vol = lead_vol_series.iloc[:-1].mean()
                            
                            # Eğer son mum hacmi, ortalamanın çarpımından (ANOMALOUS_VOLUME_MULTIPLIER) büyükse, bu habere dayalıdır!
                            if avg_vol > 0 and recent_vol > (avg_vol * ANOMALOUS_VOLUME_MULTIPLIER):
                                print(f"[{timeframe}] {lead_ticker} için anormal hacim saptandı! Sinyal iptal ediliyor. ({recent_vol} vs Ortalama {avg_vol:.1f})")
                                anomalous_volume_detected = True
                
                # Eğer volume çok anormal ise bu fırsatı tamamen çöpe at (listeye dahil etme)
                if anomalous_volume_detected:
                     continue

                candidate_pairs.append({
                    'coin1': coin1,
                    'coin2': coin2,
                    'corr': corr_value,
                    'spread': spread,
                    'lead_series': lead_series,
                    'lag_series': lag_series,
                    'lead_ret': lead_ret,
                    'lag_ret': lag_ret,
                    'has_divergence': has_divergence,
                    'is_cointegrated': is_coint
                })
                
                # Her coinin kaç kere birileriye eşleştiğini say ("Hub" tespiti için)
                partner_counts[coin1] = partner_counts.get(coin1, 0) + 1
                partner_counts[coin2] = partner_counts.get(coin2, 0) + 1
                
    # --- HUB FİLTRESİ ---
    # Eğer bir coin MAX_CORRELATION_PARTNERS sayısından fazla coin ile eşleştiyse onu "piyasa sürü dalgası" say.
    high_corr_pairs = []
    for p in candidate_pairs:
        # İki coinden biri bile Hub limitini aştıysa, o spesifik değil genelleşmiş bir harekettir, listeye alma.
        if partner_counts[p['coin1']] > MAX_CORRELATION_PARTNERS or \
           partner_counts[p['coin2']] > MAX_CORRELATION_PARTNERS:
            continue
            
        # Eğer bu aşamaya geçebildiyse geçerli, izole bir eşleşmedir (SQLite'a bu aşamada kaydet)
        is_special, count = record_correlation(p['coin1'], p['coin2'])
        p['is_special'] = is_special
        p['count'] = count
        high_corr_pairs.append(p)
                
    # Sonuçların Kullanıcıya Gönderilmesi
    if high_corr_pairs:
        # Aralarındaki bağ en güçlü olanları üstte göstermek için listeyi azalan şekilde sırala
        high_corr_pairs.sort(key=lambda x: abs(x['corr']), reverse=True)
        
        message = f"🔍 [{timeframe}] Zaman Dilimi Korelasyon Raporu\n"
        message += f"Saptanan Eşik: > {current_threshold:.2f}\n"
        if len(candidate_pairs) > len(high_corr_pairs):
            message += f"Hub Filtresi: {len(candidate_pairs) - len(high_corr_pairs)} sinyal piyasa dalgası sayılarak reddedildi.\n"
        message += "\n"
        
        # Fazla spam olmaması için sadece en güçlü 10 veya 15 coin çiftini de gösterebilirsiniz 
        # (Şu an tüm saptanan yüksek ilişkileri döngüye alıyoruz)
        for p in high_corr_pairs[:15]: 
            corr_perc = p['corr'] * 100
            symbol_a = p['coin1'].split(':')[0] # Ekstraları kes (Örn 'ADA/USDT:USDT' -> 'ADA/USDT')
            symbol_b = p['coin2'].split(':')[0]
            
            # Eğek kritik threshold atlanmışsa özel mesaj fırlat
            if p['is_special']:
                special_msg = f"🚨 ÖZEL ALARM!\n{symbol_a} ve {symbol_b} piyasa etkisi dışında tam {p['count']}. KEZ birbirine korele oldu gözüküyor! (Veritabanı Uyarısı)"
                send_message(special_msg)
            
            # Cointegration etiketi
            coint_tag = "🔬 (Coint: OK)" if p['is_cointegrated'] else ""
            
            # İstatistiksel Arbitraj (Lead-Lag Fırsatları) İçin Özel Duyuru Formatı
            # SADECE eğer Cointegration OK ise veya senkron çalışmasına ragmen divergans varsa uyarı ver
            if p['has_divergence'] and abs(corr_perc) > 0 and (p['lead_series'] is not None):
                if not p['is_cointegrated']:
                    # Makas açılmış ama coinler istatistiksel uyumlu değilse fırsat olarak gösterme, iptal et.
                    yön = '🟢' if corr_perc > 0 else '🔴'
                    msg_line = f"▪️ {symbol_a} <-> {symbol_b} | {yön} %{abs(corr_perc):.1f} (Makas Açık ama Coint FAILED!)"
                    if p['count'] > 0:
                        msg_line += f" (Sinyal: {p['count']})"
                    msg_line += "\n"
                    message += msg_line
                    continue
                
                lead_sym = symbol_a if p['lead_series'] == 'A' else symbol_b
                lag_sym = symbol_b if p['lag_series'] == 'B' else symbol_a
                
                # Pozitif korelasyon için normal Lead-Lag
                if corr_perc > 0:
                    lead_yön = 'yükseldi' if p['lead_ret'] > 0 else 'düştü'
                    lag_yön = 'yükseldi' if p['lag_ret'] > 0 else 'düştü'
                    hedef_yön = 'yukarı' if p['lead_ret'] > 0 else 'aşağı'
                    
                    msg_line = (
                        f"🚨 ARBİTRAJ FIRSATI {coint_tag}\n"
                        f"{lead_sym} ve {lag_sym} (%{abs(corr_perc):.1f} Korele)\n"
                        f"📈 {lead_sym} son mumlarda %{p['lead_ret']:.2f} {lead_yön}!\n"
                        f"🐢 {lag_sym} ise sadece %{p['lag_ret']:.2f} {lag_yön}. (Makas: %{p['spread']:.2f})\n"
                        f"🎯 FIRSAT: {lag_sym} geride kaldı, {hedef_yön} yönlü yakalama (catch-up) hareketi gelebilir!\n"
                    )
                else: 
                     # Ters Korelasyon için (Eğer zıt yönlüyse)
                     msg_line = f"▪️ {symbol_a} <-> {symbol_b} | 🔴 %{abs(corr_perc):.1f} (Ters Korele Fırsat Makası: %{p['spread']:.2f}) {coint_tag}\n"
            else:
                # Standart Listeleme (Divergence Yoksa)
                yön = '🟢' if corr_perc > 0 else '🔴'
                msg_line = f"▪️ {symbol_a} <-> {symbol_b} | {yön} %{abs(corr_perc):.1f} {coint_tag}"
                if p['count'] > 0:
                    msg_line += f" (Sinyal: {p['count']})"
                msg_line += "\n"
                
            message += msg_line
            
        # Eğer sayımız 15'ten çoksa bilgi ver 
        if len(high_corr_pairs) > 15:
            message += f"... ve saptanan diğer {len(high_corr_pairs)-15} çift"
            
        send_message(message)
        print(f"[{timeframe}] Başarılı! {len(high_corr_pairs)} sinyal için Telegram Raporu oluşturuldu.")
    else:
        print(f"[{timeframe}] Belirlenen eşiği (>{CORRELATION_THRESHOLD}) aşan saf korelasyon ilişkisi bulunamadı.")


def run_bot():
    print("--------------------------------------------------")
    print("🚀 Kripto Para Korelasyon / Radar Botu Başlatılıyor")
    print("--------------------------------------------------")
    
    # 1. Veritabanını Kur
    init_db()
    
    # 2. Telegram Entegrasyon Kontrolü
    print("Telegram ile senkronize olunuyor...")
    chat_id = get_chat_id()
    if chat_id:
        send_message("✅ Sistem Başarıyla Aktif!\nKorelasyon Botu zaman dilimlerini izlemeye başladı.")
    else:
        print("LÜTFEN DİKKAT: Telegram'dan bota bir kez 'Merhaba' deyin, ardından uygulamayı kapatıp tekrar açın.")
    
    # 3. Ayarlardaki Saatlere Göre Görevleri Zamanla
    for tf in TIMEFRAMES:
        if tf.endswith('m'):
            minutes = int(tf.replace('m', ''))
            schedule.every(minutes).minutes.do(analyze_market_for_timeframe, timeframe=tf)
        elif tf.endswith('h'):
            hours = int(tf.replace('h', ''))
            schedule.every(hours).hours.do(analyze_market_for_timeframe, timeframe=tf)
            
    print(f"Tanımlanan İzleme Periyotları: {TIMEFRAMES}")
    print("Arka planda çalışıyor. Taramaların başlaması bekleniyor...")
    print("Olası durdurma işlemi için (CTRL + C) tuşlayabilirsiniz.\n")
    
    # İlk çalıştırmada beklememek için tüm süreçleri anında 1 tur manuel döndürtelim
    print(">>> DİKKAT: Sistem saatini beklemeden İlk taramalar tetikleniyor...")
    for tf in TIMEFRAMES:
        analyze_market_for_timeframe(tf)
        
    # Programın uyanık kalarak planlı görevleri devam ettirdiği Sonsuz Loop
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n[!] Kullanıcı tarafından manuel olarak durduruldu.")
    except Exception as e:
        print(f"\n[X] Kritik bir hata oluştu: {e}")
