import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time

DB_DOSYA = "veritabani.json"
TARAMA_LIMITI = 200  # HER SEFERİNDE KAÇ FİLM TARANSIN?

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})

def db_yukle():
    if os.path.exists(DB_DOSYA):
        with open(DB_DOSYA, "r", encoding="utf-8") as f: return json.load(f)
    return []

def db_kaydet(veri):
    with open(DB_DOSYA, "w", encoding="utf-8") as f: json.dump(veri, f, ensure_ascii=False, indent=4)

def altyazi_bul(sayfa_url):
    try:
        # Altyazı kontrol ederken çok seri istek atarsan engellenebilirsin, 
        # buraya minik bir bekleme koymak sağlıklıdır.
        time.sleep(0.5) 
        
        # Link yapısı tahmini
        test_url = sayfa_url.replace("index.m3u8", "subtitle-tur-1.vtt")
        check = scraper.head(test_url, timeout=5)
        if check.status_code == 200: return test_url
        
        test_url2 = sayfa_url.replace("index.m3u8", "subtitle-tur-2.vtt")
        if scraper.head(test_url2, timeout=5).status_code == 200: return test_url2
    except: pass
    return "YOK"

def baslat():
    veritabani = db_yukle()
    toplam_db = len(veritabani)
    
    # Bu turda işlem yapılan film sayısı
    bu_tur_taranan = 0
    yeni_altyazi = 0

    print(f"🕵️ Altyazı Taraması Başladı (Hedef: {TARAMA_LIMITI} adet film)...")

    for film in veritabani:
        # Eğer limiti doldurduysak döngüyü kır ve bitir
        if bu_tur_taranan >= TARAMA_LIMITI:
            print(f"🛑 Günlük limit olan {TARAMA_LIMITI} filme ulaşıldı. Duruluyor...")
            break

        # Sadece altyazısı taranmamış (None veya boş string) olanları tara
        # NOT: 'YOK' yazanları tekrar taramaz, bu sayede kaldığı yerden devam eder.
        if film.get("altyazi") is None or film.get("altyazi") == "":
            
            bu_tur_taranan += 1
            print(f"🔍 [{bu_tur_taranan}/{TARAMA_LIMITI}] Aranıyor: {film['baslik']}")
            
            sonuc = altyazi_bul(film["video_url"])
            film["altyazi"] = sonuc # Bulamazsa 'YOK' yazar, bulursa linki yazar
            
            if sonuc != "YOK":
                yeni_altyazi += 1
                print(f"   ✅ BULDUM: {sonuc}")
            else:
                print(f"   ❌ Bulunamadı (İşaretlendi)")
            
            # Her 10 filmde bir veya limit dolunca kaydet
            if bu_tur_taranan % 10 == 0:
                db_kaydet(veritabani)
    
    db_kaydet(veritabani)
    print(f"---")
    print(f"🏁 İşlem Tamamlandı!")
    print(f"📊 Toplam Taranan: {bu_tur_taranan}")
    print(f"✨ Yeni Eklenen: {yeni_altyazi}")

if __name__ == "__main__":
    baslat()

