import requests
from config import TELEGRAM_BOT_TOKEN

# Uygulama çalıştığı sürece chat id'yi hafızada tutup API limitlerini zorlamayalım
_cached_chat_id = None

def get_chat_id():
    """Bot üzerinden gelen son mesaja bakarak kullanıcının Chat ID'sini otomatik olarak bulur."""
    global _cached_chat_id
    if _cached_chat_id is not None:
        return _cached_chat_id

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        response = requests.get(url).json()
        if response.get("ok") and len(response.get("result", [])) > 0:
            # En son gelen mesajdaki kullanıcının chat_id bilgisini alıyoruz
            _cached_chat_id = str(response["result"][-1]["message"]["chat"]["id"])
            print(f"[Telegram] Chat ID otomatik olarak bulundu: {_cached_chat_id}")
            return _cached_chat_id
        else:
            print("[Telegram] Chat ID Bulunamadı! Bota Telegram'dan '/start' komutu veya bir mesaj gönderin.")
            return None
    except Exception as e:
        print(f"[Telegram API Hatası (getUpdates)]: {e}")
        return None

def send_message(text):
    """Bulunan chat ID'ye Telegram mesajı gönderir"""
    chat_id = get_chat_id()
    if not chat_id:
        # Chat_id bilinemiyorsa mesaj gönderemeyiz, konsola log basılır
        # print("-> [Kaçırılan Sinyal - Telegram kapalı]:", text.replace('\\n', ' '))
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
        # "parse_mode": "HTML" - Removed to prevent Bad Request errors with special characters
    }
    try:
        resp = requests.post(url, json=payload).json()
        if not resp.get("ok"):
            print(f"[Telegram API Hatası (sendMessage)]: {resp.get('description')}")
    except Exception as e:
        print(f"[Telegram Hatası]: {e}")
