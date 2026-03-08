import sqlite3
import os
from config import DB_NAME, SPECIAL_ALERT_COUNT, USE_DATABASE_MEMORY

def init_db():
    if not USE_DATABASE_MEMORY:
        return
    
    # Veritabanını ve tabloyu oluştur
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS correlation_counts (
            pair_id TEXT PRIMARY KEY,
            coin1 TEXT,
            coin2 TEXT,
            count INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def record_correlation(coin1, coin2):
    """
    İki coin arasındaki yüksek korelasyonu veritabanına kaydeder/sayacı artırır.
    Özel eşik değeri (örn. 500) aşıldığında True döner.
    """
    if not USE_DATABASE_MEMORY:
        return False, 0
    
    # Çift sırasından bağımsız olarak (Örn: A-B ile B-A aynıdır) saymak için adları alfabetik diziyoruz
    coins = sorted([coin1, coin2])
    pair_id = f"{coins[0]}_{coins[1]}"
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Çifti veritabanında ara
    cursor.execute('SELECT count FROM correlation_counts WHERE pair_id = ?', (pair_id,))
    row = cursor.fetchone()
    
    if row:
        new_count = row[0] + 1
        cursor.execute('UPDATE correlation_counts SET count = ? WHERE pair_id = ?', (new_count, pair_id))
    else:
        new_count = 1
        cursor.execute('INSERT INTO correlation_counts (pair_id, coin1, coin2, count) VALUES (?, ?, ?, ?)', 
                       (pair_id, coins[0], coins[1], new_count))
        
    conn.commit()
    conn.close()
    
    # Sinyalin özel eşikleri aşıp aşmadığını test et
    is_special = (new_count > 0 and new_count % SPECIAL_ALERT_COUNT == 0)
    return is_special, new_count
