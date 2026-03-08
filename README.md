# ⚡ Crypto Quantitative Correlation & Arbitrage Bot

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Profesyonel bir perspektifle tasarlanmış, kripto para piyasasındaki anlamsız gürültüyü filtreleyerek **istatistiksel arbitraj (Pairs Trading, Lead-Lag)** fırsatlarını yakalayan tamamen otonom bir analiz aracıdır.

## 🎯 Vizyon ve Tasarım Felsefesi

Kripto para piyasası yapısal olarak yüksek korelasyonlu ve gürültülü (noisy) hareket eder. Bir "Hub" veya sürü (herd) psikolojisi tetiklendiğinde tüm altcoinler Bitcoin veya Ethereum önderliğinde aynı yöne gider.

Bu proje, sistemi **tıpkı bir üretim hattındaki (supply chain) hassas bir proses kontrol mekanizması** gibi kurgulayarak inşa edilmiştir. Sadece ham grafikleri ve fiyatları almaz; veriyi alır, kirlilikten (Bitcoin/Ethereum etkisinden) arındırır, sürü psikolojisini (Hub Effect) eler ve sadece kendi iç dinamikleriyle **birlikte hareket etme eğiliminde (Cointegrated) olan izole coin çiftlerini** bularak rafine sinyallere dönüştürür. 

Elde edilen rafine veri ile, hangi coinin (Öncü/Lead) fırladığını, hangisinin (Artçı/Lag) korelasyona rağmen fiyat eyleminde geride kaldığını hesaplayarak anlık yatırımcılara "Catch-up" (Yakalama) vizyonu sunar.

## ✨ Temel Özellikler

*   **Piyasa Etkisi Arındırması (Partial Correlation):** Seçilen altcoinler arasındaki sadece "saf" ilişkiyi (Pearson) ölçmek için, BTC ve ETH'nin genel piyasa dalgalandırmalarını istatistiksel modeller (Multiple Linear Regression) vasıtasıyla veriden izole eder.
*   **İstatistiksel Doğrulama (Cointegration):** Basit korelasyona aldanmaz. `statsmodels` kullanarak fiyat serileri arasında (Engle-Granger) doğrulaması yapar. Sadece `P-Value < 0.05` seviyesinde 'Mean-reverting' (tekrar dengeye dönecek) çiftleri onaylar.
*   **Lead-Lag (Öncü-Artçı) ve Z-Score Spread Ölçümü:** Korelasyonu teyit edilmiş coinler arasındaki bağıl makası ölçerek anlık gecikmeleri yakalar ve telegram üzerinden fırsat yönünü bildirir. 
*   **Otomatik Telegram Entegrasyonu:** Bot başlatıldığı anda CHAT ID'nizi `getUpdates` metoduyla kendi kendine bulur, `.env` veya ekstra config zahmetine sokmaz. Hızlı ve zahmetsiz devreye alım imkanı sunar.
*   **Gelişmiş Risk Tesisatı (Quant Filters):**
    *   **Anti-Spam "Hub" Filtresi:** Eğer belli bir zaman diliminde tüm piyasa yeşile bürünüp bir coin çok sayıda altcoin ile sahte korelasyon üretiyorsa, bu "sürü piskolojisidir" der ve sinyali engeller.
    *   **Kıyamet (Market Shock) Filtresi:** Bitcoin anlık bir çöküş/fırlayış (%X) ivmesine girdiyse istatistiksel fırsatların tümünü geçici dondurur.
    *   **Anormal Haber/Hacim Filtresi:** Öncü (lead) coinde anormal bir hacim patlaması (3-4 kat) varsa bunu spesifik bir habere bağlar, artçı coinin arayışı iptal edilir.
    *   **Sığ Tahta Filtresi:** Sadece örneğin günlük hacmi 10 Milyon USDT üzerindeki derin tahtalar analize girer.

## 🚀 Kurulum & Kullanım

Proje, herhangi bir API KEY gerektirmeden, **gate.io (veya dilediğiniz bir ccxt borsası)** üzerinden açık kaynak public fiyat verilerini okuyarak çalışır. 

### 1. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Telegram Botunuzu Bağlayın
BotFather (Telegram) üzerinden aldığınız Bot Token'ınızı `config.py` dosyasına yapıştırın:
```python
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
```
Ardından oluşturduğunuz Telegram botuna girip bir kez `/start` veya `Merhaba` deyin.

### 3. Sistemi Başlatın
```bash
python main.py
```
Sistem chat-id'nizi otomatik tespit edip otonom taramalara başlayacaktır!

## ⚙️ Yapılandırma (config.py)
Aşağıdaki gibi bir çok kural setini `config.py` içerisinden kendi risk profilinize göre anında modifiye edebilirsiniz:
*   `TIMEFRAMES`: Taranacak zaman dilimleri (Örn: `['5m', '15m', '1h']`)
*   `CORRELATION_THRESHOLD`: Hedef Korelasyon Oranı (Örn: `0.85`)
*   `COINTEGRATION_P_VALUE`: P-Value Doğrulama Sınırı (Örn: `0.05`)
*   `MIN_24H_VOLUME`: Minimum Hacim Derinliği (Örn: `10000000`)
*   `BTC_CRASH_THRESHOLD`: Piyasa Şoku Yüzdesi (Örn: `3.0`)

---

### ⚖️ Yasal Uyarı (Disclaimer)
*Bu yazılım tamamen açık kaynaklı bir mühendislik ve veri bilimi araştırma projesi (Proof of Concept) olarak tasarlanmıştır. Çıktıların hiçbiri bir ticaret sistemi teklifi veya finansal yatırım tavsiyesi (YTD) niteliği taşımaz. Finansal piyasalar doğası gereği yüksek risk içerir, projenin kullanımı sonucu doğabilecek kâr veya zararlardan kodun geliştiricileri veya katkıda bulunanlar sorumlu tutulamaz. Yazılımı kullanmadan önce daima kendi risk analizinizi ve testlerinizi gerçekleştirmeniz önerilir.*
